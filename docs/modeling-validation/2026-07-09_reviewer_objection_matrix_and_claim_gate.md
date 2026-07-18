# Reviewer Objection Matrix And Claim Gate

Date: 2026-07-09

Status: `STORY_HARDENING_ISSUE8_COMPLETE`

Parent issue pack:

```text
docs/project-governance/executable-plans/plans/2026-07-09-story-hardening-issue-pack.md
```

Generated artifacts:

```text
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue8/issue8_reviewer_objection_matrix.csv
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue8/issue8_claim_gate.json
archive/pferi_v1/outputs/modeling-validation/story-hardening-issue8/issue8_objection_matrix_audit.json
```

## Purpose

This document completes Issue 8 of the story hardening issue pack. Its purpose
is to make the manuscript rebuttal-ready without making the claims larger than
the evidence. The rule is strict: no reviewer objection is answered by
reassurance alone. Each objection must be answered by main evidence, appendix
sensitivity, or an explicit blocked-claim boundary.

The central claim remains:

```text
Similarity is not admissibility.
```

The claim gate status is `PASS`. The allowed positive claim is that
PF-ERI is a post-retrieval pair-level evidence admission layer for
descriptor-retrieved wildlife Re-ID candidate pairs. The gate blocks descriptor
replacement, automatic identity assignment, Bobcat identity accuracy,
unqualified retrieval-ranking improvement, universal feature-causal claims, and
distribution-free cross-domain guarantees.

## Objection Matrix

| Objection | Answer type | Evidence answer | Safe wording | Blocked wording |
| --- | --- | --- | --- | --- |
| Reviewability may be a subjective human preference rather than a defensible scientific endpoint. | `answered_by_main_evidence` | The manuscript defines reviewability as the pair-level evidential-admissibility endpoint and places construct validity first in the results ladder. Artifacts: `docs/modeling-validation/2026-07-09_results_evidence_ladder.md`; `archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_analysis_audit.json`. | PF-ERI is evaluated against blind reliability-supported reviewability and evidential-admissibility labels. | Human reviewability labels prove animal identity truth or complete causal mechanisms. |
| PF-ERI may only be an image-quality filter. | `answered_by_appendix_sensitivity` | Issue 4 tests quality-matched and high-quality subsets; pooled contrasts remain positive, while non-estimable quality fields are explicitly bounded. Artifacts: `docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md`; `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_matched_sensitivity.csv; archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_quality_subset.csv`. | PF-ERI is not reducible to the estimable image-quality controls in the current CzechLynx reviewed pairs. | PF-ERI proves universal superiority over every image-quality feature or every descriptor-specific quality stratum. |
| PF-ERI may only restate descriptor similarity. | `answered_by_main_evidence_and_appendix_sensitivity` | Issue 3 compares descriptor-only and PF-ERI models; Issue 4 adds high-similarity and rank/similarity-stratified checks. Artifacts: `docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md`; `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_similarity_subset.csv; archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_rank_similarity_stratified_sensitivity.csv`. | Similarity and quality do not fully exhaust the human reviewability construct. | PF-ERI always improves descriptor ranking, mAP, MRR, or top-k identity performance. |
| Targeted reviewed samples could inflate the apparent PF-ERI effect. | `answered_by_claim_boundary` | The final results ladder uses CzechLynx reviewed candidate pairs for evidence admission and treats targeted mechanism samples as mechanism support, not population estimates. Artifacts: `docs/modeling-validation/2026-07-09_results_evidence_ladder.md`; `docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md`. | Targeted and stratified reviewed samples support pair-level reviewability and mechanism checks within the reviewed validation contract. | The reviewed sample estimates the full retrieval-queue population effect or deployment population performance. |
| Majority labels or reviewer labels may be unstable. | `answered_by_main_evidence` | Blind reliability artifacts support the reviewability labels and final claim narrative records reviewer agreement and provenance. Artifacts: `archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_analysis_audit.json; archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis-reviewer2/blind_reliability_analysis_audit.json`; `archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet/agreement-analysis/blind_reliability_disagreement_appendix.csv`. | The labels are blind reliability-supported reviewability labels. | Blind review proves animal identity truth or removes all human-label uncertainty. |
| Bobcat transfer results cannot validate identity performance without Bobcat individual labels. | `explicitly_blocked_as_claim` | Bobcat is restricted to transfer-stress and workflow-allocation diagnostics; identity accuracy, false-match accuracy, mAP, MRR, and top-k claims are blocked. Artifacts: `archive/pferi_v1/outputs/modeling-validation/bobcat-wild-urban-transfer-stress/README.md`; `archive/pferi_v1/outputs/modeling-validation/pair-level-validation/strong-bobcat-transfer-readiness/megadescriptor_l_384/legacy-code18f_bobcat_transfer_readiness_audit.json; archive/pferi_v1/outputs/modeling-validation/pair-level-validation/strong-bobcat-transfer-readiness/dinov2_vitl14/legacy-code18f_bobcat_transfer_readiness_audit.json`. | Bobcat is an unlabeled transfer-stress and workflow-allocation context. | PF-ERI validates Bobcat identity accuracy, Bobcat false-match accuracy, Bobcat mAP, or Bobcat top-k retrieval. |
| Some PF-ERI feature mechanisms are not fully estimable because fields are constant or sparse. | `answered_by_appendix_sensitivity_and_claim_boundary` | Issue 4 reports the estimable sensitivity results and explicitly keeps constant or sparse fields as boundaries. Artifacts: `docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md`; `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_similarity_sensitivity_audit.json`. | PF-ERI shows pair-level reviewability signal under estimable quality and similarity checks. | Every PF-ERI feature family is independently validated, causal, and equally supported. |

## Claim Gate Interpretation

The matrix protects the project in two ways. First, it prevents overclaiming by
making the blocked wording explicit next to each safe wording. This is
important because several attractive but unsafe claims are close to the current
results, especially Bobcat identity performance, top-k identity improvement,
and universal feature-mechanism validation. Second, it keeps the main
contribution focused on pair-level evidence admission rather than on the
supporting statistical tools. Reviewer reliability, quality/similarity
sensitivity, review-budget routing, and transfer-stress diagnostics are
safeguards around the evidence-admission claim.

The strongest positive statement is therefore bounded but useful. PF-ERI
supports a pair-level reviewability and evidential-admissibility signal after
strong descriptor retrieval, and this signal is not exhausted by the estimable
descriptor-similarity and image-quality controls in the reviewed CzechLynx
validation setting. The Bobcat analyses remain valuable as transfer-stress and
workflow-allocation diagnostics, but they do not validate identity accuracy.

## Issue 8 Acceptance Check

The matrix covers reviewability subjectivity, the image-quality proxy
alternative, the descriptor-similarity proxy alternative, targeted-sample or
full-queue representativeness, human label reliability, Bobcat identity-label
absence, and partial feature sensitivity with non-estimable features. Each
objection has an evidence artifact, appendix sensitivity artifact, or explicit
blocked-claim boundary. The final claim narrative is updated to point to this
matrix and preserve the same safe and blocked wording.
