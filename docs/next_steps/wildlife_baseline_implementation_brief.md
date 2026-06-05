# Wildlife-Specialized Baseline Implementation Brief

## Purpose

This document defines the next technical extension after the completed CzechLynx Phase 1–3 pilot.

The current pilot used a fixed generic ResNet-50 ImageNet embedding baseline. That baseline produced weak-to-moderate same/different separation:

| Metric | Result |
|---|---:|
| Overall same-minus-different mean gap | 0.085966 |
| ROC-AUC | 0.618667 |

The next technical question is:

> Does a wildlife-specialized embedding baseline produce stronger same/different separation and clearer review-readiness group behavior than the generic ResNet-50 baseline?

This extension should be implemented only after the mentor-ready package is complete and committed.

---

## Current Baseline

The completed Phase 2 baseline used:

```text
torchvision ResNet-50 ImageNet1K V2 penultimate embedding

Properties:

fixed pretrained baseline;
generic ImageNet model;
no model training;
no fine-tuning;
200 pilot image embeddings;
400 pairwise cosine similarities;
output audit passed.

Current interpretation:

The generic baseline is useful as a reproducible measurement signal, but it is not wildlife-specialized and may underrepresent individual-specific felid visual features.

Why Add a Wildlife-Specialized Baseline

The current Phase 2 result has two possible interpretations:

The review-readiness gate has only weak relationship to Re-ID similarity reliability.
The generic ResNet-50 baseline is too weak or too background-sensitive to measure the gate properly.

A wildlife-specialized baseline can help distinguish these possibilities.

If the wildlife baseline improves same/different separation and produces clearer review-ready group behavior, then the review-readiness gate may be more meaningful than the generic baseline suggests.

If the wildlife baseline does not improve results, the project can treat that as important negative evidence and emphasize the limitations of the current rubric or pilot size.

Candidate Baseline

Recommended candidate family:

MegaDescriptor / WildlifeDatasets-based embedding baseline

Reason:

designed for wildlife / animal individual re-identification contexts;
more aligned with animal visual identity patterns than ImageNet classification features;
appropriate as a fixed pretrained baseline;
can be used without training a new model.

The exact model source, package version, checkpoint, and preprocessing must be documented before results are interpreted.

Core Boundary

This extension must not turn the project into a model-training project.

It must follow these rules:

no model training;
no fine-tuning;
no new Re-ID model claim;
no state-of-the-art claim;
no true individual identification claim;
no universal threshold claim;
no field deployment claim;
embeddings are measurement signals only.
Input Files

The extension should reuse existing validated Phase 2 inputs:

data/interim/czechlynx/czechlynx_pilot_validation_table.csv
data/interim/czechlynx/czechlynx_pilot_pairs.csv

It should not modify:

data/labels/czechlynx/czechlynx_pilot_triage_final.csv
data/labels/czechlynx/czechlynx_second_review_blinded.csv
data/interim/czechlynx/czechlynx_second_review_internal_mapping.csv

It should not use or modify second-review files.

Proposed Output Files

Generated data outputs should remain local and should not be committed.

Suggested output paths:

data/interim/czechlynx/czechlynx_pilot_embeddings_wildlife_baseline.parquet
data/interim/czechlynx/czechlynx_pair_similarities_wildlife_baseline.csv
outputs/czechlynx/qc/wildlife_baseline_similarity_output_audit.txt
outputs/czechlynx/analysis/phase2_baseline_comparison.csv
outputs/czechlynx/qc/phase2_baseline_comparison_report.txt
outputs/czechlynx/figures/phase2_baseline_comparison_auc_bar_chart.png
outputs/czechlynx/figures/phase2_baseline_comparison_gap_bar_chart.png

Docs/scripts that may be committed:

scripts/extract_czechlynx_wildlife_embeddings.py
scripts/compute_czechlynx_wildlife_pair_similarities.py
scripts/audit_czechlynx_wildlife_similarity_outputs.py
scripts/compare_czechlynx_embedding_baselines.py
docs/phase2/wildlife_baseline_execution_notes.md
docs/phase2/baseline_comparison_results_summary.md
Required Scripts
1. scripts/extract_czechlynx_wildlife_embeddings.py

Purpose:

Extract one fixed wildlife-specialized embedding per pilot image.

Requirements:

read czechlynx_pilot_validation_table.csv;
load fixed pretrained wildlife baseline;
extract exactly 200 embeddings;
record model name, source, checkpoint/version, embedding dimension, preprocessing, device, and run date;
save embeddings to local data/interim/;
fail clearly if model weights are missing or environment is not configured;
do not automatically download weights unless explicitly planned in a separate setup step;
do not train or fine-tune.
2. scripts/compute_czechlynx_wildlife_pair_similarities.py

Purpose:

Compute cosine similarities for all 400 existing pair rows using wildlife baseline embeddings.

Requirements:

read wildlife embeddings;
read existing czechlynx_pilot_pairs.csv;
compute cosine similarity for all 400 pairs;
preserve pair metadata;
save local similarity CSV.
3. scripts/audit_czechlynx_wildlife_similarity_outputs.py

Purpose:

Verify output completeness and consistency.

Requirements:

confirm exactly 200 embeddings;
confirm exactly 400 pair similarities;
confirm no missing cosine similarities;
confirm all pair IDs are present;
confirm no extra pair IDs;
confirm same_individual values match the pair file;
print clear PASS/FAIL;
exit nonzero on failure.
4. scripts/compare_czechlynx_embedding_baselines.py

Purpose:

Compare generic ResNet-50 baseline against wildlife-specialized baseline.

Requirements:

read ResNet-50 pair similarities;
read wildlife baseline pair similarities;
compute overall same/different gap for both;
compute ROC-AUC for both if sklearn is available;
compute readiness-group gaps for both;
compute threshold proxy summaries for both;
save comparison CSV;
save comparison text report;
generate optional figures if matplotlib is available;
do not make final scientific claims.
Required Documentation
docs/phase2/wildlife_baseline_execution_notes.md

Should include:

model name;
model family;
model source;
checkpoint / weight version;
citation information;
preprocessing;
image size;
device;
run date;
package versions if relevant;
no-training / no-fine-tuning statement;
limitation statement.
docs/phase2/baseline_comparison_results_summary.md

Should include:

comparison purpose;
ResNet-50 baseline recap;
wildlife baseline results;
overall gap comparison;
ROC-AUC comparison;
readiness-group comparison;
Phase 3 policy implication if relevant;
interpretation;
limitations;
next decision.
Acceptance Criteria

The extension is complete only if:

wildlife baseline embeddings are generated for exactly 200 images;
wildlife baseline similarities are generated for exactly 400 pairs;
output audit passes;
comparison report is generated;
baseline metadata are documented;
no raw data are modified;
no labels are modified;
no model training or fine-tuning is added;
no individual-identification claim is made;
generated data and outputs remain uncommitted.
Interpretation Rules
If Wildlife Baseline Improves Strongly

Possible interpretation:

The review-readiness gate may align better with animal-specialized visual features than with generic ImageNet features.

Allowed wording:

“The wildlife-specialized baseline produced stronger pilot-level separation.”
“This suggests the generic baseline may underestimate review-readiness signal.”

Forbidden wording:

“The model identifies individuals.”
“The gate is proven.”
“This is deployable.”
If Wildlife Baseline Improves Slightly

Possible interpretation:

The wildlife baseline improves the measurement signal, but the result remains pilot-level and limited by sample size.

Allowed wording:

“The wildlife baseline provides modest improvement.”
“Further sampling is needed.”
If Wildlife Baseline Does Not Improve

Possible interpretation:

The current review-readiness rubric or pilot sample may not strongly separate Re-ID reliability under the tested embedding baselines.

Allowed wording:

“The negative result is informative.”
“The review-readiness gate may need refinement.”
“The pilot may require larger pair sampling or more specific readiness subcategories.”
Risks
Risk	Why It Matters	Mitigation
Dependency problems	Wildlife baseline tools may be harder to install	Keep ResNet-50 as completed baseline
Hidden downloads	Reduces reproducibility	Use explicit setup/cache step
Citation ambiguity	Model source must be credited	Record model citation before interpreting
Overclaiming	Could weaken credibility	Maintain measurement-signal language
Sparse ready_ready pairs	May still limit group conclusions	Report counts and avoid strong claims
Background similarity	May still influence embeddings	Discuss limitation and consider future split-aware analysis
Stop Conditions

Stop the extension and do not interpret results if:

embeddings are missing for any pilot image;
pair similarities are not generated for all 400 pairs;
audit fails;
model source or checkpoint cannot be documented;
script requires uncontrolled automatic downloads;
preprocessing is unclear;
output cannot be reproduced.
Recommended Implementation Order
Research and choose exact wildlife baseline.
Document model source and citation before running.
Create a small setup/cache step if needed.
Extract wildlife embeddings.
Compute wildlife pair similarities.
Audit outputs.
Compare against ResNet-50.
Write comparison summary.
Decide whether Phase 3 should be rerun under the wildlife baseline.
Update mentor package.
Current Decision

Do not run this extension until:

mentor package is clean and committed;
Git status is clean;
model source and citation are selected;
implementation plan is reviewed.

Recommended next action:

Research the exact MegaDescriptor / WildlifeDatasets setup and decide whether it can be run locally with fixed pretrained weights and clear citation.