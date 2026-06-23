# Phase 12 RQ1-RQ4 Technical Implementation Plan

Date: 2026-06-17

Purpose: define the concrete technical plan for the four research questions in the PF-ERI reliability-aware pairwise evidence learning project.

## Phase 0: Documentation Discovery

Sources consulted:

- `docs/phase12/phase12_pairwise_evidence_learning_roadmap.md`
- `docs/phase11/phase11_pair_reliability_math_spec.md`
- `docs/phase11/phase11_experiment_digest.md`
- `docs/structure/csv_and_artifact_inventory.md`
- `scripts/README.md`
- `scripts/build_phase11_pair_level_pf_eri_table.py`
- `colab/phase11_metric_learning/train_phase11_pair_weighted_metric_learning.py`

Allowed current implementation substrates:

- Pair reliability table builder: `scripts/build_phase11_pair_level_pf_eri_table.py`
- Pair table audit: `scripts/audit_phase11_pair_level_pf_eri_table.py`
- Split diagnostics builder: `scripts/build_phase11c_split_level_diagnostics.py`
- No-training reranking reference: `scripts/phase9b_pf_eri_aware_fixed_descriptor_reranking.py`
- Reranking refinement reference: `scripts/phase9b_r_pf_eri_reranking_refinement.py`
- Phase 11 Colab training entrypoint: `colab/phase11_metric_learning/train_phase11_pair_weighted_metric_learning.py`
- Core pair table output: `outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv`
- Core visual factor input: `data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv`
- Core descriptor input: `outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv`

Anti-patterns to avoid:

- Do not claim PF-ERI identifies individuals.
- Do not treat `pair_reliability_score` as a calibrated probability.
- Do not report mAP/top-1 alone without false burden, positive retention, and query coverage.
- Do not start with more training variants before RQ1/RQ2 diagnostic tables pass.
- Do not move active top-level scripts unless their `Path(__file__).parents[1]` project-root logic is refactored.

## Shared Phase 12A Substrate

Before proving any RQ, build one unified analysis table.

### Table Name

```text
outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table.csv
```

### Required Columns

Identity/evaluation:

- `split_id`
- `query_image_id`
- `candidate_image_id`
- `query_identity`
- `candidate_identity`
- `same_identity`
- `candidate_rank_raw`
- `candidate_rank_pf_eri`
- `is_top1_raw`
- `is_top1_pf_eri`
- `false_candidate`
- `false_top1_raw`
- `false_top1_pf_eri`

Descriptor evidence:

- `descriptor_similarity`
- `descriptor_similarity_percentile`
- `reciprocal_rank_support`
- `margin_confidence`
- `descriptor_disagreement`

PF-ERI evidence:

- `pair_reliability_score`
- `side_comparability_score`
- `pattern_pair_score`
- `blur_pair_score`
- `occlusion_pair_score`
- `body_visibility_pair_score`
- `viewpoint_compatibility_score`
- `image_quality_proxy_min`
- `image_quality_proxy_mean`

Conflict and utility:

- `descriptor_evidence_conflict_score`
- `conflict_band`
- `admissibility_band`
- `candidate_utility_score`
- `review_decision`

### Core Formulas

Pair reliability comes from Phase 11:

```text
R_pair =
  0.30 * side_comparability
+ 0.25 * pattern_pair
+ 0.15 * blur_pair
+ 0.10 * occlusion_pair
+ 0.10 * body_visibility_pair
+ 0.10 * viewpoint_compatibility
```

Descriptor-evidence conflict:

```text
Conflict = descriptor_similarity_percentile * (1 - R_pair)
```

Optional stronger conflict variants:

```text
Conflict_margin = descriptor_similarity_percentile * margin_confidence * (1 - R_pair)
Conflict_disagreement = descriptor_similarity_percentile * descriptor_disagreement * (1 - R_pair)
```

### Verification

- Table exists and row count is nonzero.
- Required columns exist.
- No sensitive raw path/location/GPS/trap fields are exported.
- `pair_reliability_score`, `descriptor_similarity_percentile`, and `descriptor_evidence_conflict_score` are in `[0, 1]`.
- Same/different identity labels are used only for validation metrics.

## RQ1: Evidence Admissibility

Question:

```text
Can image- and pair-level PF-ERI scores predict whether a candidate comparison contains usable patterned-felid identity evidence?
```

### Technical Aim

Prove that PF-ERI pair admissibility is not just generic image quality. It should explain usable Re-ID evidence better than image-only quality proxies.

### Main Predictors

- `pair_reliability_score`
- `admissibility_band`
- `side_comparability_score`
- `pattern_pair_score`
- `image_quality_proxy_min`
- `image_quality_proxy_mean`

### Outcomes

Primary:

- `false_candidate`
- `positive_retention`
- `review_utility`

Secondary:

- `query_coverage`
- `candidate_retention`
- `same_identity_retained`
- `false_candidate_burden`

### Analyses

1. Band analysis:
   - Split pairs into reliability bands: high, medium, low, unusable.
   - Compare false-candidate burden, positive retention, and query coverage by band.

2. Pair-level versus image-level comparison:
   - Compare `pair_reliability_score` against `image_quality_proxy_min` and `image_quality_proxy_mean`.
   - Use paired split-level summaries, not only pooled row-level results.

3. Simple predictive model:
   - Fit logistic or monotonic regression only as an explanatory diagnostic.
   - Predict false-candidate or usable-evidence target from pair reliability and quality-only baselines.
   - Report AUC, calibration caveats, and coefficient direction.

4. Utility analysis:
   - Define review utility as:

```text
review_utility =
  + true_positive_retained_value
  - false_candidate_cost
  - review_workload_cost
  - query_drop_cost
```

   - Sweep utility weights as sensitivity, not as a final universal utility function.

### Success Criteria

RQ1 is supported if:

- higher `pair_reliability_score` is associated with lower false-candidate burden or higher positive retention;
- pair-level reliability outperforms image-only quality proxy on at least one risk/utility metric;
- effects remain visible across held-out splits or query groups.

### Failure Interpretation

If pair reliability does not outperform quality-only proxy, the claim should be weakened:

```text
PF-ERI currently behaves as a structured quality proxy, not yet a distinct pair-admissibility model.
```

## RQ2: Descriptor-Evidence Conflict

Question:

```text
Do high-similarity but low-admissibility pairs explain a distinct class of false Re-ID candidates?
```

### Technical Aim

Identify whether raw descriptor confidence fails in a specific way: high similarity when visual comparability is weak.

### Conflict Definition

Base group:

```text
high descriptor similarity:
  descriptor_similarity_percentile >= 0.90

low admissibility:
  pair_reliability_score <= 0.40

conflict group:
  high descriptor similarity and low admissibility
```

Continuous score:

```text
descriptor_evidence_conflict_score =
  descriptor_similarity_percentile * (1 - pair_reliability_score)
```

### Outcomes

- false-candidate rate;
- false top-1 rate;
- false reviewed candidates per query;
- hard-negative rate;
- positive-pair loss suppression risk.

### Analyses

1. Conflict group comparison:
   - Compare conflict group against high-similarity/high-admissibility and low-similarity groups.
   - Report false-candidate burden and false top-1 rate.

2. Incremental explanatory value:
   - Model A: descriptor similarity only.
   - Model B: descriptor similarity + pair reliability.
   - Model C: descriptor similarity + pair reliability + conflict score.
   - Compare AUC, log loss, and split-level paired differences.

3. Rank-position analysis:
   - For each query, check whether conflict candidates appear near top ranks.
   - Report how many false top-1 or top-5 errors contain high conflict.

4. Visual failure decomposition:
   - Break conflict cases by side mismatch, low pattern visibility, blur, occlusion, body visibility, and viewpoint penalty.

### Success Criteria

RQ2 is supported if:

- conflict group has higher false-candidate or false top-1 risk than descriptor-similar admissible pairs;
- conflict score adds explanatory value beyond descriptor similarity alone;
- conflict cases map to interpretable visual failure modes.

### Failure Interpretation

If conflict score adds no signal:

```text
Descriptor errors may not be mainly driven by visual admissibility conflict in this dataset.
```

Then RQ3 should still test risk-control utility, but RQ4 conflict-aware loss should be postponed.

## RQ3: Risk-Controlled Retrieval

Question:

```text
Can PF-ERI improve risk-coverage tradeoffs compared with raw descriptor ranking, random matched filtering, and quality-only filtering?
```

### Technical Aim

Do not try to prove simple top-1 improvement first. Prove controlled risk reduction:

- lower false burden at the same coverage; or
- higher coverage at the same risk; or
- Pareto improvement across false burden, positive retention, and query coverage.

### Policy Families

Baseline policies:

- raw descriptor ranking;
- random same-size;
- random same-coverage;
- quality-only filtering;
- image-level PF-ERI filtering.

PF-ERI policies:

- pair admissibility filter;
- conflict penalty reranking;
- utility-based reranking;
- review/defer/exclude policy.

### Utility Formula

Start with:

```text
Utility =
  alpha * descriptor_similarity_percentile
+ beta * pair_reliability_score
+ gamma * reciprocal_rank_support
+ delta * margin_confidence
- eta * descriptor_disagreement
- lambda * descriptor_evidence_conflict_score
```

Use small transparent grids, not unconstrained black-box tuning.

### Metrics

Retrieval:

- mAP;
- MRR;
- top-1;
- top-5.

Risk/workload:

- false top-1 rate;
- false-candidate burden;
- false reviewed candidates per query;
- query coverage;
- candidate retention;
- positive retention.

Tradeoff:

- risk-coverage curve;
- fixed-coverage risk;
- fixed-risk coverage;
- Pareto frontier.

### Validation Design

- Tune utility weights on calibration queries only.
- Evaluate on held-out queries or identity-held-out splits.
- Use random same-size and same-coverage controls for every selected policy.
- Report split-level paired differences.

### Success Criteria

RQ3 is supported if PF-ERI policy:

- reduces false-candidate burden at matched coverage; or
- improves coverage at matched risk; or
- is non-dominated on the Pareto frontier;
- while preserving positive retention and avoiding query coverage collapse.

### Failure Interpretation

If PF-ERI only improves metrics by deleting hard examples:

```text
PF-ERI is useful as confidence-control, but not yet as a balanced retrieval-control policy.
```

## RQ4: Reliability-Aware Metric Learning

Question:

```text
Can PF-ERI-conditioned pair weights improve learned retrieval representations by emphasizing admissible positive evidence and controlling unreliable hard negatives?
```

### Technical Aim

Test PF-ERI as a training signal, not as a new image backbone.

Use fixed MegaDescriptor embeddings and a small projection head. Do not fine-tune a large image model.

### Baselines

Required:

- uniform supervised contrastive learning;
- random matched image selection;
- quality-proxy matched image selection;
- PF-ERI image-level selection;
- no-training raw descriptor retrieval;
- no-training PF-ERI reranking reference from RQ3.

### Loss Variants

Start only after RQ1/RQ2 diagnostics pass.

Variant 1: positive reliability weighting.

```text
w_pos = sqrt(R_pair)
```

Reason: Phase 11 showed raw reliability weighting may suppress too much valid variation.

Variant 2: unreliable hard-negative control.

```text
if same_identity == false
and descriptor_similarity_percentile >= 0.90
and R_pair <= 0.40:
    w_neg = lambda_low
else:
    w_neg = 1
```

Use conservative `lambda_low`, such as `0.85`, before stronger downweighting.

Variant 3: conflict-aware negative weighting.

```text
w_neg = 1 - k * descriptor_evidence_conflict_score
```

Clamp to a safe floor:

```text
w_neg >= 0.70
```

Variant 4: positive rescue.

Use only if diagnostics show low-R positive pairs with strong descriptor/pattern support:

```text
same_identity == true
R_pair < threshold
descriptor_similarity high
pattern_pair_score adequate
```

### Training Design

- Use existing `colab/phase11_metric_learning/train_phase11_pair_weighted_metric_learning.py`.
- Add new configs only after RQ1/RQ2/RQ3 tables are audited.
- Use held-out split evaluation.
- Track split-level paired differences.

### Metrics

- mAP;
- MRR;
- top-1;
- top-5;
- false top-1;
- false-candidate burden;
- query coverage;
- stability across splits.

### Success Criteria

RQ4 is supported if PF-ERI-conditioned learning:

- improves held-out retrieval metrics; or
- reduces false-candidate burden; or
- stabilizes weak splits;
- while preserving query coverage and not worsening false burden.

### Failure Interpretation

If training does not improve:

```text
PF-ERI remains valuable as a diagnostic/reranking/risk-control layer, but not as a proven metric-learning signal in the current data setting.
```

## Implementation Phases

### Phase 12A: Unified Pair/Candidate Table

Implement:

- `scripts/build_phase12_pair_candidate_analysis_table.py`
- `scripts/audit_phase12_pair_candidate_analysis_table.py`

Inputs:

- Phase 11 pair table;
- Phase 9/8 candidate ranking outputs;
- Phase 4 descriptor similarities/embeddings;
- identity validation labels.

Outputs:

- `outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table.csv`
- `outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table_audit.csv`

Status:

- Implemented on 2026-06-17.
- The table contains safe image and identity tokens, descriptor ranks, pair reliability components, conflict scores, admissibility bands, top-1 false-candidate flags, and review-decision fields.
- Detection-assisted and domain-shift fields are included only as future-extension placeholders and are not used in Phase 12A scores.

Verification:

- required columns present;
- no sensitive fields;
- valid ranges for scores;
- row counts by split/query/policy.

### Phase 12B: RQ1/RQ2 Diagnostics

Implement:

- `scripts/analyze_phase12_rq1_rq2_evidence_diagnostics.py`

Outputs:

- `outputs/czechlynx/phase12/rq1_admissibility_summary.csv`
- `outputs/czechlynx/phase12/rq2_conflict_summary.csv`
- `docs/phase12/phase12_rq1_rq2_diagnostic_results.md`

Verification:

- split-level summaries exist;
- conflict group counts are nonzero or explicitly reported as sparse;
- quality-only baseline comparison included.

### Phase 12C: Risk-Controlled Retrieval

Implement:

- `scripts/phase12_risk_controlled_retrieval.py`
- `scripts/audit_phase12_risk_controlled_retrieval.py`

Outputs:

- `outputs/czechlynx/phase12/rq3_policy_comparison.csv`
- `outputs/czechlynx/phase12/rq3_risk_coverage_curve.csv`
- `outputs/czechlynx/phase12/rq3_pareto_frontier.csv`
- `docs/phase12/phase12_rq3_risk_controlled_retrieval_results.md`

Verification:

- random same-size and same-coverage controls exist;
- fixed-coverage and fixed-risk summaries exist;
- no selected policy is interpreted without positive retention and query coverage.

### Phase 12D: RQ4 Metric-Learning Extension

Implement only after Phase 12B/12C pass.

Tasks:

- Add conflict-aware columns to Phase 11/Colab configs.
- Add conservative conflict-aware negative weighting mode.
- Run split-level held-out evaluation.

Outputs:

- updated Colab configs under `colab/phase11_metric_learning/` or new `colab/phase12_metric_learning/`;
- `outputs/czechlynx/phase12/rq4_metric_learning_summary.csv`;
- `docs/phase12/phase12_rq4_metric_learning_results.md`.

Verification:

- uniform, random matched, quality-proxy, and no-training baselines included;
- query coverage does not collapse;
- false burden is not materially worse;
- split-level paired differences are reported.

## Final Verification Phase

Before making any scientific claim:

- rerun all audit scripts;
- grep outputs for sensitive fields;
- confirm all selected policies have matched controls;
- confirm no claim says identity recognition, deployment readiness, population estimation, universal threshold, or validated clouded leopard/marbled cat Re-ID;
- update `README.md`, `PROJECT_RULES.md`, and `docs/phase12/phase12_pairwise_evidence_learning_roadmap.md` only with supported conclusions.
