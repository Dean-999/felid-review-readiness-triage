# Mentor Progress Update 003

## Project Title

**Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images**

## Purpose of This Update

This update summarizes the newest technical extension after the initial Phase 1–3 pilot.

The project previously used a fixed generic ResNet-50 ImageNet baseline for Phase 2 similarity validation and Phase 3 risk–coverage analysis. That baseline produced weak-to-moderate same/different separation.

The new extension adds a wildlife-specialized fixed pretrained baseline:

```text
BVRA/MegaDescriptor-S-224

This was run through a sanitized Colab package and then audited locally. No model training or fine-tuning was performed.

The purpose of this extension is to test whether the review-readiness signal becomes clearer under an animal-specialized embedding baseline.

Core Boundary

This project still does not identify individual animals directly.

This project does not train a new Re-ID model.

This project does not claim field deployment readiness, real-world false-match rates, or universal felid Re-ID thresholds.

Embeddings are treated only as measurement signals for review-readiness validation.

Previous Baseline: ResNet-50 ImageNet

The first completed Phase 2 baseline used:

torchvision ResNet-50 ImageNet1K V2 penultimate embedding

It produced:

Metric	Result
Total pairs	400
Same-individual pairs	100
Different-individual pairs	300
Same-individual mean similarity	0.579955
Different-individual mean similarity	0.493990
Same-minus-different mean gap	0.085966
ROC-AUC	0.618667

Interpretation:

The generic ResNet-50 baseline produced weak-to-moderate same/different separation. This gave partial / mixed support for Q1, but it left open the possibility that the generic ImageNet baseline was underestimating animal individual-level visual structure.

New Baseline: MegaDescriptor-S-224

The new wildlife-specialized baseline used:

BVRA/MegaDescriptor-S-224

This model was used as a fixed pretrained embedding baseline. It was run on the same 200-image CzechLynx pilot and the same 400 pair comparisons.

No model training or fine-tuning was performed.

MegaDescriptor-S-224 produced:

Metric	Result
Total pairs	400
Same-individual pairs	100
Different-individual pairs	300
Same-individual mean similarity	0.235992
Different-individual mean similarity	0.118512
Same-minus-different mean gap	0.117479
ROC-AUC	0.690400

Compared with ResNet-50:

Metric	ResNet-50	MegaDescriptor-S-224	Change
Same-minus-different gap	0.085966	0.117479	+0.031513
ROC-AUC	0.618667	0.690400	+0.071733

The same-minus-different gap increased by approximately 36.7%.

Important interpretation note:

Absolute cosine similarity values should not be directly compared across models because different embedding spaces have different similarity scales. The meaningful comparisons are AUC, same-minus-different gap, readiness-group behavior, and within-model threshold behavior.

Colab Workflow and Local Audit

The MegaDescriptor baseline was run through a sanitized Colab package.

The package included:

200 neutral pilot images;
sanitized validation CSV;
sanitized pair CSV;
ResNet-50 reference similarities.

The package did not include:

full raw CzechLynx dataset;
unique_name;
original lynx_### paths;
latitude;
longitude;
trap ID;
cell code;
exact location;
second-review mapping;
internal identity mapping files.

After Colab inference, the generated outputs were copied back into the local repository under outputs/, then audited locally.

Local audit confirmed:

required Colab output files existed;
pair similarity row count was exactly 400;
same-individual pair count was exactly 100;
different-individual pair count was exactly 300;
no missing cosine similarity values were present;
pair IDs matched the original pair file;
no extra pair IDs were present;
same_individual values matched the original pair file;
embeddings existed for exactly 200 pilot images;
embedding model was consistent with BVRA/MegaDescriptor-S-224.

Audit result:

RESULT: PASS
Phase 2B Interpretation

The MegaDescriptor baseline strengthens Q1.

Original Q1:

Do review-ready images show stronger same/different individual similarity separation than lower-readiness images under a fixed embedding baseline?

After ResNet-50, the answer was:

partial / mixed pilot-level support

After MegaDescriptor-S-224, the answer is stronger:

moderate pilot-level support

The wildlife-specialized baseline produced clearer same/different separation than the generic ImageNet baseline. This suggests that the generic ResNet-50 baseline may have underestimated review-readiness signal.

However, the result remains pilot-level. It does not prove universal review-ready superiority.

Phase 3B MegaDescriptor Risk–Coverage Analysis

Because the MegaDescriptor cosine scale differs from the ResNet-50 cosine scale, ResNet-50 thresholds were not reused.

Phase 3B used MegaDescriptor-specific quantile thresholds:

Quantile	Threshold
0.50	0.116324
0.75	0.194070
0.90	0.348698
0.95	0.459079

The same three policies were compared:

Policy	Definition
no_filter	All pairs are retained.
balanced_filter	review-ready and review-limited images are retained; unidentifiable images are excluded.
strict_filter	Only ready_ready pairs are retained.
Phase 3B Policy Comparison
Policy	Retained Pairs	Retained Same Pairs	Retained Different Pairs	Same Mean	Different Mean	Gap
no_filter	400	100	300	0.235992	0.118512	0.117479
balanced_filter	212	55	157	0.257496	0.149243	0.108253
strict_filter	10	3	7	0.533246	0.326113	0.207133

Compared with the ResNet-50 Phase 3 analysis:

Policy	ResNet-50 Gap	MegaDescriptor Gap	Change
no_filter	0.085966	0.117479	+0.031513
balanced_filter	0.056663	0.108253	+0.051590
strict_filter	0.119379	0.207133	+0.087754

MegaDescriptor improved the separation gap under all three policies.

The most important change is the balanced filter. Under ResNet-50, balanced filtering preserved evidence but reduced proxy risk weakly. Under MegaDescriptor, the balanced-filter gap increased to 0.108253, making balanced filtering more defensible as a practical review workflow.

Phase 3B Threshold Proxy Summary
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
Updated Interpretation of Q2

Original Q2:

After filtering low-readiness images, does pairwise false-positive proxy risk decrease, and how much known matching evidence is lost?

The MegaDescriptor result strengthens the previous tiered-workflow interpretation.

Under MegaDescriptor:

strict filtering still reduces pairwise false-positive proxy counts most strongly;
strict filtering still retains too little evidence to be a general workflow policy;
balanced filtering now provides clearer mid-threshold false-positive proxy reduction while preserving much more evidence than strict filtering.

Therefore, the best current interpretation remains a tiered workflow:

Triage Label	Recommended Workflow Role
review-ready	High-confidence candidate Re-ID review
review-limited	Secondary or cautious manual review
unidentifiable	Excluded from individual-level Re-ID review
Updated Main Finding

The current project finding should now be stated as:

In the CzechLynx pilot, review-readiness appears useful as a tiered workflow-control signal for felid camera-trap Re-ID review. A wildlife-specialized MegaDescriptor-S-224 fixed baseline produced stronger same/different separation than a generic ResNet-50 ImageNet baseline. Under MegaDescriptor, balanced filtering provided measurable mid-threshold pairwise false-positive proxy reduction while preserving substantially more evidence than strict filtering.

This is still a pilot-level result.

Current Limitations
The study still uses only a 200-image pilot.
The ready_ready group remains sparse.
The strict filter retains only 3 same-individual pairs.
The Colab workflow required local audit for reproducibility.
MegaDescriptor may still capture background or encounter-level similarity.
Thresholds are model-specific and pilot-specific.
No independent inter-rater review has been completed.
No WildTrax/UWIN individual-ID validation is claimed.
No Marbled Cat Re-ID validation is claimed.
No field deployment readiness is claimed.
Current Safeguards

The project continues to follow these safeguards:

raw images are not committed;
generated outputs are not committed;
data/ and outputs/ remain local;
sensitive location metadata is not published;
internal mappings remain local and separate;
second-review mapping is not used in this extension;
no model training or fine-tuning is performed;
no individual-ID claim is made.
Updated Mentor Questions
Does the MegaDescriptor improvement make the review-readiness framing more scientifically persuasive?
Is the baseline comparison sufficient for a student research report, or should another baseline be added?
Should the next extension prioritize larger pair sampling to stabilize the sparse ready_ready group?
Is the balanced-filter interpretation now strong enough to present as the preferred workflow recommendation?
Should the paper-style draft treat MegaDescriptor as the primary result and ResNet-50 as a generic baseline comparison?
Would a second human reviewer be more valuable than another model baseline at this stage?
Should the next technical extension focus on background-control / split-aware analysis?
Immediate Next Steps
Update the paper-style project report draft with MegaDescriptor Phase 2B and Phase 3B results.
Update the mentor package index so mentors can find the new MegaDescriptor documents.
Add a daily work log entry for the Colab MegaDescriptor and Phase 3B milestone.
Keep all generated Colab outputs local and uncommitted.
Plan a larger-pair or larger-image extension to stabilize the ready_ready result.