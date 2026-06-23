# Phase 15C Targeted Method Literature Note

This is a targeted method note, not a full systematic literature review. Its purpose is to position Phase 15C against the strongest relevant wildlife Re-ID and camera-trap AI workflows, and to clarify why PF-ERI should be evaluated as an evidence-routed review layer rather than as a replacement descriptor.

## Method Position

The strongest existing workflow for our problem is not a weak descriptor baseline. A serious user can already combine:

- camera-trap detection/filtering such as MegaDetector-style animal localization;
- strong animal Re-ID descriptors such as MegaDescriptor or current multispecies Re-ID systems;
- Wildbook/IBEIS-style image management and candidate identity review;
- dataset/tooling ecosystems such as WildlifeDatasets / WildlifeReID-10k that emphasize standardized benchmarks and split discipline.

Therefore PF-ERI must answer a different question:

```text
After a strong descriptor has produced candidates, does this pair contain admissible individual-ID evidence, and what should the reviewer do with it?
```

This is why Phase 15C evaluates candidate reliability, top-k review burden, repeated query splits, subgroup behavior, risk-coverage curves, and feature contribution.

## What Prior Work Already Covers

### Strong Detection And Camera-Trap Preprocessing

Camera-trap AI pipelines already address animal/blank filtering and cross-region detection/classification problems. MegaDetector-style workflows are useful before Re-ID because they reduce blank images, localize animals, and make large-scale image triage practical.

Implication for PF-ERI:

```text
PF-ERI should not claim novelty as animal detection, blank filtering, or generic image-quality screening.
```

### Strong Wildlife Re-ID Descriptors And Toolkits

Recent wildlife Re-ID work provides strong general descriptors, dataset access tools, baseline comparisons, and split-aware evaluation. MegaDescriptor and WildlifeDatasets make it much easier to run robust animal Re-ID baselines across many species.

Implication for PF-ERI:

```text
PF-ERI must be tested against fixed strong descriptors, not only against weak image-quality baselines.
```

### Platform-Level Identity Workflows

Wildbook/IBEIS-style systems already combine image databases, computer vision, candidate review, and conservation data workflows.

Implication for PF-ERI:

```text
The adoption gap is not "can we produce a candidate list?" but "can we tell reviewers which candidate comparisons are evidentially admissible, risky, non-comparable, or species-level only?"
```

### Risk-Coverage And Reject-Option Learning

Selective prediction formalizes the idea that a model should sometimes abstain when risk is too high. This maps naturally onto Re-ID review routing: accept high-evidence pairs, review uncertain pairs, defer/non-comparable weak pairs, and report coverage-risk tradeoffs instead of forcing every image into an identity decision.

Implication for PF-ERI:

```text
Risk-coverage curves are not decorative. They are the mathematical expression of the review-routing problem.
```

## What Prior Work Does Not Fully Resolve

The remaining gap is not simply "select better photos before Re-ID." The sharper gap is:

```text
Strong wildlife Re-ID workflows can rank visually similar candidates, but they do not always expose whether a candidate pair contains admissible identity evidence under camera-trap failure modes.
```

Important under-addressed subproblems:

- high descriptor similarity can occur when side/flank/pattern evidence is weak or non-comparable;
- generic image quality can be high while individual-ID evidence is poor;
- low-evidence stress cases should not disappear from evaluation because they define review burden and failure risk;
- wild-to-urban transfer changes the evidence distribution before it changes identity accuracy;
- reviewers need decisions with risk attached, not only similarity scores.

## Phase 15C Contribution

Phase 15C contributes a controlled validation scaffold:

1. Use strong fixed MegaDescriptor retrieval as the baseline.
2. Add PF-ERI pair comparability, weakest-image evidence, detector geometry, blur/occlusion, and descriptor-evidence conflict.
3. Train calibrated rankers only on held-out query splits.
4. Evaluate repeated splits, top-k review queues, subgroup behavior, risk-coverage curves, and feature importance.
5. Keep the claim boundary CzechLynx-only for identity validation.

The result supports this narrower but stronger claim:

```text
PF-ERI features provide stable evidence-risk signal beyond descriptor similarity, suitable for candidate review routing and risk-control analysis.
```

It does not yet support:

```text
PF-ERI produces a breakthrough top-k Re-ID accuracy improvement.
```

## Why This Matters

For a heavy user of a strong wildlife Re-ID workflow, the pain point is often not the absence of a candidate list. The pain point is deciding which retrieved candidates are actually comparable enough to trust, which should be reviewed, and which should be rejected or downgraded before contaminating downstream identity decisions.

PF-ERI becomes useful if it can provide:

- an evidence reason for accepting or rejecting a candidate pair;
- a review queue sorted by expected evidence utility, not just similarity;
- a non-comparable/species-level-only route for weak images;
- a risk-coverage frontier for choosing operating points;
- a transfer diagnostic showing why urban bobcat data may require different review pressure than wild CzechLynx.

## Method References To Verify In Full Manuscript

The current note relies on targeted source checks rather than a full PRISMA-style review. Candidate source anchors for the final manuscript include:

- Beery, Morris, and Yang, "Efficient Pipeline for Camera Trap Image Review" for MegaDetector-style camera-trap preprocessing.
- Berger-Wolf et al., "Wildbook: Crowdsourcing, computer vision, and data science for conservation" for platform-level wildlife identity workflows.
- Cermak, Picek, Adam, and Papafitsoros, "WildlifeDatasets: An open-source toolkit for animal re-identification" for toolkits, MegaDescriptor, and benchmark discipline.
- Adam et al., "WildlifeReID-10k" for large-scale wildlife Re-ID benchmark design and similarity-aware split concerns.
- Geifman and El-Yaniv, "Selective Classification for Deep Neural Networks" and "SelectiveNet" for reject-option/risk-coverage framing.

These references should be citation-verified again before thesis or manuscript submission.
