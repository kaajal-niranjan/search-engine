"""Browser cookie + localStorage helpers for persistent Streamlit auth sessions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import extra_streamlit_components as stx
import streamlit as st
import streamlit.components.v1 as components

from src.session import COOKIE_MAX_AGE_SECONDS, COOKIE_NAME


def get_cookie_manager() -> Any:
    """Create CookieManager (same key each run so the browser component syncs)."""
    return stx.CookieManager(key="sps_cookie_manager")


def _read_from_request_cookies() -> Optional[str]:
    """Read session id from HTTP request cookies (available on first refresh run)."""
    try:
        cookies = st.context.cookies
    except Exception:
        return None
    if cookies is None:
        return None
    try:
        value = cookies.get(COOKIE_NAME)
    except Exception:
        try:
            value = cookies[COOKIE_NAME]  # type: ignore[index]
        except Exception:
            return None
    if value is None or value == "":
        return None
    return str(value).strip()


def read_session_cookie(manager: Any = None) -> Optional[str]:
    """Prefer request cookies; fall back to CookieManager; then query param bridge."""
    immediate = _read_from_request_cookies()
    if immediate:
        return immediate

    # One-time bridge from localStorage → ?sps_sid=… (injected elsewhere)
    qp = st.query_params.get("sps_sid")
    if qp:
        return str(qp).strip()

    if manager is None:
        return None

    try:
        all_cookies = manager.get_all()
        if isinstance(all_cookies, dict):
            value = all_cookies.get(COOKIE_NAME)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
    except Exception:
        pass

    try:
        value = manager.get(COOKIE_NAME)
    except Exception:
        value = None
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def write_session_cookie(manager: Any, session_id: str) -> None:
    """Persist a URL-safe session id as a first-party cookie."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(COOKIE_MAX_AGE_SECONDS))
    manager.set(
        COOKIE_NAME,
        session_id,
        key=f"set_{COOKIE_NAME}",
        path="/",
        expires_at=expires_at,
        max_age=int(COOKIE_MAX_AGE_SECONDS),
        same_site="lax",
    )


def clear_session_cookie(manager: Any) -> None:
    """Remove the session cookie without crashing if it is not hydrated yet."""
    try:
        try:
            known = manager.get_all() or {}
        except Exception:
            known = getattr(manager, "cookies", None) or {}

        if isinstance(known, dict) and COOKIE_NAME in known:
            try:
                manager.delete(COOKIE_NAME)
                return
            except KeyError:
                pass

        try:
            manager.cookie_manager(
                method="delete",
                cookie=COOKIE_NAME,
                key="delete_sps_session",
                default=False,
            )
        except Exception:
            pass

        cookies = getattr(manager, "cookies", None)
        if isinstance(cookies, dict):
            cookies.pop(COOKIE_NAME, None)
    except KeyError:
        pass
    except Exception:
        pass


def persist_session_id_to_browser(session_id: str) -> None:
    """Mirror session id into localStorage as a refresh backup when cookies are flaky."""
    safe = session_id.replace("\\", "\\\\").replace("'", "\\'")
    components.html(
        f"""
        <script>
        try {{
          window.parent.localStorage.setItem('sps_sid', '{safe}');
        }} catch (e) {{}}
        </script>
        """,
        height=0,
        width=0,
    )


def clear_session_id_from_browser() -> None:
    """Clear localStorage session backup on logout."""
    components.html(
        """
        <script>
        try {
          window.parent.localStorage.removeItem('sps_sid');
        } catch (e) {}
        </script>
        """,
        height=0,
        width=0,
    )


def inject_session_restore_bridge() -> None:
    """
    If the HTTP cookie is missing after refresh, recover session id from
    localStorage once via ?sps_sid=… then let Python restore auth.
    """
    components.html(
        """
        <script>
        (function () {
          try {
            const FLAG = 'sps_sid';
            const url = new URL(window.parent.location.href);
            if (url.searchParams.get('idle_logout') === '1') {
              window.parent.localStorage.removeItem('sps_sid');
              return;
            }
            if (url.searchParams.has(FLAG)) return;
            const sid = window.parent.localStorage.getItem('sps_sid');
            if (!sid) return;
            url.searchParams.set(FLAG, sid);
            window.parent.location.replace(url.toString());
          } catch (e) {}
        })();
        </script>
        """,
        height=0,
        width=0,
    )
