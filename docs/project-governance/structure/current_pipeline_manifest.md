# Current Pipeline Manifest

Date: 2026-07-01

Purpose: define the active project chain so the large historical repository does
not obscure which scripts, docs, outputs, and tests support the current claim.

This manifest is a navigation and claim-boundary file. It does not replace the
individual phase documentation.

## Current Scientific Chain

```text
legacy-code14 data foundation
-> legacy-code15 evidence-routed review evidence
-> legacy-code16 safeguards, scoring, pair contract, and claim lock
-> legacy-code17 review-utility validation
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
4. `docs/legacy-code16/legacy-code16i_gap_rationale.md`
5. `docs/legacy-code17/README.md`
6. `docs/legacy-code16/README.md`
7. `docs/legacy-code17/czechlynx_high3000_strict_audit.md`
8. `docs/bobcat_photo_selection.md`
9. `docs/structure/2026-07-01_legacy-code17_strict3000_modeling_freeze.md`
10. `docs/structure/2026-07-01_legacy-code18_gap_research_and_plan.md`
11. `docs/structure/2026-07-01_project_triage_and_legacy-code18_execution_issues.md`
12. `docs/legacy-code18/README.md`
13. `scripts/README.md`
14. `docs/structure/csv_and_artifact_inventory.md`
15. `docs/logs/daily_work_log.md`

## Active Scripts

| Layer | Script | Role | Test |
| --- | --- | --- | --- |
| legacy-code16a | `scripts/build_legacy-code16_dataset_foundation_audit.py` | Audit 3000 x 4 dataset foundation before clean modeling claims. | `tests/test_legacy-code16_dataset_foundation_audit.py` |
| legacy-code16 safeguards | `scripts/build_legacy-code16_laterality_aware_pair_audit.py` | Pair-level laterality/comparability diagnostic. | `tests/test_legacy-code16_laterality_logic.py` |
| legacy-code16 safeguards | `scripts/build_legacy-code16_leakage_pressure_audit.py` | Background/site leakage-pressure diagnostic. | `tests/test_legacy-code16_leakage_logic.py` |
| legacy-code16 benchmark | `scripts/package_legacy-code16_strong_model_benchmark.py` | Package strong-model benchmark inputs and pair contract. | Manual/package audit |
| legacy-code16e | `scripts/package_legacy-code16e_candidate_model_filter_colab.py` | Package cloud/local model-scoring runner. | Smoke/package audits |
| legacy-code16e | `scripts/package_legacy-code16e_czechlynx_direct_split_zips.py` | Package CzechLynx direct split zips. | Package audit |
| legacy-code16e | `scripts/recalibrate_legacy-code16e_candidate_scores.py` | Recalibrate candidate scores after model scoring. | Smoke/output audit |
| legacy-code16e2 | `scripts/package_legacy-code16e2_bobcat_20k_candidate_pool.py` | Build Bobcat 20k candidate pool. | Package audit |
| legacy-code16e2 | `scripts/package_legacy-code16e2_bobcat_remaining_local_images.py` | Package remaining Bobcat local image batches. | `tests/test_package_legacy-code16e2_bobcat_remaining_local_images.py` |
| legacy-code16f | `scripts/build_legacy-code16f_czechlynx_constrained_selection.py` | Select constrained CzechLynx 3000 from recalibrated pool. | `tests/test_legacy-code16f_czechlynx_constrained_selection.py` |
| legacy-code16f | `scripts/summarize_legacy-code16f_czechlynx_publication_selection.py` | Generate publication-ready selected-set summaries. | `tests/test_legacy-code16f_czechlynx_publication_summary.py` |
| legacy-code16e Bobcat receiver | `scripts/analyze_legacy-code16e_bobcat_scores.py` | Receive Bobcat scores and run transfer-stress scoring summaries. | `tests/test_legacy-code16e_bobcat_receiver.py` |
| legacy-code16g | `scripts/build_legacy-code16g_pair_feature_schema.py` | Write pair-level schema contract. | `tests/test_legacy-code16g_pair_feature_schema.py` |
| legacy-code16g | `scripts/audit_legacy-code16g_pair_table.py` | Audit pair-table schema and label boundaries. | `tests/test_legacy-code16g_pair_table_audit.py` |
| legacy-code16g | `scripts/run_legacy-code16g_real_czechlynx_pair_table.py` | Build real CzechLynx pair table from legacy-code16f and legacy-code15 candidates. | `tests/test_legacy-code16g_real_czechlynx_pair_table.py` |
| legacy-code16h | `scripts/build_legacy-code16h_czechlynx_readiness_controls.py` | Run descriptor/quality/evidence/random readiness controls. | `tests/test_legacy-code16h_czechlynx_readiness_controls.py` |
| legacy-code16h | `scripts/build_legacy-code16h_czechlynx_calibrated_router.py` | Run leakage-excluded grouped-split calibrated router diagnostics. | `tests/test_legacy-code16h_czechlynx_calibrated_router.py` |
| legacy-code17a | `scripts/build_legacy-code17a_czechlynx_review_utility.py` | Validate locked-gap CzechLynx review utility. | `tests/test_legacy-code17a_czechlynx_review_utility.py` |
| legacy-code17b | `scripts/build_legacy-code17b_bobcat_transfer_stress.py` | Build Bobcat transfer-stress statistics and stratified manual-audit queue. | `tests/test_legacy-code17b_bobcat_transfer_stress.py` |
| legacy-code17c | `scripts/build_legacy-code17c_bobcat_provisional_3000.py` | Build provisional Bobcat 3000 algorithm-prep manifest with clean backbone and transfer sentinels. | `tests/test_legacy-code17c_bobcat_provisional_3000.py` |
| Prototype | `scripts/prototypes/prototype_legacy-code17c_bobcat_3000_logic.py` | Throwaway logic explorer for legacy-code17c clean/sentinel quota choices. | Prototype only |
| legacy-code17d | `scripts/build_legacy-code17d_bobcat_manual_audit_gate.py` | Convert legacy-code17c manual-audit outcomes into a final-freeze decision. | `tests/test_legacy-code17d_bobcat_manual_audit_gate.py` |
| Prototype | `scripts/prototypes/prototype_legacy-code17d_manual_audit_gate.py` | Throwaway logic explorer for legacy-code17d decision states. | Prototype only |
| legacy-code17k | `scripts/build_legacy-code17k_bobcat_clarity_gate.py` | Build the Bobcat clarity-first review pool; metadata discovery is not algorithm-entry quality. | Manual/streamlit review |
| legacy-code17n | `scripts/build_legacy-code17n_bobcat_final3000_seed_from_human_clear.py` | Collect all prior human-confirmed Bobcat clear rows into the locked final-3000 seed. | Output audit |
| Prototype | `scripts/prototypes/prototype_bobcat_photo_selection_subject40_gate.py` | Strict subject-size/clarity rescue logic for Bobcat final top-up queues. | Prototype only |
| Prototype | `scripts/prototypes/prototype_legacy-code17o_bobcat_strict_final902_rescue.py` | Final strict Bobcat rescue queue used to complete the 3,000 clear seed. | Prototype only |
| CzechLynx strict audit | `scripts/prototypes/prototype_czechlynx_high3000_strict_audit.py` | Audit earlier CzechLynx high3000 sets under the Bobcat-style strict clarity rule. | Prototype/output audit |
| CzechLynx strict supplement | `scripts/prototypes/prototype_czechlynx_strict3000_supplement.py` | Rebuild the CzechLynx strict 3,000 review queue from local strict-pass and legacy-code16e re-score pools. | Prototype/output audit |
| CzechLynx clarity augmentation | `scripts/prototypes/prototype_czechlynx_strict3000_clarity_augmentation.py` | Create full-frame mild clarity-enhanced copies and final confirmed CzechLynx manifest. | Prototype/output audit |
| CodeGraph contract | `scripts/check_codegraph_project_contract.py` | Verify CodeGraph root status and exact current-project paths; records the boundary that CodeGraph is code navigation only. | Script exit + audit JSON |
| Structure consolidation | `scripts/build_project_artifact_consolidation_index.py` | Build a non-destructive index classifying legacy-code16/17 output directories as canonical, selection history, or support. | Script exit + audit JSON |
| legacy-code18a | `scripts/build_legacy-code18a_frozen_feature_manifest.py` | Build the first frozen image-level feature manifest with roles, hash/decode verification, and identity boundary fields. | `tests/test_legacy-code18a_frozen_feature_manifest.py` |
| legacy-code18b | `scripts/build_legacy-code18b_local_descriptor_control.py` | Build local descriptor-control embeddings when strong-model dependencies are unavailable. | `tests/test_legacy-code18_pipeline.py` |
| legacy-code18c | `scripts/build_legacy-code18c_czechlynx_pair_contract.py` | Build CzechLynx known-ID top-k pair contracts from legacy-code18b embeddings. | `tests/test_legacy-code18_pipeline.py` |
| legacy-code18d | `scripts/build_legacy-code18d_pf_eri_pair_features.py` | Add PF-ERI 2.0 admissibility, geometry, conflict, and review-score features. | `tests/test_legacy-code18_pipeline.py` |
| legacy-code18e | `scripts/build_legacy-code18e_review_router.py` | Evaluate deterministic local-control review-router policies and threshold curves. | `tests/test_legacy-code18_pipeline.py` |
| legacy-code18f | `scripts/build_legacy-code18f_bobcat_transfer_readiness.py` | Apply unlabeled Bobcat transfer-readiness routing without identity-accuracy claims. | `tests/test_legacy-code18_pipeline.py` |
| legacy-code18g | `scripts/build_legacy-code18g_strong_baseline_claim_gate.py` | Package strong-baseline handoff inputs and block final claims until strong artifacts exist. | `tests/test_legacy-code18_pipeline.py` |
| legacy-code18 all | `scripts/run_legacy-code18_all.py` | Run legacy-code18a-G in dependency order and write an all-step audit. | Script exit + audit JSON |

## Current Generated Outputs

Generated outputs are ignored by git. Their important conclusions must be
summarized in tracked documentation when they become part of the project claim.

Key local output roots:

- `outputs/legacy-code16/legacy-code16e_candidate_model_filter/`
- `outputs/legacy-code16/legacy-code16e_recalibrated_czechlynx_scores/`
- `outputs/legacy-code16/legacy-code16e_czechlynx_analysis/`
- `outputs/legacy-code16/legacy-code16f_czechlynx_constrained_selection/`
- `outputs/legacy-code16/legacy-code16f_czechlynx_publication_summary/`
- `outputs/legacy-code16/legacy-code16g_czechlynx_real_pair_table/`
- `outputs/legacy-code16/legacy-code16h_czechlynx_readiness_controls/`
- `outputs/legacy-code16/legacy-code16h_czechlynx_calibrated_router/`
- `outputs/legacy-code17/legacy-code17a_czechlynx_review_utility/`
- `outputs/legacy-code17/legacy-code17b_bobcat_transfer_stress/`
- `outputs/legacy-code17/legacy-code17c_bobcat_provisional_3000/`
- `outputs/legacy-code17/legacy-code17d_bobcat_manual_audit_gate/`
- `outputs/legacy-code17/legacy-code17n_bobcat_final3000_seed/`
- `outputs/bobcat_photo_selection/`
- `outputs/czechlynx/legacy-code17_strict3000_supplement/`
- `outputs/czechlynx/legacy-code17_strict3000_supplement/augmented/`
- `outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/`
- `outputs/project_structure/codegraph_contract/`
- `outputs/project_structure/artifact_consolidation_index/`
- `outputs/legacy-code18/legacy-code18a_frozen_feature_manifest/`
- `outputs/legacy-code18/legacy-code18b_local_descriptor_control/`
- `outputs/legacy-code18/legacy-code18c_czechlynx_pair_contract/`
- `outputs/legacy-code18/legacy-code18d_pf_eri_pair_features/`
- `outputs/legacy-code18/legacy-code18e_review_router/`
- `outputs/legacy-code18/legacy-code18f_bobcat_transfer_readiness/`
- `outputs/legacy-code18/legacy-code18g_strong_baseline_claim_gate/`
- `outputs/legacy-code18/legacy-code18_all_pipeline/`

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
  `outputs/czechlynx/legacy-code17_strict3000_supplement/augmented/legacy-code17_czechlynx_strict3000_final_confirmed_manifest.csv`;
- boundary: not yet an identity-balanced train/evaluation split.

Bobcat:

- final 3,000 human-clear seed exists after strict clarity rescue/top-up;
- canonical manifest:
  `outputs/legacy-code17/legacy-code17n_bobcat_final3000_seed/legacy-code17n_bobcat_final3000_human_clear_seed_manifest.csv`;
- boundary: Bobcat remains transfer-stress/review-readiness evidence unless
  verified individual labels or audited same/different pair labels are added.

Frozen modeling package:

- status: `FROZEN`;
- rows: 6,000 total, 3,000 Bobcat and 3,000 CzechLynx;
- all frozen files decode successfully;
- canonical combined manifest:
  `outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv`.

## Active Next Step

The repository should now prioritize:

1. using `docs/structure/2026-07-01_legacy-code18_gap_research_and_plan.md` and
   `docs/legacy-code18/README.md` as the
   legacy-code18 design boundary;
2. building the algorithm-entry feature/embedding manifest from the frozen
   package;
3. deriving any identity-balanced CzechLynx subset separately from the
   visual-quality-first manifest if algorithm training/evaluation requires it;
4. keeping Bobcat as an unlabeled transfer-stress/review-readiness set unless
   verified identity labels or audited pair labels are added;
5. keeping the legacy-code16i gap lock stable;
6. treating CodeGraph as code-location support only for data-state questions.

## Rule For Historical Scripts

Top-level historical scripts should not be moved opportunistically during active
analysis. If the project later archives more scripts, first check:

1. imports from current scripts;
2. documentation references;
3. tests;
4. output reproducibility notes.

Until then, this manifest and `scripts/README.md` define what is current.
