# legacy-code19 Strict Top-3000 Validation Protocol

Date: 2026-07-06

## Correct Selection Logic

legacy-code19 photo selection must not send the full candidate pool directly to human
review. The workflow is:

1. Split candidates by planned modeling cell:
   - `bobcat_wild_camera_trap`
   - `bobcat_urban_heterogeneous`
   - `lynx_external_heterogeneous_supplement`
2. Within each cell, apply the strict automatic prefilter.
3. Build a top-3000 candidate set per cell when enough strict candidates exist.
4. Draw a 100-image validation sample from each top-3000 candidate set.
5. Human review the 100-image sample.
6. Only if the sample CLEAR rate is high enough can the top-3000 candidate set
   be promoted to freeze candidate status.

## Strict Gate Used

Rows must satisfy:

- `legacy-code19_prefilter_decision=review`
- `technical_quality_rule=technical_strict_pass`
- `legacy-code19_manual_review_priority in {high, cautious}`
- no detector `<20%` subject-area failure
- no severe proxy failure for small image, weak edges, low sharpness, low
  contrast, scat/track/dead/sign text, or missing technical evidence

Detector area is used only when available. If no detector area is available,
the row remains a candidate only and must pass human area review.

## Validation Sample Design

The 100-image sample is not simply the first 100 images. It spans the top-3000
candidate set:

- 40 from the top strict segment;
- 30 from the middle segment;
- 30 from the boundary segment.

This tests whether the whole top-3000 set is stable, not only whether the best
few images look good.

## Current Results

- `bobcat_wild_camera_trap`: 3,000 / 3,000 candidate rows available.
- `bobcat_urban_heterogeneous`: 3,000 / 3,000 candidate rows available.
- `lynx_external_heterogeneous_supplement`: 1,264 / 3,000 candidate rows
  available under the strict gate; shortfall = 1,736.

This shortfall should not be filled by lowering the clarity standard. The next
step is either to collect more lynx external candidates or keep this cell as an
auxiliary supplement rather than a 3000-image balanced cell.

## Review App

The combined 300-image validation sample is here:

`outputs/legacy-code19/legacy-code19_strict_top3000_validation/legacy-code19_strict_top3000_validation_sample300_combined.csv`

Review working file:

`outputs/legacy-code19/legacy-code19_strict_top3000_validation_review/legacy-code19_strict_photo_review_working.csv`

Run command:

```bash
legacy-code19_PHOTO_REVIEW_SOURCE_CSV=outputs/legacy-code19/legacy-code19_strict_top3000_validation/legacy-code19_strict_top3000_validation_sample300_combined.csv \
legacy-code19_PHOTO_REVIEW_OUTPUT_DIR=outputs/legacy-code19/legacy-code19_strict_top3000_validation_review \
/tmp/felid_streamlit_venv/bin/python -m streamlit run scripts/streamlit_legacy-code19_strict_photo_review_app.py --server.port 8502 --server.address 127.0.0.1
```
