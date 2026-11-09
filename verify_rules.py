"""Verification tests for deterministic renal dosing rules (Sprint 1)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.crcl_calculator import calculate_crcl
from tools.vancomycin_dosing import get_vancomycin_dose
from tools.meropenem_dosing import get_meropenem_dose


def test_crcl_male():
    # Cockcroft-Gault: 70yo, 70kg, Cr 1.0, male
    val = calculate_crcl(70, 70, 1.0, "male")
    assert round(val, 2) == round((140 - 70) * 70 / (72 * 1.0), 2)


def test_crcl_female_factor():
    m = calculate_crcl(70, 70, 1.0, "male")
    f = calculate_crcl(70, 70, 1.0, "female")
    assert abs(f - m * 0.85) < 1e-9


def test_crcl_missing_raises():
    try:
        calculate_crcl(None, 70, 1.0, "male")
        assert False
    except ValueError:
        pass


def test_vancomycin_van001():
    r = get_vancomycin_dose(age=50, weight_kg=55, crcl_ml_min=100, infection_type="complicated")
    assert r["rule_id"] == "VAN-001"
    assert r["dose_mg"] == 750
    assert r["frequency"] == "q8h"


def test_vancomycin_van013_override():
    r = get_vancomycin_dose(age=50, weight_kg=110, crcl_ml_min=70, infection_type="complicated")
    assert r["rule_id"] == "VAN-013"
    assert r["dose_mg"] == 1000
    assert r["frequency"] == "q8h"


def test_vancomycin_dialysis_crrt():
    r = get_vancomycin_dose(age=60, weight_kg=80, crcl_ml_min=10, dialysis_modality="CRRT")
    assert r["rule_id"] == "VAN-019"


def test_vancomycin_missing_raises():
    try:
        get_vancomycin_dose(age=60, weight_kg=80)
        assert False
    except ValueError:
        pass


def test_meropenem_tc03():
    r = get_meropenem_dose(crcl_ml_min=18, indication="Standard", infusion_strategy="Short_Infusion")
    assert r["decision"] == "RENAL_ADJUSTED_REGIMEN_SELECTED"
    assert r["dose"] == 500
    assert r["dose_unit"] == "mg"
    assert r["route"] == "IV"
    assert r["frequency"] == "Every 12 hours"


def test_meropenem_tc04_ihd():
    r = get_meropenem_dose(indication="Standard", dialysis_modality="IHD")
    assert r["decision"] == "DIALYSIS_SPECIFIC_REGIMEN_SELECTED"
    assert r["dose"] == 500
    assert r["maintenance_frequency_source_text"] == "qPM"
    assert r["do_not_reinterpret_qPM"] is True


def test_meropenem_tc05_flow():
    r = get_meropenem_dose(indication="Standard", dialysis_modality="CVHD", cvvhd_flow_rate=2.5)
    assert r["decision"] == "SPECIALIST_REVIEW_REQUIRED"
    assert r["alert_code"] == "CVVHD_FLOW_ABOVE_2_L_H"
    assert r["automatic_dose_finalization_allowed"] is False


def test_meropenem_tc01_allergy():
    r = get_meropenem_dose(
        crcl_ml_min=72,
        allergy_history=[{"substance": "Meropenem", "reaction": "Anaphylaxis", "certainty": "Confirmed"}],
    )
    assert r["decision"] == "BLOCK"
    assert r["alert_code"] == "CONFIRMED_HYPERSENSITIVITY"
    assert r["dose_calculation_allowed"] is False


def test_meropenem_tc02_valproate():
    r = get_meropenem_dose(
        crcl_ml_min=64,
        concomitant_medications=[{"drug": "Valproate", "indication": "Epilepsy"}],
    )
    assert r["decision"] == "HIGH_PRIORITY_INTERACTION_ALERT"
    assert r["alert_code"] == "MEROPENEM_VALPROATE"
    assert r["dose_calculation_allowed"] is True


def test_meropenem_pd_unavailable():
    r = get_meropenem_dose(indication="Standard", dialysis_modality="PD")
    assert r["decision"] == "SOURCE_DATA_UNAVAILABLE"
    assert r["source_rule"] == "MER-008"


def test_meropenem_extended_low_crcl():
    r = get_meropenem_dose(crcl_ml_min=20, indication="Standard", infusion_strategy="Extended_Infusion")
    assert r["decision"] == "USE_SHORT_INFUSION"
    assert r["source_rule"] == "MER-004"


def test_meropenem_missing_indication_raises():
    try:
        get_meropenem_dose(crcl_ml_min=70, infusion_strategy="Short_Infusion")
        assert False
    except ValueError:
        pass


def test_meropenem_missing_infusion_raises():
    try:
        get_meropenem_dose(crcl_ml_min=70, indication="Standard")
        assert False
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Four-stage engine tests (registry / completeness gate / safety / monitoring)
# ---------------------------------------------------------------------------
from rules_engine import apply_rules
from data.drug_registry import supported_drugs


def test_engine_supported_drugs_are_registered():
    assert set(supported_drugs()) == {"Meropenem", "Vancomycin"}


def test_engine_rejects_unregistered_drug():
    r = apply_rules({
        "requested_drug": "Piperacillin/Tazobactam",
        "age_years": 60, "weight_kg": 70, "creatinine": 1.0, "gender": "Male",
        "dialysis": {"status": "No"},
    })
    assert r["decision"] == "UNSUPPORTED_DRUG"
    assert r["dose_calculation_allowed"] is False


def test_engine_abstains_without_dialysis_status():
    r = apply_rules({
        "requested_drug": "Meropenem",
        "age_years": 60, "weight_kg": 70, "creatinine": 1.0, "gender": "Male",
        "indication_group": "Standard", "infusion_strategy": "Short_Infusion",
    })
    assert r["decision"] == "NEEDS_MORE_INFORMATION"
    assert "dialysis_status" in r["missing_fields"]


def test_engine_abstains_without_indication():
    r = apply_rules({
        "requested_drug": "Meropenem",
        "age_years": 60, "weight_kg": 70, "crcl_ml_min": 80, "gender": "Male",
        "infusion_strategy": "Short_Infusion",
        "dialysis": {"status": "No"},
    })
    assert r["decision"] == "NEEDS_MORE_INFORMATION"
    assert "indication_group" in r["missing_fields"]


def test_engine_blocks_when_crcl_cannot_be_established():
    r = apply_rules({
        "requested_drug": "Vancomycin",
        "age_years": 55, "weight_kg": 70, "infection_type": "complicated",
        "dialysis": {"status": "No"},
    })
    assert r["decision"] == "BLOCK"
    assert r["alert_code"] == "MISSING_CRCL"
    assert r["dose_calculation_allowed"] is False


def test_engine_vancomycin_is_covered_by_the_generic_safety_layer():
    r = apply_rules({
        "requested_drug": "Vancomycin",
        "age_years": 45, "weight_kg": 70, "crcl_ml_min": 95,
        "infection_type": "complicated", "dialysis": {"status": "No"},
        "allergy_history": [
            {"substance": "Vancomycin", "reaction": "Anaphylaxis", "certainty": "Confirmed"}
        ],
    })
    assert r["decision"] == "BLOCK"
    assert r["alert_code"] == "CONFIRMED_HYPERSENSITIVITY"


def test_engine_unifies_vancomycin_dose_schema():
    r = apply_rules({
        "requested_drug": "Vancomycin",
        "age_years": 45, "weight_kg": 70, "crcl_ml_min": 95,
        "infection_type": "complicated", "dialysis": {"status": "No"},
    })
    assert r["decision"] == "RENAL_ADJUSTED_REGIMEN_SELECTED"
    assert r["rule_id"] == "VAN-002"
    assert r["dose"] == 1000
    assert r["dose_unit"] == "mg"


def test_engine_interaction_alert_keeps_the_monitoring_plan():
    r = apply_rules({
        "requested_drug": "Meropenem",
        "age_years": 39, "crcl_ml_min": 64, "dialysis": {"status": "No"},
        "concomitant_medications": [{"drug": "Valproate", "indication": "Epilepsy"}],
    })
    assert r["decision"] == "HIGH_PRIORITY_INTERACTION_ALERT"
    assert "monitoring_plan" in r
    assert r["monitoring_plan"]["reassessment_triggers"]


def test_engine_monitoring_plan_adapts_to_dialysis_modality():
    r = apply_rules({
        "requested_drug": "Meropenem",
        "age_years": 59, "indication_group": "Standard",
        "dialysis": {"status": "Yes", "modality": "IHD"},
    })
    assert r["decision"] == "DIALYSIS_SPECIFIC_REGIMEN_SELECTED"
    assert r["monitoring_plan"]["dialysis_specific"]


def test_engine_flags_undocumented_infection():
    r = apply_rules({
        "requested_drug": "Meropenem",
        "age_years": 60, "crcl_ml_min": 80, "indication_group": "Standard",
        "infusion_strategy": "Short_Infusion", "dialysis": {"status": "No"},
        "infection_documented": False,
    })
    rule_ids = [f["rule_id"] for f in r["therapy_assessment"]]
    assert "THER-005" in rule_ids

