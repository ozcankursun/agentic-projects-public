# 01 — Basic Agent: Implementation Guide

Build a two-agent reflection loop that generates and critiques a medical summary until it is approved.

---

## What You Will Build

A simple AI pipeline where:
1. A **Generator** agent drafts a medical summary from patient symptoms
2. A **Critic** agent reviews the draft for safety and accuracy
3. If rejected, the Generator refines using the Critic's feedback
4. The loop repeats until approved (max 5 iterations)

---

## Agentic Pattern: Reflection Loop

```
Patient Input
     │
     ▼
┌─────────────┐
│  Generator  │ ◄──────────────────┐
│    Node     │                    │ feedback
└──────┬──────┘                    │
       │ draft                     │
       ▼                           │
┌─────────────┐   not approved     │
│   Critic    │───────────────────►┘
│    Node     │
└──────┬──────┘
       │ approved
       ▼
   Final Summary
```

---

## Project Structure

```
01_basic_agent/
├── api/
│   ├── agent.py          ← LangGraph workflow (AgentState, Generator node, Critic node, graph)
│   ├── main.py           ← FastAPI server (/health, /analyze)
│   ├── requirements.txt
│   └── Dockerfile
├── ui/
│   ├── app.py            ← Streamlit frontend
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── .env
```

---

## Requirements

**`api/requirements.txt`**
```
fastapi[standard]>=0.110.0
langchain-core>=0.1.30
langgraph>=0.0.26
litellm>=1.34.0
pydantic>=2.6.0
python-dotenv>=1.0.1
uvicorn>=0.28.0
```

**`ui/requirements.txt`**
```
streamlit>=1.32.0
requests>=2.31.0
```

**External dependencies:** Python 3.11+, Docker & Docker Compose, OpenAI API key

---

## Environment File (`.env`)

```env
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

---

## Running the Project

```bash
cd 01_basic_agent
docker compose up --build
```

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

---

## API Endpoints

| Method | Path | Input | Output |
|---|---|---|---|
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/analyze` | `{"text": "patient description"}` | `{"final_summary": "...", "history": "..."}` |

---

## UI Walkthrough

1. Open http://localhost:8501
2. Paste patient symptoms or lab results into the text area
3. Click **Analyze with Agent**
4. The spinner runs while the Generator → Critic loop executes
5. The **Final Approved Medical Summary** is shown once the Critic approves
6. Expand **View Agent Thinking History** to see each Generator draft and Critic review

---

## Implementation Notes

### Agent State
Define a `TypedDict` called `AgentState` with these fields: `input_text` (str), `messages` (accumulated with `operator.add`), `draft` (str), `feedback` (str), `is_approved` (bool).

### Generator Node
Takes `input_text` and optionally `feedback`. Calls the LLM with a prompt instructing it to summarize symptoms professionally without making an explicit diagnosis. Returns updated `draft` and `messages`.

### Critic Node
Takes `draft`. Calls the LLM asking for structured JSON output (`is_approved: bool`, `feedback: str`). Checks for: no explicit diagnosis, professional tone, no hallucinations. Returns `is_approved`, `feedback`, and `messages`.

### Conditional Edge (`should_continue`)
Returns `END` if `is_approved` is `True`, otherwise returns `"generator"` to loop back.

### Graph Construction
- Entry point: `generator`
- Edge: `generator → critic`
- Conditional edge: `critic → should_continue`
- Compile with `recursion_limit=5` to cap iterations

### LLM Calls
- Use `litellm.completion()` for both nodes
- Generator: `temperature=0.2`
- Critic: `temperature=0.0` with `response_format={"type": "json_object"}` for reliable JSON output
- Load model name from env: `os.getenv("LLM_MODEL", "gpt-4o-mini")`

---

## Example Input

```
Patient is a 45-year-old male with a 3-day history of:
- Severe headache (9/10 intensity), photophobia, neck stiffness
- Nausea and one episode of vomiting
- Temperature 38.7°C, HR 94
- CBC: WBC 14,200 (elevated), neutrophils 85%
- CSF: cloudy, protein elevated, glucose low
```

## Example Output

**Final Approved Medical Summary:**
```
The patient is a 45-year-old male presenting with a 3-day history of severe headache
(9/10), photophobia, neck stiffness, nausea, and vomiting. Vital signs show low-grade
fever (38.7°C) and mild tachycardia (HR 94). Laboratory findings reveal leukocytosis
(WBC 14,200, 85% neutrophils). CSF is cloudy with elevated protein and low glucose,
indicating significant meningeal inflammation requiring urgent evaluation.
```

**Agent Thinking History:**
```
[GENERATOR]: Initial draft produced.
[CRITIC]: approved=False | Draft explicitly states "bacterial meningitis"...
[GENERATOR]: Revised draft without explicit diagnosis.
[CRITIC]: approved=True |
```

---
