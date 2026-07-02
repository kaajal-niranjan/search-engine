# Semantic Product Search & Recommendation Engine

An e-commerce search system that understands **meaning**, not just keywords. Built with Sentence Transformers, FAISS, BM25, and hybrid re-ranking.

## Features

- **Semantic search** — natural-language queries like *"warm jacket for winter trip"*
- **BM25 keyword baseline** — strong on exact product names and SKUs
- **Hybrid ranking** — configurable blend (default 70% semantic / 30% BM25)
- **Structured filters** — category, price range, minimum rating
- **Recommendations** — content-based similarity + simulated co-occurrence
- **Clustering** — KMeans on embeddings with UMAP visualization
- **Evaluation** — Precision@5 and Precision@10 on 15 realistic queries
- **Streamlit UI** — search, filters, recommendations, cluster & eval pages

## Project Structure

```
semantic-product-search/
├── data/                  # Product catalog (raw + cleaned CSV)
├── embeddings/            # Cached embeddings, FAISS index, cluster labels
├── notebooks/             # Optional EDA notebook
├── reports/               # EDA and evaluation reports
├── scripts/
│   └── run_pipeline.py    # End-to-end build script
├── src/
│   ├── config.py
│   ├── preprocessing.py
│   ├── embedding_generator.py
│   ├── vector_search.py
│   ├── bm25_search.py
│   ├── hybrid_search.py
│   ├── recommender.py
│   ├── clustering.py
│   └── evaluation.py
├── visuals/               # Cluster UMAP plot
├── app.py                 # Streamlit application
├── requirements.txt
└── README.md
```

## Setup

```bash
cd semantic-product-search
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Quick Start

### 1. Build data, embeddings, index, clusters, and evaluation

```bash
python scripts/run_pipeline.py
```

This will:
- Generate an 800-product synthetic catalog
- Clean data and write EDA report to `reports/eda_report.txt`
- Batch-encode embeddings with `all-MiniLM-L6-v2` (cached in `embeddings/`)
- Build FAISS index
- Run KMeans + UMAP cluster plot → `visuals/cluster_visualization.png`
- Evaluate BM25 vs semantic vs hybrid → `reports/evaluation_results.csv`

### 2. Launch Streamlit UI

```bash
streamlit run app.py
```

## Search Modes

| Mode | Best for | Example query |
|------|----------|---------------|
| **Semantic** | Vague intent, synonyms | "something cozy for better sleep" |
| **BM25** | Exact tokens, SKUs | "USB-C 65W laptop charger" |
| **Hybrid** | General production use | "noise cancelling headphones for travel" |

### Hybrid weighting rationale

- **0.7 semantic** — primary signal for user intent and paraphrases
- **0.3 BM25** — rescues exact matches (brand, model, rare tokens) that dense retrieval can dilute

Weights are configurable in code (`HybridSearch`) and in the Streamlit sidebar.

## Evaluation

See `reports/evaluation_report.txt` and `reports/evaluation_results.csv` after running the pipeline.

**Semantic search wins** when users describe needs in natural language without product vocabulary.

**BM25 wins** on precise keyword/SKU-style queries.

**Hybrid** typically offers the best trade-off on mixed queries.

## API Usage (Python)

```python
from src.vector_search import VectorSearch
from src.hybrid_search import HybridSearch
from src.recommender import ProductRecommender

hybrid = HybridSearch()
results = hybrid.search(
    "warm jacket for winter trip",
    top_k=5,
    category="Clothing",
    max_price=200,
    min_rating=4.0,
)

recommender = ProductRecommender()
similar = recommender.similar_products(product_id=42, top_n=5)
```

## Tech Stack

- [Sentence Transformers](https://www.sbert.net/) — `all-MiniLM-L6-v2` (384-dim)
- [FAISS](https://github.com/facebookresearch/faiss) — inner-product index on normalized vectors (= cosine similarity)
- [rank-bm25](https://github.com/dorianbrown/rank_bm25) — Okapi BM25
- [UMAP](https://umap-learn.readthedocs.io/) + [KMeans](https://scikit-learn.org/) — clustering & visualization
- [Streamlit](https://streamlit.io/) — demo UI

## Performance

The app is optimized for fast interaction after the first load:

- **Model warmup** on startup (first load ~3–5s is normal — loading the embedding model)
- **Query embedding cache** — repeated searches are near-instant
- **Search on button click** — moving filters no longer re-runs search on every slider change
- **Lazy page loading** — Clusters/Evaluation pages skip loading the ML model
- **Faster BM25** — numpy top-k instead of sorting all products
- **Hybrid** — encodes each query only once (not twice)

Restart Streamlit after pulling updates:

```powershell
streamlit run app.py
```


MIT — for educational and portfolio use.
