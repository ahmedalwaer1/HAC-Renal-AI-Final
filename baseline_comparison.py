"""Conventional rule-based comparison for the HAC-Renal AI evaluation plan.

Implements the "conventional rule-based decision support" counterpart named in
the project requirements document: a static dosing-table lookup that takes the
CrCl (or a dialysis modality) and immediately returns the matching table row -
with NO completeness gate, NO safety screen, NO declared-bounds check and NO
monitoring plan.

The point of the comparison is what HAC-Renal AI claims to add over a plain
dosing table: safe abstention when data is missing and detection of high-risk
situations (contraindication, interaction, missing source row). The raw table
numbers are, by design, the same for both sides, so they are not the metric.

Run:  python scripts/baseline_comparison.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rules_engine import _normalize, _run_dosing_function, apply_rules
from data.drug_registry import get_drug_module, resolve_drug
from tools.crcl_calculator import calculate_crcl
from evaluation import HIGH_RISK_DECISIONS, is_abstention, load_cases


def conventional_baseline(patient_input):
    """Static dosing-table lookup.

    Answers whenever CrCl is supplied or computable (on or off dialysis);
    otherwise it has no cell to show and stays silent. It never screens for
    hypersensitivity, interactions, bounds or completeness.
    """
    n = _normalize(patient_input)
    drug_key = resolve_drug(n["drug"])
    if drug_key is None:
        return {"decision": "NO_ANSWER", "reason": "unsupported_drug"}

    if not n["on_dialysis"] and n["crcl_ml_min"] is None:
        can_compute = (
            n["creatinine"] is not None and n["gender"] is not None
            and n["weight_kg"] is not None and n["age"] is not None
        )
        if not can_compute:
            return {"decision": "NO_ANSWER", "reason": "missing_crcl"}
        n["crcl_ml_min"] = calculate_crcl(
            age=n["age"], weight=n["weight_kg"], creatinine=n["creatinine"],
            gender=n["gender"],
        )

    try:
        raw = _run_dosing_function(drug_key, get_drug_module(drug_key), n)
    except ValueError as exc:
        return {"decision": "NO_ANSWER", "reason": str(exc)}

    raw.setdefault("drug", get_drug_module(drug_key)["canonical_name"])
    raw["decision"] = "REGIMEN"  # a plain table just outputs a row
    return raw


def main():
    rows = []
    engine_ms = baseline_ms = 0.0

    for source, case in load_cases():
        test_id = case.get("test_id", "?")
        expected = (case.get("expected_output") or {}).get("decision")

        start = time.perf_counter()
        engine = apply_rules(case.get("patient_input", {}))
        engine_ms += (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        baseline = conventional_baseline(case.get("patient_input", {}))
        baseline_ms += (time.perf_counter() - start) * 1000.0

        rows.append({
            "test_id": test_id,
            "source": source,
            "expected": expected,
            "engine": engine.get("decision"),
            "baseline": baseline.get("decision"),
            "engine_rule": engine.get("rule_id") or engine.get("alert_code"),
            "engine_traceable": bool(engine.get("source_rule")
                                     or engine.get("rule_id")
                                     or engine.get("alert_code")),
            "engine_high_risk": engine.get("decision") in HIGH_RISK_DECISIONS,
            "engine_abstained": is_abstention(engine),
            "baseline_answered": baseline.get("decision") == "REGIMEN",
            "extra_safety": (
                is_abstention(engine)
                and baseline.get("decision") == "REGIMEN"
            ) or (
                engine.get("decision") in HIGH_RISK_DECISIONS
                and baseline.get("decision") != engine.get("decision")
            ),
        })

    # --- report ----------------------------------------------------------
    total = len(rows)
    concordant = sum(r["engine"] == r["expected"] for r in rows)
    high_risk = [r for r in rows if r["engine_high_risk"]]
    abstained = [r for r in rows if r["engine_abstained"]]
    baseline_answered = [r for r in rows if r["baseline_answered"]]
    traceable = sum(r["engine_traceable"] for r in rows)
    extra_safety = [r for r in rows if r["extra_safety"]]

    print("=" * 78)
    print("HAC-Renal AI vs conventional rule-based (dosing table only)")
    print("=" * 78)
    print("%-12s %-28s %-22s %-14s" % ("test_id", "expected", "engine", "baseline"))
    print("-" * 78)
    for r in rows:
        print("%-12s %-28s %-22s %-14s" % (
            r["test_id"], r["expected"] or "-", r["engine"] or "-",
            r["baseline"] or "-"))
    print("-" * 78)
    print("Total synthetic cases               : %d" % total)
    print("Engine concordant with expected     : %d/%d" % (concordant, total))
    print("Engine decisions traceable          : %d/%d" % (traceable, total))
    print("Engine high-risk situations caught  : %d  %s"
          % (len(high_risk), [r["test_id"] for r in high_risk]))
    print("Engine safe abstentions             : %d  %s"
          % (len(abstained), [r["test_id"] for r in abstained]))
    print("Baseline answered (any dose row)    : %d" % len(baseline_answered))
    print("Cases where HAC added value over the table (abstained or blocked where"
          "\n  the plain table still produced a regimen): %d  %s"
          % (len(extra_safety), [r["test_id"] for r in extra_safety]))
    print("Processing time - engine  : %.1f ms  (%d cases)"
          % (engine_ms, total))
    print("Processing time - baseline: %.1f ms  (%d cases)"
          % (baseline_ms, total))


if __name__ == "__main__":
    main()