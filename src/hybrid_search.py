"""Hybrid search combining semantic and BM25 scores with filters."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.bm25_search import KeywordSearch
from src.config import (
    DEFAULT_BM25_WEIGHT,
    DEFAULT_SEMANTIC_WEIGHT,
    DEFAULT_TOP_K,
    HYBRID_CANDIDATE_MULTIPLIER,
)
from src.query_intent import QueryIntent, detect_query_intent, recommend_search_mode
from src.search_explanation import ScoreBreakdown
from src.vector_search import SearchResult, VectorSearch

logger = logging.getLogger(__name__)


@dataclass
class ExplainableSearchResponse:
    """Search results with intent analysis and per-result score breakdown."""

    results: list[SearchResult]
    intent: QueryIntent
    breakdowns: dict[int, ScoreBreakdown]
    recommended_mode: str
    applied_category_boost: bool = False


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

    def search_with_explanation(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        auto_category_boost: bool = True,
        category_boost_weight: float = 0.08,
    ) -> ExplainableSearchResponse:
        """
        Hybrid search with query intent detection and per-result score breakdown.

        When auto_category_boost is enabled and the user has not set a category filter,
        products in the detected category receive a small score boost.
        """
        intent = detect_query_intent(query)
        applied_boost = False

        if auto_category_boost and category is None and intent.has_category_hint:
            applied_boost = True

        filters = dict(
            category=category,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
        )
        pool = max(top_k * HYBRID_CANDIDATE_MULTIPLIER, 20)

        query_vec = self.vector_search.embedding_generator.encode_query(query)
        semantic_results = self.vector_search.search_with_vector(
            query_vec, top_k=pool, **filters
        )
        keyword_results = self.keyword_search.search(query, top_k=pool, **filters)

        sem_scores = {r.product_id: r.score for r in semantic_results}
        kw_scores = {r.product_id: r.score for r in keyword_results}
        sem_ranks = {r.product_id: i + 1 for i, r in enumerate(semantic_results)}
        kw_ranks = {r.product_id: i + 1 for i, r in enumerate(keyword_results)}

        sem_norm = _normalize_scores(sem_scores)
        kw_norm = _normalize_scores(kw_scores)

        all_ids = set(sem_norm) | set(kw_norm)
        score_map: dict[int, float] = {}
        breakdowns: dict[int, ScoreBreakdown] = {}

        for pid in all_ids:
            sem_c = self.semantic_weight * sem_norm.get(pid, 0.0)
            kw_c = self.bm25_weight * kw_norm.get(pid, 0.0)
            combined = sem_c + kw_c

            meta_row = next(
                (r for r in semantic_results + keyword_results if r.product_id == pid),
                None,
            )

            if applied_boost and intent.suggested_category and meta_row:
                if meta_row.category == intent.suggested_category:
                    combined += category_boost_weight * intent.confidence

            score_map[pid] = combined
            matched: list[str] = []
            if meta_row:
                title_lower = meta_row.title.lower()
                matched = [s for s in intent.matched_signals if s in title_lower]

            breakdowns[pid] = ScoreBreakdown(
                product_id=pid,
                final_score=combined,
                semantic_score=sem_scores.get(pid),
                semantic_rank=sem_ranks.get(pid),
                bm25_score=kw_scores.get(pid),
                bm25_rank=kw_ranks.get(pid),
                semantic_contribution=sem_c,
                bm25_contribution=kw_c,
                fusion_method="weighted",
                matched_signals=matched,
            )

        ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:top_k]

        meta: dict[int, SearchResult] = {}
        for r in semantic_results + keyword_results:
            meta[r.product_id] = r

        results = [
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

        for r in results:
            if r.product_id in breakdowns:
                breakdowns[r.product_id].final_score = r.score

        return ExplainableSearchResponse(
            results=results,
            intent=intent,
            breakdowns={r.product_id: breakdowns[r.product_id] for r in results},
            recommended_mode=recommend_search_mode(intent),
            applied_category_boost=applied_boost,
        )
