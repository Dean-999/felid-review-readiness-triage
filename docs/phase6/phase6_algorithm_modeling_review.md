# Phase 6 Algorithm and Modeling Digest

Date: 2026-06-17

Purpose: consolidate the Phase 6 modeling thread so readers do not need to start from dozens of intermediate planning files. This digest is an entry point, not a replacement for the original records.

## Core Modeling Decision

Phase 6 moved PF-ERI away from a single image-quality score and toward a staged evidence reliability control framework for patterned-felid Re-ID review.

The defensible model is:

```text
visual evidence admissibility
+ fixed descriptor support
+ empirical risk calibration
+ selective review/defer/exclude policy
```

The rejected model is:

```text
one hybrid score = identity confidence or safety probability
```

## What PF-ERI Represents

PF-ERI is the visual evidence gate. It estimates whether the visible evidence is usable for patterned-felid individual comparison. It is not an identity probability, not a descriptor, and not a field deployment decision.

The central insight from Phase 6 is that high visual evidence can increase useful signal and false-candidate risk at the same time. Clear pattern evidence helps true matches, but can also make different individuals look deceptively similar to a descriptor.

## Model Components

- `visual_only_eri`: primary visual evidence gate.
- fixed descriptor similarity: measurement support, not evidence reliability.
- `hybrid_eri`: secondary prioritization only.
- empirical risk proxy: high-similarity different-identity pair load under CzechLynx validation.
- policy action: review, cautious review, defer, or exclude.

## Mathematical Direction

The most durable mathematical ideas from Phase 6 are:

- risk-coverage tradeoff rather than absolute correctness;
- held-out identity validation rather than row-level random splitting;
- empirical calibration rather than universal probability claims;
- weakest-evidence logic for visual reliability;
- explicit separation between evidence quality and descriptor similarity.

These ideas directly feed the current Phase 12 pair-level roadmap.

## What Was Deprioritized

Training a new Re-ID identity model was rejected because it would move the project into a crowded descriptor-learning problem and overstate what the CzechLynx sample can support.

Allowed training remained limited to reliability-control models such as calibration, lightweight auditors, and later controlled pair-weighted metric learning with fixed embeddings.

## Current Use

Phase 6 should now be cited as the conceptual bridge from image-level review readiness to pair-level evidence admissibility. Its strongest continuing contribution is the boundary:

```text
PF-ERI is an evidence utility and risk-control signal, not an identity-recognition model.
```

## Canonical Source Files

- `phase6_pf_eri_control_reframing_summary.md`
- `phase6_pf_eri_v2_algorithm_definition.md`
- `phase6_training_vs_calibration_decision.md`
- `phase6_claims_and_risks_audit.md`
- `phase6_mathematical_model_options_review.md`
- `phase6_pf_eri_mathematical_modeling_review.md`
- `phase6_factor_to_risk_theory_review.md`
