# Proposed Enhancements

Future work and what is already done in the **current** codebase.

---

## Already Implemented

| Item | Notes |
|------|--------|
| Semantic + BM25 + Hybrid | Core brief Tasks 2–3 |
| Filters (category, price, rating) | Task 3 |
| Recommendations + co-occurrence | Task 4 |
| Clustering + UMAP file | Task 4 deliverable via pipeline |
| Evaluation P@k + comparison write-up | Task 5 deliverable via pipeline/reports |
| Login + logout + hashed passwords | Extra UX/security |
| Toast notifications | Extra UX |
| Minimal search-only UI | Matches “simple Streamlit search UI” |
| Empty-query clears old results | Bugfix |

Library modules still present (not emphasized in UI): `query_intent.py`, `search_explanation.py`, `search_with_explanation()`.

---

## Tier 1 — High Impact Next

1. **REST API (FastAPI)** — integrate search into other apps  
2. **pytest suite** — auth, hybrid fusion, filters, empty-query behavior  
3. **RRF fusion** — alternative to min-max score blending  
4. **Pre-filtered indexes** — better filter recall at scale  

---

## Tier 2 — Production

5. Docker + CI  
6. Secrets / env-based config and real user store  
7. Incremental embedding updates  

---

## Tier 3 — Advanced ML

8. Cross-encoder re-rank  
9. Learning-to-rank from clicks  
10. Real behavioral recommendations  

---

## Optional UI Enhancements (only if needed)

- Re-add read-only Clusters / Evaluation **pages** for live demos  
- Optional “advanced” panel for hybrid weight / top-k  

Not required by the written brief if file deliverables exist.

---

## Roadmap Snapshot

```
Now     → Minimal search UI + full offline deliverables
Next    → Tests + API + Docker
Later   → Re-rankers + real data
```
