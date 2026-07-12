# Proposed Enhancements

Future improvements, ordered by impact. Includes what is **already done**.

---

## Already Implemented

| Enhancement | Status | Where |
|-------------|--------|-------|
| Query intent detection | ✅ | `src/query_intent.py` |
| Explainable hybrid search | ✅ | `src/hybrid_search.py`, `search_explanation.py` |
| Category soft-boost from intent | ✅ | `search_with_explanation()` |
| Login + route protection | ✅ | `app.py`, `src/auth.py` |
| Logout in header | ✅ | `render_app_header()` |
| Salted password hashing (PBKDF2) | ✅ | `src/auth.py` |
| Toast notifications (top-right) | ✅ | `src/notifications.py` |

Details: `docs/ENHANCEMENT_REPORT.md`.

---

## Tier 1 — High Impact

### 1. REST API (FastAPI)

Expose `/search`, `/recommendations`, `/health` for integrations.

### 2. Reciprocal Rank Fusion (RRF)

Replace or complement min-max score blending with rank-based fusion.

### 3. Pre-filtering indexes

Metadata-aware retrieval so heavy filters still return full top_k.

### 4. Automated tests (pytest)

Auth verify, hybrid fusion, intent detection, toast queue helpers.

---

## Tier 2 — Production Readiness

### 5. Docker + CI/CD

Reproducible runs and quality gates.

### 6. Environment / secrets config

Move model paths and user stores out of code (Streamlit secrets / `.env`).

### 7. Real user store

SQLite/Postgres users; registration; password reset; lockout.

### 8. Incremental index updates

Add/update products without full re-embed.

---

## Tier 3 — Advanced ML

### 9. Cross-encoder re-ranking

Hybrid top-30 → cross-encoder → final top-10.

### 10. Learning-to-rank

Data-driven weights from clicks.

### 11. Real behavioral recommendations

Replace simulated co-occurrence.

---

## Tier 4 — UX & Observability

### 12. Search analytics

Query logs, CTR, zero-result rate.

### 13. A/B testing of rankers

### 14. Multilingual embeddings

---

## Recommended Roadmap

```
Phase 1  → pytest + secrets-based users + Docker
Phase 2  → FastAPI + RRF + pre-filtering
Phase 3  → Cross-encoder + analytics
Phase 4  → Real catalog / behavior / LTR
```
