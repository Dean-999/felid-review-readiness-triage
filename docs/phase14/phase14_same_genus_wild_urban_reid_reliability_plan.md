# Phase 14 Same-Genus Wild-to-Urban Re-ID Reliability Plan

Date: 2026-06-18

## New Direction

The project remains PF-ERI-centered, but the scientific framing changes from:

```text
PF-ERI improves CzechLynx Re-ID.
```

to:

```text
PF-ERI quantifies when same-genus Lynx Re-ID evidence is reliable, and tests whether a reliability model validated on wild Eurasian lynx can transfer to urban bobcat monitoring as a field-readiness stress test.
```

The new comparison is:

```text
CzechLynx / Eurasian lynx / wild known-ID validation
UWIN bobcat / Lynx rufus / urban same-genus stress context
```

This keeps CzechLynx as the quantitative validation carrier and adds UWIN bobcat as an external same-genus urban monitoring stress test.

## Core Rationale

The project should not become a broad urban ecology study and should not claim full urban bobcat identity validation unless individual labels are available.

The stronger, safer framing is:

```text
same-genus cross-context reliability testing
```

This asks whether evidence reliability patterns learned and validated in a known-ID wild lynx benchmark survive when exposed to a same-genus, human-modified urban monitoring context.

## Evidence-Risk Propagation Chain

The urban/wild comparison should not stop at single-image quality. The core structure is:

```text
image-level evidence shift -> pair-level comparability shift -> retrieval/review contamination
```

### Layer 1: Image-Level Evidence Shift

Question:

```text
Do wild Eurasian lynx and urban/peri-urban bobcat images differ in single-image Re-ID evidence readiness?
```

Use:

- pattern visibility;
- flank/side visibility;
- body visibility;
- blur;
- occlusion;
- night/IR status;
- background complexity;
- human-modified background;
- PF-ERI image score;
- review-ready / review-limited / species-level-only proportions.

### Layer 2: Pair-Level Comparability Shift

Question:

```text
Given two candidate images, does the pair contain comparable identity evidence?
```

This is the mechanism layer. Re-ID errors happen when query-gallery pairs are compared, so pair-level analysis explains how image evidence problems become candidate risk.

Use:

- weakest-image evidence;
- side/flank compatibility;
- pattern compatibility;
- viewpoint compatibility;
- pair-level PF-ERI reliability;
- descriptor similarity;
- descriptor-evidence conflict;
- non-comparable / uncertain-pair rate.

### Layer 3: Retrieval/Review Contamination

Question:

```text
How often do unreliable pairs enter retrieval candidates or human review queues?
```

Use:

- false-candidate burden where known IDs exist;
- positive retention where known IDs exist;
- high-similarity low-admissibility conflict rate;
- review/defer/species-level-only policy proportions;
- risk-coverage curves;
- review-load reduction under matched controls.

### Claim Boundary

Known-ID CzechLynx pairs can validate false-candidate risk, positive retention, and retrieval burden. Urban bobcat pairs without verified individual IDs can support pair-comparability, descriptor-evidence conflict, review-readiness, and contamination-pressure claims, but not true false-match validation.

## Data Roles

### CzechLynx

Role:

```text
primary known-ID validation carrier
```

Used for:

- candidate false-risk validation;
- descriptor-evidence conflict analysis;
- PF-ERI score calibration;
- risk-coverage and false-candidate burden;
- optional identity-disjoint retrieval tests;
- mechanism validation for pair-level evidence admissibility.

### UWIN Bobcat

Role:

```text
urban same-genus external stress context
```

Default claim boundary:

```text
field-readiness and review-readiness stress test, not full identity validation
```

Used for:

- evidence distribution shift;
- urban background / human-modified context exposure;
- descriptor-neighbor and descriptor-evidence conflict audit;
- small human-audited pair validation if feasible;
- accept / review / defer / species-level-only policy testing.

### UWIN Bobcat Small Pair Audit

Preferred route B:

```text
small manually audited pair set
```

Labels:

```text
same
different
uncertain
non-comparable
```

Purpose:

```text
test whether PF-ERI predicts human judgement of pair comparability and review need in urban bobcat data.
```

This is stronger than an unlabeled field-readiness test but does not require full individual-ID ground truth.

### UWIN Bobcat Full Identity Labels

Optional route C:

```text
full or partial individual-level UWIN bobcat validation if labels become available
```

This should be treated as exploratory until verified.

## Revised Research Questions

### RQ1: Wild Known-ID Evidence Reliability

Can PF-ERI predict unreliable candidate edges in known-ID wild Eurasian lynx Re-ID?

Evidence needed:

- false-candidate enrichment;
- descriptor-evidence conflict enrichment;
- positive retention;
- false-candidate burden;
- risk-coverage curves;
- comparison against raw descriptor, quality-only, and random controls.

### RQ2: Same-Genus Urban Image Evidence Shift

Does urban bobcat monitoring show a shifted evidence-risk distribution relative to wild Eurasian lynx?

Evidence variables:

- image quality;
- animal visibility;
- body area;
- side/flank visibility;
- pattern visibility;
- night/IR status;
- occlusion;
- background complexity;
- human-built background signal;
- descriptor confidence;
- descriptor-evidence conflict;
- PF-ERI image/pair score.

Suggested statistics:

- standardized mean difference;
- Kolmogorov-Smirnov distance;
- Jensen-Shannon divergence;
- Wasserstein distance;
- domain-classifier AUC;
- stratified effect sizes by visibility and background class.

### RQ3: Pair-Level Comparability and Conflict Shift

Do urban/peri-urban bobcat candidate pairs show a different pair-comparability and descriptor-evidence-conflict structure than known-ID wild lynx pairs?

Evidence needed:

- pair PF-ERI distribution comparison;
- high descriptor similarity plus low pair admissibility frequency;
- non-comparable or uncertain pair rate;
- pair-level failure taxonomy;
- comparison against image-quality-only pair proxies;
- CzechLynx known-ID validation linking the same pair features to false-candidate risk.

Claim boundary:

```text
For bobcat data without verified identity labels, this is a contamination-pressure and review-readiness analysis, not a false-match accuracy analysis.
```

### RQ4: Urban Review-Readiness

Under a PF-ERI-calibrated policy learned on CzechLynx, what proportion of UWIN bobcat evidence should be:

```text
accept
review
defer
species-level only
non-comparable
```

Evidence needed:

- policy transfer table;
- review-load estimate;
- evidence-failure taxonomy;
- confidence interval or bootstrap uncertainty for policy proportions.

### RQ5: Human-Audited Bobcat Pair Validation

In a small human-audited UWIN bobcat pair set, can PF-ERI distinguish:

```text
same/different confident comparisons
from uncertain or non-comparable comparisons
```

Evidence needed:

- PF-ERI vs human judgement;
- descriptor similarity vs human judgement;
- quality-only vs human judgement;
- descriptor-evidence conflict enrichment among uncertain pairs;
- inter-reviewer agreement if more than one reviewer labels the same subset.

### RQ6: Optional Full Urban Bobcat Re-ID Validation

If sufficient UWIN bobcat individual labels become available, can PF-ERI-calibrated risk policies reduce false-candidate burden in urban bobcat Re-ID?

Claim boundary:

```text
exploratory unless identity labels and split discipline are verified
```

## Mathematical Modeling Core

PF-ERI becomes an evidence-risk module inside a cross-context reliability framework.

### 1. Evidence Reliability Score

```text
R_ij = f(image evidence_i, image evidence_j, pair comparability_ij, descriptor support_ij, conflict_ij)
```

Output:

```text
probability or calibrated score that pair ij contains admissible identity evidence
```

### 2. Context Shift Quantification

For feature vector `X`:

```text
Delta_context = distance(P_CzechLynx(X), P_UWIN_bobcat(X))
```

Candidate distances:

```text
Wasserstein distance
Jensen-Shannon divergence
MMD
domain-classifier AUC
```

### 3. Review-Readiness Policy

```text
policy(pair or image) -> {accept, review, defer, species-level only, non-comparable}
```

Objective:

```text
minimize false candidate burden and non-comparable review waste
subject to positive retention or review-budget constraints
```

### 4. Human-Audited Pair Validation

For audited bobcat pairs:

```text
human_label in {same, different, uncertain, non-comparable}
```

Evaluation:

```text
R_ij should separate confident comparable pairs from uncertain/non-comparable pairs.
```

## What Changes From Earlier Plans

### Keep

- PF-ERI image and pair reliability;
- descriptor-evidence conflict;
- risk-coverage and false-candidate burden;
- CzechLynx known-ID validation;
- learned candidate utility as supporting evidence;
- Phase 13D metric-learning result as diagnostic evidence.

### Downgrade

Metric learning is no longer the main next contribution.

Current status:

```text
Phase 13D showed plain projection-head training damages strong descriptor geometry and does not pass the raw-reference gate.
```

Metric learning remains optional only after:

- identity-disjoint split discipline is fixed;
- residual geometry-preserving objectives are implemented;
- PF-ERI beats random and quality controls under held-out evaluation.

### Add

- UWIN bobcat same-genus urban stress context;
- evidence distribution shift;
- small human-audited bobcat pair set;
- accept / review / defer / species-level-only policy transfer;
- same-genus wild-to-urban claim boundary.

### Remove From Main Story

- broad clouded leopard / marbled cat validation claims;
- full metric-learning improvement claims;
- generic animal Re-ID framing;
- population estimation claims;
- urbanization causal claims without controlled data.

## Required New Audits

1. UWIN bobcat data availability audit:
   - image count;
   - bobcat detection confidence;
   - metadata availability;
   - camera/site labels;
   - night/IR status;
   - any individual labels;
   - permission constraints.

2. UWIN bobcat audit-label feasibility:
   - can same/different/uncertain/non-comparable pairs be manually reviewed?
   - how many pairs are feasible?
   - who reviews?
   - can labels be blinded?

3. Cross-context feature compatibility:
   - which PF-ERI features can be computed for both CzechLynx and UWIN bobcat?
   - which features are CzechLynx-only?
   - which urban-specific features must be added?

4. Claim-boundary audit:
   - no UWIN identity-validation claim without verified individual labels;
   - no urbanization causal claim without context controls;
   - no full cross-species generalization claim.

## Immediate Implementation Plan

The original Phase 14 data-construction plan has now been completed through
the 2x2 working-final evidence sets, fixed descriptor embeddings, pair
comparability tables, descriptor-evidence conflict tables, image-level
statistical analysis, and first risk-controlled review-policy analysis.

The next implementation direction is Phase 15:

```text
PF-ERI Evidence-Routed Review Layer
```

This means the project should now behave like a reliability module that sits
between strong descriptor retrieval and expert review. It should not compete
with Wildbook/IBEIS as a full identity database, Wildlife Insights as a
camera-trap platform, or MegaDescriptor/WildFusion as descriptor models.
Instead, it should answer the missing review question:

```text
This candidate looks similar, but is the comparison supported by admissible identity evidence, and should it be accepted, reviewed, deferred, downgraded to species-level only, or marked non-comparable?
```

Immediate Phase 15 plan:

1. Build a CzechLynx query-level candidate benchmark from the existing
   MegaDescriptor embeddings.
2. Evaluate raw descriptor top-k retrieval, query coverage, positive candidate
   retention, and false-candidate burden.
3. Build a hybrid policy-input table combining descriptor support, PF-ERI pair
   comparability, weakest-image evidence, generic quality controls,
   descriptor-evidence conflict, and evidence-role mismatch.
4. Compare descriptor-only, quality-only, PF-ERI-only, PF-ERI plus quality
   hybrid, and random matched controls.
5. Report Pareto frontiers instead of a single threshold:
   - maximize positive retention;
   - minimize false-candidate retention;
   - minimize non-comparable review burden;
   - preserve query coverage.
6. Emit evidence-routed decisions:
   - accept;
   - review;
   - defer;
   - species-level only;
   - non-comparable.
7. Apply the calibrated policy to bobcat candidate pairs as a same-genus urban
   transfer stress test, reporting review pressure and conflict pressure
   without claiming bobcat false-match accuracy.
8. Prepare a compact evidence-card table so each routed pair has an
   interpretable reason that a heavy Re-ID reviewer can understand.

## Success Criteria

The new direction is successful if it shows:

1. PF-ERI predicts candidate unreliability in CzechLynx better than descriptor
   similarity alone in the evidence-mixed candidate regimes where descriptor
   similarity is not enough.
2. A PF-ERI plus quality hybrid policy improves the risk-coverage frontier
   against descriptor-only, quality-only, PF-ERI-only, and random matched
   controls.
3. The system preserves positive candidate retention and query coverage at a
   defined false-candidate burden or review-budget level.
4. Bobcat has measurable evidence-risk distribution shift and review-pressure
   shift relative to CzechLynx, without unsupported identity-validation claims.
5. The output is reviewer-actionable: each candidate pair can be routed to
   accept, review, defer, species-level only, or non-comparable with an
   interpretable reason.

## Final Claim Boundary

Defensible:

```text
PF-ERI is a pair-level evidence reliability model validated on wild known-ID Eurasian lynx and stress-tested on same-genus urban bobcat monitoring to estimate field-readiness and review-readiness for individual-level Re-ID.
```

Not defensible yet:

```text
PF-ERI identifies urban bobcat individuals.
PF-ERI proves urbanization causes Re-ID failure.
PF-ERI improves metric learning.
PF-ERI generalizes to all felids or all animals.
```
