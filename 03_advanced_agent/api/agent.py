import json
import operator
import os
import re
from typing import Annotated, TypedDict

import litellm
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from tools import format_soap_template, get_icd10_code

MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    raw_text: str
    conditions: list[str]
    medications: list[dict]
    extractions: Annotated[list[dict], operator.add]
    soap_draft: str


# ---------------------------------------------------------------------------
# Node 1: Condition Extractor
# ---------------------------------------------------------------------------

def condition_extractor(state: AgentState) -> dict:
    prompt = (
        "You are a clinical NLP specialist. Extract all distinct medical conditions, "
        "diseases, and diagnoses from the clinical text below.\n\n"
        f"Clinical text:\n{state['raw_text']}\n\n"
        "Return ONLY a JSON array of condition strings. Example:\n"
        '["hypertension", "type 2 diabetes", "heart failure"]\n'
        "Include only medical conditions — not symptoms, medications, or lab values."
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    raw = response.choices[0].message.content.strip()

    conditions: list[str] = []
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            conditions = json.loads(match.group())
        except json.JSONDecodeError:
            pass

    if not conditions:
        try:
            conditions = json.loads(raw)
        except json.JSONDecodeError:
            conditions = []

    return {"conditions": [str(c) for c in conditions if c]}


# ---------------------------------------------------------------------------
# Node 2: Medication Extractor
# ---------------------------------------------------------------------------

def medication_extractor(state: AgentState) -> dict:
    prompt = (
        "You are a clinical pharmacist. Extract all medications from the clinical text below.\n\n"
        f"Clinical text:\n{state['raw_text']}\n\n"
        "For each medication return exactly three fields: drug, dosage, route.\n"
        "Do NOT include frequency or duration.\n"
        "Return ONLY a JSON array. Example:\n"
        '[{"drug": "atorvastatin", "dosage": "40 MG", "route": "Oral"}]\n'
        "If no medications are found, return an empty array []."
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()

    medications: list[dict] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            medications = parsed
        else:
            for v in parsed.values():
                if isinstance(v, list):
                    medications = v
                    break
    except json.JSONDecodeError:
        pass

    # Ensure only allowed fields
    clean = []
    for med in medications:
        if isinstance(med, dict) and "drug" in med:
            clean.append({
                "drug": med.get("drug", ""),
                "dosage": med.get("dosage", ""),
                "route": med.get("route", ""),
            })

    return {"medications": clean}


# ---------------------------------------------------------------------------
# Node 3: Condition Coder (ICD-10)
# ---------------------------------------------------------------------------

def condition_coder(state: AgentState) -> dict:
    conditions = state.get("conditions", [])
    if not conditions:
        return {"extractions": []}

    conditions_list = "\n".join(f"- {c}" for c in conditions)
    prompt = (
        "You are a medical coding specialist. Assign ICD-10-CM codes to each condition below.\n\n"
        f"Conditions:\n{conditions_list}\n\n"
        "Return ONLY a JSON array where each item has: chunk (condition name), entity_type, ICD10 (code).\n"
        "Example:\n"
        '[{"chunk": "hypertension", "entity_type": "medical_condition", "ICD10": "I10"}]\n'
        "Use the most specific ICD-10-CM code available."
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()

    coded: list[dict] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            coded = parsed
        else:
            for v in parsed.values():
                if isinstance(v, list):
                    coded = v
                    break
    except json.JSONDecodeError:
        pass

    # Validate and fallback
    result = []
    for i, condition in enumerate(conditions):
        if i < len(coded) and isinstance(coded[i], dict) and coded[i].get("ICD10"):
            entry = coded[i]
            entry["entity_type"] = "medical_condition"
            result.append(entry)
        else:
            result.append({
                "chunk": condition,
                "entity_type": "medical_condition",
                "ICD10": get_icd10_code(condition),
            })

    return {"extractions": result}


# ---------------------------------------------------------------------------
# Node 4: Medication Coder (RxNorm)
# ---------------------------------------------------------------------------

def medication_coder(state: AgentState) -> dict:
    medications = state.get("medications", [])
    if not medications:
        return {"extractions": []}

    # Build chunk strings: drug + dosage + route
    chunks = [
        f"{m.get('drug', '')} {m.get('dosage', '')} {m.get('route', '')}".strip()
        for m in medications
    ]
    meds_list = "\n".join(f"- {c}" for c in chunks)

    prompt = (
        "You are a pharmacy informatics specialist. Assign RxNorm (RxCUI) codes to each medication.\n\n"
        f"Medications:\n{meds_list}\n\n"
        "Return ONLY a JSON array where each item has: chunk (medication string), entity_type, RxNorm (code).\n"
        "Example:\n"
        '[{"chunk": "atorvastatin 40 MG Oral", "entity_type": "drug", "RxNorm": "617310"}]\n'
        "Use numeric RxCUI codes only."
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()

    coded: list[dict] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            coded = parsed
        else:
            for v in parsed.values():
                if isinstance(v, list):
                    coded = v
                    break
    except json.JSONDecodeError:
        pass

    result = []
    for i, chunk in enumerate(chunks):
        if i < len(coded) and isinstance(coded[i], dict) and coded[i].get("RxNorm"):
            entry = coded[i]
            entry["entity_type"] = "drug"
            entry["chunk"] = chunk
            result.append(entry)
        else:
            result.append({
                "chunk": chunk,
                "entity_type": "drug",
                "RxNorm": "0",  # unknown fallback
            })

    return {"extractions": result}


# ---------------------------------------------------------------------------
# Node 5: SOAP Drafter
# ---------------------------------------------------------------------------

def soap_drafter(state: AgentState) -> dict:
    extractions = state.get("extractions", [])
    raw_text = state.get("raw_text", "")

    condition_lines = "\n".join(
        f"- {e['chunk']} (ICD-10: {e['ICD10']})"
        for e in extractions if e.get("entity_type") == "medical_condition"
    )
    drug_lines = "\n".join(
        f"- {e['chunk']} (RxNorm: {e['RxNorm']})"
        for e in extractions if e.get("entity_type") == "drug"
    )

    prompt = (
        "You are a clinical documentation specialist. Write the Assessment and Plan sections "
        "of a SOAP note based on the extracted information.\n\n"
        f"Identified conditions:\n{condition_lines or 'None identified'}\n\n"
        f"Medications:\n{drug_lines or 'None identified'}\n\n"
        "Write:\n"
        "1. A concise Assessment (A) section listing the primary conditions with their codes\n"
        "2. A concise Plan (P) section with management recommendations\n\n"
        "Format as:\nA: <assessment text>\nP: <plan text>"
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    ap_text = response.choices[0].message.content.strip()

    # Parse A and P sections
    assessment, plan = "", ""
    a_match = re.search(r"A:\s*(.*?)(?=\nP:|\Z)", ap_text, re.DOTALL)
    p_match = re.search(r"P:\s*(.*)", ap_text, re.DOTALL)
    if a_match:
        assessment = a_match.group(1).strip()
    if p_match:
        plan = p_match.group(1).strip()

    subjective = "Patient-reported symptoms and history from clinical document. [Review and complete.]"
    objective = f"Extracted from clinical record:\n{condition_lines}\n{drug_lines}".strip()

    soap = format_soap_template(subjective, objective, assessment, plan)
    return {"soap_draft": soap}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

checkpointer = MemorySaver()


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("condition_extractor", condition_extractor)
    graph.add_node("medication_extractor", medication_extractor)
    graph.add_node("condition_coder", condition_coder)
    graph.add_node("medication_coder", medication_coder)
    graph.add_node("soap_drafter", soap_drafter)

    graph.set_entry_point("condition_extractor")
    graph.add_edge("condition_extractor", "medication_extractor")
    graph.add_edge("medication_extractor", "condition_coder")
    graph.add_edge("condition_coder", "medication_coder")
    graph.add_edge("medication_coder", "soap_drafter")
    graph.add_edge("soap_drafter", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_after=["soap_drafter"],
    )


agent_graph = build_graph()


# ---------------------------------------------------------------------------
# Entry point functions
# ---------------------------------------------------------------------------

def start_workflow(thread_id: str, raw_text: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    initial_state: AgentState = {
        "raw_text": raw_text,
        "conditions": [],
        "medications": [],
        "extractions": [],
        "soap_draft": "",
    }

    agent_graph.invoke(initial_state, config=config)

    snapshot = agent_graph.get_state(config)
    state = snapshot.values

    return {
        "soap_draft": state.get("soap_draft", ""),
        "extractions": state.get("extractions", []),
    }


def update_workflow_and_resume(thread_id: str, updated_soap: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}

    agent_graph.update_state(config, {"soap_draft": updated_soap})
    final = agent_graph.invoke(None, config=config)

    return {
        "final_soap_note": final.get("soap_draft", updated_soap),
    }
