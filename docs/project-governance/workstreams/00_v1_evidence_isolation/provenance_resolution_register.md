# Workstream 00 Provenance Resolution Register

Status: `isolated_with_provenance_pending`  
Date: 2026-07-10

## Scope and Method

This register evaluates the v1 evidence package using direct source artifacts rather than prior PASS labels. The assessment distinguishes the existence of a record from the validity of the inference drawn from it. It records what is physically present, what the source itself says, the principal bias risk, and the only role that the item may retain in PF-ERI v2.

## Identity-Balanced Phase18M Review Records

Six completed working CSVs are present under `archive/pferi_v1/outputs/modeling-validation/pair-level-validation/streamlit-identity-balanced-review/`. They contain 1,200 filled decisions across three reviewers, two descriptors, and 400 derived pair rows. This is a genuine historical source record and is retained as such. However, the Phase18M Streamlit application exposed a `PF-ERI / identity group` selector with labels including `HIGH PF-ERI admissibility`, `LOW PF-ERI admissibility`, `same ID`, and `different ID`; it also displayed the selected pair’s group and candidate rank. The exposure is visible in `archive/pferi_v1/reproducibility/scripts/streamlit_phase18m_identity_balanced_review_app.py`, including the filter and caption logic.

This is a critical detection-bias and construct-contamination problem. The reviewed outcome may reflect the reviewer’s response to a known experimental condition rather than an independent judgement of image-pair reviewability. The raw records therefore support only exploratory hypothesis generation. They do not establish blind confirmation, reviewer reliability for v2, model calibration, or workflow value. The derived 400-row validation table and all model, routing, and display outputs that inherit these labels receive the same `v1_exploratory_not_confirmatory` status.

## Synthetic Reviewer-1 Agreement Result

The agreement audit at `archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_analysis_audit.json` reports a binary Cohen’s kappa of 0.859305. Its own `reviewer_counts` field identifies `synthetic_calibration_reviewer_1`. The purported external-reviewer-1 working CSV contains 280 rows and zero completed review decisions. There is no evidentiary path from this file to an independent human review.

This is not a minor metadata defect. Reporting the 0.859305 value as human inter-rater reliability would be a source-provenance error and a form of outcome misrepresentation. The result is permanently excluded from all human-reviewer, construct-validity, and manuscript claims. It may remain only as a record of a prior synthetic calibration exercise.

## Reviewer-2 Agreement Result

The reviewer-2 working CSV contains 280 filled decisions and supports the calculation reported in `agreement-analysis-reviewer2`, including a kappa of 0.785098. Yet each source-row note describes the labels as `synthetic calibration labels for private threshold comparison only; not independent blind evidence`. A later corrected copy and provenance note state that the same labels should instead be considered an independent external blind review. The correction preserves the labels but does not provide a signed reviewer attestation, original submission record, interface version or hash, immutable session timestamps independent of the edited CSV, or a demonstrable chain from the reviewer to the reviewed packet.

The two descriptions conflict. Under a conservative evidence-quality standard, the later correction is insufficient to convert a source record that self-identifies as synthetic into independent human evidence. Reviewer 2 is therefore `provenance_pending`. The 0.785098 result may not be used in v2 reliability, construct-validity, or submission claims unless the missing primary documentation is obtained and independently linked to the existing record. Failure to obtain it does not invalidate the future v2 study; it only prevents retrospective elevation of v1.

## Phase18N Packet

The Phase18N packet is preserved but retired. Its combined audit contains 1,200 requested review rows, 92 duplicate unordered pairs across the descriptor packets, and collapsed independent-quality cutoffs: both `low_mid` and `mid_high` equal 0.55. It is an unreviewed historical packet, not an outcome dataset. Distributing it now would create a design that cannot test the intended quality alternative and would risk reusing v1 feature definitions before Workstreams 01 and 02 have validated them.

## Derived Models, Routing Outputs, and Manuscript Displays

The 400-row known-ID validation table, its model metrics, calibration bins, coefficients, budget-routing outputs, pre-inference simulation, tables, figures, and claim narrative remain reproducible historical derivatives. They have not been deleted or altered. Their PASS-like labels and presentation language are superseded by the v2 rules because they inherit nonblind outcome labels, duplicated physical pairs, feature-variation failures, and same-data routing evaluation. Their permitted use is limited to error analysis, feature design, power or cost simulation, and historical narrative.

## Resolution

Workstream 00 exits as `isolated_with_provenance_pending`. The historical record is sufficiently preserved to diagnose its limitations and generate v2 hypotheses. It is insufficient for a confirmatory claim. The outstanding reviewer-2 provenance question is explicitly non-blocking for v2 and may be resolved later only by primary documentation, never by reinterpretation of the corrected CSV.
