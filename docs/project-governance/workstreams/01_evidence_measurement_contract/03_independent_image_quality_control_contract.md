# Task 03: Independent Image-Quality Control Contract

Status: complete. Contract version: `pferi_v2_independent_quality_control_contract_v1`.

## Purpose

The primary PF-ERI v2 comparison is meaningful only if its active control is genuinely independent of pair evidence. This task defines a conservative image-quality control set that is computed from each image before pair evidence is measured. It is not an image-quality filter and it is not a claim that the controls predict reviewability. Its sole current purpose is to prevent an apparent PF-ERI increment from being explained by basic variation in usable image information.

## Active Control Definition

Four automatic image-level candidates form the provisional control set: animal coverage fraction, native pixel count, sharpness measure, and exposure-clipping fraction. The pair-level columns use a pre-declared worst-side transformation: the minimum of coverage, pixels, and sharpness, and the maximum of clipping. Both raw image-level values and their deterministic pair aggregation must be retained. This rule is fixed before outcomes exist, so it cannot be chosen because one aggregation happens to look favorable.

The controls may use decoded pixels, decoded dimensions, and the output of their registered image-level extractor. They may not use descriptor similarity, candidate rank, local matching, cross-descriptor disagreement, review outcomes, routes, identity truth, manual structural annotations, or a v1-derived proxy or constant. Local-match coverage and descriptor disagreement remain pair-evidence candidates for Task 04, not quality controls. Infrared likelihood is recorded as an automatic context variable for stratification and failure auditing, but is not included in the active control by default: its direction is environmental rather than intrinsically favorable, so treating it as generic quality would risk encoding source conditions instead of visual information.

## Feasibility Boundary

No listed control is admitted to a v2 model yet. The Workstream 02 pilot must establish automatic execution without manual rescue, nonconstant valid outputs, explicit failure and runtime logs, outcome-blind execution, and reproducible pair aggregation. The numerical retention gates must be frozen before pilot outcomes are reviewed. A control that fails any gate is removed, redefined, or retained only as an audit variable; it is never silently imputed, substituted by a historical value, or manually corrected into the primary comparison.

## Validation

`scripts/validate_v2_independent_quality_control_contract.py` validates the contract at `schemas/pferi_v2/independent_quality_control_contract_v1.json` against the v2 feature dictionary. It rejects manual/oracle fields, pair-level evidence fields, context-only fields, descriptor-like inputs, missing leakage prohibitions, and undefined pair aggregation. A passing result establishes the design boundary only; it does not establish measurement validity, predictive value, or readiness for model fitting.

```bash
python3 scripts/validate_v2_independent_quality_control_contract.py \
  --contract schemas/pferi_v2/independent_quality_control_contract_v1.json \
  --dictionary schemas/pferi_v2/evidence_measurement_dictionary_v1.json \
  --audit-json path/to/independent_quality_control_audit.json
```
