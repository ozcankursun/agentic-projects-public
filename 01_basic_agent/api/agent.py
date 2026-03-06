import json
import operator
import os
from typing import Annotated, TypedDict

import litellm
from langgraph.graph import END, StateGraph

MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


class AgentState(TypedDict):
    input_text: str
    messages: Annotated[list[str], operator.add]
    draft: str
    feedback: str
    is_approved: bool


def generator_node(state: AgentState) -> dict:
    print("\n" + "="*50)
    print("▶ NODE: GENERATOR")
    print(f"   feedback var mı: {'EVET → revize mod' if state.get('feedback') else 'HAYIR → ilk taslak'}")
    input_text = state["input_text"]
    feedback = state.get("feedback", "")

    if feedback:
        prompt = (
            "You are a clinical documentation assistant. Revise the medical summary below "
            "based on the critic's feedback.\n\n"
            f"Original patient information:\n{input_text}\n\n"
            f"Critic feedback:\n{feedback}\n\n"
            "Rules you MUST follow:\n"
            "- Do NOT write an explicit diagnosis sentence like 'the patient has X disease'\n"
            "- Use objective, professional clinical language\n"
            "- Only include facts from the patient information\n"
            "- Describe findings and observations, not conclusions\n\n"
            "Write ONLY the revised medical summary, nothing else:"
        )
    else:
        prompt = (
            "You are a clinical documentation assistant. Write a concise professional medical summary "
            "of the patient information below.\n\n"
            f"Patient information:\n{input_text}\n\n"
            "Rules you MUST follow:\n"
            "- Do NOT write an explicit diagnosis sentence like 'the patient has X disease'\n"
            "- Use objective, professional clinical language\n"
            "- Only include facts from the patient information\n"
            "- Describe findings and observations, not conclusions\n\n"
            "Write ONLY the medical summary, nothing else:"
        )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    draft = response.choices[0].message.content.strip()

    label = "Revised draft produced" if feedback else "Initial draft produced"
    print(f"   draft (ilk 100 karakter): {draft[:100]}...")
    print("="*50)
    return {"draft": draft, "messages": [f"[GENERATOR]: {label}."]}


def critic_node(state: AgentState) -> dict:
    print("\n" + "="*50)
    print("▶ NODE: CRITIC")
    draft = state["draft"]

    prompt = (
        "You are a medical safety reviewer. Evaluate this medical summary strictly on ONE rule:\n\n"
        "REJECT if the summary contains an EXPLICIT DIAGNOSIS statement such as:\n"
        "- 'the patient has [disease name]'\n"
        "- 'this is consistent with [disease name]'\n"
        "- 'findings confirm [disease name]'\n"
        "- 'presenting with [disease name]'\n\n"
        "APPROVE if the summary only describes symptoms, vitals, lab values, and clinical observations "
        "WITHOUT naming a specific diagnosis.\n\n"
        f"Medical summary to evaluate:\n{draft}\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"is_approved": true, "feedback": ""}\n'
        "OR\n"
        '{"is_approved": false, "feedback": "Quote the exact diagnosis phrase and instruct to remove it"}'
    )

    response = litellm.completion(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    result = json.loads(raw)

    is_approved = bool(result.get("is_approved", False))
    feedback = result.get("feedback", "")

    status = "approved=True" if is_approved else f"approved=False | {feedback}"
    print(f"   karar: {'✅ ONAYLANDI' if is_approved else '❌ REDDEDİLDİ'}")
    if not is_approved:
        print(f"   sebep: {feedback}")
    print("="*50)
    return {
        "is_approved": is_approved,
        "feedback": feedback,
        "messages": [f"[CRITIC]: {status}"],
    }


def should_continue(state: AgentState) -> str:
    if state.get("is_approved", False):
        print("\n🏁 KARAR: Workflow bitti → END")
        return END
    print("\n🔄 KARAR: Geri dönüyor → GENERATOR")
    return "generator"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("generator", generator_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("generator")
    graph.add_edge("generator", "critic")
    graph.add_conditional_edges(
        "critic",
        should_continue,
        {END: END, "generator": "generator"},
    )

    return graph.compile()


agent_graph = build_graph()


def run_agent(input_text: str) -> dict:
    initial_state: AgentState = {
        "input_text": input_text,
        "messages": [],
        "draft": "",
        "feedback": "",
        "is_approved": False,
    }

    # 5 iterations × 2 nodes = 10 steps; set limit to 12 for safety
    config = {"recursion_limit": 12}
    final_state = agent_graph.invoke(initial_state, config=config)

    return {
        "final_summary": final_state["draft"],
        "history": "\n".join(final_state["messages"]),
    }
