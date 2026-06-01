# WildTrax Field Triage Plan

## Purpose

This document defines how UWIN/WildTrax field images will be used in the project.

UWIN/WildTrax images are used for field motivation and field-readiness stress testing.

They are not used for strict identity validation because verified individual IDs are not currently available.

## Data Role

UWIN/WildTrax role:

```text
field motivation and field-readiness stress test
```

The images help answer:

- What kinds of camera-trap image problems appear in real field tagging?
- How often do images appear review-ready, review-limited, or unidentifiable?
- What failure modes make a species-level detection unsafe for individual-level Re-ID review?

They do not answer:

- Which true individual appeared?
- How many individuals appeared?
- What is the Re-ID accuracy?
- What is the true false-match rate?

## User Field Context

The user participates as a UWIN-Atlanta volunteer and has performed camera-trap tagging work.

This is important because the project is not invented only from literature. It comes from a real field workflow where many images are suitable for species-level tagging but not necessarily suitable for individual-level evidence.

The field tagging guide includes common ambiguity rules, such as choosing broader categories when species cannot be confidently identified, and distinguishing Bobcat from Domestic Cat using features such as short tail, body build, and wild felid appearance. This supports the project’s distinction between species-level tagging and individual-level readiness.

## Target Field Species

Primary target field examples:

- Bobcat
- Canada Lynx, if available

Secondary useful examples:

- Domestic Cat, because it can be confused with Bobcat in field images;
- Coyote / Domestic Dog / Fox examples, only as evidence of general tagging uncertainty;
- non-felid examples only if they clarify field image failure modes.

## Sample Size

Recommended initial field sample:

```text
50-100 images
```

If enough Bobcat / Canada Lynx images are available, prioritize them.

If not enough target felid images are available, include a small number of adjacent examples that show field problems such as blur, partial body, night IR, occlusion, or species uncertainty.

## What to Record

Each WildTrax/UWIN image should be labeled using the same review-readiness rubric:

- review-ready;
- review-limited;
- unidentifiable.

Also record:

- species label;
- camera location metadata if available;
- timestamp if available;
- lighting condition;
- blur level;
- occlusion level;
- visible side;
- visible region;
- pattern visibility;
- field failure reason;
- whether the image can be publicly shown.

## WildTrax Triage Output File

Recommended file:

```text
data/labels/wildtrax/wildtrax_field_triage.csv
```

Recommended columns:

```text
image_id
dataset
project_or_site_code
species_label
source_role
triage_label
blur_level
occlusion_level
lighting_condition
night_ir_artifact
visible_side
side_comparability
visible_region
pattern_visibility
body_fraction_visible
distance_to_camera
camera_angle
metadata_completeness
timestamp_available
location_metadata_available
public_display_permission
reviewer_confidence
uncertainty_flag
field_failure_reason
notes
```

## Field Failure Reasons

Use controlled terms where possible:

- `motion_blur`
- `focus_blur`
- `night_ir_artifact`
- `partial_body`
- `animal_too_far`
- `animal_too_small`
- `vegetation_occlusion`
- `body_angle_not_comparable`
- `pattern_not_visible`
- `species_uncertain`
- `domestic_cat_confusion`
- `burst_or_repeat_detection`
- `metadata_missing`
- `other`

## Public Display Rules

The user reported that WildTrax images may be shown.

However, the project should still apply conservative public-use rules:

1. Confirm permission from the relevant platform/project contact before public release.
2. Avoid publishing exact sensitive locations unless explicitly permitted.
3. Use site codes or generalized locations in public materials.
4. Do not upload raw field image sets to GitHub.
5. Use only selected examples in mentor-facing documents or posters.
6. Keep private metadata separate from public documentation.

## Analysis Plan

WildTrax/UWIN analysis is descriptive only.

Report:

- number of field images reviewed;
- percentage review-ready;
- percentage review-limited;
- percentage unidentifiable;
- most common field failure reasons;
- examples of species-level usable but Re-ID-limited images;
- comparison between field image conditions and CzechLynx validation conditions.

Do not report:

- Re-ID accuracy;
- same/different separation;
- individual count;
- true match count;
- false-match rate;
- population inference.

## Recommended Summary Table

| Metric | Value |
|---|---:|
| Total field images reviewed | pending |
| Bobcat images | pending |
| Canada Lynx images | pending |
| review-ready rate | pending |
| review-limited rate | pending |
| unidentifiable rate | pending |
| most common failure reason | pending |
| public examples available | pending |

## Boundary Language

Use this exact boundary language in reports:

UWIN/WildTrax images are used only for field-readiness stress testing and field motivation. Because verified individual IDs are not available, these images are not used for strict Re-ID accuracy, same/different validation, or true individual identification.

## How This Supports the Project

WildTrax/UWIN supports the project by showing that real field images create a review-readiness problem before Re-ID.

It connects the technical validation to the conservation workflow:

- CzechLynx proves whether the gate is meaningful under known-ID validation.
- WildTrax/UWIN shows why such a gate is needed in real field tagging.
- Marbled Cat shows how the logic could later guide Asian felid monitoring.

## Risk Audit

| Vulnerability | Why It Matters | Repair | Pass Standard | Allowed Claim After Repair | Still Not Allowed |
|---|---|---|---|---|---|
| WildTrax has no verified IDs | Cannot validate individual identity | Use only descriptive triage distribution | No identity metrics reported | Field images show readiness challenges | WildTrax Re-ID accuracy |
| Public display permission is assumed | Could violate project/platform rules | Confirm permission before public use | Each public image has permission status | Selected examples can be shown if permitted | Uploading full raw dataset |
| Field sample is biased | Images available to the user may not represent all WildTrax data | Describe sample as convenience field sample | Report sample limitations | Field stress-test examples are valid | Field-wide distribution claim |
| Location metadata is exposed | Conservation or platform data may be sensitive | Use generalized site codes in public outputs | Exact coordinates excluded unless permitted | Metadata availability can be recorded | Public exact location release without approval |
| Species uncertainty is mixed with Re-ID readiness | Confuses two different problems | Record species confidence separately from readiness | Species-level and readiness fields are separate | Some species-tagged images are not Re-ID-ready | Species tag equals identity readiness |

## Phase 1 Pass Standard

This plan is accepted only if:

- WildTrax/UWIN is field stress test only;
- no identity validation claim is made;
- sample size is defined;
- field failure reasons are recorded;
- public display permission is tracked;
- exact location handling is conservative;
- the output is a triage distribution and failure-mode summary.
