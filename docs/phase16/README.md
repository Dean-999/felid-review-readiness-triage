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

## Claim Boundary

Phase 16 may claim that PF-ERI evaluates admissible pair evidence and routes
candidate comparisons under risk constraints. It must not claim automatic
identity assignment, bobcat identity accuracy without verified labels,
urbanization causality, or a new Re-ID descriptor.
