# Phase 3B MegaDescriptor Risk–Coverage Results Summary

## Purpose

This document summarizes the Phase 3B risk–coverage analysis under the wildlife-specialized MegaDescriptor-S-224 fixed pretrained baseline.

Phase 3B extends the previous ResNet-50 Phase 3 analysis by asking whether the risk–coverage behavior changes when pairwise similarities are computed using a wildlife-specialized embedding model.

The project does not identify individual animals directly. Similarity scores are treated as measurement signals for review-readiness validation, not as final identity decisions.

No model training or fine-tuning was performed.

---

## Background

The first completed Phase 2/3 pipeline used a generic ImageNet baseline:

```text
torchvision ResNet-50 ImageNet1K V2 penultimate embedding
That baseline produced weak-to-moderate same/different separation:

Metric	ResNet-50 Result
Same-individual mean similarity	0.579955
Different-individual mean similarity	0.493990
Same-minus-different gap	0.085966
ROC-AUC	0.618667

A wildlife-specialized baseline was then tested:

BVRA/MegaDescriptor-S-224

MegaDescriptor-S-224 produced stronger separation:

Metric	MegaDescriptor-S-224 Result
Same-individual mean similarity	0.235992
Different-individual mean similarity	0.118512
Same-minus-different gap	0.117479
ROC-AUC	0.690400

The AUC improved by 0.071733, and the same-minus-different gap increased by 0.031513, which is approximately a 36.7% relative gap increase.

Absolute cosine values should not be directly compared across models because different embedding spaces have different similarity scales. The meaningful comparisons are AUC, same-minus-different gap, readiness-group behavior, and within-model threshold behavior.

Phase 3B Question

Phase 3B addresses the same risk–coverage question as Phase 3A:

After filtering low-readiness images, does pairwise false-positive proxy risk decrease, and how much known matching evidence is lost?

The difference is that Phase 3B uses MegaDescriptor-S-224 similarities rather than ResNet-50 similarities.

Input Summary
Item	Count
Total pair rows	400
Same-individual pairs	100
Different-individual pairs	300
Embedding baseline	MegaDescriptor-S-224
Model role	Fixed wildlife-specialized embedding baseline
Training / fine-tuning	None

The Colab-generated MegaDescriptor outputs passed local audit.

Audit checks confirmed:

required output files existed;
pair similarity row count was exactly 400;
same-individual pair count was exactly 100;
different-individual pair count was exactly 300;
no missing cosine similarity values were present;
pair IDs matched the original pair file;
no extra pair IDs were present;
same_individual values matched the original pair file;
embeddings existed for exactly 200 pilot images;
embedding model was consistent with BVRA/MegaDescriptor-S-224.
MegaDescriptor-Specific Thresholds

ResNet-50 thresholds were not reused because cosine similarity scales are not comparable across embedding baselines.

Phase 3B used MegaDescriptor-specific quantile thresholds:

Quantile	Threshold
0.50	0.116324
0.75	0.194070
0.90	0.348698
0.95	0.459079

These thresholds are pilot-specific and model-specific. They are not universal felid Re-ID thresholds.

Policy Definitions

The same three policy definitions were used:

Policy	Definition
no_filter	All pairs are retained.
balanced_filter	Both images are not unidentifiable; review-ready and review-limited are retained.
strict_filter	Only ready_ready pairs are retained.
Policy Comparison
Policy	Retained Pairs	Retained Pair Rate	Retained Same Pairs	Retained Different Pairs	Same Mean	Different Mean	Gap
no_filter	400	100.0%	100	300	0.235992	0.118512	0.117479
balanced_filter	212	53.0%	55	157	0.257496	0.149243	0.108253
strict_filter	10	2.5%	3	7	0.533246	0.326113	0.207133
Comparison with ResNet-50 Phase 3A
Policy	ResNet-50 Gap	MegaDescriptor Gap	Change
no_filter	0.085966	0.117479	+0.031513
balanced_filter	0.056663	0.108253	+0.051590
strict_filter	0.119379	0.207133	+0.087754

MegaDescriptor improved the separation gap under all three policies.

The most important change is the balanced filter. Under ResNet-50, balanced filtering preserved evidence but only weakly supported separation. Under MegaDescriptor, the balanced-filter gap increased to 0.108253, making balanced filtering more defensible as a practical review workflow.

Threshold Proxy Summary
Policy	Quantile	Threshold	True-Positive Proxy Count	False-Positive Proxy Count
no_filter	0.50	0.116324	66	134
no_filter	0.75	0.194070	46	54
no_filter	0.90	0.348698	23	17
no_filter	0.95	0.459079	14	6
balanced_filter	0.50	0.116324	39	90
balanced_filter	0.75	0.194070	29	40
balanced_filter	0.90	0.348698	14	12
balanced_filter	0.95	0.459079	10	6
strict_filter	0.50	0.116324	3	6
strict_filter	0.75	0.194070	2	5
strict_filter	0.90	0.348698	2	4
strict_filter	0.95	0.459079	2	1
Balanced Filter Interpretation

Compared with no filtering, the balanced filter reduced false-positive proxy counts at the 0.50, 0.75, and 0.90 thresholds:

Quantile	No Filter FP	Balanced FP	FP Reduction
0.50	134	90	44 fewer, 32.8% reduction
0.75	54	40	14 fewer, 25.9% reduction
0.90	17	12	5 fewer, 29.4% reduction
0.95	6	6	no reduction

The balanced filter also retained more evidence than the strict filter:

Policy	Retained Same Pairs	Retained Different Pairs
balanced_filter	55	157
strict_filter	3	7

Interpretation:

The balanced filter is more defensible under MegaDescriptor than it was under ResNet-50. It preserves substantially more evidence than strict filtering while providing measurable mid-threshold pairwise false-positive proxy reduction.

Strict Filter Interpretation

The strict filter reduced false-positive proxy counts most strongly, but only because it retained very few pairs.

Compared with no filtering:

Quantile	No Filter FP	Strict FP	FP Reduction	No Filter TP	Strict TP
0.50	134	6	95.5% reduction	66	3
0.75	54	5	90.7% reduction	46	2
0.90	17	4	76.5% reduction	23	2
0.95	6	1	83.3% reduction	14	2

Interpretation:

The strict filter remains useful as a high-confidence subset, but it is too evidence-losing to be the only general workflow policy.

Answer to Q2 under MegaDescriptor

Phase 3B strengthens the tiered workflow interpretation.

Under MegaDescriptor-S-224, filtering low-readiness images still produces a clear risk–coverage trade-off. Strict filtering reduces pairwise false-positive proxy counts most strongly, but it retains only 3 same-individual pairs. Balanced filtering provides a more practical compromise: it preserves much more known matching evidence while reducing false-positive proxy counts at mid-level MegaDescriptor-specific thresholds.

The most defensible workflow remains:

Triage Label	Recommended Role
review-ready	High-confidence candidate Re-ID review
review-limited	Secondary or cautious manual review
unidentifiable	Excluded from individual-level Re-ID review
Relationship to Q1

Phase 2B showed that MegaDescriptor-S-224 improved same/different separation compared with ResNet-50.

This strengthens Q1 from:

partial / mixed support

to:

moderate pilot-level support

The project can now say that review-readiness has clearer technical relevance when measured with a wildlife-specialized embedding baseline.

However, this remains pilot-level evidence. It does not prove universal review-ready superiority.

What This Result Supports

This result supports the following cautious statement:

In the CzechLynx pilot, a wildlife-specialized MegaDescriptor-S-224 fixed baseline produced stronger same/different separation than a generic ResNet-50 ImageNet baseline. Under this baseline, balanced review-readiness filtering provided measurable mid-threshold pairwise false-positive proxy reduction while preserving substantially more evidence than strict filtering. These results strengthen the interpretation of review-readiness as a tiered workflow-control signal.

What This Result Does Not Support

This result does not support claims that:

the project identifies individual animals directly;
MegaDescriptor produces final identity decisions;
the thresholds are universal;
pairwise false-positive proxy counts are real-world false-match rates;
strict filtering is always the best policy;
the workflow is field-deployment ready;
the result generalizes to all felids or camera-trap datasets.
Limitations
The pilot still uses only 200 images.
The ready_ready group remains sparse.
The strict filter retains only 3 same-individual pairs.
Colab inference requires local audit documentation for reproducibility.
MegaDescriptor may still be influenced by background or encounter-level similarity.
Thresholds are model-specific and pilot-specific.
No independent inter-rater human review has been completed.
The analysis does not validate WildTrax/UWIN individual IDs.
The analysis does not validate Marbled Cat Re-ID.
The analysis does not estimate field deployment false-match rates.
Phase 3B Decision

Phase 3B is complete for the current CzechLynx pilot.

The result should be incorporated into the mentor-facing project report, Phase 2/3 summaries, and future project planning.

Main decision:

Keep the tiered workflow interpretation, but strengthen it with the MegaDescriptor result. Balanced filtering is now more defensible than it was under ResNet-50, while strict filtering remains too evidence-losing for general use.

Next Steps
Update the mentor-facing progress summary with MegaDescriptor Phase 2B and Phase 3B results.
Update the paper-style project report draft.
Add a daily work log entry for the Colab MegaDescriptor and Phase 3B milestone.
Keep generated outputs local and uncommitted.
Consider a future larger-pair or larger-image pilot to stabilize the sparse ready_ready result.