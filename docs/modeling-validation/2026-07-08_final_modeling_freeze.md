# Final Modeling Freeze

Date: 2026-07-08

Status: frozen for paper/report writing.

## Scope

The final model is PF-ERI as a post-retrieval selective evidence sufficiency and
reviewability layer. It is evaluated on CzechLynx known-ID reviewed candidate
pairs and applied to Bobcat wild/urban data only as unlabeled same-genus
transfer-stress and workflow-allocation diagnostics.

## Final Data Freeze

- CzechLynx known-ID validation: `outputs/final_freeze/lynx-wild/manifest.csv`
  with 3,000 rows.
- Bobcat wild transfer stress: `outputs/final_freeze/bobcat-wild/manifest.csv`
  with 3,000 rows.
- Bobcat urban transfer stress: `outputs/final_freeze/bobcat-urban/manifest.csv`
  with 6,000 rows.

## Final Paper-Ready Artifacts

- Main model result table:
  `outputs/modeling-validation/advanced-mathematical-validation/paper-ready/main_model_result_table.csv`
- Final claim narrative:
  `outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_claim_narrative.md`
- Confidence and limitations table:
  `outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations_table.csv`
- Confidence and limitations appendix:
  `outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations.md`
- Final methods-ready report:
  `outputs/modeling-validation/advanced-mathematical-validation/final_methods_ready_report.md`
- Final claim gate table:
  `outputs/modeling-validation/advanced-mathematical-validation/final_advanced_claim_gate_table.csv`

## Core Model Result

The pooled main result table reports:

- Descriptor only: AUROC 0.585.
- Image quality only: AUROC 0.725.
- PF-ERI evidence only: AUROC 0.780.
- Descriptor + PF-ERI: AUROC 0.799.

These numbers support reviewability/admissibility prediction, not identity
assignment or Bobcat identity accuracy.

## Blind Reliability Evidence

The final labels are blind reliability-supported reviewability labels.

- Reviewer 1: n=280, binary kappa 0.859305, binary agreement 0.939286,
  primary reason agreement on non-ready rows 0.805970.
- Reviewer 2: n=280, binary kappa 0.785098, binary agreement 0.914286,
  primary reason agreement on non-ready rows 0.736318.

Reviewer 2 is confirmed as an independent external blind reviewer. The original
Reviewer 2 CSV contained stale metadata in `reviewer_notes`; the raw file is
preserved, and a corrected metadata copy is stored at:

`outputs/modeling-validation/blind-reliability-packet/external-reviews/external_reviewer_2/blind_reliability_review_working.corrected.csv`

The correction changes only `reviewer_notes`; labels are unchanged. The audit is:

`outputs/modeling-validation/blind-reliability-packet/external-reviews/external_reviewer_2/corrected_copy_audit.json`

## Allowed Claims

- PF-ERI is a pair-level selective evidence inference layer after strong
  descriptor retrieval.
- PF-ERI evidence features improve reviewability prediction on CzechLynx
  reviewed candidate pairs relative to descriptor-only and quality-only
  baselines.
- The validation labels can be described as blind reliability-supported
  reviewability labels.
- Empirical CzechLynx calibration/evaluation risk-coverage routing is supported,
  with finite-sample caveats.
- Query-image cluster bootstrap uncertainty can be reported for CzechLynx
  reviewability metrics.
- Predicted-risk constrained review-budget allocation can be reported as a
  workflow optimization result.

## Blocked Claims

- No automatic identity assignment.
- No Bobcat identity accuracy, false-match accuracy, mAP, MRR, or top-k
  identity metrics.
- No claim that PF-ERI is a new descriptor, embedding, or replacement for
  MegaDescriptor/DINOv2.
- No unqualified distribution-free guarantee across Bobcat or domain shift.
- No source-held-out causal domain-generalization claim.
- No complete validated causal/mechanistic reason classifier claim.

## Rebuild Commands

```bash
python3 scripts/analyze_blind_reliability_reviews.py \
  --review-root outputs/modeling-validation/blind-reliability-packet/blind_reliability_review_template.csv

python3 scripts/analyze_blind_reliability_reviews.py \
  --review-root outputs/modeling-validation/blind-reliability-packet/external-reviews/external_reviewer_2/blind_reliability_review_working.csv

python3 scripts/build_blind_reliability_packet.py \
  --correct-reviewer-copy external_reviewer_2

python3 scripts/build_advanced_claim_gates_methods_report.py
```

## Verification

```bash
python3 -m unittest \
  tests/test_advanced_claim_gates_methods_report.py \
  tests/test_blind_reliability_packet.py \
  tests/test_attest_manual_review_labels.py \
  tests/test_feature_varied_validation_packet.py \
  tests/test_online_reason_label_supplement.py \
  tests/test_streamlit_pair_review_common.py
```

Last verification: 29 tests passed, 3 skipped.

