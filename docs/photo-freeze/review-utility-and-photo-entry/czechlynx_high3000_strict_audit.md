# CzechLynx High-3000 Strict Audit

Date: 2026-07-01

## Question

Can the CzechLynx high-confidence 3000 be treated as ready under the same
clarity-first standard now used for Bobcat final entry?

## Answer

No. Under the strict Bobcat-style standard, the current CzechLynx high-confidence
3000 should not be frozen without repair or replacement.

The strict audit is intentionally conservative. It requires detector geometry,
large-enough animal crop, strong clarity/edge evidence, no major blur/exposure
flags, and no high partial-body risk.

## Outputs

```text
outputs/czechlynx/legacy-code17_strict_high3000_audit/legacy-code17_strict_czechlynx_high3000_audit.json
outputs/czechlynx/legacy-code17_strict_high3000_audit/legacy-code17_strict_czechlynx_high3000_audit_report.md
outputs/czechlynx/legacy-code17_strict_high3000_audit/legacy-code17_strict_czechlynx_high3000_failure_type_summary.csv
```

Primary pass manifest:

```text
outputs/czechlynx/legacy-code17_strict_high3000_audit/legacy-code14_working_final_high3000_strict_pass_manifest.csv
```

Primary fail review queue:

```text
outputs/czechlynx/legacy-code17_strict_high3000_audit/legacy-code14_working_final_high3000_strict_fail_review_queue.csv
```

## Gate

- detector confidence >= `0.25`;
- detector bbox short side >= `224 px`;
- detector bbox area >= `10%`;
- no detector edge-touch partial-body risk;
- contrast standard deviation >= `42`;
- Laplacian variance >= `80`;
- edge density >= `0.05`;
- no night/IR flag;
- no poor exposure flag;
- no non-low human blur/occlusion flag when available;
- no high CLIP partial/unclear probability when available.

## Results

| Set | Rows | Strict Pass | Fail/Review | Geometry Unverified |
| --- | ---: | ---: | ---: | ---: |
| legacy-code14 working final high3000 | 3,000 | 1,154 | 1,846 | 0 |
| legacy-code14 strict 2x2 high3000 | 3,000 | 818 | 2,182 | 1,108 |
| legacy-code16f selected high3000 | 3,000 | 147 | 2,853 | 1,776 |

## Interpretation

The legacy-code14 working-final set is the best current CzechLynx high-confidence
foundation because it has detector geometry and raw clarity metrics for all
rows. However, only 1,154 rows pass the new strict standard.

The legacy-code14 strict 2x2 and legacy-code16f selected 3000 files cannot be treated as
fully verified under the Bobcat-style rule because many rows lack recoverable
detector geometry in the current artifact layer. This is not proof that those
images are bad; it means they are not yet verified by the same rule.

The most common primary failure modes are blur flags, poor exposure, weak edge
evidence, small detector bbox, and missing detector geometry.

## Decision

Do not freeze CzechLynx high-confidence 3000 under the new strict final-entry
standard.

Use the 1,154 strict-pass legacy-code14 working-final rows as the confirmed base, then
repair the remaining gap by:

1. recovering or recomputing detector geometry for unverified rows;
2. selecting replacements from the broader CzechLynx candidate pool using the
   same strict gate;
3. manually reviewing borderline rows only after they pass geometry and clarity
   thresholds;
4. documenting any threshold change as a scientific rule change, not a
   convenience adjustment.

Boundary:

This audit is a prototype diagnostic. It does not delete rows and does not
change the official CzechLynx selection until a replacement/freeze step is run.

## Strict 3000 Supplement 2026-07-01

The strict audit left only 1,154 rows in the legacy-code14 working-final set. A
supplement prototype was run across the broader local CzechLynx pool to rebuild
a 3,000-row review queue without weakening the image-quality standard.

Supplement script:

```text
scripts/prototypes/prototype_czechlynx_strict3000_supplement.py
```

Final review queue:

```text
outputs/czechlynx/legacy-code17_strict3000_supplement/legacy-code17_czechlynx_strict3000_review_queue.csv
```

Detector cache:

```text
outputs/czechlynx/legacy-code17_strict3000_supplement/legacy-code17_czechlynx_strict3000_detector_cache.csv
```

Audit:

```text
outputs/czechlynx/legacy-code17_strict3000_supplement/legacy-code17_czechlynx_strict3000_supplement_audit.json
```

Result:

- selected rows: 3,000;
- unique dedupe keys: 3,000;
- local image files present: 3,000;
- strict gate pass: 3,000;
- selected identity labels/groups: 235;
- largest identity/group count: 359;
- source composition:
  - local legacy-code14 strict-pass base: 1,277;
  - legacy-code16e local detector/IQA re-score: 1,723.

The final 4-row gap was resolved by a targeted high-resolution (`imgsz=1280`)
detector recheck of sharp high-potential failures. This did not lower the gate;
it only recovered detector geometry for images that already had sufficient
clarity metrics.

Review app:

```text
http://127.0.0.1:8520
```

Important boundary:

This is now a strict 3,000-row review queue, not a frozen final CzechLynx
training/evaluation manifest. Because the queue is quality-first and uses a
wide identity cap, it contains high-quality photos but is not yet optimized for
identity balance. A final freeze step should either:

1. accept this as a visual-quality-first high-confidence 3,000; or
2. derive a smaller identity-balanced training subset from it.

## Clarity Augmentation And Final-Ready Manifest 2026-07-01

After manual inspection, the strict 3,000-row queue was accepted as visually
usable. A final mild clarity augmentation pass was then run to improve
algorithm-entry readability while keeping the original image as the scientific
source of truth.

Augmentation script:

```text
scripts/prototypes/prototype_czechlynx_strict3000_clarity_augmentation.py
```

Augmented image directory:

```text
outputs/czechlynx/legacy-code17_strict3000_supplement/augmented/images/
```

Final confirmed manifest:

```text
outputs/czechlynx/legacy-code17_strict3000_supplement/augmented/legacy-code17_czechlynx_strict3000_final_confirmed_manifest.csv
```

Audit:

```text
outputs/czechlynx/legacy-code17_strict3000_supplement/augmented/legacy-code17_czechlynx_strict3000_clarity_augmentation_audit.json
```

Result:

- source rows: 3,000;
- augmented rows: 3,000;
- augmented files present: 3,000;
- missing augmented files: 0;
- unique dedupe keys: 3,000;
- strict gate pass: 3,000 `yes`;
- final status: 3,000 `human_clear_augmented_ready_for_freeze`;
- source composition remains 1,277 legacy-code14 strict-pass rows and 1,723
  legacy-code16e local detector/IQA re-score rows.

Enhancement parameters:

```text
contrast=1.06
sharpness=1.25
unsharp_mask_radius=1.0
unsharp_mask_percent=80
unsharp_mask_threshold=3
jpeg_quality=94
crop=none
resize=none
```

Boundary:

This is readability preprocessing, not evidence creation. No crop, resize,
label change, synthetic detail, or identity balancing was applied. Each row
keeps both `original_image_path` and `algorithm_entry_image_path`. The correct
claim is now:

```text
CzechLynx has a human-reviewed, strict-gated, clarity-augmented,
visual-quality-first 3,000-image manifest ready for final freeze audit.
```

The remaining freeze decision is whether this exact manifest is sufficient for
the next algorithm step, or whether a separate identity-balanced subset should
be derived for training/evaluation splits.

## CodeGraph Check 2026-07-01

CodeGraph was checked during this step. It located the current strict3000
supplement script, but broad CzechLynx supplement/augmentation queries also
returned older Bobcat strict-clarity and legacy CzechLynx paths.

Decision:

- use CodeGraph only to locate candidate code and inspect blast radius;
- use concrete CSV/JSON/report artifacts for all CzechLynx row counts,
  manifest state, photo validity, and phase completion decisions;
- treat broad CodeGraph returns into old CzechLynx legacy scripts as retrieval
  misses, not as project-direction evidence.
