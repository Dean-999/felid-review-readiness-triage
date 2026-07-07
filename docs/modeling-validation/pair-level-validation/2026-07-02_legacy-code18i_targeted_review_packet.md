# legacy-code18i Targeted Pair Reviewability Packet

Date: 2026-07-02

## Purpose

legacy-code18i turns the legacy-code18h mechanism samples into a human-review packet.

The review target is deliberately narrow:

```text
Can this pair be reviewed as visual evidence?
```

It is not:

```text
Are these two images the same individual?
```

This keeps the next step aligned with the legacy-code18 claim: PF-ERI is a
pair-level evidence-governance layer, not a descriptor replacement and not an
automatic identity assignment system.

## Inputs

legacy-code18i uses:

```text
outputs/legacy-code18/legacy-code18h_pair_level_failure_mechanism/{descriptor}/legacy-code18h_failure_case_sample.csv
outputs/legacy-code18/legacy-code18a_frozen_feature_manifest/legacy-code18a_frozen_image_feature_manifest.csv
```

The legacy-code18h sample is balanced by construction:

| Descriptor | Rows | High-similarity false candidates | High-similarity same-ID controls |
| --- | ---: | ---: | ---: |
| MegaDescriptor | 100 | 50 | 50 |
| DINOv2 | 100 | 50 | 50 |

Known same/different labels are retained in the full packet for later analysis
only. They are omitted from the blind review form.

## Outputs

For each descriptor:

```text
outputs/legacy-code18/legacy-code18i_targeted_review_packet/{descriptor}/
```

contains:

- `legacy-code18i_blind_review_form.csv`
- `legacy-code18i_targeted_pair_review_packet.csv`
- `legacy-code18i_reviewability_codebook.csv`
- `legacy-code18i_contact_sheet.jpg`
- `legacy-code18i_review_packet.html`
- `legacy-code18i_targeted_review_packet_audit.json`

The blind review form contains only:

```text
review_pair_id
query_image_path
candidate_image_path
reviewability_label
visibility_notes
reviewer_id
review_timestamp
```

This avoids showing identity truth, descriptor scores, PF-ERI scores, or sample
group during review.

## Review Labels

Allowed labels:

| Label | Meaning |
| --- | --- |
| `review_ready` | Both images expose enough comparable animal evidence for pair review. |
| `low_evidence` | One or both images are too weak, occluded, distant, or low quality. |
| `non_comparable` | Images do not show comparable body regions, pose, scale, or view. |
| `uncertain` | Reviewer cannot choose a stronger label without additional context. |

The reviewer should not assign identity labels in legacy-code18i.

## Statistical Use After Review

After labels are filled, the analysis should compare reviewability against:

- `pf_eri_admissibility_score`;
- `pf_eri_review_score`;
- `pf_eri_route`;
- descriptor-only rank and similarity;
- known same/different CzechLynx truth retained outside the blind form.

Primary checks:

- whether low admissibility is enriched for `low_evidence` or
  `non_comparable`;
- whether `review_ready` pairs preserve same-ID candidates better than a
  quality-only filter;
- whether high-similarity false candidates are visually non-comparable or are
  descriptor-level lookalike failures despite reviewable evidence;
- whether high-similarity same-ID controls are being over-penalized by the
  current conflict score.

Recommended uncertainty:

- pair-level proportions with confidence intervals for descriptive summaries;
- query-level paired bootstrap if comparing PF-ERI routing against descriptor
  rank or quality-only controls;
- if two reviewers are used, report agreement before adjudication.

## Claim Boundary

legacy-code18i can support this type of claim:

```text
Human reviewability labels agree with PF-ERI's pair-level evidence-admissibility
signal, strengthening the evidence-governance interpretation.
```

legacy-code18i cannot support:

```text
PF-ERI identifies individuals automatically.
PF-ERI has Bobcat identity accuracy.
Human reviewability labels are new identity ground truth.
```

## Verification

Implementation:

```text
scripts/build_legacy-code18i_targeted_review_packet.py
```

Test status:

```text
/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest tests.test_legacy-code18_pipeline
Ran 13 tests in 0.081s
OK
```
