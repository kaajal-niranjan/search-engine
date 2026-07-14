# Enhancement Report — Current Product State

**Updated:** 15 July 2026  

This report summarizes major changes from the original open search demo to the **current** login-gated search product — including **15 July 2026** UX and platform enhancements — while keeping all project-brief deliverables.

> **Management briefing for today’s work:** [ENHANCEMENTS_2026-07-15.md](ENHANCEMENTS_2026-07-15.md)

---

## Executive Summary

| Area | Outcome |
|------|---------|
| Core AI search | Semantic + BM25 + Hybrid unchanged in spirit |
| Project deliverables | Catalog, FAISS, recs, cluster image, eval table still produced |
| UI | Login / register + search (mode, filters, autocomplete, history, cards) |
| Security / UX | Hashed passwords, local user store, persistent session, idle logout, toasts |
| Ranking filters | Dedicated Filter Engine after ranking (architecture-aligned) |

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
| Empty input still showed previous results | Clear `search_results` / `search_query` on empty submit |

---

## Part D — 15 July 2026 Enhancements (Detail)

| Enhancement | Summary |
|-------------|---------|
| Registration | Create account → local hashed user store |
| Persistent session | Stay signed in across refresh; idle timeout |
| Filter Engine | Post-ranking category / price / rating via Metadata Store |
| Autocomplete | Suggestions under search input (history + product titles) |
| Search History | Sidebar list: compact, scrollable, single-line + tooltip; live update; re-run on click |

Full management write-up: [ENHANCEMENTS_2026-07-15.md](ENHANCEMENTS_2026-07-15.md).

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
| Pipeline cluster + eval | ✅ | ✅ |

---

## How Reviewers Should Inspect Deliverables

1. Run `python scripts/run_pipeline.py` if artifacts missing.  
2. `streamlit run app.py` — register/sign in, try autocomplete + history, empty Search, filters.  
3. Open `visuals/cluster_visualization.png` and `reports/evaluation_results.csv`.  
4. Read [ENHANCEMENTS_2026-07-15.md](ENHANCEMENTS_2026-07-15.md) for today’s delta vs earlier GitHub state.  
