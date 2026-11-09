"""Scenario-generalization tests.

The engine must resolve scenarios it was never explicitly written for - a new
wording of the infection, a new numeric value, a new dialysis phrase - as long
as the patient stays inside the drug's declared bounds. Outside those bounds it
must refuse instead of extrapolating, and an unrecognisable scenario must
abstain instead of being guessed.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from data.clinical_vocabulary import (
    classify_dialysis,
    classify_infection_type,
    classify_meropenem_indication,
)
from rules_engine import apply_rules


# ---------------------------------------------------------------------------
# Clinical vocabulary (free wording -> source category)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("wording,expected", [
    ("MRSA bacteraemia", "complicated"),
    ("ventilator-associated pneumonia", "complicated"),
    ("meningitis", "complicated"),
    ("sepsis of unknown source", "complicated"),
    ("osteomyelitis of the tibia", "complicated"),
    ("uncomplicated urinary tract infection", "uncomplicated"),
    ("simple cystitis", "uncomplicated"),
])
def test_infection_type_classification(wording, expected):
    assert classify_infection_type(wording) == expected


def test_infection_type_unknown_returns_none():
    assert classify_infection_type("the patient feels a bit off") is None


@pytest.mark.parametrize("wording,status,modality", [
    ("continuous venovenous haemodialysis", "Yes", "CRRT"),
    ("CVVHDF", "Yes", "CRRT"),
    ("on intermittent haemodialysis", "Yes", "IHD"),
    ("peritoneal dialysis", "Yes", "PD"),
    ("no dialysis", "No", None),
    ("not on dialysis", "No", None),
    ("dialysis", "Yes", None),
])
def test_dialysis_classification(wording, status, modality):
    assert classify_dialysis(wording) == (status, modality)


@pytest.mark.parametrize("wording,expected", [
    ("ventilator-associated pneumonia", "Standard"),
    ("intra-abdominal sepsis", "Standard"),
    ("empiric therapy", "Standard"),
    ("bacterial meningitis", "Meningitis_CF"),
    ("cystic fibrosis exacerbation", "Meningitis_CF"),
])
def test_meropenem_indication_classification(wording, expected):
    assert classify_meropenem_indication(wording) == expected


# ---------------------------------------------------------------------------
# End-to-end: novel scenarios the code was not written for
# ---------------------------------------------------------------------------
def _vanco(**over):
    patient = {
        "requested_drug": "Vancomycin",
        "age_years": 60,
        "weight_kg": 70,
        "creatinine": 1.0,
        "gender": "Male",
        "infection_type": "pneumonia",
        "dialysis": {"status": "No"},
    }
    patient.update(over)
    return patient


def test_novel_infection_wording_resolves_and_records_provenance():
    result = apply_rules(_vanco(infection_type="MRSA bacteraemia"))
    assert result["decision"] == "RENAL_ADJUSTED_REGIMEN_SELECTED"
    assert result["infection_type"] == "complicated"
    assert result["classified_from"] == "MRSA bacteraemia"


def test_novel_dialysis_phrase_resolves_to_modality_cell():
    result = apply_rules(_vanco(dialysis={
        "status": "Yes", "modality": "continuous venovenous haemodialysis"}))
    assert result["decision"] == "DIALYSIS_SPECIFIC_REGIMEN_SELECTED"
    assert result["rule_id"] == "VAN-019"


def test_novel_scenario_combination_resolves():
    # New wording + a weight above the top nomogram row + an age relation the
    # source encodes as a special cell: the engine resolves all three at once.
    result = apply_rules(_vanco(age_years=70, weight_kg=110, crcl_ml_min=70,
                                infection_type="MRSA bacteraemia"))
    assert result["decision"] == "RENAL_ADJUSTED_REGIMEN_SELECTED"
    assert result["rule_id"] == "VAN-012"
    assert result["dose_mg"] == 1500


def test_meropenem_novel_indication_resolves():
    result = apply_rules({
        "requested_drug": "Meropenem",
        "age_years": 60,
        "weight_kg": 70,
        "crcl_ml_min": 80,
        "infusion_strategy": "Short_Infusion",
        "indication_group": "ventilator-associated pneumonia",
        "dialysis": {"status": "No"},
    })
    assert result["decision"] == "RENAL_ADJUSTED_REGIMEN_SELECTED"
    assert result["dose"] == 1 and result["dose_unit"] == "g"


# ---------------------------------------------------------------------------
# Fail-closed: outside the declared bounds, or unrecognisable
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("over", [
    {"weight_kg": 300},
    {"age_years": 8, "weight_kg": 25},
    {"crcl_ml_min": 250},
])
def test_out_of_declared_bounds_refuses(over):
    result = apply_rules(_vanco(**over))
    assert result["decision"] == "OUT_OF_DECLARED_BOUNDS"
    assert result.get("dose") is None
    assert result.get("declared_bounds")


def test_bounds_take_precedence_over_classification():
    # A novel (mappable) wording must not unlock a patient outside the bounds.
    result = apply_rules(_vanco(weight_kg=300, infection_type="MRSA bacteraemia"))
    assert result["decision"] == "OUT_OF_DECLARED_BOUNDS"


def test_unclassifiable_scenario_abstains_without_dose():
    result = apply_rules(_vanco(infection_type="the patient feels a bit off"))
    assert result["decision"] == "NEEDS_MORE_INFORMATION"
    assert result.get("dose") is None


def test_unsupported_drug_refuses():
    result = apply_rules({
        "requested_drug": "Ceftriaxone",
        "age_years": 60,
        "weight_kg": 70,
        "dialysis": {"status": "No"},
    })
    assert result["decision"] == "UNSUPPORTED_DRUG"
    assert result.get("dose") is None
