# PF-ERI Advanced Mathematical Validation Contract

Status: `PASS`

## Scientific Frame

PF-ERI is a pair-level selective evidence governance layer after
strong wildlife Re-ID descriptor retrieval. It is not a new visual
descriptor, not an embedding model, and not an automatic individual
identification system.

## Notation

- Candidate pair: `p = (x_i, x_j)`.
- Descriptor score: `s_d(p)`, produced upstream by MegaDescriptor,
  DINOv2, WildFusion, or another strong descriptor queue.
- PF-ERI evidence vector: `z(p)`, including image evidence, pair
  comparability, descriptor-evidence conflict, and source/domain
  stress diagnostics.
- Label: `y(p) = 1` means the reviewed pair is not-ready-or-uncertain;
  `y(p) = 0` means review-ready.
- Evidence risk score: `R_hat(p) = P(y(p)=1 | z(p), s_d(p))`.
- Evidence sufficiency score: `S_hat(p) = 1 - R_hat(p)`.
- Selective gate: `g_tau(p) = 1[R_hat(p) <= tau]`.

## Mathematical Target

For target evidence risk `alpha`, choose an admission threshold `tau`
that maximizes admitted-pair coverage while controlling selective risk:

```text
coverage(tau) = P(g_tau(p)=1)
selective_risk(tau) = P(y(p)=1 | g_tau(p)=1)

maximize coverage(tau)
subject to selective_risk(tau) <= alpha
```

The claim-bearing validation target is CzechLynx reviewed-pair
evidence admissibility. Bobcat outputs are transfer-stress and
workflow-allocation diagnostics only.

## Assumptions

- Calibration/evaluation claims require the declared split protocol.
- Pair dependence must be handled by image/component/identity-aware
  splitting or cluster-aware uncertainty.
- Source/domain generalization claims require actual source/domain
  variation; constant-source CzechLynx validation cannot prove them.
- Reason-class explanations require human reason labels; observable
  risk components alone support component attribution only.

## Authoritative Inputs

`outputs/modeling-validation/advanced-mathematical-validation/advanced_validation_authoritative_inputs.csv`

## Output Contract

`outputs/modeling-validation/advanced-mathematical-validation/advanced_validation_output_contract.json`

## Claim Boundaries

`outputs/modeling-validation/advanced-mathematical-validation/advanced_validation_claim_boundaries.csv`

## Binding Statement

maximize accepted-pair coverage subject to selective evidence risk <= alpha
