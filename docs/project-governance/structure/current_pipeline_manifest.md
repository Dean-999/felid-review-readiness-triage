# Current pipeline manifest

Date: 2026-07-17

This file identifies the active PF-ERI v2 chain. It supersedes the 2026-07-08
manifest that still described Phase16-18 exploratory scripts as active.

## Binding scientific boundary

PF-ERI v1 results are exploratory context only. PF-ERI v2 uses newly frozen,
outcome-safe inputs and must not inherit a v1 effect size, decision threshold,
calibration target, identity claim, or confirmation result.

CodeGraph and RepoWise locate code and dependencies. CSV/JSON manifests, direct
row counts, audit files, and frozen hashes determine scientific state.

## Active flow

```text
final photo freeze
  -> neutral v2 image context and canonical pair contract
  -> fresh dual-descriptor candidate reservoir
  -> outcome-free measurement-feasibility gates
  -> image-quality and local-match full measurements
  -> pre-sampling exclusions and official image allocation
  -> within-role pair frames and post-allocation gates
  -> Workbook04 power/cost and allocation readiness
  -> assignment-enforced timed operational rehearsal
  -> future confirmation sampling only after all binding gates pass
```

## Authoritative entry points

| Area | Code/artifact |
| --- | --- |
| Frozen photos | `data/frozen/pferi_v2/<scope>/manifest.csv` and `images/` |
| Canonical pairs | `scripts/build_v2_canonical_pair_contract.py` |
| Candidate reservoir | `scripts/build_v2_dual_descriptor_candidate_reservoir.py` |
| Measurement contracts | `schemas/pferi_v2/` and `scripts/validate_v2_*` |
| Robust matcher | `gpu/kaggle_v2_local_matcher_v2/` |
| Structural oracle | `scripts/analyze_v2_structural_oracle_reliability.py` |
| Information partitioning | `scripts/apply_v2_official_image_allocation.py` and related v2 builders |
| Workbook04 | `scripts/audit_ws04_power_cost_inputs.py`, `scripts/simulate_ws04_power_cost_sensitivity.py`, `scripts/audit_ws04_four_stage_allocation.py` |
| Rehearsal | `scripts/build_v2_timed_operational_rehearsal.py`, `scripts/audit_v2_timed_operational_rehearsal.py`, and contract v2 |
| Supersession history | `docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md` |

## Workbook04 status

Workbook04 is the active work area. Its v1 exploratory scenario context is
frozen in `schemas/pferi_v2/ws04_exploratory_context_v1.json`, including source
SHA-256 values. Workbook04 no longer depends on three legacy Phase18 paths.

The input audit, sensitivity simulation, allocation audit, and operational
rehearsal are distinct gates. A PASS in one does not authorize a later gate or
permit access to outcome data.

## Historical code and outputs

- `scripts/legacy/`, `scripts/prototypes/`, `colab/archive/`, the original local
  matcher, and implemented plan/spec files have left the active tree.
- Phase 7–19 scripts/tests are isolated under
  `archive/pferi_v1/reproducibility/` with a byte-level archive manifest.
- No phase-numbered v1 implementation remains in the active `scripts/` or
  `tests/` tree. New v2 code must not import from the reproducibility archive.
- Historical result tables and audits live under `archive/pferi_v1/outputs/`.
  They are not v2 evidence unless an active contract names a compact frozen input
  explicitly.
- Current v2 generated results live only under `outputs/pferi_v2/`.
- Reconstructable execution packages live under `work/pferi_v2/`; transfer ZIPs
  live under `artifacts/transfers/pferi_v2/`. Use the dry-run-first cleanup and
  materialization scripts for lifecycle operations.
- `data/frozen/pferi_v2/` is authoritative input storage and must never be treated
  as disposable generated output.

## Current read order

1. `README.md`
2. `PROJECT_RULES.md`
3. `docs/CURRENT_PROJECT_MAP.md`
4. this manifest
5. `docs/project-governance/workstreams/README.md`
6. `docs/project-governance/workstreams/04_dual_sample_confirmation/README.md`
7. `docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`
8. `scripts/README.md`

The detailed daily log is chronology, not a first-pass source of current state.
