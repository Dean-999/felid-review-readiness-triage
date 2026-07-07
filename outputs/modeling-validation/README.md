# Modeling Validation Outputs

Pair-level modeling, strong-baseline, reviewability, and identity-balanced
validation outputs.

Current contents:

```text
final-modeling-bootstrap/
pair-construction/
evidence-feature-extraction/
known-id-evidence-sufficiency-validation/
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
