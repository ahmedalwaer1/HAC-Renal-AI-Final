"""Stage 4 data: clinical follow-up events, re-assessment rules and TDM targets.

This module holds data only - the executable behaviour lives in
``followup_engine.py``. Every entry carries the source it came from so a
pharmacist can trace a follow-up recommendation the same way a dose is traced.

Sources
-------
* ``IDSA_VANCOMYCIN_2020`` - AUC24/MIC 400-600 mg*h/L for serious MRSA
  infections (AUC-guided monitoring preferred over trough-only monitoring).
* ``BETA_LACTAM_TDM_CONSENSUS`` - beta-lactam sampling timing and fT>MIC targets.
* ``HAC_RENAL_PROTOCOL`` - workflow triggers from the project requirements only.
"""

# ---------------------------------------------------------------------------
# What can be recorded after the initial regimen
# ---------------------------------------------------------------------------
FOLLOWUP_EVENT_TYPES = [
    {"code": "renal_function",
     "label": "Renal function / serum creatinine"},
    {"code": "drug_level",
     "label": "Drug level (therapeutic drug monitoring)"},
    {"code": "dialysis_session",
     "label": "Dialysis session / modality change"},
    {"code": "microbiology",
     "label": "Culture and susceptibility result"},
    {"code": "clinical_response",
     "label": "Clinical response"},
    {"code": "adverse_effect",
     "label": "Suspected adverse effect or toxicity"},
    {"code": "medication_change",
     "label": "New or changed concomitant medication"},
    {"code": "duration_review",
     "label": "Antibiotic time-out / duration review"},
]

CLINICAL_RESPONSE_OPTIONS = ["improving", "stable", "no_improvement", "worsening"]

ADVERSE_EFFECT_OPTIONS = [
    "acute kidney injury / rising creatinine",
    "infusion reaction",
    "suspected hypersensitivity",
    "haematological toxicity",
    "other",
]

# ---------------------------------------------------------------------------
# Follow-up rules (executed by followup_engine.py through the "engine" key)
# ---------------------------------------------------------------------------
FOLLOWUP_RULES = [
    {
        "rule_id": "FU-001",
        "event": "renal_function",
        "severity": "ADJUST",
        "engine": "recompute_regimen",
        "trigger": "A new creatinine or CrCl is recorded and the patient moves to a "
                   "different renal dosing band.",
        "action": "Recompute CrCl, re-run dose selection and replace the regimen if "
                  "the band changed.",
        "source": "HAC_RENAL_PROTOCOL",
    },
    {
        "rule_id": "FU-002",
        "event": "drug_level",
        "severity": "ADJUST",
        "engine": "interpret_level",
        "trigger": "A vancomycin level is recorded and can be compared with the "
                   "AUC24 target of 400-600 mg*h/L.",
        "action": "Classify the exposure as below, within or above target and state "
                  "the direction of the required dose change for pharmacist action.",
        "source": "IDSA_VANCOMYCIN_2020",
    },
    {
        "rule_id": "FU-003",
        "event": "dialysis_session",
        "severity": "ADJUST",
        "engine": "recompute_regimen",
        "trigger": "An intermittent haemodialysis session is completed, or the "
                   "dialysis modality changes.",
        "action": "Apply the modality-specific regimen (post-dialysis dosing) and "
                  "replace the previous regimen.",
        "source": "UCSF_MEROPENEM",
    },
    {
        "rule_id": "FU-004",
        "event": "microbiology",
        "severity": "REVIEW",
        "engine": "reassess_appropriateness",
        "trigger": "Culture and susceptibility results become available.",
        "action": "Clear the empirical-therapy flag, check that the isolate is "
                  "covered and recommend narrowing where possible.",
        "source": "HAC_RENAL_PROTOCOL",
    },
    {
        "rule_id": "FU-005",
        "event": "clinical_response",
        "severity": "ESCALATE",
        "engine": "reassess_response",
        "trigger": "No improvement, or worsening, at 48-72 hours of therapy.",
        "action": "Escalate for specialist review instead of changing the dose "
                  "automatically; re-check source control.",
        "source": "HAC_RENAL_PROTOCOL",
    },
    {
        "rule_id": "FU-006",
        "event": "adverse_effect",
        "severity": "STOP",
        "engine": "reassess_toxicity",
        "trigger": "A suspected drug-related adverse effect or toxicity is recorded.",
        "action": "Hold the automated recommendation, surface the toxicity for "
                  "review and re-check renal function if nephrotoxicity is suspected.",
        "source": "HAC_RENAL_PROTOCOL",
    },
    {
        "rule_id": "FU-007",
        "event": "medication_change",
        "severity": "REVIEW",
        "engine": "recompute_regimen",
        "trigger": "A new or changed concomitant medication is recorded.",
        "action": "Re-run the interaction screen before continuing the regimen.",
        "source": "HAC_RENAL_PROTOCOL",
    },
    {
        "rule_id": "FU-008",
        "event": "duration_review",
        "severity": "REVIEW",
        "engine": "reassess_duration",
        "trigger": "Antibiotic time-out reached (48-72 hours).",
        "action": "Confirm the ongoing indication, the dose and the planned stop "
                  "date; stop therapy when the infection is no longer documented.",
        "source": "HAC_RENAL_PROTOCOL",
    },
]

# ---------------------------------------------------------------------------
# Therapeutic drug monitoring targets
# ---------------------------------------------------------------------------
TDM_TARGETS = {
    "vancomycin": {
        "primary": {
            "metric": "AUC24/MIC",
            "unit": "mg*h/L",
            "low": 400,
            "high": 600,
            "preferred": True,
            "note": "AUC-guided dosing is the recommended monitoring strategy; "
                    "trough-only monitoring is no longer preferred for serious MRSA.",
            "source": "IDSA_VANCOMYCIN_2020",
        },
        "trough_context": {
            "metric": "trough",
            "unit": "mg/L",
            "serious_range": [15, 20],
            "non_serious_range": [10, 15],
            "note": "Trough ranges are kept only as a fallback context value when AUC "
                    "monitoring is not available; the sample must be drawn before the "
                    "next dose.",
            "source": "IDSA_VANCOMYCIN_2020",
        },
    },
    "meropenem": {
        "primary": {
            "metric": "fT>MIC",
            "unit": "% of the dosing interval",
            "low": 40,
            "high": 50,
            "preferred": True,
            "note": "Target free drug concentration above the MIC for 40-50% of the "
                    "dosing interval (100% for meningitis). Sample 2-4 hours after the "
                    "infusion; trough levels are not reliable for beta-lactams.",
            "source": "BETA_LACTAM_TDM_CONSENSUS",
        },
    },
}

# ---------------------------------------------------------------------------
# Scheduled follow-up items per drug
# ---------------------------------------------------------------------------
_NEXT_DUE_COMMON = [
    {"item": "Serum creatinine and CrCl",
     "due": "Every 48 hours, or sooner if renal function is unstable",
     "source": "HAC_RENAL_PROTOCOL"},
    {"item": "Clinical response review (fever, haemodynamics, source control)",
     "due": "Every 24 hours",
     "source": "HAC_RENAL_PROTOCOL"},
    {"item": "Antibiotic time-out (indication, dose, duration, stop date)",
     "due": "At 48-72 hours",
     "source": "HAC_RENAL_PROTOCOL"},
    {"item": "Culture and susceptibility review",
     "due": "As soon as results are available",
     "source": "HAC_RENAL_PROTOCOL"},
]

_NEXT_DUE_DRUG = {
    "vancomycin": [
        {"item": "Vancomycin exposure measurement (AUC24 preferred)",
         "due": "Before the 4th dose",
         "source": "IDSA_VANCOMYCIN_2020"},
        {"item": "Nephrotoxicity surveillance (creatinine, concurrent nephrotoxins)",
         "due": "Daily while on vancomycin",
         "source": "IDSA_VANCOMYCIN_2020"},
    ],
    "meropenem": [
        {"item": "Beta-lactam TDM (2-4 hour post-infusion level)",
         "due": "If augmented renal clearance, obesity, renal impairment or ECMO",
         "source": "BETA_LACTAM_TDM_CONSENSUS"},
    ],
}

_NEXT_DUE_DIALYSIS = [
    {"item": "Dose timing relative to dialysis sessions",
     "due": "At every session",
     "source": "UCSF_MEROPENEM"},
]


def get_followup_rule(rule_id):
    for rule in FOLLOWUP_RULES:
        if rule["rule_id"] == rule_id:
            return rule
    return None


def get_rule_for_event(event_code):
    for rule in FOLLOWUP_RULES:
        if rule["event"] == event_code:
            return rule
    return None


def get_tdm_target(drug_key):
    return TDM_TARGETS.get((drug_key or "").lower())


def next_due_items(drug_key, on_dialysis=False):
    """Build the follow-up schedule for the case's drug and renal state."""
    items = list(_NEXT_DUE_COMMON)
    items += list(_NEXT_DUE_DRUG.get((drug_key or "").lower(), []))
    if on_dialysis:
        items += list(_NEXT_DUE_DIALYSIS)
    return items
