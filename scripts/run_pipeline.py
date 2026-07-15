"""Run full data + embedding + clustering + evaluation pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build catalog artifacts for the search engine.")
    parser.add_argument(
        "--llm-catalog",
        action="store_true",
        help=(
            "Generate products via free local Ollama before embedding. "
            "Default (no flag) uses the existing synthetic catalog path."
        ),
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Product count (synthetic default 800; LLM default from config if --llm-catalog)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model when using --llm-catalog (default from config)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.llm_catalog:
        from src.config import LLM_CATALOG_DEFAULT_COUNT, OLLAMA_MODEL
        from src.llm_catalog import OllamaError, generate_and_save_catalog
        from src.preprocessing import DataPreprocessor

        n = args.count if args.count is not None else LLM_CATALOG_DEFAULT_COUNT
        model = args.model or OLLAMA_MODEL
        logger.info("Step 1: LLM catalog via Ollama (%d products, model=%s)", n, model)
        try:
            generate_and_save_catalog(n_products=n, clean=True, model=model)
        except OllamaError as exc:
            logger.error("%s", exc)
            sys.exit(1)
        DataPreprocessor().run_eda()
    else:
        from src.preprocessing import run_preprocessing

        n = args.count if args.count is not None else 800
        logger.info("Step 1: Data preparation & EDA (synthetic catalog, n=%d)", n)
        run_preprocessing(n_products=n)

    from src.clustering import ProductClusterer
    from src.embedding_generator import EmbeddingGenerator
    from src.evaluation import SearchEvaluator
    from src.vector_search import VectorSearch

    logger.info("Step 2: Embedding generation")
    generator = EmbeddingGenerator()
    generator.generate()

    logger.info("Step 3: FAISS index build")
    vector_search = VectorSearch(embedding_generator=generator)
    vector_search.build_index()

    logger.info("Step 4: Clustering & visualization")
    clusterer = ProductClusterer(embedding_generator=generator)
    clusterer.fit_predict()
    clusterer.visualize()

    logger.info("Step 5: Evaluation")
    evaluator = SearchEvaluator(vector_search=vector_search)
    _, report = evaluator.run_and_report()
    print(report)
    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()
