# legacy-code19 Bobcat Wild Object-Aware Full Strict Result

Date: 2026-07-06

## Purpose

Run the object-aware strict filter on the full available `bobcat_wild_camera_trap`
review candidate set. The goal is no longer to reach 3,000 images. The goal is
to keep only images where the animal itself is large enough and clear enough.

## Method

Input:

- `bobcat_wild_camera_trap` candidates that passed the broad image-level review
  gate.
- Scored rows: 3,660.

Object-aware gate:

- YOLO animal-like detection required.
- animal box area must be `>=20%` of image.
- animal crop must pass sharpness, edge, contrast, brightness, color, and
  entropy checks.
- final inclusion still requires human CLEAR review.

## Result

Kept rows: 16.

Rejected rows: 3,644.

Major rejection reasons:

- `animal_crop_motion_or_soft_laplacian_lt_1400`: 2,087.
- `animal_area_lt_0_20`: 2,058.
- `animal_crop_weak_edges_lt_38`: 1,928.
- `animal_box_dimension_too_small`: 1,683.
- `animal_crop_low_contrast_lt_48`: 1,670.
- `no_yolo_animal_box`: 1,391.
- `animal_crop_dimension_lt_260`: 875.
- `animal_crop_megapixels_lt_0_10`: 834.
- `animal_crop_low_color_or_ir`: 623.

## Outputs

- `outputs/legacy-code19/legacy-code19_object_aware_bobcat_wild_full_strict/bobcat_wild_camera_trap_object_aware_all_scored.csv`
- `outputs/legacy-code19/legacy-code19_object_aware_bobcat_wild_full_strict/bobcat_wild_camera_trap_object_aware_keep_candidates.csv`
- `outputs/legacy-code19/legacy-code19_object_aware_bobcat_wild_full_strict/legacy-code19_object_aware_audit.json`

Review app:

`http://127.0.0.1:8505`

## Interpretation

The current Bobcat wild camera-trap pool is not suitable for producing a large
high-clarity visual-comparison set under the current standard. Most candidates
fail because the animal is too small, moving/soft, low contrast, or not detected
as a sufficiently large animal subject.

Do not lower the standard to reach a target count. Use the 16 rows as candidate
keeps, review them manually, and treat the remaining shortfall as a data-source
problem.
