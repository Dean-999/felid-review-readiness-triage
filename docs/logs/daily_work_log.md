# Daily Work Log

## Purpose

This file records daily project progress, problems, repairs, and decisions.

It is not a personal diary. It is a research audit trail.

The goal is to show:

- what was done each day;
- what problem appeared;
- how the problem was repaired;
- what decision was made;
- what evidence or file changed;
- what remains unresolved.

This log will be useful for mentor meetings, paper writing, science fair process documentation, and project management.

## Logging Rule

Add one entry for every day when project work happens.

Each entry should be short but specific.

Do not write vague entries such as:

```text
Worked on project.
```

Write entries such as:

```text
Revised the triage rubric to separate species-level tagging from individual-level Re-ID readiness. Added side_comparability and night_ir_artifact as required fields because field images may be species-identifiable but not comparable for identity review.
```

## Daily Entry Template

```markdown
## YYYY-MM-DD

### Work Completed

- 

### Problem Encountered

- 

### Repair / Decision

- 

### Files Changed

- 

### Evidence / Source Notes

- 

### Remaining Risk

- 

### Next Action

- 
```

## Backfilled Initial Entries

## 2026-05-31

### Work Completed

- Narrowed the project from a broad ReID-Audit direction to Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images.
- Locked the project around two research questions: Q1 reliability and Q2 risk–coverage trade-off.
- Defined CzechLynx as the quantitative known-ID validation carrier.
- Defined UWIN/WildTrax Bobcat and Canada Lynx as field motivation and field-readiness stress test data.
- Defined Marbled Cat as a future Asian conservation application scenario only.

### Problem Encountered

- The original ReID-Audit direction was too broad and overlapped with mature animal Re-ID work.
- It risked being misunderstood as a new Re-ID model, a full identity prediction system, or a population estimation project.

### Repair / Decision

- Removed new model claims, SOTA claims, universal threshold claims, full website claims, RUDI claims, and true individual identity claims.
- Reframed Re-ID as an auxiliary measurement signal.
- Required all false-match language to use the phrase pairwise false-match risk proxy under known-ID validation.

### Files Changed

- docs/phase0/project_scope.md
- docs/phase0/research_questions.md
- docs/phase0/data_roles.md
- docs/phase0/claims_and_boundaries.md
- docs/phase0/evidence_chain.md
- docs/phase0/phase0_decision_log.md

### Evidence / Source Notes

- Existing animal Re-ID work is mature, so the project must focus on a pre-Re-ID review-readiness gate.
- Field tagging experience through UWIN-Atlanta provides the practical motivation.

### Remaining Risk

- The rubric may still look subjective unless Phase 1 defines observable fields.
- CzechLynx license and exact dataset version still need to be verified.

### Next Action

- Start Phase 1: data access notes, triage rubric, CzechLynx sampling plan, WildTrax field triage plan, Marbled Cat future application note, and Go/No-Go criteria.

## 2026-06-01

### Work Completed

- Drafted Phase 1 documentation structure.
- Added a formal daily work log mechanism.
- Defined `review-ready`, `review-limited`, and `unidentifiable` as primary triage labels.
- Added required supporting fields including blur level, occlusion level, lighting condition, night IR artifact, visible side, side comparability, visible region, pattern visibility, metadata completeness, confidence, uncertainty flag, exclusion reason, and notes.

### Problem Encountered

- The label `review-limited` could become too vague if not tied to specific observable fields.
- The project could confuse species-level tagging with individual-level Re-ID readiness.
- WildTrax/UWIN images have field value but lack verified individual IDs.

### Repair / Decision

- Required every triage label to be supported by observable fields.
- Added explicit rule: species-level usable does not mean Re-ID-ready.
- Restricted WildTrax/UWIN to field-readiness distribution and failure-mode analysis.
- Kept CzechLynx as the only current strict validation source.

### Files Changed

- docs/phase1/triage_rubric.md
- docs/phase1/czechlynx_data_access_notes.md
- docs/phase1/czechlynx_sampling_plan.md
- docs/phase1/wildtrax_field_triage_plan.md
- docs/phase1/marbled_cat_application_readiness_note.md
- docs/phase1/phase1_go_no_go_criteria.md
- docs/logs/daily_work_log.md

### Evidence / Source Notes

- CzechLynx provides the known-ID validation path.
- WildTrax/UWIN tagging experience provides field motivation.
- Marbled Cat remains future application only.

### Remaining Risk

- CzechLynx exact license and local file counts still need to be verified after download.
- WildTrax public image display permission should still be confirmed before public release.
- The rubric needs a pilot second-review consistency check.

### Next Action

- Complete CzechLynx access audit.
- Create the first CzechLynx pilot triage CSV.
- Triage 100-200 pilot images without viewing individual IDs.
- Re-triage 30 images after 48 hours for consistency.
