# Task15K Independent Calibration Design and ModelScope Control Package

Status: **COMPLETE - OUTCOME-FREE CALIBRATION CANDIDATE AND MEASUREMENT PACKAGE FROZEN**

Task15J qualified and froze the independent Task15I P5 development model, retained P3 as its active control, and authorized calibration preparation only. Task15K resolves the calibration-input compatibility question before any new calibration label is opened.

## Historical route disposition

The historical 445-pair calibration feature file was inspected only as an outcome-free feature manifest. It contains descriptor categories `both`, `dinov2_only`, and `megadescriptor_only`. The frozen Task15J P3/P5 preprocessor supports only `both_agreement` and `both_reciprocal`; all three historical categories would be transformed as unknown. The old labels therefore cannot calibrate the frozen model without an unsupported post-hoc semantic mapping. This route is permanently recorded as `INCOMPATIBLE_DESCRIPTOR_TAXONOMY` for Task15J. No calibration label was opened.

## Frozen replacement candidate

The unused portion of the independent Task15I Eurasian-lynx reservoir was queried using only previously frozen dual-descriptor ranks. The deterministic seed `77` and fixed vertex-disjoint four-edge-tree rule select 448 calibration pairs in 112 components, with 560 selected images. All Task15I development endpoints were excluded; overlap is zero. The selected categories are 303 `both_agreement` and 145 `both_reciprocal`, both valid under the frozen P3/P5 taxonomy.

The immutable design freeze is at:

`archive/pferi_v2/task_runs/model_development/2026-07-27_task15k_independent_calibration_design_freeze_v1/`

## ModelScope execution package

The package is at:

`work/pferi_v2/gpu/packages/task15k_calibration/PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE.zip`

It includes every selected image, the selected-pair manifest, a quality-percentile reference bound to the full Task15I reservoir, the frozen Task15J model bundle, the exact preprocessor implementation, the local-measurement runner, a manifest covering every packaged file, and a SHA256 declaration. It contains no review label, identity label, calibration outcome, deployment-confirmation outcome, or mechanism-confirmation outcome.

ModelScope must run the package README commands and return its final export ZIP and SHA256 declaration. The runner rejects a changed package, changed selected-pair manifest, changed final bundle, image hash mismatch, endpoint-quality measurement failure, or invalid prediction output. A failed local measurement remains an explicit failure feature and is never treated as zero evidence.

## Remaining boundary

Task15K does not open calibration labels and does not calibrate either model. Once ModelScope returns a passing control export, the next action is to freeze the calibration analysis and blinded-review collection contract. That contract may fit only an intercept and slope on each frozen raw model logit. It cannot change P3/P5 coefficients, preprocessing, features, lambda, or model selection. Deployment and mechanism confirmation remain locked.
