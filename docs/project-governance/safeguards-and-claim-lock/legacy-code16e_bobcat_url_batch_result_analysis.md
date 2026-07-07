# legacy-code16e Bobcat URL Batch Result Analysis

Date: 2026-06-29

## Claim Boundary

This analysis receives and audits the completed Bobcat URL scoring batch. It is
evidence for review-readiness transfer stress and workflow routing only.

It is not evidence of Bobcat individual-ID accuracy, not a descriptor-only
replacement claim, and not a final 3000-image freeze.

## Inputs

Source root:

```text
outputs/legacy-code16/bobcat_url_batch/
```

Merged receiver output:

```text
outputs/legacy-code16/legacy-code16e_bobcat_candidate_model_filter/legacy-code16e_bobcat_scores_00000_19999_merged.csv
outputs/legacy-code16/legacy-code16e_bobcat_candidate_model_filter/legacy-code16e_bobcat_scores_00000_19999_merged_audit.json
```

Analysis output:

```text
outputs/legacy-code16/legacy-code16e_bobcat_score_analysis/
```

## Handoff Integrity

The Bobcat run is complete enough to use as legacy-code16e transfer-stress evidence.

| check | result |
| --- | ---: |
| score CSV files | 67 |
| audit JSON files | 67 |
| merged rows | 20,000 |
| candidate ID coverage | 00001-20000 complete |
| duplicate candidate IDs | 0 |
| duplicate image URIs | 0 |
| missing required scoring columns | 0 |
| missing Bobcat metadata columns | 0 |
| forbidden sensitive columns | 0 |
| image load success rows | 20,000 |
| scoring-valid rows | 20,000 |
| model fallback rows | 0 |

The per-batch audits consistently report URL-mode scoring, successful image
loads, numeric final scores, disabled pose, no fallback scoring, and no sensitive
column leakage.

## Recalibrated Eligibility

The existing Bobcat profile was applied without changing the project threshold
logic.

| tier | count | rate |
| --- | ---: | ---: |
| strict | 4,311 | 21.6% |
| balanced | 7,384 | 36.9% |
| broad | 12,000 | 60.0% |

The recommended working tier remains balanced. Broad is useful for manual-audit
coverage and stress testing, not for clean high-confidence selection.

## Source-Tier Split

Bobcat is not one homogeneous pool.

| source role | rows | strict eligible | balanced eligible | broad eligible | final p50 | IQA p50 | side p50 | MD geometry p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `fcf_high_geometry_primary` | 6,412 | 3,201 | 4,308 | 5,752 | 0.2810 | 0.4598 | 0.0018 | 0.3171 |
| `fcf_next_best_topup` | 13,588 | 1,110 | 3,076 | 6,248 | 0.2151 | 0.4744 | 0.0013 | 0.0000 |

Interpretation:

- Tier 1 primary rows behave like the intended high-geometry pool: balanced
  eligibility is 67.2%.
- Tier 2 top-up rows are useful but weaker: balanced eligibility is 22.6%.
- The top-up rows have missing MegaDetector geometry inputs, so their
  `md_geometry_score` is 0. Their lower final score should be interpreted as a
  metadata/geometry-evidence limitation, not simply as poor image quality.

## Viewpoint And Evidence Quality

Viewpoint labels are heavily concentrated in non-ideal review states.

| CLIP viewpoint label | rows | rate |
| --- | ---: | ---: |
| `partial_or_occluded` | 17,300 | 86.5% |
| `unclear` | 2,698 | 13.5% |
| `rear` | 2 | <0.1% |

Compared with CzechLynx reference quantiles, Bobcat has higher median final
score and IQA proxy, but much lower side-view evidence:

| metric | Bobcat p50 | CzechLynx p50 | Bobcat minus CzechLynx p50 |
| --- | ---: | ---: | ---: |
| final candidate score | 0.2307 | 0.1901 | +0.0406 |
| IQA proxy | 0.4709 | 0.4010 | +0.0699 |
| CLIP side-view score | 0.0015 | 0.0072 | -0.0058 |
| viewpoint confidence | 0.9134 | 0.8050 | +0.1084 |
| partial/occluded probability | 0.9045 | 0.6392 | +0.2652 |

This is exactly the kind of signal PF-ERI should preserve: some images can be
technically sharp and confidently classified while still being weak evidence for
individual-level review.

## Runtime Artifacts

The run contains IQA out-of-memory traces, but these did not invalidate the
handoff:

- MUSIQ error rows: 4,934.
- TOPIQ error rows: 5,486.
- `iqa_quality_proxy_score` is still present for all 20,000 rows.
- `scoring_valid_for_selection` is true for all 20,000 rows.

The correct response is not to discard the run. The correct response is to keep
the audit flags visible and avoid treating individual IQA model outputs as
complete for every row.

## Scientific Interpretation

The Bobcat batch strengthens the project-first gap:

```text
descriptor retrieval can assemble candidate images
-> but candidate images differ strongly in review evidence quality
-> a post-retrieval reliability/router layer can triage review burden,
   retain usable positives, and expose weak-evidence cases
```

It does not support the stronger and riskier claim that PF-ERI beats
descriptor-only ranking. The stronger claim would require verified Bobcat
identity labels or audited same/different pair labels.

## Adversarial Review

Question: do we have factual confidence that this strategy is sound?

Yes for the narrow claim: Bobcat supports review-readiness transfer stress. The
handoff is complete, leakage-sensitive columns are absent, and the quality
signals show a real routing problem.

No for any identity-accuracy or descriptor-replacement claim. Current Bobcat
rows are species-level FCF candidates without verified individual IDs.

Possible attack: "The low top-up score is an artifact of missing MD geometry,
not a true image-quality result."

Repair: keep source-tier routing separate. Do not combine Tier 1 and Tier 2 into
a single high-confidence claim. Report Tier 2 as top-up/stress evidence and use
manual audit before any final selection.

Possible attack: "The model labeled nearly everything partial/occluded, so the
viewpoint classifier may be poorly calibrated for Bobcat."

Repair: use CLIP viewpoint as a routing signal, not ground truth. Sample top,
middle, and bottom rows for manual audit and measure agreement before assigning
strong semantic meaning to the labels.

Possible attack: "IQA OOM errors make the scoring unreliable."

Repair: the composite proxy exists for all rows, but individual MUSIQ/TOPIQ
coverage should be reported. Any publication figure should distinguish proxy
availability from per-model availability.

Possible attack: "The project is moving goalposts because descriptor-only is a
strong baseline."

Repair: keep the locked legacy-code16i/legacy-code17 claim boundary. The goal is not to beat
descriptor-only top-k; it is to add an evidence reliability and review-routing
layer after retrieval.

## Recommended Next Step

Build a Bobcat legacy-code17 transfer-stress/review-routing analysis using the
balanced tier as the primary working set and the broad tier as a manual-audit
coverage reserve.

Minimum outputs should include:

1. Tier-separated Bobcat review queue.
2. Fixed-budget review slices from strict, balanced, broad, and low-score rows.
3. Manual-audit sheet with source tier, final score, IQA proxy, side-view score,
   CLIP viewpoint, and image URI.
4. Transfer-stress comparison against CzechLynx legacy-code17a endpoints without
   claiming Bobcat identity accuracy.

