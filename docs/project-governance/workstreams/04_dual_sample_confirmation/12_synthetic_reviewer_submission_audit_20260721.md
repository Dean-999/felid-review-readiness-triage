# PF-ERI v2 synthetic reviewer submission audit

Status: **ENGINEERING PASS / HUMAN-OUTCOME PROVENANCE FAIL / QUARANTINE**
Date: 21 July 2026
Input: `final_synthetic_reviewer_submissions/`

## Decision

The supplied files are internally coherent synthetic simulation outputs. They are not four-person human annotations and cannot be admitted as v2 outcomes, an independent reviewability gold standard, model-training labels, confirmation labels, adjudications, or manuscript evidence. They may be retained only as explicitly labelled pipeline-test fixtures.

This disposition follows directly from the records rather than from a statistical suspicion. Each reviewer statement calls itself a `synthetic reviewer response package; not human-participant data`; the supplied audit states `Synthetic reviewer simulation only`; and every adjudication row has record type `synthetic_blind_adjudication`.

## Independent structural reconstruction

The four response files contain 1,112 rows each, for 4,448 first-pass responses. All 4,448 packet IDs resolve to the restricted assignment, every response is attributed to the assigned reviewer alias, no packet is missing or duplicated, and every one of the 2,224 formal pairs has exactly two first-pass responses. All decision, reason, confidence, and technical-problem fields satisfy the declared schema. No technical problem was recorded.

There are 183 exact three-category disagreements (8.23%). The synthetic adjudication table contains exactly one eligible-third-reviewer record for each of those 183 pairs and no extra pair. The resulting simulated final labels are 1,706 `review_ready` (76.71%), 432 `not_review_ready` (19.42%), and 86 `uncertain` (3.87%). Of the 183 synthetic adjudications, 182 are `not_review_ready`, one is `uncertain`, and none is `review_ready`.

These checks establish software-fixture consistency only. They do not establish valid human measurement.

## Descriptive synthetic agreement

Exact three-category agreement is 2,041/2,224 = 91.77%. The pooled two-category agreement after combining `not_review_ready` and `uncertain` is 93.71%. The supplied overall kappa of 0.7594 corresponds to a pooled multi-rater/Fleiss-style marginal calculation; a standard ordered-endpoint pooled Cohen calculation is 0.7595. The metric must be named explicitly rather than reported only as `overall_kappa`.

Pairwise exact three-category agreement and Cohen's kappa are:

| Reviewer dyad | n | Agreement | Cohen's kappa |
|---|---:|---:|---:|
| A–B | 371 | 94.07% | 0.8473 |
| A–C | 371 | 91.91% | 0.7784 |
| A–D | 370 | 90.27% | 0.7085 |
| B–C | 370 | 93.51% | 0.8045 |
| B–D | 371 | 90.84% | 0.6763 |
| C–D | 371 | 90.03% | 0.7177 |

No inferential confidence interval is assigned to these synthetic agreement values. Formal pairs share physical images, so ordinary independent-pair intervals would be anti-conservative even for genuine human responses. More importantly, a confidence interval around programmed labels does not quantify human measurement reliability.

## Provenance falsification checks

The operational timestamps are incompatible with genuine interactive review:

- Each reviewer has exactly 1,111 consecutive inter-response intervals of 11 seconds, with zero variation. Each simulated reviewer therefore completes exactly 1,112 tasks in 3.3947 hours.
- All 182 consecutive adjudication intervals are exactly 17 seconds, with zero variation.
- The five CSV files share the same filesystem creation time, 21 July 2026 at approximately 16:25 China Standard Time.
- Relative to that creation instant, 899/1,112 embedded reviewer-B submissions, all 1,112 reviewer-C submissions, all 1,112 reviewer-D submissions, and all 183 adjudications claim future submission times.
- Every optional note is empty, every technical flag is `no`, and several distributional properties exactly satisfy declared simulation target bands.

The timing contradiction alone prevents treating these records as human logs. The explicit synthetic provenance statements make the conclusion definitive.

## Statistical interpretation boundary

The apparent agreement, kappa, label proportions, confidence patterns, difficulty concentration, and adjudication behavior were generated to meet simulation constraints. They cannot answer whether human reviewers can measure reviewability reliably. They also cannot be used to fit or test PF-ERI: using labels generated from visible-evidence or automatic difficulty scores to validate a model based on related evidence would be circular.

`Delta Brier`, calibration, burden, subgroup, mechanism, and sensitivity results remain unestimated. In addition to the synthetic-outcome failure, the supplied audit reports that the required model-and-analysis freeze and frozen active-control/full-model predictions are absent. No primary success claim is available.

## Required remediation

1. Preserve this directory unchanged and mark it `SYNTHETIC_PIPELINE_TEST_ONLY` in any inventory.
2. Do not merge these rows into a human return table, model-development table, confirmation table, or manuscript result.
3. Obtain the actual `responses/raw_responses.csv` exported separately by four real reviewers, plus their genuine conflict attestations.
4. Verify filesystem and application logs against the embedded timestamps; retain technical events rather than manufacturing clean replacements.
5. Derive disagreements only after both real first-pass returns are immutable, then issue new blinded third-person adjudication packets. A pre-created adjudication file is not acceptable.
6. Keep confirmation outcomes inaccessible until the development model and calibration procedure are frozen under the accepted stage-separation protocol.

This is a failed human-outcome delivery, not evidence that the PF-ERI scientific hypothesis failed. The pipeline simulation worked; the required empirical measurement has not yet occurred.
