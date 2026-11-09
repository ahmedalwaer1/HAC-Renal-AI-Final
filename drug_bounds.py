"""Declared safety bounds per drug.

Everything the engine will dose must sit inside an explicit, reviewable range.
Inside the range the engine resolves every scenario (by source cell, or by the
drug's own parametric rule). Outside it, the engine refuses and says why - it
never extrapolates a regimen for a patient the source was never validated on.

The bounds are deliberately wide enough for real adult practice and narrow
enough to stay defensible.
"""
from __future__ import annotations

from typing import Optional

# weight_kg is only a hard bound for drugs whose regimen is weight-based
# (the vancomycin nomogram). For the others it merely feeds Cockcroft-Gault.
DRUG_BOUNDS = {
    "vancomycin": {
        "weight_kg": (30.0, 250.0),
        "weight_critical": True,
        "age_years": (18.0, 120.0),
        "crcl_ml_min": (0.0, 200.0),
        "modalities": ("IHD", "CRRT", "PD"),
        "source": "HAC_RENAL_PROTOCOL",
    },
    "meropenem": {
        "weight_kg": (30.0, 250.0),
        "weight_critical": False,
        "age_years": (18.0, 120.0),
        "crcl_ml_min": (0.0, 200.0),
        "modalities": ("IHD", "CRRT", "PD"),
        "source": "HAC_RENAL_PROTOCOL",
    },
}

# Human-readable labels for the abstention message.
_FIELD_LABELS = {
    "weight_kg": "weight (kg)",
    "age_years": "age (years)",
    "crcl_ml_min": "CrCl (mL/min)",
    "dialysis_modality": "dialysis modality",
}


def _violation(field, value, low, high, drug_key):
    bounds = DRUG_BOUNDS[drug_key]
    return {
        "decision": "OUT_OF_DECLARED_BOUNDS",
        "alert_code": "%s_OUT_OF_BOUNDS" % field.upper(),
        "dose_calculation_allowed": False,
        "out_of_bounds_field": field,
        "out_of_bounds_value": value,
        "declared_range": [low, high],
        "message": (
            "The supplied %s (%s) is outside the declared adult range %s-%s for "
            "this drug. The engine does not extrapolate beyond a validated range."
            % (_FIELD_LABELS[field], value, low, high)
        ),
        "required_action": (
            "Confirm the value and the intended population with clinical "
            "pharmacy; if the patient genuinely falls outside the adult range, "
            "use a source validated for that population."
        ),
        "source": bounds.get("source"),
        "clinical_review_required": True,
    }


def declared_bounds(drug_key) -> Optional[dict]:
    """The bounds currently in force for a drug (for display and audit)."""
    bounds = DRUG_BOUNDS.get(drug_key)
    if not bounds:
        return None
    return {
        "weight_kg": bounds["weight_kg"],
        "age_years": bounds["age_years"],
        "crcl_ml_min": bounds["crcl_ml_min"],
        "modalities": list(bounds["modalities"]),
        "weight_critical": bounds["weight_critical"],
    }


def check_bounds(drug_key, n) -> Optional[dict]:
    """Return None when the patient is inside the declared bounds.

    `n` is the normalised patient dict produced by rules_engine._normalize.
    Missing values are left to the completeness gate, not reported here.
    """
    bounds = DRUG_BOUNDS.get(drug_key)
    if not bounds:
        return None

    if n.get("age") is not None:
        low, high = bounds["age_years"]
        if not (low <= float(n["age"]) <= high):
            return _violation("age_years", n["age"], low, high, drug_key)

    if n.get("weight_kg") is not None and bounds["weight_critical"]:
        low, high = bounds["weight_kg"]
        if not (low <= float(n["weight_kg"]) <= high):
            return _violation("weight_kg", n["weight_kg"], low, high, drug_key)

    if n.get("crcl_ml_min") is not None:
        low, high = bounds["crcl_ml_min"]
        if not (low <= float(n["crcl_ml_min"]) <= high):
            # A very high CrCl is augmented renal clearance: the source has no
            # cell for it, so it is reported rather than silently banded.
            return _violation("crcl_ml_min", n["crcl_ml_min"], low, high, drug_key)

    modality = n.get("dialysis_modality")
    if n.get("on_dialysis") and modality:
        if str(modality).upper() not in bounds["modalities"]:
            return {
                "decision": "OUT_OF_DECLARED_BOUNDS",
                "alert_code": "DIALYSIS_MODALITY_OUT_OF_BOUNDS",
                "dose_calculation_allowed": False,
                "out_of_bounds_field": "dialysis_modality",
                "out_of_bounds_value": modality,
                "declared_range": list(bounds["modalities"]),
                "message": (
                    "Dialysis modality '%s' is outside the modalities covered by "
                    "the registered source (%s)."
                    % (modality, ", ".join(bounds["modalities"]))
                ),
                "required_action": (
                    "Confirm the exact modality; continuous and intermittent "
                    "modalities need different regimens."
                ),
                "source": bounds.get("source"),
                "clinical_review_required": True,
            }
    return None


__all__ = ["DRUG_BOUNDS", "check_bounds", "declared_bounds"]
