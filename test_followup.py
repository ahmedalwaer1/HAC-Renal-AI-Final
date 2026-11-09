"""Tests for the deterministic clinical follow-up engine (stage 4)."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import followup_engine
from followup_engine import (
    compare_regimens,
    delete_case,
    list_cases,
    load_case,
    open_case,
    record_event,
    save_case,
)


def _vanco_case():
    return open_case(
        {
            "requested_drug": "Vancomycin",
            "age_years": 70,
            "weight_kg": 70,
            "gender": "Male",
            "crcl_ml_min": 100,
            "infection_type": "complicated",
            "dialysis": {"status": "No"},
        },
        label="test case",
    )


def test_open_case_records_baseline_and_schedule():
    case = _vanco_case()
    assert case["current_result"]["decision"] == "RENAL_ADJUSTED_REGIMEN_SELECTED"
    assert case["timeline"][0]["event"] == "baseline"
    assert case["drug"] == "vancomycin"
    items = [i["item"] for i in case["next_due"]]
    assert "Vancomycin exposure measurement (AUC24 preferred)" in items
    assert "Antibiotic time-out (indication, dose, duration, stop date)" in items


def test_new_creatinine_supersedes_the_stored_crcl():
    """Regression: a stored CrCl must not mask a new creatinine."""
    case = _vanco_case()
    reassessment = record_event(case, {"type": "renal_function",
                                       "data": {"creatinine": 2.5}})
    change = reassessment["regimen_change"]
    assert change["changed"] is True
    fields = {d["field"]: (d["before"], d["after"]) for d in change["fields"]}
    assert fields["frequency"] == ("q12h", "q24h")
    assert fields["rule_id"] == ("VAN-006", "VAN-015")
    assert reassessment["crcl_recomputed_from_creatinine"] is True


def test_regimen_comparison_reports_no_change_when_state_is_stable():
    case = _vanco_case()
    # 0.7 mg/dL recomputes to CrCl >90 mL/min, i.e. the same band as the
    # baseline, so the regimen must not move.
    reassessment = record_event(case, {"type": "renal_function",
                                       "data": {"creatinine": 0.7}})
    assert reassessment["severity"] == "ADJUST"
    assert reassessment["regimen_change"]["changed"] is False


def test_a_different_band_moves_the_regimen():
    case = _vanco_case()
    # 1.0 mg/dL recomputes to CrCl ~68 mL/min -> 50-90 band -> VAN-010.
    reassessment = record_event(case, {"type": "renal_function",
                                       "data": {"creatinine": 1.0}})
    assert reassessment["regimen_change"]["changed"] is True
    assert case["current_result"]["rule_id"] == "VAN-010"


def test_auc_and_trough_levels_are_classified():
    case = _vanco_case()
    low = record_event(case, {"type": "drug_level",
                              "data": {"level_type": "auc", "value": 300}})
    assert low["level_assessment"]["status"] == "BELOW_TARGET"
    assert low["level_assessment"]["direction"] == "increase exposure"
    assert low["level_assessment"]["source"] == "IDSA_VANCOMYCIN_2020"

    high = record_event(case, {"type": "drug_level",
                               "data": {"level_type": "trough", "value": 22}})
    assert high["level_assessment"]["status"] == "ABOVE_TARGET"
    assert high["level_assessment"]["direction"] == "reduce exposure"
    assert high["level_assessment"]["target_label"] == "15-20 mg/L"

    target = record_event(case, {"type": "drug_level",
                                 "data": {"level_type": "auc", "value": 500}})
    assert target["level_assessment"]["status"] == "WITHIN_TARGET"
    assert target["level_assessment"]["direction"] == "maintain the current dose"


def test_meropenem_level_is_not_compared_without_a_numeric_target():
    """The project defines no numeric meropenem threshold, so nothing is guessed."""
    case = open_case({"requested_drug": "Meropenem", "crcl_ml_min": 40,
                      "indication_group": "Standard",
                      "infusion_strategy": "Short_Infusion",
                      "dialysis": {"status": "No"}})
    reassessment = record_event(case, {"type": "drug_level", "data": {"value": 30}})
    assert reassessment["level_assessment"]["status"] == "NUMERIC_TARGET_UNAVAILABLE"


def test_dialysis_session_switches_to_the_dialysis_regimen():
    case = open_case({"requested_drug": "Meropenem", "crcl_ml_min": 40,
                      "indication_group": "Standard",
                      "infusion_strategy": "Short_Infusion",
                      "dialysis": {"status": "No"}})
    reassessment = record_event(case, {"type": "dialysis_session",
                                       "data": {"modality": "IHD"}})
    assert case["current_result"]["decision"] == "DIALYSIS_SPECIFIC_REGIMEN_SELECTED"
    assert reassessment["regimen_change"]["changed"] is True
    assert reassessment["rule_id"] == "FU-003"


def test_culture_result_clears_the_empirical_flag():
    case = _vanco_case()
    before = [f["rule_id"] for f in case["current_result"]["therapy_assessment"]]
    assert "THER-004" in before
    reassessment = record_event(case, {"type": "microbiology",
                                       "data": {"culture_result": "MRSA, vancomycin S"}})
    assert reassessment["empirical_flag_cleared"] is True


def test_clinical_response_and_toxicity_drive_the_severity():
    case = _vanco_case()
    improving = record_event(case, {"type": "clinical_response",
                                    "data": {"response": "improving"}})
    assert improving["severity"] == "CONTINUE"
    assert improving["requires_pharmacist_action"] is False

    failing = record_event(case, {"type": "clinical_response",
                                  "data": {"response": "no_improvement"}})
    assert failing["severity"] == "ESCALATE"
    assert failing["requires_pharmacist_action"] is True

    toxicity = record_event(case, {"type": "adverse_effect",
                                   "data": {"effect": "acute kidney injury"}})
    assert toxicity["severity"] == "STOP"
    assert toxicity["hold_automated_recommendation"] is True


def test_medication_change_re_screens_interactions():
    case = open_case({"requested_drug": "Meropenem", "crcl_ml_min": 64,
                      "indication_group": "Standard",
                      "infusion_strategy": "Short_Infusion",
                      "dialysis": {"status": "No"}})
    reassessment = record_event(case, {"type": "medication_change",
                                       "data": {"medications": ["Valproate"]}})
    assert case["current_result"]["decision"] == "HIGH_PRIORITY_INTERACTION_ALERT"
    assert reassessment["regimen_change"]["changed"] is True


def test_unknown_event_type_is_rejected():
    case = _vanco_case()
    with pytest.raises(ValueError):
        record_event(case, {"type": "made_up_event", "data": {}})


def test_case_persistence_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(followup_engine, "CASES_DIR", str(tmp_path))
    case = _vanco_case()
    record_event(case, {"type": "renal_function", "data": {"creatinine": 2.5}})

    save_case(case)
    assert [c["case_id"] for c in list_cases()] == [case["case_id"]]

    reloaded = load_case(case["case_id"])
    assert len(reloaded["timeline"]) == len(case["timeline"]) == 2
    assert reloaded["patient"].get("crcl_ml_min") is None
    assert reloaded["current_result"]["rule_id"] == "VAN-015"

    assert delete_case(case["case_id"]) is True
    assert list_cases() == []


def test_compare_regimens_lists_field_differences():
    diff = compare_regimens({"dose": 1250, "frequency": "q12h"},
                            {"dose": 1000, "frequency": "q12h"})
    assert diff["changed"] is True
    assert diff["fields"] == [{"field": "dose", "before": 1250, "after": 1000}]
