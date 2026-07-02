"""Hybrid search combining semantic and BM25 scores with filters."""

from __future__ import annotations

import logging
from typing import Optional

from src.bm25_search import KeywordSearch
from src.config import (
    DEFAULT_BM25_WEIGHT,
    DEFAULT_SEMANTIC_WEIGHT,
    DEFAULT_TOP_K,
    HYBRID_CANDIDATE_MULTIPLIER,
)
from src.vector_search import SearchResult, VectorSearch

logger = logging.getLogger(__name__)


def _normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    """Min-max normalize scores to [0, 1]."""
    if not scores:
        return {}
    values = list(scores.values())
    min_s, max_s = min(values), max(values)
    if max_s == min_s:
        return {k: 1.0 for k in scores}
    return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}


class HybridSearch:
    """
    Blend semantic (FAISS) and keyword (BM25) retrieval.

    Default weighting: 0.7 semantic + 0.3 BM25.
    """

    def __init__(
        self,
        vector_search: Optional[VectorSearch] = None,
        keyword_search: Optional[KeywordSearch] = None,
        semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
        bm25_weight: float = DEFAULT_BM25_WEIGHT,
    ):
        self.vector_search = vector_search or VectorSearch()
        self.keyword_search = keyword_search or KeywordSearch()
        self.semantic_weight = semantic_weight
        self.bm25_weight = bm25_weight

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        candidate_pool: Optional[int] = None,
    ) -> list[SearchResult]:
        """Re-rank by weighted combination of normalized semantic and BM25 scores."""
        filters = dict(
            category=category,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
        )
        pool = candidate_pool or max(top_k * HYBRID_CANDIDATE_MULTIPLIER, 20)

        # Encode query once and share across semantic retrieval
        query_vec = self.vector_search.embedding_generator.encode_query(query)
        semantic_results = self.vector_search.search_with_vector(
            query_vec, top_k=pool, **filters
        )
        keyword_results = self.keyword_search.search(query, top_k=pool, **filters)

        sem_scores = {r.product_id: r.score for r in semantic_results}
        kw_scores = {r.product_id: r.score for r in keyword_results}

        sem_norm = _normalize_scores(sem_scores)
        kw_norm = _normalize_scores(kw_scores)

        all_ids = set(sem_norm) | set(kw_norm)
        score_map: dict[int, float] = {}
        for pid in all_ids:
            score_map[pid] = (
                self.semantic_weight * sem_norm.get(pid, 0.0)
                + self.bm25_weight * kw_norm.get(pid, 0.0)
            )

        ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:top_k]

        meta: dict[int, SearchResult] = {}
        for r in semantic_results + keyword_results:
            meta[r.product_id] = r

        return [
            SearchResult(
                product_id=pid,
                score=score,
                title=meta[pid].title,
                description=meta[pid].description,
                category=meta[pid].category,
                price=meta[pid].price,
                rating=meta[pid].rating,
            )
            for pid, score in ranked
            if pid in meta
        ]
