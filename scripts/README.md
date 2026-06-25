# Scripts Map

Date: 2026-06-23

Use this file as a script routing map. The repository contains many historical
scripts because the project direction evolved. The current execution path is
Phase 14 data foundation -> Phase 15 evidence-routed review -> Phase 16
strategy safeguards.

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

Phase 16 scripts are planned in:

```text
docs/superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md
```

They should be added only if they support PF-ERI pair-level evidence modeling,
review routing, risk-controlled evaluation, or necessary data-governance
safeguards.

### Historical / Diagnostic

- Phase 6/8/9/11/12/13 scripts are preserved for reproducing older analyses and
  explaining the modeling direction.
- `scripts/legacy/` contains earlier annotation, CzechLynx, and retrieval
  utilities. Use only when reproducing historical outputs.

## Do Not Treat As Current Main Path

- metric-learning scripts from Phase 9D/10/11;
- one-off annotation utilities;
- old second-review or expanded-pilot package builders;
- scripts under `scripts/legacy/` unless a historical result must be reproduced.

Top-level `scripts/` now contains current core scripts and one direct dependency needed by active reranking code. Historical phase scripts were moved to `scripts/legacy/`.

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
