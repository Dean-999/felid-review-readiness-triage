# Current Pipeline Manifest

Date: 2026-07-01

Purpose: define the active project chain so the large historical repository does
not obscure which scripts, docs, outputs, and tests support the current claim.

This manifest is a navigation and claim-boundary file. It does not replace the
individual phase documentation.

## Current Scientific Chain

```text
Phase14 data foundation
-> Phase15 evidence-routed review evidence
-> Phase16 safeguards, scoring, pair contract, and claim lock
-> Phase17 review-utility validation
-> Bobcat/CzechLynx strict image-entry gates
-> final-freeze candidate manifests
```

The active claim is PF-ERI as a post-retrieval pair-level evidence reliability
and review-routing layer.

The active claim is not descriptor replacement, top-k ranking superiority,
automatic identity assignment, or Bobcat identity accuracy without verified
identity labels or audited same/different pair labels.

## Canonical Read Order

1. `README.md`
2. `PROJECT_RULES.md`
3. `docs/CURRENT_PROJECT_MAP.md`
4. `docs/phase16/phase16i_gap_rationale.md`
5. `docs/phase17/README.md`
6. `docs/phase16/README.md`
7. `docs/phase17/czechlynx_high3000_strict_audit.md`
8. `docs/bobcat_photo_selection.md`
9. `docs/structure/2026-07-01_phase17_strict3000_modeling_freeze.md`
10. `docs/structure/2026-07-01_phase18_gap_research_and_plan.md`
11. `docs/structure/2026-07-01_project_triage_and_phase18_execution_issues.md`
12. `docs/phase18/README.md`
13. `scripts/README.md`
14. `docs/structure/csv_and_artifact_inventory.md`
15. `docs/logs/daily_work_log.md`

## Active Scripts

| Layer | Script | Role | Test |
| --- | --- | --- | --- |
| Phase16A | `scripts/build_phase16_dataset_foundation_audit.py` | Audit 3000 x 4 dataset foundation before clean modeling claims. | `tests/test_phase16_dataset_foundation_audit.py` |
| Phase16 safeguards | `scripts/build_phase16_laterality_aware_pair_audit.py` | Pair-level laterality/comparability diagnostic. | `tests/test_phase16_laterality_logic.py` |
| Phase16 safeguards | `scripts/build_phase16_leakage_pressure_audit.py` | Background/site leakage-pressure diagnostic. | `tests/test_phase16_leakage_logic.py` |
| Phase16 benchmark | `scripts/package_phase16_strong_model_benchmark.py` | Package strong-model benchmark inputs and pair contract. | Manual/package audit |
| Phase16E | `scripts/package_phase16e_candidate_model_filter_colab.py` | Package cloud/local model-scoring runner. | Smoke/package audits |
| Phase16E | `scripts/package_phase16e_czechlynx_direct_split_zips.py` | Package CzechLynx direct split zips. | Package audit |
| Phase16E | `scripts/recalibrate_phase16e_candidate_scores.py` | Recalibrate candidate scores after model scoring. | Smoke/output audit |
| Phase16E2 | `scripts/package_phase16e2_bobcat_20k_candidate_pool.py` | Build Bobcat 20k candidate pool. | Package audit |
| Phase16E2 | `scripts/package_phase16e2_bobcat_remaining_local_images.py` | Package remaining Bobcat local image batches. | `tests/test_package_phase16e2_bobcat_remaining_local_images.py` |
| Phase16F | `scripts/build_phase16f_czechlynx_constrained_selection.py` | Select constrained CzechLynx 3000 from recalibrated pool. | `tests/test_phase16f_czechlynx_constrained_selection.py` |
| Phase16F | `scripts/summarize_phase16f_czechlynx_publication_selection.py` | Generate publication-ready selected-set summaries. | `tests/test_phase16f_czechlynx_publication_summary.py` |
| Phase16E Bobcat receiver | `scripts/analyze_phase16e_bobcat_scores.py` | Receive Bobcat scores and run transfer-stress scoring summaries. | `tests/test_phase16e_bobcat_receiver.py` |
| Phase16G | `scripts/build_phase16g_pair_feature_schema.py` | Write pair-level schema contract. | `tests/test_phase16g_pair_feature_schema.py` |
| Phase16G | `scripts/audit_phase16g_pair_table.py` | Audit pair-table schema and label boundaries. | `tests/test_phase16g_pair_table_audit.py` |
| Phase16G | `scripts/run_phase16g_real_czechlynx_pair_table.py` | Build real CzechLynx pair table from Phase16F and Phase15 candidates. | `tests/test_phase16g_real_czechlynx_pair_table.py` |
| Phase16H | `scripts/build_phase16h_czechlynx_readiness_controls.py` | Run descriptor/quality/evidence/random readiness controls. | `tests/test_phase16h_czechlynx_readiness_controls.py` |
| Phase16H | `scripts/build_phase16h_czechlynx_calibrated_router.py` | Run leakage-excluded grouped-split calibrated router diagnostics. | `tests/test_phase16h_czechlynx_calibrated_router.py` |
| Phase17A | `scripts/build_phase17a_czechlynx_review_utility.py` | Validate locked-gap CzechLynx review utility. | `tests/test_phase17a_czechlynx_review_utility.py` |
| Phase17B | `scripts/build_phase17b_bobcat_transfer_stress.py` | Build Bobcat transfer-stress statistics and stratified manual-audit queue. | `tests/test_phase17b_bobcat_transfer_stress.py` |
| Phase17C | `scripts/build_phase17c_bobcat_provisional_3000.py` | Build provisional Bobcat 3000 algorithm-prep manifest with clean backbone and transfer sentinels. | `tests/test_phase17c_bobcat_provisional_3000.py` |
| Prototype | `scripts/prototypes/prototype_phase17c_bobcat_3000_logic.py` | Throwaway logic explorer for Phase17C clean/sentinel quota choices. | Prototype only |
| Phase17D | `scripts/build_phase17d_bobcat_manual_audit_gate.py` | Convert Phase17C manual-audit outcomes into a final-freeze decision. | `tests/test_phase17d_bobcat_manual_audit_gate.py` |
| Prototype | `scripts/prototypes/prototype_phase17d_manual_audit_gate.py` | Throwaway logic explorer for Phase17D decision states. | Prototype only |
| Phase17K | `scripts/build_phase17k_bobcat_clarity_gate.py` | Build the Bobcat clarity-first review pool; metadata discovery is not algorithm-entry quality. | Manual/streamlit review |
| Phase17N | `scripts/build_phase17n_bobcat_final3000_seed_from_human_clear.py` | Collect all prior human-confirmed Bobcat clear rows into the locked final-3000 seed. | Output audit |
| Prototype | `scripts/prototypes/prototype_bobcat_photo_selection_subject40_gate.py` | Strict subject-size/clarity rescue logic for Bobcat final top-up queues. | Prototype only |
| Prototype | `scripts/prototypes/prototype_phase17o_bobcat_strict_final902_rescue.py` | Final strict Bobcat rescue queue used to complete the 3,000 clear seed. | Prototype only |
| CzechLynx strict audit | `scripts/prototypes/prototype_czechlynx_high3000_strict_audit.py` | Audit earlier CzechLynx high3000 sets under the Bobcat-style strict clarity rule. | Prototype/output audit |
| CzechLynx strict supplement | `scripts/prototypes/prototype_czechlynx_strict3000_supplement.py` | Rebuild the CzechLynx strict 3,000 review queue from local strict-pass and Phase16E re-score pools. | Prototype/output audit |
| CzechLynx clarity augmentation | `scripts/prototypes/prototype_czechlynx_strict3000_clarity_augmentation.py` | Create full-frame mild clarity-enhanced copies and final confirmed CzechLynx manifest. | Prototype/output audit |
| CodeGraph contract | `scripts/check_codegraph_project_contract.py` | Verify CodeGraph root status and exact current-project paths; records the boundary that CodeGraph is code navigation only. | Script exit + audit JSON |
| Structure consolidation | `scripts/build_project_artifact_consolidation_index.py` | Build a non-destructive index classifying Phase16/17 output directories as canonical, selection history, or support. | Script exit + audit JSON |
| Phase18A | `scripts/build_phase18a_frozen_feature_manifest.py` | Build the first frozen image-level feature manifest with roles, hash/decode verification, and identity boundary fields. | `tests/test_phase18a_frozen_feature_manifest.py` |
| Phase18B | `scripts/build_phase18b_local_descriptor_control.py` | Build local descriptor-control embeddings when strong-model dependencies are unavailable. | `tests/test_phase18_pipeline.py` |
| Phase18C | `scripts/build_phase18c_czechlynx_pair_contract.py` | Build CzechLynx known-ID top-k pair contracts from Phase18B embeddings. | `tests/test_phase18_pipeline.py` |
| Phase18D | `scripts/build_phase18d_pf_eri_pair_features.py` | Add PF-ERI 2.0 admissibility, geometry, conflict, and review-score features. | `tests/test_phase18_pipeline.py` |
| Phase18E | `scripts/build_phase18e_review_router.py` | Evaluate deterministic local-control review-router policies and threshold curves. | `tests/test_phase18_pipeline.py` |
| Phase18F | `scripts/build_phase18f_bobcat_transfer_readiness.py` | Apply unlabeled Bobcat transfer-readiness routing without identity-accuracy claims. | `tests/test_phase18_pipeline.py` |
| Phase18 all | `scripts/run_phase18_all.py` | Run Phase18A-F in dependency order and write an all-step audit. | Script exit + audit JSON |

## Current Generated Outputs

Generated outputs are ignored by git. Their important conclusions must be
summarized in tracked documentation when they become part of the project claim.

Key local output roots:

- `outputs/phase16/phase16e_candidate_model_filter/`
- `outputs/phase16/phase16e_recalibrated_czechlynx_scores/`
- `outputs/phase16/phase16e_czechlynx_analysis/`
- `outputs/phase16/phase16f_czechlynx_constrained_selection/`
- `outputs/phase16/phase16f_czechlynx_publication_summary/`
- `outputs/phase16/phase16g_czechlynx_real_pair_table/`
- `outputs/phase16/phase16h_czechlynx_readiness_controls/`
- `outputs/phase16/phase16h_czechlynx_calibrated_router/`
- `outputs/phase17/phase17a_czechlynx_review_utility/`
- `outputs/phase17/phase17b_bobcat_transfer_stress/`
- `outputs/phase17/phase17c_bobcat_provisional_3000/`
- `outputs/phase17/phase17d_bobcat_manual_audit_gate/`
- `outputs/phase17/phase17n_bobcat_final3000_seed/`
- `outputs/bobcat_photo_selection/`
- `outputs/czechlynx/phase17_strict3000_supplement/`
- `outputs/czechlynx/phase17_strict3000_supplement/augmented/`
- `outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701/`
- `outputs/project_structure/codegraph_contract/`
- `outputs/project_structure/artifact_consolidation_index/`
- `outputs/phase18/phase18a_frozen_feature_manifest/`
- `outputs/phase18/phase18b_local_descriptor_control/`
- `outputs/phase18/phase18c_czechlynx_pair_contract/`
- `outputs/phase18/phase18d_pf_eri_pair_features/`
- `outputs/phase18/phase18e_review_router/`
- `outputs/phase18/phase18f_bobcat_transfer_readiness/`
- `outputs/phase18/phase18_all_pipeline/`

## Current Data/Artifact Status

- `data/` remains a local data store and should not be treated as generally
  committed source code.
- The tracked CzechLynx label CSV under
  `data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_v1.csv`
  is a deliberate historical label artifact until it is either documented as a
  fixture or migrated to a clearer metadata/fixture path.
- `sources/` is a tracked literature/source-evidence cache that supports the gap
  rationale and should be cited through summaries, not treated as active model
  outputs.

## Current Final-Entry Status

CzechLynx:

- final-freeze candidate exists as a human-reviewed, strict-gated,
  clarity-augmented, visual-quality-first 3,000;
- canonical manifest:
  `outputs/czechlynx/phase17_strict3000_supplement/augmented/phase17_czechlynx_strict3000_final_confirmed_manifest.csv`;
- boundary: not yet an identity-balanced train/evaluation split.

Bobcat:

- final 3,000 human-clear seed exists after strict clarity rescue/top-up;
- canonical manifest:
  `outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_manifest.csv`;
- boundary: Bobcat remains transfer-stress/review-readiness evidence unless
  verified individual labels or audited same/different pair labels are added.

Frozen modeling package:

- status: `FROZEN`;
- rows: 6,000 total, 3,000 Bobcat and 3,000 CzechLynx;
- all frozen files decode successfully;
- canonical combined manifest:
  `outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv`.

## Active Next Step

The repository should now prioritize:

1. using `docs/structure/2026-07-01_phase18_gap_research_and_plan.md` and
   `docs/phase18/README.md` as the
   Phase18 design boundary;
2. building the algorithm-entry feature/embedding manifest from the frozen
   package;
3. deriving any identity-balanced CzechLynx subset separately from the
   visual-quality-first manifest if algorithm training/evaluation requires it;
4. keeping Bobcat as an unlabeled transfer-stress/review-readiness set unless
   verified identity labels or audited pair labels are added;
5. keeping the Phase16I gap lock stable;
6. treating CodeGraph as code-location support only for data-state questions.

## Rule For Historical Scripts

Top-level historical scripts should not be moved opportunistically during active
analysis. If the project later archives more scripts, first check:

1. imports from current scripts;
2. documentation references;
3. tests;
4. output reproducibility notes.

Until then, this manifest and `scripts/README.md` define what is current.
