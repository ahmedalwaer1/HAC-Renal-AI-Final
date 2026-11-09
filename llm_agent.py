"""HAC-Renal AI LangChain AI Agent Module.

This module provides the AI Agent layer that wraps deterministic Python tools
with a LangChain agent using an LLM via API key.
"""

import json
import os

from agents.ai_tools import (
    calculate_creatinine_clearance,
    get_vancomycin_regimen,
    get_meropenem_regimen,
    search_knowledge_base,
    check_safety_rules,
    check_interaction,
)
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_agent_executor(api_key: str, base_url: str, model_name: str) -> AgentExecutor:
    """Initialize and return a LangChain AgentExecutor.

    Raises ValueError if api_key is empty or equals "your_api_key_here".
    """
    if not api_key or api_key == "your_api_key_here":
        raise ValueError("API key must be provided and not be the placeholder 'your_api_key_here'")

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0,
        max_tokens=2000,
    )

    tools = [
        calculate_creatinine_clearance,
        get_vancomycin_regimen,
        get_meropenem_regimen,
        search_knowledge_base,
        check_safety_rules,
        check_interaction,
    ]

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are HAC-Renal AI, a strict clinical decision support system for antibiotic dosing in renal impairment. "
            "CRITICAL RULES: "
            "1) You MUST use the provided tools to calculate doses and check safety. "
            "NEVER calculate doses or invent medical rules yourself. "
            "2) If critical data like weight, creatinine, or age is missing, ask the user for it. "
            "3) Always cite the rule_id and source URL in your final response. "
            "4) If a safety rule is triggered like allergy or drug interaction, block the recommendation immediately and explain why. "
            "5) Keep your final response professional, clear, and structured.",
        ),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)


def _fallback_deterministic(patient_input):
    """Run the deterministic rules engine (safety checks + dosing)."""
    from rules_engine import apply_rules
    return apply_rules(patient_input)


def evaluate_patient_via_agent(patient_input):
    """Evaluate a patient through the LLM agent when an API key is configured,
    otherwise fall back to the deterministic rules engine.

    Always returns a dict containing a "decision" key so callers/tests can
    reason about the outcome uniformly.
    """
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    model_name = os.getenv("LLM_MODEL_NAME", "deepseek/deepseek-chat")

    if not api_key or api_key == "your_api_key_here":
        return _fallback_deterministic(patient_input)

    try:
        executor = create_agent_executor(api_key, base_url, model_name)
        result = executor.invoke({"input": json.dumps(patient_input)})
        return {
            "decision": "AGENT_RESPONSE",
            "output": result.get("output", ""),
            "clinical_review_required": True,
        }
    except Exception as e:
        fallback = _fallback_deterministic(patient_input)
        fallback.setdefault("agent_note", f"LLM unavailable: {e}")
        return fallback


# ---------------------------------------------------------------------------
# Conversational layer: the model only PARSES input and NARRATES output.
# Every number still comes from the deterministic engine (rules_engine.py).
# ---------------------------------------------------------------------------
_EXTRACTION_SYSTEM = (
    "You convert a clinician's free-text note, written in any language, into "
    "structured patient data for a renal dosing engine. "
    "Return ONLY one JSON object - no prose, no markdown. "
    "Never invent a value: include a field only when the clinician stated it or "
    "it already exists in KNOWN_DATA. Keep KNOWN_DATA unless the clinician "
    "corrects it. "
    "Allowed fields: requested_drug, age_years, weight_kg, gender (Male|Female), "
    "creatinine (mg/dL), crcl_ml_min, indication_group, "
    "infusion_strategy (Short_Infusion|Extended_Infusion), "
    "infection_type, "
    "dialysis {status (Yes|No), modality, flow_rate_l_per_hour}, "
    "allergy_history [{\"substance\", \"reaction\", \"certainty\"}], "
    "concomitant_medications [{\"drug\"}], culture_result, "
    "infection_documented (true|false). "
    "OPEN VOCABULARY: for indication_group, infection_type and "
    "dialysis.modality copy the clinician's OWN clinical wording verbatim "
    "(for example \"MRSA bacteraemia\", \"ventilator-associated pneumonia\", "
    "\"cystic fibrosis\", \"continuous venovenous haemodialysis\"). Do NOT "
    "force the wording into a fixed list and never substitute a category the "
    "clinician did not state; a deterministic clinical-vocabulary layer maps "
    "the wording onto the source category. "
    "Set dialysis.status to Yes or No only when it is clearly stated; when the "
    "clinician names a modality keep that exact wording in dialysis.modality. "
    "Also add \"__language\" holding the ISO-639-1 code of the clinician's message."
)

_NARRATION_SYSTEM = (
    "You are HAC-Renal AI, a clinical pharmacist writing a consultation note for "
    "another pharmacist or prescriber. A deterministic Python engine has already "
    "produced ENGINE_RESULT; you only explain it. "
    "ABSOLUTE RULES: never change, recompute, round or invent any dose, number or "
    "threshold; use only ENGINE_RESULT and EVIDENCE. "
    "WRITE LIKE A CLINICAL PHARMACIST, NOT LIKE A PROGRAMMER: use standard "
    "drug-therapy wording (loading dose, maintenance dose, infusion duration, renal "
    "clearance, therapeutic drug monitoring, trough, AUC, MIC, renal replacement "
    "therapy). Explain what the rule means clinically instead of repeating it. "
    "NEVER mention code identifiers, rule ids (for example MER-001 or THER-003), "
    "function names, class names, file names, JSON field names, decision codes or "
    "any internal variable; if the source wording is technical, translate it into "
    "plain clinical language. "
    "Reply in the SAME language as the clinician's last message. "
    "If the decision is NEEDS_MORE_INFORMATION, give no dose and state precisely "
    "which clinical values are missing - list each one with its exact parameter "
    "name and unit (for example serum creatinine in mg/dL, CrCl in mL/min, weight "
    "in kg, age in years, dialysis status and modality, infection type or site); "
    "never say only that \"information is missing\". Then tell the clinician that "
    "sending these values in a follow-up message will produce the regimen. "
    "If the decision is UNSUPPORTED_DRUG, name the supported drugs and give no dose. "
    "Structure the reply with short clinical headings suited to the reply language "
    "(for example: القرار / النظام الجرعي / السلامة والملاءمة / المتابعة وإعادة "
    "التقييم / المراجع). "
    "In the references section, cite each source the way a pharmacist cites it: the "
    "issuing body and the document name, for example \"جدول UCSF لجرعات الميروبينيم "
    "(IDMP)\" or \"نشرة FDA/DailyMed للميروبينيم الوريدي\" - never a file name, path, "
    "link anchor or code. "
    "If ENGINE_RESULT contains classified_from, state explicitly which clinical "
    "category the clinician's own wording was mapped onto. "
    "If the decision is OUT_OF_DECLARED_BOUNDS, quote the declared_range and say "
    "the engine does not extrapolate past a validated range. "
    "End with one line stating this is decision support, not a prescription."
)


def _chat_model(api_key, base_url, model_name, temperature=0.0, max_tokens=1200):
    """Build a plain chat model (no tool loop) for parsing and narration."""
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _parse_json_object(text):
    """Extract the first JSON object from a model reply, tolerating code fences."""
    if not text:
        return {}
    cleaned = text.replace("```json", "```").replace("```JSON", "```")
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        data = json.loads(cleaned[start:end + 1])
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def extract_patient_from_text(message, api_key, base_url, model_name, known=None):
    """Turn a free-text note (any language) into structured patient data.

    Returns (patient_dict, language_code). The model extracts only what the
    clinician actually stated; nothing is inferred.
    """
    llm = _chat_model(api_key, base_url, model_name)
    payload = {"known_data": known or {}, "clinician_message": message}
    reply = llm.invoke([
        SystemMessage(content=_EXTRACTION_SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ])
    data = _parse_json_object(getattr(reply, "content", "") or "")
    language = str(data.pop("__language", "") or "").strip() or None
    return data, language


def compose_clinical_reply(message, engine_result, evidence, language,
                           api_key, base_url, model_name):
    """Explain an engine result in the clinician's language, without new numbers."""
    llm = _chat_model(api_key, base_url, model_name)
    payload = {
        "reply_language": language or "same language as the clinician's message",
        "clinician_message": message,
        "ENGINE_RESULT": engine_result,
        "EVIDENCE": {
            "source_rule": (evidence or {}).get("source_rule"),
            "source_note": (evidence or {}).get("source_note"),
            "sources": (evidence or {}).get("sources"),
            "sections": (evidence or {}).get("sections"),
        },
    }
    reply = llm.invoke([
        SystemMessage(content=_NARRATION_SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)),
    ])
    return (getattr(reply, "content", "") or "").strip()


def test_agent_load():
    """Verify that all imports work correctly.

    Prints confirmation message if all imports succeed.
    """
    print("AI Agent module loaded successfully")