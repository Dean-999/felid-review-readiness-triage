# Phase 12C Confidence Evidence and Literature Grounding

Date: 2026-06-17

Purpose: convert Phase 12A/12B results into defensible, confidence-aware claims for RQ1-RQ4 planning.

## Evidence Standard

For this project, a claim is treated as strong only when it satisfies all four conditions:

1. It is measured on the 1000-image Phase 12A table, not the earlier 500-image aligned subset.
2. It is evaluated at split level or query level, not only as pooled candidate rows.
3. It includes a paired uncertainty estimate or a matched control.
4. Its interpretation is consistent with existing selective prediction, risk-control, and wildlife Re-ID literature.

## Literature Grounding

Selective classification and reject-option learning justify the use of risk-coverage curves rather than raw top-1 accuracy alone. Geifman and El-Yaniv framed deep selective classification as a system that can reject uncertain cases to meet a target risk level, explicitly trading coverage for lower error. This supports RQ3's risk-coverage design.

Conformal risk control extends conformal prediction to control expected monotone losses. The current PF-ERI system is not yet a conformal guarantee, but the literature supports the direction: calibration/held-out risk control should be the future target if PF-ERI thresholds are used in conservation decision workflows.

WildlifeDatasets and MegaDescriptor establish fixed wildlife Re-ID descriptors as a valid baseline substrate. This supports the decision to treat MegaDescriptor as a fixed descriptor and ask whether PF-ERI improves evidence selection/reranking around it, rather than claiming PF-ERI is itself an identity-recognition model.

Recent animal Re-ID work highlights generalization, open-set behavior, and species/domain variation. This supports keeping singleton identities as realistic distractors and hard negatives, while reserving positive-pair learning for identities with at least two images.

## Strong Claims Supported Now

### Claim 1: PF-ERI candidate utility gives a stable but modest top-1 improvement over raw descriptor ranking.

Evidence source:

`outputs/czechlynx/phase12/rq_confidence_evidence/phase12c_top1_paired_confidence.csv`

Evaluation split-paired results:

| Descriptor | Method | Metric | Mean | 95% CI | Direction probability |
|---|---|---:|---:|---:|---:|
| MegaDescriptor | PF-ERI candidate utility | false top-1 risk reduction vs raw | 0.0105 | 0.0073 to 0.0135 | 1.000 |
| MegaDescriptor | PF-ERI candidate utility | true top-1 gain vs raw | 0.0105 | 0.0072 to 0.0135 | 1.000 |
| ResNet50 | PF-ERI candidate utility | false top-1 risk reduction vs raw | 0.0137 | 0.0104 to 0.0168 | 1.000 |
| ResNet50 | PF-ERI candidate utility | true top-1 gain vs raw | 0.0137 | 0.0103 to 0.0169 | 1.000 |

Interpretation:

This is the strongest current result. The effect is small in absolute size, but it is directionally stable across 20 held-out split comparisons. The correct wording is:

> PF-ERI candidate utility produced a small but split-stable reduction in false top-1 burden compared with raw descriptor ranking.

Avoid wording:

> PF-ERI substantially improves Re-ID accuracy.

### Claim 2: Quality-only reranking is not enough.

Evidence source:

`outputs/czechlynx/phase12/rq_confidence_evidence/phase12c_top1_paired_confidence.csv`

Evaluation results:

| Descriptor | Method | False top-1 risk reduction vs raw | 95% CI | Direction probability |
|---|---|---:|---:|---:|
| MegaDescriptor | quality-only | -0.0011 | -0.0022 to 0.0000 | 0.028 |
| ResNet50 | quality-only | -0.0080 | -0.0097 to -0.0064 | 0.000 |

Interpretation:

Quality-only reranking is weak or harmful relative to raw ranking. This supports the claim that the useful signal is not generic image quality alone; it depends on candidate-level utility combining descriptor and evidence information.

### Claim 3: PF-ERI candidate utility reduces top-5 false burden slightly while retaining or improving positive-present@5.

Evidence source:

`outputs/czechlynx/phase12/rq_confidence_evidence/phase12c_topk_false_burden_positive_retention.csv`

Evaluation mean results:

| Descriptor | Method | False candidates per query @5 | Positive-present@5 | Hard negatives per query @5 |
|---|---|---:|---:|---:|
| MegaDescriptor | raw descriptor | 4.664 | 0.253 | 0.070 |
| MegaDescriptor | PF-ERI candidate utility | 4.647 | 0.256 | 0.057 |
| ResNet50 | raw descriptor | 4.708 | 0.218 | 0.000 |
| ResNet50 | PF-ERI candidate utility | 4.691 | 0.236 | 0.000 |

Interpretation:

The top-5 result is consistent with the top-1 result: not a large gain, but a stable reduction in review burden with equal or better positive retention.

## Moderate Claims Supported Now

### Claim 4: Reliability thresholding is useful for controlling hard-negative evidence, but can remove positives too aggressively.

Evidence source:

`outputs/czechlynx/phase12/rq_confidence_evidence/phase12c_reliability_threshold_curve.csv`

Evaluation mean results:

| Descriptor | Reliability threshold | Query coverage | Positive retention | False retention | Hard-negative retention |
|---|---:|---:|---:|---:|---:|
| MegaDescriptor | >=0.25 | 0.932 | 0.897 | 0.890 | 0.745 |
| MegaDescriptor | >=0.50 | 0.740 | 0.650 | 0.642 | 0.000 |
| MegaDescriptor | >=0.75 | 0.247 | 0.131 | 0.127 | 0.000 |

Interpretation:

Reliability thresholding is not a simple free improvement. It can eliminate hard negatives at moderate thresholds, but it also drops many positives and queries. This supports a risk-constrained review policy, not a hard deletion policy.

## Claims That Need Rewriting

### RQ1 should not be framed as "PF-ERI admissibility bands predict false candidates" using pooled candidate false rate.

Reason:

Top-20 candidate pools are dominated by different-identity candidates, so pooled false-candidate rate is heavily base-rate driven. High and unusable admissibility bands can both show false rates near 0.97. This does not mean PF-ERI has no signal; it means the pooled row-level false-rate endpoint is the wrong primary endpoint.

Better RQ1 framing:

> Do PF-ERI scores identify candidate comparisons whose use changes review burden, hard-negative exposure, and positive retention under query-level selection policies?

### RQ2 should be framed as hard-negative/conflict enrichment, not broad false-candidate explanation.

Reason:

The high-similarity/low-admissibility conflict group is rare. It does not explain most false candidates. But for MegaDescriptor, conflict captures the hard-negative candidates by construction in the current table:

`hard_negative_candidates` conflict-rate = 1.000, mean conflict score = 0.673.

Better RQ2 framing:

> Do descriptor-evidence conflicts isolate a small, high-risk hard-negative subset that raw descriptor ranking alone cannot distinguish?

## Recommended RQ Updates

### RQ1 Revised

Can PF-ERI evidence utility identify candidate comparisons that should be reviewed, deferred, or downweighted by improving query-level review burden and positive retention relative to quality-only filtering?

Primary endpoints:

- positive-present@5;
- false candidates per query@5;
- hard negatives per query@5;
- query coverage under reliability thresholds.

### RQ2 Revised

Do high-descriptor, low-admissibility conflicts isolate a distinct hard-negative failure mode in patterned-felid Re-ID?

Primary endpoints:

- conflict enrichment among hard negatives;
- conflict score distribution across same-identity, false-candidate, and high-similarity groups;
- raw top-1 vs PF-ERI top-1 conflict exposure.

### RQ3 Revised

Can PF-ERI candidate utility improve risk-coverage tradeoffs compared with raw descriptor ranking and quality-only reranking?

Primary endpoints:

- split-paired false top-1 risk reduction;
- top-5 false burden;
- positive-present@5;
- random top-20 control.

### RQ4 Revised

Can PF-ERI-conditioned pair weights improve metric learning when positive-pair supervision is restricted to identities with at least two images and singleton identities are used only as distractors/hard negatives?

Primary endpoints:

- held-out top-1 and mAP;
- false top-1 burden;
- hard-negative exposure;
- positive-pair retention by reliability band.

## Current Confidence Map

| Claim | Confidence | Reason |
|---|---|---|
| PF-ERI candidate utility improves top-1 risk vs raw | High | 20 split-paired comparisons, 95% CI above zero for both descriptors |
| PF-ERI improvement is large | Low | Effect size is about 1.0-1.4 percentage points |
| Quality-only is sufficient | Low | quality-only is weak or harmful, especially ResNet50 |
| Reliability threshold alone is sufficient | Low | thresholding drops positives and query coverage |
| Conflict explains most false candidates | Low | conflict group is rare |
| Conflict isolates hard-negative mode | Moderate to high for MegaDescriptor | hard-negative conflict-rate is 1.000 in current operational definition |
| RQ4 can use all identities as positives | Low | singleton identities lack positive pairs |

## Next Technical Step

Proceed to Phase 12D:

1. Build revised RQ1/RQ2 query-level tables using the Phase 12C endpoints.
2. Produce publication-ready figures:
   - paired top-1 risk reduction with CI;
   - top-5 false burden and positive-present@5;
   - reliability threshold retention curve;
   - conflict enrichment bar chart.
3. Update the paper draft with cautious, confidence-mapped claims.

## References

- Geifman, Y. and El-Yaniv, R. Selective Classification for Deep Neural Networks. arXiv:1705.08500.
- Angelopoulos, A. N., Bates, S., Fisch, A., Lei, L. and Schuster, T. Conformal Risk Control. arXiv:2208.02814.
- Cermak, V., Picek, L., Adam, L. and Papafitsoros, K. WildlifeDatasets: An open-source toolkit for animal re-identification. arXiv:2311.09118.
- Adam, L., Cermak, V., Papafitsoros, K. and Picek, L. WildlifeReID-10k: Wildlife re-identification dataset with 10k individual animals. arXiv:2406.09211.
- Hou, S. et al. OpenAnimals: Revisiting Person Re-Identification for Animals Towards Better Generalization. arXiv:2410.00204.
