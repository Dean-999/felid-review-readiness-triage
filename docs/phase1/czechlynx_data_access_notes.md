# CzechLynx Data Access Notes

## Purpose

This document records the access, license, version, metadata, and permitted-use status of CzechLynx before it is used for validation.

CzechLynx is the quantitative known-ID validation carrier for this project.

No embedding extraction, model testing, or formal validation should begin until this access audit is complete.

## Dataset Role

CzechLynx is used for:

- Q1 reliability validation;
- Q2 risk–coverage trade-off analysis;
- known-ID same-individual and different-individual pair construction;
- triage category comparison;
- pairwise false-match risk proxy under known-ID validation.

CzechLynx is not used to define the entire project as a Eurasian lynx project.

## Public Dataset Facts to Verify

Before analysis, confirm and record the exact dataset version being used.

Public descriptions of CzechLynx describe it as an open-access Eurasian lynx camera-trap dataset for individual identification, pose estimation, and instance segmentation. The current public Scientific Data version describes tens of thousands of camera-trap images, identity labels, segmentation masks, and skeleton annotations across multiple years of monitoring.

However, different public versions may report different image counts or identity counts. Therefore, the project must record the exact version used.

## Access Checklist

Fill this table before using the dataset.

| Item | Status | Notes |
|---|---|---|
| Dataset source identified | pending | Kaggle / official paper release / repository / other |
| Dataset downloaded | pending | Record date and method |
| Dataset version recorded | pending | Record exact version or release date |
| License located | pending | Do not proceed until license is found |
| License permits research use | pending | Required |
| License permits science fair / mentor review use | pending | Required |
| License permits showing sample images | pending | Required if images appear in poster/paper |
| Citation format recorded | pending | Required |
| Metadata files located | pending | Required |
| Individual ID labels located | pending | Required |
| Image paths verified | pending | Required |
| Evaluation split files located | pending | Optional but recommended |
| Camera/site metadata located | pending | Recommended |
| Timestamp metadata located | pending | Recommended |
| Sensitive location fields checked | pending | Required before public release |

## Local Storage Plan

Use the project local path:

```text
/Users/deanshen/Desktop/scientific project/felid-review-readiness-triage
```

Recommended internal storage:

```text
data/raw/czechlynx/
data/interim/czechlynx/
data/labels/czechlynx/
outputs/czechlynx/
```

Do not commit raw CzechLynx images to GitHub unless the license explicitly permits redistribution and the repo is intentionally public.

Recommended `.gitignore` protection:

```gitignore
data/raw/
data/interim/
outputs/cache/
*.zip
*.tar
*.tar.gz
*.csv
*.xlsx
*.parquet
*.pt
*.pth
*.ckpt
.env
```

If a small label template or metadata schema needs to be tracked, place it under:

```text
docs/templates/
```

## Required Metadata Fields

The ideal CzechLynx metadata table should include:

- image_id;
- image_path;
- individual_id;
- species;
- date or timestamp;
- camera_id or site_id;
- region;
- split assignment if available;
- annotation availability;
- mask availability;
- skeleton availability;
- bounding box if available;
- original image dimensions.

If some fields are unavailable, record that explicitly.

## Identity Handling

### Sampling Stage

Individual IDs may be used during sampling to ensure enough repeated individuals and enough same-individual pair potential.

### Triage Stage

Individual IDs must be hidden during manual triage.

The triage sheet used by the reviewer should not display `individual_id`.

### Validation Stage

Individual IDs are restored only after triage labels are finalized.

## Legal and Ethical Use Rules

### Rule 1: Do Not Redistribute Raw Images Without Permission

Even if the dataset is open-access, redistribution must follow the dataset license.

### Rule 2: Record Public Display Permissions

Before using any CzechLynx image in:

- mentor slides;
- science fair poster;
- paper;
- website;
- GitHub README,

confirm whether the license permits public display.

### Rule 3: Use Proper Citation

The dataset paper and/or official dataset page must be cited in any mentor-facing or public document.

### Rule 4: Avoid Sensitive Location Exposure

If the dataset includes exact camera locations or sensitive conservation locations, public outputs should use aggregate or anonymized location labels unless the dataset documentation permits exact disclosure.

## Dataset Version Log

| Field | Entry |
|---|---|
| Access date | 2026-06-01 |
| Source URL or platform | Kaggle CzechLynx dataset |
| Download method | Kaggle dataset download |
| Local raw data path | data/raw/czechlynx/ |
| Total local files found | 79,762 |
| Total image files found | 79,760 |
| Real metadata file | CzechLynxDataset-Metadata-Real.csv |
| Synthetic metadata file | CzechLynxDataset-Metadata-Synthetic.csv |
| Real metadata rows | 39,760 |
| Synthetic metadata rows | 40,000 |
| Main validation file | CzechLynxDataset-Metadata-Real.csv |
| Synthetic data use | Not used for primary Q1/Q2 validation |
| Working individual ID field | unique_name |
| Unique working individual IDs | 319 |
| Unique encounters | 18,782 |
| Unique locations | 86 |
| Unique trap IDs | 659 |
| Metadata path check | First 1,000 real metadata paths checked; 1,000 existed locally |
| Image readability check | First 100 real images checked; 100 readable, 0 bad |
| Split fields found | split-geo_aware, split-time_open, split-time_closed, split-pose |
| License name | pending |
| Citation | pending |
| Public image display allowed? | pending |
| Redistribution allowed? | pending |
| Current decision | Conditional Go for internal sampling; No public display until license/display permission is confirmed |

## Initial Sanity Checks

Before sampling:

1. Confirm image files open correctly.
2. Confirm metadata rows map to image files.
3. Confirm individual IDs are non-empty for validation images.
4. Count images per individual.
5. Count repeated individuals with at least two images.
6. Check whether timestamp/camera/site metadata exist.
7. Check whether any split definitions are included.
8. Check whether masks/skeletons are necessary for this project.
9. Create a small file manifest.
10. Save a read-only copy of original metadata.

## Minimum Requirements for Proceeding

CzechLynx is usable for this project only if:

- image files are accessible;
- verified individual ID labels are accessible;
- the license permits non-commercial research use;
- citation requirements are recorded;
- enough repeated individuals exist to construct same-individual pairs;
- metadata can connect images to individual IDs.

## Go / No-Go

### Go

Proceed to CzechLynx sampling if:

- license and citation are clear;
- image files are accessible;
- known individual IDs are accessible;
- at least 50 repeated individuals or a sufficient pilot subset exists;
- metadata can be joined to image paths;
- triage can be done without exposing IDs to the reviewer.

### Conditional Go

Proceed only with limited planning if:

- images and IDs are accessible but public image display rights are unclear;
- metadata fields are incomplete but IDs and image paths are usable;
- exact sample size must be reduced for feasibility.

### No-Go

Do not proceed if:

- license is unclear;
- individual IDs are unavailable;
- image paths cannot be mapped to metadata;
- data access violates platform rules;
- dataset use cannot be cited or justified.

## Risk Audit

| Vulnerability | Why It Matters | Repair | Pass Standard | Allowed Claim After Repair | Still Not Allowed |
|---|---|---|---|---|---|
| Version mismatch | Different releases may have different image/ID counts | Record exact version and counts from local files | Dataset version log is complete | Results apply to the recorded version | Results apply to all CzechLynx versions |
| License uncertainty | Public use may be restricted | Locate license before analysis | License and citation recorded | Dataset used legally for research | Public display if not permitted |
| ID leakage during triage | Reviewer may unconsciously label easier images for known individuals | Hide IDs during triage | Triage sheet excludes IDs | Triage labels are blinded to identity | Triage is fully objective |
| Inadequate repeated individuals | Cannot construct enough same-individual pairs | Sample individuals with repeated detections | Enough same-pair potential exists | Pilot validation is feasible | Full statistical power if sample is small |
| Sensitive location exposure | Conservation data may be sensitive | Aggregate or remove exact locations in public outputs | Public outputs avoid exact sensitive coordinates | Field/site effects can be described generally | Exact coordinates can be published without permission |

## Phase 1 Pass Standard

This document is complete only when:

- dataset source is recorded;
- exact version is recorded;
- license is recorded;
- citation is recorded;
- image count and ID count are locally verified;
- individual ID availability is confirmed;
- public display permissions are known;
- a Go / Conditional Go / No-Go decision is made.

## Current CzechLynx Access Decision

CzechLynx is technically available for internal Phase 1 sampling.

The real metadata file contains 39,760 rows and 319 unique `unique_name` values. The `unique_name` column will be treated as the working individual ID field for sampling and later same/different pair construction, pending final confirmation from dataset documentation.

The first 1,000 metadata paths were checked and all existed locally. The first 100 real images were checked with PIL and all were readable.

The main validation will use `CzechLynxDataset-Metadata-Real.csv` only. Synthetic images will not be used for the primary Q1/Q2 validation because the project studies real camera-trap review-readiness.

This is a Conditional Go, not a full Go, because license, citation, redistribution, and public image display permissions are still pending.