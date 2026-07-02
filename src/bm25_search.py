"""BM25 keyword-based search baseline."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from src.config import CLEAN_CATALOG_PATH, DEFAULT_TOP_K
from src.vector_search import SearchResult

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Simple lowercase alphanumeric tokenization."""
    return re.findall(r"\b\w+\b", text.lower())


class KeywordSearch:
    """BM25 keyword search over product search_text field."""

    def __init__(self, catalog_path: Path = CLEAN_CATALOG_PATH):
        self.catalog_path = catalog_path
        self._df: Optional[pd.DataFrame] = None
        self._records: Optional[list[dict]] = None
        self._bm25: Optional[BM25Okapi] = None

    def _load_and_index(self) -> None:
        if self._bm25 is not None:
            return

        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog not found: {self.catalog_path}")

        self._df = pd.read_csv(self.catalog_path)
        self._records = self._df.to_dict("records")
        corpus_tokens = [_tokenize(t) for t in self._df["search_text"].astype(str)]
        self._bm25 = BM25Okapi(corpus_tokens)
        logger.info("BM25 index built over %d documents", len(self._df))

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

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
    ) -> list[SearchResult]:
        """Return BM25-ranked products for a keyword query."""
        self._load_and_index()
        assert self._records is not None and self._bm25 is not None

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = np.asarray(self._bm25.get_scores(query_tokens), dtype=np.float32)
        has_filters = any(v is not None for v in (category, min_price, max_price, min_rating))
        pool = min(len(scores), top_k * (10 if has_filters else 3))

        if pool < len(scores):
            candidate_idx = np.argpartition(-scores, pool - 1)[:pool]
            candidate_idx = candidate_idx[np.argsort(-scores[candidate_idx])]
        else:
            candidate_idx = np.argsort(-scores)

        results: list[SearchResult] = []
        for idx in candidate_idx:
            row = self._records[int(idx)]
            if not self._passes_filters(row, category, min_price, max_price, min_rating):
                continue
            results.append(
                SearchResult(
                    product_id=int(row["id"]),
                    score=float(scores[idx]),
                    title=str(row["title"]),
                    description=str(row["description"]),
                    category=str(row["category"]),
                    price=float(row["price"]),
                    rating=float(row["rating"]),
                )
            )
            if len(results) >= top_k:
                break

        return results
