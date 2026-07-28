# Model-route horizontal–vertical literature review

Status: **COMPLETE — DESIGN RECOMMENDATION, NOT MODEL FREEZE**
Date: 22 July 2026
Applies to: Workstream 05 Task 01

## Purpose

This task determines which probabilistic model families are scientifically defensible before any PF-ERI v2 development fitting is treated as a model-selection result. It compares regularized logistic regression, restricted GAMs, Bayesian logistic models, Firth correction, EBM, tree ensembles, TabPFN, GNNs, and stacking against the frozen PF-ERI objective and the actual 445-row development constraints.

The task used only the label-bearing development table at `archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1/development_open/development_modeling_input.csv`. It did not read or join calibration, deployment-confirmation, or mechanism-confirmation outcomes. It did not fit a candidate model, select a regularization value, calibrate a probability, choose a route threshold, generate confirmation predictions, or alter the scientific algorithm.

## Decision recommendation

The confirmatory primary family should remain a common-preprocessing L2/ridge logistic probability model. The active control and full model must be strictly nested, differing only by the frozen automatic pair-evidence block. A restricted penalized logistic GAM is the prespecified nonlinear secondary. Weak-prior Bayesian logistic, crossed-image random-effects, and Firth/FLIC are sensitivity models. EBM, shallow CatBoost, and fixed-version TabPFN are exploratory performance-bound models. GNNs, stacking, unrestricted deep tabular models, broad boosting searches, and class-rebalancing methods are excluded from the primary route.

This recommendation does not assert that ridge logistic will obtain the lowest observed development or confirmation Brier score. It asserts that ridge logistic provides the best confirmatory balance of small-sample stability, calibrated-probability intent, interpretability, strict active-control nesting, and auditability under the frozen protocol.

## Design findings that must shape implementation

- The development table has 445 pairs, 373 review-ready outcomes, and 72 not-ready-or-uncertain outcomes.
- The selected-pair graph has 551 images, 116 connected components, maximum image degree 6, and 381 pairs touching at least one repeated image.
- Strict component-disjoint cross-validation is feasible and must replace random row-wise folds.
- The inverse inclusion weights span a ratio of approximately 69.9 and have a Kish effective sample size of approximately 239.3; fitting-weight strategy must be resolved by an outcome-free design simulation rather than intuition.
- SMOTE, over/under-sampling, and balanced class weights are prohibited because the project requires natural-queue probabilities.
- The primary evidence block must remain minimal. Cross-descriptor disagreement remains diagnostic and cannot be promoted into the primary full model.

## Deliverables

The complete Chinese-language review, verified source list, mathematical recommendations, model matrix, and evidence-to-decision diagram are stored at:

`archive/pferi_v2/task_runs/model_route_review/2026-07-22_hv_literature_model_selection_v1/`

The figures are generated reproducibly by:

`scripts/build_pferi_v2_model_route_review_figures.py`

## Next gate

The next task is not a full development fit. It must first freeze a candidate-model registry, construct an outcome-free simulation harness using the frozen covariate/weight/graph structure, and build deterministic component-balanced nested folds. Only after those gates pass may the real development outcomes be used for the registered model comparison and final `development_model_freeze_record.json`.
