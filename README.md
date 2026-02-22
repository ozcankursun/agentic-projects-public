# Agentic Projects — Student Implementation Guide

A hands-on series of three healthcare AI projects, each building on the last. By completing all three, students progress from a simple two-node loop to a full stateful multi-agent pipeline with human oversight.

---

## What You Will Learn

### Agentic AI Concepts
- How to define and manage **state** that flows through a multi-node graph
- How to build **reflection loops** where agents critique and improve each other's output
- How to **route tasks dynamically** at runtime using LLM-driven supervisor logic
- How to run multiple agents **in parallel** and merge their results
- How to **pause and resume** a workflow for human review using stateful checkpoints

### LangGraph Skills
- Building graphs with `StateGraph`, nodes, edges, and conditional edges
- Using `operator.add` as a state reducer for parallel node outputs
- Using the `Send` API to fan-out work across multiple node instances
- Compiling a graph with `interrupt_after` and `MemorySaver` for human-in-the-loop flows
- Resuming a paused graph with `update_state` + `invoke(None)`

### Software Engineering Skills
- Structuring a project as a **FastAPI backend + Streamlit frontend** microservice pair
- Containerising both services with **Docker** and wiring them via **Docker Compose**
- Calling LLMs through **LiteLLM** for provider-agnostic model access
- Parsing and validating **structured JSON output** from LLM responses using Pydantic
- Extracting text from **PDF, TXT, and CSV** files programmatically

### Healthcare AI Domain Knowledge
- Why **ICD-10-CM** codes matter and how they map to medical conditions
- What **RxNorm (RxCUI)** codes are and how they standardise medication references
- How a **SOAP note** is structured and used in clinical documentation
- Why clinical AI needs **human review gates** — safety, accuracy, and accountability

---

## Project Summaries

### Project 01 — Basic Agent
**Pattern:** Reflection Loop (Generator → Critic)

A patient symptom description is passed to a **Generator** agent that drafts a medical summary. A **Critic** agent then reviews the draft, checking that it does not make explicit diagnoses, uses professional clinical tone, and does not hallucinate facts. If the Critic rejects the draft, it sends back specific feedback and the Generator refines it. This loop runs up to 5 times until the Critic approves.

---

### Project 02 — Intermediate Agent
**Pattern:** Supervisor + Parallel Fan-Out + Aggregator

A medical case is sent to a **Supervisor** LLM that reads the case and selects the most relevant specialists from a pool of 20. The selected specialists all analyze the case **simultaneously** using LangGraph's `Send` API. An **Aggregator** then synthesizes all specialist assessments into a single integrated clinical summary. Users control how many specialists are consulted (1–20) via a slider in the UI.

---

### Project 03 — Advanced Agent
**Pattern:** Sequential Multi-Phase Pipeline + Human-in-the-Loop

Clinical documents (PDF, TXT, CSV) are processed through a 5-node sequential pipeline: conditions and medications are extracted, then ICD-10-CM and RxNorm codes are assigned, and finally a SOAP note is drafted. The workflow **pauses** after the SOAP draft is produced, allowing a clinician to review and edit the note in the UI before approving. Once approved, the workflow resumes and the final note is signed off.

---

## Project Progression

```
01 Basic          Reflection loop        2 nodes     Text in → Text out
      ↓
02 Intermediate   Supervisor + parallel  3 roles     Text in → Multi-specialist summary
      ↓
03 Advanced       Sequential pipeline    5 nodes     Files in → Coded entities + SOAP note
                  + human approval
```

Each project introduces new concepts:

| Feature | 01 | 02 | 03 |
|---|---|---|---|
| Conditional edges | ✓ | ✓ | — |
| `Send` API (parallel fan-out) | — | ✓ | — |
| `operator.add` reducer | ✓ | ✓ | ✓ |
| LLM supervisor routing | — | ✓ | — |
| `interrupt_after` (human gate) | — | — | ✓ |
| `MemorySaver` + `update_state` | — | — | ✓ |
| File ingestion (PDF/TXT/CSV) | — | — | ✓ |
| Multi-state UI | — | — | ✓ |
| Terminology coding (ICD-10 / RxNorm) | — | — | ✓ |

---

## Project 01 — Detailed Guide

### Flowchart
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

## Project 02 — Detailed Guide

### Flowchart
```
Medical Case Input
       │
       ▼
┌──────────────┐
│  Supervisor  │  (LLM selects top_k specialist keys)
└──────┬───────┘
       │  Send API fan-out
       ▼
┌──────┬──────┬──────┐
│Spec 1│Spec 2│Spec N│  (run in parallel)
└──────┴──────┴──────┘
       │  results merged via operator.add
       ▼
┌──────────────┐
│  Aggregator  │  (synthesizes all assessments)
└──────┬───────┘
       │
       ▼
  Final Summary
```

## Project 03 — Detailed Guide

### Flowchart
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

## Student Evaluation Rubric

### Project 01 — Basic Agent (100 points)

| Category | Criteria | Points |
|---|---|---|
| **State Design** | `AgentState` TypedDict has all 5 fields; `operator.add` used on `messages` | 10 |
| **Generator Node** | Correctly returns `draft` and appends to `messages`; uses `feedback` when present | 15 |
| **Critic Node** | Returns structured `is_approved` + `feedback`; uses `temperature=0.0` and `response_format=json_object` | 15 |
| **Conditional Edge** | `should_continue` correctly returns `END` or `"generator"` | 10 |
| **Graph Construction** | Entry point, edges, conditional edge, and `recursion_limit=5` all correctly set | 10 |
| **API** | `/health` and `/analyze` endpoints functional; returns `final_summary` and `history` | 15 |
| **UI** | Spinner, result display, and thinking history expander all working | 10 |
| **Docker** | Both services start cleanly; ports accessible; volumes mounted | 10 |
| **Safety** | Generator never states an explicit diagnosis in the approved output | 5 |
| **Total** | | **100** |

**Critique points to watch:**
- Does the Critic actually reject drafts that contain explicit diagnoses, or always approve?
- Does the Generator meaningfully use the Critic's feedback to improve the draft?
- Is the `recursion_limit` correctly set to prevent infinite loops?

---

### Project 02 — Intermediate Agent (100 points)

| Category | Criteria | Points |
|---|---|---|
| **Specialist Registry** | All 20 specialists defined with accurate names and descriptions | 15 |
| **Agent State** | `operator.add` on `assessments`; `top_k` field present | 10 |
| **Supervisor Node** | LLM correctly selects `top_k` keys; JSON parsed robustly; fallback padding works | 20 |
| **Send API Fan-Out** | `route_to_specialists` returns correct list of `Send` objects | 15 |
| **Specialist Runner** | Each specialist provides domain-specific analysis in its role | 10 |
| **Aggregator Node** | Synthesizes consensus, divergence, and prioritized management plan | 10 |
| **API** | `/analyze` accepts `top_k` field; correct response structure | 10 |
| **UI** | Sidebar slider works; each specialist assessment shown in a separate tab | 5 |
| **Docker** | Both services start cleanly | 5 |
| **Total** | | **100** |

**Critique points to watch:**
- Do all parallel specialist nodes actually run? Verify with 3+ specialists selected.
- Does the supervisor select the *right* specialists for the given case, or pick random ones?
- Does the aggregator reflect actual consensus/disagreement, or just list assessments?
- Does `top_k=1` work as well as `top_k=20`?

---

### Project 03 — Advanced Agent (100 points)

| Category | Criteria | Points |
|---|---|---|
| **Pipeline Order** | All 5 nodes run sequentially in the correct order | 10 |
| **Condition Extractor** | Accurately extracts conditions as a string list from clinical text | 10 |
| **Medication Extractor** | Correctly extracts only `drug + dosage + route` — no frequency or other fields | 10 |
| **Condition Coder** | ICD-10-CM codes assigned and formatted correctly; fallback handled | 10 |
| **Medication Coder** | RxNorm codes assigned; `chunk` string built from 3 fields | 10 |
| **SOAP Drafter** | SOAP note correctly formatted with all four sections | 10 |
| **Human-in-the-Loop** | Workflow genuinely pauses at interrupt; edits are preserved after resume | 15 |
| **API** | All 5 endpoints functional; storage mode works with `data/` volume | 15 |
| **UI** | All 3 states (idle, awaiting_approval, completed) render and transition correctly | 5 |
| **Docker** | `./data:/app/data` volume mounted; both services start cleanly | 5 |
| **Total** | | **100** |

**Critique points to watch:**
- Does the workflow actually pause after the SOAP draft, or does it skip the interrupt?
- Are human edits to the SOAP note preserved in the final output, or overwritten?
- Does the medication extractor avoid including frequency/duration information?
- Do both `/upload` and `/process-storage` endpoints produce the same output format?
- Does selecting multiple files produce a combined analysis, not separate ones?

---

## Common Mistakes to Avoid

| Mistake | Project | How to avoid |
|---|---|---|
| Using `interrupt_before=[END]` instead of `interrupt_after=["node_name"]` | 03 | Always name the actual node, never interrupt on `END` |
| Missing `operator.add` reducer on accumulating state fields | 02, 03 | Use `Annotated[List[dict], operator.add]` for any field that multiple nodes write to |
| `DATA_DIR` set to a relative path that doesn't exist inside the container | 03 | Use `/app/data` (absolute path matching the Docker volume mount target) |
| LLM sometimes returns fewer keys than `top_k` | 02 | Always implement fallback padding after parsing the supervisor response |
| Critic always approves on first iteration | 01 | Test with a draft that clearly states an explicit diagnosis — Critic must reject it |
| Not restarting the API container after code changes | 02, 03 | Run `docker compose restart api` — the API has no hot-reload |

---

