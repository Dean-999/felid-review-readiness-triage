# CSV and Artifact Inventory

Date: 2026-06-29

Purpose: identify the important local tables and generated artifacts without moving or deleting data. `data/` and `outputs/` are local evidence stores and are intentionally not committed.

Exception: one historical CzechLynx label artifact is currently tracked even
though most of `data/` is ignored:

```text
data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_v1.csv
```

Treat this as a deliberate versioned label artifact until it is either kept as a
documented fixture or migrated to a clearer metadata/fixture path. Do not add new
local data files under `data/` without an explicit rule.

## Current Core Inputs

These are the main CzechLynx CSV inputs for the pairwise evidence-learning foundation. legacy-code14 adds UWIN bobcat inventory and cross-context tables once local data paths are confirmed.

- `data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv`
- `data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv`
- `outputs/czechlynx/phase10_lite/phase10_lite_plus_matched_training_manifest_k3.csv`
- `outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv`
- `outputs/czechlynx/phase4/czechlynx_phase4c_pair_level_mechanism_similarity_table.csv`

## Current Core Outputs

These are the most important generated tables for Phase 12A:

- `outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table.csv`
- `outputs/czechlynx/phase12/phase12_pair_candidate_analysis_summary.csv`
- `outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table_audit.csv`
- `outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv`
- `outputs/czechlynx/phase11/phase11_pair_level_pf_eri_score_summary.csv`
- `outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table_audit.csv`
- `outputs/czechlynx/phase11c/diagnostics/phase11c_positive_pair_reliability_by_split_group.csv`
- `outputs/czechlynx/phase11c/diagnostics/phase11c_negative_pair_hard_negative_by_split_group.csv`
- `outputs/czechlynx/phase11d/target_rate_positive_rescue/phase11dr2_target_rate_positive_rescue_count_preview.csv`

## Historical But Still Important

These remain important because current claims and diagnostics depend on them:

- `outputs/czechlynx/phase4/`: visual mechanism tables, descriptor embeddings, and pair similarity signals.
- `outputs/czechlynx/phase5/`: historical PF-ERI v1 and internal pair-score outputs.
- `outputs/czechlynx/phase6/`: identity-holdout, calibrated risk, open-set, annotation package, and policy outputs.
- `outputs/czechlynx/phase7a/`: 1000-image visual-factor and risk-coverage outputs.
- `outputs/czechlynx/phase8/`: retrieval benchmark, query-level calibration/evaluation, and downstream sensitivity outputs.
- `outputs/czechlynx/phase9/`: no-training reranking outputs.
- `outputs/czechlynx/phase10_lite/`: matched metric-learning manifests and package audits.

## Label and Mapping Files

Treat these as sensitive and do not expose them publicly:

- `data/interim/czechlynx/*internal*.csv`
- `data/interim/czechlynx/*mapping*.csv`
- `data/labels/czechlynx/*working*.csv`
- any table containing raw paths, working identities, original IDs, coordinates, trap IDs, cell codes, or location fields.

## Backups

The backup CSVs under:

- `data/labels/czechlynx/backups/`
- `data/labels/czechlynx/_superseded_cleanup_backups/`

are noisy but small relative to the raw image data. They were kept because they are recovery points for annotation cleanup.

## Large Artifacts

Large local artifacts are mostly:

- raw CzechLynx images under `data/raw/`;
- review-package ZIPs under `outputs/`;
- descriptor embedding CSVs under `outputs/czechlynx/phase4/`;
- Colab export packages under `colab_exports/`.

Do not delete these unless the corresponding source, package, or output lineage is already backed up elsewhere.
