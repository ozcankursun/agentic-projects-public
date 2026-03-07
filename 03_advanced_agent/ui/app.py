import json
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(
    page_title="Clinical Document Processor",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Clinical Document Processor")
st.caption("5-node pipeline: Extract → Code → SOAP → Human Review | Powered by LangGraph + LiteLLM")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "workflow_status" not in st.session_state:
    st.session_state.workflow_status = "idle"      # idle | awaiting_approval | completed
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "soap_draft" not in st.session_state:
    st.session_state.soap_draft = ""
if "extractions" not in st.session_state:
    st.session_state.extractions = []
if "final_soap" not in st.session_state:
    st.session_state.final_soap = ""


# ---------------------------------------------------------------------------
# STATE 1 — IDLE
# ---------------------------------------------------------------------------

if st.session_state.workflow_status == "idle":
    st.subheader("Upload or select a clinical document")

    with st.expander("📋 Try an example — copy text below, save as patient.txt, then upload"):
        st.code(
            "Patient: Linda Kowalski, 61F\n"
            "Chief complaint: 3-day history of worsening chest pain, radiating to left arm, associated diaphoresis.\n"
            "History: hypertension, hyperlipidemia, family history of CAD (father MI at 58).\n"
            "Medications: atorvastatin 40mg, lisinopril 10mg, aspirin 81mg.\n"
            "Vitals: BP 148/90, HR 96, RR 18, Temp 37.0°C, SpO2 97%.\n"
            "Exam: mild diaphoresis, S4 gallop, no rales, no JVD.\n"
            "Labs: troponin-I 1.8 ng/mL (elevated), BNP 210, CK-MB 28.\n"
            "ECG: ST depression 1mm in leads V4-V6, T-wave inversion V5-V6.\n"
            "CXR: mild cardiomegaly, no pulmonary edema.",
            language=None,
        )

    mode = st.radio("Input mode", ["Upload file(s)", "Select from storage"], horizontal=True)

    if mode == "Upload file(s)":
        uploaded = st.file_uploader(
            "Upload PDF, TXT, or CSV files",
            type=["pdf", "txt", "csv"],
            accept_multiple_files=True,
        )
        if st.button("Process Document(s)", type="primary", disabled=not uploaded):
            with st.spinner("Running 5-node pipeline… this may take a moment."):
                try:
                    files = [("files", (f.name, f.read(), f.type)) for f in uploaded]
                    response = requests.post(f"{API_URL}/upload", files=files, timeout=300)
                    response.raise_for_status()
                    data = response.json()
                    st.session_state.thread_id = data["thread_id"]
                    st.session_state.soap_draft = data["soap_draft"]
                    st.session_state.extractions = data["extractions"]
                    st.session_state.workflow_status = "awaiting_approval"
                    st.rerun()
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the API.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"API error: {e.response.status_code} — {e.response.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

    else:  # Storage mode
        try:
            resp = requests.get(f"{API_URL}/files", timeout=10)
            resp.raise_for_status()
            available = resp.json().get("files", [])
        except Exception:
            available = []

        if not available:
            st.info("No files found in the data/ directory. Upload files to the `data/` folder and restart.")
        else:
            selected = []
            for fname in available:
                if st.checkbox(fname):
                    selected.append(fname)

            if st.button("Process Selected File(s)", type="primary", disabled=not selected):
                with st.spinner("Running 5-node pipeline… this may take a moment."):
                    try:
                        response = requests.post(
                            f"{API_URL}/process-storage",
                            json={"filenames": selected},
                            timeout=300,
                        )
                        response.raise_for_status()
                        data = response.json()
                        st.session_state.thread_id = data["thread_id"]
                        st.session_state.soap_draft = data["soap_draft"]
                        st.session_state.extractions = data["extractions"]
                        st.session_state.workflow_status = "awaiting_approval"
                        st.rerun()
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the API.")
                    except requests.exceptions.HTTPError as e:
                        st.error(f"API error: {e.response.status_code} — {e.response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")


# ---------------------------------------------------------------------------
# STATE 2 — AWAITING APPROVAL
# ---------------------------------------------------------------------------

elif st.session_state.workflow_status == "awaiting_approval":
    st.success("Pipeline complete — SOAP draft ready for review.")
    st.info("Review the SOAP note below. Edit as needed, then click **Approve & Submit**.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("SOAP Note Draft")
        edited_soap = st.text_area(
            "Edit the SOAP note:",
            value=st.session_state.soap_draft,
            height=400,
            key="soap_editor",
        )

        if st.button("Approve & Submit", type="primary"):
            with st.spinner("Saving approved note and finalizing…"):
                try:
                    response = requests.post(
                        f"{API_URL}/approve",
                        json={
                            "thread_id": st.session_state.thread_id,
                            "updated_soap": edited_soap,
                        },
                        timeout=60,
                    )
                    response.raise_for_status()
                    data = response.json()
                    st.session_state.final_soap = data["final_soap_note"]
                    st.session_state.workflow_status = "completed"
                    st.rerun()
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the API.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"API error: {e.response.status_code} — {e.response.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        st.subheader("Extracted Entities")

        conditions = [e for e in st.session_state.extractions if e.get("entity_type") == "medical_condition"]
        drugs = [e for e in st.session_state.extractions if e.get("entity_type") == "drug"]

        with st.expander(f"Medical Conditions ({len(conditions)})", expanded=True):
            if conditions:
                st.json(conditions)
            else:
                st.write("None extracted.")

        with st.expander(f"Medications ({len(drugs)})", expanded=True):
            if drugs:
                st.json(drugs)
            else:
                st.write("None extracted.")


# ---------------------------------------------------------------------------
# STATE 3 — COMPLETED
# ---------------------------------------------------------------------------

elif st.session_state.workflow_status == "completed":
    st.success("Workflow complete — SOAP note finalized.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Final SOAP Note")
        st.markdown(st.session_state.final_soap)

    with col2:
        st.subheader("Extracted Entities")

        conditions = [e for e in st.session_state.extractions if e.get("entity_type") == "medical_condition"]
        drugs = [e for e in st.session_state.extractions if e.get("entity_type") == "drug"]

        with st.expander(f"Medical Conditions ({len(conditions)})"):
            if conditions:
                st.json(conditions)
            else:
                st.write("None extracted.")

        with st.expander(f"Medications ({len(drugs)})"):
            if drugs:
                st.json(drugs)
            else:
                st.write("None extracted.")

    st.divider()
    if st.button("Start New Patient", type="secondary"):
        st.session_state.workflow_status = "idle"
        st.session_state.thread_id = None
        st.session_state.soap_draft = ""
        st.session_state.extractions = []
        st.session_state.final_soap = ""
        st.rerun()
