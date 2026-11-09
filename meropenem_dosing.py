"""Deterministic meropenem dosing rules (MER-001 .. MER-011)."""
from typing import Any, Dict, Optional

from data.clinical_vocabulary import classify_dialysis, classify_meropenem_indication


def _norm_indication(value):
    return classify_meropenem_indication(value)


def _norm_infusion(value):
    if value is None:
        return None
    s = str(value).strip().lower().replace(" ", "_")
    if s in ("short", "short_infusion"):
        return "Short_Infusion"
    if s in ("extended", "extended_infusion"):
        return "Extended_Infusion"
    return None


def _norm_dialysis(value):
    """Return 'IHD' / 'CVHD' / 'PD' when dialysed, None when not.

    Raises ValueError when the wording says the patient is dialysed but the
    modality cannot be determined, so a continuous modality is never silently
    dosed as an intermittent one.
    """
    if value is None:
        return None
    status, modality = classify_dialysis(value)
    if status is None:
        raise ValueError(
            "Dialysis status could not be determined from '%s'; answer Yes or No "
            "and give the modality when the patient is dialysed." % value
        )
    if status == "No":
        return None
    if modality is None:
        raise ValueError(
            "Dialysis modality could not be determined from '%s'; specify IHD, "
            "CRRT/CVVHD or PD." % value
        )
    return "CVHD" if modality == "CRRT" else modality


def _mero_crcl_band(crcl):
    if crcl > 50:
        return ">50"
    if crcl >= 26:
        return "26-50"
    if crcl >= 10:
        return "10-25"
    return "<10"


_FREQ_HUMAN = {"q8h": "Every 8 hours", "q12h": "Every 12 hours",
               "q24h": "Every 24 hours", "qPM": "qPM"}

def get_meropenem_dose(
    crcl_ml_min=None,
    age=None,
    weight_kg=None,
    creatinine=None,
    gender=None,
    indication=None,
    indication_group=None,
    infusion_strategy=None,
    dialysis_modality=None,
    cvvhd_flow_rate=None,
    allergy_history=None,
    concomitant_medications=None,
    **kwargs,
):
    if crcl_ml_min is None and "crcl" in kwargs:
        crcl_ml_min = kwargs["crcl"]
    if indication is None and "indication_group" in kwargs:
        indication = kwargs["indication_group"]
    if infusion_strategy is None and "infusion" in kwargs:
        infusion_strategy = kwargs["infusion"]
    if dialysis_modality is None and "dialysis" in kwargs:
        dialysis_modality = kwargs["dialysis"]

    # Safety: confirmed hypersensitivity -> BLOCK
    if allergy_history:
        for a in allergy_history:
            substance = str((a or {}).get("substance", "")).lower()
            certainty = str((a or {}).get("certainty", "")).lower()
            reaction = str((a or {}).get("reaction", "")).lower()
            if "meropenem" in substance or "beta-lactam" in substance or "carbapenem" in substance:
                if certainty == "confirmed" or "anaphylaxis" in reaction:
                    return {
                        "decision": "BLOCK",
                        "alert_code": "CONFIRMED_HYPERSENSITIVITY",
                        "dose_calculation_allowed": False,
                        "message": "Do not administer meropenem in a patient with confirmed serious hypersensitivity to the product.",
                        "required_action": "Stop automated recommendation and request an alternative antimicrobial / clinician review.",
                    }

    # Safety: valproate interaction
    if concomitant_medications:
        for m in concomitant_medications:
            drug = str((m or {}).get("drug", "")).lower()
            if "valproate" in drug or "valproic" in drug:
                return {
                    "decision": "HIGH_PRIORITY_INTERACTION_ALERT",
                    "alert_code": "MEROPENEM_VALPROATE",
                    "dose_calculation_allowed": True,
                    "message": "Meropenem may markedly reduce valproate concentrations and cause breakthrough seizures.",
                    "required_action": "Prefer an alternative antibiotic when clinically appropriate; if concomitant use is unavoidable, urgent specialist review and seizure-control plan are required.",
                }
        for m in concomitant_medications:
            drug = str((m or {}).get("drug", "")).lower()
            if "probenecid" in drug:
                return {
                    "decision": "HIGH_PRIORITY_INTERACTION_ALERT",
                    "alert_code": "MEROPENEM_PROBENECID",
                    "dose_calculation_allowed": True,
                    "message": "Probenecid may increase meropenem exposure by reducing renal tubular secretion; concomitant use is generally not recommended.",
                    "required_action": "Generate interaction alert and request medication review.",
                }

    # Normalize dialysis modality early (needed for CrCl requirement logic)
    dm = _norm_dialysis(dialysis_modality)

    # Compute CrCl if needed (only required for non-dialysis paths)
    if crcl_ml_min is None:
        if dm is None and creatinine is not None and gender is not None and weight_kg is not None and age is not None:
            from tools.crcl_calculator import calculate_crcl
            crcl_ml_min = calculate_crcl(age, weight_kg, creatinine, gender)
        elif dm is None:
            raise ValueError("crcl_ml_min is required (or creatinine+gender+weight+age)")
        else:
            crcl_ml_min = 0  # not used for dialysis paths

    try:
        crcl_ml_min = float(crcl_ml_min)
    except (TypeError, ValueError):
        raise ValueError("crcl_ml_min must be numeric")

    ind = _norm_indication(indication if indication is not None else indication_group)
    if ind is None:
        raise ValueError("indication must be classified (Standard or Meningitis/Cystic Fibrosis) - MER-002")

    infusion = _norm_infusion(infusion_strategy)

    # Dialysis paths
    if dm == "IHD":
        initial = 500 if ind == "Standard" else 1000
        return {
            "decision": "DIALYSIS_SPECIFIC_REGIMEN_SELECTED",
            "dose": initial,
            "dose_unit": "mg",
            "route": "IV",
            "initial_instruction": "One dose now",
            "maintenance_frequency_source_text": "qPM",
            "do_not_reinterpret_qPM": True,
            "clinical_review_required": True,
            "message": "Use the IHD-specific source row. Preserve qPM exactly until its timing is clarified by the local protocol.",
            "source_rule": "MER-005",
        }

    if dm == "CVHD":
        if ind == "Standard":
            maint_dose = 1
            maint_freq_code = "q8h"
        else:
            maint_dose = 2
            maint_freq_code = "q12h"
        if cvvhd_flow_rate is not None:
            try:
                if float(cvvhd_flow_rate) > 2:
                    return {
                        "decision": "SPECIALIST_REVIEW_REQUIRED",
                        "alert_code": "CVVHD_FLOW_ABOVE_2_L_H",
                        "automatic_dose_finalization_allowed": False,
                        "message": "The supplied UCSF guidance advises discussion with ID/ASP pharmacy when CVVHD flow rate exceeds 2 L/hour.",
                        "required_action": "Refer to ID / antimicrobial stewardship / clinical pharmacy for individualized regimen confirmation.",
                        "terminology_caution": "The supplied table is labeled CVHD while its footnote refers to CVVHD; do not generalize this regimen to all CRRT modalities.",
                        "source_rule": "MER-007",
                        "clinical_review_required": True,
                    }
            except (TypeError, ValueError):
                raise ValueError("cvvhd_flow_rate must be numeric")
        return {
            "decision": "DIALYSIS_SPECIFIC_REGIMEN_SELECTED",
            "dose": maint_dose,
            "dose_unit": "g",
            "route": "IV",
            "frequency": _FREQ_HUMAN.get(maint_freq_code, maint_freq_code),
            "frequency_source_text": maint_freq_code,
            "clinical_review_required": True,
            "terminology_caution": "The supplied table is labeled CVHD while its footnote refers to CVVHD; do not generalize this regimen to all CRRT modalities.",
            "source_rule": "MER-006",
        }

    if dm == "PD":
        return {
            "decision": "SOURCE_DATA_UNAVAILABLE",
            "message": "No PD dose is provided in this extract.",
            "required_action": "Find an independent authoritative PD-specific source; retain source attribution and verify with clinical pharmacy.",
            "source_rule": "MER-008",
            "clinical_review_required": True,
        }

    # Non-dialysis path requires infusion strategy (MER-003)
    if infusion is None:
        raise ValueError("infusion_strategy must be explicitly selected (Short_Infusion or Extended_Infusion) - MER-003")

    band = _mero_crcl_band(crcl_ml_min)

    # Short infusion
    if infusion == "Short_Infusion":
        if band == ">50":
            if ind == "Standard":
                dose, unit, freq = 1, "g", "q8h"
            else:
                dose, unit, freq = 2, "g", "q8h"
        elif band == "26-50":
            if ind == "Standard":
                dose, unit, freq = 1, "g", "q12h"
            else:
                dose, unit, freq = 2, "g", "q12h"
        elif band == "10-25":
            if ind == "Standard":
                dose, unit, freq = 500, "mg", "q12h"
            else:
                dose, unit, freq = 1, "g", "q12h"
        else:
            if ind == "Standard":
                dose, unit, freq = 500, "mg", "q24h"
            else:
                dose, unit, freq = 1, "g", "q24h"
        return {
            "decision": "RENAL_ADJUSTED_REGIMEN_SELECTED",
            "dose": dose,
            "dose_unit": unit,
            "route": "IV",
            "frequency": _FREQ_HUMAN.get(freq, freq),
            "frequency_source_text": freq,
            "infusion_strategy": "Short_Infusion",
            "crcl_band": band,
            "clinical_review_required": True,
            "source_rule": "UCSF adult short-infusion renal dosing table: CrCl %s mL/min, %s indication" % (band, ind.lower()),
        }

    # Extended infusion
    if infusion == "Extended_Infusion":
        # MER-004: CrCl <26 -> use short infusion
        if band in ("10-25", "<10"):
            return {
                "decision": "USE_SHORT_INFUSION",
                "message": "For CrCl <26 mL/min, source directs use of short infusion.",
                "infusion_strategy": "Short_Infusion",
                "crcl_band": band,
                "source_rule": "MER-004",
                "clinical_review_required": True,
            }
        loading_dose = 1
        loading_unit = "g"
        if band == ">50":
            if ind == "Standard":
                maint_dose, maint_unit, maint_freq = 1, "g", "q8h"
            else:
                maint_dose, maint_unit, maint_freq = 2, "g", "q8h"
        else:
            if ind == "Standard":
                maint_dose, maint_unit, maint_freq = 1, "g", "q12h"
            else:
                maint_dose, maint_unit, maint_freq = 2, "g", "q12h"
        return {
            "decision": "EXTENDED_INFUSION_REGIMEN_SELECTED",
            "loading_dose": loading_dose,
            "loading_dose_unit": loading_unit,
            "loading_route": "IV",
            "loading_frequency": "Once",
            "loading_duration_min": 30,
            "maintenance_dose": maint_dose,
            "maintenance_dose_unit": maint_unit,
            "maintenance_route": "IV",
            "maintenance_frequency": _FREQ_HUMAN.get(maint_freq, maint_freq),
            "maintenance_frequency_source_text": maint_freq,
            "maintenance_duration_hours": 3,
            "infusion_strategy": "Extended_Infusion",
            "crcl_band": band,
            "clinical_review_required": True,
            "source_rule": "MER-003",
            "note": "Maintenance dose over 3 hours. Loading dose over 30 min; if loading dose given, start maintenance 4 hours after loading dose (MER-009).",
        }

    raise ValueError("Unable to determine meropenem regimen")

