"""Central configuration for the semantic product search engine."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
VISUALS_DIR = PROJECT_ROOT / "visuals"
REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_CATALOG_PATH = DATA_DIR / "products_raw.csv"
CLEAN_CATALOG_PATH = DATA_DIR / "products_clean.csv"
EMBEDDINGS_PATH = EMBEDDINGS_PATH_NPY = EMBEDDINGS_DIR / "product_embeddings.npy"
PRODUCT_IDS_PATH = EMBEDDINGS_DIR / "product_ids.npy"
FAISS_INDEX_PATH = EMBEDDINGS_DIR / "faiss_index.bin"
CLUSTER_LABELS_PATH = EMBEDDINGS_DIR / "cluster_labels.npy"
EDA_REPORT_PATH = REPORTS_DIR / "eda_report.txt"
EVALUATION_REPORT_PATH = REPORTS_DIR / "evaluation_report.txt"
EVALUATION_CSV_PATH = REPORTS_DIR / "evaluation_results.csv"
CLUSTER_PLOT_PATH = VISUALS_DIR / "cluster_visualization.png"

# Embedding model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_BATCH_SIZE = 64
EMBEDDING_DIMENSION = 384

# Hybrid search weights
DEFAULT_SEMANTIC_WEIGHT = 0.7
DEFAULT_BM25_WEIGHT = 0.3

# Clustering
DEFAULT_N_CLUSTERS = 12
UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST = 0.1
RANDOM_SEED = 42

# Search defaults
DEFAULT_TOP_K = 10
HYBRID_CANDIDATE_MULTIPLIER = 3
QUERY_EMBEDDING_CACHE_SIZE = 256

# Cached artifacts
COOCCURRENCE_PATH = EMBEDDINGS_DIR / "cooccurrence.parquet"
