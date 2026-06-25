# Historical Draft: Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images

## Supersession Note

This draft predates the Phase 6 PF-ERI Control redesign, the Phase 9 PF-ERI Evidence Utility Model revision, the Phase 13 metric-learning diagnosis, and the Phase 14 same-genus wild-to-urban reframing. It should be treated as historical project background, not the final project framing.

The current project title is:

**PF-ERI for Same-Genus Wild-to-Urban Lynx Re-ID Evidence Reliability**

The current main contribution being developed is PF-ERI as a same-genus Lynx pair-level evidence reliability model. CzechLynx / Eurasian lynx is the known-ID wild validation carrier; UWIN bobcat is the same-genus urban field-readiness and review-readiness stress context. Metric learning is diagnostic/optional after Phase 13D, not the current main contribution. PF-ERI / `visual_only_eri` remains the primary visual evidence gate. Descriptor support, reciprocal/margin confidence, and disagreement signals are fixed support signals. `hybrid_eri` is secondary prioritization, not a standalone safety score.

Do not cite this draft as the final manuscript until it is rewritten around the Phase 14 same-genus wild-to-urban reliability framing.

Phase 8 post-3E-R update: the current evidence does not support a robust fixed-descriptor Re-ID accuracy-improvement claim. Held-out query-level evaluation showed that PF-ERI-selected policies reduced false-candidate review burden relative to repeated random same-size controls, but did not robustly improve mAP. Phase 13D later showed that the current projection-head training route is diagnostic rather than a positive metric-learning result. No claim that PF-ERI improves metric learning is allowed unless PF-ERI-informed training consistently beats random matched and quality-proxy matched controls under held-out identity splits.

## Draft Status

This is a working paper-style project report draft.

It is intended for mentor review, project planning, and later development into a formal student research report.

Current status:

- Phase 1 manual triage completed.
- Phase 1 delayed second-review consistency check completed.
- Phase 2 fixed-baseline similarity reliability analysis completed.
- Phase 3 risk–coverage policy analysis completed.
- Interpretation remains pilot-level and conservative.

This draft should not be treated as a final paper or final scientific claim.

---

## Abstract

Camera-trap monitoring produces large volumes of wildlife imagery, but not every species-identifiable image is reliable enough for individual-level re-identification review. This issue is especially important for felids, where individual recognition often depends on visible body-side coat patterns, flank markings, limb patterns, and comparable viewpoints.

This project evaluates a pre-Re-ID review-readiness triage workflow for felid camera-trap images. The workflow classifies images into three categories: `review-ready`, `review-limited`, and `unidentifiable`. The project does not identify individual animals directly and does not train a new Re-ID model. Instead, it tests whether a rubric-based image-readiness gate can support more reliable downstream review decisions.

A 200-image blinded CzechLynx pilot was manually triaged, using known-ID CzechLynx data only after triage was finalized. The final 200-image audit passed automated consistency checks. A delayed 30-image intra-reviewer second-review check achieved 80.0% exact triage-label agreement and Cohen’s kappa of 0.700. A fixed generic ResNet-50 ImageNet embedding baseline was then used as a measurement signal for pairwise similarity validation. The pilot produced weak-to-moderate same/different separation overall, with ROC-AUC = 0.618667. Phase 3 risk–coverage analysis showed that strict review-ready-only filtering strongly reduced pairwise false-positive proxy counts but retained only 3% of same-individual pairs, while a balanced filter retained more evidence but reduced proxy risk only weakly.

The current pilot supports review-readiness as a tiered workflow-control signal rather than a single hard filter. `review-ready` images are best interpreted as high-confidence candidates for individual-level review, `review-limited` images as secondary or cautious manual-review cases, and `unidentifiable` images as unsuitable for individual-level Re-ID review. The findings are preliminary and should be interpreted as pilot-level evidence under a fixed generic embedding baseline.

---

## 1. Introduction

### 1.1 Field Problem

Camera traps are widely used in wildlife monitoring because they can collect large amounts of imagery over long time periods and across large landscapes. These images are useful for species detection, behavior observation, occupancy studies, and individual-level monitoring.

However, individual-level Re-ID is more demanding than species-level tagging. A photo may clearly show that an animal is a lynx, bobcat, or another felid, but still fail to show enough reliable individual-level visual evidence for Re-ID review.

Common failure cases include:

- heavy blur;
- night infrared washout;
- low contrast;
- overexposure;
- partial body visibility;
- frontal or rear-only views;
- occlusion by vegetation;
- missing body-side pattern;
- silhouette-only images;
- animals too far from the camera;
- unclear side comparability.

This creates a practical field workflow problem:

> Which images are reliable enough to enter individual-level Re-ID review?

### 1.2 Core Project Idea

This project proposes a review-readiness triage step before individual-level Re-ID review.

The goal is not to identify animals directly. The goal is to evaluate whether camera-trap images are visually reliable enough to be considered for individual-level review.

The project uses three main triage labels:

| Label | Meaning |
|---|---|
| `review-ready` | Image has sufficient visible pattern, body region, viewpoint, and quality for candidate individual-level review. |
| `review-limited` | Image contains some potentially useful evidence but has limitations that make it unsuitable for high-confidence review. |
| `unidentifiable` | Image lacks reliable individual-level evidence and should be excluded from individual-level Re-ID review. |

### 1.3 Research Questions

The project is organized around two research questions.

#### Q1 — Reliability Question

Do `review-ready` images show stronger same/different individual similarity separation than lower-readiness images under a fixed embedding baseline?

#### Q2 — Risk–Coverage Question

After filtering low-readiness images, does pairwise false-positive proxy risk decrease, and how much known matching evidence is lost?

---

## 2. Project Boundaries

This project does not claim to:

- identify true individual animals in field deployment;
- train a new Re-ID model;
- improve state-of-the-art Re-ID performance;
- estimate population size;
- produce real-world false-match rates;
- define universal felid Re-ID thresholds;
- validate WildTrax/UWIN individual IDs;
- validate Mainland Clouded Leopard or Marbled Cat Re-ID in the current study.

Instead, this project evaluates a pre-Re-ID review-readiness workflow using known-ID CzechLynx data as a pilot validation carrier.

---

## 3. Data Roles

### 3.1 CzechLynx

CzechLynx is used as the quantitative known-ID validation carrier.

For this project, CzechLynx provides:

- real camera-trap images;
- working individual IDs;
- metadata;
- image paths;
- known same-individual and different-individual relationships.

Only real CzechLynx images are used in the current primary pilot. Synthetic data are not used for primary validation.

Current pilot design:

| Item | Count |
|---|---:|
| Pilot images | 200 |
| Working individual IDs | 100 |
| Images per ID | 2 |
| Same-individual pairs | 100 |
| Different-individual pairs | 300 |
| Total pair comparisons | 400 |

### 3.2 UWIN / WildTrax

UWIN/WildTrax data are used as field motivation and field-readiness context only.

They are relevant because they reflect real field tagging conditions, including blurry images, partial bodies, repeated animal appearances, and uncertainty in individual-level review. However, they do not currently provide verified individual IDs for strict validation in this project.

### 3.3 Future Patterned-Felid Application

Mainland Clouded Leopard is now the main future patterned-felid conservation motivation. Marbled Cat is treated as a secondary future application scenario only.

The current study does not validate Mainland Clouded Leopard or Marbled Cat individual Re-ID.

---

## 4. Related Work and Motivation

### 4.1 Patterned-Felid Re-Identification

Animal Re-ID uses visual traits to recognize individual animals across images, but the current project is not framed as general animal Re-ID. For patterned felids, visual evidence may include coat patterns, spots, stripes, flank markings, limb patterns, body-side markings, and other stable features.

However, Re-ID is sensitive to image quality and viewpoint. A photo may contain the correct species but lack the visual evidence required for reliable individual matching.

### 4.2 Camera-Trap Image Review

Camera-trap workflows often involve large-scale image review, species tagging, and filtering. Species-level tagging is usually less demanding than individual-level review.

A workflow gap exists between:

1. species-level usable image;
2. individual-level Re-ID-ready image.

This project focuses on that gap.

### 4.3 Need for Review-Readiness Triage

A pre-Re-ID readiness gate may help conservation workflows by:

- reducing unreliable candidate matches;
- separating high-confidence review cases from ambiguous cases;
- preserving useful but limited images for secondary review;
- excluding images that lack individual-level evidence;
- making downstream review more auditable.

---

## 5. Methods

## 5.1 Overview

The project follows a three-phase validation design.

| Phase | Purpose |
|---|---|
| Phase 1 | Define and audit manual review-readiness triage. |
| Phase 2 | Test whether triage groups show measurable similarity reliability differences. |
| Phase 3 | Evaluate risk–coverage trade-offs under filtering policies. |

Workflow:

```text
CzechLynx real images
→ blinded 200-image pilot sample
→ manual review-readiness triage
→ automated consistency audit
→ delayed 30-image second-review check
→ restore known IDs after triage
→ construct same/different pairs
→ extract fixed ResNet-50 embeddings
→ compute pairwise cosine similarities
→ analyze reliability and risk–coverage trade-offs
5.2 Phase 1 — Manual Review-Readiness Triage
5.2.1 Pilot Sampling

A 200-image CzechLynx pilot subset was sampled from 100 working individual IDs, with 2 images per ID.

The triage file used blinded image names and did not expose:

unique_name;
original lynx_### identity path;
raw CzechLynx image path;
latitude;
longitude;
exact location;
trap ID;
cell code.
5.2.2 Triage Labels

Each image was assigned one of three labels:

Label	Definition
review-ready	Strong enough to enter high-confidence individual-level Re-ID review.
review-limited	Some useful evidence exists, but limitations reduce reliability.
unidentifiable	Insufficient individual-level evidence for Re-ID review.
5.2.3 Supporting Fields

The rubric also recorded supporting fields, including:

blur level;
occlusion level;
lighting condition;
night IR artifact;
visible side;
side comparability;
visible region;
pattern visibility;
body fraction visible;
distance to camera;
camera angle;
reviewer confidence;
uncertainty flag;
exclusion reason;
optional notes.

These fields were designed to make the label decision auditable rather than purely subjective.

5.2.4 Automated Consistency Audit

The final 200-image triage CSV passed automated checks for:

required field completeness;
allowed values;
logical consistency;
row count;
label validity.

Final label distribution:

Label	Count
review-ready	34
review-limited	107
unidentifiable	59
5.3 Delayed Second-Review Consistency Check
5.3.1 Purpose

The second-review check tested intra-reviewer consistency.

It asked:

If the same reviewer applies the same rubric again after a delay, do the main triage decisions remain stable?

This is not inter-rater reliability. It is delayed intra-reviewer consistency.

5.3.2 Design

A 30-image second-review subset was created using stratified sampling:

Original Label	Count
review-ready	10
review-limited	10
unidentifiable	10

The second-review images were renamed with neutral filenames to reduce memory and label leakage.

The second-review blinding audit passed.

5.3.3 Results
Metric	Result
Reviewed rows	30
Exact triage_label agreement	24/30 = 0.800
Cohen’s kappa for triage_label	0.700
pattern_visibility agreement	20/30 = 0.667
side_comparability agreement	16/30 = 0.533
exclusion_reason agreement	20/30 = 0.667

Interpretation:

The main triage label showed acceptable pilot-level consistency. Supporting fields were less stable, especially side_comparability, and should be treated as exploratory.

5.4 Phase 2 — Fixed-Baseline Similarity Reliability Analysis
5.4.1 Purpose

Phase 2 tested whether review-readiness categories correspond to measurable pairwise similarity behavior under a fixed embedding baseline.

The analysis asked:

Do same-individual pairs score higher than different-individual pairs, and does this separation vary by review-readiness group?

5.4.2 Pair Construction

After triage was finalized, the blinded labels were joined back to internal working individual IDs.

The pair set contained:

Pair Type	Count
Same-individual pairs	100
Different-individual pairs	300
Total pairs	400
5.4.3 Embedding Baseline

The baseline was:

torchvision ResNet-50 ImageNet1K V2 penultimate embedding

No model training or fine-tuning was performed.

This baseline is generic and not wildlife-specialized. It is used only as a fixed measurement signal.

Embedding extraction results:

Item	Result
Images embedded	200/200
Embedding dimension	2048
Pair similarities computed	400/400
Similarity output audit	PASS
5.4.4 Metrics

The analysis computed:

cosine similarity;
same-individual mean similarity;
different-individual mean similarity;
same-minus-different mean gap;
ROC-AUC;
readiness-group summaries;
threshold proxy summaries.
5.5 Phase 3 — Risk–Coverage Policy Analysis
5.5.1 Purpose

Phase 3 tested how filtering policies affect retained evidence and pairwise false-positive proxy counts.

The analysis asked:

If low-readiness images are filtered out, how much proxy risk is reduced, and how much known same-individual evidence is lost?

5.5.2 Policies
Policy	Definition
No filter	Retain all images and pairs.
Balanced filter	Retain review-ready and review-limited; exclude unidentifiable.
Strict filter	Retain only review-ready.
5.5.3 Caution

False-positive counts in this analysis are pairwise proxy counts, not real-world false-match rates.

The thresholds are pilot-specific and model-specific. They are not universal felid Re-ID thresholds.

6. Results
6.1 Phase 1 Results

The 200-image blinded manual triage was completed and passed the automated consistency audit.

Final label distribution:

Label	Count
review-ready	34
review-limited	107
unidentifiable	59

The delayed second-review consistency check showed:

Metric	Result
Exact triage-label agreement	24/30 = 0.800
Cohen’s kappa	0.700

Interpretation:

The rubric is acceptable for pilot-level progression. However, supporting fields are less stable than the main triage label.

6.2 Phase 2 Results

Overall same/different results:

Pair Type	Mean Cosine Similarity
Different-individual pairs	0.493990
Same-individual pairs	0.579955

Overall same-minus-different mean gap:

0.085966

ROC-AUC:

0.618667

Interpretation:

The fixed generic ResNet-50 baseline produced weak-to-moderate same/different separation.

Selected readiness-group gaps:

Pair Readiness Group	Mean Gap
limited_limited	0.035978
ready_limited	0.068114
ready_ready	0.119379
unidentifiable_unidentifiable	0.133164

The ready_ready group showed a positive signal compared with the overall gap and the limited_limited group. However, the group had sparse pair counts: 3 same-individual pairs and 7 different-individual pairs.

Interpretation:

Q1 receives partial / mixed support. The results suggest that review-readiness captures some reliability-relevant image quality signal, but the current evidence is not strong enough for a final claim.

## 6.2B Wildlife-Specialized Baseline Results

After the generic ResNet-50 baseline, a wildlife-specialized fixed pretrained baseline was added to test whether the weak-to-moderate Phase 2 result was partly caused by the generic ImageNet feature extractor.

The added baseline was:

```text
BVRA/MegaDescriptor-S-224

This model was used only as a fixed embedding baseline. No model training or fine-tuning was performed.

The same 200 CzechLynx pilot images and the same 400 pair comparisons were used.

Baseline Comparison
Baseline	Same Mean	Different Mean	Gap	ROC-AUC
ResNet-50 ImageNet	0.579955	0.493990	0.085966	0.618667
MegaDescriptor-S-224	0.235992	0.118512	0.117479	0.690400

MegaDescriptor-S-224 improved ROC-AUC by 0.071733 and improved the same-minus-different mean gap by 0.031513. The relative gap increase was approximately 36.7%.

Absolute cosine similarity values should not be compared directly across models because embedding spaces have different similarity scales. The meaningful comparisons are AUC, same-minus-different gap, readiness-group behavior, and within-model threshold behavior.

6.3 Phase 3 Results

Policy comparison:

Policy	Retained Images	Retained IDs	Retained Same Pairs	Retained Pair Rate	Mean Gap
No filter	200/200 = 100.0%	100/100 = 100.0%	100/100 = 100.0%	100.0%	0.085966
Balanced filter	141/200 = 70.5%	86/100 = 86.0%	55/100 = 55.0%	53.0%	0.056663
Strict filter	34/200 = 17.0%	31/100 = 31.0%	3/100 = 3.0%	2.5%	0.119379

Threshold proxy summary:

Policy	Threshold	True-Positive Proxy Count	False-Positive Proxy Count
No filter	0.547081	60	140
No filter	0.680093	34	66
No filter	0.770424	22	18
No filter	0.808955	14	6
Balanced filter	0.547081	44	119
Balanced filter	0.680093	27	61
Balanced filter	0.770424	19	17
Balanced filter	0.808955	12	6
Strict filter	0.547081	3	7
Strict filter	0.680093	3	6
Strict filter	0.770424	3	3
Strict filter	0.808955	2	1

Interpretation:

Phase 3 shows a clear risk–coverage trade-off.

The strict filter reduces pairwise false-positive proxy counts most strongly, but it retains only 3% of known same-individual pairs. This makes it too evidence-losing to serve as the only general workflow policy in this pilot.

The balanced filter preserves substantially more coverage, retaining 70.5% of images, 86.0% of identities, and 55.0% of same-individual pairs. However, it only weakly reduces high-threshold false-positive proxy counts.

The best current interpretation is a tiered workflow:

Triage Label	Recommended Role
review-ready	High-confidence candidate Re-ID review
review-limited	Secondary or cautious manual review
unidentifiable	Excluded from individual-level Re-ID review

## 6.3B MegaDescriptor Risk–Coverage Results

Because MegaDescriptor-S-224 uses a different embedding space from ResNet-50, the ResNet-50 thresholds were not reused. Phase 3B used MegaDescriptor-specific quantile thresholds.

| Quantile | Threshold |
|---:|---:|
| 0.50 | 0.116324 |
| 0.75 | 0.194070 |
| 0.90 | 0.348698 |
| 0.95 | 0.459079 |

### Policy Comparison

| Policy | Retained Pairs | Retained Same Pairs | Retained Different Pairs | Same Mean | Different Mean | Gap |
|---|---:|---:|---:|---:|---:|---:|
| `no_filter` | 400 | 100 | 300 | 0.235992 | 0.118512 | 0.117479 |
| `balanced_filter` | 212 | 55 | 157 | 0.257496 | 0.149243 | 0.108253 |
| `strict_filter` | 10 | 3 | 7 | 0.533246 | 0.326113 | 0.207133 |

Compared with ResNet-50, MegaDescriptor improved the separation gap under all three policies:

| Policy | ResNet-50 Gap | MegaDescriptor Gap | Change |
|---|---:|---:|---:|
| `no_filter` | 0.085966 | 0.117479 | +0.031513 |
| `balanced_filter` | 0.056663 | 0.108253 | +0.051590 |
| `strict_filter` | 0.119379 | 0.207133 | +0.087754 |

### Interpretation

Phase 3B strengthens the tiered workflow interpretation.

Strict filtering still reduces pairwise false-positive proxy counts most strongly, but it retains too little known matching evidence to serve as the only general workflow policy. Balanced filtering is more defensible under MegaDescriptor than it was under ResNet-50 because it preserves substantially more evidence while showing clearer mid-threshold proxy-risk reduction.

The best current workflow interpretation remains:

| Triage Label | Recommended Role |
|---|---|
| `review-ready` | High-confidence candidate Re-ID review |
| `review-limited` | Secondary or cautious manual review |
| `unidentifiable` | Excluded from individual-level Re-ID review |

7. Discussion
7.1 Main Finding

The pilot supports review-readiness as a workflow-control signal rather than a single hard filter.

The strongest current finding is not that review-ready images always solve Re-ID reliability. Instead, the results show that filtering policies create measurable trade-offs between retained evidence and pairwise proxy risk.

7.2 Interpretation of Phase 1

Phase 1 showed that the rubric can be applied consistently enough for pilot progression.

The main triage label reached 80% agreement in delayed second-review, but supporting fields were less stable. This suggests that the three-class readiness label is more reliable than some fine-grained image-quality attributes.

7.3 Interpretation of Phase 2

Phase 2 showed weak-to-moderate same/different separation under a generic embedding baseline.

The ready_ready group had a positive signal, but sparse pair counts limit the strength of interpretation. Some lower-readiness groups also showed positive gaps, which may reflect sampling effects, encounter similarity, background similarity, or limitations of the generic baseline.

7.4 Interpretation of Phase 3

Phase 3 showed that strict filtering reduces pairwise false-positive proxy counts but sacrifices most evidence.

Balanced filtering retains more coverage but does not strongly reduce high-threshold proxy risk.

This supports a tiered workflow rather than a simple strict inclusion/exclusion rule.

8. Limitations
The pilot uses only 200 images.
The same-review consistency check uses only 30 images.
The consistency check measures intra-reviewer consistency, not inter-rater reliability.
Supporting fields are less stable than the main triage label.
The embedding baseline is generic ResNet-50 ImageNet, not a wildlife-specialized Re-ID model.
The ready_ready group has sparse pair counts.
The Phase 2 ROC-AUC is weak-to-moderate, not strong.
Pairwise proxy counts are not real-world false-match rates.
Thresholds are pilot-specific and model-specific.
The current study does not validate field deployment readiness.
The current study does not generalize to all felid species.
The current study does not identify individual animals directly.
9. Future Work
9.1 Wildlife-Specialized Embedding Baseline

A future extension should test a wildlife-specialized embedding baseline, such as a MegaDescriptor / WildlifeDatasets-based model.

This would help determine whether the weak-to-moderate Phase 2 separation is due to:

the generic ResNet-50 baseline;
the review-readiness gate itself;
sparse pair counts;
background similarity;
encounter-level effects.
9.2 Larger Pair Sampling

The pilot currently uses 100 same-individual pairs and 300 different-individual pairs. A larger analysis could increase negative sampling and test stability across multiple random seeds.

9.3 Split-Aware Validation

CzechLynx includes geo-aware and time-aware splits. A future analysis could test whether review-readiness behaves differently across spatial or temporal shifts.

9.4 Independent Reviewer

A future study should include a second human reviewer to estimate inter-rater reliability.

9.5 Field Dataset Extension

UWIN/WildTrax images could be used to evaluate field-readiness distributions and failure modes, while still avoiding unverified individual-ID claims.

10. Conclusion

This pilot demonstrates a complete review-readiness validation workflow for felid camera-trap images.

The workflow includes:

blinded manual triage;
automated consistency auditing;
delayed intra-reviewer second-review;
known-ID pair construction;
fixed-baseline embedding similarity analysis;
risk–coverage policy evaluation.

The current results support a conservative conclusion:

Review-readiness is useful as a tiered workflow-control signal for deciding how images should enter individual-level Re-ID review, but it should not be treated as a universal hard filter or as proof of animal identification performance.

The project is now ready for mentor review and further technical extension.

11. References and Source Notes
CzechLynx Paper

Picek, L., Straka, J., Jirik, M. et al. CzechLynx: A Dataset for Individual Identification and Pose Estimation of the Eurasian Lynx. Scientific Data 13, 511 (2026). https://doi.org/10.1038/s41597-026-06853-9

CzechLynx Dataset

Picek, L. et al. CzechLynx Dataset (v1.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.17592004

Dataset Use Note

The Scientific Data article and the Zenodo dataset record have separate licenses. The article is licensed under CC BY-NC-ND 4.0, while the Zenodo dataset record is licensed under CC BY 4.0. The project remains conservative and does not commit raw images, generated image sheets, sensitive metadata, or dataset-derived visual outputs to GitHub.
