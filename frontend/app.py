"""Enterprise Nested LangGraph (Subgraphs) - Demo Dashboard.

Run with: streamlit run frontend/app.py   (from the enterprise-nested-langgraph repo root)
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

import time

import streamlit as st

st.set_page_config(
    page_title="Enterprise Nested LangGraph",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Enterprise Nested LangGraph")
st.caption("Supervisor graph with nested research / analytics / reporting subgraphs")

EXAMPLE_QUERIES = [
    "Prepare a quarterly revenue outlook.",
    "Analyze customer churn drivers.",
    "Summarize competitive positioning.",
    "Draft a weekly operations report.",
]


@st.cache_resource
def get_runner():
    from app import run

    return run


def render_state(state: dict):
    if not state:
        return
    report = state.get("report")
    if report:
        st.subheader("Report")
        st.markdown(report)

    meta = state.get("metadata") or {}
    if meta:
        st.subheader("Metadata")
        st.json(meta, default=str)


def main():
    with st.sidebar:
        st.header("Controls")
        example = st.selectbox("Example query", [""] + EXAMPLE_QUERIES)
        query = st.text_area("Query", value=example or EXAMPLE_QUERIES[0], height=100)
        run = st.button("Run", type="primary", use_container_width=True)

    if not run:
        st.info("Enter a query and press **Run** to execute the nested supervisor graph.")
        return

    if not query.strip():
        st.warning("Please enter a query.")
        return

    try:
        run_pipeline = get_runner()
        with st.spinner("Running supervisor + subgraphs..."):
            start = time.monotonic()
            state = run_pipeline(query.strip())
            elapsed = time.monotonic() - start

        st.caption(f"Completed in {elapsed:.2f}s")
        render_state(state)

        with st.expander("Raw state"):
            st.json(state, default=str)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Execution failed: {exc}")


main()
