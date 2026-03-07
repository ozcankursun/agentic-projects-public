import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(
    page_title="Multi-Specialist Medical AI",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Multi-Specialist Medical AI")
st.caption("Supervisor → Parallel Specialists → Aggregator | Powered by LangGraph + LiteLLM")

# Sidebar
with st.sidebar:
    st.header("Settings")
    top_k = st.slider(
        "Number of specialists to consult",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="The supervisor LLM will select the most relevant specialists for the case.",
    )
    st.caption(f"Selected: **{top_k}** specialist(s) will analyze the case in parallel.")

# Main input
with st.expander("📋 Try an example — expand and copy"):
    st.code(
        "Patient: James Okafor, 68M\n"
        "Chief complaint: 2-week progressive shortness of breath, bilateral leg swelling, orthopnea (3 pillows).\n"
        "History: hypertension, type 2 diabetes, prior MI (2019).\n"
        "Medications: metformin, amlodipine, aspirin.\n"
        "Vitals: BP 155/96, HR 102, RR 22, SpO2 91% on room air.\n"
        "Exam: JVD present, bilateral crackles, 2+ pitting edema to knees.\n"
        "Labs: BNP 1,450 pg/mL, troponin 0.02, Cr 1.6, Na 131.\n"
        "ECG: LBBB. CXR: cardiomegaly, bilateral pulmonary congestion.",
        language=None,
    )

case_input = st.text_area(
    "Medical Case Description",
    height=220,
    placeholder=(
        "e.g. 68-year-old female with 2-week history of progressive shortness of breath, "
        "bilateral leg swelling, and orthopnea. BNP: 1,450 pg/mL. ECG: LBBB. "
        "CXR: cardiomegaly, pulmonary congestion."
    ),
)

if st.button("Analyze with Specialists", type="primary", disabled=not case_input.strip()):
    with st.spinner(f"Supervisor selecting {top_k} specialist(s) and running parallel analysis…"):
        try:
            response = requests.post(
                f"{API_URL}/analyze",
                json={"text": case_input, "top_k": top_k},
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()

            st.success(f"Analysis complete — {len(data['assessments'])} specialist(s) consulted.")

            # Integrated summary
            st.subheader("Integrated Clinical Summary")
            st.markdown(data["final_summary"])

            st.divider()

            # Individual specialist tabs
            st.subheader("Individual Specialist Assessments")
            assessments = data["assessments"]

            if assessments:
                tab_labels = [a["role"] for a in assessments]
                tabs = st.tabs(tab_labels)
                for tab, assessment in zip(tabs, assessments):
                    with tab:
                        st.markdown(assessment["assessment"])

        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the API. Make sure the API container is running.")
        except requests.exceptions.Timeout:
            st.error("Request timed out. Try reducing the number of specialists.")
        except requests.exceptions.HTTPError as e:
            st.error(f"API error: {e.response.status_code} — {e.response.text}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
