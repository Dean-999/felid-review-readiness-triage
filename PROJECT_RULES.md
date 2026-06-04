# PROJECT_RULES.md

## Project Identity

This repository supports the project:

Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images

The project does not identify individual animals. It evaluates whether camera-trap images are reliable enough to enter individual-level Re-ID review.

## Core Scientific Boundary

- Do not claim this project identifies true individual animals.
- Do not claim a new Re-ID model.
- Do not claim population estimation.
- Do not claim a universal threshold across felid species.
- Do not claim WildTrax/UWIN identity validation without verified individual IDs.
- Do not claim Marbled Cat Re-ID validation in the current study.
- Re-ID embeddings, when used later, are measurement signals, not the project's final product.

## Data Roles

- CzechLynx: quantitative known-ID validation carrier.
- UWIN/WildTrax: field motivation and field-readiness stress test only.
- Marbled Cat: future Asian conservation application scenario only.

## Data Safety Rules

- Do not modify raw data.
- Do not commit raw images.
- Do not commit `data/` or `outputs/`.
- Do not expose `unique_name`, original `lynx_###` paths, latitude, longitude, exact location, cell_code, or trap_id in blinded review files.
- Keep internal mapping files separate from blinded label files.
- Do not publish images or contact sheets until license and display permissions are confirmed.

## Phase Discipline

- Phase 1: data access, rubric, blinded triage, consistency audit, second-review check.
- Phase 2: validation table, pair construction, embedding/similarity validation after Phase 1 consistency is complete.
- Phase 3: risk-coverage policy evaluation after pairwise similarity outputs exist.
- Do not make final scientific claims before the relevant validation step is complete.

## Current Waiting Constraint

The 30-image second-review subset has been prepared. Do not open second-review images or mapping until the planned delayed second-review labeling step. Avoid memory contamination.

## Coding Rules

- Write small, auditable scripts.
- Print clear PASS/FAIL summaries for audit scripts.
- Exit nonzero on audit failure when appropriate.
- Do not create model training code unless explicitly requested.
- Do not create website code unless explicitly requested.
- Prefer deterministic sampling with fixed random seeds.
- Keep generated outputs under `data/interim/` or `outputs/`.
- Do not use notebooks as the only source of logic; important logic should be in scripts.

## Git Rules

- Commit docs and scripts.
- Do not commit `data/`, `outputs/`, raw images, derived image sheets, internal mapping files, or local CSV outputs.
- Use clear commit messages describing the research workflow slice.
