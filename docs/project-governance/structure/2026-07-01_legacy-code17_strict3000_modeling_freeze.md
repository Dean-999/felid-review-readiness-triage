# legacy-code17 Strict 3000 Modeling Freeze

Date: 2026-07-01

## Decision

The two most important image-entry datasets are now frozen into one local
modeling package:

```text
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/
```

Freeze status:

```text
FROZEN
```

## Inputs

Bobcat source manifest:

```text
outputs/legacy-code17/legacy-code17n_bobcat_final3000_seed/legacy-code17n_bobcat_final3000_human_clear_seed_manifest.csv
```

CzechLynx source manifest:

```text
outputs/czechlynx/legacy-code17_strict3000_supplement/augmented/legacy-code17_czechlynx_strict3000_final_confirmed_manifest.csv
```

## Frozen Package Contents

```text
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/
  README.md
  images/
    bobcat/
    czechlynx/
  manifests/
    frozen_modeling_manifest.csv
    bobcat_frozen_manifest.csv
    czechlynx_frozen_manifest.csv
  checksums/
    sha256_manifest.csv
  evidence/
    freeze_audit.json
    source manifests/audits/reports
```

## Verification

Independent verification after the freeze:

- combined manifest rows: 6,000;
- Bobcat frozen manifest rows: 3,000;
- CzechLynx frozen manifest rows: 3,000;
- checksum rows: 6,000;
- Bobcat local image files: 3,000;
- CzechLynx local image files: 3,000;
- image decode status: 6,000 `ok`;
- failed rows: 0;
- package size: about 4.7 GB.

## Boundaries

This is the local modeling image-entry package, not a new scientific claim.

- Bobcat rows are human-confirmed clear photos, but not verified individual
  identity labels.
- CzechLynx rows are strict-gated and clarity-augmented, but the package is
  visual-quality-first and not automatically identity-balanced.
- CzechLynx augmentation is readability preprocessing; original image paths are
  preserved in the source manifest and evidence directory.
- Any algorithmic identity training/evaluation split must be derived from this
  frozen package with a separate split manifest.

## Next Modeling Entry

Use this combined manifest as the starting point:

```text
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv
```

The next step should create a feature/embedding manifest from
`frozen_image_path`, then derive:

1. CzechLynx identity-aware train/evaluation splits where identity labels are
   available;
2. Bobcat unlabeled transfer-stress or review-readiness inference sets;
3. shared image-quality and descriptor feature tables with checksums preserved.
