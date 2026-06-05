# Mentor Package Index

## Purpose

This document is a navigation guide for mentors, professors, or reviewers who want to understand the project quickly.

The repository now contains a complete pilot workflow for:

**Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images**

The project does not identify individual animals directly. It evaluates whether camera-trap images are reliable enough to enter individual-level Re-ID review.

This index explains which documents to read first, what each file contains, and how the current pilot results should be interpreted.

---

## Recommended Reading Order

### 1. Start Here: Project Overview

**File:** `README.md`

Read this first for:

- project title;
- one-sentence definition;
- research questions;
- data roles;
- current status;
- safety rules;
- folder structure;
- “No Final Claims Yet” boundary.

The README is the shortest entry point for understanding the repo.

---

### 2. Current Mentor Update

**File:** `docs/mentor_updates/mentor_progress_update_002.md`

Read this second.

This is the most useful mentor-facing summary of the current completed pilot. It includes:

- Phase 1 manual triage results;
- second-review consistency results;
- Phase 2 similarity reliability results;
- Phase 3 risk–coverage policy results;
- current interpretation;
- limitations;
- questions for mentor feedback.

This document is intended for a mentor meeting.

---

### 3. Full Paper-Style Draft

**File:** `paper/project_report_draft.md`

Read this if you want the full research narrative.

It includes:

- abstract;
- introduction;
- project boundaries;
- data roles;
- methods;
- results;
- discussion;
- limitations;
- future work;
- references and source notes.

This is not a final paper. It is a working project-report draft for mentor review and later polishing.

---

## Phase-Specific Documents

### Phase 0 — Scope and Boundary

Directory:

`docs/phase0/`

Important files:

| File | Purpose |
|---|---|
| `project_scope.md` | Defines the project’s final scope and what is excluded. |
| `research_questions.md` | Defines Q1 reliability and Q2 risk–coverage trade-off. |
| `data_roles.md` | Explains the roles of CzechLynx, UWIN/WildTrax, and Marbled Cat. |
| `claims_and_boundaries.md` | Lists allowed and forbidden claims. |
| `evidence_chain.md` | Explains how the project evidence is structured. |
| `phase0_decision_log.md` | Records early scope decisions. |

Read these if you want to understand why the project is framed as a review-readiness workflow rather than a new Re-ID model.

---

### Phase 1 — Manual Triage and Consistency

Directory:

`docs/phase1/`

Key files:

| File | Purpose |
|---|---|
| `triage_rubric.md` | Defines `review-ready`, `review-limited`, and `unidentifiable`. |
| `czechlynx_sampling_plan.md` | Explains pilot sampling from CzechLynx. |
| `czechlynx_data_access_notes.md` | Records local dataset audit notes. |
| `phase1_go_no_go_criteria.md` | Defines criteria for proceeding beyond Phase 1. |
| `czechlynx_license_and_citation_audit.md` | Separates article license, dataset license, and project policy. |
| `czechlynx_second_review_consistency_summary.md` | Summarizes delayed second-review consistency results. |

Most important Phase 1 result:

- 200-image manual triage completed.
- Final audit passed.
- Delayed 30-image second-review achieved 80% exact `triage_label` agreement.
- Cohen’s kappa for `triage_label` was 0.700.

Interpretation:

The manual rubric is acceptable for pilot-level progression, but supporting fields remain exploratory.

---

### Phase 2 — Similarity Reliability Validation

Directory:

`docs/phase2/`

Key files:

| File | Purpose |
|---|---|
| `phase2_validation_plan.md` | Explains Phase 2 design. |
| `embedding_baseline_selection.md` | Explains why a fixed embedding baseline is used. |
| `metrics_plan.md` | Defines similarity metrics and interpretation. |
| `phase2_embedding_execution_notes.md` | Records embedding extraction details. |
| `phase2_reliability_analysis_notes.md` | Explains Phase 2 reliability analysis. |
| `phase2_reliability_results_summary.md` | Summarizes Phase 2 results and interpretation. |

Most important Phase 2 result:

- 200 images embedded.
- 400 pair similarities computed.
- Fixed generic ResNet-50 ImageNet baseline used.
- Overall ROC-AUC: 0.618667.
- Overall same-minus-different mean gap: 0.085966.

Interpretation:

Phase 2 shows weak-to-moderate same/different separation under a generic baseline. Q1 receives partial / mixed support, not strong proof.

---

### Phase 3 — Risk–Coverage Policy Analysis

Directory:

`docs/phase3/`

Key files:

| File | Purpose |
|---|---|
| `risk_coverage_policy_plan.md` | Defines planned no-filter, balanced-filter, and strict-filter policies. |
| `phase3_risk_coverage_results_notes.md` | Records Phase 3 analysis notes. |
| `phase3_risk_coverage_results_summary.md` | Summarizes Phase 3 policy results and interpretation. |

Most important Phase 3 result:

| Policy | Retained Images | Retained IDs | Retained Same Pairs | Interpretation |
|---|---:|---:|---:|---|
| No filter | 100% | 100% | 100% | Maximum coverage, maximum noise. |
| Balanced filter | 70.5% | 86% | 55% | Preserves evidence, weak risk reduction. |
| Strict filter | 17% | 31% | 3% | Strong proxy-risk reduction, severe evidence loss. |

Interpretation:

The best current conclusion is a tiered workflow:

| Triage Label | Recommended Role |
|---|---|
| `review-ready` | High-confidence candidate Re-ID review. |
| `review-limited` | Secondary or cautious manual review. |
| `unidentifiable` | Excluded from individual-level Re-ID review. |

---

## Code and Workflow Scripts

Directory:

`scripts/`

Important workflow scripts:

| Script | Purpose |
|---|---|
| `prepare_czechlynx_pilot_manifest.py` | Builds the blinded CzechLynx pilot sample. |
| `audit_czechlynx_pilot_blinding.py` | Checks blinding of the pilot triage CSV. |
| `make_czechlynx_triage_contact_sheet.py` | Creates local review contact sheets. |
| `audit_czechlynx_triage_consistency.py` | Audits manual triage label consistency. |
| `prepare_czechlynx_second_review_subset.py` | Creates delayed second-review subset. |
| `audit_czechlynx_second_review_blinding.py` | Checks second-review blinding. |
| `compare_czechlynx_second_review_consistency.py` | Compares first and second review labels. |
| `build_czechlynx_validation_table.py` | Joins final labels back to internal known-ID validation data. |
| `construct_czechlynx_pair_sets.py` | Builds same/different individual pair sets. |
| `audit_czechlynx_pair_sets.py` | Audits pair construction. |
| `check_czechlynx_embedding_inputs.py` | Checks embedding input readiness. |
| `extract_czechlynx_embeddings.py` | Extracts fixed ResNet-50 embeddings. |
| `compute_czechlynx_pair_similarities.py` | Computes pairwise cosine similarities. |
| `audit_czechlynx_similarity_outputs.py` | Audits embedding and similarity outputs. |
| `analyze_czechlynx_phase2_reid_reliability.py` | Runs Phase 2 reliability analysis. |
| `analyze_czechlynx_phase3_risk_coverage.py` | Runs Phase 3 risk–coverage analysis. |

---

## Data and Output Safety

The following should not be committed to GitHub:

- `data/`
- `outputs/`
- raw images
- generated contact sheets
- embeddings
- pair similarity CSVs
- internal mapping files
- final label CSVs
- generated figures
- sensitive location metadata

The repository should contain only code, documentation, and project structure.

---

## Current Best Interpretation

The current pilot supports this cautious interpretation:

> Review-readiness is useful as a tiered workflow-control signal for deciding how felid camera-trap images should enter individual-level Re-ID review. The strict review-ready-only filter reduces pairwise false-positive proxy counts but loses too much known matching evidence. A balanced or tiered workflow is more defensible than a single hard filter.

The current pilot does not prove:

- true individual animal identification;
- universal thresholds;
- field deployment readiness;
- a new Re-ID model;
- real-world false-match rates.

---

## Suggested Mentor Review Questions

1. Is the review-readiness framing scientifically defensible?
2. Are the three triage classes appropriate?
3. Should `review-limited` be split into more precise subtypes?
4. Is the 30-image intra-reviewer check sufficient for a pilot?
5. Is a generic ResNet-50 baseline acceptable for preliminary validation?
6. Should the next technical extension use a wildlife-specialized embedding baseline?
7. Should the project prioritize larger pair sampling, split-aware validation, or independent second review?
8. Is the tiered workflow interpretation stronger than a strict-filter recommendation?
9. What public-display cautions should be followed for CzechLynx example images?
10. Is this project suitable for a paper-style student research report or science fair extension?

---

## Immediate Next Step After Mentor Review

The most useful next technical extension is likely one of:

1. wildlife-specialized embedding baseline comparison;
2. larger pair sampling with multiple random seeds;
3. split-aware validation using CzechLynx geo-aware and time-aware metadata;
4. independent second-review labeling by another human reviewer.

The recommended first extension is:

**wildlife-specialized embedding baseline comparison**, because it tests whether the weak-to-moderate Phase 2 separation is caused by the generic baseline rather than the review-readiness gate itself.