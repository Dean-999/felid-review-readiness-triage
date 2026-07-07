# Modeling Validation Outputs

Pair-level modeling, strong-baseline, reviewability, and identity-balanced
validation outputs.

Current contents:

```text
final-modeling-bootstrap/
pair-construction/
evidence-feature-extraction/
known-id-evidence-sufficiency-validation/
risk-calibrated-evidence-admission/
evidence-risk-decomposition/
bobcat-wild-urban-transfer-stress/
review-budget-routing/
pair-level-validation/
```

Current formal modeling entry:

- `final-modeling-bootstrap/` builds the image-level modeling contract and
  claim gates.
- `pair-construction/` builds CzechLynx known-ID pairs and Bobcat unlabeled
  transfer-stress pairs for the PF-ERI Selective Evidence Sufficiency Model.
- `evidence-feature-extraction/` computes prespecified PF-ERI pair-level
  evidence components and records predictor/label/diagnostic field roles.
- `known-id-evidence-sufficiency-validation/` trains interpretable CzechLynx
  reviewability validation models with group-aware image splits.
- `risk-calibrated-evidence-admission/` calibrates selective evidence-risk
  thresholds and emits accept/cautious/defer/conflict review routes.
- `evidence-risk-decomposition/` decomposes risk into observable component
  families and flags reason-label enrichment needs.
- `bobcat-wild-urban-transfer-stress/` applies the calibrated evidence router
  to unlabeled Bobcat wild/urban transfer-stress pairs without making identity,
  false-match, mAP, MRR, or top-k retrieval claims.
- `review-budget-routing/` compares PF-ERI selective review queues against a
  descriptor-rank-only queue under fixed human review budgets and emits Bobcat
  budget-allocation diagnostics without identity claims.
