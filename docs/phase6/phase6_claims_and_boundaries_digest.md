# Phase 6 Claims and Boundaries Digest

Date: 2026-06-17

Purpose: provide the short claim boundary for Phase 6 and prevent older wording from leaking into current project framing.

## Current Allowed Framing

Use:

```text
PF-ERI is a patterned-felid evidence reliability and review-control framework tested in CzechLynx validation.
```

Do not use:

```text
PF-ERI is an identity-recognition model.
PF-ERI is a universal animal Re-ID quality score.
PF-ERI is validated for clouded leopard or marbled cat deployment.
```

## Main Claim From Phase 6

Phase 6 made the project deeper by changing the target from static scoring to controlled evidence reliability:

- visual evidence gating;
- identity-aware validation;
- empirical risk estimation;
- simulated open-set stress testing;
- review/defer/exclude policy control.

The strongest conceptual contribution is:

```text
how to decide when imperfect patterned-felid camera-trap evidence is reliable enough for Re-ID review.
```

## Required Wording Constraints

Always say:

- CzechLynx validation;
- simulated open-set, when referring to open-set results;
- empirical risk proxy, not deployment false-match probability;
- review-control or evidence utility, not identity assignment.

Never claim:

- true individual identification;
- field deployment readiness;
- population, movement, survival, abundance, or occupancy inference;
- universal thresholds;
- validated Mainland Clouded Leopard or Marbled Cat Re-ID;
- robust metric-learning improvement from Phase 6 alone.

## Current Relationship To Later Phases

Phase 6 is no longer the endpoint. It is the claim-boundary and validation foundation for later pairwise evidence work.

Phase 8 showed that simple hard filtering was insufficient for robust fixed-descriptor mAP gains. Phase 11 and Phase 12 therefore shift the goal toward pair-level evidence admissibility, descriptor-evidence conflict, and reliability-aware metric learning.

## Canonical Source Files

- `phase6_claims_and_risks_audit.md`
- `phase6_pf_eri_control_claim_boundaries.md`
- `phase6_species_scope_decision.md`
- `phase6_training_vs_calibration_decision.md`
- `phase6_publishable_algorithm_gap_analysis.md`
- superseded publishable-roadmap notes were merged into this digest and removed from the active tree.
