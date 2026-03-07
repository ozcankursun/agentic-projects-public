# 03 — Advanced Agent: Implementation Guide

Build a 5-node clinical document processing pipeline that extracts medical entities, assigns terminology codes, drafts a SOAP note, and pauses for human review before finalizing.

---

## What You Will Build

A stateful multi-phase AI pipeline that:
1. Accepts clinical documents (PDF, TXT, CSV) via upload or from a storage directory
2. Extracts **medical conditions** and **medications** from the document text
3. Assigns **ICD-10-CM** codes to conditions and **RxNorm** codes to medications
4. Drafts a structured **SOAP note**
5. **Pauses** for clinician review — the clinician can edit the draft
6. Resumes and finalizes after approval

---

## Agentic Pattern: Sequential Pipeline + Human-in-the-Loop

```
Document(s) — PDF / TXT / CSV
       │
       ▼
condition_extractor   →  ["hypertension", "stroke", ...]
       │
       ▼
medication_extractor  →  [{drug, dosage, route}, ...]
       │
       ▼
condition_coder       →  [{chunk, entity_type, ICD10}, ...]
       │
       ▼
medication_coder      →  [{chunk, entity_type, RxNorm}, ...]
       │
       ▼
soap_drafter          →  SOAP note draft
       │
  ─────────────────────────────────────
  HUMAN REVIEW GATE (interrupt_after)
  Clinician edits SOAP note in UI
  ─────────────────────────────────────
       │
       ▼
      END  →  Final signed SOAP note
```

---

## Project Structure

```
03_advanced_agent/
├── api/
│   ├── agent.py          ← LangGraph workflow (5 nodes, MemorySaver checkpoint, interrupt)
│   ├── main.py           ← FastAPI server (/health, /files, /upload, /process-storage, /approve)
│   ├── tools.py          ← ICD-10 fallback lookup + SOAP template formatter
│   ├── requirements.txt
│   └── Dockerfile
├── ui/
│   ├── app.py            ← Streamlit frontend (idle / awaiting_approval / completed states)
│   ├── requirements.txt
│   └── Dockerfile
├── data/                 ← Pre-loaded clinical documents (PDF / TXT / CSV)
├── docker-compose.yml
└── .env
```

---

## Requirements

**`api/requirements.txt`**
```
fastapi[standard]>=0.110.0
langchain-core>=0.1.30
langgraph>=0.2.0
langgraph-checkpoint>=1.0.2
litellm>=1.34.0
pydantic>=2.6.0
python-dotenv>=1.0.1
uvicorn>=0.28.0
PyPDF2>=3.0.0
python-multipart>=0.0.9
```

**`ui/requirements.txt`**
```
streamlit>=1.32.0
requests>=2.31.0
```

**External dependencies:** Python 3.11+, Docker & Docker Compose, Groq API key (free at console.groq.com)

---

## Environment File (`.env`)

```env
GROQ_API_KEY=gsk_...
LLM_MODEL=groq/llama-3.3-70b-versatile
```

---

## Running the Project

```bash
cd 03_advanced_agent

# Optional: pre-load clinical documents
cp my_patient_notes.pdf data/

docker compose up --build
```

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

---

## API Endpoints

| Method | Path | Input | Output |
|---|---|---|---|
| `GET` | `/health` | — | `{"status": "ok"}` |
| `GET` | `/files` | — | `{"files": ["file1.pdf", ...]}` |
| `POST` | `/upload` | multipart files (PDF/TXT/CSV) | `{thread_id, status, soap_draft, extractions}` |
| `POST` | `/process-storage` | `{"filenames": ["file1.pdf"]}` | `{thread_id, status, soap_draft, extractions}` |
| `POST` | `/approve` | `{"thread_id": "...", "updated_soap": "..."}` | `{status, final_soap_note}` |

---

## UI Walkthrough

The UI has three states controlled by `st.session_state.workflow_status`.

**1. Idle** — Choose how to provide the document:
- **Upload file** mode: drag-and-drop one or more PDF/TXT/CSV files, click **Process Document(s)**
- **Storage** mode: checkboxes list files from the `data/` directory, click **Process Selected File(s)**

**2. Awaiting Approval** — The pipeline has run and paused:
- Editable SOAP note text area — review and correct the AI-generated draft
- Expandable panels show extracted **Medical Conditions** (with ICD-10 codes) and **Drugs** (with RxNorm codes) as JSON
- Click **Approve & Submit** to send the edited note back and resume the workflow

**3. Completed** — Workflow finalized:
- Final SOAP note rendered as markdown
- Extractions still visible for reference
- **Start New Patient** button resets all session state back to idle

---

## Implementation Notes

### `tools.py`
Implement two helper functions:
- `get_icd10_code(condition)` — a fallback lookup dict mapping common condition strings to ICD-10 codes. Used only if the LLM coder fails.
- `format_soap_template(subjective, objective, assessment, plan)` — returns a formatted markdown SOAP string with bold section headers.

### Agent State
`AgentState` TypedDict with: `raw_text` (str), `conditions` (List[str]), `medications` (List[dict]), `extractions` (Annotated with `operator.add`), `soap_draft` (str).

`operator.add` on `extractions` allows `condition_coder` and `medication_coder` to each append their results without overwriting.

### Condition Extractor Node
Calls LLM with a clinical NLP prompt. Returns a JSON array of condition strings. Parse with `re.search(r"\[.*\]", text, re.DOTALL)` for robustness. Store in `state["conditions"]`.

### Medication Extractor Node
Calls LLM requesting exactly three fields per drug: `drug`, `dosage`, `route`. Returns structured dicts — no frequency or duration. Validates and stores as `state["medications"]`.

### Condition Coder Node (ICD-10)
Sends the list of conditions to the LLM and asks for ICD-10-CM codes. Returns a list of `{"chunk": ..., "entity_type": "medical_condition", "ICD10": ...}` dicts. Falls back to `get_icd10_code()` if parsing fails.

### Medication Coder Node (RxNorm)
Builds a `chunk` string for each medication by joining `drug + dosage + route`. Sends to LLM for RxNorm (RxCUI) codes. Returns `{"chunk": ..., "entity_type": "drug", "RxNorm": ...}` dicts.

### SOAP Drafter Node
Collects all extractions, formats conditions and drugs as labeled lists, calls LLM to draft the assessment section, then wraps it with `format_soap_template()`. The `S` and `P` sections contain placeholders pending human review.

### Graph + Checkpoint
Compile with `MemorySaver` as checkpointer and `interrupt_after=["soap_drafter"]`. This freezes execution after the SOAP draft is produced. Each run is identified by a UUID `thread_id` stored in `{"configurable": {"thread_id": ...}}`.

### Entry Point Functions
- `start_workflow(thread_id, raw_text)` — invokes the graph, then calls `get_state()` to return the frozen state at the interrupt point
- `update_workflow_and_resume(thread_id, updated_soap)` — calls `update_state()` to inject human edits, then `invoke(None)` to resume from the checkpoint

### Text Extraction (main.py)
Two helpers: `_extract_text_from_upload(file)` for `UploadFile` objects, `_extract_text_from_path(filepath)` for files on disk. Both dispatch by file extension: PDF via `PyPDF2`, TXT via UTF-8 decode, CSV via `csv.reader`. Multiple files are concatenated with `=== filename ===` section headers.

### Docker Volume
The `docker-compose.yml` mounts `./data:/app/data` in the API container. `DATA_DIR = "/app/data"` is the constant used in `main.py`. The `/files` endpoint lists valid files from this directory.

---

## Example Input (TXT file)

```
Patient: 58-year-old female
Chief complaint: fatigue, weight gain, cold intolerance

History: 6-month history of progressive fatigue, 8 kg weight gain, constipation,
cold intolerance, and dry skin. No chest pain or dyspnea.

Medications: atorvastatin 40 MG Oral, lisinopril 10 MG Oral

Exam: HR 58, BP 138/88, BMI 31. Skin dry, hair brittle, delayed reflexes.
Thyroid: diffusely enlarged, non-tender.

Labs: TSH 18.4 mIU/L (elevated), Free T4 0.5 ng/dL (low), Total cholesterol 268 mg/dL
```

## Example Output

**Extractions:**
```json
[
  {"chunk": "hypothyroidism",         "entity_type": "medical_condition", "ICD10":  "E03.9"},
  {"chunk": "hyperlipidemia",         "entity_type": "medical_condition", "ICD10":  "E78.5"},
  {"chunk": "obesity",                "entity_type": "medical_condition", "ICD10":  "E66.9"},
  {"chunk": "atorvastatin 40 MG Oral","entity_type": "drug",              "RxNorm": "617310"},
  {"chunk": "lisinopril 10 MG Oral",  "entity_type": "drug",              "RxNorm": "314076"}
]
```

**SOAP Note Draft:**
```
S (Subjective):
Patient reports 6-month history of progressive fatigue, 8 kg weight gain,
cold intolerance, constipation, and dry skin.

O (Objective):
HR 58 (bradycardia), BP 138/88, BMI 31. Dry skin, brittle hair, delayed
reflexes, diffusely enlarged non-tender thyroid. TSH 18.4 (elevated),
Free T4 0.5 (low), Total cholesterol 268.

A (Assessment):
Primary hypothyroidism (E03.9), hyperlipidemia (E78.5), obesity (E66.9).

P (Plan):
Initiate levothyroxine, recheck TFTs in 6 weeks.
Continue atorvastatin 40 MG Oral (RxNorm: 617310).
Continue lisinopril 10 MG Oral (RxNorm: 314076).
Dietary counseling for weight management.
```

---
