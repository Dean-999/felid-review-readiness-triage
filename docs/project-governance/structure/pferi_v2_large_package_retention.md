# PF-ERI v2 Large Package Retention Plan

Scan date: 2026-07-28

## Decision

Large binary delivery packages do not all need to remain online after their workflow has been accepted. Keep the small provenance layer (`README.md`, audits, manifests, contracts, SHA256 declarations, checksum inventories, return records, and final analysis/freeze outputs). Bulky ZIP files and extracted image copies may then be moved to the Trash in a separate, explicitly approved cleanup.

## Cleanup Execution

On 2026-07-28, the confirmed `A1-A8` paths were moved to the macOS Trash through the guarded cleanup interface. The measured `archive/pferi_v2/task_runs` footprint decreased from approximately 63 GiB to 39 GiB. The files remain recoverable until the Trash is emptied.

Later on 2026-07-28, the user separately approved stripping reproducible photo members from the retained `B1-B8` ZIP packages and related PF-ERI v2 delivery ZIPs. The ZIP containers and their non-image evidence were retained. This reclaimed 41,225,145,413 bytes (38.394 GiB) from 53 ZIP files. Per-package original hashes, new hashes, removed counts, and provenance are recorded in `artifacts/manifests/pferi_v2_zip_photo_removal.csv`; the full policy and scope are in `docs/project-governance/structure/pferi_v2_zip_photo_removal.md`.

## First Cleanup Set

These redundant representations, superseded packages, or byte-identical copies were moved to the Trash, recovering approximately 24 GiB from the project directory. Some completed workflow scripts still refer to extracted directories; restore them from the retained ZIP or Trash before rerunning those historical workflows.

| ID | Estimated size | Candidate | Reason |
| --- | ---: | --- | --- |
| `A1` | 9.4 GiB | `dual_sample_confirmation/2026-07-20_formal_reviewer_candidate_delivery_v1/candidate_reviewer_packages_unzipped/` | Extracted copy of the four retained reviewer ZIP files. |
| `A2` | 8.6 GiB | `model_development/2026-07-26_task15i_candidate_reviewer_packages_v1/candidate_reviewer_packages_unzipped/` | Extracted copy of the four retained Task 15I reviewer ZIP files. |
| `A3` | 2.5 GiB | `model_development/2026-07-27_task15l_calibration_collection_freeze_v1/reviewer_packages/candidate_reviewer_packages_unzipped/` | Extracted copy of the retained calibration reviewer ZIP files; collection and freeze outputs already exist. |
| `A4` | 1.0 GiB | `dual_sample_confirmation/2026-07-21_adjudication_candidate_delivery_v1/candidate_adjudication_packages_unzipped/` | Extracted copy of the retained adjudicator ZIP files. |
| `A5` | 372 MiB | `model_development/2026-07-27_task15k_calibration_modelscope_control_package_v1/PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE/` | Extracted copy of the retained 370 MiB ZIP. |
| `A6` | 343 MiB | `model_development/2026-07-27_task15m_confirmation_modelscope_control_package/iterations/v2/PF_ERI_TASK15M_CONFIRMATION_MODELSCOPE_CONTROL_PACKAGE/` | Extracted copy of the current, checksum-verified 338 MiB ZIP. |
| `A7` | 682 MiB | `model_development/2026-07-27_task15m_confirmation_modelscope_control_package/iterations/v1/` | Superseded package iteration. The task README records why v2 replaced it. |
| `A8` | 731 MiB | `model_development/2026-07-23_task15f_modelscope_full_run_v1/` | Its `results/` directory is byte-identical to the frozen Task 15F result directory, and its source-delivery ZIP is also byte-identical. |

## Metadata-Only Preservation Set

These delivery-only binary packages originally recorded the exact stimuli supplied to reviewers or external runners. After explicit approval, their reproducible photo members were removed while the ZIP containers, metadata, audits, and adjacent evidence were retained. Measured recovery is recorded in the photo-removal manifest.

| ID | Estimated size | Candidate | Required retained evidence |
| --- | ---: | --- | --- |
| `B1` | 14 GiB | `dual_sample_confirmation/2026-07-21_formal_reviewer_subpackages_v1/` package ZIP files | Keep `subpackage_audit.json` and `CHECKSUMS.sha256`; these ZIPs represent exact reviewer-facing split deliveries. |
| `B2` | 9.4 GiB | `dual_sample_confirmation/2026-07-20_formal_reviewer_candidate_delivery_v1/candidate_reviewer_packages/` | Keep `candidate_build_audit.json`, `CHECKSUMS.sha256`, restricted metadata, return audits, and final adjudicated outcomes. |
| `B3` | 8.6 GiB | `model_development/2026-07-26_task15i_candidate_reviewer_packages_v1/candidate_reviewer_packages/` | Keep `candidate_build_audit.json`, `CHECKSUMS.sha256`, restricted metadata, accepted raw responses, and the Task 15I result freeze. |
| `B4` | 2.6 GiB | `model_development/2026-07-25_task15i_descriptor_execution_manifest_v1/TASK15I_INDEPENDENT_DESCRIPTOR_IMAGES.zip` | Keep the descriptor execution manifest, package audit, ZIP SHA256, and the materialized 4,108-image controlled reservoir. |
| `B5` | 2.5 GiB | `model_development/2026-07-27_task15l_calibration_collection_freeze_v1/reviewer_packages/candidate_reviewer_packages/` | Keep collection report, release authorization, collection freeze record, reviewer-package audit/checksums, and calibration analysis freeze. |
| `B6` | 1.0 GiB | `dual_sample_confirmation/2026-07-21_adjudication_candidate_delivery_v1/candidate_adjudication_packages/` | Keep adjudication audit, checksum inventory, returned decisions, and final adjudicated outcomes. |
| `B7` | 370 MiB | `model_development/2026-07-27_task15k_calibration_modelscope_control_package_v1/PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE.zip` | Keep package audit, package manifest hash, external return, and Task 15L freeze. |
| `B8` | 338 MiB | `model_development/2026-07-27_task15m_confirmation_modelscope_control_package/iterations/v2/PF_ERI_TASK15M_CONFIRMATION_MODELSCOPE_CONTROL_PACKAGE.zip` | Keep package audit, SHA256 declaration, final external return, and Task 15M confirmation freeze. |

## Retain

Do not remove the following as part of package cleanup:

- `data/frozen/pferi_v2/` and controlled candidate-reservoir manifests;
- accepted reviewer responses, adjudicated outcomes, calibration results, and confirmation results;
- task-level `README.md` files and iteration logic;
- audit JSON, contracts, manifests, checksum/SHA256 declarations, and scientific disposition records;
- scripts and tests needed to rebuild or validate a package;
- external return artifacts that are not duplicated in a validated freeze.

## Cleanup Rule

Use the IDs above as the approval boundary. Cleanup should move only the approved exact paths to the macOS Trash, never delete broadly by wildcard, and should report the measured space recovered. The Trash remains recoverable until it is emptied.
