# CzechLynx Sampling Plan

## Purpose

This document defines how CzechLynx images will be sampled for Phase 1 triage and later Q1/Q2 validation.

CzechLynx is the quantitative known-ID validation carrier. Sampling must therefore support both manual review-readiness labeling and later same/different pair analysis.

## Sampling Goals

The sampling plan must support:

1. a small pilot triage study;
2. a second-review consistency check;
3. later Q1 reliability validation;
4. later Q2 risk–coverage trade-off analysis;
5. avoidance of identity leakage during triage;
6. coverage of realistic camera-trap variation.

## Recommended Sample Sizes

### Phase 1 Pilot

Recommended size:

```text
100-200 images
```

Primary purpose:

- test whether the rubric is usable;
- identify ambiguous cases;
- tune supporting fields;
- run a small second-review consistency check.

### Phase 2 Expansion

Recommended size:

```text
500-1000 images
```

Primary purpose:

- construct enough same-individual and different-individual pairs;
- compare triage groups;
- compute similarity separation;
- evaluate risk–coverage policies.

### Minimum Acceptable Pilot

Minimum size:

```text
50 images
```

Use only if data access or time is limited.

## Sampling Principle

The sample should not be a random set of only easy images.

It must deliberately include variation in:

- individual identity;
- camera site;
- date/time;
- lighting;
- side/view;
- image quality;
- occlusion;
- body visibility;
- pattern visibility;
- distance to camera.

The goal is to test the rubric under real conditions, not only on clean examples.

## Sampling Dimensions

Sample across the following dimensions where metadata and images allow.

### Identity Coverage

Include multiple individuals.

Recommended pilot target:

- at least 20-40 unique individuals if possible;
- at least 2 images for some individuals;
- avoid one individual dominating the sample.

### View / Side Coverage

Include:

- left-side views;
- right-side views;
- frontal views;
- rear views;
- oblique views;
- unknown side.

Side comparability matters because individual-level felid comparison often depends on comparable visible regions.

### Body Region Coverage

Include:

- full body;
- flank;
- shoulder/torso;
- hip/rear body;
- head-only;
- tail-only;
- partial body;
- fragmentary body.

### Image Quality Coverage

Include:

- clear images;
- mild blur;
- moderate blur;
- severe blur;
- close images;
- far images;
- cropped images;
- images with vegetation or terrain obstruction.

### Lighting Coverage

Include:

- daylight;
- twilight;
- night IR;
- low-light;
- overexposed or underexposed images if present.

### Pattern Visibility Coverage

Include:

- high pattern visibility;
- medium pattern visibility;
- low pattern visibility;
- no visible pattern.

### Metadata Coverage

Include images with:

- complete metadata;
- partial metadata;
- missing or uncertain metadata if such cases exist.

## Sampling Workflow

### Step 1: Build Metadata Manifest

Create a master metadata manifest containing:

- image_id;
- image_path;
- individual_id;
- timestamp;
- camera_id;
- site_id;
- region;
- split if available;
- any quality-related metadata if available.

### Step 2: Verify Repeated Individuals

Count:

- number of unique individuals;
- number of images per individual;
- number of individuals with at least 2 images;
- number of individuals with at least 5 images;
- number of images with missing ID.

### Step 3: Select Candidate Sample

Use metadata to select a balanced candidate sample.

Individual IDs may be used at this stage only to ensure enough repeated individuals.

### Step 4: Create Blinded Triage Sheet

Create a triage sheet that excludes:

- individual_id;
- any field that obviously reveals identity;
- any previous match/candidate information.

The triage sheet may include:

- image_id;
- image_path;
- dataset;
- species;
- timestamp category if needed;
- camera/site general code if needed.

### Step 5: Manual Triage

Apply the triage rubric to each image.

Record all supporting fields.

### Step 6: Second-Review Subset

Randomly select 30 pilot images for second review after at least 48 hours.

Record:

- original label;
- second label;
- agreement or disagreement;
- reason for disagreement;
- rubric revision needed.

### Step 7: Restore IDs for Validation

Only after triage labels are finalized, join the triage table back to individual IDs.

## Pilot Sampling Target

For the first pilot, use this target distribution if possible:

| Category | Target Count |
|---|---:|
| Clear side/flank images | 30-40 |
| Partial body images | 20-30 |
| Night IR images | 20-30 |
| Blurry or low-quality images | 20-30 |
| Occluded images | 10-20 |
| Frontal/rear/oblique images | 20-30 |
| Very weak/unidentifiable cases | 10-20 |

These categories can overlap.

## Validation-Oriented Sampling

For later Q1/Q2 analysis, the expanded sample should prioritize repeated individuals.

Recommended target:

- 500-1000 images;
- at least 50 repeated individuals if possible;
- balanced sampling across individuals;
- avoid many near-duplicate burst images from the same event;
- include enough low-readiness images for comparison.

## Burst Similarity Control

Camera-trap bursts can create near-duplicate images.

This matters because near-duplicates can inflate apparent Re-ID reliability.

Record or later derive:

- timestamp cluster;
- same camera event;
- burst sequence flag;
- time gap between images;
- possible duplicate flag.

Initial Phase 1 triage does not need to remove all bursts, but it should flag them if visible or metadata-supported.

## Triage Output File

Recommended file:

```text
data/labels/czechlynx/czechlynx_pilot_triage.csv
```

Required columns:

```text
image_id
dataset
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
reviewer_confidence
uncertainty_flag
exclusion_reason
notes
```

A separate validation file may later contain:

```text
image_id
individual_id
timestamp
camera_id
site_id
split
```

Do not expose this validation file during triage.

## Sampling Pass Standard

The pilot sample is acceptable if:

- it includes at least 100 images unless constrained;
- it includes multiple individuals;
- it includes clear, limited, and unidentifiable examples;
- it includes day and night/IR images if available;
- it includes multiple views and body regions;
- triage can be done without viewing IDs;
- second-review subset is possible.

## Risk Audit

| Vulnerability | Why It Matters | Repair | Pass Standard | Allowed Claim After Repair | Still Not Allowed |
|---|---|---|---|---|---|
| Sample contains mostly clean images | Rubric will look stronger than reality | Stratify by quality, view, lighting, occlusion | Pilot includes low-readiness cases | Rubric tested across image conditions | Field robustness is proven |
| Too few repeated individuals | Q1/Q2 cannot form enough same pairs | Use ID metadata during sampling only | Repeated individuals are present before blinding | Known-ID validation is feasible | Identity labels influenced triage |
| ID leakage during triage | Biases labels | Create blinded triage sheet | Reviewer cannot see IDs | Triage is identity-blinded | Triage is perfectly objective |
| Burst duplicates inflate performance | Same-event images may be too similar | Flag burst events and later test sensitivity | Burst flag exists or timestamp review planned | Results can include burst sensitivity analysis | Random split performance is unbiased |
| Low-readiness images too rare | Cannot compare categories | Deliberately sample difficult cases | Each triage category has enough examples | Category comparison becomes possible | Full dataset distribution is known from pilot |

## Phase 1 Pass Standard

This sampling plan is accepted only if:

- the pilot size is defined;
- the expanded validation target is defined;
- identity blinding is required;
- sample diversity dimensions are listed;
- second-review consistency check is included;
- burst similarity risk is acknowledged;
- CzechLynx remains a validation carrier, not the biological scope of the project.
