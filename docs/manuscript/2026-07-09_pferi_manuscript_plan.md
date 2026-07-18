# PF-ERI Manuscript Plan

Date: 2026-07-09

Working title:

`Similarity Is Not Admissibility: Pair-Level Evidence Admission for Wildlife Re-Identification Candidate Review`

## Purpose

This plan prepares a full English manuscript draft from the completed story-hardening evidence package. The manuscript should read as an original research paper about a missing evidence-governance decision in wildlife photographic re-identification workflows. It should not read as a chronological Phase18 report.

The locked thesis is:

`Similarity is not admissibility.`

The paper's central object is a descriptor-retrieved candidate pair. The paper's central target is pair-level reviewability and evidential admissibility. PF-ERI should be framed as a post-retrieval evidence admission layer that evaluates whether a retrieved pair contains enough comparable visual evidence to enter expert review or cautious downstream use.

## Claim Boundary

The manuscript may claim that PF-ERI supports pair-level reviewability and evidential admissibility after strong descriptor retrieval in the reviewed CzechLynx validation setting. It may claim that this signal is not exhausted by the estimable descriptor-similarity and image-quality controls, and that PF-ERI can route candidate pairs to reduce not-ready or uncertain evidence under selected review budgets.

The manuscript must not claim that PF-ERI is a new descriptor, replaces MegaDescriptor or DINOv2, assigns identity, validates Bobcat identity accuracy, proves universal mAP or top-k improvement, proves every PF-ERI feature mechanism, or provides distribution-free cross-domain guarantees.

## Story Spine

Photographic wildlife re-identification supports individual-level ecological evidence, but camera-trap images often vary in viewpoint, visible body region, occlusion, blur, and pattern visibility. Strong descriptors make large image archives searchable by returning visually similar candidate pairs. A high-similarity pair can still lack the comparable visual evidence needed for review, so candidate retrieval and evidence admission are different decisions. PF-ERI formalizes the missing pair-level admission step, evaluates candidate pairs against human reviewability and evidential admissibility labels, tests quality and similarity alternatives, and routes uncertain evidence out of the immediate review path. CzechLynx supplies the known-ID reviewed validation setting; Bobcat remains an unlabeled transfer-stress and workflow-allocation context.

## Manuscript Structure

The main draft should use an IMRAD structure with a short unstructured abstract.

The introduction should move from ecological measurement to photographic individual identification, then to strong descriptor retrieval, then to the missing pair-level admission layer. The first appearance of the core line should be in the introduction: similarity is not admissibility.

The methods should separate the data contract, descriptor candidate generation, PF-ERI feature construction, human reviewability labels, model comparisons, sensitivity checks, review-budget analysis, and Bobcat boundary. The methods should preserve reproducibility without repeating every legacy phase name.

The results should follow the evidence ladder:

1. Human reviewability defines the pair-level evidence-admission endpoint.
2. PF-ERI evidence is not reducible to descriptor similarity or image quality.
3. High-similarity candidate pairs can still lack admissible pair evidence.
4. Selective evidence routing reduces not-ready or uncertain review burden.
5. Bobcat transfer-stress exposes workflow evidence pressure without identity claims.

The discussion should state what changed: candidate retrieval now has a named downstream evidence admission target. It should also state what did not change: expert review, identity validation, and ecological inference still require their own evidence.

## Figure And Table Plan

Figure 1 should use the existing evidence-chain schematic:

`archive/pferi_v1/outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.svg`

It should show the chain from image archive to descriptor retrieval, candidate pair queue, PF-ERI admission, expert review, and cautious downstream use.

Figure 2 should report the model-comparison evidence from:

`archive/pferi_v1/outputs/modeling-validation/story-hardening-issue3/issue3_core_incremental_model_comparison.csv`

The figure should emphasize reviewability prediction, not identity accuracy.

Figure 3 should report quality and similarity sensitivity from:

`archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_quality_matched_sensitivity.csv`

`archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_quality_subset.csv`

`archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_high_similarity_subset.csv`

`archive/pferi_v1/outputs/modeling-validation/story-hardening-issue4/issue4_rank_similarity_stratified_sensitivity.csv`

Figure 4 should report fixed-budget review routing from:

`archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/figure_issue5_review_budget_utility.svg`

Table 1 should define the datasets, descriptor scopes, pair counts, endpoints, and blocked identity claims.

Table 2 should summarize pooled model metrics, including AUROC, AUPRC, Brier score, calibration error, and confidence intervals.

Table 3 should summarize review-budget and pre-inference evidence hygiene metrics.

## Citation Plan

The introduction should cite animal re-identification and computer-vision reviews, including Schneider et al. (2019) and Vidal et al. (2021). It should cite CzechLynx as the known-ID Eurasian lynx data source and cite Cermak et al. (2024) for WildlifeDatasets and MegaDescriptor. It should cite Picek et al. (2026) for CzechLynx dataset context.

The field-need paragraph should cite Choo et al. (2020) on reporting individual identification from camera-trap photographs, Pereira et al. (2022) on large-felid individual identification challenges, and ecological AI references such as Tuia et al. (2022), Whytock et al. (2021), and Villon et al. (2020) to support the need for validated error-aware workflows.

The related-work paragraph should cite Wildbook documentation, Blount et al. (2022) on Flukebook/WBIA-style platform work, WildlifeDatasets, DINOv2, and selective prediction or reject-option literature. These citations should support positioning only; they should not make PF-ERI sound like a generic abstention method.

## Drafting Rules

The main manuscript should use full paragraphs. Bullets may appear in planning documents and in artifact inventories, but not in the final abstract, introduction, results, or discussion.

The manuscript should use calibrated verbs. Preferred verbs include supports, estimates, evaluates, routes, aligns with, and is consistent with. Avoid proves, guarantees, replaces, solves, validates identity, and demonstrates universal improvement.

The manuscript should state negative or mixed findings where they matter. In particular, the pooled full model adds only a small AUROC and AUPRC increment over descriptor plus quality, and descriptor-specific active-control increments are mixed. The stronger claim comes from the combined evidence package, including PF-ERI-only alignment, quality and similarity sensitivity, and review-routing utility.

## Review Standard

The internal peer review should evaluate whether the central claim follows from the results, whether the methods are reproducible enough for a reader to inspect, whether the statistics avoid pseudoreplication or identity-accuracy drift, whether Bobcat claims remain blocked, and whether the discussion states limitations as scope rather than routine future work.
