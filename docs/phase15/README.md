# Phase 15: PF-ERI Evidence-Routed Review Layer

Phase 15 contains the active query-level retrieval, routing, and calibrated
ranker work.

Core outputs are stored under:

```text
outputs/phase15/
```

Current interpretation:

- descriptor-only MegaDescriptor is a strong baseline;
- hand-written PF-ERI/quality gates are not enough;
- calibrated nonlinear rankers show modest held-out mid-k improvement;
- repeated query-split validation shows strong model-level signal but modest
  top-k queue gains;
- the strongest current claim is risk-aware review routing and evidence
  diagnosis, not a breakthrough Re-ID accuracy improvement.
- Phase 15D now exports the first operational five-action review routing table:
  accept, review, defer, species-level only, and non-comparable.
- Phase 15E applies the CzechLynx-calibrated policy to bobcat as a
  wild-to-urban transfer stress test without bobcat identity-accuracy claims.
- Phase 15F packages a 250-pair bobcat manual audit set to validate
  review-routing actions and pair comparability.
- Phase 16 is the next PF-ERI modeling phase, with data-governance safeguards
  for laterality-aware sampling/pair audit, background/site leakage-pressure
  diagnostics, and strong-model benchmark preparation.

Output structure:

- `outputs/phase15/query_level_benchmark/`
- `outputs/phase15/hybrid_routing_policy/`
- `outputs/phase15/colab_ranker_package/`
- `outputs/phase15/calibrated_ranker_results/`
- `outputs/phase15/repeated_ranker_validation/`
- `outputs/phase15/evidence_routed_review_policy/`
- `outputs/phase15/wild_urban_transfer_stress/`
- `outputs/phase15/bobcat_pair_audit_package/`

Key documents:

- `pf_eri_project_content_book_cn.md`
- `pf_eri_project_content_book_en.md`
- `pf_eri_expert_brief_bilingual.md`
- `phase15_calibrated_ranker_result_analysis_cn.md`
- `phase15c_repeated_ranker_validation_analysis_cn.md`
- `phase15c_method_literature_note.md`
- `phase15d_evidence_routed_review_policy_analysis_cn.md`
- `phase15e_wild_urban_transfer_stress_analysis_cn.md`
- `phase15f_bobcat_pair_audit_package_analysis_cn.md`
