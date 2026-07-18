# Results Evidence Ladder

Date: 2026-07-09

Status: `STORY_HARDENING_ISSUE7_COMPLETE`

Parent issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Preceded by:

```text
docs/modeling-validation/2026-07-09_manuscript_evidence_chain_outline.md
docs/modeling-validation/2026-07-09_contribution_hierarchy_related_work_distinction.md
docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md
docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md
docs/modeling-validation/2026-07-09_review_budget_routing_value.md
docs/modeling-validation/2026-07-09_pre_inference_evidence_hygiene_simulation.md
```

## Purpose

This document completes Issue 7 of the story hardening issue pack. It rewrites
the manuscript results as an evidence ladder instead of a chronological phase
report. The reader should not have to learn the history of Phase18, legacy-code
folders, review tools, and later hardening passes in order to evaluate the
claim. The results should move in the order in which scientific belief changes.

The binding thesis remains:

```text
Similarity is not admissibility.
```

The results sequence should therefore ask a narrow series of questions. First,
does the project measure a real reviewability and evidential-admissibility
construct? Second, is the signal distinct from descriptor similarity and
single-image quality? Third, do the pair-level features expose a plausible
evidence mechanism rather than only a score correlation? Fourth, does routing
the queue by this pair-level signal improve review utility under finite expert
attention? Fifth, what happens when the same workflow is moved to Bobcat data
where identity labels are not available?

## Manuscript Results Order

### Result 1: Construct Validity Of Pair-Level Reviewability

The first result section should establish the measurement target before any
model comparison. The question answered is whether the study has a defensible
human endpoint for pair-level evidence admission. The analysis is the reviewed
CzechLynx candidate-pair table, including the identity-balanced blind-reviewed
pair set and the route labels that distinguish review-ready pairs from
not-ready or uncertain pairs. The belief changed by this section is that
reviewability is not merely an informal preference or a convenience label. It
is the measured construct that defines whether a descriptor-retrieved pair can
reasonably enter individual-level visual review.

This section should report the review-label design, the blind confirmation
closure already recorded for the identity-balanced set, and the route taxonomy
used by PF-ERI. The manuscript should use old phase names only in a
reproducibility sentence or table footnote, such as "the reviewed table was
assembled from the Phase18M identity-balanced review artifacts." It should not
begin the results with "Phase18M showed..." because that makes the paper read
like a lab notebook rather than an inference chain.

The claim boundary is equally important. This construct-validity result does
not prove animal identity. It does not establish Bobcat identity labels. It
does not prove that every future reviewer would make identical decisions. It
supports the narrower statement that the project has a concrete, reviewed
pair-level endpoint for evidential admissibility.

### Result 2: PF-ERI Signal Is Distinct From Descriptor Similarity And Image Quality

The second result section should test the two strongest alternative
explanations. The question answered is whether PF-ERI merely restates the
descriptor score or filters out bad images. The analysis is the Issue 3
incremental model comparison and the Issue 4 quality and similarity sensitivity
package. The central comparison is not PF-ERI against a weak descriptor. The
central comparison is PF-ERI under active controls: descriptor-only,
quality-only, PF-ERI-only, descriptor plus quality, descriptor plus PF-ERI, and
descriptor plus quality plus PF-ERI, followed by quality-matched,
high-quality-only, high-similarity-only, and rank/similarity-stratified checks.

This section changes the reader's belief from "PF-ERI may only be a proxy" to
"quality and similarity do not fully exhaust the reviewability construct." The
pooled model table shows that PF-ERI evidence alone aligns with reviewability
and that the full model has a small pooled increment over descriptor plus
quality. The sensitivity tables provide the stronger story: inside estimable
quality strata, in the high-quality subset, in the high-similarity subset, and
across rank/similarity strata, higher PF-ERI evidence remains positively
aligned with human reviewability. The manuscript should report the positive
pooled contrasts while explicitly naming the bounded areas, especially the
constant or sparse quality fields and the non-uniform descriptor-specific
quality strata.

The claim boundary is that this result should not be written as universal
superiority over descriptor plus quality. It does not say that PF-ERI always
improves AUROC or AUPRC in every descriptor-specific scope. It says that the
reviewability signal cannot be reduced to descriptor similarity or the estimable
image-quality controls in the current CzechLynx reviewed evidence.

### Result 3: Pair-Level Evidence Mechanism And Descriptor-Evidence Conflict

The third result section should explain why the signal is scientifically
meaningful. The question answered is whether PF-ERI is only a predictive score
or whether it exposes a pair-level evidence mechanism. The analysis should
combine the pair-feature interpretation from PF-ERI with the high-similarity
and rank/similarity sensitivity results. The manuscript should emphasize that
PF-ERI evaluates a pair, not only two images separately. The relevant evidence
conditions include weakest-image evidence, shared visible pattern, body-region
overlap, viewpoint or geometry comparability, and the possibility that high
descriptor similarity appears under weak comparable evidence.

This section changes belief by moving from predictive association to domain
mechanism. A pair can be descriptor-similar and still not admissible if the
visible evidence does not support a responsible individual-level comparison.
The mechanism is not "the descriptor failed." The mechanism is that candidate
retrieval and evidence admission answer different questions. Descriptor
retrieval asks which images are visually close enough to consider. PF-ERI asks
whether the retrieved pair contains comparable evidence that can be trusted in
review.

The claim boundary is that the current evidence supports a pair-level
reviewability mechanism more strongly than a fully isolated feature-causal
mechanism. Some feature dimensions have limited variation in the current
reviewed table, and conflict-specific estimates must remain bounded where
descriptor-pair fields are sparse or non-estimable. This section should
therefore use careful language: "consistent with pair-level evidence
admission," "not exhausted by descriptor similarity," and "evidence mechanism,"
not "causal proof of every PF-ERI feature."

### Result 4: Selective Routing And Review-Budget Utility

The fourth result section should turn the evidence signal into workflow value.
The question answered is whether pair-level admission changes what an expert
sees under limited review capacity. The analysis is the fixed-budget review
utility comparison and the CzechLynx pre-inference evidence hygiene simulation.
The fixed-budget result compares PF-ERI-prioritized review with descriptor
priority on the same reviewed pair pool. The pre-inference simulation routes
candidate pairs into admitted or deferred evidence states before expert review
or downstream inference, then audits review-ready rate, not-ready/uncertain
burden, same-ID candidate retention, and false-candidate burden.

This section changes belief from "PF-ERI predicts a label" to "PF-ERI can
govern a candidate queue." In the fixed-budget analysis, PF-ERI priority
reduces pooled not-ready or uncertain burden in several practically meaningful
budget settings, including the budget-100 and budget-200 examples. In the
pre-inference simulation, admitted pairs have a much higher review-ready rate
than deferred pairs, while the deferred set concentrates not-ready or uncertain
evidence. That is the operational value of the method: it can move weaker or
riskier evidence out of the immediate evidence-use path.

The claim boundary is that review utility is not identity accuracy. A
different-ID pair can be review-ready if the reviewer can confidently reject
it. Same-ID retention is a secondary candidate-coverage audit in the known-ID
CzechLynx setting. The section must not imply automatic identity assignment,
population estimation, mAP improvement, MRR improvement, or top-k identity
superiority.

### Result 5: Bobcat Transfer-Stress Boundary

The fifth result section should appear after the CzechLynx evidence has already
established the known-ID reviewability story. The question answered is not
whether PF-ERI identifies Bobcats. The question is how the evidence-admission
workflow behaves when moved into unlabeled Bobcat wild and urban transfer-stress
settings. The analysis is the Bobcat transfer-readiness and wild/urban
transfer-stress artifacts. Strong-descriptor Bobcat transfer readiness produced
unlabeled nearest-neighbor pair queues with route summaries for MegaDescriptor
and DINOv2. The wild/urban transfer-stress module then applied the evidence
router to Bobcat pair scopes and reported evidence burden, route counts, and
calibration drift relative to CzechLynx, while keeping identity metrics blocked.

This section changes belief by showing the scope boundary of the method.
PF-ERI can be applied as a workflow-allocation and evidence-stress diagnostic
in Bobcat data, but the absence of audited Bobcat individual identities means
the manuscript cannot claim Bobcat same-ID accuracy, false-match accuracy, or
identity-level transfer. The scientific value of this result is not a positive
Bobcat accuracy claim. It is the disciplined boundary: the same pair-level
governance layer can flag transfer evidence pressure without pretending that
unlabeled data validate identity decisions.

The claim boundary should be stated in the result heading or final sentence.
Bobcat is a transfer-stress and workflow-allocation context only unless audited
identity labels or audited Bobcat same/different pair labels are added later.
This protects the paper from the most dangerous overclaim.

## Compact Evidence Ladder Table

| Manuscript result | Question answered | Analysis | Belief changed | Claim boundary |
| --- | --- | --- | --- | --- |
| Construct validity | Is reviewability a defensible pair-level endpoint? | CzechLynx reviewed candidate pairs and blind identity-balanced closure | Pair-level admissibility is a measured construct, not a loose preference | Not animal identity truth, not Bobcat labels, not universal reviewer agreement |
| Distinct from descriptor and quality | Is PF-ERI only similarity or quality? | Incremental models plus quality and similarity sensitivity | Similarity and quality do not fully exhaust human reviewability | Not universal descriptor-specific superiority |
| Evidence mechanism | Does the signal reflect pair-level evidence conditions? | Pair-feature interpretation, high-similarity checks, rank/similarity strata | Candidate retrieval and evidence admission are different decisions | Not causal proof of every feature |
| Selective routing utility | Does PF-ERI change finite-budget review? | Fixed-budget review utility and pre-inference evidence hygiene simulation | PF-ERI can govern candidate queues and concentrate weaker evidence into deferral | Review utility only, not identity accuracy or ecological outcome |
| Bobcat transfer stress | What transfers without identity labels? | Bobcat transfer-readiness and wild/urban evidence-stress artifacts | PF-ERI can audit transfer evidence pressure without claiming identity performance | Bobcat identity accuracy remains blocked |

## Recommended Results Section Headings

The manuscript should use headings that state the inference, not the phase
number. A strong results sequence is:

```text
1. Human reviewability defines the pair-level evidence-admission endpoint.
2. PF-ERI evidence is not reducible to descriptor similarity or image quality.
3. High-similarity candidate pairs can still lack admissible pair evidence.
4. Selective evidence routing reduces not-ready or uncertain review burden.
5. Bobcat transfer-stress exposes workflow evidence pressure without identity claims.
```

These headings make the central claim easier to evaluate than a chronological
report. Phase and legacy names should remain in methods tables, artifact links,
and reproducibility appendices only.

## Issue 7 Acceptance Check

A manuscript results outline now exists. Each result section states the
question answered, the analysis, the belief changed, and the claim boundary.
Old phase names are used only as provenance, not as the main narrative
structure. The result order follows inference logic from construct validity to
quality/similarity distinction, pair-level mechanism, selective routing utility,
and Bobcat transfer-stress boundary. Bobcat appears only as transfer stress and
workflow allocation because audited Bobcat identity labels are not part of the
current validated endpoint.
