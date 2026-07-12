# Architecture Diagram — Semantic Product Search Engine

This document explains **how the application is built** today: login, a minimal search UI, hybrid retrieval, recommendations, and offline clustering/evaluation artifacts.

---

## What This Application Does (In One Sentence)

An **e-commerce-style product search engine** with **secure login** that finds products by **meaning** (not only keywords), blends semantic + BM25 scores, recommends similar items, and keeps clustering/evaluation as **pipeline deliverables** (not sidebar pages).

**Example:** User searches *"warm jacket for winter trip"* → winter clothing appears even when titles don’t use that exact phrase.

---

## High-Level Architecture

```mermaid
flowchart TB
    subgraph UserLayer["👤 User Layer"]
        USER[Shopper / Reviewer]
        LOGIN[Login Page<br/>email + password]
        HEADER[Header<br/>email + Log out]
        UI[Search UI<br/>mode + filters + product cards]
        TOAST[Toast Notifications<br/>top-right]
        RECUI[Similar Products]
    end

    subgraph AuthLayer["🔐 Auth Layer"]
        AUTH[auth.py<br/>PBKDF2 salted hashes]
        SESSION[Session State]
    end

    subgraph SearchLayer["🔍 Search Layer"]
        HYB[Hybrid Search 70/30]
        SEM[Semantic FAISS]
        KW[BM25 Keywords]
    end

    subgraph MLCore["🧠 ML Core"]
        EMB[Embedding Generator<br/>all-MiniLM-L6-v2]
        FAISS[FAISS IndexFlatIP]
        BM25IDX[BM25 Index]
        REC[Product Recommender]
    end

    subgraph DataLayer["💾 Data & Artifacts"]
        CLEAN[products_clean.csv]
        NPY[embeddings.npy]
        INDEX[faiss_index.bin]
        COOC[cooccurrence.parquet]
        VIS[cluster_visualization.png]
        EVALREP[evaluation_results.csv]
    end

    subgraph Offline["⚙️ Offline Pipeline"]
        PIPE[run_pipeline.py]
        PREP[Preprocessing]
        CLUSTER[KMeans + UMAP]
        EVAL[SearchEvaluator]
    end

    USER --> LOGIN --> AUTH --> SESSION
    SESSION -->|authenticated| HEADER
    SESSION -->|authenticated| UI
    UI --> TOAST
    LOGIN --> TOAST
    HEADER -->|Log out| SESSION

    UI --> HYB
    UI --> SEM
    UI --> KW
    UI --> RECUI --> REC

    HYB --> SEM
    HYB --> KW
    SEM --> EMB --> FAISS
    KW --> BM25IDX
    SEM --> CLEAN
    KW --> CLEAN
    REC --> NPY
    REC --> COOC

    PIPE --> PREP --> CLEAN
    PIPE --> EMB --> NPY
    PIPE --> FAISS --> INDEX
    PIPE --> CLUSTER --> VIS
    PIPE --> EVAL --> EVALREP
```

---

## Layer-by-Layer Explanation

### 1. User Layer (minimal UI)

| Screen | What the user sees |
|--------|--------------------|
| **Login** | Default route — only page before sign-in |
| **Header** | App title, signed-in email, **Log out** |
| **Search sidebar** | Mode (Hybrid / Semantic / BM25) + filters (category, price, rating) |
| **Main area** | Search box, product cards, similar products |
| **Toasts** | Success / error / warning at top-right |

**Not in the UI (by design):** Clusters page, Evaluation page, score metrics, “Why this result?” panels, weight/top-k sliders.

Those features still exist as **code + files** for the project deliverables.

---

### 2. Auth Layer

| Piece | File | Role |
|-------|------|------|
| Credential store | `src/auth.py` | Email → `salt:hash` (PBKDF2) |
| Verify | `verify_credentials()` | Re-hash typed password; compare digests |
| Session | `st.session_state` | `authenticated`, `user_email` |

Passwords are never shown in the UI and never stored as plain text.

---

### 3. Search Layer

| Mode | Module | Role |
|------|--------|------|
| Semantic | `vector_search.py` | Meaning via FAISS |
| BM25 | `bm25_search.py` | Keyword baseline |
| Hybrid | `hybrid_search.py` | Default 70% semantic + 30% BM25 |

**Filters (Task 3):** category, price range, minimum rating — applied after retrieval.

**Defaults (fixed in UI):** `top_k = 10`, semantic weight `0.7` (justified in `reports/`).

---

### 4. Recommendations (Task 4)

| Piece | File |
|-------|------|
| Content similarity | `recommender.py` (embeddings) |
| Also-viewed style | Simulated co-occurrence parquet |
| UI | “Similar Products” after picking a result |

---

### 5. Offline Deliverables (not sidebar pages)

| Deliverable | How it’s produced | Where it lives |
|-------------|-------------------|----------------|
| Cluster visualization | `clustering.py` via pipeline | `visuals/cluster_visualization.png` |
| Evaluation table | `evaluation.py` via pipeline | `reports/evaluation_results.csv` |
| Written comparison | docs / reports | `reports/search_comparison.md` |

Run: `python scripts/run_pipeline.py`

---

## Component Dependency Map

```
app.py
 ├── auth.py
 ├── notifications.py
 ├── HybridSearch ── VectorSearch ── EmbeddingGenerator
 │               └── KeywordSearch
 └── ProductRecommender

scripts/run_pipeline.py
 ├── preprocessing
 ├── embedding_generator
 ├── vector_search
 ├── clustering          → visuals/
 └── evaluation         → reports/
```

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Default route | Login | Protect search until signed in |
| UI scope | Search only | Matches brief: “search UI with filters and product cards” |
| Clusters / eval in UI | Removed | Deliverables are image + CSV/reports, not extra pages |
| Hybrid weights in UI | Fixed 70/30 | Cleaner UI; justification in reports |
| Result cards | Title, category, rating, description, price | E-commerce style; no internal score UI |
| Password storage | PBKDF2 salted hash | One-way; no decrypt |

---

## What Is Still Out of Scope

- REST API, Docker/CI, real user DB, real purchase logs  
- Incremental index updates at catalog scale  

See `docs/ENHANCEMENTS.md`.
