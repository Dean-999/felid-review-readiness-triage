# Mentor Review Checklist

## Purpose

This checklist is intended for a mentor, professor, or research advisor reviewing the current pilot version of the project:

**Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images**

The goal is to make the review process efficient and transparent.

This checklist summarizes:

- what has been completed;
- what evidence supports each phase;
- what claims are allowed;
- what claims are not allowed;
- what decisions need mentor feedback;
- what the next technical extension should be.

---

## Core Project Definition

This project evaluates whether felid camera-trap images are reliable enough to enter individual-level Re-ID review.

It does not identify individual animals directly.

It does not train a new Re-ID model.

It does not claim field deployment readiness.

The project focuses on a pre-Re-ID review-readiness gate that classifies camera-trap images into:

- `review-ready`
- `review-limited`
- `unidentifiable`

---

## Recommended Files to Review First

| Priority | File | Purpose |
|---:|---|---|
| 1 | `README.md` | Short project overview and repository status. |
| 2 | `docs/mentor_updates/mentor_progress_update_002.md` | Best current mentor-facing results summary. |
| 3 | `docs/mentor_updates/mentor_package_index.md` | Navigation guide for all major project files. |
| 4 | `paper/project_report_draft.md` | Full paper-style project draft. |
| 5 | `docs/phase1/czechlynx_second_review_consistency_summary.md` | Phase 1 consistency evidence. |
| 6 | `docs/phase2/phase2_reliability_results_summary.md` | Phase 2 similarity reliability interpretation. |
| 7 | `docs/phase3/phase3_risk_coverage_results_summary.md` | Phase 3 risk–coverage interpretation. |
| 8 | `docs/next_steps/technical_extension_plan.md` | Planned technical extensions. |

---

## Phase 1 Review Checklist

### Phase 1 Goal

Determine whether a rubric-based review-readiness triage workflow can be applied consistently enough for pilot-level validation.

### Completed Items

| Item | Status |
|---|---|
| CzechLynx local dataset access audit | Complete |
| Real-image metadata audit | Complete |
| Blinded pilot sample generation | Complete |
| 200-image manual triage | Complete |
| Automated triage consistency audit | PASS |
| 30-image delayed second-review subset | Complete |
| Second-review blinding audit | PASS |
| Second-review consistency comparison | Complete |
| Phase 1 second-review summary document | Complete |

### Key Phase 1 Results

| Metric | Result |
|---|---:|
| Total manually triaged images | 200 |
| `review-ready` images | 34 |
| `review-limited` images | 107 |
| `unidentifiable` images | 59 |
| Second-review subset size | 30 |
| Exact `triage_label` agreement | 24/30 = 0.800 |
| Cohen’s kappa for `triage_label` | 0.700 |
| `pattern_visibility` agreement | 20/30 = 0.667 |
| `side_comparability` agreement | 16/30 = 0.533 |
| `exclusion_reason` agreement | 20/30 = 0.667 |

### Phase 1 Interpretation

The main triage label showed acceptable pilot-level intra-reviewer consistency.

Supporting fields were less stable than the main `triage_label`, especially `side_comparability`. Therefore, supporting-field analyses should be treated as exploratory.

### Phase 1 Mentor Review Questions

1. Is the three-class rubric scientifically defensible?
2. Should `review-limited` be split into more specific categories?
3. Is 80% delayed intra-reviewer agreement sufficient for pilot-level progression?
4. Which supporting fields are most important for felid Re-ID review?
5. Should the project add a second human reviewer before paper submission?

---

## Phase 2 Review Checklist

### Phase 2 Goal

Test whether review-readiness labels correspond to measurable same/different similarity behavior under a fixed embedding baseline.

### Completed Items

| Item | Status |
|---|---|
| Final labels joined back to internal known-ID table | Complete |
| Same/different pair construction | Complete |
| Pair construction audit | PASS |
| Embedding input audit | PASS |
| Fixed ResNet-50 embedding extraction | Complete |
| Pair cosine similarity computation | Complete |
| Similarity output audit | PASS |
| Phase 2 reliability analysis | Complete |
| Phase 2 results summary document | Complete |

### Key Phase 2 Setup

| Item | Count / Description |
|---|---:|
| Validation images | 200 |
| Working individual IDs | 100 |
| Same-individual pairs | 100 |
| Different-individual pairs | 300 |
| Total pairs | 400 |
| Embedding baseline | torchvision ResNet-50 ImageNet1K V2 penultimate embedding |
| Embedding dimension | 2048 |
| Training / fine-tuning | None |

### Key Phase 2 Results

| Metric | Result |
|---|---:|
| Same-individual mean cosine similarity | 0.579955 |
| Different-individual mean cosine similarity | 0.493990 |
| Overall same-minus-different mean gap | 0.085966 |
| ROC-AUC | 0.618667 |

Selected readiness-group gaps:

| Pair Readiness Group | Mean Gap |
|---|---:|
| `limited_limited` | 0.035978 |
| `ready_limited` | 0.068114 |
| `ready_ready` | 0.119379 |
| `unidentifiable_unidentifiable` | 0.133164 |

### Phase 2 Interpretation

The fixed generic ResNet-50 baseline produced weak-to-moderate same/different separation.

The `ready_ready` group showed a positive signal compared with the overall gap and the `limited_limited` group, but the `ready_ready` group had sparse pair counts:

- 3 same-individual pairs
- 7 different-individual pairs

Therefore, Q1 receives partial / mixed support, not strong proof.

### Phase 2 Mentor Review Questions

1. Is a generic ResNet-50 baseline acceptable as an initial measurement signal?
2. Should the next baseline be wildlife-specialized?
3. How should the sparse `ready_ready` pair count be handled?
4. Should the analysis use more negative pairs or multiple random seeds?
5. Are same/different cosine similarities an appropriate proxy for pilot-level validation?

---

## Phase 3 Review Checklist

### Phase 3 Goal

Evaluate whether filtering low-readiness images reduces pairwise false-positive proxy counts, and quantify how much known matching evidence is lost.

### Completed Items

| Item | Status |
|---|---|
| No-filter policy analysis | Complete |
| Balanced-filter policy analysis | Complete |
| Strict-filter policy analysis | Complete |
| Threshold proxy summary | Complete |
| Phase 3 risk–coverage report | Complete |
| Phase 3 results summary document | Complete |

### Policy Definitions

| Policy | Definition |
|---|---|
| No filter | Retain all images and pairs. |
| Balanced filter | Retain `review-ready` and `review-limited`; exclude `unidentifiable`. |
| Strict filter | Retain only `review-ready`. |

### Key Phase 3 Results

| Policy | Retained Images | Retained IDs | Retained Same Pairs | Retained Pair Rate | Mean Gap |
|---|---:|---:|---:|---:|---:|
| No filter | 200/200 = 100.0% | 100/100 = 100.0% | 100/100 = 100.0% | 100.0% | 0.085966 |
| Balanced filter | 141/200 = 70.5% | 86/100 = 86.0% | 55/100 = 55.0% | 53.0% | 0.056663 |
| Strict filter | 34/200 = 17.0% | 31/100 = 31.0% | 3/100 = 3.0% | 2.5% | 0.119379 |

### Phase 3 Interpretation

Phase 3 shows a clear risk–coverage trade-off.

The strict filter reduces pairwise false-positive proxy counts most strongly, but it retains only 3% of known same-individual pairs. This makes it too evidence-losing to serve as the only general workflow policy in this pilot.

The balanced filter preserves substantially more image, identity, and same-pair coverage, but it only weakly reduces high-threshold false-positive proxy counts.

The best current interpretation is a tiered workflow:

| Triage Label | Recommended Workflow Role |
|---|---|
| `review-ready` | High-confidence candidate Re-ID review |
| `review-limited` | Secondary or cautious manual review |
| `unidentifiable` | Excluded from individual-level Re-ID review |

### Phase 3 Mentor Review Questions

1. Is the tiered workflow interpretation more defensible than strict filtering?
2. Is the strict filter too conservative for conservation use?
3. Should `review-limited` be subdivided for better policy design?
4. Are the threshold proxy counts useful for describing risk–coverage trade-offs?
5. How should evidence loss be presented in a paper-style report?

---

## Data Safety Checklist

| Rule | Status |
|---|---|
| Raw images not committed | Satisfied |
| `data/` not committed | Satisfied |
| `outputs/` not committed | Satisfied |
| Contact sheets not committed | Satisfied |
| Internal mapping files not committed | Satisfied |
| Final label CSVs not committed | Satisfied |
| Sensitive location metadata not published | Satisfied |
| Public image display remains conservative | Satisfied |
| CzechLynx article license separated from dataset license | Satisfied |
| Zenodo dataset license recorded | Satisfied |

---

## Claims Checklist

### Claims Currently Supported

The project can currently support the following cautious claims:

- A blinded review-readiness triage workflow was implemented for a 200-image CzechLynx pilot.
- The main triage label showed acceptable pilot-level intra-reviewer consistency.
- Under a fixed generic ResNet-50 baseline, the pilot showed weak-to-moderate same/different similarity separation.
- The `ready_ready` group showed a positive signal, but pair counts were sparse.
- Risk–coverage analysis showed that strict filtering reduces pairwise false-positive proxy counts but loses most known same-pair evidence.
- A tiered review workflow is more defensible than a single strict hard filter.

### Claims Not Supported

The project cannot currently claim:

- true individual animal identification;
- field deployment readiness;
- real-world false-match rates;
- universal Re-ID thresholds;
- a new Re-ID model;
- state-of-the-art performance;
- population estimation;
- validated WildTrax/UWIN individual IDs;
- Marbled Cat Re-ID validation;
- generalization to all felids or all camera-trap datasets.

---

## Current Review Decision

The project is ready for mentor review as a complete pilot workflow.

The current pilot is not final-publication-ready yet, but it is strong enough for:

- mentor feedback;
- paper-style report development;
- science fair planning discussion;
- next technical-extension planning.

Recommended next technical extension:

**Wildlife-specialized embedding baseline comparison.**

This extension would test whether the current weak-to-moderate Phase 2 separation is caused by the generic ResNet-50 baseline rather than by weak review-readiness signal.

---

## Requested Mentor Feedback

The most important requested feedback is:

1. Is the review-readiness framing scientifically useful?
2. Is the rubric appropriate for felid Re-ID readiness?
3. Is the current pilot design rigorous enough for a student research project?
4. Is the Phase 2 result worth strengthening with a wildlife-specialized baseline?
5. Should the next extension prioritize stronger embeddings, larger pair sampling, or independent reviewer validation?
6. Is the tiered workflow interpretation the best way to frame the Phase 3 result?
7. What should be revised before this becomes a full paper-style report?