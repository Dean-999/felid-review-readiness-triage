# Phase 8 Index

Phase 8 tested PF-ERI around fixed-descriptor retrieval behavior. It is the main evidence chain showing that simple hard filtering was not enough for robust retrieval accuracy improvement, but PF-ERI did reduce false-candidate burden and supported downstream contamination sensitivity analysis.

## Read Order

Start with:

1. `phase8_results_digest.md`
2. `phase8_claim_boundary_digest.md`

Then read the original slice sequence when details are needed:

1. `phase8_slice1_czechlynx_retrieval_benchmark_results.md`
2. `phase8_slice2_czechlynx_full_retrieval_benchmark_results.md`
3. `phase8_slice2b_full_retrieval_failure_diagnosis_and_pf_eri_control_results.md`
4. `phase8_slice3a_pf_eri_retrieval_control_v2_results.md`
5. `phase8_slice3b_descriptor_disagreement_false_neighbor_confidence_control_results.md`
6. `phase8_slice3c_utility_constrained_pf_eri_policy_selection_results.md`
7. `phase8_slice3d_pf_eri_deep_algorithm_v4_results.md`
8. `phase8_slice3e_query_level_calibration_evaluation_results.md`
9. `phase8_slice3e_reid_accuracy_evidence_selection_results.md`
10. `phase8_post_3e_r_interpretation_and_claim_revision.md`
11. `phase8_slice3f_downstream_ecological_sensitivity_simulation_results.md`

## Key Interpretation

Phase 8 should not be read as a failed endpoint. It established three important boundaries:

1. simple PF-ERI hard filtering was too blunt for robust fixed-descriptor mAP improvement;
2. PF-ERI reduced false-candidate burden under CzechLynx held-out query evaluation;
3. downstream sensitivity simulation gave application-value support, but not population, movement, occupancy, survival, or field-deployment evidence.

These results motivate the current Phase 12 direction:

```text
pair-level evidence admissibility + descriptor-evidence conflict + reliability-aware metric learning
```

## Slice Map

| Slice | Role | Current use |
|---|---|---|
| Slice 1 | sampled candidate-pair retrieval benchmark | Historical baseline. |
| Slice 2 | full all-vs-all CzechLynx retrieval benchmark | Fixed descriptor behavior baseline. |
| Slice 2B | failure diagnosis and PF-ERI control | Failure-mode evidence. |
| Slice 3A | PF-ERI retrieval-control v2 | Candidate assignment foundation. |
| Slice 3B | descriptor disagreement and false-neighbor control | Direct precursor to descriptor-evidence conflict. |
| Slice 3C | utility-constrained policy selection | Risk/coverage policy foundation. |
| Slice 3D | algorithm review and v4 redesign | Stronger candidate scoring attempt. |
| Slice 3E | query-level calibration and evidence-selection evaluation | Main claim-boundary evidence. |
| Slice 3F | downstream ecological sensitivity simulation | Application-value layer, not main algorithm. |

## Cleanup Recommendation

Keep all result docs. The first-pass digest files now exist:

- `phase8_results_digest.md`
- `phase8_claim_boundary_digest.md`

Older plan-only files were removed after their conclusions were merged into the digests. Main Phase 8 now keeps the digest, claim boundary, and active boundary result files.
