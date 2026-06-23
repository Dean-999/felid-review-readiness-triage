# Phase 14 LILA MegaDetector Prefilter And Cleanup Log

Date: 2026-06-20

## Space Cleanup

The workspace was close to full before cleanup:

```text
available_space_before: 4.9G
project_size_before: 39G
```

Removed only regeneratable intermediate packages and old review archives that were not referenced by the current Phase 14 final high/low CSV files:

```text
outputs/phase14/phase14_colab_megadetector_package
outputs/phase14/phase14_colab_megadetector_low_evidence_package
outputs/phase14/phase14_2x2_manual_audit_400
outputs/phase14/phase14_strict_2x2_validation_audit_200
outputs/phase14/phase14_strict_2x2_validation_audit_200.zip
data/external/felidae_conservation_fund/review_batches/refined_manual_review_1126_zip_batches
data/interim/czechlynx/phase14/czechlynx_phase14_1341_manual_review_zip_batches
data/interim/czechlynx/phase14/czechlynx_phase14_1182_pose_refined_manual_review_zip_batches
outputs/czechlynx/phase6/archive/flawed_unique_500_selection_20260613
```

Post-cleanup state before new downloads:

```text
available_space_after_cleanup: 9.9G
project_size_after_cleanup: 34G
```

Core current result files were preserved:

```text
outputs/phase14/phase14_colab_megadetector_final_selection/phase14_bobcat_megadetector_high_confidence_final.csv
outputs/phase14/phase14_colab_megadetector_final_selection/phase14_czechlynx_megadetector_high_confidence_final.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_bobcat_low_evidence_stress_3000.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_czechlynx_low_evidence_stress_3000.csv
```

## LILA Source Index

Downloaded the official LILA camera-trap dataset index:

```text
sources/lila/lila_camera_trap_datasets.csv
sources/lila/phase14_candidate_lila_sources.csv
```

Candidate sources with MegaDetector/RDE-style results include:

```text
Felidae Conservation Fund 2020-2025
NACTI
Idaho Camera Traps
Caltech Camera Traps
Oregon Critters
WSU Lynx
Seattle(ish) Camera Traps
AMMonitor Camera Traps
```

## FCF Official MegaDetector Prefilter

Downloaded the FCF official filtered MegaDetector result:

```text
sources/lila/md_results/felidae_conservation_fund_mdv5a_filtered.json.zip
```

This file is small relative to images:

```text
zip_size: 22M
md_images_total: 357,934
```

Joined the detector results with the full local FCF bobcat manifest:

```text
bobcat_manifest_rows: 31,278
md_missing_for_bobcat_rows: 0
```

Applied the same high-evidence geometry gate:

```text
md_best_confidence >= 0.55
md_area_fraction >= 0.035
md_width_fraction >= 0.18
md_height_fraction >= 0.10
0.70 <= md_aspect_ratio <= 4.80
edge_touch_allowed = no
```

Result:

```text
md_high_evidence_passed_bobcat_rows: 6,412
passed_already_in_local_bobcat_roots: 1,686
passed_not_in_local_bobcat_roots: 4,726
```

This shows that FCF can still support bobcat high-confidence top-up if images are selected by detector metadata before download.

## Bobcat Top-Up Download

Selected the top 2,800 not-yet-local bobcat candidates by detector score:

```text
data/external/felidae_conservation_fund/manifests/fcf_bobcat_md_prefilter_top2800_manifest.csv
```

Downloaded to:

```text
data/external/felidae_conservation_fund/images/bobcat_md_prefilter_top2800/
```

Download audit:

```text
downloaded_or_exists_count: 2,800
failed_count: 0
download_size: 4.416G
available_space_after_download: 8.0G
```

The downloaded top-up set has strong detector geometry:

```text
min_md_best_confidence: 0.6920
min_md_area_fraction: 0.0501
min_md_width_fraction: 0.1900
min_md_height_fraction: 0.1230
min_md_aspect_ratio: 0.7003
```

## Bobcat 3000 Detector-First Working Final Label Set

Created a 3,000-row bobcat high-confidence detector-first table:

```text
outputs/phase14/phase14_expanded_high_confidence_candidates/phase14_bobcat_high_confidence_candidate_3000_detector_first.csv
outputs/phase14/phase14_expanded_high_confidence_candidates/phase14_bobcat_high_confidence_candidate_3000_detector_first_summary.json
```

Composition:

```text
existing_colab_final_rows: 656
official_md_prefilter_topup_rows: 2,344
combined_rows: 3,000
local_exists_count: 3,000
duplicate_image_id_count: 0
```

Promoted this detector-first table to the current Phase 14 working final high-confidence label table:

```text
outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_high_confidence_3000_working_final_labels.csv
outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_high_confidence_3000_working_final_labels_summary.json
```

Working label assignment:

```text
human_review_bucket: review_ready
human_review_confidence: high
human_training_eligible: yes
human_label_status: working_final
human_label_provenance: detector_first_high_confidence_promoted_by_project_note
```

Boundary:

This is now the operational working final high-confidence label set for current Phase 14 modeling. It should be treated as final inside the current project workflow. The provenance field is intentionally retained so later manual review can overwrite or audit the detector-first promotion without losing the source trail.

## Current Remaining Gap

Bobcat high-confidence target is now operationally filled:

```text
urban_bobcat_high_confidence_working_final_3000: ready
```

CzechLynx high-confidence remains below 3,000:

```text
current_czechlynx_detector_high_confidence: 2,220
remaining_needed_for_3000: 780
```

CzechLynx cannot use the LILA MD result shortcut because it is a local dataset. The next step should prepare an additional CzechLynx candidate package from unused local images and run the same detector gate through Colab or a local detector.

## CzechLynx High-Confidence Top-Up Cloud Package

Prepared a detector-first CzechLynx high-confidence top-up candidate pool from unused wild middle-reviewable images. The current 3,552 strict high candidates had already been screened by MegaDetector, so the top-up pool intentionally excludes:

```text
outputs/phase14/phase14_colab_megadetector_final_selection/phase14_colab_megadetector_all_gated_candidates.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_czechlynx_low_evidence_stress_3000.csv
```

Candidate selection:

```text
source_pool: wild CzechLynx middle_reviewable unused images
candidate_rows: 2,500
selection_score: auto_evidence_score, auto_quality_score, blur_laplacian_var, contrast_std
```

Package:

```text
outputs/phase14/phase14_czechlynx_high_topup_colab_package/
```

Files:

```text
phase14_colab_megadetector_manifest.csv
phase14_czechlynx_high_topup_images_part_01.zip
phase14_czechlynx_high_topup_images_part_02.zip
phase14_czechlynx_high_topup_images_part_03.zip
run_phase14_megadetector_colab.py
```

Package audit:

```text
candidate_rows: 2,500
zip_count: 3
zip_total_size_bytes: 539,905,049
duplicate_candidate_ids: 0
duplicate_source_paths: 0
source_exists: 2,500
zip_integrity: pass
```

The local CPU detector smoke test was stopped because cloud GPU is the correct execution target for this batch. Finalization should use:

```text
scripts/finalize_phase14_czechlynx_high_working_final.py
```

after placing the returned detector CSV at:

```text
outputs/phase14/phase14_czechlynx_high_topup/phase14_czechlynx_high_topup_megadetector_detections.csv
```
