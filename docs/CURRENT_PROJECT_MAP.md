# Current project map

Date: 2026-07-17

## Scientific state

PF-ERI v2 studies pair-level evidence admission after strong wildlife Re-ID
retrieval. Its governing line is **Similarity is not admissibility.** It does not
replace a descriptor, assign identities automatically, or turn exploratory v1
results into confirmation evidence.

The project is `v2_design_locked`. The four-stage programme, practical decision
rule, dependence/interval specification, reviewer operation, sampling strata,
official seed, historical-pair exclusion register, and exact zero-overlap
1,000/1,000/1,000 image allocation are frozen pre-outcome. No v2 outcome packet
has been authorized.

## Active work

Workbook04 / Workstream 04 is active. The accepted programme targets:

- 400 analyzable development pairs;
- 400 analyzable calibration pairs;
- 400 analyzable mechanism-confirmation pairs;
- 800 analyzable deployment-confirmation pairs.

At the accepted 0.90 planning completion fraction this means 2,224 prepared
unique unordered pairs and 4,448 first-pass judgements under full double review.
The immediate gate is completion and audit of within-role automatic pair
measurements and post-allocation capacity. Pair sampling and outcome packets
remain blocked until those gates pass.

The timed operational rehearsal v1 failed because it permitted duplicate
participant/packet submissions. The assignment-enforced v2 replacement passed
its operational gate on a distinct, permanently excluded pilot set. It informs
interface operation only and does not estimate semantic-review completion or
reviewer reliability.

## Current architecture

```text
data/frozen/pferi_v2
  -> outputs/pferi_v2
  -> canonical v2 pair and measurement contracts
  -> fresh dual-descriptor reservoir
  -> outcome-free feasibility gates
  -> full image-quality and local-match measurement
  -> exclusions, strata, seed, image allocation
  -> within-role pair frames and automatic measurement
  -> Workbook04 readiness and sampling execution
  -> blinded collection only after all gates pass
```

The current implementation map is
`docs/project-governance/structure/current_pipeline_manifest.md`. Script entry
points are listed in `scripts/README.md`.

## Historical boundary

PF-ERI v1 and top-level Phase18-19 results are exploratory. They may explain
failure modes and provide explicitly labelled scenario context, but they cannot
set a v2 effect size, threshold, calibration target, success criterion, identity
claim, or confirmation result. Workbook04 reads a compact frozen context capsule
at `schemas/pferi_v2/ws04_exploratory_context_v1.json` rather than the legacy
Phase18 output paths.

Phase 7–17 source/test bytes are isolated under
`archive/pferi_v1/reproducibility/`. Earlier `scripts/legacy/`, prototype,
archived-Colab, matcher-v1, oracle-v1, and implemented-plan files have left the
active tree. Their succession and evidence retention rules are documented in
`docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`; exact tracked source is
available from Git history.

## Output boundary

`data/frozen/pferi_v2/` is authoritative input storage. Its three populated
manifests match 6,000 Bobcat-urban, 3,000 Bobcat-wild, and 3,000 CzechLynx image
files. Current result tables, audits and response logs live under
`outputs/pferi_v2/`. Reconstructable execution and reviewer packages live under
`work/pferi_v2/`; transport archives live under `artifacts/transfers/pferi_v2/`.
PF-ERI v1 result bytes are preserved under `archive/pferi_v1/` and are never an
active v2 result root.

The 2026-07-18 phase-code archive manifest records the original path, archive
path, size, raw SHA-256, and source commit for every isolated script and test.

The 2026-07-17 migration recorded every old/new path, size and source SHA-256 in
`docs/project-governance/structure/2026-07-17_pferi_v1_v2_relocation_manifest.csv`.
Work images removed as byte-identical frozen-input copies are reconstructable
from `artifacts/manifests/pferi_v2_work_image_dedup.csv`.

## Read order

1. `README.md`
2. `PROJECT_RULES.md`
3. this map
4. `docs/project-governance/structure/current_pipeline_manifest.md`
5. `docs/project-governance/workstreams/04_dual_sample_confirmation/README.md`
6. `docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`
7. `scripts/README.md`

The daily log preserves chronology but is not authoritative for current status.
