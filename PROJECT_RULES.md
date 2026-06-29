# PROJECT_RULES.md

## Project Identity

This repository supports the project:

PF-ERI for Same-Genus Wild-to-Urban Lynx Re-ID Evidence Reliability

The project method is **PF-ERI Reliability-Aware Pairwise Evidence Learning**. PF-ERI is not a new Re-ID descriptor, not a single hybrid score, not an automatic identity-assignment system, and not a complete Re-ID model. It is an evidence-utility mechanism for estimating whether same-genus Lynx camera-trap images and image pairs contain admissible identity evidence for retrieval, reranking, risk control, and review-readiness.

The central project goal is to validate pair-level evidence reliability on known-ID wild Eurasian lynx and test whether the calibrated reliability model transfers to urban bobcat monitoring as a same-genus field-readiness stress test. PF-ERI may influence the Re-ID pipeline through:

1. image-level evidence utility from visual admissibility factors;
2. pair-level evidence admissibility from weakest-image evidence, side/flank comparability, pattern evidence, viewpoint compatibility, and failure penalties;
3. descriptor-evidence conflict detection when high descriptor similarity is not supported by visual comparability;
4. risk-constrained filtering, candidate reranking, and review-defer decisions;
5. review-readiness decisions such as accept, review, defer, species-level only, or non-comparable;
6. held-out identity splits, matched controls, quality-proxy controls, no-training references, and coverage/risk safeguards to prevent easier-sample overclaiming;
7. same-genus cross-context evidence shift analysis between CzechLynx and UWIN bobcat.

The project does not identify individual animals. It evaluates whether imperfect Lynx camera-trap evidence can be modeled as pair-level admissibility and used to control retrieval, reranking, review-readiness, or diagnostic analysis in a Re-ID pipeline. The earlier review/defer/exclude policy, fixed-descriptor reranking, and Phase 13D training attempts are supporting foundations, not the final endpoint.

## Binding Gap And Direction Rule

The binding project gap is defined in:

```text
docs/phase16/phase16i_gap_rationale.md
```

This gap is now project-level policy. PF-ERI must be framed as a
post-retrieval evidence reliability and review-routing layer that sits after a
strong descriptor or matching platform and before expert review or downstream
use.

Use this locked direction:

```text
strong descriptor / matching platform
-> candidate queue
-> PF-ERI pair-level evidence admissibility
-> descriptor-evidence conflict and risk estimate
-> evidence-routed review action
-> cautious downstream use
```

The project must not be reframed as:

```text
PF-ERI beats MegaDescriptor/MiewID/WildlifeTools as a descriptor
PF-ERI is a replacement Re-ID model
PF-ERI's main claim is top-k identity-ranking improvement
PF-ERI validates Bobcat identity accuracy without labels
PF-ERI is generic image quality filtering
```

If a result shows discrimination signal but does not beat descriptor-only top-k
ranking, the correct response is not to force a ranking-improvement claim. The
correct response is to evaluate review utility: evidence admissibility,
descriptor-evidence conflict, false-candidate burden, positive retention, review
burden, abstention/risk coverage, and expert-audit agreement.

Any future "tool 2.0" or open-source integration must preserve this direction:
PF-ERI may wrap, audit, and route outputs from Wildbook/WBIA, MegaDescriptor,
MiewID, WildlifeTools, WildFusion, or equivalent systems, but it must not be
presented as replacing their descriptor or identity-database role.

## Wild-to-Urban Evidence Propagation Rule

The wild-to-urban comparison must be framed as a three-layer evidence-risk propagation problem, not as a simple image-quality comparison.

Use this structure:

```text
image-level evidence shift -> pair-level comparability shift -> retrieval/review contamination
```

Layer roles:

1. Image-level evidence shift measures how single-image identity evidence differs between wild CzechLynx and urban/peri-urban bobcat data.
2. Pair-level comparability shift explains how unreliable evidence enters Re-ID, because candidate errors occur when query-gallery pairs are compared.
3. Retrieval/review contamination measures the downstream consequence: false-candidate burden, conflict enrichment, review load, defer/species-level-only rate, and risk-coverage tradeoff.

Pair-level analysis is therefore a core mechanism layer inside the wild-to-urban project, not a separate side project. It should answer:

```text
Do urban/peri-urban bobcat candidate pairs show more non-comparable or descriptor-evidence-conflict structure than known-ID wild lynx pairs?
```

Claim boundary:

```text
CzechLynx known-ID pairs can validate false-candidate risk and positive retention.
Urban bobcat pairs without verified individual IDs can validate pair comparability, review-readiness, descriptor-evidence conflict frequency, and contamination pressure, but not true false-match accuracy.
Urban bobcat identity validation is allowed only if verified individual labels or an audited same/different pair set exists.
```

Do not reduce the urban/wild comparison to "urban images are lower quality." The stronger claim is that context changes the structure by which image evidence becomes pair evidence and then Re-ID/review risk.

## 2x2 Risk-Controlled Evidence Design Rule

The project must use a two-axis evidence-risk design:

```text
environment axis: wild vs urban/peri-urban
evidence axis: high-confidence evidence vs low-evidence stress cases
```

This creates four required analysis quadrants:

```text
wild CzechLynx high-confidence evidence
wild CzechLynx low-evidence stress cases
urban/peri-urban bobcat high-confidence evidence
urban/peri-urban bobcat low-evidence stress cases
```

The project must not treat uncertain or difficult images as simple waste. It must route them into the correct scientific role:

```text
core_training
retrieval_evaluation
wild_urban_clean_comparison
low_evidence_stress_test
manual_audit_calibration
excluded_non_felid_or_duplicate
```

Training and clean wild-vs-urban comparison should use high-confidence evidence. Low-evidence images should not silently enter core training, but they must be retained as stress-test evidence for risk-coverage curves, review burden, descriptor-evidence conflict, and contamination analysis.

Use this operating rule:

```text
Do not discard uncertainty; route it.
Do not train on low-evidence noise; stress-test with it.
Do not compare only clean data; report full-pool, clean-set, and stress-set behavior.
```

The mathematical framing is:

```text
maximize usable evidence coverage
subject to estimated evidence risk <= tau
```

or, at pair level:

```text
select image/pair set S
to maximize expected evidence utility
while controlling false-comparison or training-contamination risk
```

## Core Scientific Boundary

- Do not claim this project identifies true individual animals.
- Do not claim a new Re-ID model.
- Do not claim a new Re-ID descriptor.
- Do not claim descriptor replacement or top-k identity-ranking improvement as
  the main contribution unless a later leakage-controlled, grouped or
  identity-aware held-out analysis directly supports that exact claim.
- Do not claim population estimation.
- Do not claim a universal threshold across felid species, patterned animals, or general animal Re-ID.
- Do not claim PF-ERI improves metric learning unless PF-ERI-informed training beats relevant random matched and quality-proxy matched controls under held-out identity-split evaluation for the stated metric family.
- Do not claim PF-ERI robustly improves fixed-descriptor Re-ID accuracy unless a later held-out analysis directly supports that claim.
- Do not claim WildTrax/UWIN identity validation without verified individual IDs.
- Do not claim UWIN bobcat identity validation without verified individual labels or an explicitly audited human pair set.
- Do not claim urbanization causes Re-ID failure unless urban context variables are explicitly measured and controlled.
- Do not claim Mainland Clouded Leopard or Marbled Cat Re-ID validation in the current study.
- Do not frame the validated scope as general animal Re-ID.
- Do not present `hybrid_eri` as a standalone safety score or pure evidence-quality score.
- Re-ID embeddings are fixed measurement signals for validation, model-support prioritization, and Phase 9 reranking. They are not newly trained descriptors in the current study.
- Separate PF-ERI / visual evidence reliability from fixed descriptor similarity support when reporting outputs.

## Re-ID-Specific Evidence Utility Boundary

PF-ERI must not be framed as generic image quality filtering.

Use this boundary:

```text
Generic quality filtering asks whether an image is clear.
PF-ERI asks whether an image or candidate pair contains useful individual-identification evidence for patterned-felid Re-ID.
```

PF-ERI's defensible novelty is the integration of:

```text
visual identity evidence
pair-level evidence admissibility
fixed descriptor support
reciprocal and margin confidence
descriptor disagreement
descriptor-evidence conflict
risk-coverage constraints
held-out and random-control validation
```

into a reliability-aware pairwise evidence model for patterned-felid Re-ID.

## Pairwise Evidence Learning Boundary

The current endpoint is not merely visual-evidence description or review-control policy. The final project goal is to determine whether PF-ERI can model pair-level evidence admissibility in known-ID wild lynx and whether that evidence-risk model transfers to urban bobcat monitoring as a same-genus external stress test.

Core hypothesis:

```text
PF-ERI can make same-genus Lynx Re-ID more reliable by estimating which image pairs contain admissible identity evidence, identifying descriptor-evidence conflict, and deciding when retrieved candidates should be accepted, reviewed, deferred, or downgraded to species-level evidence.
```

Primary research questions:

```text
RQ1: Can PF-ERI predict unreliable candidate edges in known-ID wild Eurasian lynx Re-ID?
RQ2: Do descriptor-evidence conflicts explain false or uncertain candidate matches better than descriptor similarity or image quality alone?
RQ3: Does urban bobcat monitoring show a shifted evidence-risk distribution relative to wild CzechLynx?
RQ4: In a small human-audited UWIN bobcat pair set, can PF-ERI identify pairs that should be accepted, reviewed, deferred, or downgraded to species-level evidence?
RQ5 exploratory: If sufficient UWIN bobcat identity labels become available, can PF-ERI-calibrated risk policies reduce false-candidate burden in urban bobcat Re-ID?
```

Primary comparison set:

```text
raw descriptor retrieval
PF-ERI evidence-routed review utility
PF-ERI-aware reranking only as a diagnostic or secondary endpoint
quality-only filtering/reranking
random same-size and same-coverage controls
uniform supervised contrastive learning
random matched image selection
quality-proxy matched image selection
PF-ERI-informed image selection
PF-ERI plus quality hybrid image selection
PF-ERI-conditioned positive-pair weighting
PF-ERI unreliable-hard-negative control
PF-ERI descriptor-evidence conflict-aware variants
UWIN bobcat evidence distribution stress test
UWIN bobcat human-audited same/different/uncertain/non-comparable pair set
accept/review/defer/species-level-only policy transfer
```

Success is layered. RQ1 may succeed by showing PF-ERI is a valid evidence signal in known-ID CzechLynx. RQ2 may succeed by identifying a descriptor-evidence conflict mechanism. RQ3 may succeed by showing measurable UWIN bobcat evidence-risk distribution shift relative to CzechLynx. RQ4 may succeed if PF-ERI predicts human-audited urban bobcat review judgements better than descriptor similarity or quality-only controls. RQ5 is optional and requires verified UWIN bobcat identity labels. Primary metrics are false-candidate burden, positive retention, review-readiness policy proportions, descriptor-evidence conflict enrichment, human-audit agreement, review burden, abstention/risk coverage, and query coverage. mAP/MRR/top-k are allowed only when identity labels exist, and they are not the main Phase 16/17 claim unless PF-ERI clears descriptor-only controls under the required split discipline.

Current interpretation:

```text
Image-level PF-ERI selection is not enough if it does not consistently beat quality-proxy controls. The central scientific direction is pair-level PF-ERI admissibility inside retrieval and review-readiness, because individual Re-ID is a pairwise evidence problem. Metric learning is now diagnostic/optional, not the main next contribution.
```

## Scientific Upgrade Rule

Weak, modest, or mixed empirical results must not automatically downgrade the project goal. Treat them first as diagnostic evidence about where the current formulation is underpowered, mis-specified, or missing a needed modeling layer.

When a result is only small, unstable, or partially negative, follow this sequence:

1. Diagnose whether the limitation comes from descriptor ceiling, data structure, endpoint choice, fixed weighting, missing model capacity, split design, or an incorrect scientific claim.
2. Separate negative evidence against a weak implementation from negative evidence against the core research direction.
3. Upgrade the formulation before reducing the ambition:
   - from image-level filtering to pair-level admissibility;
   - from pooled candidate false rate to query-level burden and positive retention;
   - from fixed hand-written weights to held-out calibrated or constrained monotonic models;
   - from no-training reranking to reliability-aware metric learning only after controls justify it;
   - from generic quality filtering to descriptor-evidence conflict and hard-negative mechanism modeling.
4. Only narrow a claim after a stronger model, better endpoint, and proper controls have been tested.
5. Never present a modest reranking gain as the final contribution if the diagnosis points to a deeper model needed for the main research question.

Use this project stance:

```text
Modest current effects are not the final claim. They are evidence that PF-ERI contains signal, and they identify which modeling layer must be upgraded next.
```

The project should progress by controlled escalation, not by untested overclaiming and not by premature retreat. Each phase should either strengthen the evidence, identify the bottleneck, or justify the next model upgrade.

## Problem-Solving Before Rule Mutation Rule

Do not weaken evidence-admission rules just because the current result is inconvenient, sparse, or operationally slow. When a high-confidence set is too small, first solve the bottleneck rather than changing the definition of high-confidence evidence.

Required sequence:

1. Verify the count, source pool, duplicate rate, and detector/model coverage.
2. Separate "not yet processed" from "processed and failed."
3. Scale the existing data source before changing the evidence definition.
4. Improve the measurement layer before relaxing the scientific claim:
   - run detector coverage on more candidates;
   - use GPU/Colab when local CPU is the bottleneck;
   - add human review for borderline candidates;
   - add a stronger detector, pose/view classifier, or calibrated model if needed;
   - expand the same dataset family before mixing new dataset contexts.
5. Treat rule changes as a last resort. They require an explicit written
   rationale showing that the rule was scientifically mis-specified, not merely
   too strict for the desired sample size.

## Best-Product Migration Test Rule

When evaluating project direction, novelty, or next-step improvements, do not
compare PF-ERI only against basic baselines or strawman workflows. First identify
the strongest relevant real-world system, product, or research toolkit for the
same user problem, then evaluate PF-ERI from the perspective of that system's
heavy user.

Use this test:

```text
If I were a loyal expert user of the strongest existing wildlife Re-ID or
camera-trap AI workflow, what would make me switch to PF-ERI, and what would
make me unable to go back after using it?
```

This means every recommendation should consider:

1. what best-in-class users already get from systems such as Wildbook/IBEIS,
   Wildlife Insights, MegaDetector/Timelapse-style workflows, WildlifeTools,
   MegaDescriptor, WildFusion, or equivalent current tools;
2. what PF-ERI uniquely adds beyond identity ranking, species classification,
   blank filtering, or generic image quality control;
3. whether PF-ERI removes a real pain point for expert users, such as
   non-comparable high-similarity candidates, uncertain review queues,
   cross-context evidence drift, or uncalibrated manual review burden;
4. whether the proposed feature is strong enough that an expert user would
   switch from the best existing workflow, not merely prefer it over a weak
   baseline;
5. which product-level gaps remain before such migration is credible.

Do not present an improvement as strong merely because it beats a basic
baseline. A strong contribution must survive comparison with the best available
workflow for the same problem and must explain why a serious user would adopt it.

## Evidence-Routed Review Layer Rule

The next active modeling target is **PF-ERI Evidence-Routed Review Layer**.
This layer must be evaluated as a practical reliability module that could sit
between existing wildlife Re-ID descriptors/platforms and expert human review.
It does not replace Wildbook/IBEIS-style identity databases, Wildlife
Insights/MegaDetector-style camera-trap processing, or MegaDescriptor/WildFusion
style descriptor models.

Use this product-level definition:

```text
Existing Re-ID systems answer: which candidate looks most similar?
PF-ERI Evidence-Routed Review answers: is this candidate comparison supported by admissible identity evidence, and what should the reviewer do with it?
```

The active output space is:

```text
accept
review
defer
species-level only
non-comparable
```

The active scientific mechanism remains:

```text
image-level evidence shift -> pair-level comparability shift -> retrieval/review contamination
```

The active algorithmic upgrade must combine:

1. fixed descriptor similarity or descriptor percentile;
2. PF-ERI pair comparability;
3. weakest-image evidence utility;
4. generic quality controls, including animal size, detector confidence, blur,
   occlusion, and crop risk;
5. descriptor-evidence conflict;
6. coverage and review-budget constraints;
7. random, descriptor-only, and quality-only matched controls.

Do not claim PF-ERI alone is superior to quality filtering in every block.
Phase 14 showed that severe low-evidence stress cases can require a
PF-ERI-plus-quality hybrid policy. Treat this as a boundary-condition discovery
and a reason to upgrade the model, not as a reason to relax the evidence rules.

Every new Phase 15 recommendation must pass a migration question:

```text
Would an expert who already uses strong descriptor matching plus manual review gain a decision they did not previously have: accept, review, defer, species-level only, or non-comparable, with evidence and risk attached?
```

If the answer is no, the feature is probably only an analysis artifact and
should not become part of the main system.

Use this operating rule:

```text
If high-confidence images are insufficient, increase evidence discovery and verification.
Do not redefine low-evidence images as high-confidence to reach a target count.
```

Current Phase 14 implication:

```text
Bobcat high-confidence evidence must be found by processing the full available bobcat pool and then, if needed, expanding to compatible camera-trap datasets. It must not be manufactured by weakening the Re-ID evidence definition.
```

## Phase 16 Balanced Strategy Rule

Phase 16 changes the active direction from a mainly Phase 15 review-routing
prototype into **PF-ERI 2.0: a competition-ready, paper-defensible, and
tool-oriented evidence reliability workflow**.

Use this priority balance:

```text
competition/showcase clarity: 40%
paper-defensible validation: 35%
practical review-routing utility: 25%
```

The active Phase 16 claim is:

```text
PF-ERI 2.0 models whether strong Re-ID candidate pairs contain admissible identity evidence and routes them into risk-controlled review actions under cross-context evidence shift.
```

The active Phase 16/17 claim is not:

```text
PF-ERI 2.0 improves top-k identity ranking over descriptor-only
```

That stronger claim is currently unsupported and must remain blocked unless a
future leakage-controlled, grouped or identity-aware held-out validation clears
the descriptor-only improvement gate. Until then, Phase 16/17 should optimize
and report review utility rather than ranking lift.

This means the project must no longer be framed as only:

```text
urban vs wild image quality comparison
```

or only:

```text
pre-Re-ID photo filtering
```

The new core frame is:

```text
strong Re-ID retrieval -> PF-ERI pair-level admissibility -> risk-controlled review action
```

with wild-to-urban transfer as the main external stress design:

```text
known-ID CzechLynx validates the reliability model;
urban/peri-urban bobcat tests review-readiness and evidence-risk shift.
```

Phase 16 required safeguards:

These safeguards are data-governance and evaluation-design rules. They improve
the credibility of the PF-ERI model, but they are not the core scientific
contribution and must not replace the pair-level evidence utility/risk-routing
modeling objective.

1. **Laterality-aware sampling and pair audit**: left, right, both, frontal,
   rear, and unknown should be represented explicitly when labels are available.
   This is primarily a photo-selection, audit, and pair-comparability rule.
   Pair-level outputs should distinguish same-side, opposite-side, non-lateral,
   and unknown-side comparisons, but laterality balance alone is not the main
   algorithmic contribution.
2. **Background/site leakage pressure audit**: candidate similarity must be
   audited with the available path, date, site, camera, sequence, crop/full-image,
   or protected metadata-derived proxies. In Phase 16A this is a risk-pressure
   diagnostic, not a causal proof. It may only be framed as a stronger leakage
   analysis or leakage proof if site-disjoint known-ID validation,
   background-only controls, crop-vs-full-image comparisons, or verified
   same-site/different-individual labels are available.
3. **Strong-model benchmark preparation**: PF-ERI must be evaluated around
   best-available descriptor or local-matching systems, not only weak baselines.
   MegaDescriptor remains the fixed baseline; WildFusion or an equivalent strong
   local/global matching model is the preferred next external benchmark if
   runnable.

Phase 16 optional extensions are deliberately secondary:

```text
Phase 16B: ecological/spatiotemporal plausibility prior
Phase 16C: augmentation or generative robustness stress test
Future: captive imagery as a high-quality calibration ceiling
```

Do not start generative augmentation, captive-data expansion, or full ecological
prior modeling until the Phase 16A data-governance gates pass:

```text
laterality-aware sampling and pair audit
background/site leakage pressure audit
strong-model benchmark package or returned scores
```

Urban-vs-wild remains important, but its role is now:

```text
transfer-stress and evidence-risk shift axis
```

not:

```text
standalone proof that urban animals are harder to identify
```

Bobcat outputs remain review-readiness and evidence-risk outputs unless verified
individual labels or audited same/different pairs exist. Do not report bobcat
identity accuracy, hit@k, mAP, or false-match accuracy without such labels.

Every Phase 16 result must answer this migration question:

```text
Would a serious user of Wildbook/IBEIS, Wildlife Insights, MegaDetector, MegaDescriptor, or WildFusion gain an actionable decision they did not already have: accept, review, defer, species-level only, or non-comparable, with evidence and risk attached?
```

If the answer is no, the result is a diagnostic artifact and should not become a
main contribution.

## Data Roles

- CzechLynx: quantitative known-ID validation carrier for wild Eurasian lynx.
- UWIN bobcat: active same-genus urban field-readiness and review-readiness stress context; identity validation only if verified labels or audited pair labels exist.
- UWIN/WildTrax other species: field motivation only, not identity validation.
- Mainland Clouded Leopard: main future patterned-felid conservation motivation only.
- Marbled Cat: secondary future patterned-felid application scenario only.
- Gecko, lizard, turtle, and other non-felid examples: distant future patterned-animal extensions only, not main framing.

## Data Safety Rules

- Do not modify raw data.
- Do not commit raw images.
- Do not commit `data/` or `outputs/`.
- Do not expose `unique_name`, original `lynx_###` paths, latitude, longitude, exact location, cell_code, or trap_id in blinded review files.
- Keep internal mapping files separate from blinded label files.
- Do not publish images or contact sheets until license and display permissions are confirmed.

## Phase Discipline

- Phase 1: data access, rubric, blinded triage, consistency audit, second-review check.
- Phase 2: validation table, pair construction, embedding/similarity validation after Phase 1 consistency is complete.
- Phase 3: risk-coverage policy evaluation after pairwise similarity outputs exist.
- Phase 4: interpretable visual mechanism factors and cross-model similarity validation.
- Phase 5: PF-ERI v1 / ERI-ReID historical scoring prototype, validation, sensitivity analysis, and policy frontier.
- Phase 6: PF-ERI Control reframing, identity-aware validation, simulated open-set CzechLynx stress testing, empirical risk calibration, and policy planning.
- Phase 8: fixed-descriptor PF-ERI retrieval-control testing. Slice 3E-R showed held-out false-candidate burden reduction, but not robust mAP/Re-ID accuracy improvement beyond repeated random same-size controls.
- Phase 9A: direction revision and PF-ERI Evidence Utility Model planning.
- Phase 9B: no-training PF-ERI-aware fixed-descriptor reranking.
- Phase 9C: PF-ERI-weighted lightweight learning feasibility using fixed embeddings only.
- Phase 9D: controlled PF-ERI-weighted metric learning only if Phase 9B/9C pass and explicit approval is given.
- Phase 9E: graph-based reliability visualization and conservation application framing.
- Phase 10-Lite: matched-identity and Phase 10-Lite Plus metric-learning preparation with k=3 primary groups, PK sampling, H3 hybrid selection, and E4 all-train PF-ERI weighting.
- Phase 11: first pair-level PF-ERI reliability-aware metric-learning scaffold with positive-pair weighting and unreliable hard-negative control.
- Phase 12: revised pairwise evidence learning roadmap, RQ1-RQ4 implementation plan, descriptor-evidence conflict formalization, and algorithm readiness gates.
- Phase 13: learned candidate utility and RQ4 training diagnostics. Phase 13D showed plain projection-head training does not pass the raw fixed-embedding reference gate and is diagnostic, not the main next path.
- Phase 14: same-genus wild-to-urban Lynx reliability reframing. CzechLynx remains the known-ID validation carrier; UWIN bobcat becomes the active urban field-readiness stress context with a preferred small human-audited pair set.
- Phase 15: PF-ERI Evidence-Routed Review Layer. CzechLynx known-ID candidate pairs validate query-level descriptor baselines, calibrated ranker signal, repeated risk-coverage behavior, and five-action review routing. Phase 15D action tables are operational routing exports; Phase 15C repeated query splits remain the validation evidence. `accept` means high-priority expert-review candidate, not automatic identity assignment. Phase 15E transfers the CzechLynx-calibrated review-routing policy to bobcat as a wild-to-urban stress test only; bobcat outputs measure review-readiness, ambiguity/defer pressure, species-level-only pressure, non-comparability, and descriptor-evidence conflict, not identity accuracy. Phase 15F packages a small human-audited bobcat pair set to validate review-routing and pair comparability, not bobcat identity accuracy.
- Phase 16: Balanced PF-ERI 2.0 strategy. Phase 16 keeps PF-ERI modeling as the core: pair-level admissible-evidence estimation, descriptor-evidence conflict, calibrated review routing, and risk-controlled evaluation. Phase 16G/H showed that PF-ERI features have pair-level signal but do not currently support a descriptor-only top-k improvement claim. Phase 16I therefore locks the project gap as post-retrieval evidence reliability and review utility, not descriptor replacement. The seven advisor-suggested dimensions are treated as data-governance, sampling, benchmark, and robustness safeguards around that model, not as a replacement main line. Laterality is a sampling/pair-audit rule; background/site leakage is a leakage-pressure diagnostic; strong-model benchmarking is an external comparison requirement. Wild-to-urban remains a transfer-stress axis, not a bobcat identity-accuracy claim. Optional generative augmentation, ecological priors, and captive calibration are deferred until Phase 16A data-governance gates pass.
- Phase 17: review-utility validation, if opened, must evaluate evidence admissibility, descriptor-evidence conflict, false-candidate burden, positive retention, review burden, abstention/risk coverage, and expert-audit agreement. It must not revive descriptor-replacement, automatic identity assignment, or unlabeled Bobcat identity-accuracy claims.
- Do not make final scientific claims before the relevant validation step is complete.

Graph-based reliability network remains a diagnostic visualization layer, not identity clustering.

Downstream ecological sensitivity remains application-value analysis, not population, movement, occupancy, survival, or field-deployment evidence.

UWIN bobcat review-readiness remains field-readiness evidence unless verified individual labels or an audited pair set supports stronger claims.

Mainland Clouded Leopard and Marbled Cat remain future conservation application motivations only unless external known-ID validation is completed.

## Optional Learning Controls

Metric learning and learned projection heads are diagnostic/optional after Phase 14, not the active main path. Do not create model training code unless explicitly requested. If any training phase is attempted, it must compare:

```text
all-images training
random same-size training
quality-only selected training
PF-ERI-selected training
PF-ERI-weighted training
PF-ERI-aware reranking without training
```

The project must not claim broad PF-ERI metric-learning improvement unless PF-ERI-informed training beats random matched and quality-proxy matched controls under held-out evaluation, with query coverage preserved and false-candidate burden not materially worsened. If PF-ERI only improves stability, false-candidate burden, or a specific evidence band, report that narrower result as a mechanism or boundary-condition finding rather than a general learning-improvement claim.

## Required Split Discipline for Reranking and Learning

Do not randomly split individual image rows without leakage checks.

At minimum use:

```text
query-level split
identity-aware split
repeated split
```

If feasible, also test:

```text
held-out identity split
```

Rules:

```text
The same query's candidate set must not appear in both calibration and evaluation.
Weights and thresholds must be tuned only on calibration queries.
Final metrics must be reported only on held-out evaluation queries.
Identity allocation must avoid background, camera, or near-duplicate leakage.
Repeated split results must be reported when possible.
```

## Current Waiting Constraint

The 30-image second-review subset has been prepared. Do not open second-review images or mapping until the planned delayed second-review labeling step. Avoid memory contamination.

## Coding Rules

- Write small, auditable scripts.
- Print clear PASS/FAIL summaries for audit scripts.
- Exit nonzero on audit failure when appropriate.
- Do not create model training code unless explicitly requested.
- Do not create website code unless explicitly requested.
- Prefer deterministic sampling with fixed random seeds.
- Keep generated outputs under `data/interim/` or `outputs/`.
- Do not use notebooks as the only source of logic; important logic should be in scripts.

## Git Rules

- Commit docs and scripts.
- Do not commit `data/`, `outputs/`, raw images, derived image sheets, internal mapping files, or local CSV outputs.
- Use clear commit messages describing the research workflow slice.
