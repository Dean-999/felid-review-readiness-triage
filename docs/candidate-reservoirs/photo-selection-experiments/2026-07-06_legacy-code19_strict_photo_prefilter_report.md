# legacy-code19 Strict Photo Prefilter Report

Date: 2026-07-06

## Purpose

Build the first strict legacy-code19 visual review queue from downloaded candidate pools.
This is a prefilter and review-routing artifact, not a final 3000-image freeze.

## Hard Visual Standard

A photo can enter the final modeling set only if human review confirms:

- the animal itself is clear, not merely the background;
- no severe motion blur, compression artifact, or mosaic-like degradation;
- the subject is sufficiently large;
- body and marking evidence are complete enough for pair-level comparison;
- the evidence is not scat, track, dead animal, sign, label, or other non-living proxy;
- the animal is not severely partial or occluded.

Subject-area rule:

- `<20%`: reject when detector or human review can establish this.
- `20-30%`: cautious retain only when the animal is genuinely sharp and body evidence is complete.
- `>=30%`: eligible for stronger priority if technical quality is also high.
- no detector box: do not auto-certify area; require manual area review.

## Outputs

- `outputs/legacy-code19/legacy-code19_strict_photo_prefilter/legacy-code19_strict_photo_prefilter_audit.json`
- `outputs/legacy-code19/legacy-code19_strict_photo_prefilter/legacy-code19_strict_photo_review_queue.csv`
- `outputs/legacy-code19/legacy-code19_strict_photo_prefilter/bobcat_wild_camera_trap_strict_photo_prefilter.csv`
- `outputs/legacy-code19/legacy-code19_strict_photo_prefilter/bobcat_urban_heterogeneous_strict_photo_prefilter.csv`
- `outputs/legacy-code19/legacy-code19_strict_photo_prefilter/lynx_external_heterogeneous_supplement_strict_photo_prefilter.csv`
- `outputs/legacy-code19/legacy-code19_strict_photo_prefilter/*_strict_photo_review_queue_top6000.csv`

Review app:

```bash
/tmp/felid_streamlit_venv/bin/streamlit run scripts/streamlit_legacy-code19_strict_photo_review_app.py
```

## Current Counts

Combined review queue: 19,578 images.

Per pool:

- `bobcat_wild_camera_trap`: 10,297 reviewable images; 20 high, 10,277 cautious.
- `bobcat_urban_heterogeneous`: 7,364 reviewable images; all cautious because reliable subject-area boxes are unavailable.
- `lynx_external_heterogeneous_supplement`: 1,917 reviewable images; all cautious because reliable subject-area boxes are unavailable.

Area evidence:

- detector `>=30%`: 20 images.
- detector `20-30%`: 193 images.
- no detector area available: 19,365 images.

## Interpretation

The queue is intentionally strict about what it can claim automatically. Most
iNaturalist/GBIF-style images lack reliable bounding boxes, so the script does
not claim that the animal occupies 20%, 30%, or 40% of the image. Those images
are ranked by technical clarity proxies and routed to human review.

Final legacy-code19 data freeze must use the Streamlit `clear` labels, not the
automatic `review` decision alone.
