"""Per-user search history and query suggestions (local JSON store)."""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import (
    CLEAN_CATALOG_PATH,
    SEARCH_HISTORY_MAX_PER_USER,
    SEARCH_HISTORY_PATH,
    SEARCH_SUGGESTION_LIMIT,
)

_lock = threading.Lock()

# Lightweight starter prompts shown when the user has little/no history yet
_DEFAULT_SUGGESTIONS = [
    "warm jacket for winter trip",
    "cozy bedding for better sleep",
    "wireless headphones",
    "running shoes",
    "kitchen coffee maker",
    "skincare moisturizer",
]


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip())


def _read_store(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_store(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def add_search_history(
    email: str,
    query: str,
    *,
    path: Path = SEARCH_HISTORY_PATH,
    max_items: int = SEARCH_HISTORY_MAX_PER_USER,
) -> None:
    """Prepend a successful search query to the user's recent history."""
    user = _normalize_email(email)
    q = _normalize_query(query)
    if not user or not q:
        return

    entry = {"query": q, "timestamp": time.time()}
    with _lock:
        data = _read_store(path)
        items = data.get(user, [])
        if not isinstance(items, list):
            items = []
        # Dedupe (case-insensitive): keep newest at front
        items = [
            it
            for it in items
            if isinstance(it, dict)
            and _normalize_query(str(it.get("query", ""))).lower() != q.lower()
        ]
        items.insert(0, entry)
        data[user] = items[:max_items]
        _write_store(data, path)


def get_search_history(
    email: str,
    *,
    limit: int = SEARCH_HISTORY_MAX_PER_USER,
    path: Path = SEARCH_HISTORY_PATH,
) -> list[str]:
    """Return recent queries for a user (newest first)."""
    user = _normalize_email(email)
    if not user:
        return []
    with _lock:
        data = _read_store(path)
        items = data.get(user, [])
    if not isinstance(items, list):
        return []
    queries: list[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        q = _normalize_query(str(it.get("query", "")))
        if q:
            queries.append(q)
        if len(queries) >= limit:
            break
    return queries


def clear_search_history(
    email: str,
    *,
    path: Path = SEARCH_HISTORY_PATH,
) -> None:
    """Remove all stored history for one user."""
    user = _normalize_email(email)
    if not user:
        return
    with _lock:
        data = _read_store(path)
        if user in data:
            data.pop(user, None)
            _write_store(data, path)


def _title_suggestions_from_list(
    titles: list[str],
    prefix: str,
    *,
    limit: int = SEARCH_SUGGESTION_LIMIT,
) -> list[str]:
    needle = prefix.lower().strip()
    clean = [_normalize_query(t) for t in titles if t]
    if not needle:
        return clean[:limit]

    starts = [t for t in clean if t.lower().startswith(needle)]
    contains = [
        t for t in clean if needle in t.lower() and not t.lower().startswith(needle)
    ]
    ordered = starts + contains
    seen: set[str] = set()
    out: list[str] = []
    for t in ordered:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def _catalog_title_suggestions(
    prefix: str,
    *,
    catalog_path: Path = CLEAN_CATALOG_PATH,
    catalog_titles: Optional[list[str]] = None,
    limit: int = SEARCH_SUGGESTION_LIMIT,
) -> list[str]:
    """Suggest product titles that match the typed prefix/substring."""
    if catalog_titles is not None:
        return _title_suggestions_from_list(catalog_titles, prefix, limit=limit)

    if not catalog_path.exists():
        return []
    try:
        df = pd.read_csv(catalog_path, usecols=["title"])
    except Exception:
        return []
    titles = df["title"].dropna().astype(str).tolist()
    return _title_suggestions_from_list(titles, prefix, limit=limit)


def get_suggestion_dropdown_options(
    email: str,
    typed: str = "",
    *,
    catalog_titles: Optional[list[str]] = None,
    history_path: Path = SEARCH_HISTORY_PATH,
    limit: int = SEARCH_SUGGESTION_LIMIT,
) -> list[str]:
    """
    Suggestion options for the search UI (no free-form "Add" entries).

    - Empty input  → recent search history only
    - While typing → all matching product titles (plus matching history)
    """
    typed_norm = _normalize_query(typed)
    if not typed_norm:
        return get_search_history(email, limit=limit, path=history_path)

    seen: set[str] = set()
    options: list[str] = []

    def _add(items: list[str]) -> None:
        for item in items:
            q = _normalize_query(item)
            if not q:
                continue
            key = q.lower()
            if key == typed_norm.lower():
                continue
            if key in seen:
                continue
            seen.add(key)
            options.append(q)
            if len(options) >= limit:
                return

    # Matching past searches first, then every matching product title
    history = get_search_history(email, path=history_path)
    _add([h for h in history if typed_norm.lower() in h.lower()])
    if len(options) >= limit:
        return options

    _add(
        _title_suggestions_from_list(
            catalog_titles or [],
            typed_norm,
            limit=limit,
        )
    )
    return options


def get_search_suggestions(
    email: str,
    typed: str = "",
    *,
    limit: int = SEARCH_SUGGESTION_LIMIT,
    history_path: Path = SEARCH_HISTORY_PATH,
    catalog_path: Path = CLEAN_CATALOG_PATH,
    catalog_titles: Optional[list[str]] = None,
) -> list[str]:
    """
    Build suggestion list from:
    1) matching personal history
    2) matching catalog titles
    3) default starter queries (when still short on matches)
    """
    typed_norm = _normalize_query(typed)
    typed_l = typed_norm.lower()
    suggestions: list[str] = []
    seen: set[str] = set()

    def _add(items: list[str]) -> None:
        for item in items:
            q = _normalize_query(item)
            if not q:
                continue
            key = q.lower()
            if typed_l and key == typed_l:
                continue
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(q)
            if len(suggestions) >= limit:
                return

    history = get_search_history(email, path=history_path)
    if typed_l:
        hist_matches = [h for h in history if typed_l in h.lower()]
    else:
        hist_matches = history
    _add(hist_matches)
    if len(suggestions) >= limit:
        return suggestions

    _add(
        _catalog_title_suggestions(
            typed_norm,
            catalog_path=catalog_path,
            catalog_titles=catalog_titles,
            limit=limit,
        )
    )
    if len(suggestions) >= limit:
        return suggestions

    if typed_l:
        defaults = [d for d in _DEFAULT_SUGGESTIONS if typed_l in d.lower()]
    else:
        defaults = list(_DEFAULT_SUGGESTIONS)
    _add(defaults)
    return suggestions
