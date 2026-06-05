# Phase 3 Risk-Coverage Results Notes

## Purpose

This note summarizes the CzechLynx pilot Phase 3 risk-coverage policy analysis.

Phase 3 uses existing Phase 2 pairwise cosine similarities from a fixed generic ResNet-50 ImageNet embedding baseline. The baseline is not a wildlife-specialized Re-ID model. The analysis evaluates pilot-level policy trade-offs for review-readiness triage; it does not identify individual animals.

## Policies

Three fixed policies were evaluated:

| Policy | Definition |
| --- | --- |
| `no_filter` | Retain all pairs and images. |
| `balanced_filter` | Retain review-ready and review-limited images; exclude unidentifiable images. |
| `strict_filter` | Retain only review-ready images. |

## Policy-Level Results

| Policy | Retained pairs | Retained pair rate | Retained same pairs | Retained different pairs | Retained images | Retained image rate | Retained identities | Same mean | Different mean | Mean gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `no_filter` | 400 | 1.000 | 100 | 300 | 200 | 1.000 | 100 | 0.579955 | 0.493990 | 0.085966 |
| `balanced_filter` | 212 | 0.530 | 55 | 157 | 141 | 0.705 | 86 | 0.682978 | 0.626315 | 0.056663 |
| `strict_filter` | 10 | 0.025 | 3 | 7 | 34 | 0.170 | 31 | 0.852984 | 0.733605 | 0.119379 |

The strict policy has the largest same-minus-different mean gap in this pilot output, but it retains only 10 pairs and 3 same-individual pairs. That sparse evidence should be interpreted cautiously.

The balanced policy retains 141 of 200 images and 55 of 100 same-individual pairs while excluding unidentifiable images. Under these fixed thresholds, it reduces some pairwise false-positive proxy counts relative to no filtering, but it does not remove all high-similarity different-individual pairs.

## Threshold Proxy Results

False-positive counts below are pairwise proxy counts: different-individual pilot pairs with similarity at or above the threshold. They are not real-world false-match rates.

| Policy | Threshold | True-positive proxy count | False-positive proxy count |
| --- | ---: | ---: | ---: |
| `no_filter` | 0.547081 | 60 | 140 |
| `no_filter` | 0.680093 | 34 | 66 |
| `no_filter` | 0.770424 | 22 | 18 |
| `no_filter` | 0.808955 | 14 | 6 |
| `balanced_filter` | 0.547081 | 44 | 119 |
| `balanced_filter` | 0.680093 | 27 | 61 |
| `balanced_filter` | 0.770424 | 19 | 17 |
| `balanced_filter` | 0.808955 | 12 | 6 |
| `strict_filter` | 0.547081 | 3 | 7 |
| `strict_filter` | 0.680093 | 3 | 6 |
| `strict_filter` | 0.770424 | 3 | 3 |
| `strict_filter` | 0.808955 | 2 | 1 |

These thresholds are pilot-specific and model-specific. They should not be treated as universal thresholds for felid Re-ID or field deployment.

## Interpretation Boundaries

This analysis can support cautious pilot-level comparison of retained evidence and pairwise false-match risk proxies under fixed triage policies.

This analysis does not claim:

- true individual identification;
- a real-world false-match rate;
- a wildlife-specialized Re-ID model;
- universal thresholds across felid species;
- field deployment readiness;
- final scientific conclusions.

## Output Files

- `outputs/czechlynx/analysis/phase3_policy_comparison.csv`
- `outputs/czechlynx/analysis/phase3_threshold_policy_summary.csv`
- `outputs/czechlynx/qc/phase3_risk_coverage_report.txt`
- `outputs/czechlynx/figures/phase3_policy_retained_evidence_bar_chart.png`
- `outputs/czechlynx/figures/phase3_policy_false_positive_proxy_bar_chart.png`
