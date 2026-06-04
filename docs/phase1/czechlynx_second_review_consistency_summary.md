# CzechLynx Second-Review Consistency Summary

## Purpose

This document summarizes the delayed intra-reviewer second-review check for the CzechLynx 200-image blinded pilot triage.

The check evaluates whether the same reviewer applies the review-readiness rubric consistently enough for pilot-level Phase 2 progression. It does not identify individual animals, validate a Re-ID model, or make final scientific claims.

## Design

- Second-review subset size: 30 images.
- Sampling design: stratified subset with 10 original `review-ready`, 10 original `review-limited`, and 10 original `unidentifiable` images.
- Second-review blinding audit: PASS.
- Joined rows: 30.
- Total reviewed rows: 30.

The second review is used as intra-reviewer consistency evidence. It is not inter-rater reliability.

## Main Result

| Measure | Agreement |
| --- | ---: |
| Exact `triage_label` agreement | 24/30 = 0.800 |
| Cohen's kappa for `triage_label` | 0.700 |
| `pattern_visibility` agreement | 20/30 = 0.667 |
| `side_comparability` agreement | 16/30 = 0.533 |
| `exclusion_reason` agreement | 20/30 = 0.667 |

The `triage_label` agreement meets the pilot progression threshold of 80%. The rubric is acceptable for pilot-level Phase 2 progression, with caution that supporting fields are less stable than the main label.

## Confusion Matrix

Rows are original triage labels. Columns are second-review triage labels.

| Original label | Second review-ready | Second review-limited | Second unidentifiable |
| --- | ---: | ---: | ---: |
| review-ready | 7 | 2 | 1 |
| review-limited | 0 | 10 | 0 |
| unidentifiable | 0 | 3 | 7 |

## Disagreement Cases

| Second-review ID | Original pilot ID | Original label | Second-review label | Interpretation |
| --- | --- | --- | --- | --- |
| `czlx_second_0005` | `czlx_pilot_0053` | unidentifiable | review-limited | Adjacent boundary shift toward review-limited |
| `czlx_second_0011` | `czlx_pilot_0141` | unidentifiable | review-limited | Adjacent boundary shift toward review-limited |
| `czlx_second_0014` | `czlx_pilot_0011` | review-ready | unidentifiable | Major disagreement; flag for rubric review |
| `czlx_second_0018` | `czlx_pilot_0047` | review-ready | review-limited | Adjacent boundary shift toward review-limited |
| `czlx_second_0023` | `czlx_pilot_0163` | unidentifiable | review-limited | Adjacent boundary shift toward review-limited |
| `czlx_second_0026` | `czlx_pilot_0002` | review-ready | review-limited | Adjacent boundary shift toward review-limited |

## Interpretation

The main `triage_label` result is acceptable for pilot-level Phase 2 progression. Most disagreements involve the adjacent boundary class `review-limited`, which suggests the middle category is doing useful work as an uncertainty buffer.

The major disagreement case is `czlx_pilot_0011`, which changed from `review-ready` to `unidentifiable`. This case should be flagged for later rubric review, but the final 200-label CSV should not be changed based on the second-review result.

Supporting fields are less stable than `triage_label`, especially `side_comparability` at 16/30 agreement. Phase 2 interpretation should therefore rely primarily on finalized `triage_label` groups and treat supporting-field summaries as secondary or exploratory.

## Phase 1 Gate Decision

Phase 1 second-review gate: acceptable for pilot-level Phase 2 progression.

This decision means the project may proceed to planned Phase 2 validation-table, pair-set, and embedding-similarity validation steps. It does not mean the rubric has perfect reliability, and it does not prove that the review-readiness gate works in deployment.

## Boundaries

- Do not modify the final 200-label CSV based on these second-review results.
- Do not modify second-review labels after summarizing this check.
- Use these results as intra-reviewer consistency evidence, not inter-rater reliability.
- Do not make final scientific claims until Phase 2 similarity analysis and Phase 3 risk-coverage evaluation are complete.
- Do not claim individual animal identification, population estimation, a new Re-ID model, or a universal felid threshold.
