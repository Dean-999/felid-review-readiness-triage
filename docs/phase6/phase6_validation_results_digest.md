# Phase 6 Validation Results Digest

Date: 2026-06-17

Purpose: summarize the Phase 6 validation evidence without replacing the original result files.

## Validation Layers

Phase 6 added three major validation layers:

1. identity-held-out CzechLynx evaluation;
2. empirical band-level risk calibration;
3. simulated open-set CzechLynx stress testing.

These layers strengthened the project by revealing where PF-ERI is useful and where it must not be overclaimed.

## Identity-Holdout Result

Identity-held-out validation reduced row-level leakage risk by evaluating folds grouped by identity. MegaDescriptor remained the stronger fixed similarity signal, but the performance was moderate rather than decisive.

Key interpretation:

```text
PF-ERI can organize evidence reliability, but it does not make the system an identity recognizer.
```

High visual or hybrid bands tended to show stronger same-minus-different separation, but high hybrid bands could also concentrate high-similarity different-pair risk.

## Calibrated Risk Result

The calibration slice showed that raw ERI values should not be treated as calibrated risk probabilities. High PF-ERI or high hybrid bands are high-information bands, not automatically low-risk bands.

The important distinction is:

```text
risk load = high-risk retained pairs / original pair pool
retained-pair risk = high-risk retained pairs / retained pairs
```

A policy can reduce total risk load by retaining fewer pairs while still concentrating risk among retained candidates. Both quantities must be reported.

## Simulated Open-Set Result

The simulated open-set test held out CzechLynx identities as unknown identities and evaluated unknown-to-known candidate risk. This supported PF-ERI as a review/defer framework.

The strongest bounded result was that visual-only high evidence reduced forced-match proxy pressure while retaining more evidence than raw top-candidate ranking in the tested setting.

This remains:

```text
simulated open-set CzechLynx validation
```

It is not field open-set deployment.

## What Phase 6 Validates

Phase 6 supports:

- identity-aware validation as a necessary design rule;
- empirical risk proxies for review-control evaluation;
- PF-ERI as a visual evidence gate;
- review/defer/exclude policy logic;
- caution against hybrid-score safety claims.

## What Phase 6 Does Not Validate

Phase 6 does not validate:

- individual identification;
- universal thresholds;
- field deployment;
- Mainland Clouded Leopard or Marbled Cat Re-ID;
- population estimation;
- robust Re-ID accuracy improvement.

## Canonical Source Files

- `phase6_identity_holdout_results.md`
- `phase6_calibrated_risk_results.md`
- `phase6_open_set_simulation_results.md`
- `phase6_clustered_uncertainty_results.md`
- `phase6_open_set_policy_interpretation.md`
- `phase6_pf_eri_policy_refinement_results.md`
