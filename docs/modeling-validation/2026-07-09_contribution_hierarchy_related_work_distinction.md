# Contribution Hierarchy And Related-Work Distinction

Date: 2026-07-09

Status: `STORY_HARDENING_ISSUE2_COMPLETE`

Parent issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Preceded by:

```text
docs/modeling-validation/2026-07-09_manuscript_evidence_chain_outline.md
```

## Purpose

This document completes Issue 2 of the story hardening issue pack. Its purpose
is to protect the project's novelty from being misread as a mixture of familiar
tools. PF-ERI uses modeling, reviewer reliability, risk routing, bootstrap
uncertainty, and review-budget analysis, but those are not the central
contribution. The central contribution is the scientific object and decision
layer:

```text
pair-level evidential admissibility after strong descriptor retrieval
```

The binding sentence remains:

```text
Similarity is not admissibility.
```

## Contribution Hierarchy

PF-ERI should be presented with a strict hierarchy. The paper should never give
readers the impression that the novelty is a generic conformal classifier, a
Bayesian annotation model, a better image-quality filter, a new descriptor, or a
replacement for expert review.

| Layer | Role in the project | Claim status | What not to claim |
| --- | --- | --- | --- |
| Primary scientific object | Descriptor-retrieved candidate pair `p=(query image, candidate image)` | Core | Do not move the object back to single-image quality or whole-dataset identity accuracy. |
| Primary target | Pair-level evidential admissibility / reviewability | Core | Do not describe the target as automatic identity recognition. |
| Primary contribution | A post-retrieval evidence admission layer that decides whether a candidate pair is admissible, risky, deferred, or non-comparable | Core | Do not claim PF-ERI is a new embedding, descriptor, or matching platform. |
| Main empirical test | Whether PF-ERI evidence features predict human reviewability beyond descriptor similarity and image quality | Core evidence | Do not claim this proves identity accuracy or population-level ecological improvement. |
| Descriptor controls | MegaDescriptor and DINOv2 candidate queues | Upstream controls | Do not frame PF-ERI as beating or replacing them as descriptors. |
| Risk routing | Empirical selective admission and review routing | Safeguard / utility layer | Do not claim unqualified distribution-free cross-domain guarantees. |
| Reviewer reliability | Blind reviewer agreement and disagreement appendices | Construct-validity safeguard | Do not claim reviewers prove animal identity or complete causal mechanisms. |
| Bootstrap uncertainty | Query-cluster uncertainty for CzechLynx reviewed pairs | Statistical safeguard | Do not generalize intervals to Bobcat identity performance. |
| Budget optimization | Predicted-risk constrained review allocation | Workflow safeguard | Do not claim the optimizer is the main scientific novelty. |
| Future Bayesian or conformal extensions | Optional sensitivity or calibration tools | Supporting appendix only | Do not let these tools displace pair-level evidence admission as the main contribution. |

This hierarchy is the defense against the "method soup" critique. PF-ERI is not
interesting because it combines many technical tools. It is interesting because
it names and operationalizes a missing pair-level evidence decision that sits
between candidate retrieval and downstream evidence use.

## Vertical Analysis: How The Gap Emerged

The older computer-vision story in wildlife Re-ID was naturally retrieval
centered. Camera traps and photographic monitoring created large archives, and
the urgent technical problem was how to make those archives searchable. Early
systems and later deep-learning descriptors made that possible by detecting
animals, cropping relevant regions, learning embeddings, ranking candidates,
and presenting likely matches for review.

That history explains why the field's language often centers on descriptors,
matching scores, top-k performance, and identity assignment. Those are the
natural metrics when the bottleneck is finding candidates in a large archive.
WildlifeDatasets and MegaDescriptor sit squarely in this lineage: they organize
animal Re-ID datasets and compare or provide representation models for
individual re-identification across species. This is valuable upstream work. It
helps answer which images are close in representation space.

Wildbook and WBIA-style platforms developed another crucial layer: operational
human-in-the-loop matching. Wildbook documentation describes workflows that
route annotations to identification algorithms, consolidate match results, and
present them for human review. That matters because real conservation workflows
do not end with a score. They require a user to inspect candidate matches and
set or confirm an individual identity. In that sense, existing platforms already
acknowledge that expert review remains part of the evidence chain.

The gap appears right at that interface. A descriptor score can make a candidate
visible, and a platform can present it for review, but neither fact alone
answers whether the pair has sufficient comparable evidence to enter an
individual-level evidence chain. A pair can be visually similar but still
unusable for responsible review if the visible body regions do not overlap, the
viewpoints are not comparable, the weakest image lacks pattern evidence, or the
descriptor score conflicts with the pair's visual evidence. PF-ERI is designed
for that missing decision.

The historical movement, then, is not "descriptors are wrong, so PF-ERI fixes
them." The more accurate story is that the field matured from manual comparison
to descriptor retrieval to platform-assisted review, and PF-ERI formalizes the
next decision layer: pair-level evidence admission before expert review and
cautious ecological use.

## Horizontal Analysis: Nearby Work And PF-ERI's Distinction

| Nearby work | What it optimizes | What it does not claim | PF-ERI distinction |
| --- | --- | --- | --- |
| Strong descriptors such as MegaDescriptor and DINOv2 | Representation quality, candidate retrieval, and identity-ranking performance on Re-ID datasets | They do not by themselves define whether a retrieved pair has admissible visual evidence for individual-level review. | PF-ERI consumes descriptor-retrieved pairs and evaluates their evidence status after retrieval. |
| WildlifeDatasets / animal Re-ID benchmark tooling | Dataset access, preprocessing, benchmarking, and model comparison for animal Re-ID | Benchmark tooling does not make pair-level evidence admission the target construct. | PF-ERI uses strong descriptor queues as upstream context but makes admissibility/reviewability the claim-bearing endpoint. |
| Wildbook / WBIA / MIEW-ID platforms | Detection, annotation, matching, candidate display, feature visualization, and human-assisted identity review | These platforms assist photo ID and present candidate matches, but do not fully formalize a separate pair-level admissibility target with descriptor/quality controls and defer routes. | PF-ERI can sit between candidate match presentation and expert confirmation as an evidence-governance layer. |
| Location-informed or metadata-constrained Re-ID | Ecological feasibility constraints, spatiotemporal filtering, and improved candidate selection | Metadata feasibility does not replace visual evidence comparability within the image pair. | PF-ERI evaluates visual admissibility and descriptor-evidence conflict, not location plausibility alone. |
| Active learning for camera-trap review | Reducing manual labeling effort by selecting informative or uncertain samples for human annotation | Active learning chooses what to label or review to improve efficiency or models; it does not necessarily classify a pair as admissible evidence for individual-level comparison. | PF-ERI routes evidence-qualified, conflict, deferred, and non-comparable pairs as evidence states, not merely annotation priorities. |
| Generic selective classification / reject option | Abstaining from predictions when confidence is low | Generic abstention usually treats rejection as a prediction-confidence decision, not a domain-specific evidence admissibility judgment. | PF-ERI's defer and non-comparable routes are evidence-governance outputs tied to visual comparability. |
| Conformal risk control | Post-processing model outputs to control a defined risk under calibration assumptions | It is a calibration framework, not a wildlife Re-ID evidence construct. It also requires its assumptions and calibration scope to be respected. | PF-ERI may use risk-control ideas as safeguards, but the scientific target remains pair-level admissibility. |
| Selective conformal risk control | Combining sample selection with risk control on selected examples | It does not define which visual pair conditions make wildlife Re-ID evidence admissible. | PF-ERI's route space gives the selection step domain meaning: accept, conflict review, defer low-evidence, or non-comparable. |
| Multi-annotator / latent-label models | Estimating latent labels and reviewer reliability from multiple annotators | Reviewer models validate measurement reliability; they are not the substantive evidence-admission contribution. | PF-ERI can use multi-annotator models to support construct validity while keeping pair-level admission as the core object. |
| Image-quality filtering | Excluding low-quality single images | Single-image quality cannot capture pair comparability, view compatibility, body-region overlap, or descriptor-evidence conflict. | PF-ERI explicitly separates weakest-image evidence from pair-level comparability and conflict. |

The important pattern is that none of these neighboring lines of work is the
enemy. Most of them are useful pieces of the larger evidence chain. PF-ERI's
claim is not that descriptor systems, platforms, active learning, or conformal
methods are inadequate in general. The claim is narrower and more durable:
after retrieval, the pair still needs an evidence-admission decision.

## Critical-Thinking Guardrails

The strongest threat to Issue 2 is not lack of novelty. The strongest threat is
claim drift. If the paper presents every supporting method with equal emphasis,
readers may infer that PF-ERI is a generic stack of uncertainty tools. That
would weaken the paper because generic tools already have their own literatures
and because the project does not need to win a novelty contest against
conformal prediction, Bayesian annotation models, or active learning.

The second threat is construct drift. Pair-level evidential admissibility must
not slide into identity truth, review convenience, or single-image quality. The
target is a measured reviewability/admissibility construct, supported by human
review and reliability checks. It is not the same thing as true animal identity,
and it is not the same thing as descriptor rank.

The third threat is false dichotomy. The paper should not imply that one must
choose between strong descriptors and PF-ERI. The correct relationship is
serial, not competitive:

```text
strong descriptor retrieval -> candidate queue -> PF-ERI evidence admission
```

That serial relationship is what makes the project robust to future descriptor
improvements. If candidate generation gets stronger, the evidential-admission
question still remains because a pair can still be high-scoring yet weak as
individual-level evidence.

The fourth threat is overgeneralization. Issue 2 supports a conceptual and
positioning claim. It does not prove that PF-ERI generalizes to every species,
camera system, or domain. It protects the contribution hierarchy. The empirical
strength of the contribution still depends on the later issues: incremental
model evidence, quality/similarity sensitivity, review-budget utility, and the
final objection matrix.

## Safe Manuscript Wording

Use this:

```text
PF-ERI introduces pair-level evidential admissibility as a post-retrieval target
for wildlife Re-ID candidate review. Strong descriptors generate candidate
pairs; PF-ERI evaluates whether those pairs contain admissible visual evidence
for individual-level review.
```

Use this:

```text
Risk routing, reviewer reliability, bootstrap uncertainty, and budget
optimization are safeguards around the pair-level evidence-admission claim, not
the primary novelty.
```

Use this:

```text
PF-ERI is compatible with strong descriptor and matching platforms because it
answers a downstream evidence question rather than replacing candidate
generation.
```

## Blocked Manuscript Wording

Do not use:

```text
PF-ERI is a new descriptor.
PF-ERI replaces MegaDescriptor, DINOv2, Wildbook, WBIA, or MIEW-ID.
PF-ERI is mainly a conformal risk-control method.
PF-ERI is mainly a Bayesian reviewer model.
PF-ERI is an image-quality filter.
PF-ERI automatically identifies individuals.
PF-ERI validates Bobcat identity accuracy.
```

## Issue 2 Acceptance Check

A contribution hierarchy is now explicitly defined. The primary contribution is
pair-level evidence admission for descriptor-retrieved wildlife Re-ID candidate
pairs. Supporting tools are labeled as safeguards rather than main novelty. The
related-work distinction table includes nearby work, what each line optimizes,
what it does not claim, and PF-ERI's distinction. The document blocks the
interpretation that PF-ERI is mainly a conformal classifier, Bayesian model,
quality filter, descriptor, or identity model.

## Sources Used For Positioning

- WildlifeDatasets / MegaDescriptor paper:
  https://arxiv.org/abs/2311.09118
- Wildbook matching process documentation:
  https://wildbook.docs.wildme.org/data/matching-process.html
- Wildbook image analysis pipeline documentation:
  https://wildbook.docs.wildme.org/introduction/image-analysis-pipeline.html
- Flukebook / WBIA platform paper:
  https://link.springer.com/article/10.1007/s42991-021-00221-3
- Conformal Risk Control, ICLR 2024:
  https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf
- Selective Conformal Risk Control:
  https://arxiv.org/abs/2512.12844
- Active learning for camera-trap species identification and counting:
  https://arxiv.org/abs/1910.09716
