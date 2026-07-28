# Task 15G Exploratory Performance-Bound Result Freeze

Status: **COMPLETE - PERFORMANCE BOUND FROZEN, NO FINAL MODEL SELECTED**
Date: 23 July 2026
Applies to: Workstream 05 / Task 15G-C

Provenance note: this document records the exact local macOS reproduction completed before the external ModelScope delivery was returned. The later external export is the authoritative Task 15G delivery and is reconciled at `14_task15g_external_result_reconciliation_20260723.md`. The local freeze remains immutable as a cross-platform reproducibility record.

## Execution and integrity

The exact Task 15G package completed all 400 registered inner configuration-fold fits and all ten E1/E2 outer refits in Python 3.12. It produced 890 honest out-of-fold predictions covering 445 unique development pairs and 116 endpoint-image components. E3 produced zero predictions, as required by its predeclared incompatibility with the common fitting-weight contract. The run accessed no calibration, deployment-confirmation, or mechanism-confirmation outcome and selected no final model.

The validated export contains 53 members and has SHA256 `027cfb040a63c60ac0caa25cae1a5f5429ea11b037cf4754fb7f8572c16d5905`. All 52 internal checksums passed. Independent recalculation reproduced every E1/E2 overall and outer-fold Brier and log-loss value, all ten selected configurations, the 400-row inner-selection inventory, and every fold checkpoint hash. The immutable result freeze is stored at:

`archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_result_freeze/iterations/v1/`

## Performance-bound findings

E1 obtained a design-weighted Brier score of 0.132725379 and weighted log loss of 0.431542304. E2 obtained a lower overall Brier score of 0.128973466 and lower weighted log loss of 0.412680955. E1 nevertheless had the lower Brier score in outer folds 0, 3, and 4, while E2 was lower in folds 1 and 2. E1 also had higher overall weighted AUROC and AUPRC. E2 therefore improved the aggregate proper scores but did not dominate E1 across discrimination and outer folds.

The selected complexity was stable and conservative. E2 selected configuration `E2_C01` in all five outer folds: depth 2, learning rate 0.03, and L2 leaf penalty 10. E1 always selected learning rate 0.025 and two leaves, alternating only between 16 bins in three folds and 32 bins in two folds. This stability supports the conclusion that the bounded search operated as intended rather than exploiting a broad or unstable hyperparameter space.

Neither exploratory learner established a higher proper-score ceiling than the already frozen S3 and S4 mathematical sensitivities. E1's weighted Brier exceeded S3 by 0.009979983 and S4 by 0.009347428. E2's weighted Brier exceeded S3 by 0.006228070 and S4 by 0.005595516. E1 and E2 did outperform the frozen P5 weighted Brier descriptively, but E1, E2, and E3 remain `confirmation_eligible=false`; their development performance cannot promote them into the confirmation route.

The observed calibration metrics also caution against interpreting the nonlinear results as ready-to-deploy probabilities. E1 had a weighted calibration intercept of 0.5595 and slope of 0.4828, while E2 had an intercept of 0.4127 and slope of 0.6521. These values are descriptive development diagnostics and cannot be repaired by opening or tuning against the locked calibration stage before Task 15H establishes an eligible frozen model.

## Binding disposition

Task 15G is frozen as `FROZEN_COMPLETE_PERFORMANCE_BOUND_ONLY_NO_FINAL_SELECTION`. It must not be rerun to obtain a more favorable result, expanded with new exploratory configurations, or used to promote E1, E2, or E3. The performance-bound result is that bounded nonlinear learners improved over P5 but did not exceed the frozen S3/S4 proper scores or provide a confirmation-eligible route.

The next authorized task is Task 15H. It must apply qualification before performance across the complete frozen development record and create a validated `development_model_freeze_record.json`. Calibration remains locked until that record exists and explicitly authorizes the next stage.
