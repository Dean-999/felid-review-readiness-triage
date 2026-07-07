# legacy-code19 Candidate Pool Download Report

Date: 2026-07-06

## Summary

Raw candidate pools were staged under:

```text
data/legacy-code19_candidate_pools/
```

This is a candidate pool only. These images are not final model-entry images
until they pass the strict legacy-code19 photo-selection gate.

## Download Results

| Pool | Candidate rows | Downloaded / present | Missing / failed | Size |
| --- | ---: | ---: | ---: | ---: |
| `bobcat_wild_camera_trap` | 20,000 | 12,204 | 7,796 | 11.494 GB |
| `bobcat_urban_heterogeneous` | 20,000 | 17,796 | 2,204 | 7.676 GB |
| `lynx_external_heterogeneous_supplement` | 4,765 | 4,253 | 512 | 2.748 GB |

Total downloaded/present image files:

```text
34,253
```

Total candidate-pool directory size:

```text
22 GB
```

## Manifests

```text
data/legacy-code19_candidate_pools/bobcat_wild_camera_trap/bobcat_wild_camera_trap_candidate_manifest.csv
data/legacy-code19_candidate_pools/bobcat_wild_camera_trap/bobcat_wild_camera_trap_download_manifest.csv
data/legacy-code19_candidate_pools/bobcat_wild_camera_trap/bobcat_wild_camera_trap_audit.json

data/legacy-code19_candidate_pools/bobcat_urban_heterogeneous/bobcat_urban_heterogeneous_candidate_manifest.csv
data/legacy-code19_candidate_pools/bobcat_urban_heterogeneous/bobcat_urban_heterogeneous_download_manifest.csv
data/legacy-code19_candidate_pools/bobcat_urban_heterogeneous/bobcat_urban_heterogeneous_audit.json

data/legacy-code19_candidate_pools/lynx_external_heterogeneous_supplement/lynx_external_heterogeneous_supplement_candidate_manifest.csv
data/legacy-code19_candidate_pools/lynx_external_heterogeneous_supplement/lynx_external_heterogeneous_supplement_download_manifest.csv
data/legacy-code19_candidate_pools/lynx_external_heterogeneous_supplement/lynx_external_heterogeneous_supplement_audit.json

data/legacy-code19_candidate_pools/legacy-code19_candidate_pools_audit.json
```

## Source Breakdown

### Bobcat Wild Camera-Trap

Candidate sources:

| Source | Candidate rows | Downloaded / present |
| --- | ---: | ---: |
| Felidae Conservation Fund 2020-2025 | 6,412 | 4,311 |
| Caltech Camera Traps | 7,984 | 4,979 |
| WSU Lynx / `lynx rufus` | 5,604 | 2,914 |

Interpretation:

```text
The Bobcat wild pool is large enough for strict review. It should be treated as
camera-trap / wildland-edge evidence, not as verified Bobcat identity data.
```

### Bobcat Urban / Heterogeneous

Candidate sources:

| Source | Candidate rows | Downloaded / present |
| --- | ---: | ---: |
| iNaturalist | 20,000 | 17,796 |

Interpretation:

```text
The Bobcat urban/heterogeneous pool is large enough for strict review. The
urban label remains a proxy and must be audited from source, place, context, and
visual evidence. These images do not provide Bobcat identity accuracy labels.
```

### Lynx External Heterogeneous Supplement

Candidate sources:

| Source | Candidate rows | Downloaded / present |
| --- | ---: | ---: |
| iNaturalist | 2,269 | 2,031 |
| GBIF | 2,496 | 2,222 |

Interpretation:

```text
The Lynx external supplement is larger than expected and sufficient for an
auxiliary sensitivity panel. It must not be described as CzechLynx urban data.
```

## Selection Gate Reminder

Final 3000 images must be selected from these candidate pools using the strict
visual-evidence protocol:

```text
clear animal
sharp animal body, not merely sharp background
visible body/pattern evidence
not severe motion blur
not severe night/IR washout
not tiny unless crop remains clearly comparable
not dead, track, scat, sign-only, skeleton, toy, drawing, or non-photo
not severe partial body or occlusion
license/provenance auditable
duplicates removed
```

When uncertain, reject from the clean 3000 and keep the image only for stress
tests or failure analysis.

## Build Script

The downloader is:

```text
scripts/download_legacy-code19_candidate_pools.py
```

It is resumable. Re-running with:

```bash
python3 scripts/download_legacy-code19_candidate_pools.py --use-existing-manifest --workers 24
```

skips already downloaded files and retries missing files.

To audit existing files without network access:

```bash
python3 scripts/download_legacy-code19_candidate_pools.py --use-existing-manifest --audit-existing-only
```

