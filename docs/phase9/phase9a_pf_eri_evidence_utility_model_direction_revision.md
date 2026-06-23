# Phase 9A PF-ERI Evidence Utility Model Direction Revision

## 1. Why the Direction Is Revised

Phase 8 clarified an important boundary. Simple PF-ERI filtering reduced false-candidate burden, and downstream sensitivity simulation showed lower simulated identity-record contamination pressure. However, query-level held-out evaluation did not show robust fixed-descriptor Re-ID accuracy improvement beyond repeated random same-size controls.

That means the project should not end as a human-review assistant, a review-only policy, or a false-candidate burden reduction report. Those are useful foundations, but they are not the strongest technical goal.

The revised direction was initially:

```text
PF-ERI Evidence Utility Model for Automated Patterned-Felid Re-ID Enhancement
```

After the Phase 11/RQ4 planning revision, the stronger direction is:

```text
PF-ERI Reliability-Aware Pairwise Evidence Learning for Patterned-Felid Re-ID
```

The core interpretation is:

```text
PF-ERI contains useful reliability signals, but simple hard filtering is not enough. The next scientific test is whether pair-level evidence admissibility can explain false candidates, improve risk-coverage tradeoffs, and provide useful metric-learning weights under strict held-out and matched-control safeguards.
```

## 2. New Main Goal

Revised goal:

```text
To develop and evaluate PF-ERI as a reliability-aware pairwise evidence model that estimates whether camera-trap image pairs contain admissible patterned-felid individual-identification evidence, then uses that signal for risk-constrained retrieval, descriptor-evidence conflict control, and evidence-conditioned metric learning under imperfect camera-trap conditions.
```

Short version:

```text
PF-ERI is a pair-level evidence admissibility and reliability-aware learning model, not just a review filter.
```

## 3. Old Framing Versus New Framing

| Aspect | Old review-control framing | Revised Phase 9 framing |
|---|---|---|
| Main role | Decide review/defer/exclude tiers. | Score image, pair, and candidate evidence utility for fixed-descriptor Re-ID enhancement. |
| Primary output | Review-control policy. | Utility scores and reranking/filtering/weighting decisions. |
| Technical endpoint | Human-review prioritization and false-candidate burden reduction. | Automated fixed-descriptor reranking first; later lightweight utility learning only if justified. |
| Phase 8 interpretation | Supported conservative review-control value. | Diagnostic foundation showing reliability signal exists but simple filtering is insufficient. |
| Main next test | More policy refinement. | PF-ERI-aware fixed-descriptor reranking against raw, filtered, random same-size, and random same-coverage controls. |

The old framing is not wrong; it is incomplete. Review/defer/exclude remains a workflow-safety layer, but it should not be treated as the final algorithmic contribution.

## 4. Final Definition

**PF-ERI Evidence Utility Model** is an interpretable, staged evidence utility model for patterned-felid Re-ID under imperfect camera-trap evidence. It estimates whether images, query-gallery pairs, and descriptor-generated candidates contain useful individual-identification evidence, then uses that utility estimate to filter, weight, rerank, or later support learning around fixed Re-ID descriptors.

PF-ERI is:

- an image-level visual evidence utility score;
- a pair-level evidence reliability score;
- a candidate utility / reranking layer;
- a calibration and risk-coverage evaluation framework;
- a future weighting signal for lightweight learning if fixed reranking succeeds.

PF-ERI is not:

- a new Re-ID descriptor;
- a deep Re-ID model;
- an automatic true-identity decision system;
- a population-estimation method;
- a field-deployment system;
- a universal animal Re-ID reliability score.

## 5. Image-Level Score Design

The image-level score asks:

```text
Does this image contain useful patterned-felid identity evidence for Re-ID?
```

Candidate design:

```text
R_image =
  visual_admissibility(pattern_visibility,
                       side_visibility,
                       side_evidence_quality,
                       body_fraction_visible)
  - visual_failure_penalty(blur_level,
                           occlusion_level,
                           lighting_condition,
                           night_ir_artifact,
                           partial_body,
                           frontal_or_rear_view,
                           silhouette_only,
                           uncertainty_flag)
```

Available image-level visual signals:

| Signal | Available source |
|---|---|
| `pattern_visibility` | `data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv`; Phase 4/5 annotated files |
| `side_visibility` | Phase 7A and Phase 4 visual annotation files |
| `side_evidence_quality` | Phase 7A and Phase 4 visual annotation files |
| `body_fraction_visible` | Phase 7A and Phase 4 visual annotation files |
| `blur_level` | Phase 7A and Phase 4 visual annotation files |
| `occlusion_level` | Phase 7A and Phase 4 visual annotation files |
| `lighting_condition` | Phase 7A and Phase 4 visual annotation files |
| `night_ir_artifact` | Phase 7A and Phase 4 visual annotation files |
| `partial_body` | Phase 7A and Phase 4 visual annotation files |
| `frontal_or_rear_view` | Phase 7A and Phase 4 visual annotation files |
| `silhouette_only` | Phase 7A and Phase 4 visual annotation files |
| `primary_limiting_factor` | Phase 7A and Phase 4 visual annotation files |
| `uncertainty_flag` | Phase 7A and Phase 4 visual annotation files |

Primary rule:

```text
R_image must remain interpretable and visual-first. Descriptor similarity must not be included in R_image.
```

## 6. Pair-Level Score Design

The pair-level score asks:

```text
Is this query-gallery pair visually and descriptor-wise reliable enough for Re-ID comparison?
```

Candidate design:

```text
R_pair(q, g) =
  w_visual * min(R_image(q), R_image(g))
  + w_support * descriptor_support(q, g)
  + w_reciprocal * reciprocal_support(q, g)
  + w_margin * margin_confidence(q, g)
  - w_disagree * descriptor_disagreement(q, g)
  - w_failure * visual_failure_penalty(q, g)
```

Available pair-level signals:

| Signal | Available source |
|---|---|
| `pair_min_score`, `pair_mean_score` | Phase 8 v2 and v4 assignment outputs |
| `query_band`, `gallery_band` | Phase 8 v2 and v4 assignment outputs |
| `query_score`, `gallery_score` | Phase 8 v2 assignments |
| `megadescriptor_similarity` | Phase 5, Phase 8 v2/v4 assignment outputs |
| `resnet50_similarity` | Phase 5, Phase 8 v4 assignment outputs |
| `descriptor_disagreement` / `descriptor_disagreement_flag` | Phase 8 v2/v4 and descriptor-disagreement outputs |
| `mega_reciprocal_rank`, `resnet50_reciprocal_rank` | Phase 8 v4 assignments |
| `reciprocal_support_flag` | Phase 8 v4 assignments |
| `margin_confidence` | Phase 8 v4 assignments |
| visual failure flags | Phase 8 v2 assignments and Phase 5 pair table |

Primary rule:

```text
R_pair may use descriptor support because it is a comparison-level utility score, but its components must remain visible and ablated.
```

## 7. Candidate Utility / Reranking Score Design

The candidate utility score asks:

```text
How should this descriptor-generated candidate be filtered, weighted, or reranked before Re-ID output or learning?
```

Candidate design:

```text
FinalScore(q, g) =
  base_descriptor_similarity(q, g)
  + alpha * R_image(q)
  + beta * R_image(g)
  + gamma * R_pair(q, g)
  + delta * reciprocal_support(q, g)
  + eta * margin_confidence(q, g)
  - lambda * descriptor_disagreement(q, g)
  - mu * visual_failure_penalty(q, g)
```

This formula is a design target, not yet a validated result. Phase 9B must test multiple transparent variants:

- descriptor-only baseline;
- image-utility weighted reranking;
- pair-utility weighted reranking;
- candidate-utility reranking;
- quality-only reranking;
- ablations removing reciprocal support, margin confidence, disagreement, and visual admissibility.

Weights must be calibrated only on calibration queries and evaluated only on held-out queries.

## 8. Relationship to Phase 8 Results

Phase 8 showed:

1. Simple PF-ERI filtering did not robustly improve fixed-descriptor mAP under held-out query-level evaluation.
2. PF-ERI reduced false-candidate burden relative to repeated random same-size controls.
3. PF-ERI false-candidate burden reduction lowered simulated CzechLynx identity-record contamination pressure under conservative assumptions.

Phase 9 interpretation:

```text
Phase 8 is not a failed endpoint. It is a diagnostic result showing that PF-ERI contains reliability information, but that hard filtering alone is too blunt. The stronger next test is reranking and weighting, not more hard-filter tuning.
```

## 9. Repositioning the Eight Modeling Modules

| Module | Phase 9 role | Status |
|---|---|---|
| Expected review/evidence utility | Core candidate utility score. | Keep central. |
| Risk-constrained optimization | Prevents easy-image-only policies and enforces coverage/retention floors. | Keep central. |
| Calibration / held-out risk control | Tunes weights and thresholds without query leakage. | Keep central. |
| Risk-coverage curve formalization | Shows accuracy/risk/coverage tradeoffs. | Keep central. |
| Pareto frontier / multi-objective optimization | Selects balanced policies rather than one metric winner. | Keep central. |
| Graph-based reliability network | Visual diagnostic layer for candidates and failure edges. | Keep secondary. |
| Downstream ecological sensitivity | Application-value analysis showing why false candidates matter. | Keep secondary. |
| Bayesian reliability score | Optional later uncertainty model. | Postpone. |

## 10. Novelty Boundary

PF-ERI does not claim novelty in these individual ideas:

- generic image-quality filtering;
- wildlife Re-ID descriptors;
- descriptor score fusion;
- selective prediction or reject-option classification;
- risk-coverage curves;
- retrieval reranking;
- human-in-the-loop review.

Novelty boundary:

```text
PF-ERI's contribution is the integration of visual identity evidence, fixed descriptor support, reciprocal and margin confidence, descriptor disagreement, and risk-coverage constraints into a Re-ID-specific evidence utility model for patterned-felid camera-trap Re-ID.
```

Difference from generic quality filtering:

```text
Generic quality filtering asks whether an image is clear. PF-ERI asks whether an image or candidate pair contains useful individual-identification evidence for patterned-felid Re-ID.
```

Difference from descriptor fusion:

```text
Descriptor fusion combines model scores. PF-ERI combines descriptor scores with explicit visual admissibility and failure-mode evidence, then tests whether utility-aware reranking improves retrieval or reduces false-candidate burden.
```

Difference from selective prediction:

```text
Selective prediction rejects uncertain cases. PF-ERI uses the reject/risk-coverage idea inside a patterned-felid evidence model with visual and descriptor-specific failure modes.
```

## 11. Graph-Based Reliability Network

Graph-based reliability network should remain a visualization and diagnostic layer.

It can show:

- image nodes;
- descriptor-generated candidate edges;
- descriptor similarity;
- PF-ERI image and pair utility;
- false-candidate edges in validation;
- changes before and after PF-ERI filtering or reranking.

It must not be framed as:

- automatic identity clustering;
- field identity assignment;
- population inference;
- movement inference;
- site-use inference.

## 12. Downstream Sensitivity

Downstream sensitivity remains an application-value analysis. It answers:

```text
If PF-ERI reduces false candidate links, could that reduce simulated identity-record contamination pressure?
```

It does not estimate abundance, occupancy, survival, movement, or field ecological parameters. It should support why false-candidate reduction matters, not become the main algorithmic claim.

## 13. Mainland Clouded Leopard and Marbled Cat Framing

Mainland Clouded Leopard and Marbled Cat remain future conservation application motivations only.

Allowed:

```text
PF-ERI is motivated by future use in rare patterned-felid monitoring, especially Mainland Clouded Leopard and Marbled Cat, where known-ID data and expert review capacity are limited.
```

Forbidden:

```text
PF-ERI has been validated on Mainland Clouded Leopard.
PF-ERI has been validated on Marbled Cat.
PF-ERI is field-deployment ready for either species.
```

## 14. Available Signals Inventory

Inspected available artifacts:

| Artifact | Rows | Key available signals |
|---|---:|---|
| `data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv` | 1000 | image visual factors, uncertainty, source phase, quality bucket |
| `data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv` | 500 | Phase 4 visual factors and review-readiness context |
| `outputs/czechlynx/phase5/czechlynx_phase5_pair_eri_scores_internal.csv` | 3000 | pair visual factors, fixed similarities, visual-only ERI, model support, cross-model agreement, hybrid variants |
| `outputs/czechlynx/phase4/czechlynx_phase4c_pair_level_mechanism_similarity_table.csv` | 3000 | pair visual mechanisms and ResNet50/MegaDescriptor similarities |
| `outputs/czechlynx/phase8/pf_eri_retrieval_control_v2/phase8_pf_eri_retrieval_control_v2_recommended_assignments.csv` | 2500 | query/gallery scores, pair scores, visual flags, disagreement, assignments |
| `outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_recommended_assignments.csv` | 2500 | MegaDescriptor/ResNet50 similarities, ranks, reciprocal ranks, margin confidence, disagreement, final class |
| `outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_policy_grid.csv` | 1009 | policy performance, risk, coverage, workload, reciprocal support, margin confidence |
| `outputs/czechlynx/phase8/reid_accuracy_evidence_selection/phase8_slice3e_policy_comparison.csv` | 17 | full-carrier policy metrics and random-control comparison |
| `outputs/czechlynx/phase8/reid_accuracy_query_calibration/phase8_slice3e_query_evaluation_policy_comparison.csv` | 120 | held-out query-level metrics and random-control comparison |
| `outputs/czechlynx/phase8/reid_accuracy_query_calibration/phase8_slice3e_query_split_design.csv` | 20 | calibration/evaluation query split design |
| `outputs/czechlynx/phase8/downstream_sensitivity/phase8_slice3f_policy_contamination_metrics.csv` | 5 | contamination-pressure metrics for policy-level comparison |

These are enough for Phase 9B fixed-descriptor reranking without external data or model training.

## 15. Missing or Future-Work Signals

Missing or not yet consolidated:

- a single Phase 9 candidate-level table joining all image utility, pair utility, descriptor, reciprocal, margin, disagreement, truth-for-validation, and split fields;
- clean query-level reranking outputs for both MegaDescriptor and ResNet50 in one schema;
- learned utility targets for any Phase 9C model;
- external patterned-felid validation data;
- measured human reviewer false-acceptance behavior;
- safe public location/trap/site variables;
- clouded leopard or marbled cat known-ID validation data.

These missing items should not block Phase 9B, but they prevent broader transfer, deployment, or learning claims.

## 16. Immediate Phase 9B Plan

Next technical phase:

```text
Phase 9B — PF-ERI-Aware Fixed-Descriptor Reranking
```

Purpose:

```text
Test whether PF-ERI image/pair/candidate utility scores can improve held-out Re-ID retrieval metrics compared with raw descriptor ranking, simple PF-ERI filtering, and random same-size/same-coverage controls.
```

Required comparisons:

- raw MegaDescriptor ranking;
- raw ResNet50 ranking if available;
- simple PF-ERI hard filtering;
- PF-ERI weighted reranking;
- PF-ERI candidate utility reranking;
- random same-size baseline;
- random same-coverage baseline;
- quality-only baseline.

Required metrics:

- top-1 accuracy;
- top-5 accuracy;
- mAP;
- MRR;
- false top-1 rate;
- false-candidate burden;
- query coverage;
- positive retention;
- risk-coverage curve;
- Pareto position.

Required safeguards:

- held-out calibration/evaluation split;
- repeated splits;
- no row-level leakage;
- random same-size and same-coverage controls;
- feature ablation;
- sensitivity over weights;
- clear failure criteria.

Success criterion:

```text
PF-ERI reranking must beat raw descriptor ranking, simple PF-ERI hard filtering, quality-only filtering, and repeated random same-size/same-coverage controls on held-out metrics while preserving acceptable query coverage and positive retention.
```

Failure criterion:

```text
If PF-ERI reranking only selects easier examples or does not outperform random controls at acceptable coverage and retention, the project must not claim Re-ID enhancement. It remains an evidence utility and review-prioritization framework.
```

## 17. Later Phase 9C / 9D Learning Plan

Do not implement learning yet.

Possible later phase:

```text
Phase 9C — PF-ERI-Weighted Lightweight Learning Feasibility
```

Purpose:

```text
Test whether fixed embeddings plus a calibrated utility head can learn candidate utility without training a large Re-ID model.
```

Possible models:

- logistic regression;
- small MLP;
- calibrated scoring head.

Possible inputs:

- descriptor similarity;
- `R_image(q)`;
- `R_image(g)`;
- `R_pair(q, g)`;
- reciprocal support;
- margin confidence;
- descriptor disagreement;
- visual failure penalties.

Future phase only if 9C succeeds:

```text
Phase 9D — Controlled PF-ERI-Weighted Re-ID Training
```

Training would require all-images, random same-size, quality-only, PF-ERI-selected, PF-ERI-weighted loss, and PF-ERI-aware reranking baselines. Training is forbidden until fixed reranking shows enough value.

## 18. Allowed Claims

Allowed now:

- PF-ERI is being reframed as an automated evidence utility model for patterned-felid Re-ID enhancement.
- PF-ERI uses visual evidence utility, fixed descriptor support, reciprocal/margin confidence, disagreement, calibration, and risk-coverage safeguards.
- Phase 8 showed false-candidate burden reduction under CzechLynx held-out query evaluation.
- Phase 8 showed reduced simulated CzechLynx identity-record contamination pressure under conservative assumptions.
- Current evidence motivates PF-ERI-aware fixed-descriptor reranking as the next test.
- Mainland Clouded Leopard and Marbled Cat are future conservation motivations only.

## 19. Forbidden Claims

Forbidden:

- PF-ERI is a new Re-ID model.
- PF-ERI is a new Re-ID descriptor.
- PF-ERI identifies true individual animals.
- PF-ERI robustly improves fixed-descriptor Re-ID accuracy based on current results.
- PF-ERI is validated across felids.
- PF-ERI is validated for Mainland Clouded Leopard or Marbled Cat.
- PF-ERI is field-deployment ready.
- PF-ERI estimates abundance, occupancy, survival, movement, or population size.
- PF-ERI solves general animal Re-ID.
- Graph visualization is automatic identity clustering.
- Downstream sensitivity simulation is ecological estimation.

## 20. Risk Audit

| Risk | Why it matters | Mitigation |
|---|---|---|
| PF-ERI may only select easy images. | Apparent gains could be sample-selection artifacts. | Require random same-size and same-coverage controls, fixed held-out evaluation, query coverage, and positive retention reporting. |
| PF-ERI may overlap with generic quality filtering. | Novelty could collapse to image clarity. | Include quality-only baseline and ablate visual identity factors from generic quality factors. |
| PF-ERI may not improve held-out Re-ID accuracy. | Phase 8 already found non-robust mAP gains. | Define honest failure criteria and keep false-candidate burden as a separate supported value. |
| PF-ERI score may be too rule-based. | Reviewers may see it as a scoring table. | Test whether interpretable components improve reranking beyond baselines and report ablation/sensitivity. |
| Training data may be too small. | Learned utility heads could overfit. | Delay training until fixed reranking succeeds; use held-out splits and random controls. |
| Graph visualization may be mistaken for identity clustering. | Could create overclaiming risk. | Keep graph network as diagnostic only; no identity clustering claims. |
| Mainland Clouded Leopard / Marbled Cat may be overclaimed. | Current data are CzechLynx only. | State future motivation only unless known-ID external validation is completed. |
| Downstream contamination simulation may be mistaken for ecological estimation. | Could imply population or occupancy claims. | Label as simulated identity-record contamination pressure only. |

## 21. Final Recommendation

Recommendation:

```text
Proceed to Phase 9B fixed-descriptor reranking.
```

Do not proceed yet to:

- descriptor expansion;
- external data download;
- deep model training;
- PF-ERI-weighted Re-ID training;
- graph-based identity clustering;
- ecological population modeling;
- Mainland Clouded Leopard or Marbled Cat validation claims.

The strategy is defensible only if Phase 9B preserves the strict safeguards that Phase 8 established: held-out calibration/evaluation, random same-size and same-coverage controls, query coverage, positive retention, false-candidate burden, risk-coverage curves, Pareto checks, and explicit failure criteria.

## 22. Confirmation

This Phase 9A revision is documentation and planning only.

No code was implemented. No model was trained. No external data were downloaded. No frozen data were modified. No files were staged or committed.
