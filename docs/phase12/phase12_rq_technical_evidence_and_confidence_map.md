# Phase 12 RQ Technical Evidence and Confidence Map

Date: 2026-06-17

Purpose: convert the Phase 12 research questions into a technically grounded implementation map. This document separates mature borrowed methods from the project's actual contribution, then rates the confidence of each research slice before implementation.

## Executive Position

The strongest defensible project target is not "a new animal Re-ID model." It is:

```text
PF-ERI is a pair-level evidence admissibility and risk-control layer for patterned-felid Re-ID.
```

The project should use existing Re-ID descriptors, then ask whether each image pair has enough comparable visual identity evidence for the descriptor score to be trusted, used for review, used for reranking, or used as a training signal.

The strongest novelty is the pair-level mathematical layer:

```text
image quality -> visual identity evidence -> pair comparability -> descriptor-evidence conflict -> risk-controlled retrieval/training
```

This is narrower than generic animal Re-ID, but stronger than a simple quality filter.

## Literature Anchors

Animal Re-ID and descriptors:

- WildlifeDatasets and MegaDescriptor provide current open-source animal Re-ID infrastructure, broad dataset support, and pretrained animal Re-ID descriptors. They are the correct baseline family, not something PF-ERI should compete with as a backbone replacement.
- WildlifeReID-10k and OpenAnimals show the field is moving toward larger multi-species benchmarks, better splits, open-set settings, and stronger animal-oriented Re-ID baselines.
- WildFusion is close to our retrieval side because it fuses deep and local matching scores with calibration. PF-ERI must therefore be framed as evidence admissibility and risk control, not just score fusion.

Biometric quality and utility:

- Biometric sample-quality work already defines quality as expected recognition utility. This supports RQ1, but also means "quality predicts recognition" is not novel by itself.
- The gap is that patterned-felid camera-trap Re-ID needs dyadic comparability: side, viewpoint, body region, and visible pattern must be compatible across two images.

Selective prediction and risk control:

- Selective classification, reject-option learning, risk-coverage curves, and conformal risk control provide mature theory for abstaining or controlling risk.
- The project contribution is applying these ideas to ranked Re-ID candidate pairs and review burden, where coverage can mean query coverage, candidate coverage, or positive-pair retention.

Visibility-aware and occluded Re-ID:

- Person Re-ID already uses visible regions, part quality, and occlusion-aware matching.
- The project extension is to animal-specific evidence regions: flank side, pelage pattern, non-frontal viewpoint, body fraction, and side comparability.

Metric learning under unreliable pairs:

- Supervised contrastive learning and deep metric learning are known to degrade when pair construction is noisy.
- Selective supervised contrastive learning and noise-resistant metric learning show that pair selection/weighting is a serious algorithmic lever.
- PF-ERI's contribution is different from label-noise correction: a same-identity pair can be correctly labeled but still weak evidence if the visible pattern regions are not comparable.

## RQ1: Evidence Admissibility

Question:

```text
Can image- and pair-level PF-ERI scores predict whether a candidate comparison contains usable patterned-felid identity evidence?
```

### Technical Logic

RQ1 asks whether PF-ERI has measurable utility before changing retrieval or training. The key test is not whether high-quality images look better. The key test is whether pair-level reliability explains false-candidate burden, positive retention, or review utility better than image-only quality.

### Mathematical Model

Use the existing Phase 11 pair reliability:

```text
R_pair =
  0.30 * side_comparability
+ 0.25 * pattern_pair
+ 0.15 * blur_pair
+ 0.10 * occlusion_pair
+ 0.10 * body_visibility_pair
+ 0.10 * viewpoint_compatibility
```

Evaluate:

```text
P(false_candidate | R_pair)
P(same_identity_retained | R_pair)
Utility(review | R_pair, cost weights)
```

Compare against:

```text
image_quality_min
image_quality_mean
generic_quality_only_score
image_level_pf_eri_score
```

### Implementation

Use the future Phase 12A table:

```text
outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table.csv
```

Required first analyses:

- reliability-band summaries;
- pair-level versus image-quality-only paired split summaries;
- simple logistic or monotonic diagnostics for false-candidate risk;
- utility sensitivity over false-candidate cost, review-workload cost, query-drop cost, and positive-retention value.

### Expected Evidence

Strong support:

- high `R_pair` has lower false-candidate burden or higher positive retention;
- `R_pair` beats image-only quality on at least one held-out split-level risk metric;
- effect direction is stable by split/query group.

Weak support:

- `R_pair` works only after pooling all rows but not by split.

Failure:

- `R_pair` behaves no better than image quality.

### Confidence

High for feasibility.

Medium-high for publishable value if pair-level reliability beats image-only quality. This RQ is well grounded in biometric quality utility and selective prediction, but the novelty depends on showing pair-level comparability adds something beyond quality.

### Risk and Mitigation

Main risk: reviewers may say this is just quality assessment.

Mitigation: always report pair-level versus image-level controls, especially side/view/pattern comparability components. Do not claim evidence utility is conceptually new; claim patterned-felid pair admissibility is the domain-specific extension.

## RQ2: Descriptor-Evidence Conflict

Question:

```text
Do high-similarity but low-admissibility pairs explain a distinct class of false Re-ID candidates?
```

### Technical Logic

RQ2 is the mechanism question. It asks whether descriptor similarity fails in a specific way: the descriptor is confident, but the visual evidence needed for identity comparison is weak or non-comparable.

This is the most important explanatory bridge between "quality scoring" and "Re-ID risk control."

### Mathematical Model

Define:

```text
Conflict(i,j) = S_percentile(i,j) * (1 - R_pair(i,j))
```

where `S_percentile` is descriptor similarity percentile within an appropriate candidate pool.

Discrete conflict group:

```text
high similarity: S_percentile >= 0.90
low admissibility: R_pair <= 0.40
```

Incremental explanatory models:

```text
M0: false_candidate ~ descriptor_similarity
M1: false_candidate ~ descriptor_similarity + R_pair
M2: false_candidate ~ descriptor_similarity + R_pair + Conflict
```

### Implementation

Phase 12A must compute:

- descriptor similarity percentile;
- reciprocal-rank support;
- margin confidence;
- descriptor disagreement across available descriptors;
- pair reliability components;
- conflict score and conflict band.

Phase 12B should produce:

- false-candidate rate by conflict band;
- false top-1/top-5 rate among conflict candidates;
- rank-position distribution of high-conflict candidates;
- visual failure decomposition: side mismatch, pattern low, blur, occlusion, body low, viewpoint incompatible.

### Expected Evidence

Strong support:

- high-similarity/low-admissibility pairs have higher false-candidate or false-top-1 risk than high-similarity/high-admissibility pairs;
- conflict score improves log loss/AUC or split-level paired false-burden summaries beyond descriptor-only;
- conflict cases concentrate in interpretable visual failure modes.

Weak support:

- conflict is associated with false candidates but does not add beyond `R_pair`.

Failure:

- descriptor errors are not enriched in low-admissibility pairs.

### Confidence

Medium for empirical outcome.

High for conceptual value if supported, because this is the project's clearest mechanism innovation. It is also the slice most likely to distinguish PF-ERI from generic biometric quality, WildFusion-style score calibration, and raw descriptor ranking.

### Risk and Mitigation

Main risk: conflict score could become a restatement of "bad images are bad."

Mitigation: compare only within high-similarity candidates. The key contrast is:

```text
high descriptor + high admissibility
vs
high descriptor + low admissibility
```

That isolates descriptor-evidence conflict from generic low-quality filtering.

## RQ3: Risk-Controlled Retrieval

Question:

```text
Can PF-ERI improve risk-coverage tradeoffs compared with raw descriptor ranking, random matched filtering, and quality-only filtering?
```

### Technical Logic

RQ3 is the strongest practical contribution. It does not require PF-ERI to improve every standard Re-ID metric. It asks whether PF-ERI can reduce false candidate burden at matched coverage, or improve coverage at matched risk.

This fits selective prediction and reject-option theory, but with Re-ID-specific coverage definitions.

### Mathematical Model

Policy score:

```text
U(i,j) =
  alpha * S_percentile(i,j)
+ beta  * R_pair(i,j)
+ gamma * reciprocal_support(i,j)
+ delta * margin_confidence(i,j)
- eta   * descriptor_disagreement(i,j)
- lambda * Conflict(i,j)
```

Risk:

```text
risk = false_candidates_reviewed / reviewed_candidates
```

Coverage alternatives:

```text
candidate_coverage = reviewed_candidates / candidate_pool_size
query_coverage = queries_with_at_least_one_reviewed_candidate / total_queries
positive_retention = same_identity_candidates_retained / same_identity_candidates_available
```

The project should report all three because a method can look good by dropping too many queries.

### Implementation

Phase 12C should implement transparent policy families:

- raw descriptor ranking;
- random same-size control;
- random same-coverage control;
- quality-only filtering/reranking;
- image-level PF-ERI filtering;
- pair-admissibility filtering;
- conflict-penalty reranking;
- utility reranking.

Weights must be selected on calibration queries only, then evaluated on held-out queries or held-out identities.

### Expected Evidence

Strong support:

- lower false burden at the same query coverage;
- higher query coverage at the same risk;
- non-dominated point on a Pareto frontier including false burden, positive retention, and query coverage;
- matched controls do not explain the gain.

Weak support:

- false burden improves but positive retention or query coverage collapses.

Failure:

- improvement disappears against quality-only or random same-coverage controls.

### Confidence

High for feasibility.

Medium-high for scientific value because risk-coverage framing is mature and defensible. The key originality is not the curve itself, but the Re-ID candidate-pair instantiation and evidence-admissibility score.

### Risk and Mitigation

Main risk: PF-ERI may improve results by deleting hard but valid cases.

Mitigation: require positive retention, query coverage, and random same-size/same-coverage controls for every result. Treat top-1/mAP as secondary unless risk metrics also improve.

## RQ4: Reliability-Aware Metric Learning

Question:

```text
Can PF-ERI-conditioned pair weights improve learned retrieval representations by emphasizing admissible positive evidence and controlling unreliable hard negatives?
```

### Technical Logic

RQ4 is the strongest algorithmic ambition, but should start only after RQ1/RQ2 diagnostics show useful signal. The idea is not to train a new backbone. The idea is to use fixed MegaDescriptor embeddings and learn a small projection head with pair weights.

Core hypothesis:

```text
Correct identity labels are not enough. Pair evidence comparability controls whether a positive or hard-negative pair is useful training signal.
```

### Mathematical Model

Positive weighting:

```text
w_pos(i,j) = sqrt(R_pair(i,j))
```

This avoids over-suppressing medium-reliability positives.

Unreliable hard-negative control:

```text
if y_i != y_j and S_percentile(i,j) >= 0.90 and R_pair(i,j) <= 0.40:
    w_neg(i,j) = lambda_low
else:
    w_neg(i,j) = 1
```

Start conservative:

```text
lambda_low in {0.70, 0.85}
```

Conflict-aware negative weighting:

```text
w_neg(i,j) = max(0.70, 1 - k * Conflict(i,j))
```

Optional positive rescue:

```text
same_identity == true
R_pair low
descriptor_similarity high
pattern_pair adequate
```

This rescue is important because some true pairs may be visually difficult but still informative.

### Implementation

Use:

```text
colab/phase11_metric_learning/train_phase11_pair_weighted_metric_learning.py
```

Add new variants only after Phase 12A/12B audits:

- uniform supervised contrastive baseline;
- quality-proxy matched baseline;
- positive reliability weighting;
- unreliable hard-negative downweighting;
- conflict-aware negative weighting;
- positive rescue only if diagnostics justify it.

### Expected Evidence

Strong support:

- held-out mAP/MRR/top-1 improves without increasing false-candidate burden;
- weak splits stabilize;
- gains beat uniform, random matched, and quality-only controls;
- no-training PF-ERI reranking does not fully explain the improvement.

Weak support:

- training improves one split but not the mean or paired split differences.

Failure:

- PF-ERI weighting suppresses too many positives or overfits reliability artifacts.

### Confidence

Medium-low for empirical success before running diagnostics.

High for algorithmic interest if it works. This is the most publishable "strong algorithm" extension because it changes the loss surface, but it is also the most fragile and must be held behind diagnostics.

### Risk and Mitigation

Main risk: reliability weighting can remove hard but valid positives, making the model cleaner but less robust.

Mitigation:

- use `sqrt(R_pair)` or floor-weighted transforms, not raw hard deletion;
- compare to quality-only weighting;
- track positive-pair retention and false-candidate burden;
- keep fixed embeddings first.

## Cross-RQ Implementation Gate

Do not implement RQ4 variants until the following gates pass:

1. Phase 12A unified table exists and audit passes.
2. RQ1 shows pair reliability is not merely image-quality-only, or documents that it is.
3. RQ2 conflict analysis shows either a real conflict mechanism or a clear reason to skip conflict-aware loss.
4. RQ3 policies include matched controls and do not collapse query coverage.

## Confidence Ranking

| Slice | Feasibility | Scientific Strength If Supported | Current Priority |
|---|---:|---:|---:|
| RQ1 evidence admissibility | High | Medium-high | 1 |
| RQ2 descriptor-evidence conflict | High | High | 2 |
| RQ3 risk-controlled retrieval | High | High | 3 |
| RQ4 reliability-aware metric learning | Medium | Very high | 4 |

## Claim Ladder

Use this ladder in reports and manuscript drafting:

1. PF-ERI pair reliability is associated with candidate evidence usability.
2. Pair reliability adds signal beyond image-only quality.
3. Descriptor-evidence conflict identifies a high-risk false-candidate mechanism.
4. PF-ERI improves risk-coverage tradeoffs under matched controls.
5. PF-ERI-conditioned pair weighting improves or stabilizes held-out metric learning.

Stop the claim at the highest level that the data actually support.

## References Used for Positioning

- Cermak et al., WildlifeDatasets / MegaDescriptor, WACV 2024: https://openaccess.thecvf.com/content/WACV2024/papers/Cermak_WildlifeDatasets_An_Open-Source_Toolkit_for_Animal_Re-Identification_WACV_2024_paper.pdf
- WildlifeTools documentation: https://wildlifedatasets.github.io/wildlife-tools/
- Adam et al., WildlifeReID-10k: https://arxiv.org/abs/2406.09211
- Hou et al., OpenAnimals: https://arxiv.org/abs/2410.00204
- Cermak et al., WildFusion: https://arxiv.org/abs/2408.12934
- Schlett et al., Face Image Quality Assessment survey: https://dl.acm.org/doi/10.1145/3507901
- NIST biometric quality program: https://www.nist.gov/programs-projects/biometric-quality
- Hernandez-Ortega et al., utility-based biometric sample quality evaluation: https://link.springer.com/article/10.1186/s13640-024-00644-1
- Geifman and El-Yaniv, selective classification for deep neural networks: https://arxiv.org/abs/1705.08500
- Angelopoulos et al., conformal risk control: https://arxiv.org/abs/2208.02814
- Yang et al., visibility-aware occluded person Re-ID: https://openaccess.thecvf.com/content/ICCV2021/papers/Yang_Learning_To_Know_Where_To_See_A_Visibility-Aware_Approach_for_ICCV_2021_paper.pdf
- Li et al., selective supervised contrastive learning with noisy labels: https://openaccess.thecvf.com/content/CVPR2022/html/Li_Selective-Supervised_Contrastive_Learning_With_Noisy_Labels_CVPR_2022_paper.html
- Liu et al., noise-resistant deep metric learning with ranking-based instance selection: https://openaccess.thecvf.com/content/CVPR2021/html/Liu_Noise-Resistant_Deep_Metric_Learning_With_Ranking-Based_Instance_Selection_CVPR_2021_paper.html
