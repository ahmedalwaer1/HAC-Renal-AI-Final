"""Hardcoded clinical data dictionaries for HAC-Renal AI (Sprint 2)."""
from __future__ import annotations

SOURCES = {
    "UCSF_VANCOMYCIN": {
        "title": "Vancomycin Initial Dosing Nomogram",
        "organization": "UCSF Infectious Diseases Management Program",
        "url": "https://idmp.ucsf.edu/content/vancomycin-initial-dosing-nomogram",
        "modified": "May 30, 2025",
        "scope": "Adult initial dosing guidance / nomogram",
    },
    "UCSF_MEROPENEM": {
        "title": "Meropenem dosing guideline",
        "organization": "UCSF Infectious Diseases Management Program",
        "url": "https://idmp.ucsf.edu/content/meropenem",
        "capture": "2026-11-02",
        "scope": "Adult antimicrobial dosing",
    },
    "DAILYMED_MEROPENEM": {
        "title": "Meropenem for Injection Prescribing Information",
        "organization": "US FDA / DailyMed",
        "url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ca5f501c-6520-4d09-aae2-4f5db74d468f",
        "supports": "Renal elimination, warnings, interactions and safety information",
    },
    "BETA_LACTAM_TDM_CONSENSUS": {
        "title": "International consensus recommendations for therapeutic drug monitoring of beta-lactam antibiotics",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30307434/",
        "year": "2019",
    },
}

INTERACTIONS = [
    {"code": "MEROPENEM_VALPROATE", "drug": "Valproate",
     "message": "Meropenem may markedly reduce valproate concentrations and cause breakthrough seizures.",
     "action": "Prefer an alternative antibiotic when clinically appropriate; if concomitant use is unavoidable, urgent specialist review and seizure-control plan are required.",
     "source": "DAILYMED_MEROPENEM"},
    {"code": "MEROPENEM_PROBENECID", "drug": "Probenecid",
     "message": "Probenecid may increase meropenem exposure by reducing renal tubular secretion; concomitant use is generally not recommended.",
     "action": "Generate interaction alert and request medication review.",
     "source": "DAILYMED_MEROPENEM"},
]

HYPERSENSITIVITY = {
    "code": "CONFIRMED_HYPERSENSITIVITY",
    "message": "Do not administer meropenem in a patient with confirmed serious hypersensitivity to the product.",
    "action": "Stop automated recommendation and request an alternative antimicrobial / clinician review.",
    "source": "DAILYMED_MEROPENEM",
}
SAFETY_RULES = [
    {"rule_id": "MER-001", "category": "Renal adjustment", "rule": "Select non-dialysis short-infusion regimen using the documented CrCl band.", "trigger": "CrCl must be available and expressed in mL/min.", "system_action": "Block automatic dose selection if CrCl is missing or outside defined bands.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-002", "category": "Indication", "rule": "Select the indication-specific row (standard vs meningitis/cystic fibrosis).", "trigger": "Indication must be classified.", "system_action": "Do not default meningitis/CF patients to standard dosing.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-003", "category": "Infusion strategy", "rule": "Keep short infusion and extended infusion regimens separate.", "trigger": "Infusion strategy must be explicitly selected/recommended.", "system_action": "Do not combine dose and infusion duration across strategies.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-004", "category": "Extended infusion threshold", "rule": "For CrCl <26 mL/min, source directs use of short infusion.", "trigger": "CrCl band <26 mL/min.", "system_action": "Do not create an extended-infusion dose for this band from this source.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-005", "category": "IHD", "rule": "Use IHD-specific table, not non-dialysis table, for IHD patients.", "trigger": "Dialysis modality = IHD.", "system_action": "Retain qPM wording until timing is clarified.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-006", "category": "CVHD/CVVHD", "rule": "Apply only to the continuous hemodialysis modality named in the source.", "trigger": "Modality terminology must be confirmed.", "system_action": "Do not generalize to CVVH or CVVHDF without separate evidence.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-007", "category": "CVVHD flow", "rule": "If flow rate >2 L/hr, refer to ID/ASP pharmacy.", "trigger": "CVVHD flow rate >2 L/hr.", "system_action": "Trigger review; do not extrapolate a new dose.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-008", "category": "PD", "rule": "No PD dose is provided in this extract.", "trigger": "Dialysis modality = PD.", "system_action": "Return 'source data unavailable'; seek separate PD reference.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-009", "category": "Loading dose timing", "rule": "When loading dose is used in extended infusion, maintenance starts 4 hours after loading dose.", "trigger": "Extended-infusion initiation.", "system_action": "Preserve the condition and check if patient already receiving short infusion.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-010", "category": "Meningitis extended infusion", "rule": "Evidence is limited; source advises discussion with ID/ASP providers.", "trigger": "Indication = meningitis and extended infusion considered.", "system_action": "Require clinical review.", "source": "UCSF_MEROPENEM"},
    {"rule_id": "MER-011", "category": "Clinical validation", "rule": "All doses require review against current institutional protocol and patient-specific factors.", "trigger": "Before clinical use.", "system_action": "Workbook is not a prescribing order.", "source": "UCSF_MEROPENEM"},
]

VANCOMYCIN_NOTES = [
    {"field": "Complicated infection definition", "value": "CNS infections; endocarditis; pneumonia; bacteremia; osteomyelitis; sepsis", "note": "Use as source-defined condition list"},
    {"field": "Weight selection", "value": "Total Body Weight if TBW <120% of IBW; Adjusted Body Weight if TBW >120% of IBW", "note": "Need height, sex (for IBW formula), actual weight"},
    {"field": "Loading dose recommendation", "value": "20-25 mg/kg IV x1 for serious infections", "note": "Separate loading-dose rule from maintenance nomogram"},
    {"field": "CrCl bands", "value": ">90; 50-90; 15-49; <15 mL/min", "note": "Source bands reproduced; use mutually exclusive boundaries"},
    {"field": "Safety", "value": "Do not auto-prescribe solely from this sheet", "note": "Clinical pharmacist/physician validation and local protocol required"},
]

def get_safety_rule(rule_id):
    for r in SAFETY_RULES:
        if r["rule_id"] == rule_id:
            return r
    return None

def get_source(source_key):
    return SOURCES.get(source_key)

def get_interaction(code):
    for i in INTERACTIONS:
        if i["code"] == code:
            return i
    return None


# ---------------------------------------------------------------------------
# Workflow requirements source (project requirements document, not clinical evidence)
# ---------------------------------------------------------------------------
SOURCES["HAC_RENAL_PROTOCOL"] = {
    "title": "HAC-Renal AI project requirements document",
    "organization": "Project documentation",
    "scope": "Workflow requirements only: completeness gate, abstention, "
             "monitoring and reassessment. Not a clinical evidence source.",
}

SOURCES["IDSA_VANCOMYCIN_2020"] = {
    "title": "Therapeutic monitoring of vancomycin for serious MRSA infections: "
             "a revised consensus guideline (Rybak et al.)",
    "organization": "ASHP / IDSA / PIDS / SIDP",
    "url": "https://pubmed.ncbi.nlm.nih.gov/32191793/",
    "year": "2020",
    "scope": "AUC-guided therapeutic monitoring targets for vancomycin",
}

SOURCES["MEROPENEM_TDM_REVIEW"] = {
    "title": "Beta-lactam therapeutic drug monitoring - monitoring targets and timing",
    "organization": "Project extract from the international beta-lactam TDM consensus",
    "url": "https://pubmed.ncbi.nlm.nih.gov/30307434/",
    "scope": "Sampling timing and pharmacodynamic targets for beta-lactams",
}

# ---------------------------------------------------------------------------
# Per-drug hypersensitivity (generic mechanism, replaces the meropenem-only check)
# ---------------------------------------------------------------------------
DRUG_HYPERSENSITIVITY = {
    "meropenem": {
        "code": "CONFIRMED_HYPERSENSITIVITY",
        "terms": ["meropenem", "beta-lactam", "carbapenem"],
        "message": "Do not administer meropenem in a patient with confirmed serious "
                   "hypersensitivity to the product.",
        "action": "Stop automated recommendation and request an alternative "
                  "antimicrobial / clinician review.",
        "source": "DAILYMED_MEROPENEM",
    },
    "vancomycin": {
        "code": "CONFIRMED_HYPERSENSITIVITY",
        "terms": ["vancomycin"],
        "message": "Do not administer vancomycin in a patient with confirmed serious "
                   "hypersensitivity to vancomycin.",
        "action": "Stop automated recommendation and request an alternative "
                  "antimicrobial / clinician review.",
        "source": None,
        "source_note": "Generic fail-safe block. This project contains no vancomycin "
                       "prescribing information; add the official product information "
                       "before clinical use.",
    },
}

# تغطية التداخلات المتوفرة لكل دواء (فجوة التغطية تُعلَن صراحةً ولا تُخفى)
DRUG_INTERACTION_COVERAGE = {
    "meropenem": ["MEROPENEM_VALPROATE", "MEROPENEM_PROBENECID"],
    "vancomycin": [],
}

# ---------------------------------------------------------------------------
# Stage 2: therapy appropriateness assessment (كل قاعدة بمصدر)
# ---------------------------------------------------------------------------
THERAPY_ASSESSMENT_RULES = [
    {
        "rule_id": "THER-001",
        "severity": "STOP",
        "category": "Contraindication",
        "rule": "Do not continue the selected agent when a confirmed serious "
                "hypersensitivity to it is documented.",
        "trigger": "Confirmed allergy, or an anaphylactic reaction, to the selected "
                   "agent or its class.",
        "source": "DAILYMED_MEROPENEM",
    },
    {
        "rule_id": "THER-002",
        "severity": "ESCALATE",
        "category": "Limited evidence",
        "rule": "Evidence is limited for extended-infusion meropenem in meningitis; "
                "the source advises discussion with ID/ASP providers.",
        "trigger": "Indication = meningitis/cystic fibrosis AND extended infusion selected.",
        "source": "UCSF_MEROPENEM",
    },
    {
        "rule_id": "THER-003",
        "severity": "ESCALATE",
        "category": "Missing regimen",
        "rule": "No peritoneal dialysis dose is provided by the project source; an "
                "independent PD-specific reference is required.",
        "trigger": "Dialysis modality = peritoneal dialysis.",
        "source": "UCSF_MEROPENEM",
    },
    {
        "rule_id": "THER-004",
        "severity": "PROVISIONAL",
        "category": "Microbiological documentation",
        "rule": "The regimen stays empirical until culture and susceptibility results "
                "are available; therapy must then be reassessed and narrowed.",
        "trigger": "No culture / susceptibility result supplied.",
        "source": "HAC_RENAL_PROTOCOL",
    },
    {
        "rule_id": "THER-005",
        "severity": "DEFER",
        "category": "Infection not documented",
        "rule": "The system cannot confirm that antimicrobial therapy is indicated; "
                "no project source supports dosing without a documented or suspected "
                "infection.",
        "trigger": "Infection explicitly reported as not documented or not suspected.",
        "source": "HAC_RENAL_PROTOCOL",
    },
    {
        "rule_id": "THER-006",
        "severity": "ESCALATE",
        "category": "Culture-therapy mismatch",
        "rule": "The isolate is reported resistant to the selected agent; the "
                "project sources cannot confirm coverage, so a specialist review of "
                "the regimen is required.",
        "trigger": "Culture / susceptibility text reports the selected agent as "
                   "resistant or non-susceptible.",
        "source": "HAC_RENAL_PROTOCOL",
    },
]

# ---------------------------------------------------------------------------
# Stage 4: monitoring plan
# ---------------------------------------------------------------------------
MONITORING_PLAN = {
    "common": [
        {"parameter": "Clinical response",
         "detail": "Reassess fever, haemodynamic status and the source of infection at "
                   "each review.",
         "source": "HAC_RENAL_PROTOCOL"},
        {"parameter": "Renal function trend",
         "detail": "Track serum creatinine and CrCl; a changing renal function "
                   "invalidates the current dose band.",
         "source": "HAC_RENAL_PROTOCOL"},
        {"parameter": "Adverse effects",
         "detail": "Actively look for drug-specific toxicity and infusion-related "
                   "reactions.",
         "source": "HAC_RENAL_PROTOCOL"},
        {"parameter": "Microbiology",
         "detail": "Review culture and susceptibility results and narrow therapy "
                   "where possible.",
         "source": "HAC_RENAL_PROTOCOL"},
    ],
    "meropenem": [
        {"parameter": "Beta-lactam TDM",
         "detail": "Consider therapeutic drug monitoring; trough levels are not "
                   "reliable for beta-lactams, use 2-4 hour post-infusion levels.",
         "source": "BETA_LACTAM_TDM_CONSENSUS"},
        {"parameter": "Pharmacodynamic target",
         "detail": "Target free drug concentration above the MIC for 40-50% of the "
                   "dosing interval (100% for meningitis).",
         "source": "BETA_LACTAM_TDM_CONSENSUS"},
        {"parameter": "TDM indication",
         "detail": "TDM is recommended for augmented renal clearance, obesity, renal "
                   "impairment or ECMO.",
         "source": "BETA_LACTAM_TDM_CONSENSUS"},
    ],
    "vancomycin": [
        {"parameter": "Serum vancomycin levels",
         "detail": "Redosing is level-guided; the loading dose is 20-25 mg/kg IV once "
                   "for serious infections.",
         "source": "UCSF_VANCOMYCIN"},
        {"parameter": "Prescriber validation",
         "detail": "The nomogram sheet must not be used for auto-prescribing; "
                   "pharmacist/physician validation against the local protocol is "
                   "required.",
         "source": "UCSF_VANCOMYCIN"},
    ],
}

MONITORING_DIALYSIS = {
    "IHD": [
        {"parameter": "Dose timing relative to sessions",
         "detail": "Give the regimen in relation to the haemodialysis schedule; "
                   "preserve the source wording until institutional timing is "
                   "confirmed.",
         "source": "UCSF_MEROPENEM"},
    ],
    "CRRT": [
        {"parameter": "Continuous modality parameters",
         "detail": "Confirm the exact continuous modality and effluent/dialysate flow "
                   "rate; do not generalise between CRRT variants.",
         "source": "UCSF_MEROPENEM"},
    ],
    "PD": [
        {"parameter": "Peritoneal dialysis",
         "detail": "No validated PD regimen exists in this project; obtain an "
                   "independent PD reference and clinical pharmacy review.",
         "source": "UCSF_MEROPENEM"},
    ],
}

REASSESSMENT_TRIGGERS = [
    {"trigger": "Renal function changes or dialysis modality changes",
     "action": "Recompute the CrCl band and re-run dose selection.",
     "source": "HAC_RENAL_PROTOCOL"},
    {"trigger": "Culture / susceptibility results become available",
     "action": "Reassess and narrow the regimen; do not continue empirically.",
     "source": "HAC_RENAL_PROTOCOL"},
    {"trigger": "Evidence of treatment failure",
     "action": "Escalate for specialist review instead of changing the dose "
               "automatically.",
     "source": "HAC_RENAL_PROTOCOL"},
    {"trigger": "Suspected drug toxicity",
     "action": "Escalate for review and consider level measurement where indicated.",
     "source": "HAC_RENAL_PROTOCOL"},
    {"trigger": "New or changed concomitant medication",
     "action": "Re-run the interaction screen before continuing.",
     "source": "HAC_RENAL_PROTOCOL"},
]


def get_therapy_rule(rule_id):
    for r in THERAPY_ASSESSMENT_RULES:
        if r["rule_id"] == rule_id:
            return r
    return None


def get_monitoring_plan(drug_key):
    drug_key = (drug_key or "").lower()
    return list(MONITORING_PLAN.get(drug_key, []))


