"""Product recommendations: content-based and co-occurrence."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.config import CLEAN_CATALOG_PATH, COOCCURRENCE_PATH, DEFAULT_TOP_K, RANDOM_SEED
from src.embedding_generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """Recommended product with similarity score."""

    product_id: int
    score: float
    title: str
    category: str
    price: float
    rating: float
    reason: str


class ProductRecommender:
    """Content-based and co-occurrence product recommendations."""

    def __init__(
        self,
        catalog_path: Path = CLEAN_CATALOG_PATH,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        seed: int = RANDOM_SEED,
    ):
        self.catalog_path = catalog_path
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.seed = seed
        self._df: Optional[pd.DataFrame] = None
        self._embeddings: Optional[np.ndarray] = None
        self._records: Optional[list[dict]] = None
        self._id_to_idx: Optional[dict[int, int]] = None
        self._cooccurrence: Optional[pd.DataFrame] = None

    def _load(self) -> None:
        if self._df is not None:
            return
        self._df = pd.read_csv(self.catalog_path)
        self._records = self._df.to_dict("records")
        self._id_to_idx = {int(pid): i for i, pid in enumerate(self._df["id"])}
        self._embeddings, _ = self.embedding_generator.load_embeddings()
        self._load_cooccurrence()

    def _load_cooccurrence(self) -> None:
        if COOCCURRENCE_PATH.exists():
            self._cooccurrence = pd.read_parquet(COOCCURRENCE_PATH)
            return
        self._build_cooccurrence()
        COOCCURRENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._cooccurrence.to_parquet(COOCCURRENCE_PATH, index=False)
        logger.info("Cached co-occurrence matrix to %s", COOCCURRENCE_PATH)

    def _build_cooccurrence(self) -> None:
        """Simulate 'users who viewed this also viewed' co-occurrence matrix."""
        assert self._df is not None
        rng = np.random.default_rng(self.seed)
        pairs: list[tuple[int, int, int]] = []

        cat_groups = self._df.groupby("category").indices
        ids = self._df["id"].to_numpy()

        for indices in cat_groups.values():
            idx_list = list(indices)
            if len(idx_list) < 2:
                continue
            for i in idx_list:
                others = [j for j in idx_list if j != i]
                n_neighbors = min(8, len(others))
                neighbors = rng.choice(others, size=n_neighbors, replace=False)
                for j in neighbors:
                    pairs.append((int(ids[i]), int(ids[j]), int(rng.integers(1, 50))))

        self._cooccurrence = pd.DataFrame(pairs, columns=["source_id", "target_id", "count"])

    def similar_products(
        self,
        product_id: int,
        top_n: int = DEFAULT_TOP_K,
    ) -> list[Recommendation]:
        """Return top-N similar products by embedding cosine similarity."""
        self._load()
        assert (
            self._records is not None
            and self._embeddings is not None
            and self._id_to_idx is not None
        )

        if product_id not in self._id_to_idx:
            raise ValueError(f"Product id {product_id} not found in catalog")

        idx = self._id_to_idx[product_id]
        scores = self._embeddings @ self._embeddings[idx]

        pool = min(len(scores) - 1, top_n + 5)
        candidates = np.argpartition(-scores, pool)[: pool + 1]
        candidates = candidates[candidates != idx]
        candidates = candidates[np.argsort(-scores[candidates])][:top_n]

        results: list[Recommendation] = []
        for ridx in candidates:
            row = self._records[int(ridx)]
            results.append(
                Recommendation(
                    product_id=int(row["id"]),
                    score=float(scores[ridx]),
                    title=str(row["title"]),
                    category=str(row["category"]),
                    price=float(row["price"]),
                    rating=float(row["rating"]),
                    reason="content_similarity",
                )
            )
        return results

    def also_viewed(
        self,
        product_id: int,
        top_n: int = DEFAULT_TOP_K,
    ) -> list[Recommendation]:
        """Co-occurrence based 'users who viewed this also viewed' recommendations."""
        self._load()
        assert self._records is not None and self._cooccurrence is not None

        subset = self._cooccurrence[self._cooccurrence["source_id"] == product_id]
        if subset.empty:
            recs = self.similar_products(product_id, top_n=top_n)
            for r in recs:
                r.reason = "content_fallback"
            return recs

        subset = subset.nlargest(top_n, "count")
        id_to_row = {int(r["id"]): r for r in self._records}
        max_count = float(subset["count"].max())
        results: list[Recommendation] = []

        for row in subset.itertuples(index=False):
            pid = int(row.target_id)
            if pid not in id_to_row:
                continue
            prod = id_to_row[pid]
            results.append(
                Recommendation(
                    product_id=pid,
                    score=float(row.count / max_count),
                    title=str(prod["title"]),
                    category=str(prod["category"]),
                    price=float(prod["price"]),
                    rating=float(prod["rating"]),
                    reason="also_viewed",
                )
            )
        return results

    def recommend(
        self,
        product_id: int,
        top_n: int = DEFAULT_TOP_K,
        blend_cooccurrence: float = 0.4,
    ) -> list[Recommendation]:
        """Blend content similarity and co-occurrence scores."""
        content = {r.product_id: r for r in self.similar_products(product_id, top_n=top_n * 2)}
        also = {r.product_id: r for r in self.also_viewed(product_id, top_n=top_n * 2)}

        scores: dict[int, float] = {}
        meta: dict[int, Recommendation] = {}

        for pid, r in content.items():
            scores[pid] = scores.get(pid, 0.0) + (1 - blend_cooccurrence) * r.score
            meta[pid] = r

        for pid, r in also.items():
            scores[pid] = scores.get(pid, 0.0) + blend_cooccurrence * r.score
            meta.setdefault(pid, r)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [
            Recommendation(
                product_id=pid,
                score=sc,
                title=meta[pid].title,
                category=meta[pid].category,
                price=meta[pid].price,
                rating=meta[pid].rating,
                reason="blended",
            )
            for pid, sc in ranked
        ]
