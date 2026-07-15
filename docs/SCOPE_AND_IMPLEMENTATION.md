# Scope & Technical Implementation

Current understanding of **scope**, **what the UI shows**, and **how the system is implemented**.

---

## 1. Project Scope vs UI Scope

### Required by the project brief (must exist)

| Task | Deliverable | Where it lives |
|------|-------------|----------------|
| Task 1 | Catalog + `search_text` + EDA | `data/`, `reports/eda_report.txt` |
| Task 2 | Embeddings + FAISS + semantic search | `src/embedding_generator.py`, `vector_search.py` |
| Task 3 | Filters + BM25 + hybrid blend | `bm25_search.py`, `hybrid_search.py`, `filter_engine.py`, UI filters |
| Task 4 | Similar products + co-occurrence + clusters | `recommender.py`, `clustering.py`, `visuals/` |
| Task 5 | Eval queries + P@k + search UI + comparison write-up | `evaluation.py`, `reports/`, Streamlit search |

### What the Streamlit UI includes (kept minimal)

| In UI | Not in UI (still in repo) |
|-------|---------------------------|
| Sign in / Create account + logout | Cluster **page** |
| Persistent session + idle logout | Evaluation **page** |
| Search mode Hybrid / Semantic / BM25 | Score / “why ranked” panels |
| Filters: category, price, rating | Weight / top-k sliders |
| Autocomplete + Search History | — |
| Product cards + similar products | — |
| Toast notifications | — |

**Rationale:** Brief asks for a *simple search UI with filters and product cards*. Cluster plot and evaluation table are **file deliverables**, produced by the pipeline. 15 Jul 2026 additions improve account, session, and query assist without returning to a multi-page demo UI.

---

## 2. In Scope Features (Built)

- Sign in / register, hashed credentials, logout  
- Persistent session + idle auto-logout  
- Toast notifications (top-right)  
- Semantic / BM25 / hybrid search  
- Filter Engine (post-ranking structured filters)  
- Autocomplete + per-user search history  
- Recommendations (content + simulated co-occurrence)  
- Offline clustering (KMeans + UMAP image)  
- Offline evaluation (15 queries, P@5 / P@10)  
- Written comparison in `reports/search_comparison.md`  

---

## 3. Out of Scope

- REST API, OAuth, production user DB  
- Real behavioral purchase data  
- Automated pytest suite / cloud deploy  
- Sidebar pages for clusters & evaluation  

---

## 4. Technical Implementation Summary

### Auth — `src/auth.py` + `src/session.py` + `app.py`

- Default route = sign in (create account available)  
- PBKDF2-HMAC-SHA256 salted hashes in `data/users.json`  
- Session survives refresh; idle timeout auto log-out  
- Empty search clears previous results (does not reuse last query)  

### Search UI — `app.py`

```
Sidebar:
  Mode: Hybrid | Semantic | BM25
  Filters: Category, Price range, Minimum rating
  Search History: compact scrollable list (click to re-run)

Main:
  Autocomplete query + Search button
  Product cards (title, category, rating, description, price)
  Similar Products
```

Fixed defaults: `DEFAULT_TOP_K = 10`, semantic weight `0.7`.

### Hybrid ranking — `src/hybrid_search.py`

```
combined = 0.7 × normalized_semantic + 0.3 × normalized_bm25
```

Weighting justified in evaluation reports (semantic for intent; BM25 for exact tokens).

### Pipeline — `scripts/run_pipeline.py`

Preprocess → embed → FAISS → cluster plot → evaluation CSV/report.

---

## 5. How to Run

```bash
pip install -r requirements.txt
python scripts/run_pipeline.py   # builds data, indexes, visuals, reports
streamlit run app.py             # login → search UI
```

---

## 6. Success Criteria Checklist

| Criterion | Status |
|-----------|--------|
| Semantic search on natural language | ✅ |
| BM25 baseline | ✅ |
| Hybrid + filters | ✅ |
| Recommendations | ✅ |
| Cluster visualization file | ✅ pipeline |
| Evaluation table file | ✅ pipeline |
| Simple search UI | ✅ |
| Login + clean minimal UI | ✅ |

---

## 7. Known Limitations

- Synthetic catalog (~800 products)  
- Demo users hashed in code  
- Post-retrieval filtering  
- Full rebuild on catalog change  
