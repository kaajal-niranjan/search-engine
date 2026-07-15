"""Generate a product catalog via free local Ollama (build-time only).

Does not change runtime search: FAISS / BM25 / hybrid / UI still read CSV + embeddings.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.config import (
    LLM_CATALOG_BATCH_SIZE,
    LLM_CATALOG_DEFAULT_COUNT,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
    RAW_CATALOG_PATH,
)
from src.preprocessing import CATEGORIES, DataPreprocessor, _clean_text

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = list(CATEGORIES.keys())

_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


class OllamaError(RuntimeError):
    """Raised when Ollama is unavailable or returns unusable output."""


def check_ollama_available(
    *,
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = 5.0,
) -> None:
    """Ensure the Ollama HTTP API is reachable."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                raise OllamaError(
                    f"Ollama responded with HTTP {resp.status} at {url}. "
                    "Install from https://ollama.com and start the app."
                )
    except urllib.error.URLError as exc:
        raise OllamaError(
            "Cannot reach Ollama at "
            f"{base_url}. Install from https://ollama.com, start Ollama, "
            f"then run: ollama pull {OLLAMA_MODEL}"
        ) from exc


def _chat(
    messages: list[dict[str, str]],
    *,
    base_url: str,
    model: str,
    timeout: float,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.8},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OllamaError(
            f"Ollama chat failed (HTTP {exc.code}): {detail}. "
            f"Ensure the model is installed: ollama pull {model}"
        ) from exc
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"Ollama request failed: {exc}. Is Ollama running at {base_url}?"
        ) from exc

    message = body.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OllamaError("Ollama returned an empty message.")
    return content


def _extract_products_json(text: str) -> list[dict[str, Any]]:
    """Parse a JSON object/array of products from model output."""
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_ARRAY_RE.search(text)
        if not match:
            raise OllamaError("Model output was not valid JSON with a product list.")
        parsed = json.loads(match.group(0))

    if isinstance(parsed, dict):
        for key in ("products", "items", "data", "catalog"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
        else:
            # Single product object
            if any(k in parsed for k in ("title", "name", "description")):
                parsed = [parsed]
            else:
                raise OllamaError("JSON did not contain a products list.")

    if not isinstance(parsed, list):
        raise OllamaError("Expected a JSON list of products.")
    return [p for p in parsed if isinstance(p, dict)]


def _normalize_category(raw: str) -> Optional[str]:
    text = _clean_text(str(raw or ""))
    if not text:
        return None
    for cat in ALLOWED_CATEGORIES:
        if text.lower() == cat.lower():
            return cat
    # Fuzzy: substring match
    low = text.lower()
    for cat in ALLOWED_CATEGORIES:
        if cat.lower() in low or low in cat.lower():
            return cat
    return None


def _validate_product(raw: dict[str, Any], product_id: int) -> Optional[dict[str, Any]]:
    title = _clean_text(str(raw.get("title") or raw.get("name") or ""))
    description = _clean_text(str(raw.get("description") or raw.get("desc") or ""))
    category = _normalize_category(str(raw.get("category") or ""))
    if not title or not description or not category:
        return None

    try:
        price = float(raw.get("price"))
    except (TypeError, ValueError):
        return None
    try:
        rating = float(raw.get("rating"))
    except (TypeError, ValueError):
        rating = 4.0

    price = max(1.0, min(price, 5000.0))
    rating = max(1.0, min(round(rating, 1), 5.0))

    return {
        "id": product_id,
        "title": title[:180],
        "description": description[:600],
        "category": category,
        "price": round(price, 2),
        "rating": rating,
    }


def _batch_prompt(batch_size: int, categories: list[str], start_id: int) -> str:
    cat_list = ", ".join(categories)
    return (
        f"Generate exactly {batch_size} unique e-commerce products as JSON.\n"
        "Return ONLY valid JSON in this shape:\n"
        '{"products":[{"title":"...","description":"...","category":"...","price":12.99,"rating":4.2}]}\n'
        f"Rules:\n"
        f"- category MUST be one of: {cat_list}\n"
        "- title: short product name (no SKUs)\n"
        "- description: 1–2 realistic sentences\n"
        "- price: number between 5 and 900\n"
        "- rating: number between 2.5 and 5.0\n"
        f"- Start inventing from product idea #{start_id}; make titles diverse\n"
        "- Do not include markdown or commentary"
    )


def generate_products_via_ollama(
    n_products: int = LLM_CATALOG_DEFAULT_COUNT,
    *,
    batch_size: int = LLM_CATALOG_BATCH_SIZE,
    base_url: str = OLLAMA_BASE_URL,
    model: str = OLLAMA_MODEL,
    timeout: float = OLLAMA_TIMEOUT_SECONDS,
) -> pd.DataFrame:
    """Call Ollama in batches until enough validated products are collected."""
    if n_products < 1:
        raise ValueError("n_products must be >= 1")
    batch_size = max(1, min(batch_size, 25))

    check_ollama_available(base_url=base_url)

    rows: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    next_id = 1
    attempts = 0
    max_attempts = max(8, (n_products // batch_size) * 4)

    system = (
        "You are a data generator for an e-commerce product catalog. "
        "Always respond with JSON only."
    )

    while len(rows) < n_products and attempts < max_attempts:
        attempts += 1
        need = min(batch_size, n_products - len(rows))
        user = _batch_prompt(need, ALLOWED_CATEGORIES, next_id)
        logger.info(
            "Ollama catalog batch %d (have %d / %d)…",
            attempts,
            len(rows),
            n_products,
        )
        try:
            content = _chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                base_url=base_url,
                model=model,
                timeout=timeout,
            )
            raw_items = _extract_products_json(content)
        except OllamaError as exc:
            logger.warning("Batch failed: %s", exc)
            continue

        for item in raw_items:
            validated = _validate_product(item, next_id)
            if not validated:
                continue
            key = validated["title"].lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            rows.append(validated)
            next_id += 1
            if len(rows) >= n_products:
                break

    if len(rows) < max(1, n_products // 2):
        raise OllamaError(
            f"Only collected {len(rows)}/{n_products} products from Ollama. "
            f"Check model `{model}` with: ollama pull {model}"
        )

    if len(rows) < n_products:
        logger.warning(
            "Collected %d products (requested %d); continuing with what we have.",
            len(rows),
            n_products,
        )

    df = pd.DataFrame(rows[:n_products])
    logger.info("LLM catalog ready: %d products", len(df))
    return df


def write_llm_catalog(
    df: pd.DataFrame,
    *,
    raw_path: Path = RAW_CATALOG_PATH,
) -> Path:
    """Write raw catalog CSV (overwrite)."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_path, index=False)
    logger.info("Wrote LLM raw catalog → %s", raw_path)
    return raw_path


def generate_and_save_catalog(
    n_products: int = LLM_CATALOG_DEFAULT_COUNT,
    *,
    clean: bool = True,
    base_url: str = OLLAMA_BASE_URL,
    model: str = OLLAMA_MODEL,
) -> pd.DataFrame:
    """Generate via Ollama, save raw CSV, optionally clean → products_clean.csv."""
    df = generate_products_via_ollama(
        n_products=n_products,
        base_url=base_url,
        model=model,
    )
    write_llm_catalog(df)
    if clean:
        preprocessor = DataPreprocessor()
        return preprocessor.clean(df)
    return df
