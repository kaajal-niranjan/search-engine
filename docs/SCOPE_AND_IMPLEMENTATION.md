# Scope & Technical Implementation

Understanding of **project scope**, **what was built**, and **how it works** — for reviewers and technical deep dives.

---

## 1. Project Scope

### In Scope (Built)

| Area | Description |
|------|-------------|
| **Login gate** | Email + password; default route; other pages blocked until login |
| **Logout** | Header button; clears session and search state |
| **Secure passwords** | Salted PBKDF2 hashes; never shown on UI |
| **Toast notifications** | Top-right feedback for auth and search actions |
| **Semantic search** | Sentence embeddings + FAISS |
| **Keyword search** | BM25 baseline |
| **Hybrid ranking** | Weighted fusion (default 70/30) |
| **Query intent** | Category / mode hints from the query |
| **Explainable results** | Per-product semantic vs BM25 breakdown |
| **Filters** | Category, price, rating |
| **Recommendations** | Content + simulated co-occurrence |
| **Clustering** | KMeans + UMAP visualization |
| **Evaluation** | Precision@5 / @10 on 15 queries |
| **Streamlit UI** | Login + Search + Clusters + Evaluation |
| **Offline pipeline** | One-command build of data and indexes |

### Out of Scope (Not Built)

| Area | Reason |
|------|--------|
| Production REST API | Demo / portfolio focus |
| Real e-commerce catalog | 800 synthetic products |
| Real user DB / OAuth | In-app hashed demo users |
| Automated test suite | Manual eval benchmark |
| Cloud deployment | Local-first |

### Target Audience

- Technical reviewers (ML / search engineering)
- Interview deep-dive discussions
- Portfolio demonstration of hybrid retrieval + app UX

---

## 2. Problem Statement

| User need | Without this system | With this system |
|-----------|---------------------|------------------|
| Access control | Open demo | Must login first |
| Feedback | Silent / page banners | Non-blocking toasts |
| Vague search | Keyword miss | Semantic / hybrid hit |
| Trust in ranking | Black box | Explainable scores |

**Example intent query:** *"warm jacket for winter trip"* → winter clothing even without exact phrase.

---

## 3. Technical Implementation

### 3.1 Authentication

**Files:** `src/auth.py`, `app.py` (`login_page`, `logout`, `main`)

| Concern | Implementation |
|---------|----------------|
| Default route | If not `authenticated` → only login |
| Email check | Regex `is_valid_email` |
| Password storage | `salt:pbkdf2_hmac_sha256` (100k iterations) |
| Verify | Re-hash typed password; `secrets.compare_digest` |
| Logout | Clear auth + search session keys |

**Why hashing (not decryptable encryption)?**  
Stored credentials must not be reversible. Matching = hash again and compare.

### 3.2 Toast Notifications

**File:** `src/notifications.py`

| API | Use |
|-----|-----|
| `show_toast` / `toast_*` | Immediate feedback |
| `queue_toast` | Survive `st.rerun()` (login / logout) |
| `show_pending_toasts` | Flush queue at start of `main` |
| `inject_toast_styles` | Pin toasts to top-right |

### 3.3 Data Pipeline

**Files:** `src/preprocessing.py`, `scripts/run_pipeline.py`

1. Generate ~800 products across 8 categories  
2. Clean + build `search_text = title + description + category`  
3. EDA report  

### 3.4 Embeddings

**File:** `src/embedding_generator.py`

| Setting | Value |
|---------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dims | 384 |
| Batch | 64 |
| Query cache | LRU 256 |

### 3.5 Semantic Search (FAISS)

**File:** `src/vector_search.py`

- `IndexFlatIP` on L2-normalized vectors (= cosine)  
- Post-retrieval filters  
- `search_with_vector` for shared query encoding in hybrid  

### 3.6 Keyword Search (BM25)

**File:** `src/bm25_search.py`

- Tokenize with `\b\w+\b`  
- `BM25Okapi` + `np.argpartition` top-k  

### 3.7 Hybrid + Explainability

**File:** `src/hybrid_search.py`

1. Intent detection  
2. Candidate pools from semantic + BM25  
3. Min-max normalize; weighted sum  
4. Optional soft category boost  
5. `ExplainableSearchResponse` with `ScoreBreakdown`  

### 3.8 Query Intent

**File:** `src/query_intent.py`

- Keyword maps → 8 categories  
- Query type: `keyword` | `intent` | `mixed`  
- Suggested mode: BM25 / Semantic / Hybrid  

### 3.9 Recommendations, Clustering, Evaluation

| Module | Role |
|--------|------|
| `recommender.py` | Content + co-occurrence blend |
| `clustering.py` | KMeans + UMAP plot |
| `evaluation.py` | P@5 / P@10 on 15 queries |

**Benchmark (pipeline):**

| Method | Mean P@5 | Mean P@10 |
|--------|----------|-----------|
| BM25 | ~0.79 | ~0.74 |
| Semantic | ~0.92 | ~0.85 |
| Hybrid | ~0.91 | ~0.85 |

### 3.10 Streamlit UI Structure

```
Unauthenticated:
  Login only

Authenticated:
  Header (email + Log out)
  Sidebar: Search | Clusters | Evaluation
  Search: modes, filters, smart search, results, recs
```

---

## 4. Configuration

**File:** `src/config.py` — paths, embedding model, hybrid weights, cluster params.  
Auth users: `src/auth.py`.  
No `.env` required for the demo.

---

## 5. How to Run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python scripts/run_pipeline.py  # first time
streamlit run app.py
```

Open the app → **login** → use Search / Clusters / Evaluation.

---

## 6. Success Criteria

| Criterion | Status |
|-----------|--------|
| Login is default; other routes blocked | ✅ |
| Logout returns to login | ✅ |
| Passwords stored hashed, not shown in UI | ✅ |
| Toasts for auth and search | ✅ |
| Semantic handles intent queries | ✅ |
| BM25 handles exact tokens | ✅ |
| Hybrid balances both | ✅ |
| Explainable hybrid results | ✅ |
| Intent detection | ✅ |

---

## 7. Known Limitations

1. Demo users hardcoded (hashed) — not a full identity service  
2. Post-retrieval filters may return fewer than top_k  
3. FAISS row order coupled to CSV order  
4. Synthetic catalog and co-occurrence  
5. No automated unit tests / REST API  

Documented as future work in `docs/ENHANCEMENTS.md`.
