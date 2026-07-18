# Modeling Validation

> **Historical v1 modeling archive.** The documents and PASS-like labels in this folder describe exploratory material and do not establish a PF-ERI v2 result. Use `PROJECT_RULES.md`, `docs/CURRENT_PROJECT_MAP.md`, and `docs/project-governance/workstreams/` for current scientific status and execution.

This folder contains modeling, strong-baseline, and identity-balanced
validation documentation.

Current project-level positioning documents:

- `2026-07-08_final_modeling_freeze.md`: final modeling scope, allowed claims,
  blocked claims, and paper-ready artifact map.
- `2026-07-09_pair_level_evidence_admission_review.md`: field-need and
  positioning review for the core claim that similarity is not admissibility.
- `2026-07-09_story_adversarial_review_and_hardening_plan.md`: adversarial
  story review, scorecard, and hardening plan for the non-full-score dimensions.
- `2026-07-09_manuscript_evidence_chain_outline.md`: Issue 1 manuscript
  evidence-chain outline and Figure 1 concept for the pair-level evidence
  admission story.
- `2026-07-09_contribution_hierarchy_related_work_distinction.md`: Issue 2
  contribution hierarchy and related-work distinction table protecting PF-ERI
  from being framed as a descriptor, quality filter, or generic uncertainty
  wrapper.
- `2026-07-09_core_incremental_model_evidence.md`: Issue 3 paper-ready
  incremental model evidence showing pooled and descriptor-specific
  reviewability/admissibility comparisons for descriptor-only, quality-only,
  PF-ERI-only, descriptor-plus-quality, descriptor-plus-PF-ERI, and full
  active-control models.
- `2026-07-09_quality_similarity_sensitivity.md`: Issue 4 quality and
  descriptor-similarity sensitivity package testing whether PF-ERI remains
  aligned with reviewability inside quality-matched, high-quality-only,
  high-similarity-only, and rank/similarity-stratified conditions.
- `2026-07-09_review_budget_routing_value.md`: Issue 5 fixed-budget review
  utility report comparing PF-ERI-prioritized review against descriptor-priority
  review as pre-review evidence hygiene rather than identity accuracy.
- `2026-07-09_pre_inference_evidence_hygiene_simulation.md`: Issue 6
  CzechLynx pre-inference evidence hygiene simulation separating admitted and
  deferred candidate pairs before expert review or downstream inference.
- `2026-07-09_results_evidence_ladder.md`: Issue 7 manuscript results order
  that replaces phase chronology with an inference ladder from construct
  validity to Bobcat transfer-stress boundaries.
- `2026-07-09_reviewer_objection_matrix_and_claim_gate.md`: Issue 8
  rebuttal-ready objection matrix and claim gate mapping reviewer challenges to
  main evidence, appendix sensitivity, or blocked-claim boundaries.
- `2026-07-09_final_story_consistency_audit.md`: Issue 9 final consistency
  audit confirming the claim-bearing layer preserves `Similarity is not
  admissibility` and blocks descriptor, identity, Bobcat-accuracy, and generic
  tool-stack overclaims.

Current contents:

```text
learned-utility-diagnostics/
pair-level-validation/
```

`learned-utility-diagnostics/` is historical diagnostic rationale. The active
modeling and pair-level validation entry point is `pair-level-validation/`.
