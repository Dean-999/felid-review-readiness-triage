# Phase 8 Slice 3F Downstream Ecological Sensitivity Simulation Results

## Phase 9 Supersession Note

This document remains the correct boundary for downstream sensitivity claims. It supports simulated CzechLynx identity-record contamination-pressure reduction under conservative assumptions, not ecological estimation or deployment. Phase 9 treats this as application-value evidence for PF-ERI utility signals, while the next technical test is PF-ERI-aware fixed-descriptor reranking.

## 1. Purpose

Slice 3F implements a conservative CzechLynx downstream identity-record contamination sensitivity simulation. It tests whether PF-ERI's supported false-candidate burden reduction could reduce simulated downstream contamination pressure.

## 2. Post-3E-R Rationale

Slice 3E-R showed that held-out fixed-descriptor Re-ID accuracy improvement was not robust. The supported value entering this slice is false-candidate review-burden reduction, not improved identity discrimination.

## 3. Sensitivity Simulation Boundary

This is a sensitivity simulation, not ecological estimation. PF-ERI is not a Re-ID model. It does not estimate abundance, occupancy, survival, movement, or population size. It does not claim field deployment readiness and does not identify true individual animals.

## 4. Input Inventory

Inspected inputs: `13`.

Missing inputs: `0`.

## 5. Policies Compared

- `raw_megadescriptor_topk`: raw fixed-descriptor review baseline.
- `review_top1_only`: raw top-1 sensitivity baseline.
- `candidate_f`: review-control reference.
- `v4_0636`: operational refinement reference.
- `strict_pf_eri_reference`: strict confidence-control reference.
- random same-size controls for PF-ERI policies.

## 6. Candidate Truth Mapping

Candidate truth was mapped internally using CzechLynx working identities:

```text
true candidate = query and candidate share the same working identity
false candidate = query and candidate have different working identities
```

Identity labels were used only for validation/simulation truth. No raw paths, original IDs, working IDs, locations, trap IDs, GPS fields, raw dates, or per-identity histories are exported.

## 7. Reviewer False-Acceptance Assumption Grid

False-acceptance rates:

```text
0.05, 0.10, 0.20, 0.30, 0.50
```

These are not measured human behavior. They are sensitivity assumptions.

## 8. Random Same-Size Control Design

Random same-size controls were generated per PF-ERI policy by matching each policy's reviewed-candidate count per query. Random repeats: `500`.

## 9. Primary Metrics and Formulas

```text
false_candidate_burden = false_reviewed_candidates / covered query universe
expected_false_accepts = false_reviewed_candidates * false_accept_rate
simulated_identity_record_contamination_rate = expected_false_accepts / reviewed_candidates
risk_reduction_per_evidence_removed =
  (false_burden_raw - false_burden_policy) /
  max(1, raw_reviewed_candidates - policy_reviewed_candidates)
```

False merge proxy is the expected accepted false candidate links connecting different working identities. It is a proxy, not a field ecological rate.

## 10. Main Contamination Results

| policy_id | false_candidate_burden | reviewed_candidates | false_reviewed_candidates | query_coverage | positive_retention | candidate_retention | risk_reduction_per_evidence_removed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| raw_megadescriptor_topk | 4.722 | 2500 | 2361 | 1.0 | 1.0 | 1.0 |  |
| review_top1_only | 0.902 | 500 | 451 | 1.0 | 1.0 | 1.0 | 0.0019 |
| candidate_f | 2.888 | 1535 | 1444 | 0.72 | 0.6547 | 0.614 | 0.0019 |
| v4_0636 | 1.592 | 874 | 796 | 0.616 | 0.5612 | 0.3496 | 0.0019 |
| strict_pf_eri_reference | 0.224 | 150 | 112 | 0.25 | 0.3423 | 0.1 | 0.0019 |

## 11. Random Baseline Comparison

| target_policy_id | random_repeat_count | random_mean | random_p05 | random_p50 | random_p95 | policy_value | policy_minus_random_mean | better_than_random_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| candidate_f | 500 | 2.8923 | 2.884 | 2.892 | 2.902 | 2.888 | -0.0043 | yes |
| strict_pf_eri_reference | 500 | 0.2716 | 0.262 | 0.272 | 0.28 | 0.224 | -0.0476 | yes |
| v4_0636 | 500 | 1.6227 | 1.61 | 1.622 | 1.6341 | 1.592 | -0.0307 | yes |

## 12. Candidate F Interpretation

| policy_id | false_candidate_burden | reviewed_candidates | query_coverage | positive_retention | candidate_retention |
| --- | --- | --- | --- | --- | --- |
| candidate_f | 2.888 | 1535 | 0.72 | 0.6547 | 0.614 |

Candidate F remains the review-control reference because it preserves stronger coverage and positive retention. It should not be described as a Re-ID accuracy-improvement policy.

## 13. v4_0636 Interpretation

| policy_id | false_candidate_burden | reviewed_candidates | query_coverage | positive_retention | candidate_retention |
| --- | --- | --- | --- | --- | --- |
| v4_0636 | 1.592 | 874 | 0.616 | 0.5612 | 0.3496 |

`v4_0636` is the operational refinement reference. Lower contamination pressure must be interpreted with its lower positive-retention and coverage tradeoff.

## 14. Strict PF-ERI Reference Interpretation

| policy_id | false_candidate_burden | reviewed_candidates | query_coverage | positive_retention | candidate_retention |
| --- | --- | --- | --- | --- | --- |
| strict_pf_eri_reference | 0.224 | 150 | 0.25 | 0.3423 | 0.1 |

The strict PF-ERI reference is a confidence-control sensitivity layer, not the main operating policy.

## 15. Utility Policy Interpretation

Utility policies were not promoted as final policies in this slice. They remain sensitivity layers only, not identity scores or safety scores.

## 16. Whether PF-ERI Reduces Simulated Downstream Contamination Pressure

Decision:

```text
yes
```

| policy_id | false_candidate_burden | false_candidate_burden_reduction_vs_raw | beats_random_same_size_on_false_burden | query_coverage | positive_retention | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| candidate_f | 2.888 | 1.834 | yes | 0.72 | 0.6547 | lower_contamination_pressure_with_retention_tradeoff |
| v4_0636 | 1.592 | 3.13 | yes | 0.616 | 0.5612 | lower_contamination_pressure_with_retention_tradeoff |
| strict_pf_eri_reference | 0.224 | 4.498 | yes | 0.25 | 0.3423 | lower_contamination_pressure_with_retention_tradeoff |

## 17. Coverage and Positive-Retention Tradeoffs

Coverage and positive retention are reported beside all contamination metrics. Policies with lower contamination pressure but low positive retention should be interpreted as confidence-control or workload-control references rather than replacements for review-control policy.

## 18. Limitations

- CzechLynx-only sensitivity simulation.
- Reviewer false-acceptance rates are assumptions, not measured human behavior.
- No site-use, movement, occupancy, abundance, survival, or population metrics are estimated.
- Random same-size controls reduce easier-workload artifacts but do not provide external validation.
- Identity labels are internal validation labels only.

## 19. Claims Supported

If the decision above is `yes`, Slice 3F supports this bounded claim:

```text
PF-ERI false-candidate burden reduction can reduce simulated downstream identity-record contamination pressure in CzechLynx under conservative sensitivity assumptions.
```

## 20. Claims Forbidden

- Do not claim PF-ERI estimates population size.
- Do not claim PF-ERI improves occupancy, abundance, survival, movement, or field ecological estimates.
- Do not claim PF-ERI identifies true individual animals.
- Do not claim PF-ERI is ready for field deployment.
- Do not claim PF-ERI is validated across felids.
- Do not claim PF-ERI is validated for Mainland Clouded Leopard or Marbled Cat.
- Do not claim PF-ERI is a new Re-ID model.
- Do not claim PF-ERI robustly improves fixed-descriptor Re-ID accuracy.

## 21. Recommended Next Step

manuscript_integration_with_conservative_claims

## 22. Confirmation

No training, no external data download, no frozen-data edit, no staging, and no commit were performed.
