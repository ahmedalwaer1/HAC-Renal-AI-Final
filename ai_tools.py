"""LangChain tools wrapping deterministic dosing functions."""

import os
import sys
from typing import Optional, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from langchain.tools import tool
from tools.crcl_calculator import calculate_crcl
from tools.vancomycin_dosing import get_vancomycin_dose
from tools.meropenem_dosing import get_meropenem_dose
from data.clinical_data import get_safety_rule, get_interaction


@tool
def calculate_creatinine_clearance(age: float, weight_kg: float, creatinine: float, gender: str) -> str:
    """Calculate CrCl (mL/min) using Cockcroft-Gault."""
    try:
        crcl = calculate_crcl(age, weight_kg, creatinine, gender)
        return f"CrCl = {crcl:.1f} mL/min"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_vancomycin_regimen(age: Optional[float] = None, weight_kg: Optional[float] = None,
    crcl_ml_min: Optional[float] = None, creatinine: Optional[float] = None,
    gender: Optional[str] = None, infection_type: str = "complicated",
    dialysis_modality: Optional[str] = None) -> str:
    """Vancomycin dosing per UCSF nomogram (VAN-001 to VAN-021)."""
    try:
        result = get_vancomycin_dose(age=age, weight_kg=weight_kg, crcl_ml_min=crcl_ml_min,
            creatinine=creatinine, gender=gender, infection_type=infection_type,
            dialysis_modality=dialysis_modality)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_meropenem_regimen(crcl_ml_min: Optional[float] = None, age: Optional[float] = None,
    weight_kg: Optional[float] = None, creatinine: Optional[float] = None,
    gender: Optional[str] = None, indication_group: Optional[str] = None,
    infusion_strategy: Optional[str] = None, dialysis_modality: Optional[str] = None,
    cvvhd_flow_rate: Optional[float] = None, allergy_history: Optional[List] = None,
    concomitant_medications: Optional[List] = None) -> str:
    """Meropenem dosing per UCSF rules (MER-001 to MER-011)."""
    try:
        result = get_meropenem_dose(crcl_ml_min=crcl_ml_min, age=age, weight_kg=weight_kg,
            creatinine=creatinine, gender=gender, indication_group=indication_group,
            infusion_strategy=infusion_strategy, dialysis_modality=dialysis_modality,
            cvvhd_flow_rate=cvvhd_flow_rate, allergy_history=allergy_history or [],
            concomitant_medications=concomitant_medications or [])
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def search_knowledge_base(query: str) -> str:
    """Search knowledge base markdown files for rules and sources."""
    kb_dir = os.path.join(ROOT, "knowledge_base")
    results = []
    if not os.path.exists(kb_dir):
        return "Knowledge base not found."
    q = query.lower()
    for fname in os.listdir(kb_dir):
        if not fname.endswith(".md"):
            continue
        try:
            with open(os.path.join(kb_dir, fname), "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if q in content.lower() or any(t in content.lower() for t in q.split()):
            results.append(f"--- {fname} ---\n{content[:2000]}")
    return "\n\n".join(results) if results else f"No matches for: {query}"


@tool
def check_safety_rules(rule_id: str) -> str:
    """Look up safety rule by rule_id."""
    rule = get_safety_rule(rule_id)
    return str(rule) if rule else f"Rule '{rule_id}' not found."


@tool
def check_interaction(alert_code: str) -> str:
    """Look up drug interaction by alert code."""
    inter = get_interaction(alert_code)
    return str(inter) if inter else f"Interaction '{alert_code}' not found."


__all__ = ["calculate_creatinine_clearance", "get_vancomycin_regimen",
    "get_meropenem_regimen", "search_knowledge_base", "check_safety_rules",
    "check_interaction"]