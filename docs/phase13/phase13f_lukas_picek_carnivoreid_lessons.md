# Phase 13F Lessons from Lukas Picek / CarnivoreID-Adjacent Work

Date: 2026-06-18

## Search Boundary

The user mentioned a `CarnivoreID` project by Lukas Picek. Public searches for exact strings such as:

```text
CarnivoreID Lukas Picek
CarnivoreID MegaDescriptor
Carnivore ID animal re-identification
```

did not return a clearly indexed public project page, paper, or repository.

Interpretation:

```text
CarnivoreID may be an internal, unpublished, renamed, or not-yet-indexed project.
```

The public, citable work most relevant to CarnivoreID and this project is instead:

- WildlifeDatasets / MegaDescriptor
- WildlifeReID-10k
- WildFusion
- Animal Identification with Independent Foreground and Background Modeling
- CzechLynx
- Centering Ecological Goals in Automated Identification of Individual Animals

## Public Project / Paper Map

### 1. WildlifeDatasets / MegaDescriptor

Public source:

- `WildlifeDatasets: An open-source toolkit for animal re-identification`
- GitHub: `WildlifeDatasets/wildlife-datasets`
- URL: https://arxiv.org/abs/2311.09118

Core contribution:

```text
Standardized wildlife Re-ID datasets, dataset loading, preprocessing, evaluation, fine-tuning, and a general foundation descriptor: MegaDescriptor.
```

Important details:

- The GitHub project describes a pipeline for wildlife Re-ID including dataset zoo, trained models, classification in labelled databases, and clustering in unlabelled databases.
- The package reports 53 publicly available wildlife Re-ID datasets and 3 metadatasets.
- It is used for training MegaDescriptor and WildFusion.
- It emphasizes practical usability for ecologists and ML researchers.

PF-ERI lesson:

```text
Do not frame PF-ERI as a replacement for MegaDescriptor or WildlifeDatasets.
Frame PF-ERI as an evidence-admissibility and risk-control layer that can sit on top of these strong descriptors and dataset tools.
```

This strengthens the project boundary:

```text
PF-ERI is not a new descriptor.
PF-ERI is a reliability layer for deciding which image/pair/candidate evidence is admissible for retrieval, reranking, review, or training.
```

### 2. WildlifeReID-10k

Public source:

- `WildlifeReID-10k: Wildlife re-identification dataset with 10k individual animals`
- URL: https://arxiv.org/abs/2406.09211

Core contribution:

```text
A large multi-species benchmark with similarity-aware and time-aware evaluation protocols.
```

Key lesson:

The paper explicitly argues that standard random splits are inadequate because visually similar images can leak between train and test. It introduces similarity-aware splits to reduce this problem.

PF-ERI lesson:

```text
Our Phase 13D identity-overlap finding is not a small housekeeping issue. It directly matches a known methodological concern in Lukas Picek's Re-ID line: random or weak splits can overestimate performance.
```

Immediate project consequence:

```text
Phase 13E must build identity-disjoint and ideally similarity-aware splits before making any strong RQ4 training claim.
```

PF-ERI can add a new angle:

```text
Similarity-aware split controls descriptor leakage.
PF-ERI controls evidence admissibility and pair comparability.
```

The combination is stronger than either alone.

### 3. WildFusion

Public source:

- `WildFusion: Individual Animal Identification with Calibrated Similarity Fusion`
- URL: https://arxiv.org/abs/2408.12934

Core contribution:

```text
Fuse global deep descriptor scores, such as MegaDescriptor or DINOv2, with local matching similarities, such as LoFTR and LightGlue, using calibrated similarity fusion.
```

Important result:

- Local similarity alone was reported as strong in zero-shot settings.
- Dataset-specific calibration improved performance.
- Combined local and global similarity outperformed the state of the art in the reported benchmark setting.

PF-ERI lesson:

This is extremely relevant. It suggests the next strongest version of PF-ERI should not only train a projection head.

Better direction:

```text
PF-ERI should become a calibrated evidence-gating and fusion-control model:

global descriptor similarity
+ local pattern matching similarity
+ PF-ERI admissibility
+ descriptor-evidence conflict
+ review/risk threshold
```

Potential upgrade:

```text
PF-ERI-WildFusion style reranking
```

where PF-ERI controls whether a pair is eligible for local matching, how much local-vs-global similarity is trusted, and whether the candidate should be deferred to review.

This may be stronger than RQ4 projection-head training.

### 4. Independent Foreground and Background Modeling

Public source:

- `Animal Identification with Independent Foreground and Background Modeling`
- URL: https://arxiv.org/abs/2408.12930

Core contribution:

```text
Separate foreground and background, model them independently, then combine calibrated predictions.
```

The paper reports gains using automatic separation, per-instance temperature scaling, and spatial/temporal background models.

PF-ERI lesson:

This gives a direct missing component:

```text
PF-ERI should distinguish identity evidence from context evidence.
```

For patterned-felid Re-ID:

- foreground/pattern evidence can support identity;
- background/trap context can support temporal/spatial plausibility but may also create shortcut bias;
- background drift can break naive context use;
- evidence admissibility should identify when context is helpful, harmful, or irrelevant.

Possible new PF-ERI variables:

```text
foreground_pattern_visibility
foreground_segmentation_confidence
background_shortcut_risk
same_camera_context_support
background_drift_risk
foreground_background_conflict
```

This is a stronger and more explainable extension than simply increasing projection-head capacity.

### 5. CzechLynx

Public source:

- `CzechLynx: A Dataset for Individual Identification and Pose Estimation of the Eurasian Lynx`
- URL: https://arxiv.org/abs/2506.04931

Core contribution:

```text
Large-scale Eurasian lynx benchmark with identity labels, segmentation masks, pose skeletons, synthetic images, and geo/time-aware evaluation protocols.
```

Important details:

- The current arXiv abstract reports 39,760 camera-trap images, 319 individuals, segmentation masks, identity labels, and 20-point skeletons.
- It defines geo-aware, time-aware open-set, and time-aware closed-set evaluation protocols.

PF-ERI lesson:

This creates both opportunity and pressure.

Pressure:

```text
If CzechLynx already provides segmentation, pose, and realistic splits, our project cannot claim novelty just by using CzechLynx or running MegaDescriptor.
```

Opportunity:

```text
PF-ERI can use pose, segmentation, side/flank comparability, and pattern visibility to create an evidence-admissibility model that CzechLynx-style Re-ID benchmarks do not directly solve.
```

Practical next step:

If available in our local data, incorporate:

```text
pose/side comparability
segmentation quality
visible flank area
pattern-bearing body-region coverage
occlusion ratio
```

These are likely stronger than generic image-quality variables.

### 6. Centering Ecological Goals

Public source:

- `Centering Ecological Goals in Automated Identification of Individual Animals`
- URL: https://arxiv.org/abs/2604.20626

Core contribution:

```text
Automated ID should be evaluated by ecological usefulness, transparency, and mistake consequences, not only algorithmic accuracy.
```

PF-ERI lesson:

This paper strongly supports our project philosophy.

PF-ERI should be framed around:

```text
which mistakes matter
which uncertain candidates should be reviewed
which evidence is admissible
how false candidates contaminate downstream use
how risk/coverage changes under practical review budgets
```

This validates our move away from:

```text
maximize top-1 only
```

toward:

```text
risk-controlled retrieval, evidence utility, review burden, and downstream contamination sensitivity.
```

## New Findings for Our Project

### Finding 1: Our current RQ4 failure is methodologically expected

Picek-adjacent work repeatedly shows strong descriptors, calibrated fusion, realistic splits, and ecological protocols matter. A small unconstrained projection head trained on non-identity-disjoint splits is not a sufficiently strong or well-grounded RQ4 test.

Implication:

```text
Phase 13D failure is not a reason to abandon RQ4.
It is evidence that RQ4 must be upgraded to match the methodological standard of this field.
```

### Finding 2: Similarity-aware split should be added, not only identity-disjoint split

Identity-disjoint split solves one problem. WildlifeReID-10k highlights another:

```text
visually similar image leakage
```

PF-ERI should add:

```text
identity-disjoint split
similarity-aware stress split
time/geo-aware split if metadata allow
```

### Finding 3: WildFusion suggests a stronger PF-ERI route than projection-head training

Rather than only learning an embedding correction, PF-ERI can control calibrated score fusion:

```text
MegaDescriptor score
local matcher score
PF-ERI admissibility
descriptor-evidence conflict
review deferral
```

This aligns with patterned-felid Re-ID because pattern evidence is often local and side-dependent.

### Finding 4: Foreground/background modeling gives PF-ERI a concrete mechanism layer

PF-ERI can become stronger if it explicitly separates:

```text
foreground identity evidence
background/context support
background shortcut risk
foreground-background conflict
```

This creates a clearer mechanism innovation than generic image quality filtering.

### Finding 5: Ecological-goal framing protects the project from weak top-1 gains

If PF-ERI improves:

- false candidate burden;
- review utility;
- evidence transparency;
- risk/coverage;
- downstream contamination sensitivity;

then the contribution can still be meaningful even without large raw top-1 gains.

But this must be demonstrated with realistic protocols and matched controls.

## Revised Phase 13E Recommendation

Do not jump directly to full metric learning.

Phase 13E should implement:

1. Strict identity-disjoint split audit and generator.
2. Similarity-aware stress split using raw descriptor distance.
3. Residual reliability head only after split protocol is fixed.
4. Descriptor-specific margin calibration.
5. PF-ERI + local matching fusion prototype, inspired by WildFusion.
6. Foreground/context evidence variables if segmentation or pose data are available.

Recommended order:

```text
13E-1: identity-disjoint + similarity-aware split
13E-2: PF-ERI risk/reranking under those splits
13E-3: residual reliability head with geometry preservation
13E-4: WildFusion-style calibrated fusion layer
13E-5: foreground/background evidence extension
```

## Claim Boundary After This Review

Strong claim to avoid:

```text
PF-ERI is a better Re-ID model than CarnivoreID/MegaDescriptor/WildFusion.
```

Defensible claim to pursue:

```text
PF-ERI is an evidence-admissibility and risk-control layer for patterned-felid Re-ID that can complement strong descriptors and calibrated fusion systems by deciding when image pairs contain usable identity evidence, when descriptor similarity conflicts with visual evidence, and when candidates should be trusted, downweighted, or reviewed.
```

This is a more realistic and stronger contribution.
