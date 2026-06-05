# Larger Pilot and Pair Sampling Plan

## Purpose

This document defines the next technical stage after completing the initial CzechLynx 200-image pilot, ResNet-50 baseline, MegaDescriptor-S-224 baseline, and Phase 3B risk–coverage analysis.

The current results are scientifically useful, but they remain pilot-level. The main remaining weakness is sparse evidence in the `ready_ready` group.

The next stage should test whether the current findings remain stable under larger sampling and stronger pair coverage.

---

## Current Completed Evidence

### Phase 1

The project completed a 200-image blinded CzechLynx manual triage pilot.

Final label distribution:

| Label | Count |
|---|---:|
| `review-ready` | 34 |
| `review-limited` | 107 |
| `unidentifiable` | 59 |

A delayed 30-image second-review consistency check showed:

| Metric | Result |
|---|---:|
| Exact `triage_label` agreement | 24/30 = 0.800 |
| Cohen’s kappa | 0.700 |

Interpretation:

The main triage label is acceptable for pilot-level progression. Supporting fields are less stable and should remain exploratory.

---

### Phase 2A — ResNet-50 Baseline

The generic ResNet-50 ImageNet baseline produced:

| Metric | Result |
|---|---:|
| Same-individual mean similarity | 0.579955 |
| Different-individual mean similarity | 0.493990 |
| Same-minus-different gap | 0.085966 |
| ROC-AUC | 0.618667 |

Interpretation:

The generic baseline showed weak-to-moderate same/different separation.

---

### Phase 2B — MegaDescriptor-S-224 Baseline

The wildlife-specialized MegaDescriptor-S-224 baseline produced:

| Metric | Result |
|---|---:|
| Same-individual mean similarity | 0.235992 |
| Different-individual mean similarity | 0.118512 |
| Same-minus-different gap | 0.117479 |
| ROC-AUC | 0.690400 |

Improvement over ResNet-50:

| Metric | Improvement |
|---|---:|
| AUC gain | +0.071733 |
| Gap gain | +0.031513 |
| Relative gap increase | ~36.7% |

Interpretation:

MegaDescriptor strengthens Q1 from partial / mixed support to moderate pilot-level support.

---

### Phase 3B — MegaDescriptor Risk–Coverage

MegaDescriptor Phase 3B showed:

| Policy | Retained Same Pairs | Retained Different Pairs | Gap |
|---|---:|---:|---:|
| `no_filter` | 100 | 300 | 0.117479 |
| `balanced_filter` | 55 | 157 | 0.108253 |
| `strict_filter` | 3 | 7 | 0.207133 |

Interpretation:

Balanced filtering is more meaningful under MegaDescriptor than under ResNet-50. Strict filtering still reduces proxy risk most strongly but retains too little same-pair evidence.

---

## Main Remaining Weakness

The current 200-image pilot has sparse `ready_ready` evidence.

Critical issue:

| Group | Same Pairs | Different Pairs |
|---|---:|---:|
| `ready_ready` | 3 | 7 |

This is too small for strong claims.

The `ready_ready` result is directionally strong, but it may be unstable because a few individual pairs can strongly affect the mean gap.

Therefore, the next technical stage should focus on increasing stable evidence for:

- `ready_ready` pairs;
- balanced-filter pairs;
- strict-filter retained evidence;
- multiple-seed negative pair stability.

---

## Why Larger Pair Sampling Alone Is Not Enough

With the current 200-image pilot, each working individual ID has only 2 images.

This means:

- each individual contributes only one same-individual pair;
- the maximum number of same-individual pairs is fixed at 100;
- the number of `ready_ready` same pairs is fixed by existing labels;
- larger different-individual sampling can improve negative-pair stability, but cannot increase `ready_ready` same-pair evidence.

Therefore, larger pair sampling is useful but insufficient by itself.

It can answer:

> Are different-individual results stable under more negative sampling?

It cannot fully answer:

> Does `review-ready` consistently improve same-individual evidence?

To answer the second question, the pilot needs more images and preferably more images per individual.

---

## Candidate Expansion Strategies

## Strategy A — Current 200-Image Multi-Seed Negative Pair Stability

### Description

Reuse the existing 200-image pilot and generate multiple different-individual pair samples across fixed random seeds.

Same-individual pairs remain fixed at 100.

Different-individual pairs can be increased or repeated across seeds.

### Purpose

Test whether Phase 2 and Phase 3 results are stable across negative-pair sampling.

### Advantages

- No new manual labeling required.
- Fast.
- Low risk.
- Uses existing validated labels and embeddings.
- Good for checking whether AUC and false-positive proxy behavior are sensitive to one random seed.

### Limitations

- Does not increase `ready_ready` same pairs.
- Does not solve the strict-filter evidence-loss issue.
- Still pilot-level.

### Recommended Use

Use as a short stability check before expanding the image pilot.

---

## Strategy B — Expand to 500 Images with 2 Images per ID

### Description

Create a 500-image pilot from 250 working individual IDs, with 2 images per ID.

### Purpose

Increase total image coverage and improve the chance of more `review-ready` images.

### Advantages

- Straightforward extension of current sampling design.
- Increases total images.
- Increases same-individual pairs from 100 to 250.
- Keeps labeling workload manageable.

### Limitations

- Still only 1 same pair per ID.
- If `review-ready` remains rare, `ready_ready` same-pair counts may still be limited.
- Requires manual triage of 300 additional images.

### Recommended Use

Good next expansion if time is limited and manual labeling workload must remain controlled.

---

## Strategy C — Multi-Image-per-ID Expansion

### Description

Sample more than 2 images per individual ID, prioritizing IDs with enough available real images.

Example design:

| IDs | Images per ID | Total Images |
|---:|---:|---:|
| 100 | 4 | 400 |
| 125 | 4 | 500 |
| 150 | 4 | 600 |

### Purpose

Increase same-individual pair coverage within each ID.

With 4 images per ID, each ID can produce 6 same-individual pairs instead of only 1.

### Advantages

- Strongly improves same-pair evidence.
- Better for testing Re-ID reliability.
- More likely to produce stable `ready_ready` same-pair results.
- More useful for pairwise similarity analysis.

### Limitations

- More complex sampling.
- More manual labeling.
- More chance of repeated near-duplicate images if not controlled.
- Needs encounter/time diversity rules to avoid overly easy same-pair matches.

### Recommended Use

This is the best scientific design if the goal is to strengthen Q1.

---

## Strategy D — Targeted Review-Ready Enrichment

### Description

Use a pre-screening strategy to increase the number of likely `review-ready` images in the expanded pilot.

This does not mean changing labels. It means sampling candidates likely to include more usable side-body pattern evidence.

### Purpose

Increase `ready_ready` pair counts.

### Advantages

- Directly addresses the sparse `ready_ready` problem.
- Makes strict-filter analysis more stable.
- Can produce stronger Q1 evidence.

### Limitations

- May introduce sampling bias.
- Must be clearly documented.
- Cannot be treated as representative full-dataset readiness distribution.
- Must not use identity labels in a way that creates leakage.

### Recommended Use

Use only as a secondary targeted sample, not as the main representative pilot.

---

## Recommended Next Design

The recommended next stage should combine two parts:

## Part 1 — Multi-Seed Negative Pair Stability on Current 200-Image Pilot

Purpose:

Test whether existing ResNet-50 and MegaDescriptor results are stable across different negative-pair samples.

This is fast and does not require new labeling.

Outputs:

- multiple pair files across seeds;
- AUC / gap summaries across seeds;
- Phase 3B stability across seeds;
- stability report.

Decision:

If the MegaDescriptor improvement remains stable across seeds, the current result becomes more robust.

---

## Part 2 — Expanded Multi-Image-per-ID Pilot

Purpose:

Increase same-pair evidence, especially for `ready_ready`.

Recommended design:

| Parameter | Recommended Value |
|---|---:|
| Working IDs | 100–125 |
| Images per ID | 4 |
| Total images | 400–500 |
| Same pairs per ID | up to 6 |
| Manual labeling target | 400–500 images |

This design is scientifically stronger than simply increasing to 500 images with 2 per ID.

Why:

The main weakness is not just total image count. The main weakness is same-pair evidence inside readiness groups.

Multi-image-per-ID sampling directly addresses that issue.

---

## Expanded Pilot Sampling Rules

The expanded pilot should follow these rules:

1. Use real CzechLynx images only.
2. Do not use synthetic images for primary validation.
3. Use only IDs with enough available images.
4. Avoid sampling near-duplicate frames when possible.
5. Preserve blinded filenames.
6. Do not expose `unique_name`, raw identity folder names, latitude, longitude, trap ID, cell code, or exact location in manual triage files.
7. Keep internal mapping separate from blinded labels.
8. Do not use second-review files.
9. Do not overwrite the completed 200-image pilot.
10. Store expanded-pilot files under new names.

Suggested naming:

```text
czechlynx_expanded_manifest.csv
czechlynx_expanded_internal_with_ids.csv
czechlynx_expanded_triage_blinded.csv
expanded_review_images/

Expanded Pilot Labeling Strategy

The expanded pilot should reuse the existing rubric:

review-ready
review-limited
unidentifiable

Supporting fields should remain the same for compatibility.

However, because supporting fields were less stable than the main label, Phase 4 analysis should prioritize:

main triage_label;
exclusion reason;
pattern visibility;
visible side / side comparability only as exploratory fields.
Expanded Pilot Analysis Plan

After expanded labeling:

Run blinding audit.
Run triage consistency audit.
Build expanded validation table.
Construct pair sets:
all or sampled same-individual pairs;
fixed-seed different-individual pairs;
multiple negative sampling seeds.
Extract MegaDescriptor embeddings.
Compute pair similarities.
Analyze:
overall AUC;
same-minus-different gap;
readiness-group gaps;
ready_ready same/different counts;
balanced-filter and strict-filter behavior;
threshold proxy behavior.
Compare expanded pilot results against 200-image pilot results.
Success Criteria

The larger pilot strengthens the project if:

Criterion	Target
Expanded audit	PASS
Same-individual pairs	substantially more than 100
ready_ready same pairs	substantially more than 3
MegaDescriptor AUC	stable or improved
Balanced-filter behavior	stable or improved
Strict-filter evidence loss	better quantified
Claims	remain conservative

Minimum useful target:

ready_ready same pairs >= 20

Stronger target:

ready_ready same pairs >= 30

If this cannot be reached naturally, the result should be reported as a dataset limitation rather than forced.

Risks
Risk	Why It Matters	Mitigation
Manual labeling workload increases	400–500 images takes time	Start with 400-image expansion
More images may still not produce many review-ready pairs	Review-ready may be rare	Report rarity as finding
Sampling bias	Targeted sampling may overstate readiness	Separate representative and enriched samples
Near-duplicate same pairs	Could inflate same-pair similarity	Use encounter/time diversity rules
Background similarity	May inflate pair similarity	Future split-aware / camera-aware analysis
Colab reproducibility	Notebook execution is less controlled	Keep local audits and source notes
Overclaiming	Stronger results may tempt broad claims	Keep pilot-level language
Stop Conditions

Stop the expansion and reassess if:

blinding audit fails;
leakage appears in triage files;
raw paths or identity labels appear in manual files;
expanded sampling creates too many near-duplicates;
manual labeling quality drops;
generated outputs accidentally enter Git;
model outputs cannot be audited;
results are interpreted as identity decisions.
Recommended Immediate Next Step

Do not immediately label 500 new images.

First implement a planning and audit slice:

Inspect CzechLynx image counts per working ID.
Estimate how many IDs have at least 4 usable real images.
Simulate possible expanded sampling sizes:
100 IDs × 4 images;
125 IDs × 4 images;
150 IDs × 3 images;
250 IDs × 2 images.
Produce a sampling feasibility report.
Choose expanded pilot design based on feasibility.

This avoids committing to a labeling workload before knowing what the dataset can support.

Decision

The next technical work should be:

Phase 4A — Expanded Pilot Feasibility and Pair-Stability Planning

not immediate full labeling.

Primary deliverable:

docs/next_steps/expanded_pilot_feasibility_decision.md

Primary script:

scripts/plan_czechlynx_expanded_pilot_sampling.py

The script should not create final expanded labels yet. It should only inspect feasibility and produce candidate sampling plans.