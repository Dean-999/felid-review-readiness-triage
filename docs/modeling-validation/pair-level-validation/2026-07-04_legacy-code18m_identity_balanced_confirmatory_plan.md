# legacy-code18m Identity-Balanced Confirmatory Validation

Date: 2026-07-04

## Purpose

Phase18L showed descriptor-controlled support for MegaDescriptor. Its high/low
PF-ERI groups still had unequal known same/different identity composition.
Phase18M removes that confound.

The confirmatory claim is:

```text
PF-ERI admissibility predicts human reviewability after controlling descriptor family, high descriptor similarity, and known same/different identity stratum.
```

## Design

For each descriptor:

```text
same-ID + high PF-ERI admissibility
same-ID + low PF-ERI admissibility
different-ID + high PF-ERI admissibility
different-ID + low PF-ERI admissibility
```

Default sample:

```text
50 matched high/low pairs per identity stratum
200 review pairs per descriptor
400 review pairs total
3 reviewers
1200 human labels total
```

High and low PF-ERI rows are greedily matched by descriptor similarity percentile within each identity stratum.

## Blinding

The Streamlit review app shows only:

```text
photo pair
reviewability_decision
not_ready_reason
secondary_reason
visibility_notes
```

It does not show identity truth, PF-ERI group, PF-ERI scores, descriptor similarity, or route.

## Pass Standard

The strict gate requires all descriptor-specific identity-stratum checks to pass:

```text
MegaDescriptor same-ID: low PF-ERI > high PF-ERI uncertain/not-ready
MegaDescriptor different-ID: low PF-ERI > high PF-ERI uncertain/not-ready
DINOv2 same-ID: low PF-ERI > high PF-ERI uncertain/not-ready
DINOv2 different-ID: low PF-ERI > high PF-ERI uncertain/not-ready
```

Each check must have a positive bootstrap confidence interval lower bound.

## Boundary

This phase is not identity accuracy, not a new descriptor, not a universal threshold claim, and not a Bobcat identity claim.

## Group-Visible Result

The Phase18M group-visible review produced 1,200 labels over 400
majority-vote pairs:

```text
outputs/legacy-code18/legacy-code18m_identity_balanced_analysis/
```

Current gate:

```text
PASS
```

Majority-vote effects:

| Descriptor | Identity stratum | High uncertain/not-ready | Low uncertain/not-ready | Difference | 95% CI |
| --- | --- | ---: | ---: | ---: | --- |
| MegaDescriptor | same-ID | 0.020 | 0.180 | +0.160 | [+0.060, +0.280] |
| MegaDescriptor | different-ID | 0.200 | 0.640 | +0.440 | [+0.260, +0.620] |
| DINOv2 | same-ID | 0.020 | 0.400 | +0.380 | [+0.240, +0.520] |
| DINOv2 | different-ID | 0.300 | 0.740 | +0.440 | [+0.260, +0.600] |

Interpretation:

```text
Low PF-ERI admissibility remains enriched for human uncertain/not-ready
reviewability labels after descriptor family, descriptor similarity, and
known same/different identity stratum are controlled.
```

## Blind-Confirmation Completion

The project completed the final blind confirmation on the same 400 legacy-code18m
pairs. In that pass, reviewers must not see:

```text
PF-ERI high/low group
same/different identity stratum
descriptor similarity
PF-ERI scores
PF-ERI route
```

The project used this pass as the locked closure step for the strict Phase18M
claim.

Final claim rule:

```text
The strict manuscript claim is allowed because the blind
confirmation reproduces the positive low-minus-high effect in all four
descriptor x identity-stratum cells.
```

The result status is:

```text
BLIND_CONFIRMED_IDENTITY_BALANCED_PASS
```

Verified artifacts:

```text
outputs/legacy-code18/legacy-code18m_identity_balanced_review_packet/
outputs/legacy-code18/legacy-code18m_streamlit_review/
outputs/legacy-code18/legacy-code18m_identity_balanced_analysis/legacy-code18m_claim_gate.csv
```
