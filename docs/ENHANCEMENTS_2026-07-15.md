# Enhancement Summary — 15 July 2026

**Audience:** Management / reviewers  
**Branch:** `backup` (local work promoted for review)  
**Status:** Implemented and committed locally — see this pack with related doc updates  

This note explains what changed **today** versus the earlier GitHub baseline (`main` / previous `backup`), why it matters, and where to look in the product and codebase.

---

## Executive Snapshot

| Theme | What management should know |
|-------|-----------------------------|
| **Accounts** | Users can **create an account**; credentials stored locally (hashed), not a hard-coded demo list only |
| **Session** | Stay signed in after browser refresh; **auto log-out** after idle time |
| **Filters** | Category / price / rating applied **after ranking**, aligned with architecture diagrams |
| **Search UX** | Under-input **autocomplete**; **Search History** in the sidebar (compact, scrollable, single-line with tooltip) |
| **Correctness** | Empty Search **clears** old results (no stale products from the previous query) |

**Business value:** Closer to a real shopper experience — remember the user, help them type and re-run past queries, and show only what they asked for — without changing the core hybrid search science.

---

## 1. User Registration & Local Credential Store

| Before | After (today) |
|--------|----------------|
| Mostly static / seeded demo logins | **Sign in** and **Create account** flows |
| Credentials buried in code | Local store `data/users.json` (ignored by git) |
| — | Passwords still **PBKDF2** salted hashes |

**Modules:** `src/auth.py`, `src/config.py` (`USERS_STORE_PATH`), `app.py` auth views  

**Management takeaway:** Reviewers and demo users can self-register without engineering editing code.

---

## 2. Persistent Session & Idle Logout

| Before | After (today) |
|--------|----------------|
| Refresh → forced re-login | Session **survives refresh** (browser session id + server session file) |
| No idle policy | **Idle timeout** (configurable; currently **600 seconds / 10 minutes**) |
| — | Manual **Log out** still clears session + search state |

**Modules:** `src/session.py`, `src/browser_cookies.py`, `data/sessions.json`  

**Management takeaway:** Less friction in demos and usability testing; safer than an endless open session.

---

## 3. Filter Engine (Architecture Alignment)

| Before | After (today) |
|--------|----------------|
| Filters mixed into search call sites | Dedicated **Filter Engine** + **Metadata Store** |
| Harder to describe vs diagrams | Rank first → filter by category / price / rating |

**Modules:** `src/filter_engine.py`; wired from `vector_search.py`, `bm25_search.py`, `hybrid_search.py`  

**Management takeaway:** Matches the agreed architecture/data-flow diagrams (Module: Filter Engine after ranking). UI filter controls unchanged for shoppers.

---

## 4. Search Autocomplete

| Before | After (today) |
|--------|----------------|
| Plain text box | Custom control under the search input |
| — | Suggests **recent searches** when focused/empty; **product titles** while typing |
| — | Click suggestion or press Search / Enter to run |

**Modules:** `src/search_autocomplete.py`, `src/frontend_search_ac/index.html`, `src/search_assist.py`  

**Management takeaway:** Faster discovery; fewer misspelled / abandoned searches in demos.

---

## 5. Per-User Search History (Sidebar)

| Before | After (today) |
|--------|----------------|
| No history list | **Search History** panel in the sidebar |
| — | Newest first; up to **20** queries per user (`search_history.json`) |
| — | Compact **scrollable** list; **one line** per item with `…` + hover tooltip for full text |
| — | Click a row to re-run that search; **Clear history** supported |
| — | List **updates immediately** after each successful search |

**Modules:** `src/search_assist.py`, `src/search_history_list.py`, `src/frontend_search_history/index.html`, `app.py` sidebar  

**Management takeaway:** Shoppers (and reviewers) can recover past demo queries without retyping.

---

## 6. Empty Search Clears Results

| Issue | Fix |
|-------|-----|
| Cleared input + Search still showed previous products | Empty query **clears** results and query state; warning toast |

**Management takeaway:** UI honesty — no results when there is no query.

---

## Files Added / Touched (Technical Index)

| Area | Key paths |
|------|-----------|
| Auth / users | `src/auth.py`, `data/users.json` (local) |
| Sessions | `src/session.py`, `src/browser_cookies.py`, `data/sessions.json` |
| Filters | `src/filter_engine.py` |
| Search assist | `src/search_assist.py`, `src/search_autocomplete.py`, `src/search_history_list.py` |
| Frontends | `src/frontend_search_ac/`, `src/frontend_search_history/` |
| UI wiring | `app.py`, `src/config.py` |
| Docs | This file + updates in `ENHANCEMENTS.md`, `ENHANCEMENT_REPORT.md`, `CODEBASE_GUIDE.md`, `DATA_FLOW.md`, `ARCHITECTURE.md`, `SCOPE_AND_IMPLEMENTATION.md`, `README.md` |

---

## How to Demo for Management (5 minutes)

1. Open the app → **Create account** (or sign in).  
2. Refresh the browser → still signed in.  
3. Type in search → see autocomplete; run a query.  
4. Confirm new item appears in **Search History**; click it to re-run.  
5. Clear the box → Search → results disappear + toast.  
6. Leave idle ~10 minutes (or temporarily lower timeout in config for a short demo) → auto log-out.  

---

## Out of Scope Today (Unchanged)

- REST API, cloud user database, OAuth  
- Cluster / Evaluation **pages** in the sidebar (still pipeline file deliverables)  
- Changing hybrid science (still ~70% semantic / 30% BM25 in UI)  

---

## Related Documents

| Document | Use |
|----------|-----|
| [ENHANCEMENT_REPORT.md](ENHANCEMENT_REPORT.md) | Broader before/after product story |
| [ENHANCEMENTS.md](ENHANCEMENTS.md) | Done checklist + future roadmap |
| [DATA_FLOW.md](DATA_FLOW.md) | Auth, session, search, history flows |
| [CODEBASE_GUIDE.md](CODEBASE_GUIDE.md) | Where each new module lives |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layers including assist + filter engine |
| [../README.md](../README.md) | Product overview for new readers |
