"""Inline search autocomplete under the input (Streamlit custom component)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend_search_ac"

_search_ac = components.declare_component(
    "sps_search_autocomplete",
    path=str(_FRONTEND_DIR),
)


def render_search_autocomplete(
    *,
    history: Sequence[str],
    product_titles: Sequence[str],
    current_query: str = "",
    placeholder: str = "Search products…",
    max_products: int = 400,
    max_suggestions: int = 25,
    key: str = "sps_search_autocomplete",
) -> Optional[dict[str, Any]]:
    """
    Render one search box with suggestions attached beneath it.

    Returns a dict ``{"action": "search", "query": "...", "nonce": ...}``
    when the user clicks Search, presses Enter, or picks a suggestion.
    Otherwise returns None.
    """
    safe_history = [str(x) for x in history if str(x).strip()]
    safe_titles = [str(x) for x in product_titles if str(x).strip()][:max_products]

    result = _search_ac(
        history=safe_history,
        product_titles=safe_titles,
        current_query=current_query or "",
        placeholder=placeholder,
        max_suggestions=int(max_suggestions),
        key=key,
        default=None,
    )
    if isinstance(result, dict) and result.get("action") == "search":
        return result
    return None


def consume_autocomplete_query() -> Optional[tuple[str, bool]]:
    """Deprecated URL bridge — kept for import compatibility; always None."""
    return None
