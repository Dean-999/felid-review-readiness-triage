# Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images

This project evaluates whether felid camera-trap images are reliable enough to enter individual-level Re-ID review.

## Core Boundary

This project does not identify individual animals. It evaluates whether images are reliable enough to enter individual-level Re-ID review.

It does not claim a new Re-ID model, population estimation method, field-deployment identity system, or universal threshold across felid species.

## Core Research Questions

### Q1: Reliability

Do images labeled as review-ready show more reliable Re-ID behavior than review-limited or unidentifiable images?

### Q2: Trade-off

After filtering low-readiness images, does pairwise false-match risk proxy decrease, and how much potential known matching evidence is lost?

## Data Roles

- CzechLynx: quantitative known-ID validation carrier.
- UWIN/WildTrax: field motivation and stress test.
- Marbled Cat: future application only.

## Current Completed Status

- 200-image CzechLynx blinded pilot triage completed.
- Final triage consistency audit passed.
- 30-image second-review subset prepared and blinding audit passed.
- Phase 2 validation table and pair set prepared.
- Phase 3 risk-coverage policy plan drafted.

## Current Pending Status

- Delayed second-review labeling.
- CzechLynx license and citation verification.
- Embedding baseline selection.
- Phase 2 similarity analysis.

## Repository Safety

- Raw data are not committed.
- Generated images and contact sheets are not committed.
- `data/` and `outputs/` are ignored and should remain out of Git.
- Public image display is pending license and display-permission confirmation.
- Internal mapping files remain separate from blinded review files.

## Folder Structure

- `docs/phase0/`: project scope, evidence chain, research questions, and data roles.
- `docs/phase1/`: data access notes, rubric, CzechLynx pilot triage planning, license/citation audit, and go/no-go criteria.
- `docs/phase2/`: validation, embedding baseline, and metrics planning.
- `docs/phase3/`: risk-coverage policy planning.
- `docs/logs/`: daily work log.
- `docs/mentor_updates/`: concise mentor-facing progress updates.
- `scripts/`: auditable utility scripts for triage, blinding, validation-table, pair-set, and input checks.
- `data/`: local data and generated CSV artifacts; not committed.
- `outputs/`: local reports and generated review artifacts; not committed.

## No Final Claims Yet

The current repository records preparation, triage, audits, and planning. Final scientific claims must wait until delayed second-review consistency, license/citation verification, embedding baseline selection, Phase 2 similarity analysis, and Phase 3 policy evaluation are complete.