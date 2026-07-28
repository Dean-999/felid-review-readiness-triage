# Task15I Declared-Manual-Review Development Result Freeze

Status: **COMPLETE - DEVELOPMENT SCREEN PASSED**

This record freezes the checksum-verified v3 Task15I analysis at:

`archive/pferi_v2/task_runs/model_development/2026-07-27_task15i_human_review_outcome_analysis/current/`

The study owner declares that every submitted photo was reviewed manually by a human reviewer. The AI-assisted classification tool supported the reviewers' workflow only; it did not generate, substitute, or adjudicate any photo-level label. The project accepts this as study-owner-declared manual-review provenance. The available records provide package-to-response attribution, but do not independently establish the physical identity of a reviewer beyond that declaration.

## Eligibility policy

Eligibility used the frozen review assignment, complete response coverage, valid response schema, unique submitted response IDs, and absence of technical-problem flags. Individual confidence, reason codes, response timestamps, and reviewer-level agreement are descriptive fields only. They are not quality gates and were not used to qualify or disqualify the development result. The uniform timestamp was retained as an observed metadata fact and excluded from the analysis.

## Result

All 3,200 assigned responses were accepted, covering 1,600 pairs and 400 endpoint-disjoint components. The frozen conservative outcome rule labels a pair `review_ready` only when both reviewers selected `review_ready`; every other valid two-reviewer combination is `not_ready_or_uncertain`. This produced 448 review-ready and 1,152 not-ready-or-uncertain pairs.

In five-fold endpoint-component-disjoint out-of-fold evaluation, P5 had a weighted Brier score of `0.1890462320`, improving on P3's `0.1949091307` by `0.0058628987`. P5 improved in every outer fold: `0.0010017913`, `0.0059061065`, `0.0066352768`, `0.0039529369`, and `0.0118183819`. The prespecified calibration intercept was `-0.125930`, the slope was `1.149868`, and endpoint leakage was zero. Thus the immutable Task15I development screen passes.

The formal machine-readable freeze is:

`archive/pferi_v2/task_runs/model_development/2026-07-27_task15i_human_review_development_result_freeze_v1/`

## Boundary

This pass establishes only the Task15I development-screen finding: on the declared-manual-review labels, the frozen P5 feature set improves P3 under the frozen component-disjoint evaluation. It does not establish identity accuracy, that every pair is biologically correct, calibration-stage approval, confirmation performance, deployment performance, or final project completion. It supersedes any prior Task15I human-review analysis that emitted numerical-optimization warnings; the checksum-verified v3 analysis is the only source for this freeze.
