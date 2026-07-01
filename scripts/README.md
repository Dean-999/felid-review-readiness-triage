# Scripts Map

Date: 2026-07-01

Use this file as a script routing map. The repository contains many historical
scripts because the project direction evolved. The current execution path is
Phase 14 data foundation -> Phase 15 evidence-routed review -> Phase 16
strategy safeguards -> Phase 17 review-utility validation -> strict
Bobcat/CzechLynx image-entry gates.

For the current executable chain, use:

```text
docs/structure/current_pipeline_manifest.md
```

Current freeze builder:

- `freeze_phase17_modeling_dataset.py` - validates the Bobcat and CzechLynx
  strict 3,000 final-entry manifests, downloads/copies all image files into one
  local modeling package, and writes combined manifests, checksums, evidence
  copies, and a freeze audit.
- `check_codegraph_project_contract.py` - verifies the repository CodeGraph
  contract and records that CodeGraph is a code-navigation helper, not a data
  truth source.
- `build_project_artifact_consolidation_index.py` - builds a non-destructive
  Phase16/17 output index so selection-condition experiments are not confused
  with current Phase18 inputs.
- `build_phase18a_frozen_feature_manifest.py` - builds the first Phase18
  algorithm-entry image manifest from the frozen strict 3,000 x 2 package.
- `build_phase18b_local_descriptor_control.py` - builds a local
  pixel/histogram descriptor-control embedding table when strong model
  dependencies are unavailable.
- `build_phase18c_czechlynx_pair_contract.py` - builds CzechLynx known-ID top-k
  pair contracts from Phase18B embeddings.
- `build_phase18d_pf_eri_pair_features.py` - adds PF-ERI 2.0 admissibility,
  geometry, conflict, and review-score features.
- `build_phase18e_review_router.py` - evaluates deterministic local-control
  review-router policies.
- `build_phase18f_bobcat_transfer_readiness.py` - applies transfer-readiness
  routing to unlabeled Bobcat nearest-neighbor pairs without identity claims.
- `run_phase18_all.py` - runs Phase18A-F in dependency order.

## Current Script Layers

### Layer 1: Data Foundation

Use these when rebuilding or auditing the 2x2 wild/urban x high/low evidence
sets:

- `prepare_phase14_*`
- `build_phase14_*`
- `finalize_phase14_*`
- `package_phase14_*`
- `audit_phase14_*`
- `extract_phase14_megadescriptor_embeddings.py`
- `download_phase14_fcf_bobcat_images.py`
- `safe_phase14_disk_cleanup.py`

### Layer 2: Current Modeling

Use these for the active PF-ERI evidence-routed review story:

- `build_phase15_czechlynx_query_benchmark.py`
- `build_phase15_hybrid_routing_policy.py`
- `build_phase15c_repeated_ranker_validation.py`
- `build_phase15d_evidence_routed_review_policy.py`
- `build_phase15e_wild_urban_transfer_stress.py`
- `package_phase15f_bobcat_pair_audit.py`

### Layer 3: Next Strategy

Phase 16 scripts are planned and routed through:

```text
docs/superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md
```

They should be added only if they support PF-ERI pair-level evidence modeling,
review routing, risk-controlled evaluation, or necessary data-governance
safeguards.

Current Phase 16 execution entry points:

- `build_phase16_dataset_foundation_audit.py` - audits whether the 3000 x 4
  image foundation is ready for clean modeling or requires rebuild/top-up.
- `build_phase16_laterality_audit_table.py` and
  `build_phase16_laterality_aware_pair_audit.py` - build laterality audit and
  pair-comparability diagnostics.
- `build_phase16_leakage_pressure_audit.py` - estimates path-derived
  background/site leakage pressure without exposing sensitive locations.
- `package_phase16_strong_model_benchmark.py` - packages the strong-model
  benchmark contract.
- `package_phase16e_candidate_model_filter_colab.py` and
  `package_phase16e_czechlynx_direct_split_zips.py` - package Phase 16E model
  scoring inputs.
- `recalibrate_phase16e_candidate_scores.py` - recomputes strict, balanced, and
  broad score tiers after Phase 16E.
- `build_phase16f_czechlynx_constrained_selection.py` - selects the first
  CzechLynx constrained 3000 candidate set from the balanced recalibrated pool
  with path-group caps, rejected-pool reporting, and manual-audit samples.
- `summarize_phase16f_czechlynx_publication_selection.py` - converts the
  CzechLynx constrained 3000 into compact publication-ready summary tables and
  a methods snippet.
- `analyze_phase16e_bobcat_scores.py` - receives returned Bobcat Phase 16E
  score CSVs, validates handoff columns, runs the existing recalibration tier
  logic, preserves source-tier metadata, and writes transfer-stress summaries.
- `build_phase16g_pair_feature_schema.py` - writes the Phase 16G pair-level
  schema contract used by CzechLynx and later Bobcat pair tables.
- `build_phase16g_czechlynx_pair_prototype.py` - builds a CzechLynx known-ID
  pair-table prototype from Phase 16F selected images and descriptor candidate
  pairs without training a review-router.
- `run_phase16g_real_czechlynx_pair_table.py` - bridges the real Phase 16F
  CzechLynx selected 3000 manifest to Phase 15 descriptor candidate pairs,
  joins optional leakage/laterality flags, and writes the audited Phase 16G
  CzechLynx real pair-table outputs.
- `audit_phase16g_pair_table.py` - audits Phase 16G pair tables for required
  columns, unique pair IDs, self-pairs, split metadata, and Bobcat label-boundary
  violations.
- `build_phase16h_czechlynx_readiness_controls.py` - evaluates CzechLynx
  Phase 16G pair-table readiness before any calibrated review-router training,
  including descriptor-only, quality-only, evidence-only, random same-size,
  risk-coverage, confidence-loop, and leakage-sensitivity controls.
- `build_phase16h_czechlynx_calibrated_router.py` - runs leakage-excluded
  grouped-split calibrated router validation using descriptor-only, quality-only,
  no-training diagnostic, logistic, and interaction-logistic policies; outputs a
  conservative claim gate rather than a performance claim.

Phase 16G prepares pair-level tables and audits for later Phase 16H calibrated
review-router modeling. It does not train the final model and does not support
Bobcat identity-accuracy claims without verified labels or audited same/different
pair labels.

Phase 16H readiness controls are still pre-training diagnostics. They may permit
grouped-split model design, but they do not by themselves establish a PF-ERI
ranking improvement claim over descriptor-only.

Phase 16H calibrated-router validation is also claim-gated. A model with ROC-AUC
or AP signal still cannot be reported as an improvement unless it beats the
descriptor-only review-queue gate under leakage-excluded grouped splits.

### Layer 4: Phase 17 Review Utility

- `build_phase17a_czechlynx_review_utility.py` - evaluates the locked Phase16I
  gap on leakage-excluded CzechLynx known-ID pairs. It reports fixed
  review-budget, fixed positive-retention, abstention/risk-coverage,
  descriptor-evidence conflict enrichment, and proxy review-action outputs. It
  is a review-utility validation, not descriptor replacement or automatic
  identity assignment.
- `build_phase17b_bobcat_transfer_stress.py` - evaluates completed Bobcat
  Phase16E scores as unsupervised transfer-stress and manual-audit routing
  evidence. It reports source-tier distribution diagnostics, non-parametric
  effect sizes, bootstrap intervals, routing summaries, and a stratified
  manual-audit sheet. It does not evaluate Bobcat identity accuracy.
- `build_phase17c_bobcat_provisional_3000.py` - builds the provisional Bobcat
  3000 algorithm-prep manifest from Phase16E/Phase17B scores. It selects a
  Tier 1 clean backbone plus capped Tier 2 transfer sentinels, writes rejected
  pools, balance summaries, and a manual-audit expansion sheet. It is not a
  final identity-labeled high-confidence set.
- `prototypes/prototype_phase17c_bobcat_3000_logic.py` - throwaway logic
  explorer for Phase17C quota choices. Delete or absorb it after the selection
  policy is accepted.
- `build_phase17d_bobcat_manual_audit_gate.py` - converts filled Phase17C
  manual-audit outcomes into `BLOCKED_PENDING_AUDIT`, `PASS`,
  `PASS_WITH_SPLIT`, or `REVISE` final-freeze recommendations. It is a
  review-readiness gate only and does not evaluate Bobcat identity accuracy.
- `streamlit_phase17d_bobcat_manual_audit_app.py` - local Streamlit image-review
  tool for filling the Phase17D Bobcat manual-audit working CSV from public
  `image_uri` links.
- `prototypes/prototype_phase17d_manual_audit_gate.py` - throwaway logic
  explorer for Phase17D final-freeze state transitions. Delete or absorb it
  after the gate policy is accepted.
- `build_phase17k_bobcat_clarity_gate.py` - builds the Bobcat clarity-first
  review pool. It exists because metadata/source-discovery rows were not stable
  enough for algorithm-entry quality.
- `build_phase17n_bobcat_final3000_seed_from_human_clear.py` - collects prior
  human-confirmed Bobcat clear rows into the locked final-3000 seed manifest.
- `prototypes/prototype_bobcat_photo_selection_subject40_gate.py` - strict
  subject-size/clarity prototype used to build high-quality Bobcat rescue
  queues.
- `prototypes/prototype_phase17o_bobcat_strict_final902_rescue.py` - final
  strict Bobcat rescue prototype used to complete the 3,000 clear seed.

### Layer 5: CzechLynx Strict 3000 Final-Ready Set

- `prototypes/prototype_czechlynx_high3000_strict_audit.py` - audits older
  CzechLynx high3000 artifacts under the Bobcat-style clarity standard.
- `prototypes/prototype_czechlynx_strict3000_supplement.py` - rebuilds a strict
  3,000-row CzechLynx review queue from local strict-pass rows and Phase16E
  detector/IQA re-scoring.
- `prototypes/prototype_czechlynx_strict3000_clarity_augmentation.py` - writes
  full-frame mild clarity-enhanced copies and the final confirmed CzechLynx
  manifest.

The CzechLynx strict 3,000 is currently a visual-quality-first final-freeze
candidate. It is not automatically an identity-balanced training/evaluation
split.

### Historical / Diagnostic

- Phase 6/8/9/11/12/13 scripts are preserved for reproducing older analyses and
  explaining the modeling direction.
- `scripts/legacy/` contains earlier annotation, CzechLynx, and retrieval
  utilities. Use only when reproducing historical outputs.
- `scripts/prototypes/` contains throwaway logic/data prototypes. Some are
  currently important because they generated final-entry manifests; treat the
  documentation and output audits as the durable record, not the prototype
  location as a long-term architecture decision.

## Do Not Treat As Current Main Path

- metric-learning scripts from Phase 9D/10/11;
- one-off annotation utilities;
- old second-review or expanded-pilot package builders;
- scripts under `scripts/legacy/` unless a historical result must be reproduced.

Top-level `scripts/` contains current core scripts plus older support and
historical scripts that have not yet been moved because imports, docs, and
reproducibility references must be checked first. Treat
`docs/structure/current_pipeline_manifest.md` as the current-script boundary.

### Layer 6: Phase18 Algorithm Entry And Pair-Level Modeling

- `check_codegraph_project_contract.py` - run when CodeGraph behavior is in
  doubt; exact paths and artifact audits remain the current-state authority.
- `build_project_artifact_consolidation_index.py` - run before structural
  cleanup discussions; it classifies Phase16/17 directories without moving or
  deleting them.
- `build_phase18a_frozen_feature_manifest.py` - the Phase18A entry script. It
  verifies frozen image hashes, bytes, decode status, dimensions, modeling role,
  and known-identity boundary.
- `build_phase18b_local_descriptor_control.py` - local-control descriptor
  extraction. This is not a strong descriptor baseline; use it to keep the
  Phase18 chain executable until MegaDescriptor/WildFusion dependencies are
  installed.
- `build_phase18c_czechlynx_pair_contract.py` - CzechLynx known-ID top-k pair
  contract.
- `build_phase18d_pf_eri_pair_features.py` - pair-level PF-ERI 2.0 feature
  table.
- `build_phase18e_review_router.py` - no-training deterministic router
  evaluation and threshold curves.
- `build_phase18f_bobcat_transfer_readiness.py` - Bobcat transfer-readiness
  application without Bobcat identity validation.
- `run_phase18_all.py` - one-command Phase18A-F automation.

## Top-Level Core

- `audit_phase14_uwin_bobcat_inventory.py` - scans local tabular/source files for UWIN bobcat metadata availability without exposing sensitive path/location values.
- `audit_phase14_uwin_bobcat_inventory_outputs.py` - audits Phase 14 UWIN inventory outputs and claim-boundary safety.
- `build_phase14_cross_context_evidence_table.py` - builds the Phase 14 shared CzechLynx/UWIN evidence schema, with CzechLynx-only dry-run support.
- `audit_phase14_cross_context_evidence_table.py` - audits the Phase 14 shared evidence table for schema completeness and sensitive-field leakage.
- `prepare_phase14_czechlynx_3000_manifest.py` - builds the identity-balanced 3000-image CzechLynx Phase 14 manifest from the existing 1000 labeled rows plus 2000 additional raw images.
- `build_phase14_czechlynx_3000_auto_prefeatures.py` - computes bobcat-compatible automated image prefeatures for the CzechLynx 3000-image wild known-ID set.
- `fill_phase14_czechlynx_3000_review_labels.py` - combines existing 1000 CzechLynx human labels with AI first-pass labels for the 2000 new Phase 14 images.
- `refine_phase14_czechlynx_3000_review_confidence.py` - refines CzechLynx AI first-pass confidence while preserving true low-confidence rows for human review.
- `refine_phase14_czechlynx_manual_review_with_pose.py` - uses CzechLynx pose keypoints to refine low-confidence Phase 14 labels before human review.
- `package_phase14_czechlynx_3000_manual_review.py` - packages CzechLynx refined low-confidence rows into 100-image zip batches with a blank manual-review template.
- `prepare_phase14_fcf_bobcat_manifest.py` - prepares the public FCF/LILA bobcat full manifest and deterministic 3000-image sample manifest.
- `download_phase14_fcf_bobcat_images.py` - downloads the Phase 14 FCF/LILA 3000-image bobcat stress-test set with retries and fallback URLs.
- `repair_phase14_fcf_bobcat_manifest.py` - replaces unreadable FCF bobcat sample rows from the full manifest.
- `build_phase14_fcf_bobcat_auto_prefeatures.py` - computes automated image-quality/evidence prefeatures and provisional review buckets for all 3000 FCF bobcat images.
- `prepare_phase14_fcf_bobcat_review_batch.py` - creates the 400-image human-review manifest from the machine-prefeature table.
- `audit_phase14_fcf_bobcat_prefeatures.py` - audits FCF bobcat prefeatures, image availability, and human-review batch integrity.
- `fill_phase14_fcf_bobcat_review_labels.py` - fills FCF bobcat review/evidence tables with AI first-pass evidence labels and flags low-confidence rows for human checking; used for both 400-image audit batches and the full 3000-image stress-test set.
- `refine_phase14_fcf_bobcat_review_confidence.py` - refines full-set FCF bobcat AI confidence by promoting stable boundary-only cases while preserving genuinely risky low-confidence rows for human review.
- `prioritize_phase14_fcf_bobcat_manual_checks.py` - creates highest-priority manual-check subsets from AI-filled FCF bobcat review labels, including the 120-row pilot subset and 300/600/1000-row full-set review tiers.
- `package_phase14_fcf_bobcat_refined_manual_review.py` - packages the 1126 refined low-confidence FCF bobcat rows into 100-image zip batches with per-batch manifests and a combined review CSV.
- `audit_phase14_fcf_bobcat_ai_review_labels.py` - audits allowed values, missing fields, confidence flags, row counts, and manual-check subset integrity for AI-filled FCF bobcat review labels.
- `build_phase12_pair_candidate_analysis_table.py` - builds the Phase 12A unified pair/candidate analysis table for RQ1-RQ4.
- `audit_phase12_pair_candidate_analysis_table.py` - audits the Phase 12A unified pair/candidate analysis table.
- `build_phase12_rq1_rq3_evidence_analysis.py` - builds Phase 12B RQ1-RQ3 evidence summaries from the unified candidate table.
- `audit_phase12_rq1_rq3_evidence_analysis.py` - audits Phase 12B evidence summaries.
- `build_phase12c_confidence_evidence.py` - builds split-paired confidence intervals, top-k burden, reliability threshold, conflict enrichment, and random-control evidence.
- `audit_phase12c_confidence_evidence.py` - audits Phase 12C confidence evidence outputs.
- `build_phase12d_failure_diagnosis_and_policy_revision.py` - diagnoses why Phase 12 effects are modest and tests held-out policy revisions.
- `audit_phase12d_failure_diagnosis_and_policy_revision.py` - audits Phase 12D failure diagnosis and policy revision outputs.
- `build_phase13_learned_candidate_utility.py` - trains held-out learned candidate-utility models for Phase 13 and compares them with raw descriptor, fixed PF-ERI, quality-only, and conflict-penalty controls.
- `audit_phase13_learned_candidate_utility.py` - audits Phase 13 learned candidate-utility outputs.
- `build_phase13b_quality_boundary_diagnosis.py` - diagnoses when learned PF-ERI rescues or harms queries relative to learned quality-control and fixed PF-ERI.
- `audit_phase13b_quality_boundary_diagnosis.py` - audits Phase 13B quality-boundary diagnosis outputs.
- `build_phase13c_rq4_training_control_manifest.py` - builds the RQ4 reliability-aware pair-training control manifest with descriptor-only, random, quality, PF-ERI, and conflict-aware policies.
- `audit_phase13c_rq4_training_control_manifest.py` - audits Phase 13C RQ4 training-control manifest outputs.
- `build_phase13d_rq4_fixed_embedding_training.py` - runs local RQ4 fixed-embedding projection-head sanity training plus simulated loss-exposure diagnostics.
- `audit_phase13d_rq4_fixed_embedding_training.py` - audits Phase 13D RQ4 fixed-embedding training sanity outputs.
- `summarize_phase13d_rq4_fixed_embedding_training.py` - summarizes paired Phase 13D policy contrasts across one or more split/descriptor retrieval metric files.
- `run_phase13d_rq4_multi_split.py` - runs Phase 13D across multiple split/descriptor combinations and writes aggregate confidence tables.
- `audit_phase13e_rq4_identity_split_disjointness.py` - audits whether Phase 13 RQ4 calibration/evaluation splits are identity-disjoint before any held-out identity training claim.
- `prepare_phase7a_1000_reid_inputs.py` - builds the 1000-image identity table and embedding manifests from Phase 4 plus Phase 6 v2 labels.
- `extract_phase7a_phase6_embeddings.py` - extracts Phase 6 v2 MegaDescriptor/ResNet50 embeddings and merges 1000-image descriptor files.
- `audit_phase7a_1000_reid_inputs.py` - audits the 1000-image identity, annotation, image-path, and embedding alignment needed by Phase 12A.
- `build_phase11_pair_level_pf_eri_table.py` - builds the current pair-level PF-ERI reliability table.
- `audit_phase11_pair_level_pf_eri_table.py` - audits the pair table.
- `build_phase11c_split_level_diagnostics.py` - builds split-level diagnostics.
- `audit_phase11c_split_level_diagnostics.py` - audits split diagnostics.
- `phase9b_pf_eri_aware_fixed_descriptor_reranking.py` - no-training PF-ERI-aware reranking.
- `phase9b_r_pf_eri_reranking_refinement.py` - refined reranking reference.
- `audit_phase9b_pf_eri_aware_fixed_descriptor_reranking.py` - audits Phase 9B.
- `audit_phase9b_r_pf_eri_reranking_refinement.py` - audits Phase 9B-R.
- `phase8_pf_eri_retrieval_control_v2_optimizer.py` - retained because Phase 9B imports helper functions from it.

## Legacy

`scripts/legacy/` contains old phase scripts, annotation utilities, packaging scripts, preview scripts, and historical audits. Use them only when reproducing an older phase. They are not current implementation entry points.
## Phase 15 Evidence-Routed Review Layer

- `build_phase15_czechlynx_query_benchmark.py`
  - Builds the CzechLynx query-level fixed MegaDescriptor top-k baseline.
  - Uses existing Phase 14 2x2 working-final images and embeddings.
  - Performs no model training.
  - Outputs query top-k candidates, query summaries, descriptor metrics, a
    Markdown report, and an audit JSON under
    `outputs/phase15/query_level_benchmark/`.
- `build_phase15_hybrid_routing_policy.py`
  - Adds PF-ERI pair comparability, quality controls, and descriptor-evidence
    conflict to the CzechLynx top-k candidate table.
  - Evaluates descriptor-only, quality-only, PF-ERI-only, hand-written hybrid
    gates, and hand-written evidence-aware reranking.
  - Performs no model training.
  - Outputs routing inputs, policy evaluation, Pareto candidates, a Markdown
    report, and an audit JSON under
    `outputs/phase15/hybrid_routing_policy/`.
- `build_phase15c_repeated_ranker_validation.py`
  - Runs repeated held-out query-split validation for calibrated PF-ERI/quality
    candidate rankers.
  - Reports model-level ROC-AUC/AP, top-k review-queue burden, subgroup
    behavior, risk-coverage curves, and permutation importance.
  - Outputs reports and tables under
    `outputs/phase15/repeated_ranker_validation/`.
- `build_phase15d_evidence_routed_review_policy.py`
  - Converts Phase 15C repeated-validation evidence into an operational
    five-action review-routing table.
  - Fits a final HGB ranker on all CzechLynx known-ID candidate pairs for score
    export only; this is not a new held-out validation result.
  - Outputs accept, review, defer, species-level-only, and non-comparable
    actions under `outputs/phase15/evidence_routed_review_policy/`.
- `build_phase15e_wild_urban_transfer_stress.py`
  - Applies the CzechLynx-calibrated evidence-routing policy to urban/peri-urban
    bobcat candidate pairs.
  - Builds bobcat top-50 MegaDescriptor candidate pairs, computes PF-ERI/quality
    pair features, and exports five-action review-routing stress outputs.
  - Does not evaluate bobcat identity accuracy because verified bobcat
    individual labels are unavailable.
  - Outputs under `outputs/phase15/wild_urban_transfer_stress/`.
- `package_phase15f_bobcat_pair_audit.py`
  - Builds the 250-pair bobcat manual-audit package from Phase 15E actions.
  - Samples 50 pairs per action and creates side-by-side pair sheets plus a
    blank manual-review template.
  - Outputs under `outputs/phase15/bobcat_pair_audit_package/`.

Training-related next step:

- `colab/phase15_calibrated_ranker_colab.py`
  - Optional Colab/Kaggle script for held-out query-split calibrated ranker
    training.
  - Use only after reviewing the no-training Phase 15 routing results.
  - Must beat descriptor-only and quality/PF-ERI controls before any trained
    improvement claim is allowed.
