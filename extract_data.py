"""Extract raw pharmacy data from Excel workbooks into Markdown knowledge-base files.

Run from the project root:
    python scripts/extract_data.py
"""
import os
import shutil
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(PROJECT_ROOT.parent)))
KB_DIR = PROJECT_ROOT / "knowledge_base"
DATA_DIR = PROJECT_ROOT / "data"

VANCOMYCIN_XLSX = RAW_DATA_DIR / "HAC_Renal_AI_Vancomycin_Data.xlsx"
MEROPENEM_UCSF_XLSX = RAW_DATA_DIR / "HAC_Renal_AI_Meropenem_UCSF_Data_Entry.xlsx"
MEROPENEM_TDM_XLSX = RAW_DATA_DIR / "HAC_Renal_AI_Meropenem_TDM.xlsx"
SYNTHETIC_JSON = RAW_DATA_DIR / "HAC_Renal_AI_Meropenem_Synthetic_Test_Cases.json"


def read_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    """Read a single sheet as strings to preserve source values exactly."""
    return pd.read_excel(
        path,
        sheet_name=sheet_name,
        dtype=str,
        keep_default_na=False,
    )


def df_to_markdown(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a GitHub-flavoured Markdown table."""
    if df is None or df.empty:
        return "_No rows._\n"
    columns = [str(c) for c in df.columns]
    rows = []
    for _, row in df.iterrows():
        rows.append([str(v).replace("|", "\\|").replace("\n", " ") for v in row.tolist()])
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return header + "\n" + sep + "\n" + body + "\n"


def all_sheets(path: Path) -> dict:
    xls = pd.ExcelFile(path)
    out = {}
    for name in xls.sheet_names:
        out[name] = read_sheet(path, name)
    return out


def build_vancomycin_md() -> str:
    sheets = all_sheets(VANCOMYCIN_XLSX)
    lines = []
    lines.append("# Vancomycin Dosing Knowledge Base")
    lines.append("")
    lines.append("Source: UCSF Vancomycin Initial Dosing Nomogram (extracted from HAC_Renal_AI_Vancomycin_Data.xlsx).")
    lines.append("Rule IDs (VAN-001 .. VAN-021) are preserved from the source workbook.")
    lines.append("")
    for name, df in sheets.items():
        lines.append(f"## Sheet: {name}")
        lines.append("")
        lines.append(df_to_markdown(df))
        lines.append("")
    return "\n".join(lines)


def build_meropenem_rules_md() -> str:
    sheets = all_sheets(MEROPENEM_UCSF_XLSX)
    lines = []
    lines.append("# Meropenem Dosing Knowledge Base (UCSF)")
    lines.append("")
    lines.append("Source: UCSF Infectious Diseases Management Program - Meropenem (extracted from HAC_Renal_AI_Meropenem_UCSF_Data_Entry.xlsx).")
    lines.append("Safety rule IDs (MER-001 .. MER-011) are preserved from the source workbook.")
    lines.append("")
    for name, df in sheets.items():
        lines.append(f"## Sheet: {name}")
        lines.append("")
        lines.append(df_to_markdown(df))
        lines.append("")
    return "\n".join(lines)


def build_meropenem_tdm_md() -> str:
    sheets = all_sheets(MEROPENEM_TDM_XLSX)
    lines = []
    lines.append("# Meropenem Therapeutic Drug Monitoring (TDM) Knowledge Base")
    lines.append("")
    lines.append("Source: HAC_Renal_AI_Meropenem_TDM.xlsx (TDM, PK/PD targets, renal relations, triggers, safety).")
    lines.append("")
    for name, df in sheets.items():
        lines.append(f"## Sheet: {name}")
        lines.append("")
        lines.append(df_to_markdown(df))
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    KB_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    (KB_DIR / "vancomycin_rules.md").write_text(build_vancomycin_md(), encoding="utf-8")
    (KB_DIR / "meropenem_rules.md").write_text(build_meropenem_rules_md(), encoding="utf-8")
    (KB_DIR / "meropenem_tdm.md").write_text(build_meropenem_tdm_md(), encoding="utf-8")

    if SYNTHETIC_JSON.exists():
        shutil.copyfile(SYNTHETIC_JSON, DATA_DIR / "synthetic_cases.json")
    else:
        raise FileNotFoundError(f"Synthetic test cases file not found: {SYNTHETIC_JSON}")

    print("Extraction complete.")
    print(f"  Knowledge base: {KB_DIR}")
    print(f"  Synthetic cases: {DATA_DIR / 'synthetic_cases.json'}")


if __name__ == "__main__":
    main()
