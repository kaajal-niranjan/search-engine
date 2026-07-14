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
from src.filter_engine import FilterCriteria, FilterEngine
from src.vector_search import SearchResult

logger = logging.getLogger(__name__)

_FILTER_CANDIDATE_MULTIPLIER = 10
_DEFAULT_CANDIDATE_MULTIPLIER = 3


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
        self._filter_engine = FilterEngine()

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

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        apply_filters: bool = True,
    ) -> list[SearchResult]:
        """
        Return BM25-ranked products for a keyword query.

        Ranks by BM25 first, then applies Filter Engine (category / price / rating)
        when apply_filters is True.
        """
        self._load_and_index()
        assert self._records is not None and self._bm25 is not None

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = np.asarray(self._bm25.get_scores(query_tokens), dtype=np.float32)
        criteria = FilterCriteria.from_kwargs(
            category=category,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
        )
        mult = (
            _FILTER_CANDIDATE_MULTIPLIER
            if apply_filters and criteria.is_active()
            else _DEFAULT_CANDIDATE_MULTIPLIER
        )
        pool = min(len(scores), top_k * mult)

        if pool < len(scores):
            candidate_idx = np.argpartition(-scores, pool - 1)[:pool]
            candidate_idx = candidate_idx[np.argsort(-scores[candidate_idx])]
        else:
            candidate_idx = np.argsort(-scores)

        ranked: list[SearchResult] = []
        for idx in candidate_idx:
            row = self._records[int(idx)]
            ranked.append(
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

        if not apply_filters:
            return ranked[:top_k]

        return self._filter_engine.apply(ranked, criteria, top_k=top_k)
