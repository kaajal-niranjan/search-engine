# Search Comparison Analysis

## Executive Summary

On 15 realistic e-commerce queries over an 800-product catalog, **semantic search** achieved the highest mean Precision@5 (0.92) and Precision@10 (0.85). **Hybrid search** (70% semantic / 30% BM25) matched semantic at P@10 and was close at P@5 (0.91). **BM25** lagged on intent-heavy queries (P@5: 0.79, P@10: 0.74).

| Method   | Mean P@5 | Mean P@10 |
|----------|----------|-----------|
| BM25     | 0.787    | 0.740     |
| Semantic | 0.920    | 0.847     |
| Hybrid   | 0.907    | 0.847     |

## Where Semantic Search Wins

### 1. Natural-language intent without product vocabulary

**Query:** `warm jacket for winter trip`

Users describe needs, not SKUs. Embeddings map "warm jacket for winter trip" near products titled *Men's Winter Puffer Jacket*, *Thermal Base Layer Top*, and *Wool Blend Sweater* even when the exact phrase "warm jacket" is absent.

### 2. Conceptual / vague queries

**Query:** `something cozy for better sleep`

Semantic retrieval connects "cozy" and "sleep" to weighted blankets, memory foam pillows, herbal sleep tea, and essential oil diffusers across categories.

### 3. Multi-attribute fitness intent

**Query:** `home workout equipment small apartment`

BM25 returned **0 relevant hits** (no document contains all tokens). Semantic search ranked dumbbells, resistance bands, and yoga mats highly because embeddings encode "home workout" and "apartment-friendly" context from descriptions.

### 4. Cross-field relevance

**Query:** `anti aging night skincare`

Semantic models leverage full `search_text` (title + description + category), surfacing retinol night cream and serums even when query terms are spread across fields.

## Where BM25 Wins (or ties)

### 1. Exact SKU / model-number queries

**Query:** `USB-C 65W laptop charger`

Rare tokens (`USB-C`, `65W`) are strong BM25 signals. Both BM25 and semantic achieve moderate P@5 (0.6) because the catalog has many charger variants; exact match disambiguation benefits from keyword weighting in hybrid mode.

### 2. Precise keyword overlap

**Query:** `beginner learn python coding`

When query terms literally appear in titles (*Beginner Python Programming Guide*), BM25 is fast and interpretable with no model inference cost.

### 3. Low-latency cold start

BM25 requires no GPU/CPU-heavy encoding step — useful for autocomplete and exact-match fallbacks.

## Hybrid Search: Production Recommendation

Default weights **0.7 semantic + 0.3 BM25** because:

1. **Recall:** Semantic retrieval captures paraphrases and intent (primary user pain point in the brief).
2. **Precision rescue:** BM25 boosts listings where rare tokens (brand, wattage, ISBN) must match exactly.
3. **Stability:** Normalized score blending prevents either signal from dominating when score scales differ.

Observed: hybrid improved `gift for toddler birthday party` from P@5 0.2 (BM25) / 0.4 (semantic) to **0.6** by combining both candidate pools.

## When Semantic Search Can Hurt

- **Rare proper nouns** not seen during pre-training
- **Very short queries** (1–2 chars) with ambiguous embeddings
- **Numerical constraints** — price/rating filters are applied post-retrieval; embeddings do not encode "$50 max" without explicit filters (implemented in this system)
- **Adversarial / off-domain queries** — may return semantically "close" but commercially irrelevant items

## Engineering Notes

- Embeddings cached in `embeddings/product_embeddings.npy` — rebuild only when catalog changes.
- FAISS `IndexFlatIP` on L2-normalized vectors = cosine similarity; exact search suitable for &lt;1M products.
- Batch size 64 balances memory and throughput on CPU.

## Conclusion

Deploy **hybrid search** as the default production mode with semantic-heavy weighting. Keep **BM25** as a baseline, fallback, and A/B comparison arm. Use **structured filters** (category, price, rating) alongside vector retrieval for commerce-grade relevance.
