# Phase 6 Unique-500 v2 Balanced Selection Results

## Status

The balanced v2 selection was built successfully.

## Main Outputs

Review image folder:

```text
data/review_images/czechlynx/phase6_unique_500_v2_balanced/
```

Working CSV:

```text
data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_working.csv
```

Template CSV:

```text
data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_template.csv
```

Internal mapping:

```text
data/interim/czechlynx/czechlynx_phase6_unique_500_v2_balanced_review_mapping_internal.csv
```

Assisted workspace:

```text
outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/
```

## Overall Distribution

| Quality Bucket | Count | Percent |
|---|---:|---:|
| high evidence proxy | 150 | 30.0 |
| medium evidence proxy | 175 | 35.0 |
| low but annotatable proxy | 110 | 22.0 |
| extreme hard proxy | 65 | 13.0 |

Near-black, eye-shine-only, or almost-empty proxy count:

```text
38 / 500
```

This is 7.6 percent of the full set, below the 15 percent cap.

## Batch Distribution

| Batch | High | Medium | Low | Extreme Hard | Near-Black/Empty Proxy |
|---|---:|---:|---:|---:|---:|
| batch_001 | 15 | 18 | 11 | 6 | 3 |
| batch_002 | 15 | 18 | 11 | 6 | 4 |
| batch_003 | 15 | 18 | 11 | 6 | 4 |
| batch_004 | 15 | 18 | 11 | 6 | 6 |
| batch_005 | 15 | 18 | 11 | 6 | 4 |
| batch_006 | 15 | 17 | 11 | 7 | 3 |
| batch_007 | 15 | 17 | 11 | 7 | 6 |
| batch_008 | 15 | 17 | 11 | 7 | 4 |
| batch_009 | 15 | 17 | 11 | 7 | 1 |
| batch_010 | 15 | 17 | 11 | 7 | 3 |

No batch has more than 10 extreme-hard or near-black/empty proxy images.

## QC

Selection audit:

```text
PASS
```

Leakage scan:

```text
PASS
```

Batch ZIP integrity:

```text
PASS
```

Each batch ZIP contains 50 images plus the required manifest, annotation template, review protocol, and QC report.
