# PF-ERI Evidence-Routed Review Layer Design

Date: 2026-06-22

## Purpose

This design upgrades Phase 14 from evidence analysis into a reviewer-useful reliability layer. The target is not a new Re-ID descriptor and not an identity-assignment platform. The target is a decision layer that could sit after strong descriptor retrieval and before expert review.

Best-product migration test:

```text
If a Wildbook/IBEIS, Wildlife Insights/MegaDetector, or MegaDescriptor/WildFusion user already has strong candidate ranking, what does PF-ERI add that makes review safer and harder to give up?
```

The answer must be:

```text
PF-ERI turns high-similarity candidate lists into evidence-routed review decisions:
accept, review, defer, species-level only, or non-comparable.
```

## Current Evidence Base

Phase 14 now has the required 2x2 evidence pool:

- wild CzechLynx high-confidence evidence: 3,000 images;
- wild CzechLynx low-evidence stress: 3,000 images;
- urban/peri-urban bobcat high-confidence evidence: 3,000 images;
- urban/peri-urban bobcat low-evidence stress: 3,000 images.

It also has fixed MegaDescriptor embeddings, pair comparability tables, descriptor-evidence conflict tables, image-level statistical analysis, and a first risk-controlled review-policy analysis.

The most important result is mixed, and that is useful:

- In clean high-confidence CzechLynx pairs, raw descriptor ranking is already strong, so PF-ERI should not gate aggressively.
- In mixed-evidence pairs, PF-ERI reduces false-candidate burden more selectively than simple descriptor ranking.
- In severe low-evidence stress blocks, quality-only controls can dominate PF-ERI alone, so the next model must be hybrid.

## Main Design

The next system is:

```text
PF-ERI + quality hybrid risk policy
```

The policy takes candidate pairs from fixed descriptor retrieval and computes:

- descriptor percentile or similarity support;
- PF-ERI pair comparability;
- weakest-image evidence utility;
- detector confidence and animal size;
- blur, occlusion, crop risk, and body/flank visibility;
- descriptor-evidence conflict;
- evidence-role mismatch, such as high-evidence query versus low-evidence gallery;
- environment context, used for reporting and stress testing, not identity inference.

It outputs:

```text
accept
review
defer
species-level only
non-comparable
```

The policy should be constrained rather than purely accuracy-maximizing:

```text
maximize positive candidate retention and usable review coverage
subject to false-candidate retention, non-comparable review load, and review-budget limits
```

## Required Comparisons

A result is not strong unless it beats or clarifies the best realistic alternatives:

- raw descriptor top-k retrieval;
- descriptor percentile threshold;
- quality-only gate;
- PF-ERI pair-comparability-only gate;
- PF-ERI plus quality hybrid;
- random same-coverage controls;
- random matched image-selection controls;
- quality-proxy matched controls.

The main benchmark is CzechLynx because it has known IDs. Bobcat remains a same-genus urban/peri-urban transfer stress test unless individual IDs or audited same/different pair labels become available.

## Phase 15 Work Units

### Unit 1: Candidate Query Benchmark

Build query-level CzechLynx candidate lists from MegaDescriptor embeddings. Evaluate top-k behavior, positive candidate retention, false-candidate burden, and query coverage before and after evidence routing.

### Unit 2: Hybrid Risk Policy

Fit or grid-search a constrained policy over descriptor support, PF-ERI pair comparability, weakest-image utility, quality features, and conflict score. Report Pareto frontiers rather than one cherry-picked threshold.

### Unit 3: Evidence Routing Table

For every candidate pair, emit a decision label and reason fields:

```text
accept/review/defer/species-level-only/non-comparable
primary_failure_reason
secondary_failure_reason
risk_band
coverage_band
```

### Unit 4: Product-Migration Evidence Cards

Create a compact per-pair evidence-card table, not a UI yet. Each row should be understandable to a heavy Re-ID reviewer:

```text
descriptor says similar, but side/flank evidence is not comparable
descriptor says similar, evidence is admissible, keep for review
descriptor is weak but visual evidence is good, retain as secondary candidate
```

### Unit 5: Urban Transfer Stress

Apply the calibrated policy to bobcat candidate pairs without claiming false-match accuracy. Report review pressure, non-comparable pressure, descriptor-evidence conflict rate, and high-confidence versus low-evidence differences.

## Success Criteria

The next phase succeeds if it shows at least one strong, bounded result:

1. On CzechLynx known-ID query retrieval, the hybrid policy improves the risk-coverage frontier against raw descriptor, quality-only, PF-ERI-only, and random matched controls.
2. The policy preserves query coverage and positive-candidate retention at a specified false-candidate burden or review-budget level.
3. The evidence routing table produces interpretable reasons for accept, review, defer, species-level-only, and non-comparable decisions.
4. The bobcat transfer stress test shows how urban/peri-urban data shift review pressure without making unsupported identity-accuracy claims.

## Non-Goals

Do not build a new descriptor.
Do not fine-tune a backbone.
Do not claim bobcat identity validation.
Do not claim universal thresholds.
Do not weaken high-confidence evidence rules to inflate sample size.
Do not present severe low-evidence filtering as the main innovation if quality-only already explains it.

## Implementation Readiness

The project is ready to start Unit 1 because the final 2x2 image sets and MegaDescriptor embeddings already exist. The first implementation should be a query-level benchmark and policy-input table, not model training.
