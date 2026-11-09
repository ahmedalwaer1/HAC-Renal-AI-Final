"""Tests for the synthetic-case evaluation harness and its metrics."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import evaluation
from rules_engine import apply_rules
from tools.vancomycin_dosing import get_vancomycin_dose


def test_every_synthetic_case_is_concordant():
    summary = evaluation.run_evaluation()
    assert summary["total_cases"] == 8
    failing = [r["test_id"] for r in summary["rows"] if not r["concordant"]]
    assert failing == []


def test_all_metric_rates_are_fully_covered():
    metrics = evaluation.run_evaluation()["metrics"]
    assert metrics["concordance_rate"] == 1.0
    assert metrics["high_risk_detection_rate"] == 1.0
    assert metrics["abstention_correct_rate"] == 1.0
    assert metrics["traceability_rate"] == 1.0
    assert metrics["mean_processing_ms"] < 50


def test_compare_reports_only_mismatched_expected_keys():
    diffs = evaluation.compare({"decision": "BLOCK", "dose": 500}, {"decision": "BLOCK"})
    assert diffs == [{"field": "dose", "expected": 500, "actual": None}]


def test_is_abstention_covers_safe_failures():
    assert evaluation.is_abstention({"decision": "NEEDS_MORE_INFORMATION"})
    assert evaluation.is_abstention(
        {"decision": "BLOCK", "alert_code": "MISSING_CRCL"}
    )
    assert not evaluation.is_abstention({"decision": "RENAL_ADJUSTED_REGIMEN_SELECTED"})


def test_vancomycin_ihd_does_not_require_crcl():
    """Regression: dialysis regimens are selected by modality, not by CrCl."""
    result = apply_rules(
        {
            "requested_drug": "Vancomycin",
            "age_years": 62,
            "weight_kg": 80,
            "infection_type": "complicated",
            "dialysis": {"status": "Yes", "modality": "IHD"},
        }
    )
    assert result["decision"] == "DIALYSIS_SPECIFIC_REGIMEN_SELECTED"
    assert result["rule_id"] == "VAN-020"
    assert result["frequency"] == "Once, then 500 mg post-HD only"


def test_vancomycin_still_requires_crcl_off_dialysis():
    try:
        get_vancomycin_dose(age=55, weight_kg=70, infection_type="complicated")
        assert False, "expected ValueError when CrCl cannot be established"
    except ValueError:
        pass
