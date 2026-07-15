# Enhancement Report — Current Product State

**Updated:** 15 July 2026  
**Audience:** Management / reviewers  
**Branch:** `backup`

This report summarizes major changes from the original open search demo to the **current** login-gated search product — including **15 July 2026** UX and platform enhancements — while keeping all project-brief deliverables.

---

## Executive Summary

| Area | Outcome |
|------|---------|
| Core AI search | Semantic + BM25 + Hybrid unchanged in spirit |
| Project deliverables | Catalog, FAISS, recs, cluster image, eval table still produced |
| UI | Login / register + search (mode, filters, autocomplete, history, cards) |
| Security / UX | Hashed passwords, local user store, persistent session, idle logout, toasts |
| Ranking filters | Dedicated Filter Engine after ranking (architecture-aligned) |

### 15 July 2026 snapshot (for management)

| Theme | What changed |
|-------|----------------|
| **Accounts** | Users can **create an account**; credentials in local hashed store (not hard-coded demos only) |
| **Session** | Stay signed in after browser refresh; **auto log-out** after idle time (10 minutes) |
| **Filters** | Category / price / rating applied **after ranking**, aligned with architecture diagrams |
| **Search UX** | Under-input **autocomplete**; sidebar **Search History** (compact, scrollable, single-line + tooltip) |
| **Correctness** | Empty Search **clears** old results |

**Business value:** Closer to a real shopper experience — remember the user, help them type and re-run past queries, and show only what they asked for — without changing the core hybrid search science.

---

## Part A — UI Alignment With the Brief

### Before (busy demo UI)

- Sidebar pages: Search, Clusters, Evaluation  
- Extra controls: top-k, semantic weight, smart-search toggles  
- Result cards: Score metric + “Why this result?” expanders  
- Intent info banners  

### After (minimal + assistive UI)

- Sidebar: **Mode** + **Filters** + **Search History**  
- Main: autocomplete search box, product cards, similar products  
- Cards: title, category, rating, description, price  
- Clusters & evaluation: **files** from `run_pipeline.py`, not menu items  

### Reasoning

Task 5 asks for a *simple Streamlit search UI with filters and product cards*.  
Task 4/5 cluster plot and evaluation table are **deliverables**, satisfied by:

- `visuals/cluster_visualization.png`  
- `reports/evaluation_results.csv` (+ comparison markdown)  

---

## Part B — Authentication, Session & Toasts

| Feature | Behavior |
|---------|----------|
| Default route | Sign in (optional Create account) |
| Passwords | PBKDF2 `salt:hash` in local `data/users.json`; never shown on UI |
| Session | Survives browser refresh via session id; idle auto-logout |
| Logout | Header button; clears session and search state |
| Toasts | Top-right feedback for auth and search |

---

## Part C — Search Behavior Fixes

| Issue | Fix |
|-------|-----|
| Empty input still showed previous results | Clear `search_results` / `search_query` on empty submit; warning toast |

---

## Part D — 15 July 2026 Enhancements (Detail)

### 1. User Registration & Local Credential Store

| Before | After |
|--------|--------|
| Mostly static / seeded demo logins | **Sign in** and **Create account** flows |
| Credentials buried in code | Local store `data/users.json` (ignored by git) |
| — | Passwords still **PBKDF2** salted hashes |

**Modules:** `src/auth.py`, `src/config.py` (`USERS_STORE_PATH`), `app.py` auth views  

**Takeaway:** Reviewers and demo users can self-register without engineering editing code.

### 2. Persistent Session & Idle Logout

| Before | After |
|--------|--------|
| Refresh → forced re-login | Session **survives refresh** (browser session id + server session file) |
| No idle policy | **Idle timeout** (currently **600 seconds / 10 minutes**) |
| — | Manual **Log out** still clears session + search state |

**Modules:** `src/session.py`, `src/browser_cookies.py`, `data/sessions.json`  

**Takeaway:** Less friction in demos; safer than an endless open session.

### 3. Filter Engine (Architecture Alignment)

| Before | After |
|--------|--------|
| Filters mixed into search call sites | Dedicated **Filter Engine** + **Metadata Store** |
| Harder to describe vs diagrams | Rank first → filter by category / price / rating |

**Modules:** `src/filter_engine.py`; wired from `vector_search.py`, `bm25_search.py`, `hybrid_search.py`  

**Takeaway:** Matches the agreed architecture/data-flow diagrams. UI filter controls unchanged for shoppers.

### 4. Search Autocomplete

| Before | After |
|--------|--------|
| Plain text box | Custom control under the search input |
| — | Suggests **recent searches** when focused/empty; **product titles** while typing |
| — | Click suggestion or press Search / Enter to run |

**Modules:** `src/search_autocomplete.py`, `src/frontend_search_ac/index.html`, `src/search_assist.py`  

**Takeaway:** Faster discovery; fewer abandoned searches in demos.

### 5. Per-User Search History (Sidebar)

| Before | After |
|--------|--------|
| No history list | **Search History** panel in the sidebar |
| — | Newest first; up to **20** queries per user (`search_history.json`) |
| — | Compact **scrollable** list; **one line** per item with `…` + hover tooltip |
| — | Click a row to re-run that search; **Clear history** supported |
| — | List **updates immediately** after each successful search |

**Modules:** `src/search_assist.py`, `src/search_history_list.py`, `src/frontend_search_history/index.html`, `app.py` sidebar  

**Takeaway:** Shoppers and reviewers can recover past demo queries without retyping.

### 6. Empty Search Clears Results

| Issue | Fix |
|-------|-----|
| Cleared input + Search still showed previous products | Empty query **clears** results and query state; warning toast |

**Takeaway:** No results when there is no query.

### Files added / touched

| Area | Key paths |
|------|-----------|
| Auth / users | `src/auth.py`, `data/users.json` (local) |
| Sessions | `src/session.py`, `src/browser_cookies.py`, `data/sessions.json` |
| Filters | `src/filter_engine.py` |
| Search assist | `src/search_assist.py`, `src/search_autocomplete.py`, `src/search_history_list.py` |
| Frontends | `src/frontend_search_ac/`, `src/frontend_search_history/` |
| UI wiring | `app.py`, `src/config.py` |

### How to demo (5 minutes)

1. Open the app → **Create account** (or sign in).  
2. Refresh the browser → still signed in.  
3. Type in search → see autocomplete; run a query.  
4. Confirm new item appears in **Search History**; click it to re-run.  
5. Clear the box → Search → results disappear + toast.  
6. Leave idle ~10 minutes (or lower timeout in config for a short demo) → auto log-out.  

### Out of scope (unchanged)

- REST API, cloud user database, OAuth  
- Cluster / Evaluation **pages** in the sidebar (still pipeline file deliverables)  
- Changing hybrid science (still ~70% semantic / 30% BM25 in UI)  

---

## Part E — Free LLM Catalog (Ollama, Build-Time Only)

Search UI, hybrid ranking, filters, history, and auth are **unchanged**. A free local LLM can optionally **generate** the product CSV used by the existing pipeline.

| Item | Detail |
|------|--------|
| Runtime search | Still FAISS + BM25 + hybrid over `products_clean.csv` |
| LLM role | Build-time catalog generation only (not per query) |
| Provider | [Ollama](https://ollama.com) (free, local) — default model `llama3.2` |
| Script | `python scripts/generate_catalog_llm.py --count 200` |
| Pipeline | `python scripts/run_pipeline.py --llm-catalog --count 200` |
| Fallback | Default pipeline (no flag) keeps synthetic catalog |

**Modules:** `src/llm_catalog.py`, `scripts/generate_catalog_llm.py`, config keys `OLLAMA_*` / `LLM_CATALOG_*`

**Full how-to:** [LLM_CATALOG.md](LLM_CATALOG.md)

---

## Before / After Matrix

| Capability | Original busy UI | Current |
|------------|------------------|---------|
| Hybrid / Semantic / BM25 | ✅ | ✅ |
| Filters | ✅ | ✅ (Filter Engine) |
| Recommendations | ✅ | ✅ |
| Cluster **page** | ✅ | ❌ (file only) |
| Evaluation **page** | ✅ | ❌ (file only) |
| Score / explanation UI | ✅ | ❌ |
| Login + toasts | ✅ (later) | ✅ |
| Register + local users | ❌ | ✅ |
| Session persist / idle logout | ❌ | ✅ |
| Autocomplete + search history | ❌ | ✅ |
| Free LLM catalog (Ollama, optional) | ❌ | ✅ (build-time) |
| Pipeline cluster + eval | ✅ | ✅ |

---

## How Reviewers Should Inspect Deliverables

1. Run `python scripts/run_pipeline.py` if artifacts missing.  
2. `streamlit run app.py` — register/sign in, try autocomplete + history, empty Search, filters.  
3. Open `visuals/cluster_visualization.png` and `reports/evaluation_results.csv`.  
4. Use **Part D** above for the 15 July 2026 delta vs the earlier GitHub baseline.  

## Related documents

| Document | Use |
|----------|-----|
| [ENHANCEMENTS.md](ENHANCEMENTS.md) | Done checklist + future roadmap |
| [DATA_FLOW.md](DATA_FLOW.md) | Auth, session, search, history flows |
| [CODEBASE_GUIDE.md](CODEBASE_GUIDE.md) | Where each new module lives |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layers including assist + filter engine |
| [../README.md](../README.md) | Product overview for new readers |
