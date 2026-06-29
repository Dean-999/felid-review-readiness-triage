# Phase16I PF-ERI Gap Rationale

Date: 2026-06-29

This note defines the defensible gap for the current project before any later
"tool 2.0" outreach or implementation. The priority is the project itself:
prove that PF-ERI fills a workflow and evidence-reliability gap around strong
animal Re-ID systems, not that it replaces those systems.

## Positioning Brief

**Identity.** PF-ERI is a pair-level evidence reliability and review-routing
layer for same-genus wild-to-urban Lynx Re-ID.

**Offer.** Given a fixed descriptor-generated candidate queue, PF-ERI estimates
whether a pair contains admissible/comparable identity evidence, identifies
descriptor-evidence conflict, and routes the pair toward review actions.

**Target users.** Wildlife Re-ID researchers and conservation workflows that
already use strong descriptors, candidate retrieval, and expert confirmation,
but need a more explicit reliability layer before relying on ranked candidates.

**Differentiator.** The contribution is descriptor-agnostic evidence governance:
known-ID CzechLynx validation, leakage-aware controls, pair-level comparability,
and cautious Bobcat transfer-stress. It is not a new descriptor and not an
automatic identity-assignment system.

**Scoping consequence.** The right comparison set is not "PF-ERI vs
MegaDescriptor/MiewID as a descriptor." The right comparison is:

```text
descriptor retrieval / matching platform
-> candidate queue
-> PF-ERI evidence admissibility and review routing
-> expert review / downstream ecological use
```

**Strategic tension.** Strong top-k retrieval performance and reliable field
review are related but not identical. A descriptor can produce a plausible
candidate list while the workflow still lacks a calibrated way to ask whether a
specific pair is reviewable, risky, conflicting, or low-evidence.

## Landscape Scope

| Tier | Examples | What they mainly cover | Gap relative to PF-ERI |
| --- | --- | --- | --- |
| Direct workflow comparators | Wildbook / WBIA / IBEIS-style systems | Image management, detection, candidate matching, individual ID workflows | They validate the importance of matching systems, but PF-ERI's claim is a quantitative post-retrieval evidence-admissibility and review-routing layer. |
| Descriptor and model comparators | MegaDescriptor / WildlifeTools, MiewID | Species-agnostic or multispecies embeddings, feature extraction, similarity, retrieval/classification | They are strong upstream candidate generators. PF-ERI should use or benchmark against them, not claim to be one of them. |
| Benchmark/data infrastructure | WildlifeDatasets, WildlifeReID-style benchmarks | Datasets, splits, evaluation metrics, reproducible baselines | They benchmark identification performance; PF-ERI adds pair-level reliability/routing endpoints such as false-candidate burden, positive retention, review burden, and conflict. |
| Adjacent substitutes | Manual review, simple quality filters, ad hoc thresholds | Human judgment or one-dimensional filtering | PF-ERI must prove it is more than image quality filtering by showing pair comparability, descriptor-evidence conflict, leakage controls, and review-action semantics. |

External evidence supports this scope. Wildbook is framed as an image-to-science
system that detects species and identifies individuals from large photo
collections. WildlifeDatasets and WildlifeTools focus on animal Re-ID datasets,
feature extraction, similarity, retrieval, classification, and
MegaDescriptor/WildFusion usage. MiewID is presented as a multispecies
individual-identification embedding model whose inference path extracts
embeddings and returns top-k nearest matches.

## Defensible Gap Claim

The strongest gap is:

```text
Existing wildlife Re-ID systems are strong at generating, ranking, and managing
candidate identities, but the workflow still needs an explicit pair-level layer
that asks whether each retrieved comparison is evidentially admissible,
comparable, risky, or in descriptor-evidence conflict before the candidate is
treated as review-ready.
```

The claim should be stated as a workflow/review-readiness gap, not a pure
model-performance gap. In manuscript language:

```text
We study PF-ERI as a calibrated evidence-reliability layer around strong
descriptor retrieval. The method is evaluated on known-ID CzechLynx pairs and
then used to stress-test same-genus Bobcat review readiness, without claiming
automatic identity assignment or unlabeled Bobcat identity accuracy.
```

## Internal Evidence From Phase16

Phase16G created the first real CzechLynx pair-level bridge:

| Evidence | Result |
| --- | ---: |
| Selected images | 3,000 |
| Descriptor routing rows scanned | 300,000 |
| Pair rows | 32,592 |
| Positive same-ID pairs | 5,815 |
| False different-ID pairs | 26,777 |
| Audit status | PASS |

Phase16H readiness controls passed the design gate:

| Evidence | Result |
| --- | --- |
| Required controls | descriptor-only, quality-only, evidence-only, conflict-penalized, diagnostic no-training, random same-size |
| Training gate | READY_FOR_DESIGN_NOT_TRAINING_CLAIM |
| Unresolved high vulnerabilities | 0 |
| Mitigation added | leakage sensitivity and leakage-excluded training scope |

Phase16H calibrated-router validation found signal but not a ranking-improvement
claim:

| Policy / model | k=10 hit rate | Mean false/query | False retained |
| --- | ---: | ---: | ---: |
| descriptor_only | 0.6149 | 7.6738 | 0.8023 |
| interaction_logistic_router | 0.6072 | 7.6971 | 0.8047 |
| logistic_calibrated_router | 0.6044 | 7.7029 | 0.8053 |
| diagnostic_no_training | 0.5973 | 7.7058 | 0.8056 |
| quality_only | 0.5565 | 7.9533 | 0.8315 |

The calibrated models had discrimination signal:

| Model | ROC-AUC | AP |
| --- | ---: | ---: |
| interaction_logistic_router | 0.7271 | 0.3346 |
| logistic_calibrated_router | 0.7258 | 0.3340 |

Interpretation: the features contain pair-level signal, but the current
leakage-excluded CzechLynx validation does not support saying PF-ERI improves
top-k identity ranking over descriptor-only. This result strengthens the final
claim boundary: PF-ERI is a reliability and routing layer, not a descriptor
replacement.

## 100% Confidence Loop

Absolute certainty is impossible in science, so the practical standard here is
"no obvious unmitigated logical vulnerability." The strategy reaches that
standard only if the claim remains narrow.

| Possible reviewer objection | Risk if unhandled | Required repair |
| --- | --- | --- |
| "This is just a weaker descriptor." | Fatal if we claim ranking superiority. | Never frame PF-ERI as a descriptor. Treat descriptors as upstream candidate generators. |
| "Descriptor-only already beats it." | Fatal for a top-k improvement paper. | Make descriptor-only the baseline and report the no-improvement result transparently. Use review-risk endpoints. |
| "This is just image quality filtering." | Serious. | Keep quality-only as a named control; emphasize pair comparability, conflict, and review-action semantics. |
| "Manual review already exists in Wildbook-style systems." | Serious if the gap is described as "review exists." | State the gap as quantitative pair-level evidence admissibility and calibrated routing before/within review, not the existence of human review. |
| "CzechLynx selected-set bias limits generalization." | Medium. | Label all current results selected-set validation; add full-gallery or reserve-set sensitivity before broad claims. |
| "Background/source leakage could inflate results." | Serious. | Use leakage-excluded grouped splits as default and report leakage sensitivity. This is already implemented in Phase16H. |
| "Laterality is mostly unknown." | Medium. | Do not make laterality a main evidential pillar until metadata/manual audit improves it. |
| "Bobcat has no verified identities." | Fatal for Bobcat identity accuracy. | Use Bobcat only for transfer-stress/review-readiness until verified identity or audited same/different labels exist. |
| "The router has AUC but no operational gain." | Serious for deployment claim. | Next endpoint must be review utility: risk coverage, false-candidate burden, abstention/review burden, and expert-label prediction, not ranking lift. |

After this loop, the high-confidence strategy is:

```text
Claim PF-ERI as a post-retrieval evidence reliability and review-routing layer.
Do not claim descriptor replacement, top-k identity improvement, automatic ID,
or unlabeled Bobcat identity accuracy.
```

## Priority Decision

Priority 1 is the project-internal gap:

1. Freeze the claim boundary in every Phase16/Phase17 document.
2. Convert Phase16H from a ranking-improvement attempt into a review-utility
   validation stage.
3. Define endpoints that a descriptor-only system does not directly answer:
   evidence admissibility, conflict, review action, false-candidate burden,
   positive retention under review budget, risk coverage, and human-audit
   agreement.
4. Add full-gallery or reserve sensitivity so the selected-set limitation cannot
   be used as a major criticism.
5. Keep Bobcat as transfer-stress until identity labels or audited
   same/different pairs exist.

Priority 2, later, is the practical "tool 2.0" path:

1. Package PF-ERI as a module that can sit after MegaDescriptor/MiewID/WBIA
   candidate generation.
2. Use the module to produce review queues, risk labels, and evidence-conflict
   reports.
3. Contact open-source maintainers only after the CzechLynx review-utility
   story is complete and the Bobcat transfer-stress report is honest.

## Next Phase

The next phase should be Phase16I/Phase17A review-utility validation, not another
attempt to beat descriptor-only ranking. A strong design is:

```text
descriptor candidate queue
-> PF-ERI evidence/risk features
-> leakage-excluded grouped validation
-> review-action labels or proxy policy
-> endpoints: false-candidate burden, positive retention, review burden,
   abstention/risk coverage, quality-only and descriptor-only controls
```

This gives a defensible gap story: strong descriptors answer "which candidates
look similar?" PF-ERI answers "which candidate comparisons are evidence-ready
enough for responsible review or downstream use?"

## Reference Sources

- Wildbook: Crowdsourcing, computer vision, and data science for conservation:
  https://arxiv.org/abs/1710.08880
- WildlifeDatasets WACV 2024 paper:
  https://openaccess.thecvf.com/content/WACV2024/html/Cermak_WildlifeDatasets_An_Open-Source_Toolkit_for_Animal_Re-Identification_WACV_2024_paper.html
- WildlifeTools documentation:
  https://wildlifedatasets.github.io/wildlife-tools/
- Multispecies Animal Re-ID Using a Large Community-Curated Dataset / MiewID:
  https://arxiv.org/html/2412.05602v1
