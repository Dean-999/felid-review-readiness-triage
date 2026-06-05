# Technical Extension Plan

## Purpose

This document defines the next technical extension options after completing the CzechLynx Phase 1–3 pilot.

The current pilot already includes:

- Phase 1 blinded manual triage;
- delayed second-review consistency check;
- Phase 2 fixed-baseline similarity reliability analysis;
- Phase 3 risk–coverage policy analysis.

The next step should not be random additional coding. Any extension should strengthen the scientific interpretation of the current pilot.

---

## Current Completed Pilot

### Phase 1

Completed:

- 200-image blinded CzechLynx manual triage.
- Final triage consistency audit passed.
- 30-image delayed intra-reviewer second-review completed.
- Exact `triage_label` agreement: 24/30 = 0.800.
- Cohen’s kappa: 0.700.

Interpretation:

The main triage rubric is acceptable for pilot progression. Supporting fields remain exploratory.

### Phase 2

Completed:

- 200 image embeddings extracted.
- 400 pairwise similarities computed.
- Fixed generic ResNet-50 ImageNet baseline used.
- Overall ROC-AUC: 0.618667.
- Overall same-minus-different mean gap: 0.085966.

Interpretation:

The generic baseline produced weak-to-moderate same/different separation. Q1 receives partial / mixed support.

### Phase 3

Completed:

- No-filter, balanced-filter, and strict-filter policies compared.
- Strict filter reduced pairwise false-positive proxy counts most strongly.
- Strict filter retained only 3% of same-individual pairs.
- Balanced filter retained 70.5% of images, 86% of identities, and 55% of same-individual pairs.
- Balanced filter reduced high-threshold false-positive proxy only weakly.

Interpretation:

The strongest current conclusion is a risk–coverage trade-off. A tiered workflow is more defensible than a strict hard filter.

---

## Extension Decision Criteria

Any next extension should satisfy at least one of the following:

1. Strengthen interpretation of Q1.
2. Strengthen interpretation of Q2.
3. Reduce a known limitation.
4. Improve mentor/paper credibility.
5. Preserve project boundaries.
6. Avoid turning the project into a generic model-training project.

Extensions should not:

- claim true individual identification;
- train a new model unless explicitly approved later;
- commit raw data or generated outputs;
- publish sensitive location metadata;
- overclaim universal thresholds;
- overwrite finalized Phase 1 labels.

---

## Candidate Extension A — Wildlife-Specialized Embedding Baseline

### Description

Run a second fixed embedding baseline that is more appropriate for wildlife Re-ID than generic ImageNet ResNet-50.

Potential candidate family:

- MegaDescriptor / WildlifeDatasets-based embedding baseline.

### Why This Matters

The current Phase 2 result is weak-to-moderate:

- ROC-AUC = 0.618667.
- Overall gap = 0.085966.

This may be because:

1. review-readiness is not strongly predictive;
2. the pilot is small;
3. the generic ResNet-50 baseline is too weak;
4. background similarity affects embeddings;
5. encounter-level visual similarity influences results.

A wildlife-specialized baseline would test whether stronger animal-specific features produce clearer separation.

### Expected Outputs

Possible outputs:

- `data/interim/czechlynx/czechlynx_pilot_embeddings_wildlife_baseline.parquet`
- `data/interim/czechlynx/czechlynx_pair_similarities_wildlife_baseline.csv`
- `outputs/czechlynx/analysis/phase2_baseline_comparison.csv`
- `outputs/czechlynx/qc/wildlife_baseline_similarity_audit.txt`
- `docs/phase2/baseline_comparison_results_summary.md`

### Scientific Value

High.

This extension directly tests whether the current weak-to-moderate separation is a baseline limitation.

### Risk

Medium.

The implementation may require additional dependencies and model weights. It may also require careful citation and reproducibility documentation.

### Recommendation

This is the best next technical extension after mentor package completion.

---

## Candidate Extension B — Larger Different-Individual Pair Sampling

### Description

Increase the number of sampled different-individual pairs and test whether Phase 2 and Phase 3 results remain stable.

The current pilot uses:

- 100 same-individual pairs;
- 300 different-individual pairs.

A larger analysis could use:

- all available same-individual pairs from the pilot;
- multiple fixed-seed negative samples;
- larger different-individual pair sets.

### Why This Matters

Some current group-level results are sensitive to sparse pair counts.

For example:

- `ready_ready` has only 3 same-individual pairs and 7 different-individual pairs.
- Strict-filter Phase 3 results depend on very few retained pairs.

Larger negative sampling would test whether findings remain stable.

### Expected Outputs

Possible outputs:

- multiple pair-set files with different random seeds;
- aggregate Phase 2 summary across seeds;
- aggregate Phase 3 policy comparison across seeds;
- stability plots or tables.

### Scientific Value

Medium to high.

This improves statistical stability but does not fix the generic baseline limitation.

### Risk

Low to medium.

It requires careful file naming and reproducibility.

### Recommendation

Useful after the wildlife-specialized baseline or in parallel if implementation is simple.

---

## Candidate Extension C — Split-Aware CzechLynx Validation

### Description

Use CzechLynx metadata splits to test whether review-readiness behavior changes under:

- geo-aware split;
- time-aware open split;
- time-aware closed split.

### Why This Matters

CzechLynx includes spatial and temporal splits. These are relevant because real conservation monitoring often requires generalization across time, camera locations, and regions.

This extension could ask:

- Does review-readiness behave differently across geographic regions?
- Does the risk–coverage trade-off change across time?
- Are low-readiness images more damaging in open-set conditions?

### Expected Outputs

Possible outputs:

- split-specific Phase 2 summaries;
- split-specific Phase 3 policy comparison;
- notes on whether the current pilot design is sufficient for split-aware analysis.

### Scientific Value

High if implemented carefully.

### Risk

Medium to high.

The current 200-image pilot may be too small for reliable split-aware conclusions.

### Recommendation

Plan, but do not prioritize before baseline comparison.

---

## Candidate Extension D — Independent Human Reviewer

### Description

Ask another person to label a subset of images using the same rubric.

The current second-review result measures intra-reviewer consistency only. It does not measure inter-rater reliability.

### Why This Matters

A second human reviewer would strengthen the claim that the rubric is understandable and reproducible beyond one reviewer.

### Expected Outputs

Possible outputs:

- independent-review blinded CSV;
- inter-rater agreement report;
- Cohen’s kappa between reviewers;
- disagreement analysis.

### Scientific Value

High.

### Risk

Medium.

It requires training another reviewer and ensuring they follow the rubric correctly.

### Recommendation

Important for a stronger paper-style version, but not necessary before mentor review.

---

## Candidate Extension E — WildTrax / UWIN Field-Readiness Distribution

### Description

Apply the triage rubric to UWIN/WildTrax field images without claiming individual identity validation.

### Why This Matters

This would show how the rubric behaves on real field-tagging images from a different workflow.

It could answer:

- How many field images are `review-ready`?
- How many are `review-limited`?
- What are the most common failure modes?
- Are field images mostly species-usable but Re-ID-limited?

### Expected Outputs

Possible outputs:

- field-readiness label distribution;
- failure-mode summary;
- examples of common image-quality limitations;
- no individual-ID validation claims.

### Scientific Value

Medium.

It strengthens field motivation but does not replace known-ID validation.

### Risk

Medium.

Image display permissions and data-access restrictions must be respected.

### Recommendation

Good for the conservation workflow story, but after the CzechLynx technical report is clean.

---

## Recommended Extension Order

### Step 1 — Finish Mentor Package

Before more experiments, finish:

1. `docs/mentor_updates/mentor_package_index.md`
2. `docs/mentor_updates/mentor_progress_update_002.md`
3. `paper/project_report_draft.md`

Reason:

The current Phase 1–3 pilot already forms a complete research chain. It should be presented clearly before adding more experiments.

### Step 2 — Wildlife-Specialized Embedding Baseline

Run a fixed wildlife-specific baseline and compare it with ResNet-50.

Primary question:

> Does a wildlife-specialized embedding baseline produce stronger same/different separation and clearer review-readiness group behavior?

### Step 3 — Larger Pair Sampling

If the wildlife baseline improves signal, test whether the result is stable under larger negative pair sampling.

### Step 4 — Independent Reviewer or Split-Aware Analysis

Choose based on mentor feedback.

If the mentor emphasizes rubric reliability, prioritize independent review.

If the mentor emphasizes machine-learning validation, prioritize split-aware analysis.

### Step 5 — WildTrax/UWIN Field Distribution

Use field data to strengthen real-world motivation without claiming identity validation.

---

## Recommended Immediate Next Extension

The recommended immediate technical extension is:

**Wildlife-specialized embedding baseline comparison.**

Rationale:

The current ResNet-50 baseline is generic and produced only weak-to-moderate separation. A wildlife-specialized baseline is the most direct way to test whether the review-readiness gate has stronger signal under a more appropriate feature extractor.

---

## Acceptance Criteria for the Next Extension

The wildlife-specialized baseline extension should only be considered complete if it provides:

1. documented model source;
2. fixed pretrained weights;
3. no training or fine-tuning;
4. exactly 200 embeddings;
5. exactly 400 pair similarities;
6. output audit pass;
7. Phase 2 comparison table against ResNet-50;
8. Phase 3 policy comparison under the new baseline;
9. conservative interpretation;
10. no final individual-identification claims.

---

## Risks and Mitigations

| Risk | Why It Matters | Mitigation |
|---|---|---|
| New baseline is difficult to install | Could slow progress | Keep ResNet-50 results as completed baseline |
| New baseline does not improve results | Could weaken apparent signal | Treat as important negative result |
| More experiments dilute project story | Could make report unclear | Finish mentor package first |
| Dependency/version issues | Could reduce reproducibility | Record exact model, package version, device, and run date |
| Overclaiming stronger baseline | Could harm credibility | Keep all conclusions pilot-level |

---

## Decision Rule

Do not start a new technical extension until:

- mentor package is complete;
- current Git status is clean;
- current results are clearly documented;
- next extension has a written implementation plan.

Current decision:

> Finish mentor package first. Then pursue wildlife-specialized embedding baseline comparison as the next technical extension, unless mentor feedback suggests a different priority.