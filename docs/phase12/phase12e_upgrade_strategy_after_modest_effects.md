# Phase 12E Upgrade Strategy After Modest Effects

Date: 2026-06-17

Purpose: decide whether the Phase 12C/12D findings are positive, negative, or diagnostic, and define how the project should upgrade rather than prematurely downgrade its ambition.

## Current Situation

Phase 12C showed that PF-ERI candidate utility gives a small but stable top-1 improvement over raw fixed descriptors:

- MegaDescriptor false top-1 risk reduction: about 1.05 percentage points, 95% CI above zero.
- ResNet50 false top-1 risk reduction: about 1.37 percentage points, 95% CI above zero.

Phase 12D showed why this is not a breakthrough by itself:

- Only about 34-38% of queries have a true positive in the descriptor top-20 pool.
- Raw top-1 true rate is only about 14-15%.
- Pair reliability alone has weak same-identity discrimination, with AUC near 0.5.
- Simple held-out grid calibration did not beat the current candidate utility.

## Is This Positive Or Negative?

It is positive as a diagnostic signal, but insufficient as the final contribution.

Positive:

- PF-ERI contains real signal because candidate utility improves top-1 risk consistently across split-paired evaluation.
- Quality-only controls are not enough, so the effect is not reducible to generic image quality.
- The current analysis identifies concrete failure mechanisms: descriptor ceiling, weak reliability-as-identity-discriminator, and singleton/no-positive-query structure.

Negative if left as final claim:

- A 1-1.5 percentage-point reranking gain is not enough to claim a breakthrough.
- A reviewer can argue that this is a minor post-processing heuristic.
- Fixed candidate utility does not yet prove a new learning mechanism.

Therefore the correct interpretation is:

```text
Phase 12C/12D validates PF-ERI as a signal and reveals the bottleneck, but the project must upgrade from fixed reranking to a stronger evidence-conditioned model.
```

## What Not To Do

Do not downgrade the project to:

- "PF-ERI is a small reranking improvement."
- "PF-ERI is a quality filter."
- "PF-ERI slightly improves top-1."
- "PF-ERI is only a diagnostic visualization."

Those claims are too easy to replace.

Also do not overclaim:

- "PF-ERI solves Re-ID."
- "PF-ERI is a new descriptor."
- "PF-ERI robustly improves metric learning" before RQ4 controlled training passes.

## Upgrade Path

### Upgrade 1: Reframe The Main Contribution

Old weak framing:

```text
PF-ERI reranks descriptor candidates and slightly improves top-1.
```

Stronger framing:

```text
PF-ERI models evidence admissibility as a pair-level reliability variable that controls when descriptor similarity should be trusted, deferred, downweighted, or used for learning.
```

This shifts the contribution from a small performance bump to a reliability modeling framework.

### Upgrade 2: Replace Pooled False Rate With Query-Level Decision Metrics

Pooled candidate false rate is structurally dominated by base rates. It should not be the main RQ1 endpoint.

Use:

- false candidates per query at top-k;
- positive-present@k;
- hard-negative exposure;
- query coverage under reliability thresholds;
- eligible-query top-1 risk.

This makes the evaluation match the real review burden and conservation decision problem.

### Upgrade 3: Build A Learned Evidence Utility Model

The fixed utility formula is interpretable but low-capacity. The next model should be a constrained learned candidate utility model:

Inputs:

- descriptor similarity percentile;
- reciprocal/margin confidence;
- descriptor disagreement;
- pair reliability;
- image quality proxy;
- visual identity evidence;
- descriptor-evidence conflict;
- admissibility band indicators.

Model options:

- constrained logistic regression;
- monotonic GAM;
- calibrated gradient-boosted model with monotonic constraints if available;
- small MLP only after simpler calibrated models pass.

Constraints:

- descriptor support should generally increase utility;
- severe conflict should not increase utility;
- reliability can interact with descriptor confidence rather than act alone.

Validation:

- train/calibrate only on calibration split;
- evaluate on held-out split;
- compare against raw descriptor, quality-only, fixed PF-ERI utility, and random top-20 control.

### Upgrade 4: Treat Descriptor Ceiling As A Separate Problem

PF-ERI cannot recover positives outside top-20. Therefore retrieval has two layers:

1. descriptor recall layer: can the descriptor place the true identity in the candidate pool?
2. evidence utility layer: can PF-ERI select or weight trustworthy candidates inside that pool?

We should report both. This prevents unfairly judging PF-ERI for descriptor recall failure while also preventing overclaiming.

### Upgrade 5: Move RQ4 From Optional To Central, But Controlled

The strongest possible contribution is not fixed reranking. It is reliability-aware learning:

```text
Can pair-level evidence reliability improve the training signal by emphasizing admissible positives and controlling unreliable hard negatives?
```

Implementation rule:

- Positive pairs only from identities with at least two images.
- Singleton identities can be used as distractors/hard negatives, not positives.
- Compare all-images training, random matched training, quality-only matched training, fixed PF-ERI reranking, and PF-ERI-conditioned pair weighting.

If RQ4 succeeds, the project becomes substantially stronger. If RQ4 fails, the project still has a defensible reliability-control contribution, but not a learning contribution.

## What We Need To Modify Now

### RQ1

Current:

```text
Can PF-ERI scores predict usable identity evidence?
```

Upgrade:

```text
Can PF-ERI evidence utility predict which candidate comparisons should be trusted, deferred, or downweighted to reduce query-level review burden while retaining positive identity evidence?
```

### RQ2

Current:

```text
Do high-similarity but low-admissibility pairs explain false candidates?
```

Upgrade:

```text
Do descriptor-evidence conflicts identify a distinct hard-negative mechanism where descriptor confidence is high but visual comparability is weak?
```

### RQ3

Current:

```text
Can PF-ERI improve risk-coverage tradeoffs?
```

Upgrade:

```text
Can learned or constrained PF-ERI candidate utility improve risk-coverage and review burden beyond raw descriptor, fixed PF-ERI, quality-only, and random controls under held-out split evaluation?
```

### RQ4

Current:

```text
Can PF-ERI-conditioned pair weights improve learned retrieval representations?
```

Upgrade:

```text
Can PF-ERI-conditioned pair weights improve retrieval training by separating admissible positive evidence from unreliable hard negatives under held-out identity-aware evaluation?
```

## Next Implementation Phase

Phase 13 should implement the learned evidence utility model before more paper writing.

Minimum Phase 13 outputs:

1. `phase13_candidate_utility_training_table.csv`
2. `phase13_calibrated_utility_model_results.csv`
3. `phase13_risk_coverage_comparison.csv`
4. `phase13_model_ablation_summary.csv`
5. `phase13_holdout_confidence_summary.csv`

Success criteria:

- learned PF-ERI utility beats fixed PF-ERI and quality-only on held-out query-level false burden or positive-present@k;
- confidence interval does not cross zero for at least one primary endpoint;
- ablation shows pair reliability/conflict adds value beyond descriptor similarity alone;
- query coverage is preserved or explicitly traded off on a risk-coverage frontier.

## Strategic Decision

Do not treat the modest Phase 12 result as the final message. Treat it as the first proof that PF-ERI has signal, and use the diagnosed limitations to justify the next upgrade:

```text
From fixed evidence utility scoring to learned, constrained, reliability-aware candidate utility and metric-learning supervision.
```
