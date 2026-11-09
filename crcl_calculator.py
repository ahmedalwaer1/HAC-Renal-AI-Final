"""Cockcroft-Gault creatinine clearance calculator."""


def calculate_crcl(age, weight, creatinine, gender):
    """Calculate creatinine clearance (mL/min) using Cockcroft-Gault."""
    # Formula: Cockcroft-Gault (standard renal function estimate used by the
    # vancomycin/meropenem nomograms referenced in the knowledge base).
    if age is None or weight is None or creatinine is None or gender is None:
        raise ValueError("age, weight, creatinine and gender are all required")
    if creatinine <= 0:
        raise ValueError("creatinine must be > 0")
    if weight <= 0:
        raise ValueError("weight must be > 0")
    if age < 0:
        raise ValueError("age must be >= 0")

    crcl = (140.0 - float(age)) * float(weight) / (72.0 * float(creatinine))
    g = str(gender).strip().lower()
    if g in ("female", "f", "woman", "women"):
        crcl *= 0.85
    elif g not in ("male", "m", "man", "men"):
        raise ValueError("gender must be 'male' or 'female'")
    return crcl

