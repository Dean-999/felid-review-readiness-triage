# Phase 3B MegaDescriptor Risk–Coverage Plan

## Why Phase 3 Must Be Rerun Under MegaDescriptor

Phase 3A evaluated risk–coverage trade-offs under the generic ResNet-50 ImageNet baseline. Phase 2 baseline comparison showed that MegaDescriptor-S-224 improves same/different separation (higher ROC-AUC and larger same-minus-different gap) on the same CzechLynx pilot pairs.

Because policy retention and threshold-proxy behavior depend on the similarity distribution produced by the embedding baseline, Phase 3 must be rerun under MegaDescriptor before any updated Q2 interpretation is made.

Phase 3B is therefore a parallel risk–coverage analysis using MegaDescriptor Colab pairwise similarities, not a replacement of the Phase 3A ResNet record.

## Why ResNet-50 Thresholds Cannot Be Reused

ResNet-50 and MegaDescriptor-S-224 operate on different embedding scales and produce different cosine similarity distributions. The ResNet Phase 2 quantile thresholds (approximately 0.547, 0.680, 0.770, and 0.809) are not transferable to MegaDescriptor.

Phase 3B therefore computes **MegaDescriptor-specific quantile thresholds** from the MegaDescriptor cosine similarity distribution. Absolute threshold values must be interpreted only within the MegaDescriptor baseline.

## MegaDescriptor-Specific Quantile Threshold Method

Thresholds are computed from all 400 MegaDescriptor pairwise cosine similarities:

| Quantile | Role |
|---:|---|
| 0.50 | median-like pilot threshold |
| 0.75 | upper-quartile pilot threshold |
| 0.90 | high-similarity pilot threshold |
| 0.95 | very-high-similarity pilot threshold |

For each policy and each threshold:

- `true_positive_proxy_count` = same-individual pairs with cosine similarity ≥ threshold
- `false_positive_proxy_count` = different-individual pairs with cosine similarity ≥ threshold

These are pairwise proxy counts, not real-world false-match rates.

## Policies to Compare

| Policy | Definition |
|---|---|
| `no_filter` | all 400 pairs retained |
| `balanced_filter` | both images are not `unidentifiable` |
| `strict_filter` | `pair_readiness_group == ready_ready` |

These mirror Phase 3A intent while using the readiness-group definition for the strict policy.

## Metrics to Compute

### Policy comparison (per policy)

- `retained_pair_count`
- `retained_pair_rate`
- `retained_same_pair_count`
- `retained_different_pair_count`
- `retained_same_pair_rate` (relative to 100 same pairs)
- `retained_different_pair_rate` (relative to 300 different pairs)
- `same_pair_mean_similarity`
- `different_pair_mean_similarity`
- `same_minus_different_mean_gap`

### Threshold proxy summary (per policy × quantile)

- `threshold_quantile`
- `threshold`
- `true_positive_proxy_count`
- `false_positive_proxy_count`
- `retained_same_pair_count`
- `retained_different_pair_count`

## Outputs

Analysis script:

`scripts/analyze_czechlynx_phase3_risk_coverage_megadescriptor.py`

Generated outputs (untracked under `outputs/`):

| Output | Path |
|---|---|
| Policy comparison CSV | `outputs/czechlynx/analysis/phase3_megadescriptor_policy_comparison.csv` |
| Threshold summary CSV | `outputs/czechlynx/analysis/phase3_megadescriptor_threshold_policy_summary.csv` |
| QC report | `outputs/czechlynx/qc/phase3_megadescriptor_risk_coverage_report.txt` |
| Retained evidence figure (optional) | `outputs/czechlynx/figures/phase3_megadescriptor_policy_retained_evidence_bar_chart.png` |
| False-positive proxy figure (optional) | `outputs/czechlynx/figures/phase3_megadescriptor_policy_false_positive_proxy_bar_chart.png` |

Prerequisite audit:

`scripts/audit_czechlynx_colab_megadescriptor_outputs.py`

## Claims Allowed

After Phase 3B completes, cautious pilot-level statements may describe:

- MegaDescriptor-specific risk–coverage behavior under the three policies;
- pairwise false-positive proxy counts above MegaDescriptor quantile thresholds;
- pilot-level comparison of evidence retention versus proxy risk reduction;
- whether results support a tiered review workflow more strongly than a strict-only workflow.

## Claims Forbidden

Phase 3B must not claim:

- real-world false-match rates;
- universal felid Re-ID thresholds;
- individual animal identification decisions;
- field deployment readiness;
- that MegaDescriptor replaces human review;
- that strict filtering alone is sufficient for conservation monitoring.

## Decision Criteria

Interpret Phase 3B using these decision rules:

1. **If the balanced filter improves risk–coverage behavior more clearly under MegaDescriptor**, tiered workflow control gains additional pilot-level support.
2. **If the strict filter still loses most known matching evidence**, a strict-only policy remains too conservative for general use.
3. **If results remain mixed**, report them as pilot-level mixed evidence rather than a definitive workflow recommendation.

## Safety Constraints

- Do not modify raw data.
- Do not modify triage labels or second-review labels.
- Do not read or modify second-review mapping files.
- Do not train or fine-tune any model.
- Commit only scripts and docs; keep `data/` and `outputs/` untracked.

## Relationship to Phase 3A

Phase 3A (ResNet-50) remains the reference for generic-baseline risk–coverage behavior. Phase 3B adds the wildlife-specialized baseline perspective. Cross-baseline conclusions should compare policy patterns and proxy counts, not absolute cosine values.
