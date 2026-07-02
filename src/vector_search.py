"""FAISS-based semantic vector search."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
import pandas as pd

from src.config import (
    CLEAN_CATALOG_PATH,
    DEFAULT_TOP_K,
    EMBEDDING_DIMENSION,
    FAISS_INDEX_PATH,
)
from src.embedding_generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result with product metadata and score."""

    product_id: int
    score: float
    title: str
    description: str
    category: str
    price: float
    rating: float


class VectorSearch:
    """FAISS index for fast nearest-neighbor semantic search."""

    def __init__(
        self,
        catalog_path: Path = CLEAN_CATALOG_PATH,
        index_path: Path = FAISS_INDEX_PATH,
        embedding_generator: Optional[EmbeddingGenerator] = None,
    ):
        self.catalog_path = catalog_path
        self.index_path = index_path
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self._index: Optional[faiss.IndexFlatIP] = None
        self._df: Optional[pd.DataFrame] = None
        self._records: Optional[list[dict]] = None

    def _load_catalog(self) -> pd.DataFrame:
        if self._df is None:
            if not self.catalog_path.exists():
                raise FileNotFoundError(f"Catalog not found: {self.catalog_path}")
            self._df = pd.read_csv(self.catalog_path)
            self._records = self._df.to_dict("records")
        return self._df

    def build_index(self, force: bool = False) -> faiss.IndexFlatIP:
        """Build or load FAISS inner-product index (cosine sim on normalized vectors)."""
        if not force and self.index_path.exists():
            logger.info("Loading FAISS index from %s", self.index_path)
            self._index = faiss.read_index(str(self.index_path))
            self._load_catalog()
            return self._index

        embeddings, product_ids = self.embedding_generator.generate()
        dim = embeddings.shape[1]
        if dim != EMBEDDING_DIMENSION:
            logger.warning("Embedding dim %d differs from config %d", dim, EMBEDDING_DIMENSION)

        index = faiss.IndexFlatIP(dim)
        index.add(np.ascontiguousarray(embeddings, dtype=np.float32))

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_path))
        logger.info("Built FAISS index with %d vectors", index.ntotal)

        self._index = index
        self._load_catalog()
        self._product_ids = product_ids
        return index

    @property
    def index(self) -> faiss.IndexFlatIP:
        if self._index is None:
            self.build_index()
        return self._index  # type: ignore[return-value]

    def _passes_filters(
        self,
        row: dict,
        category: Optional[str],
        min_price: Optional[float],
        max_price: Optional[float],
        min_rating: Optional[float],
    ) -> bool:
        if category and row["category"] != category:
            return False
        if min_price is not None and row["price"] < min_price:
            return False
        if max_price is not None and row["price"] > max_price:
            return False
        if min_rating is not None and row["rating"] < min_rating:
            return False
        return True

    def _row_to_result(self, row: dict, score: float) -> SearchResult:
        return SearchResult(
            product_id=int(row["id"]),
            score=float(score),
            title=str(row["title"]),
            description=str(row["description"]),
            category=str(row["category"]),
            price=float(row["price"]),
            rating=float(row["rating"]),
        )

    def search_with_vector(
        self,
        query_vec: np.ndarray,
        top_k: int = DEFAULT_TOP_K,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
    ) -> list[SearchResult]:
        """Semantic search using a precomputed query embedding."""
        self._load_catalog()
        assert self._records is not None

        has_filters = any(v is not None for v in (category, min_price, max_price, min_rating))
        fetch_k = min(len(self._records), top_k * (5 if has_filters else 2))

        vec = np.ascontiguousarray(query_vec.astype(np.float32).reshape(1, -1))
        scores, indices = self.index.search(vec, fetch_k)

        results: list[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            row = self._records[idx]
            if not self._passes_filters(row, category, min_price, max_price, min_rating):
                continue
            results.append(self._row_to_result(row, score))
            if len(results) >= top_k:
                break
        return results

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        query_vec: Optional[np.ndarray] = None,
    ) -> list[SearchResult]:
        """Semantic search: natural-language query -> ranked products."""
        if query_vec is None:
            query_vec = self.embedding_generator.encode_query(query)
        return self.search_with_vector(
            query_vec,
            top_k=top_k,
            category=category,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
        )
