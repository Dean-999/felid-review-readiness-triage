# Task15L Calibration Collection Freeze

Status: **AUTHORIZED FOR CONTROLLED CALIBRATION FIRST-PASS COLLECTION**

Task15K's ModelScope execution passed integrity, coverage, image-quality reproduction, feature reconstruction, and frozen P3/P5 prediction reconstruction. Task15L imports that output into the project as an immutable source delivery, freezes the calibration-label rule, and creates the controlled reviewer release.

The collection contains 448 independent calibration pairs. Each pair is assigned to two distinct reviewers, for 896 first-pass decisions. The existing four-person roster is reused; each reviewer receives exactly 224 items. Reviewer ZIPs show only opaque packet and asset tokens plus rendered metadata-stripped PNGs. Predictions, descriptors, ranks, pair IDs, image IDs, components, sampling stage, source metadata, and other reviewers' work are restricted.

The pair label is `0` only when both first-pass reviewers select `review_ready`; all other combinations produce `not_ready_or_uncertain_label=1`. Coverage, valid response schema, unique response provenance, and no technical-problem flag are the only hard eligibility requirements. Reasons, confidence, timestamps, and reviewer agreement are descriptive only.

After response return, calibration may fit only an intercept and slope on the logit of each raw P3/P5 probability. It may not change model coefficients, preprocessing, lambda, model selection, or decision threshold. The resulting calibration is apparent calibration; independent future confirmation remains necessary for performance claims.
