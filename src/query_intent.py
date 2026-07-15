"""Query intent detection: infer category and search signals from natural language."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Keyword hints mapped to catalog categories (see preprocessing.py)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Electronics": [
        "laptop", "charger", "usb", "headphones", "earbuds", "tv", "television",
        "4k", "hdmi", "wireless", "bluetooth", "smartphone", "tablet", "camera",
        "monitor", "keyboard", "mouse", "speaker", "noise cancelling",
    ],
    "Clothing": [
        "jacket", "coat", "sweater", "shirt", "pants", "dress", "shoes",
        "boots", "winter", "thermal", "fleece", "rain", "waterproof", "commute",
        "socks", "hat", "gloves",
    ],
    "Home & Kitchen": [
        "pan", "cookware", "nonstick", "kitchen", "bedding", "blanket", "pillow",
        "sleep", "cozy", "diffuser", "candle", "organizer", "desk", "chair",
    ],
    "Sports & Outdoors": [
        "camping", "tent", "hiking", "backpack", "workout", "gym", "yoga",
        "dumbbell", "resistance", "fitness", "outdoor", "running", "cycling",
    ],
    "Beauty & Personal Care": [
        "skincare", "retinol", "serum", "moisturizer", "anti aging", "night cream",
        "shampoo", "lotion", "makeup", "beauty",
    ],
    "Books & Stationery": [
        "book", "python", "programming", "journal", "planner", "notebook",
        "stationery", "coding", "learn",
    ],
    "Toys & Games": [
        "toddler", "toy", "birthday", "party", "plush", "blocks", "board game",
        "children", "kids", "puzzle",
    ],
    "Health & Wellness": [
        "protein", "supplement", "vitamin", "wellness", "health", "tea",
        "recovery", "foam roller", "nutrition",
    ],
}


@dataclass
class QueryIntent:
    """Detected intent from a user search query."""

    query: str
    suggested_category: Optional[str]
    confidence: float
    matched_signals: list[str]
    query_type: str  # "intent", "keyword", or "mixed"

    @property
    def has_category_hint(self) -> bool:
        return self.suggested_category is not None and self.confidence >= 0.25


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b\w+\b", text.lower()))


def detect_query_intent(query: str) -> QueryIntent:
    """
    Infer likely product category and query style from natural language.

    Example:
        >>> intent = detect_query_intent("warm jacket for winter trip")
        >>> intent.suggested_category
        'Clothing'
        >>> intent.query_type
        'intent'
    """
    tokens = _tokenize(query)
    if not tokens:
        return QueryIntent(query=query, suggested_category=None, confidence=0.0,
                           matched_signals=[], query_type="intent")

    category_scores: dict[str, list[str]] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in tokens or any(kw in t for t in tokens)]
        if hits:
            category_scores[category] = hits

    suggested: Optional[str] = None
    confidence = 0.0
    signals: list[str] = []

    if category_scores:
        best_cat, best_hits = max(category_scores.items(), key=lambda x: len(x[1]))
        suggested = best_cat
        signals = best_hits
        confidence = min(1.0, len(best_hits) / 3.0)

    # Classify query style: short exact tokens vs descriptive intent
    has_rare_tokens = bool(re.search(r"\d|usb|4k|65w|sku", query.lower()))
    is_short = len(tokens) <= 3
    if has_rare_tokens or is_short:
        query_type = "keyword"
    elif len(tokens) >= 5:
        query_type = "intent"
    else:
        query_type = "mixed"

    return QueryIntent(
        query=query,
        suggested_category=suggested,
        confidence=confidence,
        matched_signals=signals,
        query_type=query_type,
    )


def recommend_search_mode(intent: QueryIntent) -> str:
    """Suggest Hybrid, Semantic, or BM25 based on detected intent."""
    if intent.query_type == "keyword":
        return "BM25"
    if intent.query_type == "intent":
        return "Semantic"
    return "Hybrid"
