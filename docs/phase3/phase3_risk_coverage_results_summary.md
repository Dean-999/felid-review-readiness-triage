# Phase 3 Risk–Coverage Results Summary

## Project Context

This project evaluates whether felid camera-trap images are reliable enough to enter individual-level Re-ID review.

The project does not identify individual animals directly. It does not train a new Re-ID model. Instead, it tests whether a review-readiness gate can help control the trade-off between retaining useful matching evidence and reducing pairwise false-positive proxy risk.

Phase 3 uses the Phase 2 pairwise cosine similarity outputs from a fixed generic ResNet-50 ImageNet embedding baseline. These similarities are treated as measurement signals for evaluating review-readiness behavior, not as final animal-identification decisions.

## Phase 3 Question

Phase 3 addresses Q2:

> After filtering low-readiness images, does pairwise false-match risk proxy decrease, and how much known matching evidence is lost?

The analysis compares three policy settings:

1. **No filter** — all images and pairs are retained.
2. **Balanced filter** — `review-ready` and `review-limited` images are retained; `unidentifiable` images are excluded.
3. **Strict filter** — only `review-ready` images are retained.

## Inputs

The analysis used:

- `data/interim/czechlynx/czechlynx_pair_similarities.csv`
- `data/interim/czechlynx/czechlynx_pilot_pairs.csv`
- `data/interim/czechlynx/czechlynx_pilot_validation_table.csv`

Input summary:

| Item | Count |
|---|---:|
| Total pair rows | 400 |
| Same-individual pairs | 100 |
| Different-individual pairs | 300 |
| Validation-table images | 200 |
| Unique working individual IDs | 100 |

## Policy Definitions

### No Filter

All candidate pairs and images are retained.

This policy preserves maximum evidence but also keeps all low-readiness and noisy image pairs.

### Balanced Filter

Pairs are retained when both images are either `review-ready` or `review-limited`.

This policy excludes `unidentifiable` images while keeping partially usable review-limited material.

### Strict Filter

Pairs are retained only when both images are `review-ready`.

This policy keeps only the highest-confidence review subset but discards most available evidence.

## Policy Comparison Results

| Policy | Retained Pairs | Retained Pair Rate | Retained Images | Retained Image Rate | Retained IDs | Retained Same Pairs | Retained Same-Pair Rate | Same Mean | Different Mean | Mean Gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| No filter | 400 | 100.0% | 200 | 100.0% | 100 | 100 | 100.0% | 0.579955 | 0.493990 | 0.085966 |
| Balanced filter | 212 | 53.0% | 141 | 70.5% | 86 | 55 | 55.0% | 0.682978 | 0.626315 | 0.056663 |
| Strict filter | 10 | 2.5% | 34 | 17.0% | 31 | 3 | 3.0% | 0.852984 | 0.733605 | 0.119379 |

## Threshold Proxy Results

The following thresholds were inherited from the Phase 2 quantile-based threshold proxy summary. These thresholds are pilot-specific and model-specific. They are not universal Re-ID thresholds.

| Policy | Threshold | True-Positive Proxy Count | False-Positive Proxy Count |
|---|---:|---:|---:|
| No filter | 0.547081 | 60 | 140 |
| No filter | 0.680093 | 34 | 66 |
| No filter | 0.770424 | 22 | 18 |
| No filter | 0.808955 | 14 | 6 |
| Balanced filter | 0.547081 | 44 | 119 |
| Balanced filter | 0.680093 | 27 | 61 |
| Balanced filter | 0.770424 | 19 | 17 |
| Balanced filter | 0.808955 | 12 | 6 |
| Strict filter | 0.547081 | 3 | 7 |
| Strict filter | 0.680093 | 3 | 6 |
| Strict filter | 0.770424 | 3 | 3 |
| Strict filter | 0.808955 | 2 | 1 |

## Main Interpretation

Phase 3 shows a clear risk–coverage trade-off.

The **strict filter** reduces pairwise false-positive proxy counts most strongly, but it also removes most known matching evidence. It retains only:

- 17.0% of images;
- 31.0% of unique working individual IDs;
- 3.0% of same-individual pairs;
- 2.5% of all candidate pairs.

This makes the strict policy useful as a high-confidence review subset, but too evidence-losing to serve as the only general workflow policy in this pilot.

The **balanced filter** preserves substantially more ecological and matching coverage. It retains:

- 70.5% of images;
- 86.0% of unique working individual IDs;
- 55.0% of same-individual pairs;
- 53.0% of all candidate pairs.

However, the balanced filter only weakly reduces false-positive proxy counts at higher thresholds. For example, at threshold `0.770424`, the false-positive proxy count decreases only from 18 to 17. At threshold `0.808955`, it remains 6.

Therefore, balanced filtering is better interpreted as an evidence-preserving cleanup policy rather than a strong risk-reduction policy.

The **no-filter policy** retains all evidence, but it also keeps all low-readiness and noisy image pairs. It is useful as a baseline condition but not as a practical review-control strategy.

## Answer to Q2

The pilot supports the existence of a risk–coverage trade-off.

Filtering low-readiness images can reduce pairwise false-positive proxy counts, especially under the strict review-ready-only policy. However, the strict policy achieves this reduction by discarding nearly all same-individual matching evidence. The balanced policy preserves much more image, identity, and same-pair coverage, but it does not strongly reduce high-threshold false-positive proxy counts.

The most defensible interpretation is that review-readiness should be used as a **tiered workflow control variable**, not as a single hard filter.

A practical workflow would be:

1. `review-ready` images enter high-confidence candidate Re-ID review.
2. `review-limited` images enter secondary or cautious manual review.
3. `unidentifiable` images are excluded from individual-level Re-ID review.

## Relationship to Phase 2

Phase 2 showed weak-to-moderate same/different separation under a fixed generic ResNet-50 ImageNet embedding baseline. The overall ROC-AUC was `0.618667`, and the overall same-minus-different mean cosine similarity gap was `0.085966`.

The `ready_ready` group showed a positive signal, with a mean gap of `0.119379`, but it had sparse pair counts: 3 same-individual pairs and 7 different-individual pairs. This limited the strength of any direct claim about review-ready superiority.

Phase 3 extends this finding by showing that strict filtering can reduce proxy risk, but with substantial evidence loss. This supports the project’s central framing: review-readiness is useful as a reliability and workflow-control signal, but it should be evaluated through both risk reduction and evidence retention.

## Recommended Policy Interpretation

### Best General Interpretation

The best general interpretation is a **tiered review policy**.

The strict filter is too conservative for general use because it retains only 3% of known same-individual pairs. The balanced filter retains much more identity and same-pair coverage but does not substantially reduce high-threshold false-positive proxy. Therefore, the workflow should not treat `review-ready` as the only usable class.

Instead, the triage categories should define different levels of review confidence:

| Triage Label | Recommended Role |
|---|---|
| `review-ready` | High-confidence candidate review |
| `review-limited` | Secondary or cautious manual review |
| `unidentifiable` | Excluded from individual-level Re-ID review |

### Why Strict Filter Is Not Sufficient Alone

The strict filter produces the strongest proxy risk reduction, but it also removes nearly all same-pair evidence. In conservation monitoring, losing too much matching evidence can reduce the usefulness of the review process, especially when data are already sparse.

### Why Balanced Filter Is Not a Complete Solution

The balanced filter preserves more evidence but only weakly reduces high-threshold false-positive proxy counts. This means it should not be described as a strong risk-reduction method. Its main value is preserving usable evidence while removing the least reliable images.

## Limitations

This Phase 3 analysis has several limitations:

1. The analysis is pilot-level and uses only 200 images.
2. The embedding baseline is a fixed generic ResNet-50 ImageNet model, not a wildlife-specialized Re-ID model.
3. No model training or fine-tuning was performed.
4. Similarity scores are measurement signals, not true identity decisions.
5. False-positive counts are pairwise proxy counts, not real-world false-match rates.
6. Thresholds are pilot-specific and model-specific.
7. The strict policy has very sparse retained same-pair evidence.
8. The balanced policy may retain many difficult review-limited cases.
9. This analysis does not establish field deployment readiness.
10. This analysis does not define universal felid Re-ID thresholds.

## What This Analysis Can Support

This analysis can support the following cautious statement:

> In the CzechLynx pilot, review-readiness filtering created a measurable risk–coverage trade-off under a fixed generic ResNet-50 embedding baseline. A strict review-ready-only policy reduced pairwise false-positive proxy counts but discarded most known matching evidence, while a balanced policy preserved more evidence but reduced proxy risk only weakly. These findings support using review-readiness as a tiered workflow-control signal rather than as a single hard filter.

## What This Analysis Cannot Claim

This analysis cannot claim:

- that the project identifies individual animals;
- that ResNet-50 is an effective lynx Re-ID model;
- that the thresholds are universal;
- that pairwise proxy counts are real-world false-match rates;
- that strict filtering is always best;
- that the workflow is ready for field deployment;
- that the result generalizes to all felids or all camera-trap datasets.

## Phase 3 Decision

Phase 3 is complete for the current CzechLynx pilot.

The result supports moving toward a mentor-facing technical report and a paper-style project draft, with conservative interpretation. The main finding should be framed as a risk–coverage trade-off rather than a final proof of review-ready superiority.

## Next Steps

1. Create a mentor-facing results update summarizing Phase 1, Phase 2, and Phase 3.
2. Update the daily work log for 2026-06-05.
3. Begin a paper-style project report draft.
4. Consider whether to run a wildlife-specialized embedding baseline later, such as a MegaDescriptor/WildlifeDatasets-based model, as a comparison baseline.
5. Preserve all current generated outputs locally, but do not commit `data/` or `outputs/` to Git.