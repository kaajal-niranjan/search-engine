"""Run full data + embedding + clustering + evaluation pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clustering import ProductClusterer
from src.embedding_generator import EmbeddingGenerator
from src.evaluation import SearchEvaluator
from src.preprocessing import run_preprocessing
from src.vector_search import VectorSearch

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Step 1: Data preparation & EDA")
    run_preprocessing(n_products=800)

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
    df, report = evaluator.run_and_report()
    print(report)
    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()
