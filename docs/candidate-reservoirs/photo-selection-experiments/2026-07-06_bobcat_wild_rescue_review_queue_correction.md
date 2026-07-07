# legacy-code19 Bobcat Wild Rescue Review Queue Correction

Date: 2026-07-06

## Correction

The previous statement that Bobcat wild had only 16 usable images was not a
valid final conclusion. That number came from an over-strict object-aware filter
after an ultra-strict prefilter. It was useful as a diagnostic, but it was not a
scientifically acceptable estimate of usable image supply.

Problems with that estimate:

- it scanned only 3,660 broad-gated rows, not all 12,204 downloaded Bobcat wild
  images;
- YOLO is not a reliable final bobcat detector in camera-trap imagery;
- animal-crop Laplacian/edge metrics can still be fooled;
- automatic filters should rank review priority, not replace human calibration.

## Restored Selection Logic

The project returns to the original working logic:

1. keep the full Bobcat wild reservoir;
2. use multiple weak signals only to rank and stratify review priority;
3. sample across source datasets and score tiers;
4. use human CLEAR/REJECT decisions to decide which pockets can be expanded;
5. never lower the visual standard merely to hit a target count.

## New Full Reservoir

Input downloaded rows:

- `bobcat_wild_camera_trap`: 12,204 images.

Source counts:

- `Caltech Camera Traps`: 4,979.
- `Felidae Conservation Fund 2020-2025`: 4,311.
- `WSU Lynx`: 2,914.

Rescue priority tiers:

- `tier1_high_priority_review`: 195.
- `tier2_plausible_review`: 962.
- `tier3_rescue_review`: 1,287.
- `tier4_low_priority`: 9,760.

These are review-priority tiers, not final acceptance labels.

## Review Sample

The calibration sample contains 598 images, stratified across source datasets
and score tiers.

Review app:

`http://127.0.0.1:8506`

Working file:

`outputs/legacy-code19/legacy-code19_bobcat_wild_rescue_review/legacy-code19_strict_photo_review_working.csv`

Source files:

- `outputs/legacy-code19/legacy-code19_bobcat_wild_rescue_review_queue/bobcat_wild_full_rescue_ranked_queue.csv`
- `outputs/legacy-code19/legacy-code19_bobcat_wild_rescue_review_queue/bobcat_wild_full_rescue_review_sample600.csv`

## Interpretation

The next valid claim depends on the human review rate in this sample. If tier1
and tier2 have high CLEAR rates, expand those pockets. If they remain poor,
Bobcat wild must be sourced differently rather than rescued by threshold tuning.
