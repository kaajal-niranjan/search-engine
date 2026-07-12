# Technical Deep Dive — Codebase Review

Prepared for the next-round technical discussion. Maps **modules**, auth, toasts, search, and talking points.

---

## Repository Map

| Path | Purpose |
|------|---------|
| `app.py` | Streamlit UI: login gate, header, pages, toasts |
| `src/auth.py` | Email/password with PBKDF2 salted hashes |
| `src/notifications.py` | Toast queue + top-right CSS |
| `src/config.py` | Paths and search/ML constants |
| `src/preprocessing.py` | Synthetic catalog + cleaning |
| `src/embedding_generator.py` | Sentence Transformer encoding |
| `src/vector_search.py` | FAISS semantic search |
| `src/bm25_search.py` | BM25 keyword search |
| `src/hybrid_search.py` | Fusion + explainability |
| `src/query_intent.py` | Intent detection |
| `src/search_explanation.py` | Score breakdown dataclass |
| `src/recommender.py` | Content + co-occurrence recs |
| `src/clustering.py` | KMeans + UMAP |
| `src/evaluation.py` | Precision@k benchmark |
| `scripts/run_pipeline.py` | Offline build |
| `docs/` | Architecture, flow, scope, reports |

---

## Module Deep Dive

### `app.py` — Presentation + Auth Gate

**Startup order:**

1. `set_page_config`  
2. `inject_toast_styles()`  
3. `init_auth_state()`  
4. `show_pending_toasts()`  
5. If not authenticated → `login_page()` and return  
6. Else → `render_app_header()` + sidebar navigation  

**Protected pages:** Search, Clusters, Evaluation.

**Caching:**

| Decorator | What |
|-----------|------|
| `@st.cache_resource` | Search stack (model, indexes) |
| `@st.cache_data` | Recommendations per product |

---

### `src/auth.py` — Security

| Function | Role |
|----------|------|
| `hash_password` | Create `salt:digest` for storage |
| `_derive_hash` | PBKDF2-HMAC-SHA256 (100k iterations) |
| `verify_credentials` | Hash typed password; compare digests |
| `is_valid_email` | Basic email format check |

**Talking point:** Passwords are not “decrypted.” Verification is one-way hash comparison. Plain passwords never appear in the login UI.

---

### `src/notifications.py` — Toasts

| Function | Role |
|----------|------|
| `inject_toast_styles` | Fixed top-right positioning |
| `queue_toast` | Persist message across `st.rerun()` |
| `show_pending_toasts` | Flush queue at app start |
| `toast_success/error/warning/info` | Immediate `st.toast` |

**Events wired in app:** login success/fail, logout, empty/successful search, cluster generate, engine load failure.

---

### `src/config.py` — Single Source of Truth

Paths (`DATA_DIR`, `EMBEDDINGS_DIR`, …), model name, hybrid weights (`0.7` / `0.3`), cluster and search defaults.

---

### `src/preprocessing.py` — Data

- Generate synthetic catalog  
- Clean + `search_text`  
- EDA report  

---

### `src/embedding_generator.py` — Encoding

| Method | Purpose |
|--------|---------|
| `generate()` | Batch encode products |
| `encode_query()` | Query vector (LRU cached) |
| `warmup()` | Pre-load model |

---

### `src/vector_search.py` — Semantic Retrieval

`SearchResult` dataclass; `IndexFlatIP`; filters after ANN; `search_with_vector` for hybrid.

**Assumption:** FAISS row `i` ↔ catalog row `i`.

---

### `src/bm25_search.py` — Keyword Retrieval

Simple tokenizer; `BM25Okapi`; `argpartition` for top-k.

---

### `src/hybrid_search.py` — Fusion

| API | Returns |
|-----|---------|
| `search()` | `list[SearchResult]` (backward compatible) |
| `search_with_explanation()` | `ExplainableSearchResponse` |

Includes intent, optional category boost, and per-id `ScoreBreakdown`.

---

### `src/query_intent.py` / `search_explanation.py`

Intent: category, confidence, query type, recommended mode.  
Explanation: semantic/BM25 ranks, contributions, `summary()`.

---

### `src/recommender.py` / `clustering.py` / `evaluation.py`

Recommendations (content + simulated co-occurrence), UMAP clusters, 15-query Precision@k eval.

---

## Data Structures

```
SearchResult
Recommendation
QueryIntent
ScoreBreakdown
ExplainableSearchResponse
EvalQuery
Session: authenticated, user_email, search_*, _pending_toasts
```

---

## Interview Talking Points

### Why login before search?

Demo access control; protects evaluation/search pages; mirrors product apps where search is behind auth.

### Why PBKDF2 instead of reversible encryption?

Security best practice: stores must not yield original passwords if leaked. Login = re-hash + compare.

### Why hybrid?

Semantic wins on intent (high P@5); BM25 rescues SKUs; hybrid improves mixed queries (e.g. toddler gift).

### Why FAISS IndexFlatIP?

800 products → exact search is fine; swap to IVF/HNSW at millions.

### What did recent enhancements add?

1. Auth gate + logout  
2. Hashed credentials (no password on UI)  
3. Top-right toasts  
4. Intent + explainable hybrid  

### Weakest parts?

No pytest suite; FAISS↔CSV coupling; synthetic data; demo user store.

---

## Files to Review Live

| Priority | File | Focus |
|----------|------|-------|
| 1 | `app.py` | Auth gate, header, toasts |
| 2 | `src/auth.py` | Password hashing |
| 3 | `src/hybrid_search.py` | Fusion + explainability |
| 4 | `src/vector_search.py` | FAISS + filters |
| 5 | `src/notifications.py` | Toast UX |
| 6 | `src/evaluation.py` | Metrics |

---

## Quick Verification

```bash
python scripts/run_pipeline.py
streamlit run app.py
# Login → Search → toast on success → Log out → back to login
```

```python
from src.auth import verify_credentials
from src.query_intent import detect_query_intent
print(verify_credentials("admin@valere.io", "<your-password>"))
print(detect_query_intent("warm jacket for winter trip"))
```

---

## Likely Deep-Dive Questions

1. How does route protection work without a real router?  
2. How are passwords stored and verified?  
3. How would you scale to 10M products?  
4. How would you add OAuth / a real user DB?  
5. How does explainability help trust?  
6. How do queued toasts survive `st.rerun()`?

Answers also live in `SCOPE_AND_IMPLEMENTATION.md`, `ENHANCEMENTS.md`, and `ENHANCEMENT_REPORT.md`.
