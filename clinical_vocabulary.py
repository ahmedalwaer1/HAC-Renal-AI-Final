"""Deterministic clinical vocabulary - source-anchored classification.

A clinician can use a hundred different words for the same concept ("bacteraemia",
"blood stream infection", "MRSA sepsis"). The engine must still land on the right
nomogram cell instead of rejecting the request.

Every mapping here is taken from the project's own registered sources - above all
the UCSF vancomycin nomogram definition of a *complicated* infection, quoted in
knowledge_base/vancomycin_rules.md:

    "Complicated Infection Definition:
     CNS infections; endocarditis; pneumonia; bacteremia; osteomyelitis; sepsis"

So this module classifies *what the clinician said*. It never produces a dose and
never invents a category: an unrecognised term returns None and the engine
abstains.
"""
from __future__ import annotations

from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def _tokens(value) -> str:
    """Lower-case, strip punctuation, collapse whitespace."""
    text = str(value or "").lower()
    out = []
    for ch in text:
        out.append(ch if (ch.isalnum() or ch.isspace() or ch == "/") else " ")
    return " ".join("".join(out).replace("/", " ").split())


# ---------------------------------------------------------------------------
# Infection type / severity  (UCSF vancomycin nomogram)
# ---------------------------------------------------------------------------
# Terms the source explicitly lists as complicated, plus their common synonyms.
COMPLICATED_TOKENS = {
    # the source's own category word
    "complicated",
    # CNS
    "cns", "meningitis", "meningeal", "meningoencephalitis", "encephalitis",
    "ventriculitis", "brain", "cerebritis", "shunt",
    # endocarditis / endovascular
    "endocarditis", "endovascular", "valve", "prosthetic",
    # respiratory
    "pneumonia", "cap", "hap", "vap", "empyema", "lung",
    # bloodstream
    "bacteremia", "bacteraemia", "bloodstream", "septicemia", "septicaemia",
    "fungemia", "fungaemia",
    # sepsis
    "sepsis", "septic", "septicemic", "septicemic",
    # bone and joint / deep
    "osteomyelitis", "discitis", "spondylodiscitis", "arthritis", "joint",
    "bone", "abscess", "deep", "necrotizing", "necrotising", "fasciitis",
}

COMPLICATED_PHRASES = (
    "blood stream", "brain abscess", "spinal", "cns infection",
)

UNCOMPLICATED_TOKENS = {
    "uncomplicated", "uncomplex", "simple", "superficial",
}


def classify_infection_type(value) -> Optional[str]:
    """Map any phrasing of the infection to 'complicated' / 'uncomplicated'.

    Returns None when the wording is not covered, so the caller abstains rather
    than defaulting a serious infection to the lower-exposure cell.
    """
    text = _tokens(value)
    if not text:
        return None

    tokens = set(text.split())
    if "uncomplicated" in tokens or "uncomplicated" in text:
        return "uncomplicated"
    if {"un", "complicated"} <= tokens:
        return "uncomplicated"
    if tokens & UNCOMPLICATED_TOKENS and not (tokens & COMPLICATED_TOKENS):
        return "uncomplicated"

    if tokens & COMPLICATED_TOKENS:
        return "complicated"
    if any(phrase in text for phrase in COMPLICATED_PHRASES):
        return "complicated"
    return None


# ---------------------------------------------------------------------------
# Dialysis
# ---------------------------------------------------------------------------
_NO_DIALYSIS = {"no", "none", "nil", "false", "negative", "not", "off"}
# Order matters: continuous modalities are tested before intermittent ones,
# because "continuous venovenous haemodialysis" also contains "haemodialysis".
_MODALITY_TOKENS = (
    ("CRRT", {"crrt", "cvvh", "cvvhd", "cvvhdf", "cvvha", "cvhd", "continuous",
              "venovenous", "hemofiltration", "haemofiltration"}),
    ("IHD", {"ihd", "hd", "hemodialysis", "haemodialysis", "intermittent"}),
    ("PD", {"pd", "peritoneal", "peritonealdialysis"}),
)


def classify_dialysis(value) -> Tuple[Optional[str], Optional[str]]:
    """Return (status, modality) where status is 'Yes' / 'No' / None.

    None status means the wording was not recognised at all; 'Yes' with a None
    modality means the patient is clearly dialysed but the modality needs to be
    confirmed - the engine asks instead of guessing a regimen.
    """
    text = _tokens(value)
    if not text:
        return None, None

    tokens = set(text.split())
    if text in ("not on dialysis", "no dialysis", "non dialysis", "none"):
        return "No", None
    if tokens <= _NO_DIALYSIS | {"dialysis"} and tokens & _NO_DIALYSIS:
        return "No", None

    for modality, markers in _MODALITY_TOKENS:
        if tokens & markers:
            return "Yes", modality

    # Clearly dialysis-related wording but no modality we recognise.
    if "dialysis" in text or "dialysed" in text or "dialyzed" in text or "rrt" in tokens:
        return "Yes", None
    return None, None


# ---------------------------------------------------------------------------
# Meropenem indication  (UCSF meropenem table: standard vs meningitis/CF)
# ---------------------------------------------------------------------------
_INDICATION_CNS_TOKENS = {
    "meningitis", "meningeal", "meningoencephalitis", "encephalitis",
    "ventriculitis", "cns", "brain", "cerebritis",
}
_INDICATION_CF_TOKENS = {"cf", "cystic", "fibrosis", "bronchiectasis"}
_STANDARD_MARKERS = {
    "standard", "std", "usual", "routine", "normal", "empiric", "empirical",
    "regular", "default",
}
_NON_CNS_INFECTION_TOKENS = {
    "pneumonia", "cap", "hap", "vap", "uti", "pyelonephritis", "sepsis",
    "septic", "bacteremia", "bacteraemia", "bloodstream", "skin", "cellulitis",
    "intra", "abdominal", "peritonitis", "cholangitis", "osteomyelitis", "joint",
    "endocarditis", "wound", "abscess", "empyema", "febrile", "neutropenia",
}


def classify_meropenem_indication(value) -> Optional[str]:
    """Map free text to 'Standard' or 'Meningitis_CF' (the two source rows)."""
    text = _tokens(value)
    if not text:
        return None

    tokens = set(text.split())
    if tokens & _INDICATION_CNS_TOKENS:
        return "Meningitis_CF"
    if {"cystic", "fibrosis"} <= tokens or "cf" in tokens:
        return "Meningitis_CF"
    if tokens & _STANDARD_MARKERS:
        return "Standard"
    if tokens & _NON_CNS_INFECTION_TOKENS:
        return "Standard"
    return None


__all__ = [
    "classify_infection_type",
    "classify_dialysis",
    "classify_meropenem_indication",
    "COMPLICATED_TOKENS",
]
