# Final Story Consistency Audit

Date: 2026-07-09

Status: `STORY_HARDENING_ISSUE9_COMPLETE`

Parent issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Generated artifacts:

```text
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue9/issue9_story_consistency_findings.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue9/issue9_story_consistency_audit.json
```

## Purpose

This document completes the final story consistency audit for the story
hardening issue pack. The audit checks whether the project-facing and
manuscript-facing claim layers preserve the same scientific line:

```text
Similarity is not admissibility.
PF-ERI is pair-level evidence admission after descriptor retrieval.
```

The audit is intentionally conservative. It searches for language that could
reframe PF-ERI as a descriptor, automatic identity system, Bobcat identity
validation, universal ranking improvement, generic conformal/Bayesian wrapper,
or generic classifier. Each flagged line is classified as a safe boundary, a
manual-review item, or an unsafe positive claim.

## Audit Result

The final gate status is `PASS`. The audit found
0 unsafe positive claim lines,
12 manual-review lines, and
95 safe boundary lines. Manual-review lines are not
claim failures; they are lines where a risk phrase appears without an automatic
negation marker and should be read in context. No current unsafe positive claim
is allowed to remain in the claim-bearing layer.

## Files Checked

- `PROJECT_RULES.md`
- `README.md`
- `docs/CURRENT_PROJECT_MAP.md`
- `docs/modeling-validation/README.md`
- `docs/modeling-validation/2026-07-08_final_modeling_freeze.md`
- `docs/modeling-validation/2026-07-09_pair_level_evidence_admission_review.md`
- `docs/modeling-validation/2026-07-09_story_adversarial_review_and_hardening_plan.md`
- `docs/modeling-validation/2026-07-09_manuscript_evidence_chain_outline.md`
- `docs/modeling-validation/2026-07-09_contribution_hierarchy_related_work_distinction.md`
- `docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md`
- `docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md`
- `docs/modeling-validation/2026-07-09_review_budget_routing_value.md`
- `docs/modeling-validation/2026-07-09_pre_inference_evidence_hygiene_simulation.md`
- `docs/modeling-validation/2026-07-09_results_evidence_ladder.md`
- `docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md`
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_claim_narrative.md`
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations.md`
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations_table.csv`
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/main_model_result_table.csv`
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/final_advanced_claim_gate_table.csv`
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/advanced_validation_claim_boundaries.csv`
- `archive/pferi_v1/outputs/modeling-validation/robustness-and-claim-gates/final_claim_gate_table.csv`

## Central Claim Presence

- `PROJECT_RULES.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `README.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `docs/CURRENT_PROJECT_MAP.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `docs/modeling-validation/README.md`: similarity_line=False, pair_level=True, post_retrieval=False
- `docs/modeling-validation/2026-07-08_final_modeling_freeze.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `docs/modeling-validation/2026-07-09_pair_level_evidence_admission_review.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `docs/modeling-validation/2026-07-09_story_adversarial_review_and_hardening_plan.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `docs/modeling-validation/2026-07-09_manuscript_evidence_chain_outline.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `docs/modeling-validation/2026-07-09_contribution_hierarchy_related_work_distinction.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md`: similarity_line=False, pair_level=True, post_retrieval=False
- `docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md`: similarity_line=False, pair_level=True, post_retrieval=False
- `docs/modeling-validation/2026-07-09_review_budget_routing_value.md`: similarity_line=False, pair_level=False, post_retrieval=False
- `docs/modeling-validation/2026-07-09_pre_inference_evidence_hygiene_simulation.md`: similarity_line=False, pair_level=True, post_retrieval=False
- `docs/modeling-validation/2026-07-09_results_evidence_ladder.md`: similarity_line=True, pair_level=True, post_retrieval=False
- `docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_claim_narrative.md`: similarity_line=True, pair_level=True, post_retrieval=True
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations.md`: similarity_line=False, pair_level=False, post_retrieval=False
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/final_confidence_limitations_table.csv`: similarity_line=False, pair_level=False, post_retrieval=False
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/paper-ready/main_model_result_table.csv`: similarity_line=False, pair_level=False, post_retrieval=False
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/final_advanced_claim_gate_table.csv`: similarity_line=False, pair_level=True, post_retrieval=True
- `archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation/advanced_validation_claim_boundaries.csv`: similarity_line=False, pair_level=True, post_retrieval=True
- `archive/pferi_v1/outputs/modeling-validation/robustness-and-claim-gates/final_claim_gate_table.csv`: similarity_line=False, pair_level=True, post_retrieval=True

## Risk Families Flagged

- `automatic_identity`: 31
- `bobcat_identity_accuracy`: 38
- `descriptor_replacement`: 24
- `ranking_overclaim`: 6
- `tool_stack_reframe`: 8

## Manual-Review Lines

- `PROJECT_RULES.md:929` `bobcat_identity_accuracy`: 4. Any final claim involving Bobcat identity accuracy, same-ID retention,
- `README.md:137` `ranking_overclaim`: than a broad Re-ID accuracy breakthrough.
- `README.md:142` `ranking_overclaim`: replacement or ranking-superiority.
- `docs/CURRENT_PROJECT_MAP.md:323` `descriptor_replacement`: - training a new descriptor as the main contribution;
- `docs/CURRENT_PROJECT_MAP.md:324` `automatic_identity`: - claiming automatic Bobcat individual recognition;
- `docs/modeling-validation/2026-07-08_final_modeling_freeze.md:70` `bobcat_identity_accuracy`: assignment or Bobcat identity accuracy.
- `docs/modeling-validation/2026-07-09_story_adversarial_review_and_hardening_plan.md:495` `bobcat_identity_accuracy`: - Bobcat identity accuracy;
- `docs/modeling-validation/2026-07-09_story_adversarial_review_and_hardening_plan.md:496` `descriptor_replacement`: - descriptor replacement;
- `docs/modeling-validation/2026-07-09_manuscript_evidence_chain_outline.md:177` `bobcat_identity_accuracy`: replacement, or Bobcat identity validation.
- `docs/modeling-validation/2026-07-09_contribution_hierarchy_related_work_distinction.md:73` `automatic_identity`: matching scores, top-k performance, and identity assignment. Those are the
- `docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md:38` `automatic_identity`: replacement, automatic identity assignment, Bobcat identity accuracy,
- `docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md:38` `bobcat_identity_accuracy`: replacement, automatic identity assignment, Bobcat identity accuracy,

## Edits Made

This pass adds the Issue 9 audit script, line-level findings table, JSON audit,
and this final consistency report. It also updates the project map,
modeling-validation README, daily log, and story hardening issue pack so Issue
9 is part of the active navigation layer. The scan did not require claim-text
repairs in the current claim-bearing documents because dangerous phrases are
already framed as blocked claims, caveats, or explicit boundaries.

## Remaining Boundaries

PF-ERI remains a post-retrieval pair-level evidence admission layer. It is not a
new descriptor, not an automatic identity-assignment system, not a Bobcat
identity-validation system, and not a generic conformal, Bayesian,
multi-annotator, or classifier method. The strongest positive claim remains
reviewability and evidential admissibility on the CzechLynx reviewed validation
contract, with Bobcat restricted to unlabeled transfer-stress and workflow
allocation unless audited Bobcat identity labels or same/different pair labels
are added later.

## Next Action

The story-hardening issue pack is complete. The next scientific step should be
manuscript assembly from the evidence chain, contribution hierarchy, results
evidence ladder, objection matrix, and final claim narrative. The next
engineering step should be a separate repository hygiene pass only if the user
wants staging, committing, or further cleanup.
