# Phase 6 Unique-500 v2 Balanced Annotation Workflow Protocol

## Active Workflow

```text
phase6_unique_500_v2_balanced
```

## Annotation Files

Primary working CSV:

```text
data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_working.csv
```

Template CSV:

```text
data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_template.csv
```

Future audited v1 path:

```text
data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_v1.csv
```

Do not create the final v1 file until annotation import, correction, audit, and review are complete.

## Batch ZIP Workflow

Batch ZIPs are stored in:

```text
outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/batch_zips/
```

Each ZIP contains:

- 50 safe review images;
- `batch_manifest.csv`;
- `batch_annotation_template.csv`;
- `batch_review_protocol.md`;
- `qc_report.txt`.

Send one batch ZIP at a time for assisted annotation.

## Annotation Status

Use:

- `pending`: unannotated;
- `complete`: annotator has approximately 75 percent confidence in the labels;
- `needs_review`: annotation itself is unstable or ambiguous.

Low image quality alone is not `needs_review`. A poor image can still be `complete` if the visual-factor labels are clear.

## Sensitive Data Boundary

Public batch files contain only anonymous v2 IDs and safe copied image names.

The internal mapping is separate and must not be sent for annotation.
