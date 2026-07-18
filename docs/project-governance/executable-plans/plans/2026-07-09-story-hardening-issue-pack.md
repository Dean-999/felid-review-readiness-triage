# Story Hardening Issue Pack

Date: 2026-07-09

Status: `APPROVED_EXECUTION_ISSUE_PACK`

Parent plan:

```text
docs/modeling-validation/2026-07-09_story_adversarial_review_and_hardening_plan.md
```

Goal:

```text
Harden the project story around the non-negotiable thesis that similarity is
not admissibility, and raise the non-full-score dimensions from the adversarial
review: field necessity, novelty protection, evidence strength, logic closure,
and reviewer resistance.
```

Execution rule:

- Complete issues in dependency order.
- Each issue must produce a reviewable artifact or result on its own.
- Do not introduce a new main claim. Every issue must support pair-level
  evidential admissibility after strong descriptor retrieval.
- Do not convert PF-ERI into a descriptor, identity classifier, generic
  conformal method, Bayesian method, or Bobcat identity-performance claim.

## Issue 1: Build Manuscript Evidence-Chain Outline

Status: `COMPLETE`

Completion artifact:

```text
docs/modeling-validation/2026-07-09_manuscript_evidence_chain_outline.md
```

## Parent

`Story Hardening Issue Pack`

## What to build

Create a manuscript-facing outline that makes the field need unavoidable from
the first paragraph. The outline must show that photographic wildlife Re-ID is
an evidence chain, not only a retrieval benchmark. It should move from
misidentification and unclassifiable evidence to descriptor candidate retrieval,
then to the missing pair-level evidence admission step, then to PF-ERI and
cautious ecological inference.

This issue is complete when the project has a durable manuscript outline and
Figure 1 concept that a reader can understand before seeing any model result.

## Acceptance criteria

- [x] The introduction outline follows this chain:
  `misidentification / unclassifiable evidence -> descriptor candidate retrieval -> missing pair-level evidence admission -> PF-ERI -> cautious ecological inference`.
- [x] Figure 1 concept includes:
  `image archive -> descriptor retrieval -> candidate pair queue -> PF-ERI evidence admission -> expert review -> cautious ecological inference`.
- [x] The outline explains why PF-ERI remains necessary even if future
  descriptors improve.
- [x] The outline does not frame the project as `PF-ERI catches descriptor
  failures`.
- [x] The artifact is linked from the modeling-validation README or current
  project map.

## Blocked by

None - can start immediately.

## Issue 2: Add Contribution Hierarchy And Related-Work Distinction

Status: `COMPLETE`

Completion artifact:

```text
docs/modeling-validation/2026-07-09_contribution_hierarchy_related_work_distinction.md
```

## Parent

`Story Hardening Issue Pack`

## What to build

Create a contribution hierarchy and related-work distinction table that protects
the novelty from becoming a mixture of generic methods. The hierarchy must make
pair-level evidential admissibility the primary contribution and place risk
routing, bootstrap uncertainty, reviewer reliability, review-budget routing,
Bayesian sensitivity, and conformal-style risk control as supporting safeguards.

The related-work table should distinguish PF-ERI from strong descriptors,
Wildbook/WBIA-style matching platforms, location-informed Re-ID, active
learning, selective classification, conformal risk control, image-quality
filtering, and multi-annotator models.

## Acceptance criteria

- [x] A `Contribution hierarchy` section or box exists in a durable document.
- [x] The primary contribution is stated as pair-level evidence admission for
  descriptor-retrieved wildlife Re-ID candidate pairs.
- [x] Supporting tools are explicitly labeled as safeguards rather than main
  novelty.
- [x] A related-work distinction table includes at least:
  `nearby work`, `what it optimizes`, `what it does not claim`, and
  `PF-ERI distinction`.
- [x] The document blocks the interpretation that PF-ERI is mainly a conformal
  classifier, Bayesian model, quality filter, descriptor, or identity model.

## Blocked by

- Issue 1: Build Manuscript Evidence-Chain Outline.

## Issue 3: Make Core Incremental Model Evidence Paper-Ready

Status: `COMPLETE`

Completion artifacts:

```text
docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue3/issue3_core_incremental_model_comparison.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue3/issue3_core_incremental_model_evidence_audit.json
```

## Parent

`Story Hardening Issue Pack`

## What to build

Produce the core paper-ready model comparison that tests whether PF-ERI adds
reviewability/admissibility signal beyond descriptor similarity and image
quality. The comparison must use identical row sets and report pooled plus
descriptor-specific results.

Required model families:

```text
descriptor only
quality only
PF-ERI evidence only
descriptor + quality
descriptor + PF-ERI
descriptor + quality + PF-ERI
```

This issue is complete when a reader can inspect one table and understand the
incremental evidence claim without reading the project history.

## Acceptance criteria

- [x] All compared models use identical row sets.
- [x] Output includes AUROC, AUPRC, Brier score, ECE or calibration diagnostic,
  and uncertainty intervals where estimable.
- [x] Results are reported both pooled and descriptor-specific for
  MegaDescriptor and DINOv2.
- [x] The paper-ready interpretation says reviewability/admissibility only.
- [x] The output explicitly blocks identity accuracy, mAP, MRR, and top-k
  identity-improvement claims.
- [x] The final table is linked from the story hardening or final claim
  narrative layer.

## Blocked by

- Issue 1: Build Manuscript Evidence-Chain Outline.

## Issue 4: Add Quality And Similarity Sensitivity Package

Status: `COMPLETE_PASS_WITH_BOUNDARIES`

Completion artifacts:

```text
docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_matched_sensitivity.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_quality_subset.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_similarity_subset.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_rank_similarity_stratified_sensitivity.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_similarity_sensitivity_audit.json
```

## Parent

`Story Hardening Issue Pack`

## What to build

Build the sensitivity package that answers the two strongest alternative
explanations:

```text
PF-ERI is just image quality.
PF-ERI is just descriptor similarity.
```

The package must test whether PF-ERI signal persists under quality-matched,
high-quality-only, high-similarity-only, and rank/similarity-stratified
conditions. If a condition weakens the signal, report it as a boundary rather
than hiding it.

## Acceptance criteria

- [x] Quality-matched sensitivity is produced or documented as not estimable
  with a clear reason.
- [x] High-quality-only subset analysis is produced.
- [x] High-similarity-only subset analysis is produced.
- [x] Rank-bin or similarity-bin stratified analysis is produced.
- [x] Each sensitivity output uses the same target definition:
  human reviewability / evidential admissibility.
- [x] The report states whether PF-ERI remains distinct from quality and
  similarity under each condition.
- [x] Any weak or non-estimable result is converted into a claim boundary, not
  a positive claim.

## Blocked by

- Issue 3: Make Core Incremental Model Evidence Paper-Ready.

## Issue 5: Turn Review-Budget Routing Into Applied Evidence Value

Status: `COMPLETE`

Completion artifacts:

```text
docs/modeling-validation/2026-07-09_review_budget_routing_value.md
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_fixed_budget_review_utility.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_fixed_budget_policy_delta.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/figure_issue5_review_budget_utility.svg
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_review_budget_value_audit.json
```

## Parent

`Story Hardening Issue Pack`

## What to build

Convert review-budget routing from a technical metric into a clear applied
evidence-value result. At fixed review budgets, compare PF-ERI-prioritized
review against descriptor-priority review and report whether PF-ERI reduces
not-ready/uncertain burden while preserving useful candidate coverage.

This is a workflow and evidence-hygiene claim. It must not become an identity
accuracy claim.

## Acceptance criteria

- [x] Fixed-budget tables or figures are produced for at least one meaningful
  review budget.
- [x] A descriptor-priority baseline is included.
- [x] Output reports empirical risk or predicted risk, admitted/reviewed count,
  and not-ready/uncertain burden.
- [x] Where known-ID labels are available, output reports same-ID candidate
  retention or coverage as a secondary utility measure.
- [x] The interpretation is framed as pre-review evidence hygiene.
- [x] Bobcat identity accuracy and top-k identity claims remain blocked.

## Blocked by

- Issue 3: Make Core Incremental Model Evidence Paper-Ready.

## Issue 6: Build CzechLynx Pre-Inference Evidence Hygiene Simulation

Status: `COMPLETE`

Completion artifacts:

```text
docs/modeling-validation/2026-07-09_pre_inference_evidence_hygiene_simulation.md
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6/issue6_pre_inference_evidence_hygiene_pairs.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6/issue6_pre_inference_evidence_hygiene_summary.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue6/issue6_pre_inference_evidence_hygiene_audit.json
```

## Parent

`Story Hardening Issue Pack`

## What to build

Build a small CzechLynx known-ID simulation that shows how PF-ERI changes the
candidate queue before expert review or downstream evidence use. The simulation
should start from a candidate queue, apply evidence admission or defer routing,
and report same-ID retention, false-candidate burden, and not-ready/uncertain
concentration.

This issue gives the project a concrete application-facing demonstration while
remaining inside the honest CzechLynx known-ID evidence boundary.

## Acceptance criteria

- [x] The simulation input is a descriptor-retrieved candidate queue or
  documented equivalent candidate-pair table.
- [x] The simulation output separates admitted and deferred pairs.
- [x] The output reports same-ID retention where known-ID labels are available.
- [x] The output reports false-candidate burden as review utility, not identity
  accuracy.
- [x] The output reports not-ready/uncertain concentration or reduction.
- [x] The report states that this is a pre-inference evidence hygiene
  simulation, not a population estimate or validated ecological outcome.

## Blocked by

- Issue 3: Make Core Incremental Model Evidence Paper-Ready.
- Issue 5: Turn Review-Budget Routing Into Applied Evidence Value.

## Issue 7: Rewrite Results As Evidence Ladder

Status: `COMPLETE`

Completion artifacts:

```text
docs/modeling-validation/2026-07-09_results_evidence_ladder.md
scripts/prototypes/prototype_issue7_evidence_ladder.py
```

## Parent

`Story Hardening Issue Pack`

## What to build

Create a manuscript result order that follows inference logic rather than phase
chronology. The result sequence should show how each analysis changes what the
reader can believe about pair-level evidence admission.

Required evidence ladder:

```text
construct validity
-> distinct from descriptor and quality
-> descriptor-evidence conflict mechanism
-> selective routing and review utility
-> Bobcat transfer-stress boundary
```

## Acceptance criteria

- [x] A manuscript results outline exists.
- [x] Each result section states:
  `question answered`, `analysis`, `belief changed`, and `claim boundary`.
- [x] Old phase names are used only as provenance, not as the main narrative
  structure.
- [x] The result order makes the central claim easier to evaluate than a
  chronological phase report.
- [x] Bobcat appears only as transfer-stress or workflow allocation unless
  audited identity labels are later added.

## Blocked by

- Issue 1: Build Manuscript Evidence-Chain Outline.
- Issue 2: Add Contribution Hierarchy And Related-Work Distinction.
- Issue 3: Make Core Incremental Model Evidence Paper-Ready.
- Issue 4: Add Quality And Similarity Sensitivity Package.
- Issue 5: Turn Review-Budget Routing Into Applied Evidence Value.
- Issue 6: Build CzechLynx Pre-Inference Evidence Hygiene Simulation.

## Issue 8: Build Reviewer Objection Matrix And Claim Gate

Status: `COMPLETE`

Completion artifacts:

```text
docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue8/issue8_reviewer_objection_matrix.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue8/issue8_claim_gate.json
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue8/issue8_objection_matrix_audit.json
```

## Parent

`Story Hardening Issue Pack`

## What to build

Create a rebuttal-ready objection matrix and claim gate that maps every major
reviewer objection to one of three answer types:

```text
answered by main evidence
answered by appendix sensitivity
explicitly blocked as a claim
```

No objection should be answered only by reassurance. The matrix must include
safe wording, blocked wording, and the artifact or analysis that supports the
answer.

## Acceptance criteria

- [x] The matrix covers reviewability subjectivity.
- [x] The matrix covers the quality-proxy alternative explanation.
- [x] The matrix covers the descriptor-similarity-proxy alternative
  explanation.
- [x] The matrix covers targeted-sample or full-queue representativeness.
- [x] The matrix covers human label reliability.
- [x] The matrix covers Bobcat identity-label absence.
- [x] The matrix covers partial feature sensitivity and non-estimable features.
- [x] Each objection has an evidence artifact, appendix sensitivity, or blocked
  claim boundary.
- [x] The final claim narrative or claim gate is updated to reflect the matrix.

## Blocked by

- Issue 1: Build Manuscript Evidence-Chain Outline.
- Issue 2: Add Contribution Hierarchy And Related-Work Distinction.
- Issue 3: Make Core Incremental Model Evidence Paper-Ready.
- Issue 4: Add Quality And Similarity Sensitivity Package.
- Issue 5: Turn Review-Budget Routing Into Applied Evidence Value.
- Issue 6: Build CzechLynx Pre-Inference Evidence Hygiene Simulation.
- Issue 7: Rewrite Results As Evidence Ladder.

## Issue 9: Final Story Consistency Audit

Status: `COMPLETE`

Completion artifacts:

```text
docs/modeling-validation/2026-07-09_final_story_consistency_audit.md
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue9/issue9_story_consistency_findings.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue9/issue9_story_consistency_audit.json
```

## Parent

`Story Hardening Issue Pack`

## What to build

Run a final consistency audit across the project-facing and manuscript-facing
documents. The audit must check that the same central claim appears everywhere:

```text
Similarity is not admissibility.
PF-ERI is pair-level evidence admission after descriptor retrieval.
```

The audit should remove or flag wording that accidentally reframes PF-ERI as a
descriptor, automatic identity classifier, generic conformal method, generic
Bayesian method, or Bobcat identity-validation system.

## Acceptance criteria

- [x] The audit checks project rules, current project map, modeling validation
  docs, final claim narrative, and paper-ready claim tables.
- [x] Any wording that implies descriptor replacement is removed or blocked.
- [x] Any wording that implies automatic identity assignment is removed or
  blocked.
- [x] Any wording that implies Bobcat identity accuracy is removed or blocked.
- [x] Any wording that makes conformal, Bayesian, multi-annotator, or generic
  classifier methods the main novelty is removed or demoted.
- [x] The final audit summary lists checked files, edits made, remaining
  boundaries, and next action.

## Blocked by

- Issue 8: Build Reviewer Objection Matrix And Claim Gate.

## Execution Order

```text
Issue 1
-> Issue 2
-> Issue 3
-> Issue 4
-> Issue 5
-> Issue 6
-> Issue 7
-> Issue 8
-> Issue 9
```

Issues 4 and 5 can run in parallel after Issue 3 if two agents are available.
Issue 6 should wait for both Issue 3 and Issue 5. Issues 7, 8, and 9 should stay
sequential because they consolidate the scientific story.
