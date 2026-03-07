import os

import streamlit as st

st.set_page_config(
    page_title="AI Medical Agent Portfolio",
    page_icon="🧠",
    layout="centered",
)

URL1 = os.getenv("URL_BASIC", "http://localhost:8501")
URL2 = os.getenv("URL_INTERMEDIATE", "http://localhost:8502")
URL3 = os.getenv("URL_ADVANCED", "http://localhost:8503")

st.markdown(
    """
    <style>
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div:first-child {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div:first-child > div:last-child {
        margin-top: auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧠 AI Medical Agent Portfolio")
st.caption("Three agentic AI systems built with LangGraph + LiteLLM")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("01 — Basic Agent")
    st.markdown(
        "**Reflection Loop**\n\n"
        "Generator drafts a medical summary. "
        "Critic reviews it. Loop repeats until approved."
    )
    st.link_button("Open App", URL1, use_container_width=True)
    with st.expander("Architecture"):
        st.code(
            "User Input\n"
            "     │\n"
            "     ▼\n"
            "┌─────────────┐\n"
            "│  Generator  │ ◄──────────┐\n"
            "│ Drafts      │            │ rejected\n"
            "│ summary     │            │\n"
            "└──────┬──────┘            │\n"
            "       ▼                   │\n"
            "┌─────────────┐            │\n"
            "│   Critic    │ ───────────┘\n"
            "│ Reviews for │\n"
            "│ accuracy    │\n"
            "└──────┬──────┘\n"
            "       │ approved\n"
            "       ▼\n"
            "  Final Summary",
            language=None,
        )

with col2:
    st.subheader("02 — Intermediate Agent")
    st.markdown(
        "**Supervisor + Parallel Specialists**\n\n"
        "Supervisor routes the case to multiple specialists "
        "running in parallel. Aggregator synthesizes results."
    )
    st.link_button("Open App", URL2, use_container_width=True)
    with st.expander("Architecture"):
        st.code(
            "User Input\n"
            "     │\n"
            "     ▼\n"
            "┌─────────────┐\n"
            "│  Supervisor │\n"
            "│ Selects     │\n"
            "│ specialists │\n"
            "└──────┬──────┘\n"
            "  ┌────┼────┐\n"
            "  ▼    ▼    ▼\n"
            " [S1] [S2] [S3] ← parallel\n"
            "  └────┬────┘\n"
            "       ▼\n"
            "┌─────────────┐\n"
            "│  Aggregator │\n"
            "│ Synthesizes │\n"
            "└──────┬──────┘\n"
            "       ▼\n"
            "  Final Summary",
            language=None,
        )

with col3:
    st.subheader("03 — Advanced Agent")
    st.markdown(
        "**Pipeline + Human-in-the-Loop**\n\n"
        "5-node pipeline: extract entities, assign codes, "
        "draft SOAP note, pause for clinician review."
    )
    st.link_button("Open App", URL3, use_container_width=True)
    with st.expander("Architecture"):
        st.code(
            "Clinical Document\n"
            "     │\n"
            "     ▼\n"
            "┌─────────────┐\n"
            "│   Extract   │\n"
            "│   Entities  │\n"
            "└──────┬──────┘\n"
            "       ▼\n"
            "┌─────────────┐\n"
            "│ Assign ICD  │\n"
            "│   Codes     │\n"
            "└──────┬──────┘\n"
            "       ▼\n"
            "┌─────────────┐\n"
            "│ Draft SOAP  │\n"
            "│    Note     │\n"
            "└──────┬──────┘\n"
            "       ▼\n"
            "┌─────────────┐\n"
            "│ ⏸ Human    │\n"
            "│   Review    │\n"
            "└──────┬──────┘\n"
            "       │ approved\n"
            "       ▼\n"
            "  Final SOAP Note",
            language=None,
        )

st.divider()
st.caption("Powered by LangGraph · LiteLLM · FastAPI · Streamlit")
