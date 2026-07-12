# Enhancement Report — Current Product State

**Updated:** July 2026  

This report summarizes major changes from the original open search demo to the **current** login-gated, minimal search UI — while keeping all project-brief deliverables.

---

## Executive Summary

| Area | Outcome |
|------|---------|
| Core AI search | Semantic + BM25 + Hybrid unchanged in spirit |
| Project deliverables | Catalog, FAISS, recs, cluster image, eval table still produced |
| UI | Simplified to **login + search** only |
| Security / UX | Hashed passwords, toasts, empty-query fix |

---

## Part A — UI Alignment With the Brief

### Before (busy demo UI)

- Sidebar pages: Search, Clusters, Evaluation  
- Extra controls: top-k, semantic weight, smart-search toggles  
- Result cards: Score metric + “Why this result?” expanders  
- Intent info banners  

### After (minimal UI)

- Sidebar: **Mode** + **Filters** only  
- Main: query, product cards, similar products  
- Cards: title, category, rating, description, price  
- Clusters & evaluation: **files** from `run_pipeline.py`, not menu items  

### Reasoning

Task 5 asks for a *simple Streamlit search UI with filters and product cards*.  
Task 4/5 cluster plot and evaluation table are **deliverables**, satisfied by:

- `visuals/cluster_visualization.png`  
- `reports/evaluation_results.csv` (+ comparison markdown)  

---

## Part B — Authentication & Toasts (Still Present)

| Feature | Behavior |
|---------|----------|
| Default route | Login |
| Passwords | PBKDF2 `salt:hash`; never shown on UI |
| Logout | Header button; clears session |
| Toasts | Top-right feedback for auth and search |

---

## Part C — Search Behavior Fixes

| Issue | Fix |
|-------|-----|
| Empty input still showed previous results | Clear `search_results` / `search_query` on empty submit |

---

## Before / After Matrix

| Capability | Original busy UI | Current |
|------------|------------------|---------|
| Hybrid / Semantic / BM25 | ✅ | ✅ |
| Filters | ✅ | ✅ |
| Recommendations | ✅ | ✅ |
| Cluster **page** | ✅ | ❌ (file only) |
| Evaluation **page** | ✅ | ❌ (file only) |
| Score / explanation UI | ✅ | ❌ |
| Login + toasts | ✅ (later) | ✅ |
| Pipeline cluster + eval | ✅ | ✅ |

---

## How Reviewers Should Inspect Deliverables

```bash
python scripts/run_pipeline.py
streamlit run app.py          # demo search UX
# then open:
#   visuals/cluster_visualization.png
#   reports/evaluation_results.csv
#   reports/search_comparison.md
```

---

## Conclusion

The product now matches the **written brief’s UI expectation** (clean search demo) without dropping **ML deliverables**. Clustering and evaluation remain first-class outputs of the offline pipeline and documentation pack.
