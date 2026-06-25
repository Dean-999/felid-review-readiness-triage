# Phase 16 Balanced PF-ERI Strategy Plan

Status: active compact plan.

## Goal

Build PF-ERI 2.0 as a competition-ready, paper-defensible, tool-oriented evidence reliability workflow.

Core chain:

```text
strong descriptor retrieval
-> PF-ERI pair-level admissibility
-> descriptor-evidence conflict
-> calibrated review routing
-> risk-controlled evaluation
-> wild-to-urban transfer stress
```

## Current Boundaries

- CzechLynx is known-ID validation carrier.
- Bobcat is same-genus urban/peri-urban review-readiness stress unless verified individual labels or audited same/different pair labels exist.
- PF-ERI is not a descriptor, not identity assignment, not population estimation.
- Phase 16E scoring does not freeze final 3000 and does not simple top-3000.
- OpenCLIP and SuperAnimal are proxy signal sources, not final evidence judges.

## Current Assets

```text
docs/phase16/README.md
docs/phase16/phase16e_colab_batch_execution.md
docs/phase16/phase16e_result_acceptance_criteria.md
outputs/phase16/expanded_high_confidence_candidate_pool/
outputs/phase16/phase16e_candidate_model_filter_colab_package/
outputs/phase16/phase16e_czechlynx_direct_zips/
outputs/phase16/phase16e2_bobcat_20k_candidate_pool/
```

## Completed Phase 16 Tasks

- Dataset foundation audit.
- Laterality audit table and pair audit.
- Leakage-pressure diagnostic.
- Strong-model benchmark package.
- Expanded high-confidence candidate pool.
- Phase 16E Colab streaming runner.
- CzechLynx direct split zips.
- Bobcat 20k candidate pool expansion.
- Phase 16E result acceptance criteria.

## Next Tasks

1. Wait for full Phase 16E model scoring results.
2. Apply `docs/phase16/phase16e_result_acceptance_criteria.md`.
3. Diagnose hard `selection_eligible` failure; do not use it as final decision.
4. Build Phase 16F soft eligibility recalculation.
5. Run constrained selection:

```text
image_load_success
+ IQA/crop quality
+ animal size / geometry when available
+ OpenCLIP side-view probability as soft evidence
- OpenCLIP uncertain/front/rear/partial penalty
+ optional pose completeness proxy
+ duplicate control
+ laterality balance
+ source-tier tracking
+ manual audit calibration
```

6. Produce high-confidence shortlist for manual audit.
7. Freeze final 3000 only after audit-calibrated constrained selection.

## Required Controls

- Descriptor-only control.
- Quality-only control.
- Random same-size control.
- Source-tier report for Bobcat Tier 1 vs Tier 2.
- Laterality known/unknown report.
- Duplicate and near-duplicate report.
- Manual audit sample from high, borderline, uncertain, Tier 2, and rejected-loaded buckets.

## Claim Boundary

Allowed:

```text
PF-ERI estimates admissible evidence and routes candidate comparisons under risk constraints.
```

Not allowed:

- automatic identity recognition;
- bobcat identity accuracy without verified labels;
- urbanization causality;
- universal threshold;
- new Re-ID descriptor;
- final 3000 selection before Phase 16F and manual audit.
