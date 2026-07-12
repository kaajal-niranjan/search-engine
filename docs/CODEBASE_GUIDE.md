# Codebase Guide — What Lives Where (and Why)

Plain-language map of the **current** project: folders, files, how inputs are taken, and what is UI vs file deliverable.

---

## Questions This Guide Answers

- Where do I change login or search UI?  
- Which files build FAISS / BM25 / hybrid?  
- Why are Clusters / Evaluation not in the sidebar?  
- How is the query / password / catalog **taken** into the system?  

---

## Big Picture

```
search-engine/
│
├── app.py                 ← Login + minimal Search UI only
├── requirements.txt
├── README.md
│
├── src/                   ← Core logic (auth, search, ML, eval, clustering)
├── scripts/               ← Offline pipeline (builds indexes + deliverables)
├── data/                  ← Product CSVs
├── embeddings/            ← Generated vectors / FAISS (local)
├── visuals/               ← Cluster plot deliverable (local)
├── reports/               ← EDA + evaluation deliverables
├── notebooks/             ← Optional EDA notebook
└── docs/                  ← Architecture, DFD, this guide, …
```

| Layer | Location | Job |
|-------|----------|-----|
| UI | `app.py` | Login, search, filters, cards, recs, toasts |
| Logic | `src/` | Auth, embeddings, search, recs, cluster, eval |
| Build | `scripts/run_pipeline.py` | Create data + indexes + visuals + reports |
| Inputs | `data/` | Catalog |
| Outputs | `embeddings/`, `visuals/`, `reports/` | Runtime + deliverables |

---

## UI vs Project Deliverables

| Brief item | In Streamlit? | In repo? |
|------------|---------------|----------|
| Search UI + filters + cards | ✅ | `app.py` |
| Similar products | ✅ | `recommender.py` |
| Cluster visualization | ❌ no menu page | `visuals/` via pipeline |
| Evaluation table / comparison | ❌ no menu page | `reports/` via pipeline |

**Why:** The brief asks for a *simple search UI*. Cluster image and evaluation table are separate deliverables.

---

## Suggested Reading Order

1. This file  
2. `README.md`  
3. `app.py`  
4. `src/config.py` → `auth.py` → `hybrid_search.py` → `vector_search.py` → `bm25_search.py`  
5. `scripts/run_pipeline.py`  
6. `docs/ARCHITECTURE.md` + `DATA_FLOW.md`  

---

## How Input Is Taken (End-to-End)

### 1. Login email & password

```
Login form (app.py)
  → is_valid_email / verify_credentials (auth.py)
  → hash typed password with stored salt (PBKDF2)
  → compare digests (no decrypt)
  → session authenticated + welcome toast
```

### 2. Search query

```
Search form text_input (key=search_query_input)
  → on Submit, read submitted string
  → if empty: clear previous results + warning toast
  → if not empty: run_search(mode, filters) → session results
```

**Modes:** Hybrid → `HybridSearch.search` · Semantic → `VectorSearch` · BM25 → `KeywordSearch`.

### 3. Filters

Sidebar → `category`, `min_price`/`max_price`, `min_rating` → passed into search → applied after retrieval.

### 4. Catalog & embeddings

- Pipeline writes `products_clean.csv` and embedding/FAISS files  
- Search modules **read** those files at runtime  

### 5. Recommendations

User picks a result → `product_id` → `ProductRecommender.recommend`.

### 6. Clusters & evaluation (not from UI forms)

Hardcoded / pipeline-driven:

- Clustering reads embeddings → writes PNG  
- Evaluation loops `EVAL_QUERIES` → writes CSV  

---

## Root Files

### `app.py`

**Purpose:** Only user-facing app.

**Contains now:**

- Login gate + logout header  
- Toasts  
- Search sidebar (mode + filters)  
- Product cards + similar products  
- Empty-query clears old results  

**Does not contain:** Clusters page, Evaluation page.

**How input is taken:** Forms and sidebar widgets → `src/` functions.

---

### `requirements.txt` / `README.md` / `.gitignore`

Dependencies, how to run, ignore `embeddings/` / `visuals/` / venv, etc.

---

## Folder: `src/`

| File | Purpose | Why |
|------|---------|-----|
| `config.py` | Paths, model name, `DEFAULT_TOP_K`, hybrid weights | Single place for defaults |
| `auth.py` | PBKDF2 verify | Secure login |
| `notifications.py` | Toasts + top-right CSS | Non-blocking feedback |
| `preprocessing.py` | Synthetic catalog + `search_text` + EDA | Task 1 |
| `embedding_generator.py` | Encode products/queries | Task 2 |
| `vector_search.py` | FAISS semantic search | Task 2 |
| `bm25_search.py` | Keyword baseline | Task 3 |
| `hybrid_search.py` | Blend scores | Task 3 |
| `recommender.py` | Similar + co-occurrence | Task 4 |
| `clustering.py` | KMeans + UMAP file | Task 4 deliverable |
| `evaluation.py` | Precision@k | Task 5 deliverable |
| `query_intent.py` | Intent helpers | Optional/advanced (not in minimal UI) |
| `search_explanation.py` | Breakdown dataclass | Optional/advanced (not in minimal UI) |
| `__init__.py` | Package marker | Imports |

---

## Folder: `scripts/`

### `run_pipeline.py`

Builds everything offline:

1. Preprocess  
2. Embeddings  
3. FAISS  
4. Clusters → `visuals/`  
5. Evaluation → `reports/`  

**Run before demos** (or let first search bootstrap embeddings if missing).

---

## Folders: `data/`, `embeddings/`, `visuals/`, `reports/`, `notebooks/`

| Folder | Contents | UI reads it? |
|--------|----------|--------------|
| `data/` | raw + clean CSV | Yes (clean) |
| `embeddings/` | vectors, FAISS, co-occurrence | Yes |
| `visuals/` | cluster PNG | No (deliverable) |
| `reports/` | EDA, eval CSV/txt, comparison md | No (deliverable) |
| `notebooks/` | EDA notebook | No |

---

## Folder: `docs/`

| Doc | Purpose |
|-----|---------|
| `CODEBASE_GUIDE.md` | This file |
| `ARCHITECTURE.md` | System diagram |
| `DATA_FLOW.md` | Login/search/pipeline flows |
| `SCOPE_AND_IMPLEMENTATION.md` | Scope vs UI |
| `TECHNICAL_DEEP_DIVE.md` | Review talking points |
| `ENHANCEMENTS.md` | Roadmap |
| `ENHANCEMENT_REPORT.md` | Before/after of UI & features |
| `README.md` | Doc index |

---

## How Files Connect

```
User
 └─ app.py
      ├─ auth.py
      ├─ notifications.py
      ├─ HybridSearch / VectorSearch / KeywordSearch
      └─ ProductRecommender

Pipeline
 └─ preprocessing → embeddings → FAISS
      → clustering (visuals/)
      → evaluation (reports/)
```

---

## “I Want To Change X → Edit Y”

| Goal | Edit |
|------|------|
| Login / logout / search layout | `app.py` |
| Users / password hashing | `src/auth.py` |
| Toasts | `src/notifications.py` |
| Default top-k / hybrid weights | `src/config.py` |
| Semantic / BM25 / hybrid logic | `vector_search` / `bm25_search` / `hybrid_search` |
| Recommendations | `recommender.py` |
| Rebuild cluster image / eval table | `scripts/run_pipeline.py` |
| Eval queries | `evaluation.py` |

---

## Checklist Before a Review

- [ ] UI is login + search only  
- [ ] Cluster PNG and evaluation CSV exist after pipeline  
- [ ] Hybrid 70/30 justified in reports  
- [ ] Empty search does not keep old results  
- [ ] Passwords are hashed, not shown  

If yes, the codebase matches the current documented architecture.
