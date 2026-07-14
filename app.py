"""Streamlit UI for semantic product search and recommendations."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.auth import is_valid_email, verify_credentials
from src.notifications import (
    inject_toast_styles,
    queue_toast,
    show_pending_toasts,
    toast_error,
    toast_success,
    toast_warning,
)
from src.bm25_search import KeywordSearch
from src.config import (
    CLEAN_CATALOG_PATH,
    DEFAULT_SEMANTIC_WEIGHT,
    DEFAULT_TOP_K,
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

inject_toast_styles()


def inject_app_styles() -> None:
    """Tighter spacing and alignment for the authenticated search UI."""
    st.markdown(
        """
        <style>
        /* Reduce default Streamlit vertical padding */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1.5rem !important;
            max-width: 1100px;
        }

        /* Compact sidebar */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem !important;
        }
        section[data-testid="stSidebar"] h2 {
            font-size: 1.05rem !important;
            margin-bottom: 0.35rem !important;
        }
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.4rem !important;
        }

        /* Header: brand + signed-in on left; logout fixed at extreme top-right */
        .app-header-marker { display: none; }
        .logout-corner-marker { display: none; }
        .app-brand {
            font-size: 1.25rem;
            font-weight: 650;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 2.25rem !important;
            min-height: 2.25rem;
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }
        .app-user-text {
            color: rgba(49, 51, 63, 0.7);
            font-size: 0.9rem;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 2.25rem !important;
            min-height: 2.25rem;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            white-space: nowrap;
        }
        div[data-testid="stHorizontalBlock"]:has(.app-header-marker) {
            align-items: center !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.app-header-marker) [data-testid="stMarkdownContainer"] p,
        div[data-testid="stHorizontalBlock"]:has(.app-header-marker) [data-testid="stMarkdownContainer"] div {
            margin: 0 !important;
        }

        /* Pin Log out to extreme top-right of the window */
        div[data-testid="stHorizontalBlock"]:has(.logout-corner-marker) {
            position: relative !important;
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.logout-corner-marker) > div {
            height: 0 !important;
            min-height: 0 !important;
            overflow: visible !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.logout-corner-marker) > div:last-child {
            position: static !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.logout-corner-marker) [data-testid="stButton"] {
            position: fixed !important;
            top: 0.35rem !important;
            right: 0.5rem !important;
            z-index: 1000001 !important;
            width: auto !important;
            margin: 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.logout-corner-marker) [data-testid="stButton"] > button {
            margin: 0 !important;
            height: 2.25rem !important;
            min-height: 2.25rem !important;
            padding: 0 1rem !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            white-space: nowrap !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
        }
        .app-tagline {
            color: rgba(49, 51, 63, 0.75);
            font-size: 0.95rem;
            margin: 0 0 0.75rem 0;
        }

        /* Tighter main vertical stack */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem;
        }

        /* Search form: input + button joined */
        div[data-testid="stForm"] {
            border: 1px solid rgba(49, 51, 63, 0.15);
            border-radius: 0.5rem;
            padding: 0.75rem 1rem 0.85rem 1rem;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            align-items: flex-end !important;
            gap: 0 !important;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:first-child input {
            border-top-right-radius: 0 !important;
            border-bottom-right-radius: 0 !important;
            border-right: 0 !important;
            height: 2.5rem;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:last-child button {
            border-top-left-radius: 0 !important;
            border-bottom-left-radius: 0 !important;
            height: 2.5rem;
            min-height: 2.5rem;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:last-child {
            margin-top: 0 !important;
        }

        /* Product cards: less padding, price right-aligned */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            margin-bottom: 0.35rem;
        }
        .product-price {
            text-align: right;
            font-size: 1.1rem;
            font-weight: 650;
            margin-top: 0.15rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_auth_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None


def clear_app_state() -> None:
    """Reset search-related session data on logout."""
    for key in ("search_results", "search_query"):
        st.session_state.pop(key, None)


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    clear_app_state()
    # Keep URL clean: http://localhost:8501 (no ?logout=1)
    if "logout" in st.query_params:
        del st.query_params["logout"]
    queue_toast("You have been logged out.", "info")
    st.rerun()


def login_page() -> None:
    """Default route — email/password login gate."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarCollapsedControl"] { display: none; }
        .login-title {
            text-align: center;
            margin-bottom: 0.25rem;
        }
        .login-subtitle {
            text-align: center;
            color: rgba(49, 51, 63, 0.7);
            margin-bottom: 1.5rem;
        }
        .field-error {
            color: #c62828;
            font-size: 0.85rem;
            margin: -0.35rem 0 0.75rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    email_error = st.session_state.get("login_email_error", "")
    password_error = st.session_state.get("login_password_error", "")

    _spacer, center, _spacer2 = st.columns([1, 1.2, 1])
    with center:
        st.markdown('<p class="login-title"><h2>🔍 Sign in</h2></p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="login-subtitle">Semantic Product Search Engine</p>',
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="example@gmail.com")
            if email_error:
                st.markdown(f'<p class="field-error">{email_error}</p>', unsafe_allow_html=True)

            password = st.text_input("Password", type="password", placeholder="Enter your password")
            if password_error:
                st.markdown(f'<p class="field-error">{password_error}</p>', unsafe_allow_html=True)

            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)

        if submitted:
            email_value = email.strip()
            st.session_state.login_email_error = ""
            st.session_state.login_password_error = ""
            has_field_error = False

            if not email_value:
                st.session_state.login_email_error = "Email is required."
                has_field_error = True
            elif not is_valid_email(email_value):
                st.session_state.login_email_error = "Please enter a valid email address."
                has_field_error = True

            if not password:
                st.session_state.login_password_error = "Password is required."
                has_field_error = True

            if has_field_error:
                st.rerun()

            if verify_credentials(email_value, password):
                st.session_state.authenticated = True
                st.session_state.user_email = email_value.lower()
                st.session_state.login_email_error = ""
                st.session_state.login_password_error = ""
                queue_toast(f"Welcome back, {email_value.lower()}!", "success")
                st.rerun()

            # Auth failed after fields are filled — toast on submit is OK
            st.session_state.login_email_error = ""
            st.session_state.login_password_error = ""
            toast_error("Invalid email or password.")

        st.caption("Enter your registered email and password to continue.")


def render_app_header() -> None:
    """Brand + signed-in text in content; Log out fixed at extreme top-right."""
    if "logout" in st.query_params:
        del st.query_params["logout"]

    email = st.session_state.user_email or ""

    # Invisible layout row — button is CSS-fixed to top-right corner
    _spacer, logout_col = st.columns([20, 1])
    with logout_col:
        st.markdown('<span class="logout-corner-marker"></span>', unsafe_allow_html=True)
        if st.button("Log out", type="secondary", key="header_logout"):
            logout()

    brand_col, user_col = st.columns([3, 2.5], vertical_alignment="center")
    with brand_col:
        st.markdown(
            '<span class="app-header-marker"></span>'
            '<div class="app-brand">🔍 Semantic Product Search</div>',
            unsafe_allow_html=True,
        )
    with user_col:
        st.markdown(
            f'<div class="app-user-text">Signed in as&nbsp;<strong>{email}</strong></div>',
            unsafe_allow_html=True,
        )
    st.divider()

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
    """Display a simple product card (title, category, rating, description, price)."""
    with st.container(border=True):
        cols = st.columns([5, 1], vertical_alignment="top")
        with cols[0]:
            st.markdown(f"**#{rank} · {result.title}**")
            st.caption(f"{result.category} · ⭐ {result.rating:.1f}")
            desc = result.description
            st.caption(desc[:180] + ("..." if len(desc) > 180 else ""))
        with cols[1]:
            st.markdown(
                f'<p class="product-price">${result.price:.2f}</p>',
                unsafe_allow_html=True,
            )


def search_page(
    vector: VectorSearch,
    keyword: KeywordSearch,
    hybrid: HybridSearch,
    catalog: pd.DataFrame,
) -> None:
    # Brand already in header — keep a short tagline only (no duplicate title)
    st.markdown(
        '<p class="app-tagline">Search by <strong>meaning</strong>, not just keywords. '
        "Try: <em>warm jacket for winter trip</em></p>",
        unsafe_allow_html=True,
    )

    price_floor = float(catalog["price"].min())
    price_ceil = float(catalog["price"].max())

    with st.sidebar:
        st.markdown("**Search**")
        mode = st.radio(
            "Mode",
            ["Hybrid", "Semantic", "BM25"],
            index=0,
            help="Hybrid blends meaning + keywords. Semantic = meaning only. BM25 = keywords only.",
        )

        st.markdown("---")
        st.markdown("**Filters**")
        categories = ["All"] + sorted(catalog["category"].unique().tolist())
        category = st.selectbox("Category", categories)
        price_min, price_max = st.slider(
            "Price range ($)", price_floor, price_ceil, (price_floor, price_ceil)
        )
        min_rating = st.slider("Minimum rating", 0.0, 5.0, 0.0, 0.5)

    # Fixed defaults (weights justified in reports; keeps UI minimal)
    top_k = DEFAULT_TOP_K
    sem_w = DEFAULT_SEMANTIC_WEIGHT

    with st.form("search_form", clear_on_submit=False):
        input_col, btn_col = st.columns([8, 1], gap="small", vertical_alignment="bottom")
        with input_col:
            query = st.text_input(
                "Search query",
                placeholder="e.g. cozy bedding for better sleep",
                label_visibility="collapsed",
                key="search_query_input",
            )
        with btn_col:
            submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

    # Always use the value submitted from the input (including empty string)
    submitted_query = (query or "").strip()

    if submitted and submitted_query:
        cat_filter = None if category == "All" else category
        filters = dict(
            category=cat_filter,
            min_price=price_min if price_min > price_floor else None,
            max_price=price_max if price_max < price_ceil else None,
            min_rating=min_rating if min_rating > 0 else None,
        )
        with st.spinner("Searching…"):
            results = run_search(
                submitted_query, mode, top_k, sem_w, filters, vector, keyword, hybrid
            )
        st.session_state["search_results"] = results
        st.session_state["search_query"] = submitted_query
        if results:
            toast_success(f"Found {len(results)} result(s) for your search.")
        else:
            toast_warning("No products matched your query and filters.")
    elif submitted and not submitted_query:
        # Empty search must clear previous results — do not keep old query/results
        for key in ("search_results", "search_query"):
            st.session_state.pop(key, None)
        toast_warning("Please enter a search query.")

    results: list[SearchResult] = st.session_state.get("search_results", [])

    if not results:
        st.caption("Enter a query and click **Search**. Filters apply when you search.")
        return

    if "search_query" in st.session_state:
        st.caption(f"Showing results for: *{st.session_state['search_query']}*")

    st.markdown(f"**Results ({len(results)})**")
    for i, r in enumerate(results, 1):
        render_product_card(r, i)

    st.markdown("---")
    st.markdown("**Similar Products**")
    anchor_id = st.selectbox(
        "Pick a result to see recommendations",
        options=[r.product_id for r in results],
        format_func=lambda pid: next(r.title for r in results if r.product_id == pid),
    )
    if anchor_id:
        recs = get_recommendations(int(anchor_id))
        for rec in recs:
            with st.container(border=True):
                left, right = st.columns([5, 1], vertical_alignment="center")
                with left:
                    st.markdown(f"**{rec['title']}**")
                    st.caption(f"{rec['category']} · ⭐ {rec['rating']:.1f}")
                with right:
                    st.markdown(
                        f'<p class="product-price">${rec["price"]:.2f}</p>',
                        unsafe_allow_html=True,
                    )


def main() -> None:
    init_auth_state()
    # Always prefer a clean base URL (no ?logout=1)
    if "logout" in st.query_params:
        del st.query_params["logout"]
    show_pending_toasts()

    if not st.session_state.authenticated:
        login_page()
        return

    inject_app_styles()
    render_app_header()

    try:
        vector, keyword, hybrid, recommender, catalog = load_search_stack()
    except Exception as exc:
        toast_error("Failed to load search engine.")
        st.error(f"Failed to load search engine: {exc}")
        st.code("python scripts/run_pipeline.py")
        return

    search_page(vector, keyword, hybrid, catalog)


if __name__ == "__main__":
    main()
