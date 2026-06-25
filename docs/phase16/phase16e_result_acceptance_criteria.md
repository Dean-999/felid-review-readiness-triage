# Phase 16E Result Acceptance Criteria

Phase 16E output is pretrained model scoring and candidate evidence signals. It is not final high-confidence data and not identity prediction.

## Handoff Flow

```text
raw model outputs
-> acceptance audit
-> hard-gate diagnosis
-> soft eligibility recomputation
-> constrained selection
-> manual audit calibration
```

Low `selection_eligible` counts should trigger gate diagnosis, not weaker evidence standards.

## Required Files

```text
phase16e_candidate_model_filter_scores.csv
phase16e_candidate_model_filter_audit.json
phase16e_candidate_model_filter_summary.md
debug_samples/
```

Bobcat 20k runs must preserve:

```text
source_tier
source_role
source_dataset
identity_label_available
topup_reason
```

## Required Columns

Base columns:

```text
candidate_id
target_quadrant
species_label
scientific_name
source_mode
image_uri
image_load_success
rejection_reason
selection_eligible
final_candidate_score
```

OpenCLIP columns:

```text
clip_viewpoint_label
clip_viewpoint_confidence
clip_viewpoint_prob_left_side
clip_viewpoint_prob_right_side
clip_viewpoint_prob_frontal
clip_viewpoint_prob_rear
clip_viewpoint_prob_partial_or_occluded
clip_viewpoint_prob_unclear
```

Pose columns must exist even when pose is disabled:

```text
pose_enabled
pose_model_name
pose_success
pose_failure_reason
pose_num_keypoints
pose_mean_keypoint_confidence
pose_valid_keypoint_fraction
pose_body_coverage_score
pose_orientation_proxy
pose_side_view_proxy
pose_front_rear_proxy
pose_partial_body_proxy
pose_quality_score
pose_fallback_scoring_used
```

## Hard Checks

- `candidate_id` unique.
- `image_uri` duplicates reported.
- `image_load_success` distribution present.
- `final_candidate_score` numeric or recomputable.
- `source_mode` documented.
- `target_quadrant` present.
- No sensitive columns leaked.
- Bobcat rows must not imply verified identity labels unless separate verified labels exist.

Sensitive columns forbidden:

```text
unique_name
identity
identity_label
individual_id
animal_id
lynx_id
latitude
longitude
trap_id
location
location_id
cell_code
camera_id
```

## Current Hard-Gate Warning

Current runner `selection_eligible` is early prototype and diagnostic only.

Observed smoke-test issue:

```text
CzechLynx 1000: selection_eligible True = 18 / 1000
Bobcat 100: selection_eligible True = 0 / 100
```

Likely cause: OpenCLIP `partial_or_occluded`, `unclear`, `frontal`, or `rear` used as hard exclusion.

Rule:

```text
OpenCLIP label != final evidence decision
OpenCLIP probability = weak proxy / penalty / audit flag
```

## Phase 16F Soft Eligibility

Recompute offline:

```text
image_load_success hard requirement
+ IQA/crop quality
+ animal size / geometry when available
+ OpenCLIP side-view probability as soft evidence
- OpenCLIP uncertain/partial/front/rear as penalty, not automatic reject
+ optional pose completeness/viewpoint proxy
+ source-tier and duplicate controls
+ laterality balance
+ manual audit calibration
= soft eligibility and candidate shortlist
```

Use the recalibration script before constrained selection:

```bash
python3 scripts/recalibrate_phase16e_candidate_scores.py \
  --input outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_scores.csv \
  --output-dir outputs/phase16/phase16e_recalibrated_candidate_scores
```

It writes three quality-preserving tiers:

```text
strict_recalibrated_eligible
balanced_recalibrated_eligible
broad_recalibrated_eligible
```

Default downstream use should start from `balanced_recalibrated_eligible`.
`broad_recalibrated_eligible` is a reserve pool only and must not be used
directly as the final 3000.

Hard reject only:

- image failed to load;
- known duplicate selected into same final pool;
- unsupported source mode;
- known wrong species;
- catastrophic processing failure with no usable score;
- human audit confirms non-comparable or species-level-only for high-confidence set.

## Bobcat Tier 2 Boundary

Phase 16E2 Bobcat 20k:

```text
Tier 1 = 6412 FCF high-geometry candidates
Tier 2 = 13588 same-source FCF species-level URL top-up
```

Tier 2 expands scoring margin. It is not clean Re-ID data. It must pass Phase 16E scoring, Phase 16F constrained selection, laterality checks, and manual audit before final high-confidence use.

## Go / No-Go

Go to Phase 16F if:

- scores and audit files exist;
- `candidate_id` unique;
- image-load success rate explainable;
- IQA or `final_candidate_score` available for loaded images;
- OpenCLIP probabilities present or explicitly failed;
- pose failure is row-level if pose enabled;
- no sensitive columns leaked.

Do not proceed if:

- scores missing;
- most rows fail from source/path errors;
- all model scores missing in production run;
- IDs not unique;
- source-tier or target metadata lost;
- sensitive columns leaked.

## Claim Boundary

Allowed:

```text
Phase 16E extracted auditable pretrained quality, viewpoint, and optional pose structural proxies for candidate evidence scoring.
```

Not allowed:

- final high-confidence 3000 selected;
- automatic identity recognition;
- OpenCLIP viewpoint as ground truth;
- SuperAnimal pose as identity evidence;
- bobcat Re-ID accuracy;
- urbanization causality.
