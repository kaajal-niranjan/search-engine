"""Streamlit UI for semantic product search and recommendations."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.auth import is_valid_email, register_user, verify_credentials
from src.browser_cookies import (
    clear_session_cookie,
    clear_session_id_from_browser,
    get_cookie_manager,
    inject_session_restore_bridge,
    persist_session_id_to_browser,
    read_session_cookie,
    write_session_cookie,
)
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
    SEARCH_HISTORY_MAX_PER_USER,
)
from src.embedding_generator import EmbeddingGenerator
from src.hybrid_search import HybridSearch
from src.recommender import ProductRecommender
from src.search_assist import (
    add_search_history,
    clear_search_history,
    get_search_history,
)
from src.search_autocomplete import render_search_autocomplete
from src.search_history_list import render_search_history_list
from src.session import (
    IDLE_TIMEOUT_SECONDS,
    create_session,
    delete_session,
    get_session,
    touch_session,
    validate_session_for_restore,
)
from src.vector_search import SearchResult, VectorSearch

import streamlit.components.v1 as components
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
        /* Align autocomplete selectbox with Search button */
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:first-child [data-baseweb="select"] > div {
            min-height: 2.5rem;
            border-top-right-radius: 0 !important;
            border-bottom-right-radius: 0 !important;
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
        /* Hide CookieManager helper iframe (session persistence) */
        iframe[title="extra_streamlit_components.CookieManager.cookie_manager"] {
            display: none !important;
            height: 0 !important;
            width: 0 !important;
            position: absolute !important;
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
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "login"  # "login" | "register"


def clear_app_state() -> None:
    """Reset search-related session data on logout."""
    for key in ("search_results", "search_query"):
        st.session_state.pop(key, None)


def establish_login(email: str, cookie_manager) -> None:
    """Mark user authenticated and persist a server-backed browser session."""
    normalized = email.strip().lower()
    session = create_session(normalized)
    write_session_cookie(cookie_manager, session.session_id)
    persist_session_id_to_browser(session.session_id)
    st.session_state.authenticated = True
    st.session_state.user_email = normalized
    st.session_state.session_id = session.session_id


def logout(cookie_manager=None, *, reason: str = "manual") -> None:
    """Clear in-memory auth, server session, and browser session id."""
    session_id = st.session_state.get("session_id")
    if not session_id:
        # Fall back to cookie / query bridge if state was lost
        try:
            session_id = read_session_cookie(cookie_manager) if cookie_manager else None
        except Exception:
            session_id = None

    delete_session(session_id)
    if cookie_manager is not None:
        clear_session_cookie(cookie_manager)
    clear_session_id_from_browser()

    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.session_id = None
    clear_app_state()
    for key in ("logout", "idle_logout", "sps_sid"):
        if key in st.query_params:
            del st.query_params[key]
    if reason == "idle":
        queue_toast("You were logged out due to 1 minute of inactivity.", "warning")
    else:
        queue_toast("You have been logged out.", "info")
    st.rerun()


def inject_idle_logout_watchdog() -> None:
    """
    Browser-side idle signal (best effort).

    Streamlit HTML components run in a sandboxed iframe and often cannot
    navigate the parent page, so this alone is not enough — see
    idle_session_watchdog() for the reliable server-side logout.
    """
    idle_ms = int(IDLE_TIMEOUT_SECONDS * 1000)
    components.html(
        f"""
        <script>
        (function () {{
          const IDLE_MS = {idle_ms};
          const FLAG = 'idle_logout';
          let lastActivity = Date.now();
          const bump = function () {{
            lastActivity = Date.now();
            try {{ window.parent.localStorage.setItem('sps_last_activity', String(lastActivity)); }} catch (e) {{}}
          }};
          const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click', 'wheel'];

          const targetDocs = [];
          try {{ targetDocs.push(window.parent.document); }} catch (e) {{}}
          targetDocs.push(document);

          targetDocs.forEach(function (doc) {{
            events.forEach(function (name) {{
              try {{ doc.addEventListener(name, bump, true); }} catch (e) {{}}
            }});
          }});
          try {{ window.parent.addEventListener('focus', bump); }} catch (e) {{}}
          bump();

          setInterval(function () {{
            if (Date.now() - lastActivity < IDLE_MS) return;
            try {{
              window.parent.localStorage.removeItem('sps_sid');
              window.parent.localStorage.setItem('sps_idle_logout', '1');
            }} catch (e) {{}}
            try {{
              const url = new URL(window.top.location.href);
              if (url.searchParams.get(FLAG) === '1') return;
              url.searchParams.set(FLAG, '1');
              window.top.location.replace(url.toString());
            }} catch (err) {{
              try {{
                const url = new URL(window.parent.location.href);
                url.searchParams.set(FLAG, '1');
                window.parent.location.replace(url.toString());
              }} catch (err2) {{}}
            }}
          }}, 1000);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


@st.fragment(run_every=timedelta(seconds=5))
def idle_session_watchdog() -> None:
    """
    Reliable idle auto-logout: runs every 5s while the dashboard is open.

    Any Streamlit action (search, click, filter change) refreshes last_activity
    via sync_auth_session → touch_session. If no action happens for 1 minute,
    this fragment logs the user out.
    """
    if not st.session_state.get("authenticated"):
        return
    sid = st.session_state.get("session_id")
    if not sid:
        return
    session = get_session(sid)
    if session is None or session.is_idle_expired:
        cookie_manager = get_cookie_manager()
        logout(cookie_manager, reason="idle")


def sync_auth_session(cookie_manager) -> None:
    """
    Restore auth after refresh from cookie / localStorage bridge,
    keep server-side last_activity fresh, and honor idle logout.
    """
    st.session_state._sps_suppress_login = False

    if st.query_params.get("idle_logout") == "1":
        logout(cookie_manager, reason="idle")

    session_id = read_session_cookie(cookie_manager)
    if "sps_sid" in st.query_params:
        # Clean the localStorage bridge param from the URL after reading it
        try:
            del st.query_params["sps_sid"]
        except Exception:
            pass

    # Already signed in this Streamlit session — keep the same session id alive
    if st.session_state.authenticated and st.session_state.user_email:
        sid = st.session_state.get("session_id") or session_id
        if sid:
            touched = touch_session(sid)
            if touched is None:
                st.session_state.session_id = None
                logout(cookie_manager, reason="idle")
                return
            st.session_state.session_id = touched.session_id
            write_session_cookie(cookie_manager, touched.session_id)
            persist_session_id_to_browser(touched.session_id)
        else:
            # Recover a session id if cookie was missing mid-session
            created = create_session(st.session_state.user_email)
            st.session_state.session_id = created.session_id
            write_session_cookie(cookie_manager, created.session_id)
            persist_session_id_to_browser(created.session_id)
        return

    # Fresh browser load — restore from server-backed session id
    session = validate_session_for_restore(session_id)
    if session is not None:
        touched = touch_session(session.session_id) or session
        st.session_state.authenticated = True
        st.session_state.user_email = touched.email
        st.session_state.session_id = touched.session_id
        write_session_cookie(cookie_manager, touched.session_id)
        persist_session_id_to_browser(touched.session_id)
        return

    # Invalid / unknown id — clear browser copies, but don't crash
    if session_id:
        delete_session(session_id)
        clear_session_cookie(cookie_manager)
        clear_session_id_from_browser()

    # Allow CookieManager / localStorage bridge one turn before showing sign-in
    if not st.session_state.get("_sps_cookie_wait_done"):
        st.session_state._sps_cookie_wait_done = True
        st.session_state._sps_suppress_login = True


def _inject_auth_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarCollapsedControl"] { display: none; }
        /* Hide CookieManager helper iframe (session persistence) */
        iframe[title="extra_streamlit_components.CookieManager.cookie_manager"] {
            display: none !important;
            height: 0 !important;
            width: 0 !important;
            position: absolute !important;
        }
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
        .auth-switch {
            text-align: center;
            margin-top: 1rem;
            color: rgba(49, 51, 63, 0.75);
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _switch_auth_view(view: str) -> None:
    st.session_state.auth_view = view
    for key in (
        "login_email_error",
        "login_password_error",
        "register_email_error",
        "register_password_error",
        "register_confirm_error",
    ):
        st.session_state.pop(key, None)
    st.rerun()


def login_form(cookie_manager) -> None:
    """Email/password sign-in against the local credential store."""
    email_error = st.session_state.get("login_email_error", "")
    password_error = st.session_state.get("login_password_error", "")

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
            st.session_state.login_email_error = ""
            st.session_state.login_password_error = ""
            establish_login(email_value, cookie_manager)
            queue_toast(f"Welcome back, {email_value.lower()}!", "success")
            st.rerun()

        st.session_state.login_email_error = ""
        st.session_state.login_password_error = ""
        toast_error("Invalid email or password.")

    st.caption("Sign in with the email and password you registered.")
    st.markdown('<p class="auth-switch">Don\'t have an account?</p>', unsafe_allow_html=True)
    if st.button("Create an account", use_container_width=True, key="goto_register"):
        _switch_auth_view("register")


def register_form() -> None:
    """Create a new account and save credentials to the local store."""
    email_error = st.session_state.get("register_email_error", "")
    password_error = st.session_state.get("register_password_error", "")
    confirm_error = st.session_state.get("register_confirm_error", "")

    st.markdown('<p class="login-title"><h2>🔍 Create account</h2></p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="login-subtitle">Register to use Semantic Product Search</p>',
        unsafe_allow_html=True,
    )

    with st.form("register_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="example@gmail.com", key="register_email")
        if email_error:
            st.markdown(f'<p class="field-error">{email_error}</p>', unsafe_allow_html=True)

        password = st.text_input(
            "Password",
            type="password",
            placeholder="At least 6 characters",
            key="register_password",
        )
        if password_error:
            st.markdown(f'<p class="field-error">{password_error}</p>', unsafe_allow_html=True)

        confirm = st.text_input(
            "Confirm password",
            type="password",
            placeholder="Re-enter your password",
            key="register_confirm",
        )
        if confirm_error:
            st.markdown(f'<p class="field-error">{confirm_error}</p>', unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "Create account", type="primary", use_container_width=True
        )

    if submitted:
        email_value = email.strip()
        st.session_state.register_email_error = ""
        st.session_state.register_password_error = ""
        st.session_state.register_confirm_error = ""
        has_field_error = False

        if not email_value:
            st.session_state.register_email_error = "Email is required."
            has_field_error = True
        elif not is_valid_email(email_value):
            st.session_state.register_email_error = "Please enter a valid email address."
            has_field_error = True

        if not password:
            st.session_state.register_password_error = "Password is required."
            has_field_error = True
        elif len(password) < 6:
            st.session_state.register_password_error = (
                "Password must be at least 6 characters."
            )
            has_field_error = True

        if not confirm:
            st.session_state.register_confirm_error = "Please confirm your password."
            has_field_error = True
        elif password and confirm != password:
            st.session_state.register_confirm_error = "Passwords do not match."
            has_field_error = True

        if has_field_error:
            st.rerun()

        ok, message = register_user(email_value, password)
        if ok:
            st.session_state.auth_view = "login"
            for key in (
                "register_email_error",
                "register_password_error",
                "register_confirm_error",
            ):
                st.session_state.pop(key, None)
            queue_toast(message, "success")
            st.rerun()

        # Duplicate email or store error — show inline + toast after rerun
        st.session_state.register_email_error = message
        queue_toast(message, "error")
        st.rerun()

    st.caption("Your account is saved locally. Passwords are stored as salted hashes only.")
    st.markdown('<p class="auth-switch">Already have an account?</p>', unsafe_allow_html=True)
    if st.button("Back to sign in", use_container_width=True, key="goto_login"):
        _switch_auth_view("login")


def login_page(cookie_manager) -> None:
    """Auth gate — Sign in or Create account (local credential store)."""
    _inject_auth_styles()

    _spacer, center, _spacer2 = st.columns([1, 1.2, 1])
    with center:
        if st.session_state.auth_view == "register":
            register_form()
        else:
            login_form(cookie_manager)


def render_app_header(cookie_manager) -> None:
    """Brand + signed-in text in content; Log out fixed at extreme top-right."""
    if "logout" in st.query_params:
        del st.query_params["logout"]

    email = st.session_state.user_email or ""

    # Invisible layout row — button is CSS-fixed to top-right corner
    _spacer, logout_col = st.columns([20, 1])
    with logout_col:
        st.markdown('<span class="logout-corner-marker"></span>', unsafe_allow_html=True)
        if st.button("Log out", type="secondary", key="header_logout"):
            logout(cookie_manager, reason="manual")

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

    user_email = st.session_state.user_email or ""
    price_floor = float(catalog["price"].min())
    price_ceil = float(catalog["price"].max())
    catalog_titles = catalog["title"].dropna().astype(str).tolist()

    # Apply a history click from the sidebar before widgets render
    pending_query = st.session_state.pop("_pending_search", None)
    if pending_query is not None:
        st.session_state["search_query_input"] = pending_query
        st.session_state["_run_pending_search"] = True

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

        st.markdown("---")
        st.markdown("**Search History**")
        history = get_search_history(user_email, limit=SEARCH_HISTORY_MAX_PER_USER)
        if history:
            hist_click = render_search_history_list(history, key="sidebar_search_history")
            if isinstance(hist_click, dict):
                nonce = hist_click.get("nonce")
                if nonce != st.session_state.get("_last_hist_nonce"):
                    st.session_state["_last_hist_nonce"] = nonce
                    past_q = str(hist_click.get("query") or "").strip()
                    if past_q:
                        st.session_state["_pending_search"] = past_q
                        st.rerun()
            if st.button("Clear history", key="clear_search_history"):
                clear_search_history(user_email)
                queue_toast("Search history cleared.", "success")
                st.rerun()
        else:
            st.caption("Your recent searches will appear here.")

    # Fixed defaults (weights justified in reports; keeps UI minimal)
    top_k = DEFAULT_TOP_K
    sem_w = DEFAULT_SEMANTIC_WEIGHT

    current_query = str(st.session_state.get("search_query_input") or "")
    
    # Render autocomplete component
    ac_result = render_search_autocomplete(
        history=get_search_history(user_email, limit=10),
        product_titles=catalog_titles,
        current_query=current_query,
        placeholder="Click for recent searches, or type to match products…",
    )

    run_pending = st.session_state.pop("_run_pending_search", False)
    submitted_query = str(st.session_state.get("search_query_input") or "").strip()

    # Component returns a value when Search / Enter / suggestion is chosen
    if isinstance(ac_result, dict) and ac_result.get("action") == "search":
        nonce = ac_result.get("nonce")
        if nonce != st.session_state.get("_last_ac_nonce"):
            st.session_state["_last_ac_nonce"] = nonce
            # Always trust the current box value (including empty → clear prior results)
            submitted_query = str(ac_result.get("query") or "").strip()
            st.session_state["search_query_input"] = submitted_query
            run_pending = True

    should_search = run_pending
    submitted = run_pending

    if should_search:
        if submitted_query:
            # Non-empty search - execute normally
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
            add_search_history(user_email, submitted_query)
            if results:
                queue_toast(f"Found {len(results)} result(s) for your search.", "success")
            else:
                queue_toast("No products matched your query and filters.", "warning")
            # Rerun so sidebar history reflects this search immediately
            st.rerun()
        else:
            # Empty search - clear results and show notification
            st.session_state.pop("search_results", None)
            st.session_state.pop("search_query", None)
            st.session_state["search_query_input"] = ""
            queue_toast("Please enter a search query to find products.", "warning")
            st.rerun()

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
    cookie_manager = get_cookie_manager()
    sync_auth_session(cookie_manager)

    # Always prefer a clean base URL (no ?logout=1)
    if "logout" in st.query_params:
        del st.query_params["logout"]
    show_pending_toasts()

    if not st.session_state.authenticated:
        # Give cookie / localStorage bridge a chance before painting sign-in
        if st.session_state.get("_sps_suppress_login"):
            inject_session_restore_bridge()
            return
        login_page(cookie_manager)
        return

    inject_idle_logout_watchdog()
    idle_session_watchdog()
    if st.session_state.session_id:
        persist_session_id_to_browser(st.session_state.session_id)
    inject_app_styles()
    render_app_header(cookie_manager)

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
