# PF-ERI for Same-Genus Wild-to-Urban Lynx Re-ID Evidence Reliability

This project studies whether **PF-ERI** can quantify when same-genus Lynx individual re-identification evidence is reliable. PF-ERI converts visual Re-ID conditions such as pattern visibility, flank/side comparability, blur, occlusion, body visibility, viewpoint compatibility, descriptor support, descriptor-visual conflict, and context shift into reliability signals that can guide candidate filtering, reranking, review-readiness, and risk control.

PF-ERI is not a new Re-ID descriptor and not an automatic identity-assignment system. It is a post-retrieval evidence reliability and review-routing layer around strong descriptor or matching systems. The current technical goal is to validate pair-level evidence reliability on known-ID wild Eurasian lynx and test whether the calibrated reliability model transfers to urban bobcat monitoring as a same-genus field-readiness stress test.

PF-ERI has four evidence levels:

1. image-level evidence utility: whether an image contains usable patterned-felid identity evidence;
2. pair-level evidence admissibility: whether a query-gallery comparison is visually comparable enough for descriptor similarity to be trusted;
3. descriptor-evidence conflict: whether high descriptor similarity is contradicted by weak visual comparability or failure-mode evidence;
4. candidate/review utility: how image pairs should be selected, reranked, accepted, reviewed, deferred, or downgraded to species-level evidence.

The wild-to-urban comparison is organized as an evidence-risk propagation chain:

```text
image-level evidence shift -> pair-level comparability shift -> retrieval/review contamination
```

Image-level analysis asks what changes in single-image evidence. Pair-level analysis asks how those changes enter Re-ID candidate comparisons. Retrieval/review analysis asks why the shift matters for false-candidate burden, review load, defer decisions, and species-level-only outcomes. This makes pair comparison a core mechanism layer of the urban/wild project rather than a separate Re-ID experiment.

## Core Boundary

This project does not identify individual animals. It tests whether imperfect Lynx evidence can be used more intelligently in controlled Re-ID retrieval, review-readiness, and cross-context stress testing.

It does not claim a new Re-ID model, population estimation method, field-deployment identity system, general animal Re-ID validation, urbanization causality, or universal threshold across felid species.

## Core Research Direction

This project reframes same-genus Lynx Re-ID as a reliability-aware pairwise evidence problem:

```text
Given two camera-trap images and fixed descriptor evidence, does the pair contain comparable Lynx identity evidence, and should it be trusted for retrieval, reranking, review, or species-level-only use?
```

The current evidence is not sufficient to claim that PF-ERI improves metric learning. Phase 13D showed that plain projection-head training can damage strong fixed descriptor geometry. The revised direction therefore uses metric learning as a diagnostic/optional path and separates the main research questions:

1. **Wild known-ID validation**: can PF-ERI predict unreliable candidate edges in known-ID wild Eurasian lynx Re-ID?
2. **Descriptor-evidence conflict**: do high-similarity but low-admissibility pairs explain false or uncertain candidate matches better than descriptor similarity or image quality alone?
3. **Same-genus urban stress**: does UWIN bobcat monitoring show a shifted evidence-risk distribution relative to wild CzechLynx?
4. **Urban review-readiness**: in a small human-audited UWIN bobcat pair set, can PF-ERI identify pairs that should be accepted, reviewed, deferred, or downgraded to species-level evidence?
5. **Optional urban identity validation**: if sufficient UWIN bobcat identity labels become available, can PF-ERI-calibrated risk policies reduce false-candidate burden in urban bobcat Re-ID?

Without verified urban bobcat identities, urban pair analysis is interpreted as pair-comparability and contamination-pressure stress testing, not true false-match validation. CzechLynx remains the known-ID dataset for false-candidate and positive-retention claims.

Success does not require every layer to improve every Re-ID metric. A valid contribution may show that PF-ERI explains an error mechanism, improves risk control, reduces false-candidate burden, predicts human review judgements, or identifies when urban bobcat data should remain species-level only.

The active next target is **PF-ERI Evidence-Routed Review Layer**. This is a
review-risk module that sits after strong descriptor retrieval and before expert
review. It asks whether a candidate pair should be accepted, reviewed, deferred,
downgraded to species-level only, or marked non-comparable. This is the missing
decision layer between "these images look similar" and "this comparison has
admissible individual Re-ID evidence."

The locked claim direction is therefore not to beat descriptor-only top-k
ranking as the main claim. Descriptor-only remains a required strong baseline.
PF-ERI's primary endpoints are evidence admissibility, descriptor-evidence
conflict, false-candidate burden, positive retention, review burden,
abstention/risk coverage, and human-audit agreement.

## Core Outputs

- image-level PF-ERI evidence utility scores from observed visual factors.
- pair-level admissibility scores combining weakest-image evidence, side/flank comparability, pattern evidence, blur, occlusion, body visibility, and viewpoint compatibility.
- descriptor-evidence conflict scores identifying high descriptor similarity under weak visual comparability.
- candidate utility / reranking scores for fixed-descriptor candidate lists under risk-coverage constraints.
- UWIN bobcat same-genus evidence distribution shift and review-readiness stress-test tables.
- small human-audited UWIN bobcat pair labels if feasible.
- reliability-aware metric-learning designs as diagnostic/optional work, not the main current endpoint.
- risk-coverage, random-control, Pareto, and downstream sensitivity outputs for bounded validation.
- graph-based reliability network diagnostics and downstream contamination sensitivity as supporting interpretation layers, not the primary algorithmic endpoint.
- evidence-routed review decisions for candidate pairs: accept, review, defer, species-level only, or non-comparable.

## Data Roles

- CzechLynx: quantitative known-ID validation carrier for wild Eurasian lynx.
- UWIN bobcat: active same-genus urban field-readiness and review-readiness stress context; identity validation only if verified individual labels or audited pair labels exist.
- UWIN/WildTrax other species: field motivation only, not identity validation.
- Mainland Clouded Leopard and Marbled Cat: future patterned-felid motivation only, not current validation.
- Non-felid patterned taxa: distant future extensions only, not the main validated scope.

## Current Completed Status

- 200-image CzechLynx blinded pilot triage completed.
- Final triage consistency audit passed.
- 30-image second-review subset prepared and blinding audit passed.
- Phase 4A frozen visual mechanism annotations completed for 500 CzechLynx review images.
- Phase 4B pair-level mechanism table completed for 3,000 known-ID validation pairs.
- Phase 4C similarity table completed with fixed ResNet50 and MegaDescriptor signals.
- Phase 4D-4I mechanism, policy, and uncertainty outputs completed.

## Current Pending Status

- Historical foundation: Phase 5/6/8/9/11/12/13 are preserved as evidence
  history and diagnostic reasoning. They explain why the project moved away from
  generic quality filtering and broad metric-learning claims.
- Data foundation: the wild-urban evidence foundation built the current 2x2 evidence design with four
  working-final evidence sets: CzechLynx high-confidence, CzechLynx low-evidence
  stress, bobcat high-confidence, and bobcat low-evidence stress. Fixed
  MegaDescriptor embeddings, pair comparability tables, descriptor-evidence
  conflict tables, image-level statistical analysis, and initial
  risk-controlled review-policy outputs are available locally under
  `outputs/data-foundation/wild-urban-evidence-foundation/`.
- Current model evidence: the evidence-routed review layer is complete.
  Repeated query-split validation showed model-level signal across 20
  held-out CzechLynx query splits: HGB mean ROC-AUC 0.851 and AP 0.599 versus
  descriptor-only ROC-AUC 0.722 and AP 0.334. Top-k queue gains are modest, so
  the strongest current claim is PF-ERI as a calibrated review/risk layer rather
  than a broad Re-ID accuracy breakthrough.
- Safeguards update: the real CzechLynx pair table and leakage-excluded calibrated
  router validation found pair-level signal but did not clear the conservative
  descriptor-only top-k improvement gate. The claim lock defines the project gap as
  post-retrieval evidence reliability and review utility, not descriptor
  replacement or ranking-superiority.
- Operational routing: the all-data action export provides five-action CzechLynx review-routing
  tables: accept, review, defer, species-level-only, and non-comparable.
  `accept` means high-priority expert-review candidate, not automatic identity
  assignment.
- Transfer stress: the transfer-stress analysis applied the CzechLynx-calibrated policy to
  urban/peri-urban bobcat candidate pairs. Bobcat identity labels are
  unavailable, so this is a review-readiness and ambiguity-pressure stress test,
  not bobcat identity-accuracy validation.
- Human audit: the bobcat pair-audit package contains 250 pairs with 50
  pairs from each review action.
- Active next direction: the safeguards layer keeps PF-ERI modeling as the core and adds
  data-governance/benchmark safeguards: laterality-aware sampling and pair
  audit, background/site leakage-pressure diagnostics, and strong-model
  benchmark preparation. Generative augmentation, ecological priors, and captive
  imagery remain later extensions. The next scientific validation should
  prioritize review utility and expert-audit agreement rather than another
  attempt to force descriptor-only ranking improvement.
- Review utility: leakage-excluded CzechLynx validation now reports
  fixed review-budget, fixed positive-retention, abstention/risk-coverage,
  conflict-enrichment, and proxy review-action outputs under
  `outputs/photo-selection/photo-entry-gates/czechlynx-review-utility/`. The result keeps the
  claim boundary intact: descriptor-only remains best on the k=10 ranking-like
  snapshot, while PF-ERI diagnostic review utility reduces false-pair retention
  at the 90% positive-retention endpoint.

## Repository Safety

- Raw data are not committed.
- Generated images and contact sheets are not committed.
- `data/` and `outputs/` are ignored and should remain out of Git.
- Public image display is pending license and display-permission confirmation.
- Internal mapping files remain separate from blinded review files.

## Folder Structure

- `docs/project-governance/`: current rules, structure maps, logs, executable
  plans, and claim-lock documentation.
- `docs/data-foundation/`: data-foundation docs, including the former
  `docs/data-foundation/wild-urban-evidence-foundation` evidence foundation.
- `docs/photo-freeze/`: strict photo-entry and freeze docs, including the
  former `docs/phase17` compatibility path.
- `docs/pair-evidence/`: pair-level evidence research-question and contract
  docs.
- `docs/review-routing/`: evidence-routed review policy docs, including the
  former `docs/phase15` compatibility path.
- `docs/modeling-validation/`: strong-baseline, reviewability, and
  identity-balanced validation docs, including the former `docs/phase18` compatibility path.
- `docs/candidate-reservoirs/`: exploratory source-selection and candidate-pool
  docs, including the former `docs/phase19` compatibility path.
- `docs/archive/`: superseded plans/specs and historical phase rationale.
- `scripts/`: active and recent phase scripts; see `scripts/README.md` for the
  current routing map.
- `scripts/legacy/`: old phase scripts, annotation utilities, packaging scripts,
  preview scripts, and historical audits.
- `colab/`: cloud helpers organized by content area.
- `data/`: local manifests, audits, labels, provenance records, mappings, and
  intermediate CSV/JSON artifacts; not committed. Current image files are not
  stored here. See `data/README.md`.
- `outputs/`: generated reports, audits, tables, packages, and review artifacts
  organized by content area; not committed. See `outputs/README.md`.

Current navigation should use the content-based folders and
`docs/project-governance/structure/content_directory_migration_map.csv`.
Historical phase-number paths and alias-style compatibility directories are not
part of the active structure.

## Claim Status

The current repository supports a method-development claim for **PF-ERI as a same-genus Lynx pair-level evidence reliability model under test**. It may discuss CzechLynx as known-ID validation and UWIN bobcat as urban field-readiness stress testing. It must not present PF-ERI as identity recognition, population estimation, urbanization causality, deployment accuracy, proven Re-ID learning improvement, general animal Re-ID validation, a universal threshold, a new descriptor, or a hybrid-score safety guarantee.
