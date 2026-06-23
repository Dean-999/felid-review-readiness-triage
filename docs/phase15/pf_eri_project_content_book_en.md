# PF-ERI Project Content Book (English Version)

## 1. One-Sentence Summary

This project is not about building another animal Re-ID model. It addresses a more practical reliability problem:

```text
After a strong Re-ID system retrieves visually similar candidates, how can we determine whether each candidate pair actually contains admissible individual-identification evidence?
```

The project can be summarized as:

```text
PF-ERI: Patterned-Felid Evidence Reliability and Routing
```

Its goal is to evaluate image-level and pair-level evidence utility after descriptor-based retrieval, then route candidate pairs into `accept`, `review`, `defer`, `species-level only`, or `non-comparable` actions.

## 2. Why I Am Doing This

This project did not start from an abstract machine-learning problem. It started from a practical observation while I was organizing wildlife Re-ID images and comparing candidate pairs.

From the perspective of a high-school researcher, my strongest advantage is not having a complete large-lab system, but having direct access to real wildlife camera-trap images from different contexts and carefully working through image selection, review, and pair comparison. Therefore, the project starts from observable and measurable problems: which images show an animal but do not support individual identification, and which visually similar pairs lack comparable evidence.

When working with CzechLynx, bobcat, UWIN-related urban wildlife data, and rewilding/conservation-oriented animal monitoring contexts, I noticed a repeated problem: many images show an animal, but they do not necessarily provide enough evidence for individual Re-ID.

At the pair level, the problem became even clearer:

- some images show a bobcat or lynx, but the animal is too small, distant, blurred, or occluded for individual identification;
- some images look acceptable individually, but become non-comparable when paired because one is lateral and the other is frontal or rear-facing;
- some candidate pairs have high descriptor similarity, but the flank, body, or pattern evidence does not support a reliable comparison;
- urban/peri-urban bobcat images and wild CzechLynx images differ in background, distance, framing, occlusion, and body pose;
- these differences are not just about general image quality, but about whether a pair can support an identity decision.

Therefore, my question shifted from:

```text
How can I improve Re-ID accuracy?
```

to:

```text
Can the reliability of Re-ID evidence be quantified, calibrated, and routed?
```

This connects directly with my research background:

- **UWIN / urban wildlife** gives me a realistic urban-monitoring perspective;
- **rewilding and conservation monitoring contexts** make me interested in how image evidence changes across managed, urban, and wild settings;
- **Re-ID** provides the technical core;
- **CzechLynx vs bobcat** provides an executable same-genus wild-to-urban comparison.

The goal is not simply to claim that urban data are harder than wild data. The deeper question is:

```text
Do different monitoring environments change the evidence structure behind Re-ID reliability?
```

## 3. Core Logic

The main logic is:

```text
wild vs urban evidence shift
-> image-level evidence utility
-> pair-level comparability
-> descriptor-evidence conflict
-> risk-controlled review routing
```

More specifically:

1. **Environment affects image evidence**
   - Wild CzechLynx and urban/peri-urban bobcat data may differ in camera placement, background, animal distance, occlusion, and pose.
   - These differences change the evidence available for individual identification.

2. **Image evidence constrains pair comparability**
   - Re-ID is not only about whether a single image is clear.
   - A pair is reliable only if the two images share comparable identity evidence, such as flank, body, or pattern regions.

3. **Non-comparable pairs contaminate retrieval and review**
   - Unreliable pairs entering top-k candidate queues increase review burden.
   - Low-evidence images can also introduce noisy training signals.

4. **PF-ERI performs risk routing**
   - It does not automatically assign identity.
   - It decides whether a candidate pair should be accepted for high-priority review, reviewed cautiously, deferred, downgraded to species-level evidence, or marked non-comparable.

PF-ERI and wild vs urban comparison are therefore not two separate projects. Wild vs urban is the real monitoring context that may create evidence shift; PF-ERI is the mathematical and algorithmic framework used to quantify how that shift affects Re-ID reliability.

## 4. Research Questions

### RQ1: Image-Level Evidence Shift

```text
Do wild and urban/peri-urban datasets differ systematically in image-level Re-ID evidence?
```

Key variables:

- animal bounding-box size;
- edge/crop risk;
- side/flank visibility;
- pattern visibility;
- body visibility;
- blur, occlusion, and background complexity;
- high-confidence vs low-evidence stress proportions.

Purpose:

This step does not perform identity recognition. It tests whether raw image evidence distributions differ between monitoring contexts.

### RQ2: Pair-Level Comparability Shift

```text
Even when images are visible, are the paired images actually comparable for individual Re-ID?
```

Key variables:

- weakest-image utility;
- whether both images contain usable flank evidence;
- whether both images contain comparable pattern regions;
- view mismatch;
- body-region mismatch;
- pair admissibility score.

Purpose:

Many Re-ID failures occur not because the animal is invisible, but because the pair lacks shared comparable evidence. This is often under-emphasized when systems only output similarity rankings.

### RQ3: Descriptor-Evidence Conflict

```text
Are there high-similarity candidate pairs with low admissible evidence?
```

Core concept:

```text
high descriptor similarity + low evidence admissibility = conflict pair
```

Purpose:

These pairs are dangerous in real use because they can appear near the top of the candidate list while lacking reliable visual evidence. PF-ERI aims to identify this conflict rather than blindly trusting similarity.

### RQ4: Risk-Controlled Review Routing

```text
Can candidate pairs be routed into evidence-based risk categories to reduce review burden and false-candidate pressure?
```

Routing actions:

```text
accept
review
defer
species-level only
non-comparable
```

Purpose:

The final system should not only output top-k candidates. It should explain how each candidate should be used.

## 5. Data Design

The current design is a 2 x 2 structure:

| Axis | Levels |
|---|---|
| environment | wild CzechLynx vs urban/peri-urban bobcat |
| evidence condition | high-confidence evidence vs low-evidence stress |

Four data blocks:

```text
CzechLynx high-confidence
CzechLynx low-evidence stress
Bobcat high-confidence
Bobcat low-evidence stress
```

Each block targets 3,000 images, for 12,000 images total.

Important boundaries:

- CzechLynx has known individual IDs, so it can validate retrieval risk, positive retention, false-candidate risk, and pair-level routing.
- Bobcat currently lacks verified individual IDs, so it cannot support claims about bobcat identity accuracy, hit@k, or mAP.
- Bobcat is used for urban/peri-urban transfer stress testing, with emphasis on evidence distribution, pair comparability, and review-routing pressure.

## 6. Technical Model

PF-ERI can be decomposed into four model layers.

### 6.1 Image Evidence Utility Model

For each image, estimate evidence utility:

```text
U_i = f(pattern_i, flank_i, body_i, sharpness_i, occlusion_i, box_i, crop_i)
```

Where:

- `pattern_i`: whether visible pattern evidence is present;
- `flank_i`: whether the side/flank region is visible;
- `body_i`: whether enough body region is visible;
- `sharpness_i`: blur level;
- `occlusion_i`: occlusion level;
- `box_i`: detection-box size and position;
- `crop_i`: edge truncation or partial-body crop risk.

This score answers:

```text
Does this image contain usable individual-identification evidence?
```

### 6.2 Pair Comparability Model

For a candidate pair `(i, j)`, estimate comparability:

```text
C_ij = g(min(U_i, U_j), flank_match_ij, pattern_overlap_ij, view_match_ij, body_match_ij)
```

The `min(U_i, U_j)` term is important because a pair is often limited by the weaker image.

This score answers:

```text
Do these two images share comparable identity evidence?
```

### 6.3 Descriptor-Evidence Conflict Model

MegaDescriptor provides visual similarity:

```text
S_ij = cosine(embedding_i, embedding_j)
```

PF-ERI focuses on:

```text
Conflict_ij = high(S_ij) and low(C_ij)
```

This means:

```text
the descriptor thinks the pair is visually similar, but the evidence layer does not support a reliable comparison.
```

These conflict pairs are a major source of false-candidate and review-burden risk.

### 6.4 Risk-Controlled Routing Model

The final output is not identity. It is a review action:

```text
A_ij = h(S_ij, U_i, U_j, C_ij, Conflict_ij, calibrated risk)
```

Five actions:

- `accept`: high-priority candidate for review;
- `review`: usable but requires caution;
- `defer`: insufficient evidence for high-priority identity judgment;
- `species-level only`: supports only species-level evidence;
- `non-comparable`: unsuitable for pair-level Re-ID comparison.

The modeling objective is:

```text
reduce high-risk candidate burden while maintaining useful coverage.
```

## 7. Algorithmic Workflow

The current implementation follows this workflow:

1. **Detector-first image screening**
   - Use MegaDetector or similar detector outputs to remove clear failures.
   - Preserve detection geometry such as box size, location, and confidence.

2. **Evidence feature extraction**
   - Build image-level features from human labels, AI-assisted working labels, detector geometry, and image-quality signals.

3. **MegaDescriptor embedding**
   - Use fixed MegaDescriptor embeddings.
   - The contribution does not depend on training a new descriptor.

4. **Candidate pair generation**
   - Generate positive and negative candidate pairs for known-ID CzechLynx.
   - Generate bobcat candidate pairs for transfer stress testing and manual pair audit.

5. **PF-ERI feature construction**
   - weakest-image utility;
   - pair comparability;
   - descriptor-evidence conflict;
   - quality/evidence hybrid features.

6. **Calibrated ranker**
   - Train calibrated models on CzechLynx known-ID candidate pairs.
   - Validate with repeated held-out query splits.
   - Evaluate ROC-AUC, average precision, risk-coverage, and positive retention, not only top-1 accuracy.

7. **Review-routing policy**
   - Convert candidate pairs into five review actions.
   - Validate risk on CzechLynx.
   - Transfer the calibrated policy to bobcat to measure urban/peri-urban ambiguity pressure.

## 8. How to Interpret the Current Results

The current results support a careful but meaningful conclusion:

```text
PF-ERI is not a new Re-ID model that dramatically improves top-k accuracy.
It is an evidence-routing layer that identifies candidate reliability and review risk after strong descriptor retrieval.
```

On CzechLynx known-ID candidate pairs, PF-ERI/quality/conflict features show stable predictive signal:

```text
descriptor-only ROC-AUC: 0.722
HGB ranker ROC-AUC: 0.851
descriptor-only AP: 0.334
HGB ranker AP: 0.599
```

This means the PF-ERI features are not arbitrary labels; they help predict pair risk.

However, top-k improvement is modest. Therefore, the project should not be framed as:

```text
PF-ERI dramatically improves Re-ID accuracy.
```

The stronger framing is:

```text
PF-ERI turns descriptor retrieval into risk-controlled evidence routing.
```

## 9. How to Explain Wild vs Urban

After transferring the policy to bobcat, the most interesting finding is not simply that urban data are worse. The stronger interpretation is:

```text
urban/peri-urban bobcat pairs shift strongly into the ambiguity/defer band.
```

This means many bobcat candidate pairs are not completely useless. Instead, they fall into an intermediate risk zone:

```text
some evidence is present, but not enough for direct individual-ID judgment.
```

This is more meaningful than saying that urban images have lower quality, because it proposes a more specific mechanism:

```text
environmental image structure may affect Re-ID not only by reducing image quality,
but by increasing pair-level ambiguity and descriptor-evidence conflict.
```

## 10. Contributions

### 10.1 Variable Innovation

Introduce `evidence utility`, `pair comparability`, and `descriptor-evidence conflict` as reliability variables after Re-ID retrieval.

### 10.2 Dimensional Extension

Extend the problem from image quality to:

```text
image-level evidence -> pair-level comparability -> review-routing consequence
```

### 10.3 Boundary Condition

Use wild CzechLynx and urban/peri-urban bobcat to study whether evidence reliability shifts across monitoring contexts.

### 10.4 Mechanism Innovation

Show that descriptor similarity and admissible identity evidence can conflict. High-similarity pairs should not automatically receive the same review priority.

### 10.5 Methodological Contribution

Extend Re-ID output from ranking to action routing:

```text
accept / review / defer / species-level only / non-comparable
```

## 11. Current Limitations

The project must clearly acknowledge these boundaries:

1. Bobcat has no verified individual IDs, so the project cannot report bobcat identity accuracy.
2. Bobcat currently supports transfer stress testing, evidence distribution analysis, and pair audit, not identity validation.
3. The project cannot yet claim that urbanization causes Re-ID failure because explicit urban-gradient covariates are not modeled.
4. AI-assisted image labels require manual sampling and calibration to control label error.
5. PF-ERI does not replace Re-ID; it is a reliability layer after Re-ID retrieval.

These limitations make the project more rigorous because they define which claims are supported and which claims should not be made.

## 12. Final Contribution Statement

The final contribution can be stated as:

```text
I propose and implement an evidence-routed review framework for patterned-felid Re-ID.
It converts candidate pairs after strong descriptor retrieval into interpretable, calibrated,
risk-controlled review actions, validates the model on known-ID CzechLynx, and stress-tests
wild-to-urban evidence shift using urban/peri-urban bobcat data.
```

Shorter version:

```text
PF-ERI does not ask only "who looks most similar?"
It asks "is this comparison supported by admissible identity evidence?"
```

## 13. Spoken Explanation

My project started from a practical issue I noticed while organizing wildlife Re-ID images: many photos show an animal, but they do not support individual identification; many candidate pairs look visually similar, but they do not share comparable flank, pattern, or body evidence. This problem became especially clear when comparing urban/peri-urban bobcat data with wild CzechLynx data, so I designed the project as a wild vs urban evidence-reliability comparison.

My method is not to train a new Re-ID descriptor. Instead, I add PF-ERI after strong retrieval models such as MegaDescriptor. PF-ERI estimates image-level evidence utility, pair-level comparability, and descriptor-evidence conflict, then routes candidate pairs into accept, review, defer, species-level only, or non-comparable. CzechLynx has known identities, so it can validate whether this routing model corresponds to candidate risk. Bobcat currently does not have individual IDs, so it is used as an urban/peri-urban transfer stress test.

The value of this project is that Re-ID should not only answer "which candidate looks most similar?" It should also answer "can this comparison be trusted, and how should it be used?" This matters for real conservation monitoring because low-evidence candidates increase review burden and may contaminate training or downstream analysis.
