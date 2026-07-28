# Task 02: Candidate Model-Route Registry Freeze

Status: **COMPLETE — FROZEN PASS, NO MODEL FIT**
Date: 22 July 2026
Applies to: Workstream 05 / development Task 15A

## Why 445 rows do not replace the larger pair reservoir

PF-ERI v2 retains several nested populations with different scientific functions. The immutable canonical reservoir contains 85,182 eligible unordered pairs. Zero-crossing image-role allocation assigns 3,000 images equally to development, calibration, and confirmation roles; retaining only pairs whose two endpoints share a role produces 28,295 within-role pairs: 9,445 development, 9,433 calibration, and 9,417 confirmation. This endpoint separation prevents the same image from leaking across the three scientific roles.

The formal one-time sampler selected 2,224 unique pairs from those role-specific frames. It assigned 445 to development, 445 to calibration, 889 to deployment confirmation, and 445 to mechanism confirmation. Therefore, 445 is the currently open labelled model-development sample, not the total candidate-pair count and not evidence that the larger reservoir was discarded. The other 1,779 formal pairs remain scientifically active but outcome-locked for their declared purposes.

## Frozen decision

The candidate registry contains 14 model roles:

- P0–P5 probability references and ridge-logistic primary route;
- S1–S5 prespecified nonlinear or mathematical sensitivity routes;
- E1–E3 exploratory performance-bound routes.

The only confirmation-eligible incremental comparison is P5 full ridge against P3 active-control ridge. Both use the same family and preprocessing policy; P5 adds only the `pair_evidence` block. That block contains frozen local-match coverage and its measurement-failure state. Descriptor disagreement, sampling cells, rank bands, evidence-state fields, and local-match percentiles are diagnostic or design variables and cannot enter the primary incremental block.

The registry also freezes a small ridge penalty grid, restricted-GAM and exploratory-model complexity budgets, component-disjoint nested cross-validation, design-aware Brier tuning, the absence of class rebalancing, and qualification-before-performance rules. GNNs, stacking, unrestricted deep tabular networks, broad boosting searches, row-random folds, SMOTE, and balanced class weights remain outside the primary route.

## Audit and information boundary

The freeze builder read the development file header and row count, verified its SHA256 and the stage-gate SHA256, and confirmed that calibration, deployment confirmation, and mechanism confirmation remain locked. It copied no outcome value, fitted no model, produced no prediction, and performed no calibration. The real development input contained exactly 445 rows and 32 columns. The freeze registered 14 model roles and recorded zero locked-stage label columns read.

The executable is `scripts/freeze_pferi_v2_model_route_registry.py`; its focused test suite is `tests/test_freeze_pferi_v2_model_route_registry.py`. The source candidate registry is `schemas/pferi_v2/model_route_candidate_registry_v1.json`. The immutable output package is stored under:

`archive/pferi_v2/task_runs/model_development/2026-07-22_model_route_freeze_v1/`

## Verification

- Python compilation: PASS.
- Focused tests: 10/10 PASS.
- Focused line coverage: 83%.
- Registry scientific-invariant audit: PASS.
- Development row count: 445.
- Registered models: 14.
- Confirmation-eligible models: P3 and P5 only.
- Locked-stage label columns read: 0.
- Model fitting performed: false.

## Next gate

Task 15B must build an outcome-free design-simulation harness using the frozen development covariate, missingness, sampling-weight, sampling-cell, and endpoint-graph structure. Synthetic outcomes must cover prespecified linear, nonlinear, null-increment, weak-increment, redundancy, interaction, separation, informative-failure, shared-image-effect, and calibration-shift mechanisms. The simulation may select a fitting-weight strategy and eliminate unstable candidate routes under a frozen minimax-regret rule; it must not estimate real development performance. Task 15C then constructs deterministic component-balanced nested folds before any registered development comparison is run.
