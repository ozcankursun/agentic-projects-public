import os

import streamlit as st

st.set_page_config(
    page_title="AI Medical Agent Portfolio",
    page_icon="🧠",
    layout="wide",
)

URL1 = os.getenv("URL_BASIC", "http://localhost:8501")
URL2 = os.getenv("URL_INTERMEDIATE", "http://localhost:8502")
URL3 = os.getenv("URL_ADVANCED", "http://localhost:8503")

ARCH1 = (
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
    "  Final Summary"
)

ARCH2 = (
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
    "[S1] [S2] [S3] ← parallel\n"
    "  └────┬────┘\n"
    "       ▼\n"
    "┌─────────────┐\n"
    "│  Aggregator │\n"
    "│ Synthesizes │\n"
    "└──────┬──────┘\n"
    "       ▼\n"
    "  Final Summary"
)

ARCH3 = (
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
    "  Final SOAP Note"
)

st.markdown(
    f"""
<style>
.portfolio-header {{
    text-align: center;
    padding: 40px 0 32px;
}}
.portfolio-header h1 {{
    font-size: 2.6rem;
    font-weight: 800;
    color: #111827;
    margin: 0 0 10px;
}}
.portfolio-header p {{
    font-size: 1.05rem;
    color: #6b7280;
    margin: 0;
}}
.cards-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 28px;
    margin: 0 0 40px;
}}
.card {{
    background: #ffffff;
    border-radius: 18px;
    padding: 30px 26px 26px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
    border-top: 5px solid;
    display: flex;
    flex-direction: column;
}}
.card-1 {{ border-color: #3b82f6; }}
.card-2 {{ border-color: #10b981; }}
.card-3 {{ border-color: #8b5cf6; }}
.card-num {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 8px;
}}
.card-1 .card-num {{ color: #3b82f6; }}
.card-2 .card-num {{ color: #10b981; }}
.card-3 .card-num {{ color: #8b5cf6; }}
.card-title {{
    font-size: 1.3rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 4px;
}}
.card-subtitle {{
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 12px;
}}
.card-1 .card-subtitle {{ color: #3b82f6; }}
.card-2 .card-subtitle {{ color: #10b981; }}
.card-3 .card-subtitle {{ color: #8b5cf6; }}
.card-desc {{
    font-size: 0.92rem;
    color: #6b7280;
    line-height: 1.65;
    margin-bottom: 22px;
    flex: 1;
}}
.arch-block {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px 18px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 12px;
    color: #374151;
    line-height: 1.55;
    white-space: pre;
    overflow-x: auto;
    margin-bottom: 22px;
    flex: 1;
}}
.open-btn {{
    display: block;
    text-align: center;
    color: white !important;
    text-decoration: none !important;
    padding: 12px 0;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.95rem;
    transition: filter 0.2s;
    margin-top: auto;
}}
.open-btn:hover {{ filter: brightness(0.88); }}
.card-1 .open-btn {{ background: #3b82f6; }}
.card-2 .open-btn {{ background: #10b981; }}
.card-3 .open-btn {{ background: #8b5cf6; }}
.portfolio-footer {{
    text-align: center;
    color: #9ca3af;
    font-size: 0.85rem;
    padding: 20px 0;
    border-top: 1px solid #f0f0f0;
}}
</style>

<div class="portfolio-header">
    <h1>🧠 AI Medical Agent Portfolio</h1>
    <p>Three agentic AI systems built with LangGraph + LiteLLM</p>
</div>

<div class="cards-grid">

  <div class="card card-1">
    <div class="card-num">01 · Basic Agent</div>
    <div class="card-title">Medical Summary Agent</div>
    <div class="card-subtitle">Reflection Loop</div>
    <div class="card-desc">Generator drafts a medical summary. Critic reviews it. Loop repeats until the Critic approves.</div>
    <div class="arch-block">{ARCH1}</div>
    <a href="{URL1}" target="_blank" class="open-btn">Open App →</a>
  </div>

  <div class="card card-2">
    <div class="card-num">02 · Intermediate Agent</div>
    <div class="card-title">Multi-Specialist AI</div>
    <div class="card-subtitle">Supervisor + Parallel Specialists</div>
    <div class="card-desc">Supervisor routes the case to multiple specialists running in parallel. Aggregator synthesizes all results.</div>
    <div class="arch-block">{ARCH2}</div>
    <a href="{URL2}" target="_blank" class="open-btn">Open App →</a>
  </div>

  <div class="card card-3">
    <div class="card-num">03 · Advanced Agent</div>
    <div class="card-title">Clinical Document Processor</div>
    <div class="card-subtitle">Pipeline + Human-in-the-Loop</div>
    <div class="card-desc">5-node pipeline: extract entities, assign ICD codes, draft SOAP note, pause for clinician review.</div>
    <div class="arch-block">{ARCH3}</div>
    <a href="{URL3}" target="_blank" class="open-btn">Open App →</a>
  </div>

</div>

<div class="portfolio-footer">Powered by LangGraph · LiteLLM · FastAPI · Streamlit</div>
""",
    unsafe_allow_html=True,
)
