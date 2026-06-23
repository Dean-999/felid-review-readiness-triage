# PF-ERI for Same-Genus Wild-to-Urban Lynx Re-ID Evidence Reliability

This project studies whether **PF-ERI** can quantify when same-genus Lynx individual re-identification evidence is reliable. PF-ERI converts visual Re-ID conditions such as pattern visibility, flank/side comparability, blur, occlusion, body visibility, viewpoint compatibility, descriptor support, descriptor-visual conflict, and context shift into reliability signals that can guide candidate filtering, reranking, review-readiness, and risk control.

PF-ERI is not a new Re-ID descriptor and not an automatic identity-assignment system. The current technical goal is to validate pair-level evidence reliability on known-ID wild Eurasian lynx and test whether the calibrated reliability model transfers to urban bobcat monitoring as a same-genus field-readiness stress test.

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
- Data foundation: Phase 14 built the current 2x2 evidence design with four
  working-final evidence sets: CzechLynx high-confidence, CzechLynx low-evidence
  stress, bobcat high-confidence, and bobcat low-evidence stress. Fixed
  MegaDescriptor embeddings, pair comparability tables, descriptor-evidence
  conflict tables, image-level statistical analysis, and initial
  risk-controlled review-policy outputs are available locally under
  `outputs/phase14/`.
- Current model evidence: Phase 15 completed the evidence-routed review layer.
  Phase 15C repeated query-split validation showed model-level signal across 20
  held-out CzechLynx query splits: HGB mean ROC-AUC 0.851 and AP 0.599 versus
  descriptor-only ROC-AUC 0.722 and AP 0.334. Top-k queue gains are modest, so
  the strongest current claim is PF-ERI as a calibrated review/risk layer rather
  than a broad Re-ID accuracy breakthrough.
- Operational routing: Phase 15D exported five-action CzechLynx review-routing
  tables: accept, review, defer, species-level-only, and non-comparable.
  `accept` means high-priority expert-review candidate, not automatic identity
  assignment.
- Transfer stress: Phase 15E applied the CzechLynx-calibrated policy to
  urban/peri-urban bobcat candidate pairs. Bobcat identity labels are
  unavailable, so this is a review-readiness and ambiguity-pressure stress test,
  not bobcat identity-accuracy validation.
- Human audit: Phase 15F prepared a 250-pair bobcat manual-audit package with 50
  pairs from each review action.
- Active next direction: Phase 16 keeps PF-ERI modeling as the core and adds
  data-governance/benchmark safeguards: laterality-aware sampling and pair
  audit, background/site leakage-pressure diagnostics, and strong-model
  benchmark preparation. Generative augmentation, ecological priors, and captive
  imagery remain later extensions.

## Repository Safety

- Raw data are not committed.
- Generated images and contact sheets are not committed.
- `data/` and `outputs/` are ignored and should remain out of Git.
- Public image display is pending license and display-permission confirmation.
- Internal mapping files remain separate from blinded review files.

## Folder Structure

- `docs/CURRENT_PROJECT_MAP.md`: current phase/layer map and active-vs-archive
  distinction.
- `docs/phase16/`: active next strategy layer.
- `docs/phase15/`: current Evidence-Routed Review Layer and calibrated
  review-routing evidence.
- `docs/phase14/`: current data foundation for 2x2 wild/urban x high/low
  evidence sets.
- `docs/phase6/`, `docs/phase8/`, `docs/phase9/`, `docs/phase11/`,
  `docs/phase12/`, `docs/phase13/`: historical evidence and diagnostic
  foundation.
- `docs/archive/`: superseded plans/specs retained for historical rationale.
- `docs/superpowers/plans/`: active executable plan location; currently Phase
  16.
- `docs/structure/`: repository and CSV/artifact maps.
- `scripts/`: active and recent phase scripts; see `scripts/README.md` for the
  current routing map.
- `scripts/legacy/`: old phase scripts, annotation utilities, packaging scripts,
  preview scripts, and historical audits.
- `colab/`: active cloud scripts plus archived metric-learning diagnostics.
- `data/`: local raw/interim/label CSVs and images; not committed. See `data/README.md`.
- `outputs/`: generated reports, audits, tables, packages, and review artifacts; not committed. See `outputs/README.md`.

## Claim Status

The current repository supports a method-development claim for **PF-ERI as a same-genus Lynx pair-level evidence reliability model under test**. It may discuss CzechLynx as known-ID validation and UWIN bobcat as urban field-readiness stress testing. It must not present PF-ERI as identity recognition, population estimation, urbanization causality, deployment accuracy, proven Re-ID learning improvement, general animal Re-ID validation, a universal threshold, a new descriptor, or a hybrid-score safety guarantee.
