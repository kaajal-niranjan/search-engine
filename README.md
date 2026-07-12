# Semantic Product Search & Recommendation Engine

An e-commerce search system that understands **meaning**, not just keywords — with **secure login**, **toast notifications**, **query intent**, and **explainable hybrid ranking**.

Built with Sentence Transformers, FAISS, BM25, and Streamlit.

---

## What Makes This Different?

| Traditional demo | This engine |
|------------------|-------------|
| Open access to all pages | **Login-first**; other routes blocked until sign-in |
| Plain or visible passwords | **Salted PBKDF2 hashes**; password never shown in UI |
| Silent actions | **Top-right toast** feedback |
| Keyword-only | **70% semantic + 30% BM25** hybrid |
| Black-box scores | **Explainable** “Why this result?” breakdowns |

**Try after login:** *"warm jacket for winter trip"* — winter clothing even without that exact phrase in every title.

---

## Features

### Access & UX
- **Email/password login** (default route)
- **Route protection** — Search, Clusters, Evaluation only after login
- **Log out** in the header
- **Toast notifications** (top-right) for login, logout, search, and errors

### Search & ML
- **Semantic search** — natural-language intent
- **BM25 keyword baseline** — SKUs and exact tokens
- **Hybrid ranking** — configurable weights (default 70/30)
- **Query intent detection** — category + suggested mode
- **Explainable results** — semantic vs BM25 contribution
- **Filters** — category, price, rating
- **Recommendations** — content similarity + simulated co-occurrence
- **Clustering** — KMeans + UMAP visualization
- **Evaluation** — Precision@5 / @10 on 15 queries

---

## Quick Start

### Prerequisites

- Python 3.10+
- ~2 GB disk (PyTorch + model weights on first run)

### Setup

```bash
git clone https://github.com/kaajal-niranjan/search-engine.git
cd search-engine

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Build indexes (first time)

```bash
python scripts/run_pipeline.py
```

Creates catalog, embeddings, FAISS index, cluster plot, and evaluation reports (~2–5 minutes on CPU).

### Launch UI

```bash
streamlit run app.py
```

1. You land on the **Sign in** page  
2. Log in with a registered demo account  
3. Use **Search**, **Clusters**, or **Evaluation**  
4. Use **Log out** in the header to return to login  

---

## App Flow

```
Open app → Login (only public page)
    → Success toast → Header + protected pages
    → Search / Clusters / Evaluation
    → Log out → Info toast → Login again
```

---

## Usage Examples

### Web UI

1. Sign in  
2. Search: `noise cancelling headphones for travel`  
3. Mode: **Hybrid** (or follow intent suggestion)  
4. Expand **Why this result?** on a card  
5. Pick a result → Similar Products  
6. Watch toasts for success / empty query / logout  

### Python API

```python
from src.hybrid_search import HybridSearch
from src.query_intent import detect_query_intent
from src.auth import verify_credentials

# Auth (hashed verification — no decrypt)
ok = verify_credentials("admin@valere.io", "your-password")

# Intent
intent = detect_query_intent("warm jacket for winter trip")
print(intent.suggested_category, intent.query_type)

# Explainable hybrid search
hybrid = HybridSearch()
response = hybrid.search_with_explanation(
    "warm jacket for winter trip",
    top_k=5,
    max_price=200,
)
for r in response.results:
    print(r.title, response.breakdowns[r.product_id].summary())
```

---

## Search Modes

| Mode | Best for | Example |
|------|----------|---------|
| **Semantic** | Vague intent | "something cozy for better sleep" |
| **BM25** | Exact SKUs | "USB-C 65W laptop charger" |
| **Hybrid** | Everyday use | "noise cancelling headphones for travel" |

Default hybrid weights: **0.7 semantic / 0.3 BM25** (tunable in the sidebar).

---

## Evaluation Results

| Method | Mean P@5 | Mean P@10 |
|--------|----------|-----------|
| BM25 | 0.787 | 0.740 |
| Semantic | **0.920** | **0.847** |
| Hybrid | 0.907 | **0.847** |

See `reports/evaluation_report.txt` and `reports/search_comparison.md`.

---

## Project Structure

```
search-engine/
├── app.py                      # Login gate, header, pages, toasts
├── requirements.txt
├── data/                       # Product catalog (CSV)
├── embeddings/                 # Vectors + FAISS (gitignored; built by pipeline)
├── docs/                       # Architecture, data flow, deep dive, reports
├── notebooks/
├── reports/
├── scripts/run_pipeline.py
├── src/
│   ├── auth.py                 # PBKDF2 login verification
│   ├── notifications.py        # Toast helpers + top-right CSS
│   ├── config.py
│   ├── preprocessing.py
│   ├── embedding_generator.py
│   ├── vector_search.py
│   ├── bm25_search.py
│   ├── hybrid_search.py
│   ├── query_intent.py
│   ├── search_explanation.py
│   ├── recommender.py
│   ├── clustering.py
│   └── evaluation.py
└── visuals/                    # Cluster plot (gitignored)
```

---

## Documentation

| Doc | Contents |
|-----|----------|
| [Architecture](docs/ARCHITECTURE.md) | Diagrams: auth, UI, search, ML, data |
| [Data Flow](docs/DATA_FLOW.md) | Login → search → toast traces with examples |
| [Scope & Implementation](docs/SCOPE_AND_IMPLEMENTATION.md) | What was built and how |
| [Technical Deep Dive](docs/TECHNICAL_DEEP_DIVE.md) | Module-by-module review prep |
| [Enhancements](docs/ENHANCEMENTS.md) | Done + future roadmap |
| [Enhancement Report](docs/ENHANCEMENT_REPORT.md) | Before/after for smart search, auth, toasts |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit |
| Auth | Session state + PBKDF2-HMAC-SHA256 |
| Notifications | `st.toast` + custom CSS |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Vector search | FAISS `IndexFlatIP` |
| Keyword search | rank-bm25 (Okapi BM25) |
| Clustering | scikit-learn KMeans + UMAP |
| Data | pandas / NumPy / Parquet |

---

## Performance Notes

- First model load ~3–5s (warmup)  
- Query embedding LRU cache for repeat searches  
- Search runs on button submit (not every slider move)  
- Clusters / Evaluation avoid full ML load when possible  

---

## Recent Enhancements

1. **Smart Search** — intent detection + explainable hybrid results  
2. **Authentication** — login-first routing, logout, hashed passwords  
3. **Toasts** — top-right notifications for auth and search  

Full write-up: [docs/ENHANCEMENT_REPORT.md](docs/ENHANCEMENT_REPORT.md).

---

## Limitations

- Synthetic 800-product catalog  
- Demo users in code (hashed), not a full identity service  
- No REST API / automated test suite yet  
- Post-retrieval filtering; full rebuild on catalog change  

---

## Roadmap

See [docs/ENHANCEMENTS.md](docs/ENHANCEMENTS.md): FastAPI, RRF, Docker/CI, real user DB, cross-encoder re-ranking.

---

## Review Package (GitHub + Google Drive)

- **GitHub:** push this repo (including `docs/` and updated `README.md`) to your remote.  
- **Google Drive:** upload `docs/`, `README.md`, and `reports/`, then share the folder with your reviewer (e.g. `dd@valere.io`). Drive sharing requires your Google account.

---

## License

MIT — educational and portfolio use.
