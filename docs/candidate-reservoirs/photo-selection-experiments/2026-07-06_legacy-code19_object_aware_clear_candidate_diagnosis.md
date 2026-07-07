# legacy-code19 Object-Aware Clear Candidate Diagnosis

Date: 2026-07-06

## Trigger

Human review found that image-level quality thresholds still admitted many
motion-blurred animals and animals occupying less than 20% of the frame. The
failure mode is clear: whole-image sharpness can be high when the background is
sharp, even if the animal itself is small or moving.

## Fix

The filter was changed from whole-image quality to object-aware quality:

1. Run YOLO (`yolo11n.pt`) on candidate images.
2. Keep only rows with a large animal-like detection box.
3. Require animal box area `>=20%` of the image.
4. Compute sharpness, edge strength, contrast, brightness, color, and entropy on
   the animal crop, not the whole image.
5. Keep only rows whose animal crop passes the strict clear-evidence gate.

## Fast Object-Aware Run

Because full YOLO over all images is slow, the first stable run processed:

- first 1,000 `bobcat_wild_camera_trap` candidates;
- first 1,000 `bobcat_urban_heterogeneous` candidates;
- all 822 current `lynx_external_heterogeneous_supplement` review candidates.

Results:

- `bobcat_wild_camera_trap`: 8 keep / 1,000 scored.
- `bobcat_urban_heterogeneous`: 141 keep / 1,000 scored.
- `lynx_external_heterogeneous_supplement`: 22 keep / 822 scored.

The combined validation sample contains 130 object-aware keep rows:

`outputs/legacy-code19/legacy-code19_object_aware_clear_candidates/legacy-code19_object_aware_validation_sample_combined.csv`

Review app:

`http://127.0.0.1:8504`

## Interpretation

The low keep rate is scientifically meaningful. It confirms that the earlier
candidate pools were dominated by animals that are too small, too blurred, too
low contrast, night/IR, or not reliably detected as large animal subjects.

The project should not claim 3,000 high-quality images from these pools. The
correct next step is to validate the 130 object-aware keep rows, then continue
targeted acquisition or object-aware scanning in batches until no additional
usable images are found.
