"""Streamlit UI for semantic product search and recommendations."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.bm25_search import KeywordSearch
from src.clustering import ProductClusterer
from src.config import (
    CLEAN_CATALOG_PATH,
    CLUSTER_PLOT_PATH,
    DEFAULT_BM25_WEIGHT,
    DEFAULT_SEMANTIC_WEIGHT,
    EVALUATION_CSV_PATH,
)
from src.embedding_generator import EmbeddingGenerator
from src.hybrid_search import HybridSearch
from src.recommender import ProductRecommender
from src.vector_search import SearchResult, VectorSearch

st.set_page_config(
    page_title="Semantic Product Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner="Loading search engine…")
def load_search_stack() -> tuple[VectorSearch, KeywordSearch, HybridSearch, ProductRecommender, pd.DataFrame]:
    """Initialize search components once (cached across reruns)."""
    generator = EmbeddingGenerator()
    if not generator.embeddings_exist():
        from src.preprocessing import run_preprocessing

        run_preprocessing()
        generator.generate()

    vector = VectorSearch(embedding_generator=generator)
    vector.build_index()
    keyword = KeywordSearch()
    keyword._load_and_index()  # pre-build BM25 index at startup
    hybrid = HybridSearch(vector_search=vector, keyword_search=keyword)
    recommender = ProductRecommender(embedding_generator=generator)
    catalog = pd.read_csv(CLEAN_CATALOG_PATH)

    generator.warmup()  # JIT-compile model before first user query
    return vector, keyword, hybrid, recommender, catalog


@st.cache_data(show_spinner=False)
def get_recommendations(anchor_id: int) -> list[dict[str, Any]]:
    """Cache recommendations per product."""
    _, _, _, recommender, _ = load_search_stack()
    return [
        {
            "product_id": r.product_id,
            "score": r.score,
            "title": r.title,
            "category": r.category,
            "price": r.price,
            "rating": r.rating,
            "reason": r.reason,
        }
        for r in recommender.recommend(anchor_id, top_n=5)
    ]


def run_search(
    query: str,
    mode: str,
    top_k: int,
    sem_w: float,
    filters: dict,
    vector: VectorSearch,
    keyword: KeywordSearch,
    hybrid: HybridSearch,
) -> list[SearchResult]:
    """Execute search for the selected mode."""
    if mode == "Semantic":
        return vector.search(query, top_k=top_k, **filters)
    if mode == "BM25":
        return keyword.search(query, top_k=top_k, **filters)

    hybrid.semantic_weight = sem_w
    hybrid.bm25_weight = 1.0 - sem_w
    return hybrid.search(query, top_k=top_k, **filters)


def render_product_card(result: SearchResult, rank: int) -> None:
    """Display a single search result card."""
    with st.container(border=True):
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**#{rank} · {result.title}**")
            st.caption(f"{result.category} · ⭐ {result.rating:.1f}")
            desc = result.description
            st.write(desc[:200] + ("..." if len(desc) > 200 else ""))
        with cols[1]:
            st.metric("Price", f"${result.price:.2f}")
            st.metric("Score", f"{result.score:.3f}")


def search_page(
    vector: VectorSearch,
    keyword: KeywordSearch,
    hybrid: HybridSearch,
    catalog: pd.DataFrame,
) -> None:
    st.title("🔍 Semantic Product Search")
    st.markdown("Search by **meaning**, not just keywords. Try: *warm jacket for winter trip*")

    price_floor = float(catalog["price"].min())
    price_ceil = float(catalog["price"].max())

    with st.sidebar:
        st.header("Search Settings")
        mode = st.radio("Search mode", ["Hybrid", "Semantic", "BM25"], index=0)
        top_k = st.slider("Results (top-k)", 3, 20, 10)
        sem_w = st.slider("Semantic weight", 0.0, 1.0, DEFAULT_SEMANTIC_WEIGHT, 0.05)
        st.caption(f"BM25 weight: {1.0 - sem_w:.2f}")

        st.divider()
        st.header("Filters")
        categories = ["All"] + sorted(catalog["category"].unique().tolist())
        category = st.selectbox("Category", categories)
        price_min, price_max = st.slider(
            "Price range ($)", price_floor, price_ceil, (price_floor, price_ceil)
        )
        min_rating = st.slider("Minimum rating", 0.0, 5.0, 0.0, 0.5)

    st.markdown(
        """
        <style>
        /* Inline search: input and button on one row, visually joined */
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            align-items: flex-end;
            gap: 0 !important;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:first-child input {
            border-top-right-radius: 0 !important;
            border-bottom-right-radius: 0 !important;
            border-right: 0 !important;
            height: 2.75rem;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:last-child button {
            border-top-left-radius: 0 !important;
            border-bottom-left-radius: 0 !important;
            height: 2.75rem;
            min-height: 2.75rem;
            padding-left: 1.25rem;
            padding-right: 1.25rem;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:last-child {
            margin-top: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.form("search_form", clear_on_submit=False):
        st.markdown("**Search query**")
        input_col, btn_col = st.columns([8, 1], gap="small", vertical_alignment="bottom")
        with input_col:
            query = st.text_input(
                "Search query",
                placeholder="e.g. cozy bedding for better sleep",
                label_visibility="collapsed",
            )
        with btn_col:
            submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

    if submitted and query.strip():
        cat_filter = None if category == "All" else category
        filters = dict(
            category=cat_filter,
            min_price=price_min if price_min > price_floor else None,
            max_price=price_max if price_max < price_ceil else None,
            min_rating=min_rating if min_rating > 0 else None,
        )
        with st.spinner("Searching…"):
            results = run_search(
                query.strip(), mode, top_k, sem_w, filters, vector, keyword, hybrid
            )
        st.session_state["search_results"] = results
        st.session_state["search_query"] = query.strip()

    results: list[SearchResult] = st.session_state.get("search_results", [])
    if not results:
        st.info("Enter a query and click **Search** (filters apply on submit).")
        return

    if "search_query" in st.session_state:
        st.caption(f"Showing results for: *{st.session_state['search_query']}*")

    st.subheader(f"Results ({len(results)})")
    for i, r in enumerate(results, 1):
        render_product_card(r, i)

    st.divider()
    st.subheader("Similar Products")
    anchor_id = st.selectbox(
        "Pick a result to see recommendations",
        options=[r.product_id for r in results],
        format_func=lambda pid: next(r.title for r in results if r.product_id == pid),
    )
    if anchor_id:
        recs = get_recommendations(int(anchor_id))
        for rec in recs:
            with st.container(border=True):
                st.markdown(f"**{rec['title']}** · {rec['category']}")
                st.caption(f"Score: {rec['score']:.3f} · {rec['reason']}")
                st.write(f"${rec['price']:.2f} · ⭐ {rec['rating']:.1f}")


def clusters_page() -> None:
    st.title("📊 Embedding Clusters")
    st.markdown("UMAP projection of product embeddings colored by KMeans cluster.")

    if CLUSTER_PLOT_PATH.exists():
        st.image(str(CLUSTER_PLOT_PATH), use_container_width=True)
    else:
        st.warning("Cluster plot not found. Run `python scripts/run_pipeline.py` first.")
        if st.button("Generate clusters now"):
            with st.spinner("Generating clusters…"):
                clusterer = ProductClusterer()
                clusterer.fit_predict()
                clusterer.visualize()
            st.rerun()


def evaluation_page() -> None:
    st.title("📈 Search Evaluation")
    st.markdown("Precision@5 and Precision@10 comparing BM25, semantic, and hybrid search.")

    if EVALUATION_CSV_PATH.exists():
        df = pd.read_csv(EVALUATION_CSV_PATH)
        st.dataframe(df, use_container_width=True)

        summary = pd.DataFrame(
            {
                "Method": ["BM25", "Semantic", "Hybrid"],
                "Mean P@5": [df["bm25_p@5"].mean(), df["semantic_p@5"].mean(), df["hybrid_p@5"].mean()],
                "Mean P@10": [
                    df["bm25_p@10"].mean(),
                    df["semantic_p@10"].mean(),
                    df["hybrid_p@10"].mean(),
                ],
            }
        )
        st.subheader("Summary")
        st.table(summary)

        st.subheader("When does each method win?")
        st.markdown(
            """
            | Scenario | Best method | Example |
            |----------|-------------|---------|
            | Vague intent / natural language | **Semantic** | "warm jacket for winter trip" |
            | Exact SKU / model numbers | **BM25** | "USB-C 65W laptop charger" |
            | Mixed queries | **Hybrid** | "4K television streaming movies" |
            """
        )
    else:
        st.warning("Evaluation not run yet. Execute `python scripts/run_pipeline.py`.")


def main() -> None:
    page = st.sidebar.radio(
        "Navigation",
        ["Search", "Clusters", "Evaluation"],
        label_visibility="collapsed",
    )

    if page == "Clusters":
        clusters_page()
        return

    if page == "Evaluation":
        evaluation_page()
        return

    try:
        vector, keyword, hybrid, recommender, catalog = load_search_stack()
    except Exception as exc:
        st.error(f"Failed to load search engine: {exc}")
        st.code("python scripts/run_pipeline.py")
        return

    search_page(vector, keyword, hybrid, catalog)


if __name__ == "__main__":
    main()
