# Mentor Progress Update 002

## Project Title

**Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images**

## One-Sentence Project Definition

This project evaluates whether felid camera-trap images are reliable enough to enter individual-level Re-ID review, using a rubric-based review-readiness gate and CzechLynx known-ID data for pilot validation.

## Core Boundary

This project does **not** identify individual animals directly.

It does **not** train a new Re-ID model, claim field deployment readiness, estimate population size, or propose universal felid Re-ID thresholds.

Instead, the project asks whether a pre-Re-ID image-quality and review-readiness workflow can help conservation researchers decide which images are reliable enough for individual-level review.

---

## Current Completed Work

### Phase 1 — Blinded Manual Review-Readiness Triage

A 200-image CzechLynx pilot subset was created from real CzechLynx camera-trap images.

The pilot used:

- 200 real CzechLynx images;
- 100 working individual IDs;
- 2 images per ID;
- blinded image filenames;
- no visible `unique_name`, raw CzechLynx path, latitude, longitude, trap ID, cell code, or exact location in the manual triage file.

Each image was manually labeled as:

- `review-ready`
- `review-limited`
- `unidentifiable`

Final 200-image label distribution:

| Label | Count |
|---|---:|
| `review-ready` | 34 |
| `review-limited` | 107 |
| `unidentifiable` | 59 |

The final 200-image consistency audit passed.

### Phase 1 Second-Review Consistency Check

A delayed 30-image second-review subset was created to test intra-reviewer consistency.

The subset was stratified as:

- 10 originally `review-ready`;
- 10 originally `review-limited`;
- 10 originally `unidentifiable`.

The second-review subset used neutral filenames and remained blinded. The second-review blinding audit passed.

Second-review results:

| Metric | Result |
|---|---:|
| Reviewed rows | 30 |
| Exact `triage_label` agreement | 24/30 = 0.800 |
| Cohen’s kappa for `triage_label` | 0.700 |
| `pattern_visibility` agreement | 20/30 = 0.667 |
| `side_comparability` agreement | 16/30 = 0.533 |
| `exclusion_reason` agreement | 20/30 = 0.667 |

Interpretation:

The main triage label showed acceptable pilot-level intra-reviewer consistency. Supporting fields were less stable, especially `side_comparability`, so supporting-field analyses should remain exploratory.

The second-review result is treated as intra-reviewer consistency evidence, not inter-rater reliability.

---

## Phase 2 — Fixed-Baseline Similarity Reliability Analysis

After Phase 1 was completed, the blinded triage labels were joined back to internal CzechLynx working IDs for known-ID validation.

The Phase 2 validation setup used:

- 200 validation images;
- 100 working individual IDs;
- 100 same-individual pairs;
- 300 fixed-seed sampled different-individual pairs;
- 400 total pairwise comparisons.

A fixed generic embedding baseline was used:

```text
torchvision ResNet-50 ImageNet1K V2 penultimate embedding

No model training or fine-tuning was performed.

Embedding extraction results:

Item	Result
Images embedded	200/200
Embedding dimension	2048
Pair similarities computed	400/400
Similarity output audit	PASS

Overall same/different similarity results:

Pair Type	Mean Cosine Similarity
Different-individual pairs	0.493990
Same-individual pairs	0.579955

Overall same-minus-different mean gap:

0.085966

ROC-AUC under the fixed generic baseline:

0.618667

Interpretation:

The fixed generic ResNet-50 baseline produced weak-to-moderate same/different separation. This is useful as a measurement signal, but it should not be interpreted as animal identification performance.

Readiness-Group Results

Selected readiness-group gaps:

Pair Readiness Group	Mean Gap
limited_limited	0.035978
ready_limited	0.068114
ready_ready	0.119379
unidentifiable_unidentifiable	0.133164

The ready_ready group showed a positive signal compared with the overall gap and the limited_limited group. However, ready_ready had sparse pair counts:

3 same-individual pairs;
7 different-individual pairs.

The result should therefore be interpreted as preliminary, not as a final proof that review-ready images are always more reliable.

Phase 3 — Risk–Coverage Policy Analysis

Phase 3 evaluated how filtering low-readiness images changes pairwise false-positive proxy risk and retained matching evidence.

Three policies were compared:

No filter — all images and pairs are retained.
Balanced filter — review-ready and review-limited images are retained; unidentifiable images are excluded.
Strict filter — only review-ready images are retained.
Policy Comparison
Policy	Retained Images	Retained IDs	Retained Same Pairs	Retained Pair Rate	Mean Gap
No filter	200/200 = 100.0%	100/100 = 100.0%	100/100 = 100.0%	100.0%	0.085966
Balanced filter	141/200 = 70.5%	86/100 = 86.0%	55/100 = 55.0%	53.0%	0.056663
Strict filter	34/200 = 17.0%	31/100 = 31.0%	3/100 = 3.0%	2.5%	0.119379
Threshold Proxy Summary

At selected pilot-specific thresholds:

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

The strict filter reduces pairwise false-positive proxy counts most strongly, but it retains only 3% of same-individual pairs. This makes it too evidence-losing to serve as the only general workflow policy in this pilot.

The balanced filter preserves much more image, identity, and same-pair coverage, but it only weakly reduces high-threshold false-positive proxy counts.

The most defensible interpretation is a tiered review workflow:

Triage Label	Recommended Workflow Role
review-ready	High-confidence candidate Re-ID review
review-limited	Secondary or cautious manual review
unidentifiable	Excluded from individual-level Re-ID review
Main Current Interpretation

The current pilot supports the idea that review-readiness can be used as a workflow-control signal.

However, the results should be framed conservatively:

Phase 1 supports that the manual rubric can be applied with acceptable pilot-level intra-reviewer consistency.
Phase 2 provides weak-to-moderate evidence that known-ID similarity behavior is measurable under a fixed generic baseline.
Phase 3 shows that filtering creates a real risk–coverage trade-off.
The best current workflow interpretation is tiered review, not a single hard strict filter.

The current results do not prove universal review-ready superiority, true individual identification, or deployment-ready performance.

Current Safeguards

The project currently follows these safeguards:

Raw images are not committed to GitHub.
Generated image sheets and figures are not committed.
data/ and outputs/ remain local and ignored.
Internal mappings remain separate from blinded label files.
Sensitive location fields are not exposed in public materials.
CzechLynx article license and dataset license are separated.
Public image use remains conservative even though the Zenodo dataset is licensed under CC BY 4.0.
Current Limitations
The pilot uses only 200 CzechLynx images.
The second-review subset has only 30 images.
The consistency check measures intra-reviewer consistency, not inter-rater reliability.
Supporting fields were less stable than the main triage label.
The embedding baseline is generic ResNet-50 ImageNet, not wildlife-specialized.
The ready_ready group has sparse pair counts.
Phase 2 AUC is weak-to-moderate, not strong.
Phase 3 thresholds are pilot-specific and model-specific.
Pairwise false-positive proxy counts are not real-world false-match rates.
The results should not yet be generalized to all felids or all camera-trap datasets.
Planned Next Steps
Immediate Next Step

Prepare a mentor-facing technical report draft that combines:

project motivation;
data roles;
triage rubric;
Phase 1 consistency results;
Phase 2 reliability analysis;
Phase 3 risk–coverage interpretation;
limitations and future work.
Possible Technical Extension

A future extension could add a wildlife-specialized embedding baseline, such as a MegaDescriptor / WildlifeDatasets-based model, to compare against the current generic ResNet-50 baseline.

This would help test whether the weak-to-moderate Phase 2 separation is caused by:

the review-readiness gate itself;
the generic baseline being too weak;
sparse pair counts;
background or encounter-level similarity effects.
Possible Study Extension

A larger follow-up could expand:

number of pilot images;
number of different-individual pairs;
split-aware validation using CzechLynx geo-aware and time-aware splits;
UWIN/WildTrax field-readiness distribution analysis;
independent second-review by another reviewer.
Questions for Mentor
Is the review-readiness framing scientifically defensible as a pre-Re-ID conservation workflow?
Are the three triage labels appropriate, or should review-limited be split into more specific subcategories?
Is the intra-reviewer consistency result strong enough for a pilot study?
How should the sparse ready_ready pair count be handled in interpretation?
Would a wildlife-specialized embedding baseline be necessary before writing this as a paper-style project?
Is the tiered workflow interpretation more defensible than a strict filter recommendation?
What public-display cautions should be followed when using CzechLynx example images in a poster or mentor presentation?
Should the next extension prioritize a stronger baseline, larger pair sampling, or independent review by a second annotator?
Current Request for Guidance

I would like feedback on whether this pilot is scientifically useful as a review-readiness validation workflow.

Specifically, I would like guidance on:

whether the project framing is clear;
whether the methodology is sufficiently rigorous for a student research project;
whether the current results support moving toward a paper-style draft;
which technical extension would most improve the project next.