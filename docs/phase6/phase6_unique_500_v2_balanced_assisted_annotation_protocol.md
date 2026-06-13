# Phase 6 Unique-500 v2 Balanced Assisted Annotation Protocol

## Workspace

```text
outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/
```

Subfolders:

- `assisted_working/`;
- `incoming_from_downloads/`;
- `corrections_from_streamlit/`;
- `imported_ranges/`;
- `needs_review_index/`;
- `qc/`.

## Commands

Organize assistant results:

```bash
python3 scripts/phase6_v2_organize_assisted_range_outputs.py \
  --range-id range_000_049 \
  --downloads-dir ~/Downloads
```

Import assistant range:

```bash
python3 scripts/phase6_v2_import_assisted_range_to_workspace.py \
  --range-id range_000_049
```

Review needs-review rows:

```bash
cd outputs/czechlynx/phase6/annotation_review_packages/phase6_unique_500_v2_balanced/assisted_annotation_workspace/incoming_from_downloads/range_000_049/needs_review_streamlit
streamlit run streamlit/streamlit_needs_review_app.py
```

Apply corrections:

```bash
python3 scripts/phase6_v2_apply_needs_review_corrections.py \
  --range-id range_000_049
```

Sync assisted to primary:

```bash
python3 scripts/phase6_v2_sync_assisted_working_to_primary.py
```

## Import Rules

Assistant-returned annotated CSVs are imported by `expanded_image_id`.

The assisted working CSV is updated first. The primary working CSV is not changed until the explicit sync command is run.

Needs-review rows are indexed under `needs_review_index/`.

The working summary CSV is regenerated in `assisted_working/` after import and correction steps.

## Freeze Rule

Do not freeze a final v1 label file automatically. Freezing should happen only after all 10 ranges are imported, corrections are applied, and the final audit passes.
