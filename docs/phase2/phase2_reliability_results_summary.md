# Phase 2 Reliability Results Summary

## Purpose

This document summarizes the CzechLynx pilot Phase 2 reliability analysis results for Q1: whether images labeled as more review-ready show more reliable Re-ID behavior than review-limited or unidentifiable images.

This is a pilot analysis under a fixed generic ResNet-50 ImageNet embedding baseline. Embeddings are measurement signals for review-readiness validation, not animal identification results.

## Q1 Result

**Partial / mixed support.**

Overall same/different separation is weak-to-moderate. Some readiness groups show positive separation signals, but the evidence is not strong enough for final scientific claims or deployment conclusions.

## Overall Results

| Metric | Value |
| --- | ---: |
| Input rows | 400 pairs |
| Same-individual pairs | 100 |
| Different-individual pairs | 300 |
| Same-individual mean cosine similarity | 0.579955 |
| Different-individual mean cosine similarity | 0.493990 |
| Overall mean gap (same minus different) | 0.085966 |
| ROC-AUC | 0.618667 |

The overall gap is positive, which means same-individual pairs score higher on average than different-individual pairs under this baseline. The magnitude is modest, and the ROC-AUC is only slightly above chance.

## Readiness-Group Separation Gaps

| Pair readiness group | Same-minus-different mean gap |
| --- | ---: |
| limited_limited | 0.035978 |
| limited_unidentifiable | 0.115845 |
| ready_limited | 0.068114 |
| ready_ready | 0.119379 |
| ready_unidentifiable | 0.057317 |
| unidentifiable_unidentifiable | 0.133164 |

### Group Counts

| Pair readiness group | Same-individual pairs | Different-individual pairs |
| --- | ---: | ---: |
| ready_ready | 3 | 7 |
| limited_limited | 28 | 88 |
| unidentifiable_unidentifiable | 14 | 20 |

## Interpretation

### Overall

Overall same/different separation is weak-to-moderate. The positive overall gap supports cautious continued evaluation, but it does not prove that review-ready images always produce reliable Re-ID behavior.

### ready_ready

`ready_ready` shows a positive signal compared with the overall gap and with `limited_limited`. Its gap of 0.119379 is higher than the overall gap of 0.085966 and much higher than the `limited_limited` gap of 0.035978.

However, `ready_ready` evidence is limited by sparse pair counts: only 3 same-individual pairs and 7 different-individual pairs. This group should be interpreted as suggestive, not definitive.

### unidentifiable_unidentifiable

`unidentifiable_unidentifiable` has the largest gap at 0.133164, but this should not be interpreted as stronger Re-ID readiness. The group still has low absolute similarity levels, and the gap may reflect low within-group variance or baseline behavior on low-quality images rather than useful matching evidence.

### limited_limited

`limited_limited` has the smallest gap and the largest pair count. This suggests that review-limited images may not provide strong same/different separation under the generic baseline, which is consistent with the rubric treating them as lower-readiness inputs.

## Threshold Proxy Summary

| Threshold | Same pairs retained | Different pairs retained |
| --- | ---: | ---: |
| 0.547081 | 60 | 140 |
| 0.680093 | 34 | 66 |
| 0.770424 | 22 | 18 |
| 0.808955 | 14 | 6 |

These threshold summaries are pairwise false-match risk proxies, not real-world false-match rates. They describe how many different-individual pairs would remain above a pilot-specific similarity cutoff, not how often identity errors would occur in deployment.

Thresholds are baseline-specific and should not be treated as universal felid Re-ID thresholds.

## What This Analysis Can Support

- cautious pilot-level statements that same-individual pairs tend to score higher than different-individual pairs;
- exploratory comparison of readiness groups under a fixed generic baseline;
- justification for proceeding to Phase 3 risk-coverage policy analysis with conservative interpretation.

## What This Analysis Cannot Claim

- individual animals were identified;
- a real-world false-match rate;
- a deployment-ready Re-ID system;
- a new or improved Re-ID model;
- a universal threshold across felid species;
- final proof that review-ready always works.

## Phase 2 Decision

Proceed to Phase 3 risk-coverage analysis with conservative interpretation.

Phase 2 provides partial / mixed support for Q1 under the generic ResNet-50 baseline. The next step is to evaluate how filtering policies change retained evidence and pairwise false-match risk proxies, without treating current similarity results as final proof of rubric success.
