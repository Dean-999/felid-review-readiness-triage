# Task 15G External Result Reconciliation

Status: **COMPLETE - EXTERNAL DELIVERY AUTHORITATIVE, CONCLUSION REPRODUCED**
Date: 23 July 2026
Applies to: Workstream 05 / Task 15G external delivery and statistical interpretation

## Delivery integrity and storage

The returned ModelScope export has SHA256 `c1c66309b8fd8bb6503e49b6cd7429305ddd842d6744e3264d86c52fe88ddd3a`, exactly matching the supplied SHA256 declaration and run summary. The summary binds the run to package SHA256 `6c5702970bc2ce86ae1b52f90a71ffc27e1311543e52e4b4be50fc0d774fa0e9`, which is the frozen Task 15G execution package. The Linux run used Python 3.12.13, `interpret==0.7.8`, `catboost==1.2.10`, `numpy==2.3.3`, and `pandas==2.3.3`.

The export contains 53 members. All 52 internal SHA256 checks passed, as did the global validation audit, ten fold/model checkpoint audits, contract hash, package manifest hash, 890-row prediction inventory, 400-row inner-selection inventory, and ten selected configurations. It covers 445 unique development pairs and 116 endpoint-image components. E3 produced zero predictions, the run accessed no locked-stage outcome, and no final model was selected.

The authoritative external delivery, supplied SHA declaration, run summary, extracted results, independent recalculation, freeze audit, and scientific disposition are copied into:

`archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_result_freeze/current/`

The prior local reproduction is retained at `iterations/v1/`. It is not the authoritative external delivery.

## Statistical results

E1 obtained a design-weighted Brier score of 0.132686049 and weighted log loss of 0.431439855. E2 obtained a Brier score of 0.128973466 and log loss of 0.412680955. The raw weighted Brier difference, E1 minus E2, was 0.003712583, corresponding to a 2.798% relative reduction for E2. E1 nevertheless had higher weighted AUROC, 0.7573 versus 0.7233, and higher weighted AUPRC, 0.9372 versus 0.9270. E2 therefore improved aggregate proper scores but did not dominate across discrimination metrics.

The aggregate E2 Brier advantage was not stable across the five outer folds. E1 had lower Brier in folds 0, 3, and 4; E2 was lower in folds 1 and 2. Fold 2 alone contributed 223.5% of the net E1-minus-E2 difference because E1's advantages in the other folds offset much of that gain. E1 also had lower pairwise Brier loss for 296 of 445 pairs and lower component-level weighted loss in 73 of 116 endpoint components. E2's overall advantage is therefore driven by the magnitude and design weights of its wins, especially in fold 2, rather than broad pairwise, component-wise, or fold-wise dominance.

The configuration results were stable. E2 selected the same shallow `E2_C01` configuration in all five folds. E1 selected `E1_C00` in three folds and `E1_C02` in two; both use learning rate 0.025 and two leaves, differing only in the bin limit. All 400 inner configuration-fold fits passed.

E1 and E2 improved weighted Brier relative to P5 by 5.366% and 8.014%, respectively. Neither exceeded the already frozen S3/S4 proper scores. E1's Brier was 0.009940653 above S3 and 0.009308099 above S4; E2 was 0.006228070 above S3 and 0.005595516 above S4. The exploratory benchmark therefore did not identify a higher proper-score ceiling than the mathematical sensitivities.

Calibration remained inadequate for direct probability use. E1 had a weighted calibration intercept of 0.5594 and slope of 0.4830. E2 had an intercept of 0.4127 and slope of 0.6521. E2 was closer to the ideal intercept zero and slope one, but neither development result authorizes calibration tuning or deployment.

## Cross-platform sensitivity

The external Linux and local macOS runs used identical package manifests, contracts, inputs, folds, versions, and configuration selections. E2 probabilities agreed to machine precision, with maximum absolute difference below `1.8e-15`. E1 showed small platform-level numerical variation: mean absolute probability difference 0.000240, maximum 0.002628, and 24 of 445 rows above 0.001. The external E1 weighted Brier was 0.000039 lower than the local value. No selected configuration, fold win direction, model ranking, eligibility status, or scientific conclusion changed.

This constitutes a successful cross-platform sensitivity result rather than exact bitwise reproduction for E1. The externally returned values are authoritative for reporting.

## Inferential boundary

No post hoc p-value, row-level paired t-test, or Wilcoxon test was added. Task 15G was preregistered as descriptive development model selection and stability analysis. The observations carry unequal design weights and share endpoint-image components, so ordinary row-level tests would violate independence and introduce an outcome-guided decision rule. The appropriate registered evidence consists of the design-weighted proper-score differences, outer-fold distribution, component direction counts, configuration stability, calibration diagnostics, and cross-platform sensitivity.

The reproducible reconciliation record is stored at:

`archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_external_reconciliation_v1/`

## Binding disposition

The external result confirms `FROZEN_COMPLETE_PERFORMANCE_BOUND_ONLY_NO_FINAL_SELECTION`. E1, E2, and E3 remain `confirmation_eligible=false`. The Task 15G benchmark must not be rerun, expanded, or used to promote an exploratory route. Task 15H remains the only authorized next task and must produce a validated `development_model_freeze_record.json` before calibration can open.
