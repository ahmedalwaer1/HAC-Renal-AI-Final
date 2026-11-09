"""Drug registry: المصدر الوحيد للحقيقة بشأن الأدوية المدعومة.

أي دواء غير مسجّل هنا يُرفض صراحةً (fail-closed).
لا يوجد أي مسار افتراضي إلى Meropenem أو غيره.
"""
from __future__ import annotations

from tools.meropenem_dosing import get_meropenem_dose
from tools.vancomycin_dosing import get_vancomycin_dose


class UnsupportedDrugError(ValueError):
    """يُرفع عند طلب دواء لا توجد له بيانات في هذا المشروع."""


DRUG_REGISTRY = {
    "meropenem": {
        "canonical_name": "Meropenem",
        "aliases": ["meropenem", "meronem", "merrem"],
        "drug_class": "Carbapenem (beta-lactam)",
        "dosing_function": get_meropenem_dose,
        "kb_files": ["meropenem_rules.md", "meropenem_tdm.md"],
        "source_keys": [
            "UCSF_MEROPENEM",
            "DAILYMED_MEROPENEM",
            "BETA_LACTAM_TDM_CONSENSUS",
        ],
        "indication_field": "indication_group",
        "indication_options": ["Standard", "Meningitis_CF"],
        "extra_field": "infusion_strategy",
        "extra_options": ["Short_Infusion", "Extended_Infusion"],
        "safety_notes": (
            "Indication must be classified and the infusion strategy must be "
            "explicitly selected (MER-002, MER-003)."
        ),
    },
    "vancomycin": {
        "canonical_name": "Vancomycin",
        "aliases": ["vancomycin", "vanco", "vancocin"],
        "drug_class": "Glycopeptide",
        "dosing_function": get_vancomycin_dose,
        "kb_files": ["vancomycin_rules.md"],
        "source_keys": ["UCSF_VANCOMYCIN"],
        "indication_field": "infection_type",
        "indication_options": ["complicated", "uncomplicated"],
        "extra_field": None,
        "extra_options": [],
        "safety_notes": (
            "Infection type (complicated vs uncomplicated) changes the nomogram "
            "cell; a loading dose of 20-25 mg/kg is recommended for serious "
            "infections. The source sheet must not be used for auto-prescribing."
        ),
    },
}

# ---------------------------------------------------------------------------
# Resolving
# ---------------------------------------------------------------------------
def resolve_drug(name):
    """أعِد مفتاح الدواء المسجّل، أو None إذا كان الدواء غير مدعوم."""
    if not name:
        return None
    q = str(name).strip().lower()
    for key, entry in DRUG_REGISTRY.items():
        if q == key or q in entry["aliases"]:
            return key
    return None


def get_drug_module(name):
    """أعِد تعريف الدواء المسجّل أو ارفع UnsupportedDrugError."""
    key = resolve_drug(name)
    if key is None:
        supported = sorted(e["canonical_name"] for e in DRUG_REGISTRY.values())
        raise UnsupportedDrugError(
            "Unsupported drug '%s'. This project contains dosing data only for: %s."
            % (name, ", ".join(supported))
        )
    return DRUG_REGISTRY[key]


def canonical_name(name):
    module = get_drug_module(name)
    return module["canonical_name"]


def supported_drugs():
    return [e["canonical_name"] for e in DRUG_REGISTRY.values()]
