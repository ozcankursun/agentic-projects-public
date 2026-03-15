import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(page_title="Medical Summary Agent", page_icon="🏥", layout="centered")

st.title("🏥 Medical Summary Agent")
st.caption("Generator → Critic reflection loop | Powered by LangGraph + LiteLLM")

st.markdown(
    "Paste patient symptoms or lab results below. "
    "The agent will draft a professional medical summary and refine it until the Critic approves."
)

with st.expander("📋 Try an example — expand and copy"):
    st.code(
        "Patient: Maria Santos, 52F\n"
        "Chief complaint: sudden severe headache (10/10), worst of her life, onset during exercise.\n"
        "Associated symptoms: nausea, neck stiffness, photophobia. No fever.\n"
        "Vitals: BP 162/94, HR 88, Temp 37.1°C, SpO2 99%.\n"
        "Neuro exam: alert but distressed, Kernig sign positive.\n"
        "CT head: negative for hemorrhage.\n"
        "CSF: xanthochromic, RBC 15,000, protein 95 mg/dL, glucose 42 mg/dL, opening pressure 28 cmH2O.",
        language=None,
    )

patient_input = st.text_area(
    "Patient Description",
    height=200,
    placeholder=(
        "e.g. Patient is a 45-year-old male with a 3-day history of severe headache (9/10), "
        "photophobia, neck stiffness, nausea, and vomiting. Temperature 38.7°C, HR 94. "
        "CBC: WBC 14,200 (elevated), neutrophils 85%. CSF: cloudy, protein elevated, glucose low."
    ),
)

if st.button("Analyze with Agent", type="primary"):
    if not patient_input.strip():
        st.warning("Please enter patient information before analyzing.")
        st.stop()
    with st.spinner("Agent is thinking… (Generator → Critic loop running)"):
        try:
            response = requests.post(
                f"{API_URL}/analyze",
                json={"text": patient_input},
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()

            st.success("Analysis complete!")

            st.subheader("Final Approved Medical Summary")
            st.markdown(data["final_summary"])

            with st.expander("View Agent Thinking History"):
                history_lines = data["history"].strip().split("\n")
                for line in history_lines:
                    if line.startswith("[GENERATOR]"):
                        st.markdown(f"🟦 **{line}**")
                    elif line.startswith("[CRITIC]"):
                        if "approved=True" in line:
                            st.markdown(f"✅ **{line}**")
                        else:
                            st.markdown(f"🔴 **{line}**")
                    else:
                        st.text(line)

        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the API. Make sure the API container is running.")
        except requests.exceptions.Timeout:
            st.error("Request timed out. The agent may be taking too long.")
        except requests.exceptions.HTTPError as e:
            st.error(f"API error: {e.response.status_code} — {e.response.text}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
