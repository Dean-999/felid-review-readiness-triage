# Phase 12 Pairwise Evidence Learning Roadmap

## Purpose

Phase 12 revises the project endpoint from image-level evidence filtering toward reliability-aware pairwise evidence learning for patterned-felid Re-ID.

The core problem is:

```text
Given two camera-trap images and fixed descriptor evidence, does the pair contain comparable patterned-felid identity evidence, and should it be trusted for retrieval, reranking, or learning?
```

This phase prepares implementation for four connected research questions rather than one all-or-nothing claim that PF-ERI must improve every Re-ID metric.

## Revised Contribution Logic

PF-ERI should be treated as a pair-level evidence admissibility model. Its value can appear in four ways:

1. it predicts whether image pairs contain usable identity evidence;
2. it identifies high-risk descriptor-evidence conflict;
3. it improves risk-coverage or false-candidate burden in retrieval;
4. it provides useful pair weights for metric learning.

The project should not claim that PF-ERI is a new Re-ID descriptor, a field identity system, a universal animal Re-ID score, or a population-estimation method.

## Research Questions

### RQ1: Evidence Admissibility

Question:

```text
Can PF-ERI image and pair scores predict usable patterned-felid identity evidence?
```

Primary analysis:

- association between PF-ERI pair reliability and false-candidate risk;
- comparison of image-level quality-only scores versus pair-level admissibility;
- positive retention and query coverage by evidence band.

Success criterion:

PF-ERI pair admissibility explains retrieval risk or usable-evidence labels better than image-only quality proxies.

### RQ2: Descriptor-Evidence Conflict

Question:

```text
Do high-similarity but low-admissibility pairs explain a distinct class of false Re-ID candidates?
```

Primary analysis:

- define conflict group: high descriptor similarity and low pair admissibility;
- compare false-candidate rate, false top-1 rate, and review burden across conflict bands;
- test whether conflict score adds explanatory value beyond descriptor similarity alone.

Success criterion:

Descriptor-evidence conflict identifies a measurable failure mechanism that raw descriptor confidence misses.

### RQ3: Risk-Controlled Retrieval

Question:

```text
Can PF-ERI improve risk-coverage and false-candidate burden beyond raw descriptor, random matched, and quality-only controls?
```

Primary analysis:

- risk-coverage curves;
- fixed-coverage risk;
- fixed-risk coverage;
- random same-size and same-coverage controls;
- quality-only controls;
- Pareto frontier across retrieval quality, false-candidate burden, positive retention, and query coverage.

Success criterion:

PF-ERI improves at least one risk-control objective without query-coverage collapse or unacceptable positive-evidence loss.

### RQ4: Reliability-Aware Metric Learning

Question:

```text
Can PF-ERI-conditioned pair weights improve or stabilize metric learning under held-out identity evaluation?
```

Primary algorithms:

1. uniform supervised contrastive baseline;
2. positive-pair reliability weighting;
3. unreliable hard-negative downweighting;
4. descriptor-evidence conflict-aware variant.

Core logic:

```text
Not all positive pairs are equally useful.
Not all hard negatives are equally trustworthy.
Pair reliability should control how much each pair contributes to representation learning.
```

Success criterion:

PF-ERI-conditioned training improves held-out retrieval metrics, reduces false-candidate burden, or stabilizes performance relative to uniform, random matched, and quality-proxy matched controls.

## Algorithm Targets

### Pair Reliability

Use the Phase 11 pair table as the first deterministic reliability model:

```text
R_pair(i,j) =
  w_side * side_comparability
+ w_pattern * min(pattern_i, pattern_j)
+ w_blur * min(blur_i, blur_j)
+ w_occlusion * min(occlusion_i, occlusion_j)
+ w_body * min(body_visible_i, body_visible_j)
+ w_view * viewpoint_compatibility
```

The weakest-image rule remains central: a pair cannot be strong Re-ID evidence if one image lacks comparable individual-pattern evidence.

### Descriptor-Evidence Conflict

Add an explicit conflict score:

```text
Conflict(i,j) = high_descriptor_similarity(i,j) * (1 - R_pair(i,j))
```

Variants may use percentile-scaled similarity, margin confidence, descriptor disagreement, or reciprocal support.

Conflict is not identity evidence. It is a risk signal for high-confidence but visually weak candidate comparisons.

### Retrieval Utility

Candidate utility should be tested as transparent variants:

```text
Utility(i,j) =
  alpha * descriptor_similarity
+ beta * R_pair
+ gamma * reciprocal_support
+ delta * margin_confidence
- eta * descriptor_disagreement
- lambda * Conflict
```

Weights must be tuned on calibration queries only and reported through held-out query or held-out identity evaluation.

### Metric-Learning Loss

Use fixed MegaDescriptor embeddings and a small projection head unless a later audit approves backbone fine-tuning.

Positive-pair weighting:

```text
w_pos(i,j) = R_pair(i,j)
```

Unreliable hard-negative control:

```text
if y_i != y_j and descriptor_similarity high and R_pair low:
    w_neg(i,j) = lambda_low
else:
    w_neg(i,j) = 1
```

Conflict-aware variant:

```text
w_neg(i,j) = f(R_pair, Conflict, descriptor_disagreement)
```

## Required Controls

Every implementation slice must compare against the relevant subset of:

- raw descriptor retrieval;
- random same-size control;
- random same-coverage control;
- quality-only filtering or weighting;
- PF-ERI image-level selection;
- PF-ERI pair-level weighting;
- uniform supervised contrastive learning;
- no-training PF-ERI-aware reranking.

Do not interpret PF-ERI gains unless they beat the matched control appropriate for the claim.

## Required Metrics

Retrieval:

- mAP;
- MRR;
- top-1 accuracy;
- top-5 accuracy;
- false top-1 rate;
- false-candidate burden;
- query coverage;
- candidate retention;
- positive retention.

Risk control:

- risk-coverage curve;
- fixed-coverage risk;
- fixed-risk coverage;
- Pareto frontier position.

Training:

- held-out split mean and interval;
- split-level paired differences;
- false-candidate burden change;
- query coverage change;
- stability across repeated splits.

## Implementation Order

1. Audit existing Phase 11 pair-level reliability table and training outputs.
2. Add descriptor-evidence conflict variables to the pair/candidate table.
3. Build RQ1/RQ2 diagnostic summaries before running additional training.
4. Build RQ3 risk-coverage and conflict-aware reranking comparison.
5. Extend Phase 11 training configs to include conflict-aware loss variants only after the diagnostic tables pass audit.
6. Run held-out evaluation with matched controls.
7. Interpret RQ4 as evidence-conditioned learning, not proof of universal Re-ID improvement.

Detailed implementation plan:

```text
docs/phase12/phase12_rq1_rq4_technical_implementation_plan.md
```

Technical evidence and confidence map:

```text
docs/phase12/phase12_rq_technical_evidence_and_confidence_map.md
```

## Claim Ladder

Level 1:

```text
PF-ERI pair admissibility is associated with false-candidate risk.
```

Level 2:

```text
Descriptor-evidence conflict explains a failure mode missed by descriptor similarity alone.
```

Level 3:

```text
PF-ERI improves risk-coverage or false-candidate burden under matched controls.
```

Level 4:

```text
PF-ERI-conditioned pair weights improve or stabilize held-out metric learning under matched controls.
```

Only Level 4 can support a metric-learning enhancement claim.

## Immediate Next Step

Start implementation with an audit and augmentation slice:

```text
Phase 12A: build a unified pair/candidate analysis table containing pair reliability, descriptor similarity, descriptor disagreement, reciprocal/margin support, conflict score, identity label, split metadata, and retrieval outcome flags.
```

This table is the required substrate for RQ1-RQ4.
