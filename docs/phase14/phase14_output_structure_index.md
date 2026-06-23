# Phase 14 Output Structure Index

This document explains the current `outputs/phase14/` structure after cleanup.

## Core Scientific Chain

| Folder | Role | Keep? |
|---|---|---|
| `phase14_final_2x2_working_labels/` | Final 3000 x 4 membership and labels | yes |
| `phase14_algorithm_inputs/` | Unified image evidence and pair comparability inputs | yes |
| `phase14_descriptor_embeddings/` | Final complete 12000-image MegaDescriptor embeddings | yes |
| `phase14_descriptor_conflict/` | Descriptor similarity and descriptor-evidence conflict table | yes |
| `phase14_statistical_analysis/` | Current statistical tables and report | yes |
| `phase14_risk_controlled_review_policy/` | Candidate-pair risk-control policy, random controls, Pareto diagnostics | yes |

Canonical flow:

```text
working labels -> algorithm inputs -> descriptor embeddings -> descriptor conflict -> statistical analysis -> risk-controlled review policy
```

## Provenance / Reproducibility

| Folder | Role |
|---|---|
| `phase14_colab_megadetector_final_selection/` | high-confidence detector final-selection provenance |
| `phase14_colab_megadetector_low_evidence_final_selection/` | low-evidence detector final-selection provenance |
| `phase14_czechlynx_high_topup/` | CzechLynx high-confidence top-up detector returns |
| `phase14_low_evidence_topup_colab_package/` | low-evidence top-up manifests/package provenance |
| `phase14_detector_first_admission/` | detector-first admission diagnostics |
| `phase14_disk_cleanup/` | cleanup audit and protected keep-list |

## Historical / Diagnostic

These are not current endpoint outputs but preserve design history and
diagnostic context:

- `phase14_2x2_evidence_sets/`
- `phase14_strict_2x2_evidence_sets/`
- `phase14_megadetector_evidence_gate/`
- `phase14_megadetector_evidence_gate_300x2/`
- `phase14_megadetector_evidence_gate_mps_test/`
- `phase14_bobcat_high_confidence_inventory/`
- `phase14_lila_md_prefilter/`
- `phase14_expanded_high_confidence_candidates/`

## Regenerable Payloads Removed

The cleanup removed:

- large copied image payloads and zip chunks from `phase14_descriptor_embedding_cloud_package/`;
- 80 non-final temporary FCF bobcat candidate images;
- one duplicate complete embedding CSV;
- one incomplete 11995-row intermediate embedding CSV.

The cleanup did not remove:

- final 3000 x 4 image references;
- final working labels;
- CSV/JSON metadata/audit records;
- final 12000-row embedding table;
- descriptor-conflict or statistical-analysis outputs.

## Current Claim Boundary

Bobcat is identity-unknown in Phase 14. It can support urban/peri-urban
comparability shift, review-burden, conflict-pressure, and stress-test claims.
It cannot support true false-match accuracy or individual identity validation.

CzechLynx known-ID pairs are the validation substrate for positive retention,
false-candidate burden, and risk-coverage analysis.
