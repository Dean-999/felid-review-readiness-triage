# legacy-code18 Gap Research And Modeling Plan

Date: 2026-07-01

## Question

After freezing the strict Bobcat/CzechLynx 3,000 x 2 modeling package, should
the next plan still be a PF-ERI review-routing algorithm, or should it shift
toward training a stronger Re-ID descriptor/model?

## Short Answer

The original plan should remain intact:

```text
strong descriptor / matching platform
-> candidate queue
-> PF-ERI pair-level evidence admissibility
-> descriptor-evidence conflict and risk estimate
-> evidence-routed review action
```

The plan changes only in one important way: the descriptor baseline must be
stronger than a single MegaDescriptor cosine-similarity run. legacy-code18 must treat
WildlifeTools/MegaDescriptor, WildFusion-style calibrated score fusion, local
matching, and modern foundation/ensemble/re-ranking ideas as strong comparator
pressure.

## What Did Not Change

- PF-ERI is not a descriptor replacement.
- PF-ERI is not automatic identity assignment.
- PF-ERI must not claim Bobcat identity accuracy without verified Bobcat
  identities or audited same/different pair labels.
- If descriptor-only top-k remains stronger, the project should report that
  honestly and evaluate review utility instead.

## What Changed

The data state changed:

- `outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/` is now
  frozen.
- It contains 3,000 Bobcat and 3,000 CzechLynx local images.
- All 6,000 files decode and have checksums.

The baseline expectation changed:

- WildlifeTools now exposes a complete feature/similarity/inference workflow.
- MegaDescriptor variants are easy to run through WildlifeTools.
- WildFusion adds calibrated global + local score fusion, so a reviewer may
  expect calibrated fusion baselines alongside a single embedding baseline.
- WildlifeReID-10k and AnimalCLEF-style work show that multispecies Re-ID is
  moving toward larger benchmarks, foundation ensembles, supervised contrastive
  projections, re-ranking, and open/unknown-individual scenarios.

## External Evidence

Key evidence found in this research pass:

- WildlifeTools states that it covers training, feature extraction, similarity
  calculation, image retrieval, and classification, and provides MegaDescriptor
  and WildFusion examples.
- WildlifeTools MegaDescriptor docs use prepared/cropped images, feature
  extraction, cosine similarity, and 1-NN inference as baseline workflow.
- WildlifeTools WildFusion docs describe calibrated fusion of deep scores and
  local matching scores, with MegaDescriptor shortlisting and isotonic
  calibration.
- WildlifeDatasets reports a broad dataset ecosystem and notes CzechLynx was
  added in 2025.
- CrossRef verified the CzechLynx dataset DOI:
  `10.1038/s41597-026-06853-9`.
- CrossRef verified WildlifeReID-10k:
  `10.1109/cvprw67362.2025.00197`.
- GitHub search surfaced WildlifeReID-10k implementations using species-aware
  transformers, ArcFace, Multi-Similarity loss, k-reciprocal re-ranking, and
  foundation-model/SupCon ensembles.

## Forum / Community Trace

Agent Reach status:

- GitHub, generic web, RSS, V2EX, and Bilibili search were available.
- Reddit, Twitter/X, and Xiaohongshu were unavailable because no active backend
  or login state was configured.

Usable community/code traces came mostly from GitHub repositories and official
project documentation. WildMe community pages were attempted but did not return
usable content in this run, so they are not used as evidence here.

## Gap After Research

The gap is still real, but narrower and more specific:

```text
Modern wildlife Re-ID tools are increasingly strong at extracting/fusing
features and ranking or clustering candidates. They still do not, by default,
make the downstream evidential question explicit: is this retrieved comparison
visually admissible, comparable, risky, conflicting, or only species-level?
```

Therefore the project gap should be:

```text
PF-ERI 2.0 is a descriptor-agnostic post-retrieval evidence governance layer
that converts strong candidate queues into calibrated review-readiness,
conflict, abstention, and risk-control decisions.
```

## legacy-code18 Plan

### legacy-code18a: Freeze-Derived Feature Manifest

Input:

```text
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv
```

Output:

- one row per frozen image;
- file hash, species, local path, source status, identity label if available;
- modeling role fields:
  `czechlynx_known_id`, `bobcat_unlabeled_transfer`, `train_eval_eligible`.

### legacy-code18b: Strong Descriptor Baselines

Required baselines:

1. MegaDescriptor-L-384 through WildlifeTools/timm;
2. DINOv2 or another strong foundation descriptor;
3. optional CLIP/SigLIP-style descriptor as broad visual control;
4. shortlist + re-ranking control where feasible.

Do not claim PF-ERI beats descriptors unless evaluation shows that result.

### legacy-code18c: CzechLynx Known-ID Retrieval Benchmark

Use CzechLynx only for identity-accuracy validation.

Required controls:

- identity-disjoint or leakage-aware splits;
- descriptor-only;
- quality-only;
- evidence-only;
- descriptor + quality;
- descriptor + PF-ERI/review-risk;
- optional WildFusion/local-matching control if computationally feasible.

Metrics:

- mAP/MRR/top-k for descriptor baseline reporting;
- false-candidate burden;
- positive retention;
- review budget;
- abstention/risk coverage;
- descriptor-evidence conflict enrichment.

### legacy-code18d: PF-ERI 2.0 Pair Features

Pair features should include:

- descriptor similarity;
- weakest-image quality;
- subject size/completeness;
- side/view comparability;
- blur/occlusion/exposure;
- local-match support if available;
- descriptor-evidence conflict score;
- source/freeze provenance.

### legacy-code18e: Calibrated Review Router

Models should start conservative:

- logistic regression;
- calibrated gradient boosting;
- isotonic calibration;
- no-training diagnostic policy.

Primary endpoints:

- evidence-ready vs not-ready;
- accept/review/defer/non-comparable/species-level-only;
- false-candidate burden at fixed positive retention;
- review burden reduction;
- calibration and abstention behavior.

### legacy-code18f: Bobcat Transfer-Stress Application

Bobcat should receive:

- embeddings;
- image-level evidence scores;
- pair/readiness scores only if paired comparison design is created;
- review-readiness routing;
- no identity-accuracy claim.

If stronger Bobcat claims are desired, build a small audited same/different pair
set first.

## Confidence Assessment

High confidence:

- the frozen data package is ready for feature/embedding extraction;
- the original PF-ERI claim boundary should remain;
- the next phase should start with strong descriptor baselines;
- Bobcat must remain unlabeled transfer-stress unless pair labels are added.

Not 100% confidence:

- PF-ERI will improve top-k identity ranking;
- PF-ERI will beat WildFusion/foundation ensemble baselines;
- Bobcat routing will generalize without some pair-level audit.

Required repair loop:

1. Upgrade baselines before making claims.
2. Report descriptor-only wins transparently.
3. Make review utility, not top-k superiority, the main endpoint.
4. Add Bobcat pair audit only if the project needs stronger transfer evidence.
5. Preserve all freeze checksums and split manifests for reproducibility.

## Sources

- WildlifeTools README:
  https://github.com/WildlifeDatasets/wildlife-tools
- WildlifeTools MegaDescriptor docs:
  https://github.com/WildlifeDatasets/wildlife-tools/blob/main/docs/megadescriptor.md
- WildlifeTools WildFusion docs:
  https://github.com/WildlifeDatasets/wildlife-tools/blob/main/docs/wildfusion.md
- WildlifeDatasets README:
  https://github.com/WildlifeDatasets/wildlife-datasets
- CzechLynx DOI:
  https://doi.org/10.1038/s41597-026-06853-9
- WildlifeReID-10k DOI:
  https://doi.org/10.1109/cvprw67362.2025.00197
- WildFusion arXiv:
  https://arxiv.org/abs/2408.12934
- Wildbook image-to-science source:
  https://arxiv.org/abs/1710.08880
- Species-aware WildlifeReID-10k GitHub trace:
  https://github.com/036priyadharshini/Species-aware-deformable-transformer-framework-for-multi-species-wildlife-re-identification
- AnimalCLEF2026 open-source solution trace:
  https://github.com/fan1344rwere/AnimalCLEF2026-Solution
