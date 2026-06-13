# Phase 6 Unique-500 v2 Balanced Image Annotation Freeze Note

Date: 2026-06-13

Frozen annotation file:

`data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_v1.csv`

Source working file:

`data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_working.csv`

Final audit command:

```bash
python3 scripts/audit_phase6_unique_500_v2_balanced_image_annotations.py --final

Final audit result:

result: PASS
row_count: 500
image_count: 500
pending_count: 0
invalid_value_count: 0
missing_image_count: 0
leakage_issue_count: 0
logic_warning_count: 28

Balanced selection structure:

extreme_hard_proxy: 65
high_evidence_proxy: 150
low_but_annotatable_proxy: 110
medium_evidence_proxy: 175
batch_001 to batch_010: 50 images each
near_black_extreme_overall: 38

Interpretation:

This file is the frozen v1 label set for the Phase 6 v2 balanced unique-500 image-level annotation expansion. It is a stable input for downstream PF-ERI visual-factor distribution analysis, expanded pair-level table construction, and factor-to-risk sensitivity analysis.

The 28 logic warnings are retained as non-blocking audit warnings because the corrected final audit reported PASS and no hard schema, image, leakage, or pending-row failures remained.
