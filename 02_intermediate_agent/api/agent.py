import json
import operator
import os
import re
from typing import Annotated, TypedDict

import litellm
from langgraph.graph import END, StateGraph
from langgraph.types import Send

MODEL = os.getenv("LLM_MODEL", "groq/llama-3.3-70b-versatile")

# ---------------------------------------------------------------------------
# Specialist Registry — 20 specialists
# ---------------------------------------------------------------------------

SPECIALISTS = {
    "general_practitioner": {
        "name": "General Practitioner",
        "description": "Broad clinical assessment, triage, and coordination of care across organ systems.",
    },
    "cardiologist": {
        "name": "Cardiologist",
        "description": "Heart failure, arrhythmias, coronary artery disease, valvular disorders, and ECG interpretation.",
    },
    "neurologist": {
        "name": "Neurologist",
        "description": "Stroke, seizures, headache syndromes, neurodegenerative diseases, and CNS infections.",
    },
    "nephrologist": {
        "name": "Nephrologist",
        "description": "Acute kidney injury, chronic kidney disease, electrolyte disorders, and renal replacement therapy.",
    },
    "pulmonologist": {
        "name": "Pulmonologist",
        "description": "COPD, asthma, pneumonia, pleural effusion, pulmonary embolism, and respiratory failure.",
    },
    "hematologist": {
        "name": "Hematologist",
        "description": "Anemia, coagulopathies, leukemia, lymphoma, thrombosis, and bone marrow disorders.",
    },
    "endocrinologist": {
        "name": "Endocrinologist",
        "description": "Diabetes, thyroid disorders, adrenal insufficiency, pituitary disease, and metabolic syndrome.",
    },
    "oncologist": {
        "name": "Oncologist",
        "description": "Cancer staging, chemotherapy, targeted therapy, palliative oncology, and paraneoplastic syndromes.",
    },
    "geriatrician": {
        "name": "Geriatrician",
        "description": "Frailty, polypharmacy, falls, delirium, dementia, and complex multi-morbidity in older adults.",
    },
    "psychiatrist": {
        "name": "Psychiatrist",
        "description": "Depression, anxiety, psychosis, delirium, substance use, and psychosomatic medicine.",
    },
    "infectious_disease": {
        "name": "Infectious Disease Specialist",
        "description": "Sepsis, bacterial and viral infections, antimicrobial stewardship, and immunocompromised hosts.",
    },
    "rheumatologist": {
        "name": "Rheumatologist",
        "description": "Autoimmune diseases, inflammatory arthritis, vasculitis, lupus, and connective tissue disorders.",
    },
    "vascular_surgeon": {
        "name": "Vascular Surgeon",
        "description": "Peripheral arterial disease, DVT, aortic aneurysm, carotid stenosis, and limb ischemia.",
    },
    "cardiothoracic_surgeon": {
        "name": "Cardiothoracic Surgeon",
        "description": "Surgical indications for cardiac and thoracic conditions including valve repair and lung resection.",
    },
    "radiologist": {
        "name": "Radiologist",
        "description": "Interpretation of imaging findings: CXR, CT, MRI, ultrasound, and nuclear medicine studies.",
    },
    "clinical_pharmacist": {
        "name": "Clinical Pharmacist",
        "description": "Drug interactions, dosing adjustments, renal/hepatic dosing, and medication reconciliation.",
    },
    "dietitian": {
        "name": "Clinical Dietitian",
        "description": "Nutritional assessment, enteral and parenteral nutrition, dietary management of chronic disease.",
    },
    "physiotherapist": {
        "name": "Physiotherapist",
        "description": "Mobility assessment, rehabilitation, respiratory physiotherapy, and exercise prescription.",
    },
    "palliative_care": {
        "name": "Palliative Care Specialist",
        "description": "Symptom management, goals of care, end-of-life planning, and advance care directives.",
    },
    "emergency_physician": {
        "name": "Emergency Physician",
        "description": "Acute resuscitation, triage, undifferentiated emergencies, and stabilisation protocols.",
    },
}

# Pre-build the specialist menu string for the supervisor prompt
SPECIALIST_MENU = "\n".join(
    f"- {key}: {info['name']} — {info['description']}"
    for key, info in SPECIALISTS.items()
)

ALL_KEYS = list(SPECIALISTS.keys())


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    case_description: str
    top_k: int
    specialists_to_run: list[str]
    assessments: Annotated[list[dict], operator.add]
    final_summary: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def supervisor_node(state: AgentState) -> dict:
    top_k = state.get("top_k", 5)
    case = state["case_description"]

    prompt = (
        f"You are a medical case coordinator. Given the clinical case below, "
        f"select exactly {top_k} specialist(s) from the list who are most relevant to this case.\n\n"
        f"Clinical case:\n{case}\n\n"
        f"Available specialists:\n{SPECIALIST_MENU}\n\n"
        f"Return ONLY a JSON array of exactly {top_k} specialist keys. "
        f"Example: [\"cardiologist\", \"nephrologist\"]\n"
        f"Choose only keys from the list above. Return nothing else."
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()

    # Robustly extract JSON array
    selected: list[str] = []
    try:
        # Try direct parse first (response_format may wrap in object)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            selected = parsed
        else:
            # Find first list value in the dict
            for v in parsed.values():
                if isinstance(v, list):
                    selected = v
                    break
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: regex extraction
    if not selected:
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                selected = json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # Keep only valid keys
    selected = [k for k in selected if k in SPECIALISTS]

    # Pad with defaults if LLM returned fewer than top_k
    if len(selected) < top_k:
        for key in ALL_KEYS:
            if key not in selected:
                selected.append(key)
            if len(selected) >= top_k:
                break

    selected = selected[:top_k]

    return {"specialists_to_run": selected}


def route_to_specialists(state: AgentState) -> list[Send]:
    return [
        Send("specialist_runner", {
            "case_description": state["case_description"],
            "specialist_key": key,
        })
        for key in state["specialists_to_run"]
    ]


def specialist_runner(state: dict) -> dict:
    case = state["case_description"]
    key = state["specialist_key"]
    specialist = SPECIALISTS[key]

    prompt = (
        f"You are a {specialist['name']}. {specialist['description']}\n\n"
        f"Analyze the following clinical case from your specialist perspective.\n\n"
        f"Clinical case:\n{case}\n\n"
        f"Provide a focused assessment covering:\n"
        f"1. Key findings relevant to your specialty\n"
        f"2. Differential diagnoses or concerns\n"
        f"3. Recommended investigations\n"
        f"4. Management recommendations\n\n"
        f"Be concise and clinically precise."
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    assessment_text = response.choices[0].message.content.strip()

    return {
        "assessments": [{
            "role": specialist["name"],
            "key": key,
            "assessment": assessment_text,
        }]
    }


def aggregator_node(state: AgentState) -> dict:
    assessments = state["assessments"]

    combined = "\n\n".join(
        f"=== {a['role']} ===\n{a['assessment']}"
        for a in assessments
    )

    prompt = (
        f"You are a senior clinician synthesizing assessments from {len(assessments)} specialists.\n\n"
        f"Specialist assessments:\n{combined}\n\n"
        f"Write an integrated clinical summary that includes:\n"
        f"1. Most-likely diagnosis / differential\n"
        f"2. Critical findings and red flags\n"
        f"3. Areas of consensus among specialists\n"
        f"4. Areas of divergence or uncertainty\n"
        f"5. Prioritized management plan\n\n"
        f"Be comprehensive but concise."
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return {"final_summary": response.choices[0].message.content.strip()}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("specialist_runner", specialist_runner)
    graph.add_node("aggregator", aggregator_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", route_to_specialists, ["specialist_runner"])
    graph.add_edge("specialist_runner", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()


agent_graph = build_graph()


def run_agent(case_description: str, top_k: int = 5) -> dict:
    initial_state: AgentState = {
        "case_description": case_description,
        "top_k": top_k,
        "specialists_to_run": [],
        "assessments": [],
        "final_summary": "",
    }

    final_state = agent_graph.invoke(initial_state)

    return {
        "assessments": final_state["assessments"],
        "final_summary": final_state["final_summary"],
    }
