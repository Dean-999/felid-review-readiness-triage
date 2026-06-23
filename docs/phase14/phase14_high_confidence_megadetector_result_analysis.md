# Phase 14 High-Confidence MegaDetector Result Analysis

Date: 2026-06-20

## Input And Gate

Input folder:

```text
outputs/phase14/phase14_colab_megadetector_final_selection/
```

The Colab/MegaDetector finalizer processed all expected rows:

```text
input_manifest_rows: 7,467
input_detection_rows: 7,467
duplicate_candidate_id: 0
duplicate_source_path: 0
md_error_rows: 0
```

The fixed high-evidence gate was:

```text
md_best_confidence >= 0.55
md_area_fraction >= 0.035
md_width_fraction >= 0.18
md_height_fraction >= 0.10
0.70 <= md_aspect_ratio <= 4.80
edge_touch_allowed = no
```

## Main Result

| dataset | candidates | passed | pass rate | final status |
|---|---:|---:|---:|---|
| bobcat | 3,915 | 656 | 16.8% | below_target_do_not_force |
| CzechLynx | 3,552 | 2,220 | 62.5% | below_target_do_not_force |
| total | 7,467 | 2,876 | 38.5% | below_target_do_not_force |

Neither dataset reached the requested 3,000 detector-gated high-confidence images. This should not be fixed by relaxing the gate. The current rule is intentionally strict and should be treated as a risk-control constraint.

## Interpretation

This is a strong diagnostic result, not a failed run.

The detector-first gate corrected the main weakness found in manual audits: rule-only and AI-first-pass labels overestimated high-confidence Re-ID evidence, especially for urban/peri-urban bobcat images. Under the same gate, bobcat retained only 656 high-confidence images, while CzechLynx retained 2,220. This supports the core Phase 14 claim that urban/peri-urban bobcat imagery has lower high-evidence availability under a same-genus Re-ID evidence standard.

The result also protects the project from overclaiming. A forced 3,000-image bobcat high-confidence set would likely contain many distant, narrow, edge-touching, or non-comparable images and would weaken downstream conclusions.

## Failure Structure

### Bobcat

Bobcat failure is mostly an evidence-geometry problem, not a detector-confidence problem.

| failure component | count | rate |
|---|---:|---:|
| animal too small | 2,284 | 58.3% |
| width too narrow | 2,551 | 65.2% |
| bad aspect ratio | 1,905 | 48.7% |
| edge touch | 860 | 22.0% |
| low detector confidence | 63 | 1.6% |
| no detection | 19 | 0.5% |

The most common failed patterns were:

```text
animal_too_small|insufficient_bbox_span|extreme_aspect_ratio
animal_too_small|insufficient_bbox_span
edge_touch
```

This means most rejected bobcat images still contain detectable bobcats, but the visible animal geometry is not strong enough for individual Re-ID evidence.

### CzechLynx

CzechLynx failure is less about animal size and more about edge-touch/crop and detector confidence.

| failure component | count | rate |
|---|---:|---:|
| edge touch | 777 | 21.9% |
| low detector confidence | 643 | 18.1% |
| bad aspect ratio | 373 | 10.5% |
| animal too small | 131 | 3.7% |
| width too narrow | 135 | 3.8% |
| no detection | 120 | 3.4% |

The most common failed patterns were:

```text
edge_touch
low_md_confidence
low_md_confidence|edge_touch
```

This means CzechLynx high candidates are often large enough for Re-ID, but some are cropped, edge-constrained, or lower-confidence under the detector.

## Final High-Confidence Set Quality

### Bobcat Final Set

```text
rows: 656
locations: 88
years: 2020-2025
night_ir_rows: 0
human_review_bucket: review_ready only
human_review_confidence: 525 high, 131 medium
```

The bobcat final high-confidence set is small but clean. It is suitable for high-precision urban evidence-distribution analysis and visual audit sampling, but not for a claim that 3,000 high-confidence urban bobcat Re-ID images are available in the current local pool.

### CzechLynx Final Set

```text
rows: 2,220
unique_identities: 276
identities_with_at_least_2_images: 239
identities_with_at_least_3_images: 200
median_images_per_identity: 4.5
max_images_per_identity: 70
```

The CzechLynx final high-confidence set remains strong for known-ID retrieval and pair-level evidence analysis. It is below 3,000 but still has broad identity coverage.

## Scientific Consequence

The correct interpretation is:

```text
High-confidence evidence is not equally available across wild CzechLynx and urban/peri-urban bobcat under a shared detector-first Re-ID evidence gate.
```

This strengthens the 2x2 risk-control design:

```text
environment axis: wild vs urban/peri-urban
evidence axis: high-confidence vs low-evidence stress
```

The high-confidence sets should not be forced to equal 3,000 rows. Instead:

1. Use the detector-gated high-confidence sets as high-precision core evidence.
2. Use matched-size resampling for wild-vs-urban high-confidence comparisons.
3. Use the rejected high-candidate rows as review-limited or stress-test evidence, not as clean training data.
4. Use the low-evidence MegaDetector workflow to validate the stress sets symmetrically.

## Recommended Next Analysis

For the next step, use three linked views:

```text
View A: full candidate pool
View B: detector-gated high-confidence set
View C: detector-rejected or low-evidence stress set
```

Recommended modeling:

```text
P(pass high-evidence gate) ~ environment + image geometry + quality proxies
```

and for comparison:

```text
matched bobcat-vs-CzechLynx high-confidence analysis using n = 656 per environment
```

This avoids false balance while preserving a strict quality boundary.
