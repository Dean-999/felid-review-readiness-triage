# Final Modeling Bootstrap Contract

Date: 2026-07-07

Status: `PASS_READY_FOR_FINAL_MODELING_BOOTSTRAP`

This is the modeling entry contract after the project slimming. Final modeling
must start from `outputs/final_freeze/<scope>/manifest.csv` and copied images
under `outputs/final_freeze/<scope>/images/`.

| Scope | Status | Rows | Missing copied images | Identity validation allowed | Permitted endpoint |
| --- | --- | ---: | ---: | --- | --- |
| lynx-wild | PASS | 3000 | 0 | True | same/different pair validation, reviewability, risk routing |
| bobcat-wild | PASS | 3000 | 0 | False | review-readiness, comparability, evidence-risk transfer |
| bobcat-urban | PASS | 6000 | 0 | False | review-readiness, comparability, domain-shift pressure |
| lynx-urban | OPTIONAL_MISSING | 0 | 0 | False | qualitative/exploratory context; not a 3000-image core |

## Binding Modeling Scope

- PF-ERI is a post-retrieval pair-level selective evidence governance layer.
- The first formal model is the PF-ERI Selective Evidence Sufficiency Model:
  a risk-calibrated selective inference layer for wildlife Re-ID candidate
  pairs.
- The model should estimate pair-level evidence sufficiency and calibrated
  evidence risk after strong descriptor candidate retrieval.
- CzechLynx wild known-ID rows may support same/different pair validation.
- Bobcat wild and Bobcat urban rows may support transfer stress, pair
  comparability, review-readiness, and evidence-risk pressure only.
- Bobcat identity accuracy, Bobcat false-match accuracy, and descriptor-training
  improvement claims remain blocked unless verified Bobcat identity labels or
  audited same/different Bobcat pair labels are added later.
- `lynx-urban` is not a required 3000-image modeling cell; it is an optional
  auxiliary heterogeneity note only.

## Selective Evidence Sufficiency Modeling Plan

Active work must be named by module purpose, not by new phase numbers.

```text
modeling-contract:
  build the final pair-level input contract from outputs/final_freeze

evidence-feature-extraction:
  compute image evidence, pair comparability, descriptor conflict, and
  domain/source stress features

known-id-evidence-sufficiency-validation:
  train and validate the evidence sufficiency model on known-ID CzechLynx pairs

risk-calibrated-evidence-admission:
  calibrate selective-risk thresholds and report risk-coverage behavior

evidence-risk-decomposition:
  explain not-ready risk by observable evidence components and reason labels

bobcat-wild-urban-transfer-stress:
  evaluate evidence-risk shift and review burden under Bobcat wild/urban data
  without identity-accuracy claims

review-budget-routing:
  select pair subsets under fixed review budget and target evidence-risk levels

robustness-and-claim-gates:
  run group-aware splits, descriptor-family stratification, ablations,
  calibration checks, and blocked-claim audits
```

Mathematical target:

```text
maximize accepted-pair coverage
subject to calibrated selective evidence risk <= alpha
```
