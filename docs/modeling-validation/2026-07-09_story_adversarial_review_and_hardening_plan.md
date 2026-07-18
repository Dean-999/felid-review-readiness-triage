# Story Adversarial Review And Hardening Plan

Date: 2026-07-09

Status: `PROJECT_STORY_HARDENING_PLAN`

## Purpose

This document records the first-principles story review of the project and the
specific work required to improve the story dimensions that did not receive a
full score in the 2026-07-09 adversarial review.

The goal is not to make the story sound stronger than the evidence. The goal is
to make the strongest honest story harder to misunderstand, harder to dismiss,
and easier to evaluate.

Binding sentence:

```text
Similarity is not admissibility.
```

Current strongest thesis:

```text
PF-ERI formalizes pair-level evidence admission after strong descriptor
retrieval, separating visual similarity from the evidential conditions needed
for trustworthy individual-level review before ecological inference.
```

## First-Principles Review

### What Ecological Inference Needs

Individual-level ecological inference depends on trustworthy individual records.
In photographic Re-ID workflows, a candidate pair can influence expert review,
mark-recapture histories, abundance estimates, and downstream conservation
interpretation. A weak pair admitted into the evidence chain is not merely a bad
ranked result. It can become a weak measurement unit.

### What Strong Descriptors Provide

Strong descriptors provide candidate generation and similarity context. They
answer:

```text
Which candidate images look similar to the query?
```

This is necessary, but it is not sufficient for evidence use.

### What Strong Descriptors Do Not Define

Descriptor similarity does not by itself define whether two images contain
comparable individual-level evidence. Pair admissibility depends on whether the
two images jointly provide enough usable visual evidence: visible patterned
area, comparable body side or view, overlapping body regions, acceptable weakest
image evidence, and absence of severe descriptor-evidence conflict.

### What PF-ERI Adds

PF-ERI makes the missing post-retrieval step explicit:

```text
candidate pair
-> pair-level evidence admissibility diagnosis
-> route for accept, review, defer, or non-comparable
```

The project is strongest when PF-ERI is framed as an evidence admission layer,
not as a better descriptor, an identity classifier, or a generic uncertainty
wrapper.

## Current Story Scorecard

| Dimension | Score | Reason |
| --- | ---: | --- |
| Centrality | 3.0 / 3 | The sentence `Similarity is not admissibility` is clear, memorable, and tied to the core method object. |
| Field necessity | 2.5 / 3 | The field need is real, but the manuscript must make the link from misidentification and unclassifiable evidence to pair-level admission unavoidable. |
| Novelty | 2.5 / 3 | Pair-level evidence admission is the real innovation, but generic risk-control or multi-annotator tools could dilute the novelty if over-emphasized. |
| Evidence strength | 2.0 / 3 | CzechLynx evidence is strong for reviewability/admissibility, but Bobcat remains unlabeled transfer stress and application value is not fully closed. |
| Logic closure | 2.5 / 3 | The argument is mostly closed, but the figure and result order must follow an evidence ladder rather than project chronology. |
| Reviewer resistance | 2.0 / 3 | Claim boundaries are strong, but reviewers can still attack construct validity, sample scope, feature sensitivity, and application value. |
| Portability | 3.0 / 3 | The main sentence can be retold easily and separates the project from descriptor competition. |

The hardening work below focuses only on the dimensions below full score:

```text
field necessity
novelty protection
evidence strength
logic closure
reviewer resistance
```

## Hardening Target 1: Field Necessity

### Current Gap

The project has a strong field-need review, but the manuscript could still be
read as:

```text
Descriptors sometimes make uncertain candidate pairs, so PF-ERI filters them.
```

That is not enough. The stronger argument must be:

```text
Any photographic wildlife Re-ID workflow that converts candidate pairs into
individual-level evidence needs an explicit admission step.
```

### Likely Reviewer Attack

```text
Why is this a new scientific problem rather than normal expert review or better
candidate ranking?
```

### Required Repair

Write the introduction around the evidence chain:

1. Individual identification errors and unclassifiable photographs can affect
   ecological inference.
2. Strong descriptors and matching platforms generate candidate pairs.
3. Candidate generation is not the same as evidence admission.
4. Expert review currently absorbs this decision implicitly.
5. PF-ERI formalizes the implicit pair-level evidence admission step.

### Concrete Work

- Add a manuscript-facing introduction outline with this exact chain.
- Add one figure panel showing the evidence chain:

```text
image archive
-> descriptor retrieval
-> candidate pair queue
-> PF-ERI evidence admission
-> expert review
-> cautious ecological inference
```

- In every main document, replace weak language such as `descriptor failures`
  with `post-retrieval evidence admission`.

### Success Criterion

The paper should still make sense if every descriptor in the future becomes
stronger. The reader should understand that PF-ERI is needed because evidence
admission is a distinct scientific step, not because current descriptors are
weak.

### Confidence After Repair

High, if the introduction and first figure make the evidence-chain gap explicit.
The remaining limitation is that the field-level consequence is still argued
from literature and workflow logic, not from a completed ecological
mark-recapture case study.

## Hardening Target 2: Novelty Protection

### Current Gap

PF-ERI now uses or discusses several recognizable tools:

```text
selective routing
risk-coverage
bootstrap uncertainty
multi-reviewer reliability
budget optimization
possible conformal or Bayesian extensions
```

These are useful safeguards, but they can make the project look like a mixture
of borrowed methods if they are presented as the novelty.

### Likely Reviewer Attack

```text
Is this just selective classification, conformal prediction, or image-quality
filtering applied to wildlife Re-ID?
```

### Required Repair

Keep the method hierarchy explicit:

```text
primary object: candidate pair
primary target: evidential admissibility
primary contribution: pair-level evidence admission
supporting tools: risk calibration, reviewer reliability, budget optimization
```

### Concrete Work

- Add a `Contribution hierarchy` box to the manuscript or methods report.
- In the methods, define PF-ERI features before naming any statistical wrapper.
- Move conformal/Bayesian/multi-annotator language into `safeguards` or
  `sensitivity analysis`, not the abstract's novelty sentence.
- Add a related-work table with four columns:

```text
nearby work
what it optimizes
what it does not claim
PF-ERI distinction
```

### Success Criterion

A reader should describe the novelty as:

```text
pair-level evidence admission for descriptor-retrieved wildlife Re-ID candidate
pairs
```

not:

```text
a conformal classifier for animal Re-ID
```

### Confidence After Repair

High. The risk is controllable by writing discipline. The novelty weakens only
if the paper foregrounds generic modeling tools more than the pair-level
evidence-admission object.

## Hardening Target 3: Evidence Strength

### Current Gap

The current CzechLynx evidence is strong for reviewability/admissibility:

```text
Descriptor only AUROC:      0.585
Image quality only AUROC:   0.725
PF-ERI evidence only AUROC: 0.780
Descriptor + PF-ERI AUROC:  0.799
```

Blind review reliability is also strong:

```text
Reviewer 1 binary kappa: 0.859305
Reviewer 2 binary kappa: 0.785098
```

However, the evidence strength score was not full because:

- Bobcat is not identity-labeled.
- Bobcat cannot support identity-performance claims.
- Feature sensitivity is only partially estimable in the current validation
  table.
- Application value is not yet shown in a complete ecological use case.

### Likely Reviewer Attack

```text
The model predicts reviewability on a curated CzechLynx pair set. Why should I
believe this matters beyond that validation table?
```

### Required Repair

Do not overclaim Bobcat identity. Instead, strengthen the evidence ladder in
three honest ways:

1. Confirm that PF-ERI signal persists under descriptor and quality controls.
2. Show that selective admission changes workflow risk, not identity accuracy.
3. Add an application-facing case simulation or audited pilot that shows what
   happens to the evidence queue before expert review.

### Concrete Work

Priority A:

- Produce a manuscript-ready table for:

```text
descriptor-only
quality-only
PF-ERI evidence-only
descriptor + PF-ERI
descriptor + quality + PF-ERI
```

- Report the same table separately for MegaDescriptor and DINOv2.
- Add quality-matched and high-quality-only sensitivity as appendices if not
  already paper-ready.

Priority B:

- Convert review-budget routing into a clear applied result:

```text
At fixed review budget B, PF-ERI selects candidate pairs with lower predicted
not-ready risk than descriptor-priority review.
```

- Keep this as workflow value, not identity value.

Priority C:

- Build a small ecological-pipeline simulation using known CzechLynx labels:

```text
candidate queue
-> admitted/deferred pairs
-> potential false evidence burden
-> same-ID candidate retention
```

- Report it as a pre-inference evidence hygiene simulation, not a population
  estimate.

### Success Criterion

The strongest result section should support this sentence:

```text
PF-ERI adds reviewability/admissibility signal beyond descriptor similarity and
image quality, and this signal can be used to route candidate pairs before they
enter expert review or downstream evidence records.
```

### Confidence After Repair

Medium-high. CzechLynx support can become very strong. Bobcat and ecological
application claims remain bounded unless audited Bobcat identity labels or a
real downstream use case are added.

## Hardening Target 4: Logic Closure

### Current Gap

The project history contains many phases, packets, routers, audits, and
modeling outputs. That is good for traceability, but it can make the paper read
like a chronology instead of a proof.

### Likely Reviewer Attack

```text
The work has many moving parts. Which result actually proves the central point?
```

### Required Repair

Build the manuscript around an evidence ladder:

1. Field problem: individual-level photographic evidence can be weak,
   unclassifiable, or observer-dependent.
2. Distinct object: descriptor-retrieved candidate pairs require evidence
   admission.
3. Construct validity: reviewability/admissibility labels are blind
   reliability-supported.
4. Core predictive result: PF-ERI predicts reviewability better than descriptor
   and quality baselines.
5. Mechanism result: high similarity can conflict with low pair-level evidence.
6. Routing result: defer/non-comparable are evidence governance outputs.
7. Scope result: Bobcat shows unlabeled workflow stress, not identity accuracy.

### Concrete Work

- Create a manuscript positioning outline with figure order.
- Collapse old phase references into method roles:

```text
pair construction
feature extraction
human reviewability validation
model comparison
selective routing
transfer-stress diagnostics
```

- For every result section, state:

```text
question answered
analysis
belief changed
claim boundary
```

### Success Criterion

The results should not read as:

```text
First we built Phase18A, then Phase18B, then Phase18C...
```

They should read as:

```text
First we show the construct is measurable. Then we show it is distinct from
descriptor similarity and image quality. Then we show it changes routing.
Finally we define its transfer-stress boundary.
```

### Confidence After Repair

High. This is a writing and organization problem, not a fundamental evidence
problem.

## Hardening Target 5: Reviewer Resistance

### Current Gap

The project has strong claim boundaries, but several reviewer objections remain
plausible:

1. Reviewability may not equal evidential admissibility.
2. PF-ERI may still be a quality proxy.
3. The validation set may not represent full candidate-queue behavior.
4. Human labels may encode reviewer preference rather than stable construct.
5. Constant features weaken component-level claims.
6. Bobcat transfer stress may be seen as descriptive without labels.

### Required Repair

Create a rebuttal-ready matrix before writing the manuscript.

### Concrete Work

| Objection | Needed answer | Evidence or repair |
| --- | --- | --- |
| Reviewability is subjective | Treat it as a measured construct with blind reliability, not objective identity truth. | Kappa, agreement, disagreement appendix, label protocol. |
| PF-ERI is just quality | Keep quality-only controls visible and add quality-matched sensitivity. | Model comparison and quality-stratified analysis. |
| PF-ERI is just descriptor similarity | Keep descriptor-only controls, high-similarity subset, and descriptor-stratified reporting visible. | AUROC comparison and descriptor-family analysis. |
| Targeted samples inflate effect | Use full-queue or identity-balanced samples for main claims; targeted samples only explain mechanism. | Phase18J/M style analyses and claim boundary. |
| Human reason labels are mechanisms | Call them reason families or component attributions, not proven mechanisms. | Confidence limitations table. |
| Bobcat lacks identity labels | Use Bobcat only for transfer-stress and workflow allocation. | Blocked-claim table. |

### Success Criterion

Every likely reviewer objection should have one of three answers:

```text
answered by main evidence
answered by appendix sensitivity
explicitly blocked as a claim
```

No major objection should be answered only by reassurance.

### Confidence After Repair

Medium-high. The strongest remaining non-repairable issue is the absence of a
fully audited Bobcat identity-validation set. That should remain a future-work
or extension target, not a hidden weakness.

## Highest-Value Next Work

Approved execution issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Use that issue pack to complete the hardening work one vertical slice at a time.

### Immediate Writing Work

1. Write a manuscript positioning outline using the evidence ladder above.
2. Add a related-work distinction table that protects pair-level novelty.
3. Add a rebuttal-ready objection matrix to the methods or supplement.

### Immediate Analysis Work

1. Make descriptor + quality + PF-ERI comparison paper-ready.
2. Make descriptor-specific result reporting paper-ready.
3. Make quality-matched and high-quality-only sensitivity paper-ready.
4. Make review-budget routing visually interpretable.

### Optional High-Value Evidence Work

1. Create a CzechLynx pre-inference evidence hygiene simulation.
2. Add audited Bobcat pair labels only if the project needs a real transfer
   validation claim.
3. Add a multi-annotator latent-label sensitivity only as a robustness appendix.

## Claim Boundary After Hardening

Even after all repairs, the project should not claim:

- automatic individual identification;
- Bobcat identity accuracy;
- descriptor replacement;
- top-k or mAP identity improvement as the main endpoint;
- universal thresholds across species or domains;
- distribution-free domain-shift guarantees;
- complete causal mechanism explanation.

The hardened claim should be:

```text
On reviewed CzechLynx candidate pairs after strong descriptor retrieval, PF-ERI
supports pair-level evidence admission by predicting human reviewability beyond
descriptor similarity and image quality, enabling empirical risk-aware routing
of candidate pairs before expert review or downstream evidence use.
```

## Definition Of Near-Full Confidence

The story approaches near-full confidence when all five conditions are met:

1. The introduction makes pair-level evidence admission necessary even under
   strong future descriptors.
2. The novelty hierarchy keeps pair-level admissibility above generic modeling
   tools.
3. The main results show PF-ERI signal beyond descriptor and quality controls.
4. The evidence ladder is ordered by inference, not by phase chronology.
5. The rebuttal matrix answers or explicitly blocks every major reviewer
   objection.

This is not a promise of universal truth. It is the practical standard for a
high-trust, reviewer-resistant scientific story.
