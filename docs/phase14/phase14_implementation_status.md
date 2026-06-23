# Phase 14 Implementation Status

Date: 2026-06-18

## Current Claim Boundary

Phase 14 can only claim UWIN bobcat field-readiness or review-readiness until individual labels or human-audited pair labels are verified.

The current repository does not yet contain verified UWIN bobcat local metadata, individual labels, or pair-audit labels. Therefore, UWIN bobcat must remain a planned same-genus urban stress context, not a completed validation dataset.

## Task 1: UWIN Bobcat Inventory

Status: complete for the current workspace.

Audit script:

```text
scripts/audit_phase14_uwin_bobcat_inventory.py
```

Outputs:

```text
outputs/phase14/uwin_bobcat_inventory.csv
outputs/phase14/uwin_bobcat_inventory_summary.json
```

Result:

```text
scanned_file_count: 291
candidate_file_count: 1
local_data_candidate_file_count: 0
literature_or_source_candidate_file_count: 1
verified_individual_labels: no
human_pair_audit_labels: no
```

Interpretation:

The single candidate is a literature/source JSON file containing a bobcat-related text hit. It is not UWIN bobcat metadata and cannot support UWIN bobcat review-readiness or identity-validation claims.

## Public Reporting Rule

Never expose exact site, trap, coordinate, raw image path, original image path, or internal path fields in public docs, blinded review files, or manuscript tables.

## Statistical Plan Status

Phase 14 distribution-shift analysis should use effect-size and uncertainty reporting, not p-value-only testing.

Planned statistics after UWIN bobcat metadata are available:

- standardized mean difference for shared numeric evidence variables;
- Kolmogorov-Smirnov distance for distributional separation;
- Wasserstein distance for interpretable distribution shift;
- bootstrap confidence intervals for mean differences and policy proportions;
- domain-classifier AUC as a diagnostic of context separability, not a causal urbanization claim.

## Task 2: Shared Cross-Context Evidence Table

Status: schema dry run complete.

Build script:

```text
scripts/build_phase14_cross_context_evidence_table.py
```

Audit script:

```text
scripts/audit_phase14_cross_context_evidence_table.py
```

Outputs:

```text
outputs/phase14/phase14_cross_context_evidence_table.csv
outputs/phase14/phase14_cross_context_evidence_table_build_audit.json
outputs/phase14/phase14_cross_context_evidence_table_audit.csv
```

Current result:

```text
row_count: 1000
contexts: wild_known_id
source_dataset: CzechLynx
czechlynx_only_dry_run: true
claim_boundary: schema_dry_run_only_until_uwin_local_data_available
audit_failures: 0
```

Interpretation:

The shared evidence schema is now implemented and safety-audited for CzechLynx. It is ready to accept a future UWIN bobcat metadata table through `--uwin-table`, but it does not yet support cross-context statistical claims because no local UWIN bobcat data are present.

## Task 2B: Public Urban/Peri-Urban Bobcat Image Source

Status: complete.

Source:

```text
Felidae Conservation Fund 2020-2025
https://lila.science/datasets/felidae-conservation-fund/
```

Role:

```text
public same-genus urban/peri-urban bobcat camera-trap stress dataset
```

License:

```text
Community Data License Agreement - Permissive 1.0
```

Preparation script:

```text
scripts/prepare_phase14_fcf_bobcat_manifest.py
```

Download script:

```text
scripts/download_phase14_fcf_bobcat_images.py
```

Local outputs:

```text
data/external/felidae_conservation_fund/metadata/felidae_conservation_fund_2020_2025.json
data/external/felidae_conservation_fund/manifests/fcf_bobcat_all_manifest.csv
data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_manifest.csv
data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_manifest_audit.json
data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_download_status.csv
data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_download_audit.json
data/external/felidae_conservation_fund/images/bobcat_3000/
```

Result:

```text
full_bobcat_image_count: 31,278
sample_bobcat_image_count: 3,000
downloaded_or_exists_count: 3,000
failed_count: 0
sample_location_count: 179
year_range: 2020-2025
local_image_size: 6.4 GB
```

Interpretation:

This gives Phase 14 a reproducible public urban/peri-urban bobcat camera-trap image set. It supports evidence-shift, review-readiness, and image-level PF-ERI stress testing. It does not provide individual identities and must not be used to claim urban bobcat Re-ID identity validation.

## Task 2C: FCF Bobcat Auto Prefeatures and Review Batch

Status: complete.

Machine prefeature script:

```text
scripts/build_phase14_fcf_bobcat_auto_prefeatures.py
```

Manifest repair script:

```text
scripts/repair_phase14_fcf_bobcat_manifest.py
```

Human-review batch script:

```text
scripts/prepare_phase14_fcf_bobcat_review_batch.py
```

Audit script:

```text
scripts/audit_phase14_fcf_bobcat_prefeatures.py
```

Outputs:

```text
data/external/felidae_conservation_fund/labels/fcf_bobcat_3000_auto_prefeatures.csv
data/external/felidae_conservation_fund/labels/fcf_bobcat_3000_auto_prefeatures_summary.json
data/external/felidae_conservation_fund/labels/fcf_bobcat_3000_auto_prefeatures_audit.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_400_human_review_manifest.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_400_human_review_manifest_audit.json
```

Current result:

```text
auto_prefeature_rows: 3,000
auto_prefeature_failures: 0
likely_review_ready: 1,378
review_limited: 911
likely_species_level_only: 703
defer_manual_check: 8
auto_night_ir_yes: 37
human_review_batch_rows: 400
human_review_batch_locations: 141
human_review_batch_night_ir_yes: 37
audit_failures: 0
```

Interpretation:

The 3,000-image FCF bobcat set is now fully machine-prelabeled for quality and evidence-prioritization features. These are not ground-truth labels. They are meant to help prioritize and accelerate human review. The 400-image review batch includes editable human-label columns for pattern visibility, side/flank visibility, body visibility, blur, occlusion, background complexity, human-modified background, review bucket, confidence, and notes.

## Task 2D: FCF Bobcat AI First-Pass Review Labels

Status: complete as an AI first pass; human audit still required.

Rubric:

```text
docs/phase14/fcf_bobcat_human_review_rubric.md
```

AI-fill script:

```text
scripts/fill_phase14_fcf_bobcat_review_labels.py
```

Priority script:

```text
scripts/prioritize_phase14_fcf_bobcat_manual_checks.py
```

Confidence-refinement script:

```text
scripts/refine_phase14_fcf_bobcat_review_confidence.py
```

Manual-review packaging script:

```text
scripts/package_phase14_fcf_bobcat_refined_manual_review.py
```

Audit script:

```text
scripts/audit_phase14_fcf_bobcat_ai_review_labels.py
```

Outputs:

```text
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_400_human_review_ai_filled.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_400_needs_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_120_priority_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_400_human_review_ai_filled_audit.json
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_120_priority_manual_check_audit.json
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_400_ai_review_labels_audit.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_ai_first_pass_review_labels.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_needs_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_300_priority_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_600_priority_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_1000_priority_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_ai_first_pass_review_labels_audit.json
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_300_priority_manual_check_audit.json
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_600_priority_manual_check_audit.json
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_1000_priority_manual_check_audit.json
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_ai_review_labels_audit.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_ai_refined_review_labels.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_refined_needs_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_confidence_promoted_stable_boundary.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_refined_300_priority_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_refined_600_priority_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_refined_1000_priority_manual_check.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_confidence_refinement_audit.json
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_3000_ai_refined_review_labels_audit.csv
data/external/felidae_conservation_fund/review_batches/refined_manual_review_1126_zip_batches/fcf_bobcat_1126_refined_manual_review_all.csv
data/external/felidae_conservation_fund/review_batches/refined_manual_review_1126_zip_batches/fcf_bobcat_1126_zip_batch_index.csv
data/external/felidae_conservation_fund/review_batches/refined_manual_review_1126_zip_batches/batch_01.zip ... batch_12.zip
data/external/felidae_conservation_fund/review_batches/refined_manual_review_1126_zip_batches/batch_01_manifest.csv ... batch_12_manifest.csv
data/external/felidae_conservation_fund/review_batches/refined_manual_review_1126_zip_batches/fcf_bobcat_1126_manual_review_package_audit.json
```

Current result:

```text
ai_filled_review_rows: 400
review_ready: 120
review_limited: 135
species_level_only: 137
uncertain: 8
human_review_confidence_high: 78
human_review_confidence_medium: 48
human_review_confidence_low: 274
needs_manual_check_rows: 274
priority_manual_check_rows: 120
audit_failures: 0
```

Full-set result:

```text
ai_filled_review_rows: 3,000
review_ready: 1,378
review_limited: 911
species_level_only: 703
uncertain: 8
human_review_confidence_high: 1,250
human_review_confidence_medium: 325
human_review_confidence_low: 1,425
needs_manual_check_rows: 1,425
priority_manual_check_rows_available: 300, 600, 1,000
night_ir_rows: 37
audit_failures: 0
```

Refined full-set result:

```text
ai_refined_review_rows: 3,000
review_bucket_changed_by_refinement: no
promoted_low_to_medium_confidence: 299
refined_human_review_confidence_high: 1,250
refined_human_review_confidence_medium: 624
refined_human_review_confidence_low: 1,126
refined_needs_manual_check_rows: 1,126
remaining_manual_check_major_reasons:
  weak_center_signal: 922
  possible_exposure_issue: 123
  night_ir: 37
  low_contrast: 29
  auto_defer: 8
  pattern_review_conflict: 6
  boundary_score_only: 1
audit_failures: 0
```

Manual-review package result:

```text
manual_review_rows_packaged: 1,126
zip_batch_size: 100
zip_count: 12
batch_01_to_batch_11_rows: 100 each
batch_12_rows: 26
missing_image_count: 0
package_contents: per-batch manifest plus renamed image files
```

Interpretation:

The 400-image review batch and the full 3,000-image FCF bobcat stress-test set now have complete first-pass labels for pattern visibility, side/flank visibility, body visibility, blur, occlusion, background complexity, human-modified background, review bucket, confidence, notes, and manual-check priority. These labels are deliberately conservative. A second confidence-refinement pass promoted only stable boundary-only cases from low to medium confidence; it did not alter the review buckets. The remaining low-confidence rows are dominated by weak center-signal, exposure, night/IR, low-contrast, and conflict cases, so they remain appropriate human-review targets. For the full set, the recommended human workflow is to audit the refined 300-row priority subset first, expand to refined 600 if time allows, and use the refined 1,000-row tier for a stronger calibration/audit set.

## Task 2E: CzechLynx 3000 Wild Known-ID Evidence Expansion

Status: complete as a mixed-confidence wild expansion set.

Purpose:

```text
match the 3000-image FCF bobcat stress-test scale while preserving CzechLynx known-ID validation value
```

Claim boundary:

```text
The 3000-image CzechLynx table contains 1000 existing human-labeled review rows plus 2000 AI first-pass expansion rows. It improves image-level evidence distribution coverage and future pair-candidate sampling power, but the 2000 new rows are not human ground truth until reviewed.
```

Scripts:

```text
scripts/prepare_phase14_czechlynx_3000_manifest.py
scripts/build_phase14_czechlynx_3000_auto_prefeatures.py
scripts/fill_phase14_czechlynx_3000_review_labels.py
scripts/refine_phase14_czechlynx_3000_review_confidence.py
scripts/refine_phase14_czechlynx_manual_review_with_pose.py
scripts/package_phase14_czechlynx_3000_manual_review.py
```

Outputs:

```text
data/interim/czechlynx/phase14/czechlynx_phase14_3000_manifest.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_manifest_audit.json
data/interim/czechlynx/phase14/czechlynx_phase14_3000_auto_prefeatures.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_auto_prefeatures_summary.json
data/interim/czechlynx/phase14/czechlynx_phase14_3000_review_labels.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_review_labels_audit.json
data/interim/czechlynx/phase14/czechlynx_phase14_3000_refined_review_labels.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_refined_needs_manual_check.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_confidence_promoted_stable_boundary.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_confidence_refinement_audit.json
data/interim/czechlynx/phase14/czechlynx_phase14_1341_manual_review_zip_batches/
data/interim/czechlynx/phase14/czechlynx_phase14_1341_pose_refined_review_labels.csv
data/interim/czechlynx/phase14/czechlynx_phase14_1341_pose_refined_still_needs_manual_check.csv
data/interim/czechlynx/phase14/czechlynx_phase14_1341_pose_refined_promoted.csv
data/interim/czechlynx/phase14/czechlynx_phase14_1341_pose_refinement_audit.json
data/interim/czechlynx/phase14/czechlynx_phase14_3000_pose_refined_review_labels.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_pose_refined_needs_manual_check.csv
data/interim/czechlynx/phase14/czechlynx_phase14_3000_pose_refined_review_labels_audit.json
data/interim/czechlynx/phase14/czechlynx_phase14_1182_pose_refined_manual_review_zip_batches_v2/
```

Manifest result:

```text
row_count: 3,000
existing_human_label_count: 1,000
ai_first_pass_needed_count: 2,000
unique_identity_count: 319
identities_with_at_least_2_images: 319
singleton_identity_count: 0
median_images_per_identity: 9
max_images_per_identity: 15
missing_review_images: 0
```

Automated prefeature result:

```text
prefeature_rows: 3,000
prefeature_failures: 0
likely_review_ready: 519
review_limited: 920
likely_species_level_only: 1,380
defer_manual_check: 181
auto_night_ir_yes: 140
```

Review-label result:

```text
review_label_rows: 3,000
existing_human_label_mapped: 1,000
ai_first_pass: 2,000
review_ready: 877
review_limited: 1,053
species_level_only: 938
uncertain: 132
first_pass_needs_manual_check: 1,502
stable_boundary_promoted_low_to_medium: 161
refined_needs_manual_check: 1,341
```

Manual-review package result:

```text
initial_manual_review_rows_packaged: 1,341
zip_batch_size: 100
zip_count: 14
batch_01_to_batch_13_rows: 100 each
batch_14_rows: 41
missing_image_count: 0
```

Pose-refined review result:

```text
pose_refined_low_confidence_rows: 1,341
pose_refined_count: 293
pose_promoted_no_manual_check: 159
pose_refined_remaining_manual_check: 1,182
final_pose_refined_3000_review_ready: 893
final_pose_refined_3000_review_limited: 1,235
final_pose_refined_3000_species_level_only: 771
final_pose_refined_3000_uncertain: 101
final_pose_refined_manual_zip_count: 12
final_pose_refined_batch_01_to_11_rows: 100 each
final_pose_refined_batch_12_rows: 82
```

Interpretation:

Expanding CzechLynx from 1000 to 3000 improves Phase 14 in three ways: it matches the bobcat stress-test scale for image-level wild/urban comparison, covers all 319 known identities with no singleton identities, and gives more candidate-pair material for later pair-level comparability and conflict sampling. The expansion should be used in layers: the existing 1000 rows remain the strongest human-labeled evidence base, while the additional 2000 rows are useful for distribution coverage and targeted human audit. Because CzechLynx has pose metadata, a pose-refinement pass can improve body visibility, side/flank visibility, and review bucket estimates for some low-confidence images. These pose-refined labels remain algorithmic labels, not human ground truth.

## Immediate Blocker

Task 3 can now proceed using CzechLynx versus the public FCF/LILA bobcat stress set. UWIN-specific claims still require UWIN bobcat metadata or annotation tables.

Acceptable next inputs:

- UWIN bobcat image manifest;
- UWIN bobcat species-detection metadata;
- UWIN bobcat annotation CSV;
- UWIN bobcat candidate-pair CSV;
- UWIN bobcat individual-ID table, if available;
- human-audited bobcat pair labels, if available.

## Next Implementation Choice

Recommended next technical step:

```text
Build Phase 14 FCF bobcat image-level evidence annotations or automated quality/visibility features, then rerun the shared-schema table with FCF bobcat rows.
```

The code now supports public FCF bobcat stress testing without pretending that UWIN validation has already been completed.

## Task 2F: 2x2 High-Confidence and Low-Evidence Evidence Sets

Status: complete for AI-assisted evidence routing.

Design rule:

```text
urban/peri-urban vs wild
high-confidence evidence vs low-evidence stress cases
```

New and updated scripts:

```text
scripts/prepare_phase14_2x2_bobcat_expansion_manifest.py
scripts/prepare_phase14_2x2_czechlynx_expansion_manifest.py
scripts/download_phase14_fcf_bobcat_images.py
scripts/build_phase14_2x2_evidence_sets.py
```

Important implementation note:

```text
download_phase14_fcf_bobcat_images.py now catches incomplete HTTP reads so a single truncated response is retried or recorded instead of crashing the full download run.
```

Expansion inputs:

```text
data/external/felidae_conservation_fund/manifests/fcf_bobcat_phase14_2x2_expansion_6000_manifest.csv
data/interim/czechlynx/phase14/czechlynx_phase14_2x2_expansion_6000_manifest.csv
```

Bobcat expansion download result:

```text
expansion_rows: 6,000
downloaded_or_exists_count: 6,000
failed_count: 0
overlap_image_id_with_existing_3000: 0
overlap_file_name_with_existing_3000: 0
download_size: 12.855 GB
```

Automated prefeature and refined-label outputs:

```text
data/external/felidae_conservation_fund/labels/fcf_bobcat_phase14_2x2_expansion_6000_auto_prefeatures.csv
data/external/felidae_conservation_fund/review_batches/fcf_bobcat_phase14_2x2_expansion_6000_ai_refined_review_labels.csv
data/interim/czechlynx/phase14/czechlynx_phase14_2x2_expansion_6000_auto_prefeatures.csv
data/interim/czechlynx/phase14/czechlynx_phase14_2x2_expansion_6000_refined_review_labels.csv
```

Quality caveat:

```text
7 of 6,000 bobcat expansion images remained unreadable after targeted redownload.
They are marked excluded and are not used in either high-confidence or stress sets.
```

Final 2x2 outputs:

```text
outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_combined_evidence_pool.csv
outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_bobcat_high_confidence_3000.csv
outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_bobcat_low_evidence_stress_3000.csv
outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_czechlynx_high_confidence_3000.csv
outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_czechlynx_low_evidence_stress_3000.csv
outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_evidence_sets_audit.json
```

Final set sizes:

```text
bobcat_high_confidence: 3,000
bobcat_low_evidence_stress: 3,000
czechlynx_high_confidence: 3,000
czechlynx_low_evidence_stress: 3,000
```

Final audit highlights:

```text
bobcat_pool_rows: 9,000
bobcat_training_eligible: 5,498
bobcat_stress_test_eligible: 3,495
bobcat_excluded_unreadable: 7
bobcat_high_locations: 153
bobcat_stress_locations: 127

czechlynx_pool_rows: 9,000
czechlynx_training_eligible: 3,476
czechlynx_stress_test_eligible: 5,524
czechlynx_high_identity_count: 310
czechlynx_high_min_images_per_identity: 2
czechlynx_stress_identity_count: 295
czechlynx_stress_min_images_per_identity: 2

bobcat_high_vs_stress_path_overlap: 0
czechlynx_high_vs_stress_path_overlap: 0
```

Interpretation:

The project now has a usable 2x2 evidence-risk data base. High-confidence sets support clean training, retrieval evaluation where labels exist, and wild/urban evidence comparison. Low-evidence stress sets preserve the difficult images as risk-control evidence rather than discarding them. These labels are still AI-assisted routing labels, not final human ground truth; a smaller targeted manual audit is still needed before manuscript-level label claims.

## Task 2G: Strict 2x2 Rescreening After Manual Audit

Status: complete for strict rule-derived candidate sets; 90% precision remains pending second manual validation.

Reason:

```text
The first 400-image manual audit showed systematic threshold bias.
The original 2x2 sets must not be treated as clean final experiment labels.
```

Strict rule document:

```text
docs/phase14/phase14_strict_2x2_rescreening_rules.md
```

New scripts:

```text
scripts/prepare_phase14_strict_czechlynx_expansion_manifest.py
scripts/build_phase14_strict_2x2_evidence_sets.py
scripts/package_phase14_strict_2x2_validation_audit_200.py
```

CzechLynx extra candidate expansion:

```text
data/interim/czechlynx/phase14/czechlynx_phase14_strict_2x2_extra_15000_manifest.csv
data/interim/czechlynx/phase14/czechlynx_phase14_strict_2x2_extra_15000_auto_prefeatures.csv
data/interim/czechlynx/phase14/czechlynx_phase14_strict_2x2_extra_15000_refined_review_labels.csv
```

Expansion audit:

```text
extra_czechlynx_rows: 15,000
overlap_with_current_czechlynx_pool: 0
missing_images: 0
identity_count: 300
```

Strict candidate pool:

```text
combined_rows: 33,000
bobcat_rows: 9,000
czechlynx_rows: 24,000
duplicate_paths: 0
bobcat_strict_high_candidates: 3,915
bobcat_strict_stress_candidates: 3,474
czechlynx_strict_high_candidates: 3,552
czechlynx_strict_stress_candidates: 16,686
```

Strict final outputs:

```text
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_combined_candidate_pool.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_bobcat_high_confidence_3000.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_bobcat_low_evidence_stress_3000.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_czechlynx_high_confidence_3000.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_czechlynx_low_evidence_stress_3000.csv
outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_evidence_sets_audit.json
```

Strict selected-set highlights:

```text
bobcat_high: 3,000 rows; body 76_100 = 3,000; pattern high = 3,000; blur none = 3,000; occlusion none = 3,000
bobcat_stress: 3,000 rows; pattern low/none = 3,000; body 0_25/26_50 = 3,000
czechlynx_high: 3,000 rows; identity_count = 273; min_images_per_identity = 2; body 76_100 = 3,000; pattern high/medium = 3,000
czechlynx_stress: 3,000 rows; identity_count = 316; min_images_per_identity = 2
high_vs_stress_path_overlap: 0 for both datasets
```

Validation package:

```text
outputs/phase14/phase14_strict_2x2_validation_audit_200/
```

Validation design:

```text
50 images per quadrant
200 images total
purpose: test whether strict rescreening approaches the >=90% correctness target
```

Interpretation:

The strict 2x2 sets supersede the earlier weak-label 2x2 sets for downstream modeling. They are much more conservative and better aligned with the first manual audit. However, they are still rule-derived candidates. Do not claim 90% correctness until the strict validation audit is reviewed.

## Task 2H: Detector-First AI-Assisted Evidence Admission

Status: complete for the first operational pass; use as AI-assisted routing, not final ground truth.

Reason for change:

The strict 2x2 validation audit showed that rule-only labels still had systematic errors. The most important failure was confusing animal/species visibility with individual Re-ID evidence. Therefore the high-confidence sets should not be treated as clean training labels just because rule-derived visual labels say `review_ready`.

Design target:

```text
AI auto-accept precision target: >=75%
remaining uncertain/high-risk cases: human review
```

New design document:

```text
docs/superpowers/specs/2026-06-19-detector-first-ai-assisted-evidence-admission-design.md
```

New scripts:

```text
scripts/build_phase14_detector_first_ai_admission.py
scripts/build_phase14_megadetector_evidence_gate.py
```

First-pass calibrated proxy admission:

```text
manual_training_rows: 600
manual_sources: 400 calibrated 2x2 audit + 200 strict validation audit
target_classes: high_confidence, low_evidence_stress, review_limited_middle, uncertain_excluded
candidate_pool_rows: 33,000
detector_source: local_cv_objectness_proxy_not_pretrained_detector
selected_threshold: 0.50
selected_threshold_cv_precision_before_extra_risk_gate: 0.812
selected_threshold_cv_coverage_before_extra_risk_gate: 0.665
risk_gated_cv_auto_precision: 0.872
risk_gated_cv_auto_coverage: 0.535
```

First-pass full candidate routing:

```text
ai_auto_high_confidence: 399
ai_auto_low_evidence_stress: 6,359
human_review_required: 26,235
excluded_unreadable: 7
```

Interpretation:

The proxy admission model meets the practical auto-accept precision target under cross-validation, but it is too conservative and weak for urban bobcat high-confidence admission. It automatically routes many low-evidence stress images, but it does not identify bobcat high-confidence evidence reliably. This is not enough for final clean 3000x4 training sets.

MegaDetector evidence gate:

```text
detector: PytorchWildlife MegaDetectorV5
device_used: cpu
mps_status: unavailable for MegaDetectorV5 weight loading because float64 tensors are not supported on MPS
gate_confidence_min: 0.55
gate_area_fraction_min: 0.035
gate_width_fraction_min: 0.18
gate_height_fraction_min: 0.10
edge_touch_allowed: no
aspect_ratio_range: 0.70-4.80
```

MegaDetector 300x2 high-candidate gate:

```text
input_rows: 600
urban_periurban_input_rows: 300
wild_input_rows: 300
urban_periurban_md_auto_high_confidence: 34
urban_periurban_human_review_required: 266
wild_md_auto_high_confidence: 214
wild_human_review_required: 86
total_md_auto_high_confidence: 248
total_human_review_required: 352
```

MegaDetector outputs:

```text
outputs/phase14/phase14_detector_first_admission/phase14_detector_first_candidate_scores.csv
outputs/phase14/phase14_detector_first_admission/phase14_detector_first_model_evaluation.json
outputs/phase14/phase14_detector_first_admission/phase14_detector_first_admission_summary.json
outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_high_gate_candidates.csv
outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_urban_bobcat_auto_high_candidates.csv
outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_wild_czechlynx_auto_high_candidates.csv
outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_high_gate_human_review_required.csv
outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_high_gate_summary.json
```

Interpretation:

The detector-first result is stronger than rule-only screening because it directly models the missing prerequisite: whether the animal occupies enough usable image area without severe edge/crop risk. The urban bobcat pass rate is much lower than the wild CzechLynx pass rate under the same gate. This should be treated as a real evidence-availability signal, not as a reason to relax thresholds.

Current recommendation:

Do not force 3,000 urban high-confidence images from the present candidate pool. Use the MegaDetector-gated pass set as a high-precision seed, ask for human review on a targeted subset, and use the remaining urban images as review-limited or low-evidence stress evidence. If a balanced 3,000 urban high-confidence set remains required, run MegaDetector on a larger LILA bobcat pool or use Colab/GPU for the detector stage.

## Task 2I: Colab MegaDetector Full High-Candidate Screening Package

Status: ready for Colab execution.

Purpose:

Run MegaDetector on all current Phase 14 strict high-confidence candidates for both bobcat and CzechLynx, then select up to 3,000 detector-gated high-confidence images per dataset. If fewer than 3,000 pass, the final selection must keep the smaller number and report `below_target_do_not_force`.

Candidate counts:

```text
bobcat_strict_high_candidates: 3,915
czechlynx_strict_high_candidates: 3,552
total_colab_megadetector_candidates: 7,467
```

New scripts:

```text
scripts/prepare_phase14_colab_megadetector_package.py
colab/phase14_megadetector_selection/run_phase14_megadetector_colab.py
scripts/finalize_phase14_colab_megadetector_selection.py
```

Package outputs:

```text
outputs/phase14/phase14_colab_megadetector_package/phase14_colab_megadetector_manifest.csv
outputs/phase14/phase14_colab_megadetector_package/phase14_colab_megadetector_packaged_manifest.csv
outputs/phase14/phase14_colab_megadetector_package/phase14_colab_megadetector_zip_index.csv
outputs/phase14/phase14_colab_megadetector_package/run_phase14_megadetector_colab.py
outputs/phase14/phase14_colab_megadetector_package/phase14_md_czechlynx_images_part_01.zip
outputs/phase14/phase14_colab_megadetector_package/phase14_md_czechlynx_images_part_02.zip
outputs/phase14/phase14_colab_megadetector_package/phase14_md_czechlynx_images_part_03.zip
outputs/phase14/phase14_colab_megadetector_package/phase14_md_czechlynx_images_part_04.zip
outputs/phase14/phase14_colab_megadetector_package/phase14_colab_megadetector_package_summary.json
```

Packaging strategy:

```text
bobcat: not zipped locally; Colab downloads from LILA download_url in the manifest
czechlynx: zipped locally because images are local project files
czechlynx_zip_count: 4
czechlynx_zip_total_size_bytes: 834,556,131
```

Colab workflow:

```text
1. Upload manifest, CzechLynx zip files, and run_phase14_megadetector_colab.py to Google Drive.
2. Unzip CzechLynx images in the Drive folder.
3. Install PytorchWildlife dependencies.
4. Run run_phase14_megadetector_colab.py with GPU device cuda.
5. Download phase14_colab_megadetector_detections.csv.
6. Place it under outputs/phase14/phase14_colab_megadetector_package/colab_returned/.
7. Run scripts/finalize_phase14_colab_megadetector_selection.py locally.
```

Finalization rule:

The local finalization script uses the fixed MegaDetector gate:

```text
md_best_confidence >= 0.55
md_area_fraction >= 0.035
md_width_fraction >= 0.18
md_height_fraction >= 0.10
0.70 <= md_aspect_ratio <= 4.80
edge_touch_allowed = no
```

It selects at most 3,000 rows per dataset and never fills missing quota with failed or borderline images.

## Task 2J: Colab MegaDetector Low-Evidence Stress Screening Package

Status: ready for Colab execution.

Purpose:

Run MegaDetector on the current strict low-evidence stress candidates for bobcat and CzechLynx, then remove detector conflicts from the stress sets. A detector conflict means a row originally routed to low-evidence stress actually has a confident, sufficiently large, non-edge animal detection under the same fixed gate used for high-confidence selection.

Candidate counts:

```text
bobcat_low_evidence_candidates: 3,000
czechlynx_low_evidence_candidates: 3,000
total_colab_low_evidence_candidates: 6,000
```

New scripts:

```text
scripts/prepare_phase14_colab_megadetector_low_evidence_package.py
scripts/finalize_phase14_colab_megadetector_low_evidence_selection.py
```

Package outputs:

```text
outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_colab_megadetector_manifest.csv
outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_colab_megadetector_packaged_manifest.csv
outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_colab_megadetector_zip_index.csv
outputs/phase14/phase14_colab_megadetector_low_evidence_package/run_phase14_megadetector_colab.py
outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_md_low_czechlynx_images_part_01.zip
outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_md_low_czechlynx_images_part_02.zip
outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_md_low_czechlynx_images_part_03.zip
outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_colab_megadetector_low_evidence_package_summary.json
```

Packaging strategy:

```text
bobcat: not zipped locally; Colab downloads from LILA download_url in the manifest
czechlynx: zipped locally because images are local project files
czechlynx_low_zip_count: 3
czechlynx_low_zip_total_size_bytes: 655,725,917
```

Finalization rule:

The local low-evidence finalization script uses the same fixed MegaDetector gate as Task 2I:

```text
md_best_confidence >= 0.55
md_area_fraction >= 0.035
md_width_fraction >= 0.18
md_height_fraction >= 0.10
0.70 <= md_aspect_ratio <= 4.80
edge_touch_allowed = no
```

Rows that pass this gate are not trusted as low-evidence stress rows. They are routed to:

```text
phase14_low_evidence_rejected_high_conflict_or_review_required.csv
```

Rows that fail this gate remain eligible for the detector-validated low-evidence stress set. If fewer than 3,000 remain for either dataset, the script reports `below_target_after_conflict_removal_do_not_force` instead of filling quota with borderline images.
