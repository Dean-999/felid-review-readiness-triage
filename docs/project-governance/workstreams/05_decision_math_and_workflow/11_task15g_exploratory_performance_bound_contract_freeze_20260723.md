# Task 15G Exploratory Performance-Bound Contract Freeze

Status: **COMPLETE - CONTRACT FROZEN, NO TASK 15G MODEL FIT**
Date: 23 July 2026
Applies to: Workstream 05 / Task 15G-A

## Scientific purpose

Task 15G asks a deliberately limited question: how much development proper-score performance can tightly bounded nonlinear tabular learners attain when they receive the same frozen information and are evaluated under the same endpoint-component-disjoint design as the earlier candidate routes? It does not ask which exploratory learner should become the confirmation model. E1, E2, and E3 remain `confirmation_eligible=false`, and Task 15G cannot select the final development route or authorize calibration.

The common design remains unchanged. Only the 445 development pairs and their permitted `review_ready_label` outcomes may be used. Preprocessing is fitted separately inside every training fold. Model fitting uses square-root inverse first-order inclusion-probability weights normalized within the training set, while validation and reporting use full inverse-probability weights with Hajek normalization. The five frozen outer folds and the conditional four-fold inner assignments remain endpoint-component-disjoint. Class weights, over-sampling, under-sampling, SMOTE, row-random folds, and outcome-guided grid expansion are prohibited.

## Frozen exploratory routes

E1 uses `interpret==0.7.8` and `ExplainableBoostingClassifier`. Automatic interaction search is disabled, and no interaction is introduced. Its eight configurations cross learning rates 0.025 and 0.05, maximum bin counts 16 and 32, and maximum leaf counts 2 and 3. Internal random validation and early stopping are disabled so that model selection occurs only through the frozen component-disjoint inner folds.

E2 uses `catboost==1.2.10` and a deterministic symmetric-tree classifier. Its twelve configurations cross depths 2, 3, and 4; learning rates 0.03 and 0.08; and L2 leaf penalties 3 and 10. Each fit uses 500 boosting iterations without bootstrap sampling, random feature-strength perturbation, class balancing, or early stopping. The maximum depth and total configuration count therefore remain within the candidate-registry limits.

For E1 and E2 separately, the selected configuration within each outer training set is the one with the smallest mean design-weighted Brier score across the four frozen inner folds. Exact or numerical ties within `1e-12` are resolved by a prespecified preference for the simpler or more strongly regularized configuration. The selected configuration is then fitted once on the complete outer training set and must produce one honest out-of-fold probability for every development pair. A failed outer fold invalidates that model's performance-bound estimate; the fold cannot be omitted, replaced, or imputed.

E3 is pinned to `tabpfn==8.0.7` and the public v2 classifier checkpoint `tabpfn-v2-classifier-finetuned-zk73skhh.ckpt` from repository revision `f851f2a3c941544733b712d8c0f96dfae9b28862`. The 29,009,539-byte checkpoint has SHA256 `cf8c519c01eaf1613ee91239006d57b1c806ff5f23ac1aeb1315ba1015210e49`. The frozen classifier exposes `fit(self, X, y)` and has no native `sample_weight` argument. E3 is consequently predeclared ineligible under the common fitting-weight contract and must emit no prediction. Row duplication, weighted resampling, integer replication, fine-tuning, or switching packages after E1 or E2 results are observed would create an unregistered analysis and are forbidden.

## Audit result

The freeze builder verified the SHA256 of the development input, outer and nested fold assignments, preprocessing contract and executable, candidate registry, and Task 15F disposition. It confirmed 445 unique development pairs, 116 endpoint-image components, five outer folds, and 1,780 nested-fold assignments. Task 15F retained the status `FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_SELECTION` and explicitly authorized the exploratory performance-bound benchmark as the next task. The builder fitted no model, calculated no Task 15G performance, selected no final route, and accessed no calibration, deployment-confirmation, or mechanism-confirmation outcome.

The executable is `scripts/freeze_task15g_exploratory_performance_bound_contract.py`, and its focused tests are in `tests/test_freeze_task15g_exploratory_performance_bound_contract.py`. The source contract is `schemas/pferi_v2/task15g_exploratory_performance_bound_contract_v1.json`. The immutable local freeze is stored at:

`archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_contract_freeze_v1/`

The frozen contract SHA256 is `b736344bf0c3dbf453c95acb4a5898672ff3c775d5016df7cfd61a1af6b2dc04`.

## Next gate

The next authorized action is Task 15G-B: build an exact, checksum-verified execution package from this contract and run the validated E1/E2 benchmark without changing folds, preprocessing, weights, grids, or eligibility. After those results are independently frozen, Task 15H must apply qualification before performance and create a validated `development_model_freeze_record.json`. Calibration remains locked until that record exists and passes validation.
