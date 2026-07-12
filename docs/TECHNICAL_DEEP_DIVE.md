# Technical Deep Dive — Codebase Review

Updated for the **current** app: login-gated **search-only** UI, file-based cluster/eval deliverables.

---

## Repository Map

| Path | Role today |
|------|------------|
| `app.py` | Login, header, logout, search UI, toasts, recommendations |
| `src/auth.py` | PBKDF2 login verification |
| `src/notifications.py` | Top-right toasts |
| `src/config.py` | Paths, model, hybrid defaults |
| `src/preprocessing.py` | Catalog + `search_text` + EDA |
| `src/embedding_generator.py` | Batch embeddings + query cache |
| `src/vector_search.py` | FAISS semantic search |
| `src/bm25_search.py` | BM25 keyword search |
| `src/hybrid_search.py` | Score fusion (+ optional explain API unused by UI) |
| `src/query_intent.py` | Intent helpers (available; not shown in minimal UI) |
| `src/search_explanation.py` | Score breakdown dataclass (library; not shown in UI) |
| `src/recommender.py` | Similar products |
| `src/clustering.py` | KMeans + UMAP → `visuals/` |
| `src/evaluation.py` | P@k → `reports/` |
| `scripts/run_pipeline.py` | Offline build of all artifacts |
| `docs/` | Architecture, DFD, scope, this guide, etc. |

---

## UI vs Backend (Important for Reviewers)

| Capability | In Streamlit UI? | Still in codebase / files? |
|------------|------------------|----------------------------|
| Login / logout / toasts | Yes | Yes |
| Hybrid / Semantic / BM25 | Yes | Yes |
| Category / price / rating filters | Yes | Yes |
| Product cards + similar products | Yes | Yes |
| Cluster visualization | **No page** | Yes → `visuals/` via pipeline |
| Evaluation table | **No page** | Yes → `reports/` via pipeline |
| Score / “Why this result?” | **Removed from UI** | Explain API still in `hybrid_search` |

---

## `app.py` Flow

```
main()
  → login_page() if not authenticated
  → render_app_header()
  → load_search_stack()
  → search_page()
       sidebar: mode + filters
       form: query
       empty submit → clear previous results
       results → cards → similar products
```

**Talking point:** Sidebar has no Clusters/Evaluation pages because the brief’s UI requirement is a search demo; cluster image and eval CSV are separate deliverables.

---

## Core Search Modules

### Hybrid fusion (`hybrid_search.py`)

Default: `0.7 * sem_norm + 0.3 * bm25_norm` after min-max normalization.

### FAISS (`vector_search.py`)

`IndexFlatIP` on L2-normalized vectors (= cosine). Filters applied post-retrieval.

### BM25 (`bm25_search.py`)

Okapi BM25 over `search_text`; same filters.

### Recommender (`recommender.py`)

Content similarity + simulated co-occurrence blend.

---

## Offline Deliverables Deep Dive

### Clustering (`clustering.py`)

- KMeans on embeddings  
- UMAP 2D plot saved under `visuals/`  
- Sanity-check that embeddings form neighborhoods  

### Evaluation (`evaluation.py`)

- 15 `EVAL_QUERIES`  
- Precision@5 / @10 for BM25, Semantic, Hybrid  
- Outputs CSV + text report  

Review these files in the deep dive even though they are not sidebar pages.

---

## Interview Talking Points

1. **Why remove Clusters/Evaluation from the UI?**  
   Brief: simple search UI. Deliverables = image + evaluation table in repo/reports.

2. **Why hybrid 70/30?**  
   Semantic wins on intent queries; BM25 rescues SKUs; reports show hybrid’s trade-off.

3. **How passwords work?**  
   Salted PBKDF2; compare hashes; never decrypt; never show password on UI.

4. **Empty search bug fix?**  
   Clearing the box and submitting clears `session_state` results so the previous query is not reused.

5. **Scale to millions?**  
   Switch FAISS to IVF/HNSW; pre-filter metadata; serve embeddings separately.

---

## Suggested Live Demo Path

1. Login  
2. Query: `warm jacket for winter trip` (Hybrid)  
3. Switch mode to BM25 / Semantic and compare feel  
4. Apply Clothing + price filter  
5. Open Similar Products  
6. Show `visuals/cluster_visualization.png` and `reports/evaluation_results.csv` from disk/docs  

---

## Quick Commands

```bash
python scripts/run_pipeline.py
streamlit run app.py
```
