# Phase 16 PF-ERI 2.0 Strategy

Date: 2026-06-25

Phase 16 keeps PF-ERI modeling at the center and adds data governance, candidate-pool expansion, model scoring, and selection safeguards.

## Core Modeling Line

```text
strong descriptor retrieval
-> PF-ERI pair-level evidence utility
-> descriptor-evidence conflict
-> calibrated review routing
-> risk-controlled evaluation
-> wild-to-urban transfer stress
```

## Additions

Phase 16 does not replace the PF-ERI main line. It adds:

1. dataset-foundation audit;
2. laterality-aware sampling and pair audit;
3. background/site leakage-pressure diagnostics;
4. strong-model benchmark preparation;
5. expanded high-confidence candidate pools;
6. Phase 16E streaming model scoring;
7. Phase 16F soft eligibility and constrained selection.

## Dataset Foundation Gate

The current 3000 x 4 image foundation must pass a conservative readiness audit
before it is treated as a clean training or clean comparison base. Use:

```text
python3 scripts/build_phase16_dataset_foundation_audit.py
```

Primary outputs:

```text
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_quadrant_summary.csv
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_issue_detail.csv
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_manual_audit_candidates.csv
outputs/phase16/dataset_foundation_audit/phase16_dataset_foundation_audit_report.md
```

Interpretation rule:

```text
If high-confidence quadrants do not reach the 90% readiness target, do not
weaken the definition of high-confidence evidence. First run targeted manual
audit, then rebuild or top up only the failing evidence categories.
```

## Candidate Pools And Scoring

Expanded same-domain pools:

```text
outputs/phase16/expanded_high_confidence_candidate_pool/
outputs/phase16/phase16e2_bobcat_20k_candidate_pool/
```

Scoring packages:

```text
outputs/phase16/phase16e_candidate_model_filter_colab_package/
outputs/phase16/phase16e_czechlynx_direct_zips/
```

Runner docs:

```text
docs/phase16/phase16e_colab_batch_execution.md
docs/phase16/phase16e_result_acceptance_criteria.md
```

Model-score signals:

```text
IQA + OpenCLIP + optional SuperAnimal pose
```

These are proxy signals, not identity evidence. Current runner `selection_eligible` is diagnostic only. Phase 16F must recompute soft eligibility.

## Current Candidate Counts

```text
wild_czechlynx_high_confidence: 39760 CzechLynx candidates
urban_bobcat_high_confidence: 20000 FCF candidates after Phase 16E2 expansion
```

Bobcat Tier 2 is same-source FCF species-level URL top-up, not clean Re-ID data. It must pass scoring, constrained selection, and audit before final high-confidence use.

## Active Plan

```text
docs/superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md
```

## Next Step

```text
Phase 16E scores
-> result acceptance
-> Phase 16F soft eligibility
-> constrained selection
-> manual audit
-> final 3000 only after calibration
```

## Phase 16G Planning Boundary

Phase16G / Phase 16G is planned as a pair-level evidence contract and CzechLynx known-ID
prototype, not final calibrated model training:

```text
docs/superpowers/specs/2026-06-28-phase16g-pair-level-contract-design.md
docs/superpowers/plans/2026-06-28-phase16g-pair-level-contract.md
docs/phase16/phase16g_pair_level_contract.md
```

Formal review-router training should be treated as Phase 16H after Bobcat
Phase 16E/16F outputs and manual audit calibration are available.

## Phase16G Real CzechLynx Run

Run the real CzechLynx pair-table bridge after Phase16F selected images and
Phase15 descriptor candidate pairs are available:

```text
python3 scripts/run_phase16g_real_czechlynx_pair_table.py
outputs/phase16/phase16g_czechlynx_real_pair_table/
```

This output is an audited pair-level table for Phase16H planning. It is not
final calibrated model training and does not affect the Bobcat identity claim
boundary.

## Phase16H Readiness Controls

Before training any calibrated review-router, run the CzechLynx readiness and
control-baseline gate:

```text
python3 scripts/build_phase16h_czechlynx_readiness_controls.py
outputs/phase16/phase16h_czechlynx_readiness_controls/
```

This produces descriptor-only, quality-only, evidence-only, conflict-penalized,
diagnostic no-training, random same-size, risk-coverage, and leakage-sensitivity
controls. A `READY_FOR_DESIGN_NOT_TRAINING_CLAIM` gate means Phase16H may move
to grouped-split calibrated model design, but it still does not support a claim
that PF-ERI improves ranking over descriptor-only.

Run the first grouped-split calibrated router validation with:

```text
python3 scripts/build_phase16h_czechlynx_calibrated_router.py
outputs/phase16/phase16h_czechlynx_calibrated_router/
```

Current interpretation: the calibrated router can be used as diagnostic
evidence if it reports discrimination signal, but it may not support a PF-ERI
ranking-improvement claim unless it clears the descriptor-only improvement gate
under leakage-excluded grouped splits.

## Phase16I Gap Rationale

The current gap rationale is:

```text
docs/phase16/phase16i_gap_rationale.md
```

This freezes the project-first claim boundary: PF-ERI is a post-retrieval
evidence reliability and review-routing layer. The next validation should
prioritize review utility, risk coverage, false-candidate burden, positive
retention, and expert-audit agreement rather than another attempt to beat
descriptor-only top-k ranking.

## Phase17A CzechLynx Review Utility

Run the first locked-gap review-utility validation with:

```text
python3 scripts/build_phase17a_czechlynx_review_utility.py
outputs/phase17/phase17a_czechlynx_review_utility/
```

Phase17A uses leakage-excluded CzechLynx known-ID pairs to evaluate fixed review
budget, fixed positive-retention, abstention/risk coverage,
descriptor-evidence conflict enrichment, and proxy review actions.

Current interpretation: descriptor-only remains best on the k=10 ranking-like
snapshot, so Phase17A must not be used as a ranking-improvement claim. At 90%
positive retention, the diagnostic review-utility policy retains fewer false
pairs than descriptor-only, supporting the locked Phase16I claim that PF-ERI is
a review-utility layer rather than a descriptor replacement.

CzechLynx Phase 16F constrained selection now has a first executable output:

```text
python3 scripts/build_phase16f_czechlynx_constrained_selection.py
outputs/phase16/phase16f_czechlynx_constrained_selection/
```

This selects 3000 rows from the recalibrated balanced CzechLynx pool with an
identity-like path-group cap and audit outputs. It is not simple top-3000 and
does not finalize the set until manual audit calibration is complete.

Publication-ready CzechLynx selected-set tables are generated with:

```text
python3 scripts/summarize_phase16f_czechlynx_publication_selection.py
outputs/phase16/phase16f_czechlynx_publication_summary/
```

When Bobcat Phase 16E scores finish, receive them with:

```text
python3 scripts/analyze_phase16e_bobcat_scores.py --input path/to/bobcat_scores.csv
outputs/phase16/phase16e_bobcat_score_analysis/
```

The Bobcat analysis is a review-readiness transfer-stress analysis only. It
does not estimate Bobcat identity accuracy without verified identity labels or
an audited same/different pair set.

## Claim Boundary

Phase 16 may claim that PF-ERI evaluates admissible pair evidence and routes
candidate comparisons under risk constraints. It must not claim automatic
identity assignment, bobcat identity accuracy without verified labels,
urbanization causality, or a new Re-ID descriptor.
