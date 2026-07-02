"""K-means clustering and UMAP visualization of product embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from src.config import (
    CLEAN_CATALOG_PATH,
    CLUSTER_LABELS_PATH,
    CLUSTER_PLOT_PATH,
    DEFAULT_N_CLUSTERS,
    EMBEDDINGS_DIR,
    RANDOM_SEED,
    UMAP_MIN_DIST,
    UMAP_N_NEIGHBORS,
    VISUALS_DIR,
)
from src.embedding_generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


class ProductClusterer:
    """Cluster product embeddings and visualize with UMAP."""

    def __init__(
        self,
        n_clusters: int = DEFAULT_N_CLUSTERS,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        catalog_path: Path = CLEAN_CATALOG_PATH,
        seed: int = RANDOM_SEED,
    ):
        self.n_clusters = n_clusters
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.catalog_path = catalog_path
        self.seed = seed
        self._labels: Optional[np.ndarray] = None

    def fit_predict(self, force: bool = False) -> np.ndarray:
        """Run KMeans on embeddings and cache cluster labels."""
        if not force and CLUSTER_LABELS_PATH.exists():
            self._labels = np.load(CLUSTER_LABELS_PATH)
            logger.info("Loaded cluster labels from cache")
            return self._labels

        embeddings, _ = self.embedding_generator.load_embeddings()
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=self.seed, n_init=10)
        self._labels = kmeans.fit_predict(embeddings)

        EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
        np.save(CLUSTER_LABELS_PATH, self._labels)
        logger.info("KMeans clustering complete: %d clusters", self.n_clusters)
        return self._labels

    def visualize(self, output_path: Path = CLUSTER_PLOT_PATH) -> Path:
        """Reduce embeddings with UMAP and save cluster scatter plot."""
        import umap

        embeddings, _ = self.embedding_generator.load_embeddings()
        labels = self.fit_predict()

        reducer = umap.UMAP(
            n_neighbors=UMAP_N_NEIGHBORS,
            min_dist=UMAP_MIN_DIST,
            random_state=self.seed,
            metric="cosine",
        )
        coords = reducer.fit_transform(embeddings)

        df = pd.read_csv(self.catalog_path)

        VISUALS_DIR.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(12, 9))
        scatter = ax.scatter(
            coords[:, 0],
            coords[:, 1],
            c=labels,
            cmap="tab20",
            alpha=0.65,
            s=18,
            edgecolors="none",
        )
        ax.set_title("Product Embedding Clusters (UMAP + KMeans)", fontsize=14)
        ax.set_xlabel("UMAP-1")
        ax.set_ylabel("UMAP-2")
        plt.colorbar(scatter, ax=ax, label="Cluster")
        ax.grid(True, alpha=0.2)

        # Annotate cluster centroids with dominant category.
        for cluster_id in range(self.n_clusters):
            mask = labels == cluster_id
            if not mask.any():
                continue
            cx, cy = coords[mask, 0].mean(), coords[mask, 1].mean()
            top_cat = df.loc[mask, "category"].mode().iloc[0]
            short = top_cat.split()[0][:8]
            ax.annotate(short, (cx, cy), fontsize=7, ha="center", alpha=0.8)

        plt.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Cluster visualization saved to %s", output_path)
        return output_path
