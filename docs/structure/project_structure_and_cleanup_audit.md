# Project Structure and Cleanup Audit

Date: 2026-06-17

Purpose: document the final cleaned structure after aggressive consolidation. This project now keeps current implementation guidance visible and moves historical execution code out of the way.

## Current Project Center

```text
PF-ERI for Reliability-Aware Pairwise Evidence Learning in Patterned-Felid Re-ID
```

Active implementation target:

```text
Phase 12A: build a unified pair/candidate analysis table containing pair reliability, descriptor similarity, descriptor disagreement, reciprocal/margin support, conflict score, identity label, split metadata, and retrieval outcome flags.
```

## Authority Order

1. `README.md`
2. `PROJECT_RULES.md`
3. `docs/phase12/phase12_pairwise_evidence_learning_roadmap.md`
4. `docs/phase12/phase12_rq1_rq4_technical_implementation_plan.md`
5. `docs/phase11/phase11_pair_reliability_math_spec.md`
6. `docs/phase11/phase11_experiment_digest.md`
7. `docs/structure/csv_and_artifact_inventory.md`
8. `scripts/README.md`

## Cleaned Directory Roles

| Path | Role |
|---|---|
| `docs/` | Compact current documentation only. |
| `docs/phase6/` | Phase 6 digest layer only. |
| `docs/phase8/` | Phase 8 digest and active boundary result files. |
| `docs/phase9/` | Active no-training reranking result notes. |
| `docs/phase11/` | Pair reliability math, implementation summary, split diagnostic report, and experiment digest. |
| `docs/phase12/` | Active roadmap. |
| `docs/structure/` | Repository map and CSV/artifact inventory. |
| `scripts/` | Current top-level implementation scripts only. |
| `scripts/legacy/` | Historical phase scripts, old audits, annotation tools, packaging tools, and preview scripts. |
| `colab/` | Training/evaluation packages. Phase 11 is active; earlier folders are controls/history. |
| `data/` | Local raw/interim/label data. Not committed. |
| `outputs/` | Generated evidence, audits, packages, and tables. Not committed. |
| `sources/` | Literature/source search caches and synthesis files. |

## Documentation Reduction

The docs tree was reduced to current working documents and digests. Old phase notes, logs, mentor updates, next-step plans, and superseded detailed phase files were removed after their conclusions were captured in digest files.

Current key docs:

- `docs/README.md`
- `docs/phase6/phase6_index.md`
- `docs/phase6/phase6_algorithm_modeling_review.md`
- `docs/phase6/phase6_validation_results_digest.md`
- `docs/phase6/phase6_annotation_workflow_digest.md`
- `docs/phase6/phase6_claims_and_boundaries_digest.md`
- `docs/phase8/phase8_index.md`
- `docs/phase8/phase8_results_digest.md`
- `docs/phase8/phase8_claim_boundary_digest.md`
- `docs/phase9/phase9a_pf_eri_evidence_utility_model_direction_revision.md`
- `docs/phase9/phase9b_pf_eri_aware_fixed_descriptor_reranking_results.md`
- `docs/phase9/phase9b_r_pf_eri_reranking_refinement_results.md`
- `docs/phase11/phase11_pair_reliability_math_spec.md`
- `docs/phase11/phase11_pair_level_pf_eri_metric_learning_implementation.md`
- `docs/phase11/phase11c_split_level_diagnostic_report.md`
- `docs/phase11/phase11_experiment_digest.md`
- `docs/phase12/phase12_pairwise_evidence_learning_roadmap.md`
- `docs/phase12/phase12_rq1_rq4_technical_implementation_plan.md`
- `docs/structure/csv_and_artifact_inventory.md`

## Script Reduction

Top-level `scripts/` now contains current implementation and required dependency scripts only:

- `build_phase11_pair_level_pf_eri_table.py`
- `audit_phase11_pair_level_pf_eri_table.py`
- `build_phase11c_split_level_diagnostics.py`
- `audit_phase11c_split_level_diagnostics.py`
- `phase9b_pf_eri_aware_fixed_descriptor_reranking.py`
- `phase9b_r_pf_eri_reranking_refinement.py`
- `audit_phase9b_pf_eri_aware_fixed_descriptor_reranking.py`
- `audit_phase9b_r_pf_eri_reranking_refinement.py`
- `phase8_pf_eri_retrieval_control_v2_optimizer.py`

Everything else moved to `scripts/legacy/`.

Reason for retaining `phase8_pf_eri_retrieval_control_v2_optimizer.py`: Phase 9B imports helper functions from it.

## Data And Outputs

`data/` and `outputs/` were not aggressively deleted because they contain raw images, internal mappings, generated evidence tables, and audit outputs. The cleanup instead added:

- `data/README.md`
- `outputs/README.md`
- `docs/structure/csv_and_artifact_inventory.md`

## Cleanup Rule Going Forward

New work should not create one-off phase notes unless they will become active references. Prefer updating:

- `docs/phase12/phase12_pairwise_evidence_learning_roadmap.md`
- `docs/phase11/phase11_experiment_digest.md`
- `docs/structure/csv_and_artifact_inventory.md`
- `scripts/README.md`

If a script is not part of the current implementation path, put it under `scripts/legacy/`.
