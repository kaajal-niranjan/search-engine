"""Explainable search: breakdown of why each product ranked where it did."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScoreBreakdown:
    """Per-product score contribution from each retrieval signal."""

    product_id: int
    final_score: float
    semantic_score: Optional[float] = None
    semantic_rank: Optional[int] = None
    bm25_score: Optional[float] = None
    bm25_rank: Optional[int] = None
    semantic_contribution: float = 0.0
    bm25_contribution: float = 0.0
    fusion_method: str = "weighted"
    matched_signals: list[str] = field(default_factory=list)

    def primary_signal(self) -> str:
        if self.semantic_contribution > self.bm25_contribution + 0.05:
            return "semantic"
        if self.bm25_contribution > self.semantic_contribution + 0.05:
            return "keyword"
        return "balanced"

    def summary(self) -> str:
        parts = []
        if self.semantic_rank is not None:
            parts.append(f"semantic rank #{self.semantic_rank}")
        if self.bm25_rank is not None:
            parts.append(f"BM25 rank #{self.bm25_rank}")
        signal = self.primary_signal()
        if signal == "semantic":
            parts.append("matched by meaning/intent")
        elif signal == "keyword":
            parts.append("matched by exact keywords")
        else:
            parts.append("balanced semantic + keyword match")
        return " · ".join(parts)
