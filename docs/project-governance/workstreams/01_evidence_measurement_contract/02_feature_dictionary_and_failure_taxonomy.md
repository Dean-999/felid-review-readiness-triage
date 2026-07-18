# Task 02: Feature Dictionary and Failure Taxonomy

Status: complete.  Dictionary version: `pferi_v2_evidence_measurement_dictionary_v1`.

## Purpose

This task converts the v2 evidential-admissibility construct into named measurements without pretending that a plausible measurement is already scientifically feasible. The dictionary separates automatic core candidates, oracle measurements, and provenance metadata. A candidate may enter neither the primary model nor the reviewer interface merely because it appears in the dictionary. Automatic candidates remain pending the Workstream 02 feasibility and Workstream 04 automatic-extraction checks; oracle and metadata fields are permanently blocked from the primary automatic model.

## Measurement and Failure Contract

Each measurement record must identify its entity, feature name, numeric or categorical value, value status, failure code, source mode, extractor or annotation version, runtime, and manual-correction time. A zero is a real measured value only when the value status is `not_missing`; it cannot stand for unavailable evidence. A blank value must carry a non-`not_missing` status and a declared failure code. The global taxonomy distinguishes an absent upstream input, decoding failure, no detected subject, low detector confidence, inference failure, invalid model output, inapplicability, restricted metadata, and ambiguous structural annotation. This ensures that a low measurement, an unavailable measurement, and a failed measurement remain analytically distinct.

The dictionary contains seven automatic candidates: animal coverage, native pixel count, sharpness, exposure clipping, infrared likelihood, local-match coverage, and descriptor disagreement. Their operational definitions are intentionally extractor-neutral until an implementation is registered. It also contains four oracle-only structural measures: visible patterned area, viewpoint compatibility, shared visible body region, and occlusion. These give the feasibility pilot a way to compare automatic measurements with a feature-only reference without leaking an outcome-review judgement into the model. Descriptor name, queue snapshot, and source dataset are metadata for provenance and stratification only.

## Validation and Boundary

`scripts/validate_v2_evidence_measurement_dictionary.py` validates the checked-in dictionary at `schemas/pferi_v2/evidence_measurement_dictionary_v1.json`. It rejects outcome- or identity-like feature names, a manual field masquerading as an automatic candidate, and any oracle or metadata field that is allowed into the primary model. The validator checks a contract, not a model: a passing result does not demonstrate valid extraction, nonconstant values, annotation reliability, predictive benefit, calibration, or a deployment threshold.

```bash
python3 scripts/validate_v2_evidence_measurement_dictionary.py \
  --dictionary schemas/pferi_v2/evidence_measurement_dictionary_v1.json \
  --audit-json path/to/evidence_measurement_dictionary_audit.json
```

The next task must define the independent image-quality controls and test whether they are actually measurable and nonconstant on a locked pilot. It must not borrow historical v1 constants, feature values, thresholds, reviewer outcomes, routes, or identity truth.
