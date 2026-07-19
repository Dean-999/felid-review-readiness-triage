# Scripts map

The active implementation is PF-ERI v2. Historical Phase 7–19 sources and their
directly coupled tests are isolated under
`archive/pferi_v1/reproducibility/`; they are not inputs to the v2 confirmation
chain. The former `scripts/legacy/`, prototype, and archived-Colab trees were
removed after their outcomes and supersession reasons were consolidated in
`docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`.

## PF-ERI v2 execution chain

### Candidate reservoir and contracts

- `build_v2_canonical_pair_contract.py`
- `build_v2_czechlynx_image_context.py`
- `build_v2_descriptor_execution_manifest.py`
- `build_v2_dual_descriptor_candidate_reservoir.py`
- `validate_v2_evidence_measurement_dictionary.py`
- `validate_v2_independent_quality_control_contract.py`
- `validate_v2_automatic_pair_evidence_contract.py`
- `validate_v2_blinded_outcome_export_contract.py`

### Measurement-feasibility pilot

- `build_v2_measurement_feasibility_pilot_manifest.py`
- `build_v2_pilot_quality_execution_manifest.py`
- `run_v2_pilot_quality_measurements.py`
- `build_v2_structural_oracle_annotation_package.py`
- `analyze_v2_structural_oracle_reliability.py`
- `build_v2_reviewer_interface_dry_run.py`
- `audit_v2_reviewer_interface_dry_run.py`
- `validate_v2_reviewer_interface_human_audit.py`

### Full v2 measurement and information partitioning

- `build_v2_full_image_quality_execution_manifest.py`
- `run_v2_full_image_quality_measurements.py`
- `build_v2_full_frame_local_match_control_package.py`
- `build_v2_full_frame_local_match_shards.py`
- `freeze_v2_official_sampling_seed.py`
- `apply_v2_official_image_allocation.py`
- `build_v2_pre_sampling_exclusion_register.py`
- `prepare_v2_image_allocation_strata.py`
- `build_v2_within_role_pair_frames.py`

### Workbook04 / dual-sample confirmation preparation

- `audit_ws04_power_cost_inputs.py` audits authorized pre-outcome inputs.
- `simulate_ws04_power_cost_sensitivity.py` runs nonbinding sensitivity grids.
- `audit_ws04_four_stage_allocation.py` checks the four-stage allocation contract.
- `build_v2_timed_operational_rehearsal.py` builds the current assignment-enforced
  v2 rehearsal package.
- `audit_v2_timed_operational_rehearsal.py` audits operational returns without
  interpreting image outcomes.

The three Workbook04 scripts remain separate because they enforce different
scientific authorization boundaries. Shared helpers are intentionally local and
small; combining the stages would make it easier to cross an outcome/freeze gate
accidentally.

## Historical reproducibility code

Phase 7–19 source bytes and tests are preserved under
`archive/pferi_v1/reproducibility/`, with original paths, hashes, sizes, and the
source commit recorded in the 2026-07-18 phase-code archive manifest. Restore
the original tree in a separate Git worktree when reproducing an old run.

Phase 18–19 joined the same source-hash archive on 19 July 2026 after their
working-tree state was verified clean. No phase-numbered v1 script is an active
PF-ERI v2 entry point.

## Repository maintenance

- `check_codegraph_project_contract.py` verifies the code-navigation boundary.
- `build_project_artifact_consolidation_index.py` indexes retained artifacts.
- `build_project_cleanup_indexes.py` audits artifact organization.
- `cleanup_superseded_artifacts.py` performs allowlisted output cleanup; it is a
  dry run unless `--apply` is supplied and never targets `data/frozen/pferi_v2/`.
- `archive_pferi_v1_phase_code.py` records and isolates inactive Phase 7–19
  source/test bytes; it is also dry-run-first.

Current routing and claim boundaries are defined by
`docs/project-governance/structure/current_pipeline_manifest.md`.
