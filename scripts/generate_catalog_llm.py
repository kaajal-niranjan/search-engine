"""Generate product catalog with free local Ollama, then optionally rebuild indexes.

Usage:
  python scripts/generate_catalog_llm.py --count 200
  python scripts/generate_catalog_llm.py --count 100 --rebuild
  python scripts/generate_catalog_llm.py --model mistral --count 150

Requires Ollama: https://ollama.com
  ollama pull llama3.2
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    LLM_CATALOG_DEFAULT_COUNT,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from src.llm_catalog import OllamaError, generate_and_save_catalog

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


def _run_rebuild() -> None:
    from src.clustering import ProductClusterer
    from src.embedding_generator import EmbeddingGenerator
    from src.evaluation import SearchEvaluator
    from src.vector_search import VectorSearch

    logger.info("Rebuilding embeddings, FAISS, clusters, evaluation…")
    generator = EmbeddingGenerator()
    generator.generate()
    vector_search = VectorSearch(embedding_generator=generator)
    vector_search.build_index()
    clusterer = ProductClusterer(embedding_generator=generator)
    clusterer.fit_predict()
    clusterer.visualize()
    evaluator = SearchEvaluator(vector_search=vector_search)
    _, report = evaluator.run_and_report()
    print(report)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate products_clean.csv via free local Ollama (search UI unchanged)."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=LLM_CATALOG_DEFAULT_COUNT,
        help=f"Number of products to generate (default {LLM_CATALOG_DEFAULT_COUNT})",
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help=f"Ollama model name (default {OLLAMA_MODEL})",
    )
    parser.add_argument(
        "--base-url",
        default=OLLAMA_BASE_URL,
        help=f"Ollama API base URL (default {OLLAMA_BASE_URL})",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="After writing the catalog, rebuild embeddings / FAISS / clusters / eval",
    )
    args = parser.parse_args()

    try:
        df = generate_and_save_catalog(
            n_products=args.count,
            clean=True,
            base_url=args.base_url,
            model=args.model,
        )
    except OllamaError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    logger.info("Catalog ready (%d products). UI/search code unchanged.", len(df))
    if args.rebuild:
        _run_rebuild()
        logger.info("Rebuild complete. Start the app with: streamlit run app.py")
    else:
        logger.info(
            "Next: python scripts/run_pipeline.py   "
            "(or re-run this script with --rebuild) then streamlit run app.py"
        )


if __name__ == "__main__":
    main()
