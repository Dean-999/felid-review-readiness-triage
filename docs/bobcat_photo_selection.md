# Bobcat Photo Selection

This is the single current document for Bobcat photo selection.

Older `legacy-code17*` queues are historical inputs and diagnostics. Do not create
more lettered photo-selection phases just to try another rule. New work should
write into:

```text
outputs/bobcat_photo_selection/
```

## Current Hard Standard

A photo may enter the final Bobcat 3000 only if all are true:

- human-confirmed CLEAR;
- animal body is the dominant subject;
- detector/segmentation proxy estimates animal area at least 40% of the full
  image;
- image is sharp enough for comparison;
- no mosaic/compression blur;
- no scat, track, dead specimen, sign-only, or species-presence-only evidence.

If a rule-derived or detector-derived gate disagrees with human judgment, human
judgment wins.

Working interpretation after the first successful detector review:

- `>=40%` animal area is the ideal high-confidence standard.
- `20%-30%` animal area is an expansion band for review candidates only. It may
  be used to find enough photos, but it does not automatically become final.
- Photos in the expansion band must still be human-confirmed as clear,
  non-mosaic, non-dead, non-scat/track, and individually comparable.

## Current Prototype

```text
python3 scripts/prototypes/prototype_bobcat_photo_selection_subject40_gate.py
```

The prototype uses a general YOLO detector to test whether a subject-area gate
can remove the failure mode where an image is sharp but the bobcat is too small
or not comparable.

## Boundary

Detector pass is not final truth. It creates a smaller review queue. Final
inclusion still requires human CLEAR.

## Prototype Result 2026-06-30

Input:

```text
outputs/legacy-code17/legacy-code17m_inat_annotation_aware_strict_clarity_queue/legacy-code17m_inat_annotation_aware_strict_clarity_review_queue_5000.csv
```

Small test:

- candidates tested: 300;
- detector-gated pass rows: 13;
- pass rate: 4.3%;
- main rejection mode: no accepted animal detection or animal area below 40%;
- output queue:
  `outputs/bobcat_photo_selection/bobcat_photo_selection_subject40_review_queue.csv`.

Interpretation:

The strict 40% subject-area standard is much stronger than the previous
metadata/pixel-proxy queues. It correctly removes most photos that are sharp but
not comparable because the animal is too small. The next production step should
optimize detector batching and run this gate over a much larger candidate pool.

## Expansion Test 2026-06-30

User review of the 40% detector queue was positive: nearly all passed human
inspection except a small number of incomplete-body cases. Therefore, the next
test lowered the subject-area band to 20%-30% while keeping sharpness,
contrast, detector confidence, and human CLEAR as required safeguards.

Inputs:

```text
outputs/legacy-code17/legacy-code17l_multisource_strict_clarity_queue/legacy-code17l_multisource_bobcat_pre_score_candidates.csv
outputs/legacy-code17/legacy-code17m_inat_annotation_aware_strict_clarity_queue/legacy-code17m_inat_annotation_aware_strict_clarity_review_queue_5000.csv
```

Key outputs:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_subject20_multisource_interim_4k_review_queue.csv
outputs/bobcat_photo_selection/bobcat_photo_selection_subject20_multisource_interim_4k_audit.json
outputs/bobcat_photo_selection/bobcat_photo_selection_subject30_multisource_2k_review_queue.csv
outputs/bobcat_photo_selection/bobcat_photo_selection_detector_scores.csv
```

Observed counts:

- 2,000-candidate multisource test:
  - 30% area / 38% width / 30% height: 136 candidates;
  - 20% area / 30% width / 23% height: 218 candidates.
- 4,125-candidate interim cache:
  - 20% area / 30% width / 23% height: 414 candidates;
  - 15% area / 24% width / 20% height: 518 candidates;
  - 10% area / 18% width / 16% height: 655 candidates.

Interpretation:

The 20%-30% expansion band increases yield without removing the sharpness and
contrast safeguards, but it probably does not reach 3,000 final photos by
itself. A simple linear extrapolation from the 4,125-candidate interim cache
suggests that full multisource detection may produce roughly 1,500-1,700
20%-band review candidates before human rejection. Even a 10% subject-area band
may still be short of 3,000 after human rejection and would be riskier for
individual comparability.

Decision:

Use the 20% multisource queue as the next human-review batch, but do not treat
lowering the area threshold as the main solution. The main solution should be
candidate-source optimization: find or construct pools where the animal is
already likely to be large, complete-body, clear, and comparable before detector
screening.

Current review app:

```text
http://127.0.0.1:8512
```

The 8512 app uses an independent working CSV:

```text
outputs/bobcat_photo_selection/reviews/subject20_multisource_interim_4k/bobcat_photo_selection_review_working.csv
```

Implementation note:

The detector cache is shared across threshold simulations. Do not run multiple
threshold simulations in parallel because they all write
`bobcat_photo_selection_detector_scores.csv`. The prototype now writes CSVs via
atomic replacement and parses numeric fields defensively. A corrupted cache
backup from the parallel write incident is retained here:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_detector_scores_corrupt_backup_20260630_233107.csv
```

Review rule for this queue:

- CLEAR only if the photo is actually sharp, non-mosaic, and comparable.
- Reject dead/specimen, scat, track, sign-only, incomplete-body, tiny subject,
  bad angle, or severe occlusion.
- Treat detector class (`cat`, `dog`, `bear`) as a rough subject detector only,
  not as species truth.

## Human Review Result 2026-07-01

Reviewed queue:

```text
outputs/bobcat_photo_selection/reviews/subject20_multisource_interim_4k/bobcat_photo_selection_review_working.csv
```

Result:

- rows reviewed: 414 / 414;
- human CLEAR: 263;
- human NOT CLEAR: 151;
- CLEAR rate: 63.5%.

Interpretation:

The 20% detector gate is now good enough as a human-review queue. The main
remaining rejection mode is not catastrophic blur, mosaic, scat, tracks, or
dead/specimen material. The main remaining rejection mode is body completeness
and comparability, especially partial-body cases. Therefore the next filter
improvement should target complete-body/comparable-pose signals, not stricter
generic sharpness.

legacy-code17n seed update:

```text
scripts/build_legacy-code17n_bobcat_final3000_seed_from_human_clear.py
outputs/legacy-code17/legacy-code17n_bobcat_final3000_seed/legacy-code17n_bobcat_final3000_human_clear_seed_manifest.csv
```

After adding this review source to the legacy-code17n seed builder:

- raw positive rows across all human-review sources: 635;
- deduplicated human-confirmed clear photos: 400;
- remaining clear photos needed for final 3000: 2600.

Next strategy:

Run a larger 20% detector-gated batch, but prioritize candidates likely to have
complete body and comparable posture. Lowering the subject-area threshold below
20% should not be the default next move because it increases partial-body and
low-comparability risk.

## Full Multisource Detector Run 2026-07-01

Question:

Can the full multisource candidate pool produce all suitable Bobcat review
candidates, while pushing partial-body or occlusion-risk photos behind more
complete-body candidates?

Command shape:

```text
python scripts/prototypes/prototype_bobcat_photo_selection_subject40_gate.py \
  --candidates outputs/legacy-code17/legacy-code17l_multisource_strict_clarity_queue/legacy-code17l_multisource_bobcat_pre_score_candidates.csv \
  --limit 15745 \
  --target-count 20000 \
  --gallery-count 500 \
  --min-subject-area 0.20 \
  --min-subject-width 0.30 \
  --min-subject-height 0.23 \
  --detector-conf 0.25 \
  --image-size 640 \
  --label subject20_multisource_full_complete_priority \
  --download-workers 8 \
  --download-batch-size 24 \
  --batch-size 8 \
  --timeout 3 \
  --exclude-seed
```

Outputs:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_subject20_multisource_full_complete_priority_review_queue.csv
outputs/bobcat_photo_selection/bobcat_photo_selection_subject20_multisource_full_complete_priority_audit.json
outputs/bobcat_photo_selection/bobcat_photo_selection_subject20_multisource_full_complete_priority_gallery.html
outputs/bobcat_photo_selection/reviews/subject20_multisource_full_complete_priority/
```

Result:

- candidate rows considered: 15,745;
- detector/scored rows: 15,745;
- review candidates after excluding existing seed photos: 1,010;
- `complete_body_likely`: 716;
- `review_partial_or_occlusion_risk`: 200;
- `not_comparable_or_unknown`: 94;
- low partial-body risk: 746;
- medium partial-body risk: 170;
- high partial-body risk: 94.

The full run installed `pi-heif` automatically when HEIF/HEIC-like images were
encountered; the run continued successfully.

Interpretation:

The full multisource 20% gate finds about one thousand additional review
candidates beyond the current human-confirmed seed. The complete-body proxy is
useful for review ordering: it does not claim truth, but it pushes edge-contact
and likely partial-body cases behind cleaner candidates. The first review block
should focus on the `complete_body_likely` group before spending time on
partial/occlusion-risk rows.

Current full review app:

```text
http://127.0.0.1:8513
```

The 8513 app uses an independent working CSV:

```text
outputs/bobcat_photo_selection/reviews/subject20_multisource_full_complete_priority/bobcat_photo_selection_review_working.csv
```

Review guidance:

- Start with the front of the queue; it is sorted by low edge-contact and
  complete-body-likely first.
- Continue rejecting partial body, severe occlusion, dead/specimen, scat,
  tracks, sign-only, tiny subject, or non-comparable angle.
- Treat `completeness_proxy` as a priority signal only; human judgment remains
  final.

## Seed Update And Rescue Plan 2026-07-01

User accepted the full 20% complete-priority queue as suitable. The 1,010 rows
were bulk-marked CLEAR with an explicit note that this is user-confirmed image
clearance, not identity labeling.

Bulk-accepted working CSV:

```text
outputs/bobcat_photo_selection/reviews/subject20_multisource_full_complete_priority/bobcat_photo_selection_review_working.csv
```

After rebuilding legacy-code17n:

- raw positive rows across all human-review sources: 1,645;
- deduplicated human-confirmed clear photos: 1,410;
- remaining clear photos needed for final 3000: 1,590.

Important conclusion:

The original legacy-code17l multisource pool is mostly exhausted at the high-quality
20% gate. Lowering it to 15% or 10% creates more candidates, but most are no
longer strong complete-body candidates. Therefore the remaining gap should be
handled as a rescue review, not automatic acceptance.

Additional rescue queues created:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_subject10_multisource_full_complete_priority_rescue_review_queue.csv
outputs/bobcat_photo_selection/bobcat_photo_selection_legacy-code16e_md10_rescue_review_queue.csv
outputs/bobcat_photo_selection/bobcat_photo_selection_combined_rescue_to_3000_review_queue.csv
```

Combined rescue queue:

- rows: 2,021;
- `complete_body_likely`: 181;
- `review_partial_or_occlusion_risk`: 364;
- `not_comparable_or_unknown`: 1,476;
- current seed + all combined rescue candidates would be 3,431, giving 431
  rows of buffer over the 3,000 target.

Current rescue review app:

```text
http://127.0.0.1:8516
```

Rescue review rule:

- Review from the top of the queue.
- Stop once legacy-code17n reaches 3,000 CLEAR rows plus a small safety buffer.
- Do not bulk-accept the full rescue queue unless the user explicitly decides
  quality is acceptable, because this layer contains many lower-comparability
  rows.

## Rescue Queue Reversal 2026-07-01

User review of the combined rescue queue showed that quality was unacceptable:
many rows were night/low-animal-sharpness images where the environment could
look clear while the animal itself was motion-blurred. This invalidates the
combined rescue queue as a primary path to 3,000.

Observed working result:

```text
outputs/bobcat_photo_selection/reviews/combined_rescue_to_3000/bobcat_photo_selection_review_working.csv
```

- reviewed before stopping: 42;
- CLEAR: 2;
- NOT CLEAR: 40.

Decision:

Do not continue using 8516 as the main rescue path. The failure mode is not
generic image quality; it is animal-subject sharpness and motion blur,
especially in night/infrared-like material.

Replacement rescue source:

```text
outputs/legacy-code14/legacy-code14_bobcat_high_confidence_inventory/legacy-code14_bobcat_all_strict_high_candidates.csv
```

Rationale:

legacy-code14 has explicit auto-prefeature bands for night/IR, blur, exposure,
contrast, edge density, and quality. It can enforce a better first principle:
only use photos where the animal image itself is likely frozen and comparable.

New rescue queue:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_legacy-code14_day_ultra_no_poor_exposure_rescue_review_queue.csv
```

Gate:

- exclude already-seeded images;
- `auto_night_ir = no`;
- `auto_blur_band = none`;
- `blur_laplacian_var >= 1000`;
- `contrast_std >= 45`;
- `edge_density >= 0.05`;
- `auto_quality_score >= 0.6`;
- exclude `auto_exposure_band = poor`.

Result:

- rows: 1,935;
- exposure bands: good 800, strong 787, limited 348;
- current seed 1,410 + this queue 1,935 gives a maximum of 3,345 before
  deduplication/review losses, enough to fill the 3,000 target with buffer.

Current recommended review app:

```text
http://127.0.0.1:8517
```

Review guidance:

- Use 8517 instead of 8516.
- Reject any animal motion blur, even if the background/environment is sharp.
- The rule for final inclusion is animal-subject clarity, not scene clarity.

## Animal-Size Threshold And Crop Preview 2026-07-01

User review of 8517 showed a second failure mode: the scene can be high quality
but the animal is too small in the full frame. Simple upscaling is not enough
because it cannot recover missing animal detail. The correct compromise is:

- use an animal-size threshold when the detector bbox is large enough in pixels;
- allow crop/zoom review only when the animal bbox has enough source pixels;
- reject images where the animal remains too small or motion-blurred after crop.

Threshold test on the 8517 day-ultra queue:

- full-frame animal area >= 20%: 15 rows;
- full-frame animal area >= 15%: 42 rows;
- full-frame animal area >= 10%: 109 rows;
- detector bbox shortest side >= 224 px: 688 rows.

Decision:

Full-frame area threshold alone is too strict for high-resolution camera-trap
images. Use bbox pixel size as a crop-eligibility threshold, then review the
cropped animal subject.

Crop review queue:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_legacy-code14_day_ultra_bbox224_crop_rescue_review_queue.csv
```

Current crop review app:

```text
http://127.0.0.1:8518
```

The app now displays the full image and, when detector bbox fields are present,
an animal crop preview below it.

## Crop Augmentation Acceptance 2026-07-01

User reviewed the crop-preview set and accepted it for the final 3000, provided
that the final use applies crop/zoom plus mild clarity enhancement. These rows
were bulk-marked CLEAR with `augmentation_required=yes`.

Accepted source:

```text
outputs/bobcat_photo_selection/reviews/legacy-code14_day_ultra_bbox224_crop_rescue/bobcat_photo_selection_review_working.csv
```

legacy-code17n after adding this source:

- deduplicated human-confirmed clear photos: 2,098;
- remaining clear photos needed for final 3000: 902.

Augmentation outputs:

```text
outputs/bobcat_photo_selection/augmented/legacy-code14_day_ultra_bbox224_crop_rescue/images/
outputs/bobcat_photo_selection/augmented/legacy-code14_day_ultra_bbox224_crop_rescue/legacy-code14_day_ultra_bbox224_crop_rescue_augmented_manifest.csv
outputs/bobcat_photo_selection/augmented/legacy-code14_day_ultra_bbox224_crop_rescue/legacy-code14_day_ultra_bbox224_crop_rescue_augmented_audit.json
```

Augmentation rule:

- detector bbox crop;
- 25% padding around bbox;
- resize only when crop short side is below 512 px;
- mild contrast enhancement (`1.08`);
- mild sharpness enhancement (`1.35`);
- unsharp mask (`radius=1.1`, `percent=90`, `threshold=3`).

Result:

- accepted crop-review rows: 688;
- augmented crop images written: 682;
- remote-download timeout failures: 6.

Boundary:

Augmentation is preprocessing for crop-eligible images. It helps review/training
chip visibility, but it does not create biological detail in images where the
animal is truly too small or motion-blurred.

## legacy-code17o Strict Final-902 Rescue 2026-07-01

Question:

Can the remaining 902-photo final-3000 gap be filled without weakening the
accepted clarity/crop standard?

Answer:

Yes. A strict legacy-code17o review queue now contains 902 candidates, with 904 strict
passes available before truncation to the target count.

Output queue:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_legacy-code17o_strict_final902_rescue_review_queue.csv
```

Audit:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_legacy-code17o_strict_final902_rescue_audit.json
```

Combined source inventory:

```text
outputs/bobcat_photo_selection/bobcat_photo_selection_legacy-code17o_strict_final902_rescue_combined_candidates.csv
```

Strict gate:

- allowed detector classes: `cat`, `dog`, `bear`;
- detector confidence >= `0.25`;
- detector bbox short side >= `224 px`;
- contrast standard deviation >= `42`;
- gradient p90 >= `18`;
- Laplacian variance >= `80`;
- edge contact count <= `1` to block high partial-body or edge-crop risk;
- exclude existing legacy-code17n seed rows;
- exclude prior human-reviewed rejects.

Result:

- combined candidate rows: 29,808;
- detector cache rows after incremental scoring: 19,685;
- existing legacy-code17n seed rows excluded: 2,098;
- prior human-reject keys excluded: 249;
- strict pass rows available: 904;
- selected legacy-code17o review queue rows: 902;
- selected class proxy counts: cat 525, bear 246, dog 131;
- partial-body risk proxy in selected rows: low 871, medium 31, high 0.

Boundary:

legacy-code17o is a review queue only. It does not fill the final 3000 until these
rows receive human CLEAR decisions. The standard was not relaxed; the bottleneck
was solved by processing more candidates and reusing the same crop-eligible
clarity rule.

## Bobcat Final-3000 Seed Completed 2026-07-01

User reviewed the legacy-code17o strict final-902 rescue batch and accepted it as high
quality. The 902 rows were bulk-marked CLEAR and added to legacy-code17n.

Final seed output:

```text
outputs/legacy-code17/legacy-code17n_bobcat_final3000_seed/legacy-code17n_bobcat_final3000_human_clear_seed_manifest.csv
```

Result:

- deduplicated final seed rows: 3,000;
- unique canonical image keys: 3,000;
- remaining clear rows needed: 0;
- audit status: `READY_FOR_FINAL_FREEZE_AUDIT`.

Latest source composition:

- subject20 multisource full complete priority: 1,010;
- legacy-code17o strict final-902 rescue: 902;
- legacy-code14 day-ultra bbox224 crop rescue: 688;
- subject20 multisource interim 4k: 263;
- earlier human-clear audit sources: 137 combined.

Boundary:

Bobcat photo selection is now complete enough to enter final freeze audit and
algorithm-entry packaging. It is still not identity validation; it is a
clarity-confirmed image-entry set for downstream PF-ERI/review-readiness work.
