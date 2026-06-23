# Phase 8 Results Digest

Date: 2026-06-17

Purpose: summarize Phase 8 retrieval-control results and keep the current interpretation separate from older provisional accuracy claims.

## Phase 8 Question

Phase 8 asked whether PF-ERI can improve fixed-descriptor retrieval behavior by filtering, selecting, or reranking evidence around MegaDescriptor and ResNet50 outputs.

## Main Result

The final Phase 8 interpretation is:

```text
PF-ERI reduced false-candidate review burden, but did not robustly improve fixed-descriptor mAP under held-out query-level evaluation.
```

This is not a failed endpoint. It is the result that motivated the current pair-level Phase 12 direction.

## Slice 3E Result

Slice 3E initially found conditional evidence that PF-ERI-selected policies could improve full-carrier fixed-descriptor retrieval metrics against random same-size controls.

That result is now treated as hypothesis-generating because the stricter Slice 3E-R held-out query-level evaluation did not support robust mAP improvement.

## Slice 3E-R Result

Slice 3E-R used deterministic query-level calibration/evaluation splits.

Key interpretation:

- selected policies reduced false-candidate burden in all held-out splits;
- selected policies beat random same-size controls on mAP in only a minority of splits;
- `candidate_f` remains the review-control reference;
- `v4_0636` remains an operational lower-burden/lower-retention refinement.

## Slice 3F Result

Slice 3F showed that false-candidate burden reduction can reduce simulated downstream identity-record contamination pressure under conservative assumptions.

This supports application value, not ecological estimation.

## What Phase 8 Contributes

Phase 8 contributes:

- strict random same-size control design;
- query-level calibration/evaluation logic;
- false-candidate burden as a meaningful workflow metric;
- evidence that hard filtering alone is too blunt;
- motivation for descriptor-evidence conflict and pair-level admissibility.

## Canonical Source Files

- `phase8_post_3e_r_interpretation_and_claim_revision.md`
- `phase8_slice3e_query_level_calibration_evaluation_results.md`
- `phase8_slice3e_reid_accuracy_evidence_selection_results.md`
- `phase8_slice3f_downstream_ecological_sensitivity_simulation_results.md`
