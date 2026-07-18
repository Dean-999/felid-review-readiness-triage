# legacy-code16 PF-ERI 2.0 Strategy

Date: 2026-06-25

legacy-code16 keeps PF-ERI modeling at the center and adds data governance, candidate-pool expansion, model scoring, and selection safeguards.

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

legacy-code16 does not replace the PF-ERI main line. It adds:

1. dataset-foundation audit;
2. laterality-aware sampling and pair audit;
3. background/site leakage-pressure diagnostics;
4. strong-model benchmark preparation;
5. expanded high-confidence candidate pools;
6. legacy-code16e streaming model scoring;
7. legacy-code16f soft eligibility and constrained selection.

## Dataset Foundation Gate

The current 3000 x 4 image foundation must pass a conservative readiness audit
before it is treated as a clean training or clean comparison base. Use:

```text
python3 scripts/build_legacy-code16_dataset_foundation_audit.py
```

Primary outputs:

```text
outputs/legacy-code16/dataset_foundation_audit/legacy-code16_dataset_foundation_quadrant_summary.csv
outputs/legacy-code16/dataset_foundation_audit/legacy-code16_dataset_foundation_issue_detail.csv
outputs/legacy-code16/dataset_foundation_audit/legacy-code16_dataset_foundation_manual_audit_candidates.csv
outputs/legacy-code16/dataset_foundation_audit/legacy-code16_dataset_foundation_audit_report.md
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
outputs/legacy-code16/expanded_high_confidence_candidate_pool/
outputs/legacy-code16/legacy-code16e2_bobcat_20k_candidate_pool/
```

Scoring packages:

```text
outputs/legacy-code16/legacy-code16e_candidate_model_filter_colab_package/
outputs/legacy-code16/legacy-code16e_czechlynx_direct_zips/
```

Runner docs:

```text
docs/legacy-code16/legacy-code16e_colab_batch_execution.md
docs/legacy-code16/legacy-code16e_result_acceptance_criteria.md
```

Model-score signals:

```text
IQA + OpenCLIP + optional SuperAnimal pose
```

These are proxy signals, not identity evidence. Current runner `selection_eligible` is diagnostic only. legacy-code16f must recompute soft eligibility.

## Current Candidate Counts

```text
wild_czechlynx_high_confidence: 39760 CzechLynx candidates
urban_bobcat_high_confidence: 20000 FCF candidates after legacy-code16e2 expansion
```

Bobcat Tier 2 is same-source FCF species-level URL top-up, not clean Re-ID data. It must pass scoring, constrained selection, and audit before final high-confidence use.

## Active Plan

```text
docs/superpowers/plans/2026-06-23-legacy-code16-balanced-pf-eri-strategy.md
```

## Current Handoff

```text
legacy-code16i gap lock
-> legacy-code17a CzechLynx review-utility validation
-> Bobcat legacy-code16e score receipt and transfer-stress/review-readiness analysis
-> expert-audit or verified-label escalation before any stronger Bobcat claim
```

The earlier legacy-code16e -> legacy-code16f -> legacy-code16g/H path has been
executed for CzechLynx and remains documented below as historical evidence. The
active validation and modeling entry points are now:

```text
docs/modeling-validation/2026-07-08_final_modeling_freeze.md
docs/modeling-validation/pair-level-validation/README.md
docs/project-governance/structure/current_pipeline_manifest.md
```

## legacy-code16g Planning Boundary

legacy-code16g is the pair-level evidence contract and CzechLynx known-ID prototype,
not final calibrated model training:

```text
docs/superpowers/specs/2026-06-28-legacy-code16g-pair-level-contract-design.md
docs/superpowers/plans/2026-06-28-legacy-code16g-pair-level-contract.md
docs/legacy-code16/legacy-code16g_pair_level_contract.md
```

Formal review-router training should be treated as legacy-code16h after Bobcat
legacy-code16e/16F outputs and manual audit calibration are available.

## legacy-code16g Real CzechLynx Run

Run the real CzechLynx pair-table bridge after legacy-code16f selected images and
legacy-code15 descriptor candidate pairs are available:

```text
python3 scripts/run_legacy-code16g_real_czechlynx_pair_table.py
outputs/legacy-code16/legacy-code16g_czechlynx_real_pair_table/
```

This output is an audited pair-level table for legacy-code16h planning. It is not
final calibrated model training and does not affect the Bobcat identity claim
boundary.

## legacy-code16h Readiness Controls

Before training any calibrated review-router, run the CzechLynx readiness and
control-baseline gate:

```text
python3 scripts/build_legacy-code16h_czechlynx_readiness_controls.py
outputs/legacy-code16/legacy-code16h_czechlynx_readiness_controls/
```

This produces descriptor-only, quality-only, evidence-only, conflict-penalized,
diagnostic no-training, random same-size, risk-coverage, and leakage-sensitivity
controls. A `READY_FOR_DESIGN_NOT_TRAINING_CLAIM` gate means legacy-code16h may move
to grouped-split calibrated model design, but it still does not support a claim
that PF-ERI improves ranking over descriptor-only.

Run the first grouped-split calibrated router validation with:

```text
python3 scripts/build_legacy-code16h_czechlynx_calibrated_router.py
outputs/legacy-code16/legacy-code16h_czechlynx_calibrated_router/
```

Current interpretation: the calibrated router can be used as diagnostic
evidence if it reports discrimination signal, but it may not support a PF-ERI
ranking-improvement claim unless it clears the descriptor-only improvement gate
under leakage-excluded grouped splits.

## legacy-code16i Gap Rationale

The current gap rationale is:

```text
docs/legacy-code16/legacy-code16i_gap_rationale.md
```

This freezes the project-first claim boundary: PF-ERI is a post-retrieval
evidence reliability and review-routing layer. The next validation should
prioritize review utility, risk coverage, false-candidate burden, positive
retention, and expert-audit agreement rather than another attempt to beat
descriptor-only top-k ranking.

## legacy-code17a CzechLynx Review Utility

Run the first locked-gap review-utility validation with:

```text
python3 scripts/build_legacy-code17a_czechlynx_review_utility.py
outputs/legacy-code17/legacy-code17a_czechlynx_review_utility/
```

legacy-code17a uses leakage-excluded CzechLynx known-ID pairs to evaluate fixed review
budget, fixed positive-retention, abstention/risk coverage,
descriptor-evidence conflict enrichment, and proxy review actions.

Current interpretation: descriptor-only remains best on the k=10 ranking-like
snapshot, so legacy-code17a must not be used as a ranking-improvement claim. At 90%
positive retention, the diagnostic review-utility policy retains fewer false
pairs than descriptor-only, supporting the locked legacy-code16i claim that PF-ERI is
a review-utility layer rather than a descriptor replacement.

CzechLynx legacy-code16f constrained selection now has a first executable output:

```text
python3 scripts/build_legacy-code16f_czechlynx_constrained_selection.py
outputs/legacy-code16/legacy-code16f_czechlynx_constrained_selection/
```

This selects 3000 rows from the recalibrated balanced CzechLynx pool with an
identity-like path-group cap and audit outputs. It is not simple top-3000 and
does not finalize the set until manual audit calibration is complete.

## legacy-code16e Bobcat URL Batch Receipt

The completed Bobcat URL scoring batch has been received and analyzed:

```text
docs/legacy-code16/legacy-code16e_bobcat_url_batch_result_analysis.md
outputs/legacy-code16/legacy-code16e_bobcat_candidate_model_filter/legacy-code16e_bobcat_scores_00000_19999_merged.csv
outputs/legacy-code16/legacy-code16e_bobcat_score_analysis/
```

Current interpretation: the 20,000-row Bobcat batch is complete as
review-readiness transfer-stress evidence. It supports tier-separated routing
and manual-audit queue design. It still does not support Bobcat identity
accuracy or descriptor-replacement claims.

Publication-ready CzechLynx selected-set tables are generated with:

```text
python3 scripts/summarize_legacy-code16f_czechlynx_publication_selection.py
outputs/legacy-code16/legacy-code16f_czechlynx_publication_summary/
```

When Bobcat legacy-code16e scores finish, receive them with:

```text
python3 scripts/analyze_legacy-code16e_bobcat_scores.py --input path/to/bobcat_scores.csv
outputs/legacy-code16/legacy-code16e_bobcat_score_analysis/
```

The Bobcat analysis is a review-readiness transfer-stress analysis only. It
does not estimate Bobcat identity accuracy without verified identity labels or
an audited same/different pair set.

## Claim Boundary

legacy-code16 may claim that PF-ERI evaluates admissible pair evidence and routes
candidate comparisons under risk constraints. It must not claim automatic
identity assignment, bobcat identity accuracy without verified labels,
urbanization causality, or a new Re-ID descriptor.
