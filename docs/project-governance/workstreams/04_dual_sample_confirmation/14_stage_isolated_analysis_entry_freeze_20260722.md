# Stage-isolated analysis entry freeze

Status: **FROZEN PASS — DEVELOPMENT ONLY OPEN**
Date: 22 July 2026
Applies to: Workstream 04 Task 14

## Purpose

Task 14 restores the four analytical roles at the model-analysis boundary. The final outcome table necessarily contains all 2,224 accepted labels, but a model-development programme must not treat those rows as one interchangeable dataset. The stage-isolation builder therefore joins the frozen formal pairs to the outcome-free 28,295-pair automatic derivation frame, verifies exact pair, endpoint, role, and row-count agreement, and then emits a development-open table separately from the three locked-stage feature tables. It does not fit a model, select a transformation, calibrate a probability, choose a route threshold, or calculate a confirmation metric.

The join used `final_adjudicated_outcomes.csv` from Task 13 and `restricted_outcome_free_master_derivation_frame.csv` from the accepted post-allocation derivation. The source outcome audit and study-owner disposition both authorized model analysis, and all source checksums passed before the join. Every formal pair resolved to exactly one outcome-free automatic feature row. The observed stage totals were 445 development, 445 calibration, 889 deployment confirmation, and 445 mechanism confirmation, matching the frozen formal sampling contract.

## Open development input

The file `development_open/development_modeling_input.csv` contains exactly 445 development rows. It includes the frozen descriptor representation, descriptor support and rank-band fields, automatic endpoint-quality measurements and failure states, local-match coverage and failure state, endpoint identifiers, sampling metadata, and the accepted human endpoint. This is the only table currently permitted for feature transformation, model-family comparison, regularization selection, cross-validation, and development error analysis. The table does not contain calibration or confirmation rows.

The development stage may compare the descriptor-only baseline, independent-quality model, active control, and full automatic-evidence model under a common probabilistic modelling framework. It may also determine prespecified transformations, interaction handling, missingness encoding, and regularization. Every such choice must be made within development and recorded in a development model freeze before calibration outcomes are joined.

## Locked stages and commitments

The files `calibration_features.csv`, `deployment_confirmation_features.csv`, and `mechanism_confirmation_features.csv` are stored under `outcome_free_locked_features/`. They contain 445, 889, and 445 rows, respectively, and expose the frozen automatic predictors needed to generate later predictions. None contains `final_three_category_label`, `review_ready_label`, `not_ready_or_uncertain_label`, a reviewer decision, an adjudication decision, or any other human outcome column. The stage-isolation audit reports zero locked-stage label columns exposed.

The file `sealed_outcome_commitments.json` records a deterministic SHA-256 commitment for each locked outcome stage without publishing its label values in the analysis-entry package. Each commitment hashes the sorted canonical pair identifier, final three-category label, binary labels, and final-label source. These commitments allow a later validator to establish that calibration and confirmation outcomes were not replaced after the model or prediction files were frozen.

Calibration remains locked until `development_model_freeze_record.json` exists and passes validation. Deployment confirmation and mechanism confirmation remain locked until the development model, calibration policy, confirmation analysis code, and both active-control and full-model prediction files are frozen. Mechanism rows may then support prespecified failure and heterogeneity analyses, but they may not be pooled into the primary deployment Brier estimand.

## Exposure accounting and enforcement boundary

Aggregate stage label counts had already been calculated during endpoint validation before Task 14. The exposure register preserves that fact rather than implying that the confirmation outcomes had never been summarized. Task 14 did not compute any locked-stage feature–outcome association, fit, score, calibration curve, or subgroup result. Subsequent development code must use the development-open file as its only label-bearing input and must not read the source final-outcome table.

This control is an auditable analytical gate rather than an operating-system confidentiality mechanism. The immutable source outcome table remains part of the restricted project archive, while the ordinary development entry point contains only development outcomes. The stage contract, explicit prerequisites, source hashes, overwrite refusal, and tests make accidental or undocumented cross-stage use detectable. They do not replace accountable adherence to the declared information roles.

## Frozen artifacts and verification

The Task 14 package is stored at `archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1/`. It contains the development-open table, three locked outcome-free feature tables, the stage gate contract, sealed outcome commitments, an exposure register, a stage-isolation audit, and a checksum manifest. The audit status is `PASS`, the current open stage is `development`, and model training is explicitly prohibited on calibration, deployment-confirmation, and mechanism-confirmation rows.

The package was created by `scripts/build_v2_stage_isolated_analysis_inputs.py`. Focused tests cover successful development-only exposure, absence of outcome columns in all locked feature tables, rejection of an incomplete feature join, rejection of an unauthorized source disposition, source checksum verification, exact stage counts, and overwrite refusal. The next authorized task is Workstream 04 Task 15, which develops and selects the probabilistic model using only the 445-row development-open table.
