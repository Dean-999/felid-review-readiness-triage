# legacy-code18m Identity-Balanced Confirmatory Validation

Date: 2026-07-04

## Purpose

legacy-code18l showed strong descriptor-controlled support for MegaDescriptor, but its high/low PF-ERI groups were not balanced by known same/different identity outcome. legacy-code18m directly removes that confound.

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

The highest-goal gate requires all descriptor-specific identity-stratum checks to pass:

```text
MegaDescriptor same-ID: low PF-ERI > high PF-ERI uncertain/not-ready
MegaDescriptor different-ID: low PF-ERI > high PF-ERI uncertain/not-ready
DINOv2 same-ID: low PF-ERI > high PF-ERI uncertain/not-ready
DINOv2 different-ID: low PF-ERI > high PF-ERI uncertain/not-ready
```

Each check must have a positive bootstrap confidence interval lower bound.

## Boundary

This phase is not identity accuracy, not a new descriptor, not a universal threshold claim, and not a Bobcat identity claim.

## Completed Group-Visible Result

The completed legacy-code18m group-visible review produced 1,200 labels over 400
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

This was not a new exploratory branch. It was the locked closure step for the
highest-confidence legacy-code18m claim.

Final claim rule:

```text
The highest-confidence manuscript claim is allowed because the blind
confirmation reproduces the positive low-minus-high effect in all four
descriptor x identity-stratum cells.
```

The current completed result is therefore:

```text
BLIND_CONFIRMED_IDENTITY_BALANCED_PASS
```

Verified artifacts:

```text
outputs/legacy-code18/legacy-code18m_identity_balanced_review_packet/
outputs/legacy-code18/legacy-code18m_streamlit_review/
outputs/legacy-code18/legacy-code18m_identity_balanced_analysis/legacy-code18m_claim_gate.csv
```
