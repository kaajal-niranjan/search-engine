"""Batch embedding generation with local caching."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.config import (
    CLEAN_CATALOG_PATH,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
    EMBEDDINGS_DIR,
    EMBEDDINGS_PATH,
    PRODUCT_IDS_PATH,
    QUERY_EMBEDDING_CACHE_SIZE,
)

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate and cache sentence embeddings for product catalog."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        embeddings_path: Path = EMBEDDINGS_PATH,
        product_ids_path: Path = PRODUCT_IDS_PATH,
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.embeddings_path = embeddings_path
        self.product_ids_path = product_ids_path
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def warmup(self) -> None:
        """Load model and run a dummy encode so first real query is fast."""
        _ = self.model
        self.encode_query("__warmup__")

    def embeddings_exist(self) -> bool:
        """Check if cached embeddings are available."""
        return self.embeddings_path.exists() and self.product_ids_path.exists()

    def load_embeddings(self) -> tuple[np.ndarray, np.ndarray]:
        """Load cached embeddings and product IDs."""
        if not self.embeddings_exist():
            raise FileNotFoundError(
                f"Embeddings not found at {self.embeddings_path}. Run generate() first."
            )
        embeddings = np.load(self.embeddings_path, mmap_mode="r")
        product_ids = np.load(self.product_ids_path)
        logger.info("Loaded embeddings: shape=%s", embeddings.shape)
        return embeddings, product_ids

    def generate(
        self,
        df: Optional[pd.DataFrame] = None,
        catalog_path: Path = CLEAN_CATALOG_PATH,
        force: bool = False,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate embeddings for all products in batches and cache to disk.

        Returns:
            Tuple of (embeddings matrix, product id array).
        """
        if not force and self.embeddings_exist():
            logger.info("Using cached embeddings from %s", self.embeddings_path)
            return self.load_embeddings()

        if df is None:
            if not catalog_path.exists():
                raise FileNotFoundError(f"Catalog not found: {catalog_path}")
            df = pd.read_csv(catalog_path)

        texts = df["search_text"].astype(str).tolist()
        product_ids = df["id"].values

        logger.info("Encoding %d products in batches of %d...", len(texts), self.batch_size)
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
        np.save(self.embeddings_path, embeddings)
        np.save(self.product_ids_path, product_ids)
        logger.info("Saved embeddings to %s", self.embeddings_path)
        return embeddings, product_ids

    @lru_cache(maxsize=QUERY_EMBEDDING_CACHE_SIZE)
    def _encode_query_cached(self, query: str) -> tuple[float, ...]:
        """Internal cached encode; returns hashable tuple for lru_cache."""
        vector = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return tuple(vector.tolist())

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single search query into a normalized embedding vector (cached)."""
        if query == "__warmup__":
            vector = self.model.encode(
                "product search",
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vector

        return np.asarray(self._encode_query_cached(query), dtype=np.float32)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    from src.preprocessing import run_preprocessing

    run_preprocessing()
    generator = EmbeddingGenerator()
    generator.generate()
