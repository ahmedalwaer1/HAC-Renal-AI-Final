# Meropenem Dosing Rules

## Source: UCSF Infectious Diseases Management Program - Meropenem
**URL:** https://idmp.ucsf.edu/content/meropenem

## Safety Source: DailyMed - Meropenem for Injection Prescribing Information
**URL:** https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ca5f501c-6520-4d09-aae2-4f5db74d468f

## MER-001: Renal Adjustment
Rule: Select non-dialysis short-infusion regimen using the documented CrCl band.
Trigger: CrCl must be available and expressed in mL/min.
System Action: Block automatic dose selection if CrCl is missing or outside defined bands.

## MER-002: Indication
Rule: Select the indication-specific row (standard vs meningitis/cystic fibrosis).
Trigger: Indication must be classified.
System Action: Do not default meningitis/CF patients to standard dosing.

## MER-003: Infusion Strategy
Rule: Keep short infusion and extended infusion regimens separate.
Trigger: Infusion strategy must be explicitly selected/recommended.
System Action: Do not combine dose and infusion duration across strategies.

## MER-004: Extended Infusion Threshold
Rule: For CrCl <26 mL/min, source directs use of short infusion.
Trigger: CrCl band <26 mL/min.
System Action: Do not create an extended-infusion dose for this band from this source.

## MER-005: IHD
Rule: Use IHD-specific table, not non-dialysis table, for IHD patients.
Trigger: Dialysis modality = IHD.
System Action: Retain qPM wording until timing is clarified.

## MER-006: CVHD/CVVHD
Rule: Apply only to the continuous hemodialysis modality named in the source.
Trigger: Modality terminology must be confirmed.
System Action: Do not generalize to CVVH or CVVHDF without separate evidence.

## MER-007: CVVHD Flow
Rule: If flow rate >2 L/hr, refer to ID/ASP pharmacy.
Trigger: CVVHD flow rate >2 L/hr.
System Action: Trigger review; do not extrapolate a new dose.

## MER-008: PD
Rule: No PD dose is provided in this extract.
Trigger: Dialysis modality = PD.
System Action: Return 'source data unavailable'; seek separate PD reference.

## MER-009: Loading Dose Timing
Rule: When loading dose is used in extended infusion, maintenance starts 4 hours after loading dose.
Trigger: Extended-infusion initiation.
System Action: Preserve the condition and check if patient already receiving short infusion.

## MER-010: Meningitis Extended Infusion
Rule: Evidence is limited; source advises discussion with ID/ASP providers.
Trigger: Indication = meningitis and extended infusion considered.
System Action: Require clinical review.

## MER-011: Clinical Validation
Rule: All doses require review against current institutional protocol and patient-specific factors.
Trigger: Before clinical use.
System Action: Workbook is not a prescribing order.

## Short-Infusion Renal Dosing Table (UCSF)
| CrCl Band | Standard Indication | Meningitis/CF |
|-----------|-------------------|---------------|
| >50 mL/min | 1 g q8h | 2 g q8h |
| 26-50 mL/min | 1 g q12h | 2 g q12h |
| 10-25 mL/min | 500 mg q12h | 1 g q12h |
| <10 mL/min | 500 mg q24h | 1 g q24h |

## Extended-Infusion Regimen (MER-003)
Loading dose: 1 g IV over 30 min
Maintenance (CrCl >50, Standard): 1 g IV over 3h q8h
Maintenance (CrCl >50, Meningitis/CF): 2 g IV over 3h q8h
Maintenance (CrCl 26-50, Standard): 1 g IV over 3h q12h
Maintenance (CrCl 26-50, Meningitis/CF): 2 g IV over 3h q12h
Note: For CrCl <26 mL/min, use short infusion instead (MER-004).
