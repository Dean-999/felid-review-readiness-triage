# Expanded CzechLynx 125x4 Sampling Notes

## Purpose

This document records the expanded CzechLynx blinded review package for the next manual triage step.

The project remains a review-readiness triage study. It does not identify individual animals directly, train a new Re-ID model, estimate population size, or claim universal felid thresholds.

## Selected Design

The selected expanded pilot design is:

| Item | Value |
|---|---:|
| Working individual IDs | 125 |
| Images per ID | 4 |
| Total blinded review images | 500 |
| Dataset role | CzechLynx quantitative known-ID validation carrier |
| Random seed | 20260606 |

The expanded package uses real CzechLynx images only and excludes images already used in the current 200-image pilot.

## Why 125 IDs x 4 Images

The completed 200-image pilot produced useful pilot-level evidence, especially after the MegaDescriptor-S-224 baseline. Its main remaining limitation is that the ready-ready same-pair subset is sparse; the strict filter retains only 3 same-individual pairs.

The feasibility check showed that `125 IDs x 4 images` is available in the remaining CzechLynx manifest and gives the highest same-pair ceiling among the candidate designs considered:

- `125 x 4` gives up to 750 same-individual pairs before readiness filtering.
- The manual workload is 500 images.
- The design increases same-pair evidence more efficiently than a 2-image-per-ID expansion.

These are design reasons for the next blinded manual review package, not final scientific claims.

## Inputs

The package preparation reads:

- `data/interim/czechlynx/czechlynx_real_manifest.csv`
- `data/interim/czechlynx/czechlynx_pilot_internal_with_ids.csv`

The package does not read or use second-review files.

## Outputs

Generated local package files:

- `data/interim/czechlynx/expanded_125x4_review_images/`
- `data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv`
- `data/labels/czechlynx/czechlynx_expanded_125x4_triage_blinded.csv`
- `data/interim/czechlynx/czechlynx_expanded_125x4_sampling_summary.txt`

Generated QC and review aids:

- `outputs/czechlynx/qc/czechlynx_expanded_125x4_blinding_audit.txt`
- `outputs/czechlynx/expanded_125x4_contact_sheets/`

Generated `data/` and `outputs/` artifacts remain local and uncommitted.

## Blinding Safeguards

The internal mapping is separate from the blinded triage CSV.

The blinded triage CSV contains only:

- neutral expanded image IDs;
- neutral review image paths under `expanded_125x4_review_images`;
- manual triage fields.

The blinded CSV must not contain:

- working individual IDs;
- `unique_name`;
- original `lynx_` identity paths;
- latitude or longitude;
- exact location;
- `cell_code`;
- `trap_id`;
- raw CzechLynx paths;
- second-review fields.

The audit script checks row counts, image existence, filename format, current-pilot overlap, and leakage strings before manual review proceeds.

## Manual Labeling Workload

The next manual task is triage labeling for 500 blinded images.

The triage fields match the existing pilot review schema:

- review-readiness label;
- blur, occlusion, lighting, side comparability, visible region, and pattern visibility;
- body fraction, distance, camera angle, confidence, uncertainty, exclusion reason, and notes.

## What Was Not Done

This slice does not:

- modify raw data;
- modify existing 200-image pilot files;
- modify final 200-image labels;
- read or modify second-review files;
- create final expanded labels;
- construct expanded pair sets;
- run embeddings or model analysis;
- train or fine-tune any model;
- make final scientific claims.

## Next Step

The next step is manual triage of the 500 blinded expanded images using:

- `data/labels/czechlynx/czechlynx_expanded_125x4_triage_blinded.csv`
- `outputs/czechlynx/expanded_125x4_contact_sheets/`

After manual triage is complete, a separate audited slice can create finalized expanded labels and then build expanded validation/pair files.
