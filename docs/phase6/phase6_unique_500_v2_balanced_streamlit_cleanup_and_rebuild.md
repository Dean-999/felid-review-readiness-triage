# Phase 6 Unique-500 v2 Balanced Streamlit Cleanup And Rebuild

## Why The Old App Was Invalid

The old needs-review Streamlit package used the generic app name:

```text
streamlit_needs_review_app.py
```

That package was tied to the earlier flawed unique-500 workflow and could be confused with v1 range outputs. It should not be used for the active v2 balanced workflow.

The active workflow is:

```text
phase6_unique_500_v2_balanced
```

## Cleanup

Stale or ambiguous artifacts were archived under:

```text
outputs/czechlynx/phase6/archive/stale_v1_assisted_annotation_artifacts_20260613/
```

The cleanup report is:

```text
outputs/czechlynx/qc/phase6_v2_stale_artifact_cleanup_report.txt
```

Archived artifacts included old v1-style range files, old generic needs-review Streamlit packages, stale ZIPs, and confusing `(1)` files after their intended v2 CSV content was copied to canonical filenames.

## New Clean v2 Package

New package path:

```text
outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/incoming_from_downloads/range_000_049/needs_review_streamlit_v2_clean/
```

New app:

```text
outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/incoming_from_downloads/range_000_049/needs_review_streamlit_v2_clean/streamlit/streamlit_phase6_v2_needs_review_app.py
```

Needs-review rows:

```text
8
```

The new package contains:

- copied v2 review images;
- a v2 clean manifest;
- a v2 clean correction template;
- a v2-specific Streamlit app;
- QC report;
- README.

## Run Command

```bash
cd "/Users/deanshen/Desktop/scientific project/felid-review-readiness-triage/outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/incoming_from_downloads/range_000_049/needs_review_streamlit_v2_clean"

streamlit run streamlit/streamlit_phase6_v2_needs_review_app.py
```

Do not use old `streamlit_needs_review_app.py` packages for v2 balanced correction.

## Apply Corrections After Review

```bash
cd "/Users/deanshen/Desktop/scientific project/felid-review-readiness-triage"

python3 scripts/phase6_v2_apply_needs_review_corrections.py \
  --range-id range_000_049 \
  --correction-csv "outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/incoming_from_downloads/range_000_049/needs_review_streamlit_v2_clean/range_000_049_needs_review_corrections_working_v2_clean.csv"
```

## Annotation Rule

Use `complete` when the annotator has approximately 75 percent confidence in the visual-factor labels.

Use `needs_review` only when field labels remain genuinely unstable or ambiguous.

Poor image quality alone is not `needs_review`.

## QC

The clean package QC report is:

```text
outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/incoming_from_downloads/range_000_049/needs_review_streamlit_v2_clean/qc/needs_review_streamlit_v2_clean_qc_report.txt
```

Results:

- needs-review rows: 8;
- images copied: 8;
- missing images: 0;
- app syntax check: pass;
- leakage scan: pass;
- primary working CSV not overwritten.
