# Triage Rubric

## Purpose

This document defines the review-readiness rubric for felid camera-trap images before individual-level Re-ID review.

The rubric is designed for Phase 1 of the project:

**Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images**

The purpose is not to identify individual animals. The purpose is to decide whether an image contains enough visible and comparable individual-level evidence to enter Re-ID review.

## Core Principle

A camera-trap image can be species-identifiable without being individual-ID-ready.

For example, an image may be clear enough to tag as Bobcat, Canada Lynx, or Eurasian Lynx, but still be too blurred, occluded, partial, angled, or night-distorted to support reliable individual-level comparison.

This rubric separates those standards.

## Primary Labels

Each image receives exactly one primary triage label:

1. `review-ready`
2. `review-limited`
3. `unidentifiable`

These labels describe readiness for individual-level Re-ID review, not species-level identification.

## Label 1: review-ready

### Definition

An image is `review-ready` if it shows enough visible, sharp, and comparable individual-level evidence to enter candidate Re-ID review.

For felids, this usually requires a visible diagnostic body region such as flank, torso side, shoulder region, hip region, or another patterned region that can be compared across images.

### Minimum Conditions

An image should be labeled `review-ready` only if most of the following are true:

- the animal is a felid or likely target felid;
- the image contains a sufficiently visible diagnostic region;
- the diagnostic region has usable coat pattern, spots, rosettes, mottling, stripe-like markings, or other stable visual features;
- blur is absent or mild;
- occlusion does not hide most of the diagnostic region;
- lighting is sufficient for pattern interpretation;
- night IR artifacts do not erase the useful pattern;
- the side or view is interpretable;
- the visible region is comparable to at least one plausible future image region;
- the image is not only a head, leg, tail, eye shine, or silhouette unless that visible region is unusually diagnostic.

### Felid-Specific Guidance

For lynx and bobcat-like animals, useful evidence may include:

- flank or side-body pattern;
- shoulder and torso pattern;
- hip and rear-side pattern;
- visible contrast in spots or mottling;
- short-tail markings only as supporting evidence, not usually as the only evidence;
- side comparability, especially left side versus right side.

A clean side image with visible flank pattern is usually stronger than a frontal, rear, or heavily angled image.

### Intended Use

`review-ready` images can enter:

- strict Re-ID review;
- balanced Re-ID review;
- known-ID validation analysis;
- same/different pair similarity analysis.

### Allowed Claim

After validation, the project may test whether `review-ready` images produce stronger same-individual versus different-individual similarity separation.

### Not Allowed

A `review-ready` label does not mean:

- the individual identity is known;
- the image produces a true identity match;
- the image can be used without expert review;
- the same threshold transfers to another species or dataset.

## Label 2: review-limited

### Definition

An image is `review-limited` if it contains some potentially useful individual-level evidence, but the evidence is incomplete, weak, or condition-dependent.

These images may be useful in an expert review queue, but should not be treated as strong stand-alone identity evidence.

### Typical Cases

Label an image `review-limited` when one or more of the following apply:

- partial flank is visible but incomplete;
- pattern is visible but blurred;
- the animal is moderately occluded;
- the image is night IR but some pattern remains visible;
- the animal is at an awkward angle;
- the body is partly cropped;
- only one diagnostic region is visible;
- distance is high but pattern is partly interpretable;
- the side is uncertain but some region is comparable;
- image quality is not strong enough for strict reporting but may help a human reviewer.

### Felid-Specific Guidance

A `review-limited` image may show:

- partial spots or mottling;
- part of the torso or hip;
- side pattern interrupted by vegetation;
- low-contrast coat pattern under IR;
- a comparable region, but not enough for confident stand-alone review.

### Intended Use

`review-limited` images may enter:

- balanced expert review;
- failure-mode analysis;
- sensitivity analysis;
- optional secondary review.

They should not be used as strong identity evidence alone.

### Allowed Claim

The project may test whether including selected `review-limited` images preserves useful known matching evidence while increasing or decreasing pairwise false-match risk proxy.

### Not Allowed

A `review-limited` label does not mean:

- the image is useless;
- the image is identity-ready;
- the image should be excluded from all analyses;
- a candidate match from this image is a true identity.

## Label 3: unidentifiable

### Definition

An image is `unidentifiable` if it lacks enough visible individual-level evidence to support candidate Re-ID review.

This does not necessarily mean the species is unidentifiable. It means the image is not suitable for individual-level evidence.

### Typical Cases

Label an image `unidentifiable` when one or more of the following apply:

- severe motion blur;
- animal is too small or too far away;
- only eye shine is visible;
- only tail, leg, paw, ear, or body fragment is visible;
- animal is mostly hidden by vegetation, terrain, snow, objects, or camera obstruction;
- pattern is not visible;
- lighting or IR artifact removes diagnostic detail;
- animal is only a silhouette;
- visible side cannot be interpreted;
- no diagnostic region is available;
- image cannot support individual-level comparison even with expert caution.

### Intended Use

`unidentifiable` images are excluded from identity inference.

They may still be used for:

- species-level tagging if species is clear;
- field-readiness distribution;
- failure-mode counts;
- examples of why species-level tagging is not the same as Re-ID readiness.

### Allowed Claim

The project may claim that `unidentifiable` images are excluded from individual-level Re-ID review under the proposed gate.

### Not Allowed

The project may not claim that excluding these images improves real-world population estimates unless downstream ecological validation is performed.

## Supporting Fields

Each image must also receive supporting fields. These fields prevent the triage label from becoming vague or purely subjective.

### Required Fields

| Field | Allowed Values | Purpose |
|---|---|---|
| `image_id` | string | Unique image identifier |
| `dataset` | CzechLynx / UWIN-WildTrax / other | Source dataset |
| `species_label` | species name or unknown | Species-level label if available |
| `source_role` | validation / field_stress_test / future_application | Evidence role |
| `triage_label` | review-ready / review-limited / unidentifiable | Primary label |
| `blur_level` | none / mild / moderate / severe | Motion or focus blur |
| `occlusion_level` | none / mild / moderate / severe | Vegetation/body obstruction |
| `lighting_condition` | daylight / twilight / night_ir / low_light / unknown | Lighting context |
| `night_ir_artifact` | none / mild / moderate / severe / not_applicable | IR distortion |
| `visible_side` | left / right / frontal / rear / top / mixed / unknown | View direction |
| `side_comparability` | high / medium / low / none | Whether side/view can be compared |
| `visible_region` | flank / torso / shoulder / hip / head / tail / legs / partial_body / full_body / unknown | Main visible region |
| `pattern_visibility` | high / medium / low / none | Diagnostic coat pattern visibility |
| `body_fraction_visible` | 0-25 / 25-50 / 50-75 / 75-100 | Approximate body visibility |
| `distance_to_camera` | close / medium / far / unknown | Relative image scale |
| `camera_angle` | side / oblique / frontal / rear / overhead / unknown | Camera view |
| `metadata_completeness` | complete / partial / missing / unknown | Whether timestamp/location/camera metadata exist |
| `reviewer_confidence` | high / medium / low | Confidence in triage label |
| `uncertainty_flag` | yes / no | Whether the label needs second review |
| `exclusion_reason` | controlled vocabulary or blank | Main reason for exclusion |
| `notes` | free text | Short justification |

### Recommended Exclusion Reasons

Use controlled values where possible:

- `severe_blur`
- `too_far`
- `too_small`
- `major_occlusion`
- `pattern_not_visible`
- `side_unknown`
- `body_fragment_only`
- `night_ir_artifact`
- `silhouette_only`
- `non_target_species`
- `duplicate_or_burst_issue`
- `metadata_missing`
- `other`

## Decision Rules

### Rule 1: Do Not Use Individual ID During Triage

Triage must be assigned without viewing the verified individual ID.

This prevents identity knowledge from influencing the review-readiness label.

### Rule 2: Species-Level Usable Does Not Mean Re-ID-Ready

If an image can be tagged as Bobcat or Lynx but lacks diagnostic individual-level evidence, it should be `review-limited` or `unidentifiable`.

### Rule 3: Ambiguity Should Not Be Forced Into review-ready

If the reviewer is unsure whether the visible pattern is comparable, assign `review-limited` and set `uncertainty_flag = yes`.

### Rule 4: Pattern Visibility Matters More Than General Image Beauty

A visually clear image with only the face or rear may be less useful than a slightly imperfect image with a visible flank pattern.

### Rule 5: Side Comparability Must Be Recorded

Left-side and right-side images may not be directly comparable. Record visible side and side comparability separately.

### Rule 6: Night IR Is Not Automatic Exclusion

Night IR images can be `review-ready` if pattern detail remains visible. They become `review-limited` or `unidentifiable` if IR artifacts erase diagnostic pattern.

### Rule 7: Partial Body Is Not Automatic Exclusion

Partial body images can be `review-limited` or occasionally `review-ready` if the visible region contains strong diagnostic pattern. They should not be treated as review-ready by default.

### Rule 8: Duplicate Burst Images Must Be Flagged

If images appear to come from the same burst sequence, record a possible burst duplicate flag later during sampling or metadata review. Burst similarity can inflate apparent Re-ID reliability.

## Second-Review Subset

To reduce subjectivity, Phase 1 should include a small consistency check.

Recommended plan:

- triage 100-200 CzechLynx pilot images;
- re-triage 30 randomly selected images after at least 48 hours;
- compare original and second labels;
- record disagreements;
- revise the rubric if disagreement is high.

### Pass Standard

The rubric is usable if:

- most disagreements occur between adjacent labels, not between `review-ready` and `unidentifiable`;
- disagreement reasons can be explained by visible fields;
- the reviewer can apply the rubric without looking at individual ID;
- ambiguous cases are not forced into review-ready.

## Risk Audit

| Vulnerability | Why It Matters | Repair | Pass Standard | Allowed Claim After Repair | Still Not Allowed |
|---|---|---|---|---|---|
| Labels are subjective | Weak reproducibility | Use supporting fields and second-review subset | Disagreements are explainable and mostly adjacent | Rubric is operationally defined | Human triage is automatically correct |
| Species-level tagging is confused with Re-ID readiness | Overstates field images | Separate species label from readiness label | Images can be species-tagged but still excluded from Re-ID review | Species-level and Re-ID readiness are distinct | Species tag proves identity-readiness |
| review-limited becomes a vague middle category | Reduces interpretability | Require specific reasons and supporting fields | Each review-limited image has a clear limitation | review-limited can support balanced expert review | review-limited is safe stand-alone identity evidence |
| Night IR images are excluded too aggressively | May lose useful evidence | Score pattern visibility and IR artifact separately | Some IR images can remain review-ready | IR effects are explicitly recorded | All night images are unusable |
| Partial body images are excluded too aggressively | May lose known matching evidence | Evaluate visible diagnostic region | Some partial-body images can be review-limited or review-ready | Partial evidence can be measured | Partial image automatically proves identity |

## Phase 1 Pass Standard

This rubric is accepted only if:

- the three labels are clearly defined;
- each label has observable criteria;
- all images receive supporting fields;
- individual ID is hidden during triage;
- ambiguous cases are not forced into review-ready;
- the rubric can be applied to both CzechLynx and UWIN/WildTrax field samples;
- the rubric supports later Q1 and Q2 validation.
