# Phase 6 Annotation Workflow Digest

Date: 2026-06-17

Purpose: summarize the Phase 6 annotation and review-package lineage. This file is a navigation layer; it does not replace the original protocols or audit records.

## Why Phase 6 Added Annotation Work

PF-ERI depends on explicit visual evidence factors rather than generic image quality alone. Phase 6 expanded the annotation workflow to capture factors that matter for patterned-felid Re-ID:

- pattern visibility;
- side/flank comparability;
- blur;
- occlusion;
- body visibility;
- viewpoint compatibility;
- review usability and failure modes.

## Main Workflow Families

### Candidate Selection

Candidate selection documents record how additional images were chosen for review or annotation. These are provenance records and should not be deleted until the final annotation lineage is summarized in one audited table.

### Unique-500 Workflow

The unique-500 documents record image batching, review protocols, audit rules, rebuild decisions, and balanced v2 selection. This cluster is large because it preserves selection lineage and correction history.

### Assisted Annotation

The assisted annotation files document workspace setup, assisted review range handling, synchronization, and cleanup/rebuild decisions.

### Streamlit Review App

The Streamlit app and related protocols are annotation infrastructure. They are not the scientific algorithm, but they preserve how labels were collected and reviewed.

## Cleanup Boundary

Do not delete annotation files only because they look operational. They explain provenance, blinding, label schema, and review decisions.

Safe future cleanup should:

1. preserve final schema and final label lineage;
2. preserve audit reports;
3. keep only final annotation lineage summaries in the active docs tree.

## Canonical Source Files

- superseded candidate-selection plans were merged into this digest and removed from the active tree.
- `phase6_annotation_candidate_selection_results.md`
- `phase6_annotation_reliability_protocol.md`
- `phase6_unique_500_annotation_workflow_protocol.md`
- `phase6_unique_500_annotation_audit_rules.md`
- `phase6_unique_500_review_set_rebuild_results.md`
- `phase6_unique_500_v2_balanced_selection_results.md`
- `phase6_unique_500_v2_balanced_annotation_workflow_protocol.md`
- `phase6_unique_500_v2_balanced_assisted_annotation_protocol.md`
