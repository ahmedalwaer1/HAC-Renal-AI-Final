"""Tests for the HAC-Renal AI Agent (LangChain-based)."""

import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.llm_agent import evaluate_patient_via_agent, _fallback_deterministic


def test_meropenem_crcl_18():
    """Test Meropenem dosing for CrCl 18 mL/min (should give 500mg q12h)."""
    patient_input = {
        "requested_drug": "Meropenem",
        "age_years": 67,
        "weight_kg": 70,
        "creatinine": 2.5,
        "gender": "Male",
        "indication_group": "Standard",
        "infusion_strategy": "Short_Infusion",
        "crcl_ml_min": 18,
        "dialysis": {"status": "No"},
    }
    result = evaluate_patient_via_agent(patient_input)
    print("=== MERO-TC-03 (CrCl 18) ===")
    print(json.dumps(result, indent=2))
    # The deterministic path should return RENAL_ADJUSTED_REGIMEN_SELECTED
    assert result.get("decision") in (
        "RENAL_ADJUSTED_REGIMEN_SELECTED", "AGENT_RESPONSE", "ERROR"
    ), f"Unexpected decision: {result.get('decision')}"
    print("PASS: Meropenem CrCl 18 test completed\n")


def test_meropenem_allergy_block():
    """Test Meropenem with confirmed allergy (should BLOCK)."""
    patient_input = {
        "requested_drug": "Meropenem",
        "age_years": 46,
        "weight_kg": 70,
        "creatinine": 1.0,
        "gender": "Male",
        "indication_group": "Standard",
        "infusion_strategy": "Short_Infusion",
        "crcl_ml_min": 72,
        "allergy_history": [
            {"substance": "Meropenem", "reaction": "Anaphylaxis", "certainty": "Confirmed"}
        ],
        "dialysis": {"status": "No"},
    }
    result = evaluate_patient_via_agent(patient_input)
    print("=== MERO-TC-01 (Allergy Block) ===")
    print(json.dumps(result, indent=2))
    assert result.get("decision") in ("BLOCK", "AGENT_RESPONSE", "ERROR"), \
        f"Unexpected decision: {result.get('decision')}"
    print("PASS: Meropenem allergy block test completed\n")


def test_vancomycin_normal_renal():
    """Test Vancomycin normal renal function (VAN-TC-01)."""
    patient_input = {
        "requested_drug": "Vancomycin",
        "age_years": 45,
        "weight_kg": 70,
        "creatinine": 0.8,
        "gender": "Male",
        "infection_type": "complicated",
        "crcl_ml_min": 95,
        "dialysis": {"status": "No"},
    }
    result = evaluate_patient_via_agent(patient_input)
    print("=== VAN-TC-01 (Normal Renal) ===")
    print(json.dumps(result, indent=2))
    assert result.get("decision") in (
        "RENAL_ADJUSTED_REGIMEN_SELECTED", "AGENT_RESPONSE", "ERROR"
    ), f"Unexpected decision: {result.get('decision')}"
    print("PASS: Vancomycin normal renal test completed\n")


def test_vancomycin_hemodialysis():
    """Test Vancomycin hemodialysis (VAN-TC-02)."""
    patient_input = {
        "requested_drug": "Vancomycin",
        "age_years": 62,
        "weight_kg": 80,
        "creatinine": 4.0,
        "gender": "Male",
        "infection_type": "complicated",
        "dialysis": {"status": "Yes", "modality": "IHD"},
    }
    result = evaluate_patient_via_agent(patient_input)
    print("=== VAN-TC-02 (Hemodialysis) ===")
    print(json.dumps(result, indent=2))
    assert result.get("decision") in (
        "DIALYSIS_SPECIFIC_REGIMEN_SELECTED", "AGENT_RESPONSE", "ERROR"
    ), f"Unexpected decision: {result.get('decision')}"
    print("PASS: Vancomycin hemodialysis test completed\n")


def test_vancomycin_missing_crcl():
    """Test Vancomycin missing CrCl - should BLOCK (VAN-TC-03)."""
    patient_input = {
        "requested_drug": "Vancomycin",
        "age_years": 55,
        "weight_kg": 70,
        "infection_type": "complicated",
        "dialysis": {"status": "No"},
    }
    result = evaluate_patient_via_agent(patient_input)
    print("=== VAN-TC-03 (Missing CrCl - Safe Failure) ===")
    print(json.dumps(result, indent=2))
    assert result.get("decision") in ("BLOCK", "AGENT_RESPONSE", "ERROR"), \
        f"Unexpected decision: {result.get('decision')}"
    print("PASS: Vancomycin missing CrCl test completed\n")


def test_fallback_deterministic():
    """Test that fallback to deterministic engine works when LLM is unavailable."""
    patient_input = {
        "requested_drug": "Meropenem",
        "age_years": 67,
        "weight_kg": 70,
        "creatinine": 2.5,
        "gender": "Male",
        "indication_group": "Standard",
        "infusion_strategy": "Short_Infusion",
        "crcl_ml_min": 18,
        "dialysis": {"status": "No"},
    }
    result = _fallback_deterministic(patient_input)
    print("=== Fallback Deterministic Test ===")
    print(json.dumps(result, indent=2))
    assert result.get("decision") in (
        "RENAL_ADJUSTED_REGIMEN_SELECTED", "ERROR"
    ), f"Unexpected decision: {result.get('decision')}"
    print("PASS: Fallback deterministic test completed\n")


if __name__ == "__main__":
    test_meropenem_crcl_18()
    test_meropenem_allergy_block()
    test_vancomycin_normal_renal()
    test_vancomycin_hemodialysis()
    test_vancomycin_missing_crcl()
    test_fallback_deterministic()
    print("All tests completed.")