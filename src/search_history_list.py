"""Compact scrollable search-history list (Streamlit custom component)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend_search_history"

_history_list = components.declare_component(
    "sps_search_history_list",
    path=str(_FRONTEND_DIR),
)


def render_search_history_list(
    items: Sequence[str],
    *,
    key: str = "sps_search_history_list",
) -> Optional[dict[str, Any]]:
    """
    Render a single-line, ellipsis-truncated history list.

    Returns ``{"action": "select", "query": "...", "nonce": ...}`` when an
    item is clicked; otherwise None.
    """
    safe = [str(x).strip() for x in items if str(x).strip()]
    result = _history_list(items=safe, key=key, default=None)
    if isinstance(result, dict) and result.get("action") == "select":
        return result
    return None
