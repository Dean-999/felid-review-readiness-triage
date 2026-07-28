# Task 05: Feature Lineage and Fold-Train Preprocessing Freeze

Status: **COMPLETE — FROZEN PASS, NO PREDICTIVE MODEL FIT**
Date: 22 July 2026
Applies to: Workstream 05 / development Task 15D

## Why this freeze precedes model comparison

Missing-value handling, scaling, categorical encoding, unknown-level behavior, and feature ordering can materially change cross-validated performance. Freezing them after viewing candidate results would permit researcher degrees of freedom and make the P5-versus-P3 comparison vulnerable to outcome-guided preprocessing. Task 15D therefore turns the earlier conceptual preprocessing policy into executable, hashed behavior before Task 15E fits ridge or GAM models.

The freeze executable inspected the development file header and row count, verified the open-stage and fold gates, and used a synthetic canonical fixture to exercise transformations. It did not read a development label value or fit a predictive model. Calibration, deployment-confirmation, and mechanism-confirmation inputs remained unread.

## Frozen feature lineage

Ten source predictors are permitted:

- descriptor: MegaDescriptor percentile, DINOv2 percentile, and descriptor-support category;
- independent quality: native-pixel, sharpness, and exposure percentiles plus quality-failure and frozen-quality-stress states;
- pair evidence: local-match coverage and local-match measurement-failure state.

Diagnostic rank bands, raw similarities, descriptor disagreement, sampling cells, retrieval strata, evidence-state fields, labels, and adjudication metadata cannot enter a predictive design matrix. P3 uses descriptor plus independent quality. P5 uses the identical P3 blocks followed only by pair evidence.

## Frozen transformation behavior

Every inner-training fold and outer-training fold fits its own transformer.

For continuous variables:

1. coerce non-numeric and non-finite values to missing;
2. fail if the training feature is entirely missing;
3. impute with the training-fold median;
4. always emit an explicit missing indicator;
5. center by the imputed training-fold mean; and
6. divide by the imputed training-fold population standard deviation, using 1 only for a non-finite or effectively constant scale.

For categorical variables:

1. canonicalize booleans to `true` and `false`;
2. retain explicit `__MISSING__` and `__UNKNOWN__` columns;
3. drop only the lexicographically first observed ordinary training level as reference; and
4. map every unseen validation level to `__UNKNOWN__`.

A failed local measurement is represented by its explicit failure state and a missing coverage indicator. It is never imputed as zero evidence. Resampling and class rebalancing remain prohibited.

## Strict P3/P5 nesting result

The canonical fixture produced:

- P3: 20 transformed predictor columns;
- P5: 25 transformed predictor columns;
- P5 incremental columns: 5, all and only from pair evidence.

The five added columns are standardized local coverage, local-coverage missingness, local-failure `true`, local-failure missing, and local-failure unknown. The complete P3 column sequence is an exact prefix of the P5 sequence. This ordering invariant is tested, serialized, and hashed rather than inferred from feature names after fitting.

## Adversarial appraisal

### Strengths

- Statistics and category vocabularies are learned only from the relevant training fold.
- Missingness and measurement failure remain distinguishable from zero evidence.
- Unknown validation categories cannot silently become a reference level.
- P3 and P5 share one implementation, making the incremental evidence claim auditable.
- A serialization round trip reproduces identical transformed values and hashes.
- A synthetic fixture proves behavior without using outcome values.

### Critical boundary

This PASS establishes feature lineage and deterministic preprocessing only. It does not show that any feature predicts reviewability, that P5 improves Brier score, or that probabilities are calibrated.

### Important limitations

- Categorical vocabularies can differ across folds by design. The explicit unknown column prevents execution failure but does not create information about an absent rare level.
- Only two development rows have matcher failure. The resulting failure coefficient and subgroup performance will be weakly identified even though encoding is correct.
- Median imputation plus a missing indicator is transparent and stable, but it does not prove the missingness mechanism is ignorable.
- The exact reference level may differ between folds if a rare ordinary category is absent; ridge predictions remain valid, but coefficient labels must be interpreted together with each fold's serialized transformer.

## Artifacts

- Contract: `schemas/pferi_v2/feature_preprocessing_contract_v1.json`
- Reusable transformer: `scripts/pferi_v2_fold_preprocessor.py`
- Freeze builder: `scripts/freeze_pferi_v2_feature_preprocessing.py`
- Tests: `tests/test_freeze_pferi_v2_feature_preprocessing.py`
- Frozen package: `archive/pferi_v2/task_runs/model_development/2026-07-22_feature_preprocessing_freeze_v1/`

The package contains the frozen contract, ten-feature lineage table, canonical input fixture, fitted P3/P5 fixture transformers, transformed fixture outputs, audit, report, both source snapshots, and SHA256 manifest.

## Verification

- Python compilation: PASS.
- Focused tests: 7/7 PASS.
- Contract-to-model-registry lineage: PASS.
- P3/P5 strict transformed-column nesting: PASS.
- Serialization round trip: PASS.
- Unknown and missing category tests: PASS.
- All-missing continuous hard-failure test: PASS.
- Development label values read by freeze executable: false.
- Predictive model fitted: false.
- Generated checksum verification: 11/11 PASS.

## Next gate

Task 15E may now run the ridge primary line and restricted-GAM challenger with the frozen 5×4 component-disjoint folds. Square-root IPW is used for fitting as conditionally selected by Task 15B; Hájek IPW is used for validation. Inner folds select regularization by design-aware Brier and the one-standard-error preference for stronger shrinkage. Development inference remains descriptive: no development p-value may substitute for the one-shot confirmation rule.
