"""Toast notifications for the Streamlit UI."""

from __future__ import annotations

from typing import Literal

import streamlit as st

ToastType = Literal["success", "error", "warning", "info"]

_TOAST_KEY = "_pending_toasts"
_ICONS: dict[ToastType, str] = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
}


def inject_toast_styles() -> None:
    """Pin toast notifications flush to the extreme top-right of the viewport."""
    st.markdown(
        """
        <style>
        /* Force toast container to absolute top-right of the browser window */
        [data-testid="toastContainer"],
        [data-testid="stToastContainer"],
        div[data-baseweb="toast"]:has([data-testid="stToast"]),
        body > div[class*="toast"],
        [class*="ToastContainer"],
        [class*="stToastContainer"] {
            position: fixed !important;
            inset: 0 auto auto auto !important;
            top: 0.5rem !important;
            right: 0.5rem !important;
            bottom: unset !important;
            left: unset !important;
            padding: 0 !important;
            margin: 0 !important;
            transform: translateY(0) !important;
            z-index: 2147483647 !important;
            align-items: flex-end !important;
            justify-content: flex-start !important;
            pointer-events: none;
        }

        [data-testid="toastContainer"] > *,
        [data-testid="stToastContainer"] > *,
        [data-testid="stToast"] {
            pointer-events: auto;
            margin: 0 !important;
            margin-top: 0 !important;
            top: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def queue_toast(message: str, toast_type: ToastType = "info") -> None:
    """Store a toast to display after the next rerun."""
    pending = st.session_state.setdefault(_TOAST_KEY, [])
    pending.append({"message": message, "type": toast_type})


def show_toast(message: str, toast_type: ToastType = "info") -> None:
    """Show a toast notification immediately."""
    st.toast(message, icon=_ICONS.get(toast_type, "ℹ️"))


def show_pending_toasts() -> None:
    """Display any toasts queued before a rerun."""
    pending = st.session_state.pop(_TOAST_KEY, [])
    for item in pending:
        show_toast(item["message"], item["type"])


def toast_success(message: str) -> None:
    show_toast(message, "success")


def toast_error(message: str) -> None:
    show_toast(message, "error")


def toast_warning(message: str) -> None:
    show_toast(message, "warning")


def toast_info(message: str) -> None:
    show_toast(message, "info")
