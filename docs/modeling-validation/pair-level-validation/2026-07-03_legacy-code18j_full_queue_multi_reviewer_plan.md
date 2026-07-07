# legacy-code18j Full-Queue Multi-Reviewer Validation Plan

Date: 2026-07-03

## Purpose

legacy-code18j fixes the three main legacy-code18i weaknesses:

1. single reviewer;
2. targeted-only sample;
3. no explicit `low_evidence` / `non_comparable` reason labels.

The new packet samples the full CzechLynx evaluation retrieval queue from both
strong descriptors:

```text
outputs/legacy-code18/legacy-code18d_strong_pf_eri_pair_features/megadescriptor_l_384/
outputs/legacy-code18/legacy-code18d_strong_pf_eri_pair_features/dinov2_vitl14/
```

## Packet

Generated output:

```text
outputs/legacy-code18/legacy-code18j_full_queue_review_packet/
```

Composition:

| Descriptor | Pairs | same-ID | false candidates |
| --- | ---: | ---: | ---: |
| MegaDescriptor | 300 | 150 | 150 |
| DINOv2 | 300 | 150 | 150 |
| Total | 600 | 300 | 300 |

Sampling is stratified by:

- descriptor;
- evaluation split only;
- descriptor rank bin: `rank_01`, `rank_02_05`, `rank_06_10`, `rank_11_20`;
- PF-ERI admissibility tertile: low/mid/high;
- same/different known-ID truth for balanced validation.

Truth labels are excluded from the blind form.

## Recommended Reviewer Count

Use **3 reviewers**.

Why:

- 2 reviewers are the minimum for agreement and Cohen's kappa.
- 3 reviewers allow majority vote and cleaner adjudication.
- If one reviewer is noisy or incomplete, the study still has a usable
  two-reviewer subset.

## Reviewer Commands

Run one reviewer at a time on different ports, or on separate machines with the
same repository.

Reviewer 1:

```bash
legacy-code18j_REVIEWER_ID=reviewer1 \
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
-m streamlit run scripts/streamlit_legacy-code18j_full_queue_review_app.py \
--server.address 127.0.0.1 --server.port 8511 --server.headless true
```

Reviewer 2:

```bash
legacy-code18j_REVIEWER_ID=reviewer2 \
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
-m streamlit run scripts/streamlit_legacy-code18j_full_queue_review_app.py \
--server.address 127.0.0.1 --server.port 8512 --server.headless true
```

Reviewer 3:

```bash
legacy-code18j_REVIEWER_ID=reviewer3 \
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
-m streamlit run scripts/streamlit_legacy-code18j_full_queue_review_app.py \
--server.address 127.0.0.1 --server.port 8513 --server.headless true
```

Open:

```text
http://127.0.0.1:8511
http://127.0.0.1:8512
http://127.0.0.1:8513
```

Each reviewer must label both descriptors:

```text
megadescriptor_l_384
dinov2_vitl14
```

## Labeling Protocol

First choose:

```text
review_ready
not_review_ready
uncertain
```

If `not_review_ready`, choose one primary reason:

```text
low_evidence
non_comparable
both_low_evidence_and_non_comparable
identity_uncertain_but_reviewable
other
```

Definitions:

- `review_ready`: both images expose enough comparable animal evidence for
  pair-level review.
- `low_evidence`: at least one image is too weak, small, blurry, distant,
  occluded, or low quality.
- `non_comparable`: images are visible, but body region, viewpoint, pose,
  scale, or evidence type cannot be compared.
- `both_low_evidence_and_non_comparable`: both problems are substantial.
- `identity_uncertain_but_reviewable`: the pair is visually reviewable, but
  identity itself is difficult. Normally this should still be `review_ready`.
- `uncertain`: use only when reviewability itself cannot be determined after
  considering the reason options.

Do not label identity. The question is:

```text
Can this pair be used as reviewable visual evidence?
```

not:

```text
Are these the same individual?
```

## Output Files

Reviewer 1:

```text
outputs/legacy-code18/legacy-code18j_streamlit_review/reviewer1/megadescriptor_l_384/legacy-code18j_full_queue_review_working.csv
outputs/legacy-code18/legacy-code18j_streamlit_review/reviewer1/dinov2_vitl14/legacy-code18j_full_queue_review_working.csv
```

Reviewer 2:

```text
outputs/legacy-code18/legacy-code18j_streamlit_review/reviewer2/megadescriptor_l_384/legacy-code18j_full_queue_review_working.csv
outputs/legacy-code18/legacy-code18j_streamlit_review/reviewer2/dinov2_vitl14/legacy-code18j_full_queue_review_working.csv
```

Reviewer 3:

```text
outputs/legacy-code18/legacy-code18j_streamlit_review/reviewer3/megadescriptor_l_384/legacy-code18j_full_queue_review_working.csv
outputs/legacy-code18/legacy-code18j_streamlit_review/reviewer3/dinov2_vitl14/legacy-code18j_full_queue_review_working.csv
```

After completion, click `Export analysis-ready CSV` in the app for each
descriptor/reviewer.

## Analysis After Review

After all reviewers finish, legacy-code18j should compute:

- completion and invalid-label audit;
- per-reviewer label distributions;
- pairwise percent agreement;
- Cohen's kappa for binary `review_ready` vs non-ready;
- optional multi-rater Fleiss kappa;
- majority vote / adjudicated labels;
- PF-ERI admissibility vs reviewability in full-queue population sample;
- PF-ERI vs quality-only AUC;
- descriptor-stratified and pooled query-cluster bootstrap CIs.

Success criterion:

```text
PF-ERI admissibility predicts full-queue human reviewability across both
descriptors, with acceptable reviewer agreement.
```

Strong reviewer agreement target:

```text
Cohen's kappa >= 0.60 usable
Cohen's kappa >= 0.75 strong
```

## Claim Boundary

Even legacy-code18j does not produce Bobcat identity accuracy. It validates
pair-level reviewability governance on CzechLynx known-ID candidate pairs.
