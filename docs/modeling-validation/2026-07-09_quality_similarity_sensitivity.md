# Quality And Similarity Sensitivity

Date: 2026-07-09

Status: `PASS_WITH_BOUNDARIES`

This sensitivity package evaluates the two strongest alternative explanations for the Issue 3 model result. The first alternative explanation is that PF-ERI is only an image-quality filter. The second is that PF-ERI is only a descriptor-similarity proxy. The analysis keeps the endpoint fixed as CzechLynx human reviewability and evidential admissibility; it does not evaluate identity accuracy, Bobcat identity performance, mAP, MRR, or top-k retrieval improvement.

The quality-matched analysis groups pairs by an explicit quality proxy and then asks whether the non-quality PF-ERI pair signal separates review-ready from not-ready or uncertain pairs inside those quality strata. The high-quality-only analysis asks the same question after restricting the table to the top quality quartile. These tests are important because several nominal quality features are constant in the current 400-row reviewed table, so the estimable quality contrast is driven by body-part overlap rather than by visible-pattern area or night-motion blur variation.

In the pooled quality-matched table, 4 estimable quality strata show a positive high-minus-low PF-ERI reviewability contrast. In the pooled high-quality subset, the high-minus-low PF-ERI contrast is 0.156. This result means that the current data provide a direct guardrail against the simplest quality-only explanation, but the guardrail is bounded by the limited variation of several image-quality fields and by descriptor-specific quality strata that are not uniformly positive.

The high-similarity and rank/similarity-stratified analyses address the descriptor-proxy explanation. They restrict attention to candidate pairs that are already similar according to the strong descriptor queue or compare pairs within rank and similarity strata. If PF-ERI remains aligned with reviewability inside these restricted comparisons, the result is more consistent with pair-level evidence admission than with a pure retrieval-score restatement.

In the pooled high-similarity subset, the high-minus-low PF-ERI contrast is 0.176. Across pooled estimable rank/similarity strata, 10 of 10 strata show a positive high-minus-low PF-ERI contrast. This supports the bounded interpretation that PF-ERI is not merely descriptor similarity, while also preserving any weak or sparse strata as claim boundaries rather than converting them into positive evidence.

The scientific interpretation is therefore stronger than Issue 3 alone but still properly bounded. PF-ERI shows evidence consistent with a pair-level admissibility signal under quality and similarity pressure tests, especially when the comparison is framed around non-quality pair evidence such as body-part overlap and cross-descriptor agreement. The result should not be written as universal superiority over descriptor plus quality; it should be written as evidence that similarity and quality do not fully exhaust the human reviewability construct in the reviewed CzechLynx candidate pairs.

## Artifact Links

The quality-matched table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_matched_sensitivity.csv`. The high-quality subset table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_quality_subset.csv`. The high-similarity subset table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_similarity_subset.csv`. The rank/similarity-stratified table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_rank_similarity_stratified_sensitivity.csv`. The audit file is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_similarity_sensitivity_audit.json`.
