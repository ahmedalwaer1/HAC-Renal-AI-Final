"""Deterministic vancomycin dosing rules (VAN-001 .. VAN-021).

Source: HAC_Renal_AI_Vancomycin_Data.xlsx (UCSF Vancomycin Initial Dosing Nomogram).
"""
from typing import Optional, Dict, Any

from data.clinical_vocabulary import classify_dialysis, classify_infection_type


def _weight_band(weight_kg: float) -> str:
    # Source bands: "<60 kg", "60-80 kg", "81-100 kg", ">100 kg"
    if weight_kg < 60:
        return "<60 kg"
    if weight_kg <= 80:
        return "60-80 kg"
    if weight_kg <= 100:
        return "81-100 kg"
    return ">100 kg"


def _crcl_band(crcl: float) -> str:
    # Source bands: ">90", "50-90", "15-49", "<15" mL/min
    if crcl > 90:
        return ">90"
    if crcl >= 50:
        return "50-90"
    if crcl >= 15:
        return "15-49"
    return "<15"


def get_vancomycin_dose(
    age=None,
    weight_kg=None,
    crcl_ml_min=None,
    creatinine=None,
    gender=None,
    infection_type="complicated",
    dialysis_modality=None,
    **kwargs,
) -> Dict[str, Any]:
    # Merge common aliases from kwargs
    if weight_kg is None and "weight" in kwargs:
        weight_kg = kwargs["weight"]
    if crcl_ml_min is None and "crcl" in kwargs:
        crcl_ml_min = kwargs["crcl"]
    if dialysis_modality is None and "dialysis" in kwargs:
        dialysis_modality = kwargs["dialysis"]

    if age is None or weight_kg is None:
        raise ValueError("age and weight_kg are required")

    try:
        weight_kg = float(weight_kg)
        age = float(age)
        if crcl_ml_min is not None:
            crcl_ml_min = float(crcl_ml_min)
    except (TypeError, ValueError):
        raise ValueError("age, weight_kg and crcl_ml_min must be numeric")

    raw_infection_type = infection_type if infection_type is not None else "complicated"
    infection_type = classify_infection_type(raw_infection_type)
    if infection_type is None:
        raise ValueError(
            "infection_type '%s' could not be classified; specify whether the "
            "infection is complicated or uncomplicated. The source defines a "
            "complicated infection as: CNS infections, endocarditis, pneumonia, "
            "bacteremia, osteomyelitis, sepsis." % raw_infection_type
        )

    status, dm = classify_dialysis(dialysis_modality)
    if status == "Yes" and dm is None:
        raise ValueError(
            "Dialysis modality could not be determined from '%s'; specify IHD, "
            "CRRT or PD." % dialysis_modality
        )
    if status != "Yes":
        dm = None

    # Dialysis branches (VAN-019, VAN-020, VAN-021): chosen by modality alone,
    # so CrCl is not required for these patients.
    if dm == "CRRT":
        return {"decision": "DIALYSIS_SPECIFIC_REGIMEN_SELECTED", "rule_id": "VAN-019", "drug": "Vancomycin", "route": "IV", "dose_mg": None, "dose_mg_per_kg": "20-25", "frequency": "Once, then 10-15 mg/kg q24h", "dose_type": "Loading then maintenance", "dialysis_modality": "CRRT", "timing": "q24h maintenance", "note": "CRRT row in UCSF nomogram"}
    if dm == "IHD":
        return {"decision": "DIALYSIS_SPECIFIC_REGIMEN_SELECTED", "rule_id": "VAN-020", "drug": "Vancomycin", "route": "IV", "dose_mg": None, "dose_mg_per_kg": "20-25", "frequency": "Once, then 500 mg post-HD only", "dose_type": "Loading then post-HD maintenance", "dialysis_modality": "Intermittent Hemodialysis", "timing": "500 mg after HD only", "note": "Assumes modality-specific dialysis conditions; verify current local protocol"}
    if dm == "PD":
        return {"decision": "DIALYSIS_SPECIFIC_REGIMEN_SELECTED", "rule_id": "VAN-021", "drug": "Vancomycin", "route": "IV", "dose_mg": None, "dose_mg_per_kg": "10-15", "frequency": "Once, then level-guided", "dose_type": "Initial then redose", "dialysis_modality": "Peritoneal Dialysis", "timing": "Redose according to serum levels", "note": "PD row in UCSF nomogram"}

    # Non-dialysis dosing is CrCl-based: derive it when possible, otherwise abstain.
    if crcl_ml_min is None:
        if creatinine is not None and gender is not None:
            from tools.crcl_calculator import calculate_crcl
            crcl_ml_min = calculate_crcl(age, weight_kg, creatinine, gender)
        else:
            raise ValueError("crcl_ml_min is required (or creatinine+gender)")
    crcl_ml_min = float(crcl_ml_min)

    band = _crcl_band(crcl_ml_min)
    wb = _weight_band(weight_kg)

    if band == "<15":
        return {"decision": "RENAL_ADJUSTED_REGIMEN_SELECTED", "rule_id": "VAN-018", "drug": "Vancomycin", "route": "IV", "dose_mg": None, "dose_mg_per_kg": "10-15", "frequency": "Once, then level-guided", "dose_type": "Initial then redose", "crcl_band": band, "weight_band": "Not specified in this row", "note": "Not on dialysis"}

    if band == "15-49":
        mapping = {"<60 kg": ("VAN-014", 750), "60-80 kg": ("VAN-015", 1000), "81-100 kg": ("VAN-016", 1250), ">100 kg": ("VAN-017", 1500)}
        rid, dose = mapping[wb]
        return {"decision": "RENAL_ADJUSTED_REGIMEN_SELECTED", "rule_id": rid, "drug": "Vancomycin", "route": "IV", "dose_mg": dose, "dose_mg_per_kg": None, "frequency": "q24h", "dose_type": "Maintenance", "crcl_band": band, "weight_band": wb, "note": "UCSF initial dosing nomogram"}

    # 50-90 mL/min -> VAN-009..013
    if band == "50-90":
        if wb == ">100 kg" and age < 65 and infection_type == "complicated":
            return {"decision": "RENAL_ADJUSTED_REGIMEN_SELECTED", "rule_id": "VAN-013", "drug": "Vancomycin", "route": "IV", "dose_mg": 1000, "dose_mg_per_kg": None, "frequency": "q8h", "dose_type": "Special nomogram cell / override", "crcl_band": band, "weight_band": wb, "note": "Special condition displayed in >100 kg cell; verify interpretation against live source before production use"}
        mapping = {"<60 kg": ("VAN-009", 750), "60-80 kg": ("VAN-010", 1000), "81-100 kg": ("VAN-011", 1250), ">100 kg": ("VAN-012", 1500)}
        rid, dose = mapping[wb]
        return {"decision": "RENAL_ADJUSTED_REGIMEN_SELECTED", "rule_id": rid, "drug": "Vancomycin", "route": "IV", "dose_mg": dose, "dose_mg_per_kg": None, "frequency": "q12h", "dose_type": "Maintenance", "crcl_band": band, "weight_band": wb, "note": "UCSF initial dosing nomogram"}

    # >90 mL/min -> VAN-001..008
    if band == ">90":
        complicated_young = (age < 65) and (infection_type == "complicated")
        if complicated_young:
            mapping = {"<60 kg": ("VAN-001", 750), "60-80 kg": ("VAN-002", 1000), "81-100 kg": ("VAN-003", 1250), ">100 kg": ("VAN-004", 1500)}
            rid, dose = mapping[wb]
            return {"decision": "RENAL_ADJUSTED_REGIMEN_SELECTED", "rule_id": rid, "drug": "Vancomycin", "route": "IV", "dose_mg": dose, "dose_mg_per_kg": None, "frequency": "q8h", "dose_type": "Maintenance", "crcl_band": band, "weight_band": wb, "note": "UCSF initial dosing nomogram"}
        mapping = {"<60 kg": ("VAN-005", 1000), "60-80 kg": ("VAN-006", 1250), "81-100 kg": ("VAN-007", 1500), ">100 kg": ("VAN-008", 1750)}
        rid, dose = mapping[wb]
        return {"decision": "RENAL_ADJUSTED_REGIMEN_SELECTED", "rule_id": rid, "drug": "Vancomycin", "route": "IV", "dose_mg": dose, "dose_mg_per_kg": None, "frequency": "q12h", "dose_type": "Maintenance", "crcl_band": band, "weight_band": wb, "note": "UCSF initial dosing nomogram"}

    raise ValueError("Unable to determine vancomycin regimen")

