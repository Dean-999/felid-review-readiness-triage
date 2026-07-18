# Similarity Is Not Admissibility: Pair-Level Evidence Admission for Wildlife Re-Identification Candidate Review

> **Historical v1 manuscript under submission lock.** This draft contains exploratory analyses that do not satisfy the PF-ERI v2 confirmation contract. It is retained for provenance and cannot be submitted, cited as a final result, or updated with v2 language until v2 raw logs, manifests, and confirmatory analyses are frozen.

Author list: [to be completed]

Affiliations: [to be completed]

Corresponding author: [to be completed]

## Abstract

Photographic wildlife re-identification workflows use images as individual-level evidence, yet modern candidate retrieval systems answer a narrower question: which images look similar. A retrieved candidate pair can score high under a strong descriptor while lacking comparable flank views, shared body regions, visible pattern evidence, or an informative weakest image. We introduce PF-ERI as a post-retrieval, pair-level evidence admission layer for wildlife Re-ID candidate review. PF-ERI evaluates whether descriptor-retrieved candidate pairs contain admissible visual evidence for human review and evidence routing; it does not train a new descriptor or assign identity. We tested PF-ERI on reviewed CzechLynx candidate pairs generated with MegaDescriptor and DINOv2 queues. The endpoint was human reviewability and evidential admissibility, not identity accuracy or retrieval mAP. Blind reliability analyses supported the human reviewability construct on 280 reviewed pairs, with binary Cohen's kappa of 0.859 in one review packet and 0.785 in an independent external review packet. In pooled model validation on 400 reviewed pairs, PF-ERI evidence alone achieved AUROC 0.740 and AUPRC 0.845 for reviewability, while descriptor-only similarity achieved AUROC 0.585 and AUPRC 0.775. Adding PF-ERI to descriptor plus quality controls produced a small pooled increment, from AUROC 0.772 to 0.786 and AUPRC 0.882 to 0.885. Quality- and similarity-stratified analyses showed positive PF-ERI reviewability contrasts in the pooled high-quality subset, high-similarity subset, and all estimable rank/similarity strata. At review budgets of 100 and 200 pairs, PF-ERI priority reduced not-ready or uncertain burden relative to descriptor priority. The evidence supports PF-ERI as a descriptor-agnostic evidence-governance layer for reviewed CzechLynx candidate pairs, with Bobcat analyses restricted to unlabeled transfer-stress and workflow allocation.

## Introduction

Individual photographic identification has become a practical measurement tool in wildlife ecology and conservation. Camera traps and field photographs can support encounter histories, mark-recapture studies, longitudinal monitoring, and management decisions when observers recognize individuals from natural markings. Those uses depend on a measurement condition that researchers cannot skip: the image pair used for an individual-level decision must contain enough comparable visual information for a reviewer to accept, reject, or defer the candidate match. If weak or non-comparable image pairs enter encounter histories, downstream analyses can inherit misidentification, unclassifiable photographs, and observer disagreement as measurement error. Reporting guidance for camera-trap individual identification therefore asks researchers to document unclassifiable images, inter-observer discrepancies, and identification uncertainty (Choo et al., 2020). Large-felid field studies describe the same practical pressure from pose, image quality, body-region visibility, and reviewer uncertainty (Pereira et al., 2022).

Computer vision has changed the scale of photographic individual identification by making large image archives searchable. Reviews of camera-trap animal re-identification and cross-disciplinary perspectives on individual identification describe a field moving from manual comparison toward learned representations, retrieval systems, and human-assisted candidate review (Schneider et al., 2019; Vidal et al., 2021). WildlifeDatasets and MegaDescriptor provide open-source animal Re-ID tooling and strong descriptor baselines across species (Cermak et al., 2024a). DINOv2 provides a strong general visual representation that can serve as another upstream descriptor source (Oquab et al., 2023). Recent benchmark and fusion work, including WildlifeReID-10k and WildFusion, extends the retrieval and identity-ranking side of animal Re-ID (Adam et al., 2025; Cermak et al., 2024b). These systems answer a retrieval question: which gallery images lie close to a query image in a visual representation space?

A reviewer faces a second question after retrieval. A camera-trap pair can be visually similar yet weak as individual-level evidence if one image is blurred, if the animal shows different sides, if the shared visible body region is small, if the coat pattern is hidden, or if the descriptor score conflicts with the visible pair evidence. Similarity is not admissibility. Strong descriptor retrieval can produce a useful candidate queue, but the queue still contains pairs that differ in evidential status.

Existing human-in-the-loop platforms make this interface visible. Wildbook and related image-analysis systems route images through detection, annotation, matching algorithms, and human review rather than treating a score as the end of the evidence chain (Wildbook, 2026a; Wildbook, 2026b). Flukebook and WBIA-style platform work also place algorithmic matching inside a broader photo-identification workflow (Blount et al., 2022). These platforms make candidate generation and review operational. PF-ERI adds a measured pair-level target to that workflow: whether a retrieved pair contains enough comparable visual evidence to enter review with a defined route, risk state, or deferral decision.

Ecological machine learning has developed safeguards for error-aware use of automated labels. Researchers have shown that downstream ecological analyses can require validation when camera-trap labels come from machine-learning models (Whytock et al., 2021). Others have proposed methods to control error rates in automated species identification and have called for machine-learning tools that support conservation workflows with uncertainty-aware human oversight (Villon et al., 2020; Tuia et al., 2022). Selective prediction and reject-option methods provide a formal vocabulary for abstaining when predictions carry unacceptable risk (Geifman and El-Yaniv, 2017; Geifman and El-Yaniv, 2019; Hendrickx et al., 2024). Conformal risk control calibrates bounded risks for selected predictions under stated assumptions (Angelopoulos et al., 2024). PF-ERI uses this risk-aware vocabulary in a narrower wildlife Re-ID setting: descriptor-retrieved candidate pairs whose visual evidence may or may not be admissible for human review.

We define PF-ERI as a post-retrieval, descriptor-agnostic pair-level evidence admission layer for wildlife Re-ID candidate review. A strong descriptor generates a candidate queue. PF-ERI then evaluates each candidate pair for reviewability and evidential admissibility using pair-level evidence signals, including weakest-image evidence, visible pattern support, body-region overlap, viewpoint or side comparability, cross-descriptor agreement, and source-domain stress. The layer routes pairs into review-ready, cautious, conflict, deferred, or non-comparable evidence states. PF-ERI does not replace descriptors, fuse embeddings for identity ranking, or assign animal identity. It separates candidate retrieval from evidence admission.

We evaluated PF-ERI on CzechLynx candidate pairs because CzechLynx provides identity-labeled Eurasian lynx images and a suitable known-ID validation context (Picek et al., 2026). We used MegaDescriptor and DINOv2 as strong upstream descriptor sources, reviewed candidate pairs for human reviewability and evidential admissibility, and then tested whether PF-ERI evidence remains informative under descriptor and quality controls. Our primary endpoint was human reviewability, not identity accuracy. CzechLynx known-ID labels supported same-ID and different-ID audits, while Bobcat data were used only as unlabeled transfer-stress and workflow-allocation context. This design tests a narrow claim: after strong descriptor retrieval, PF-ERI can evaluate whether a candidate pair carries admissible evidence for review.

## Methods

### Study Design

We designed this study as a post-retrieval evidence-admission validation around strong descriptor candidate queues. The unit of analysis was a candidate pair, defined as a query image and a candidate image returned by an upstream descriptor. The main endpoint was human reviewability and evidential admissibility. A pair was treated as review-ready when the available visual evidence allowed a human reviewer to make a responsible individual-level comparison, including confident rejection for different-ID pairs. A pair was treated as not-ready or uncertain when the reviewer could not rely on the pair as individual-level evidence because the images lacked comparable visual information or showed unresolved evidence conflict.

The study separated three tasks that often collapse into one score. The descriptor produced candidate pairs. PF-ERI evaluated whether those pairs had admissible pair evidence. Known identity labels in CzechLynx supported audits of same-ID retention and false-candidate burden, but those audits did not define the primary endpoint. This endpoint design treats a different-ID pair as review-ready when the reviewer can reject it with confidence.

### Data Scope And Known-ID Validation Contract

The main validation used reviewed CzechLynx candidate pairs. CzechLynx is an individual-identification and pose-estimation dataset for Eurasian lynx, with identity-labeled camera-trap images and long-term monitoring context (Picek et al., 2026). In the manuscript-facing validation set used here, 400 reviewed candidate pairs formed the pooled model comparison table, with 200 pairs from the MegaDescriptor queue and 200 pairs from the DINOv2 queue. The pooled table contained 275 review-ready pairs and 125 not-ready or uncertain pairs.

The manuscript treats Bobcat pair outputs as unlabeled transfer-stress and workflow-allocation artifacts. CzechLynx provides the known-ID validation contract. Bobcat identity accuracy, Bobcat mAP, Bobcat top-k, and Bobcat false-match claims are blocked unless later work adds audited Bobcat individual labels or same/different pair labels.

### Candidate-Pair Contract And Sampling

The reviewed pair table was built from descriptor-retrieved candidate queues rather than from arbitrary image pairs. Each row preserved a query image identifier, a candidate image identifier, descriptor scope, descriptor similarity percentile, known CzechLynx same/different identity audit fields, PF-ERI evidence features, route fields, and human reviewability labels. The row contract excluded self-pairs, kept compared models on identical row sets within each scope, and preserved descriptor-specific analyses for MegaDescriptor and DINOv2. The manuscript-facing pooled model table used 400 reviewed pairs: 200 from each descriptor queue.

The reviewed set should be interpreted as a validation contract for pair-level evidence admission, not as a deployment-population estimate over every possible retrieval edge. Targeted and stratified review packets were used to stress the mechanism and quality/similarity alternatives. The main manuscript reports the 400-row reviewed evidence table with sensitivity analyses rather than claiming full-queue population prevalence. Reproducibility artifacts for the row contract are recorded in `outputs/modeling-validation/story-hardening-issue3/issue3_core_incremental_model_comparison.csv` and the Issue 4-6 story-hardening outputs.

The current sampling design supports construct validation, proxy-alternative testing, and bounded workflow utility. It does not estimate the prevalence of review-ready pairs across all possible retrieval queues, camera systems, or species. A deployment-population estimate would require a larger prospective sample drawn from the full candidate queue with query-clustered or identity-clustered uncertainty analysis.

### Upstream Descriptor Candidate Queues

We used strong descriptors as upstream candidate generators rather than as methods to be replaced. MegaDescriptor came from the WildlifeDatasets and WildlifeTools ecosystem for animal re-identification (Cermak et al., 2024a). DINOv2 served as a general self-supervised visual descriptor source (Oquab et al., 2023). For each descriptor scope, candidate pairs were scored by descriptor similarity percentile and then passed to the PF-ERI evidence layer. Self-pairs were excluded in pipeline validation.

Descriptor scores provide retrieval context and active controls. PF-ERI operates after retrieval, so the evaluation does not treat PF-ERI as an embedding improvement or a replacement retrieval model.

### PF-ERI Pair-Level Evidence Features

PF-ERI represented each candidate pair with evidence features designed to describe pair admissibility rather than identity by itself. The feature set included visible pattern evidence, viewpoint or side compatibility, body-part overlap, night or motion blur risk, cross-descriptor agreement, and source-domain shift stress. In model tables these fields were named `visible_pattern_area_score`, `viewpoint_side_compatibility`, `body_part_overlap_score`, `night_or_motion_blur_risk`, `cross_descriptor_agreement_score`, and `source_domain_shift_score`.

The model also produced an evidence admission score used for routing and review-budget analysis. Higher values indicated stronger admissible pair evidence. The implementation treated source-domain stress as a diagnostic and claim-boundary feature, not as a causal explanation. Several quality-related fields had limited variation in the final 400-row reviewed table, so the sensitivity analyses explicitly marked constant or sparse fields as non-estimable rather than converting them into evidence.

### Human Reviewability Labels And Reliability

The human endpoint was reviewability and evidential admissibility. Reviewers assessed whether a candidate pair contained enough comparable visual evidence for individual-level review. The label asked reviewers to judge evidential readiness, not to assign identity for the model or convert reviewability into identity truth.

Blind reliability artifacts supported the construct. In one reviewed packet of 280 pairs, binary percent agreement was 0.939 and binary Cohen's kappa was 0.859. In an independent external review packet of 280 pairs, binary percent agreement was 0.914 and binary Cohen's kappa was 0.785. Primary reason agreement on non-ready pairs was 0.806 in the first packet and 0.736 in the external packet. These values support the use of blind reliability-supported reviewability labels, while leaving reviewer disagreement and reason-family variation as limitations.

### Model Comparisons

We evaluated six interpretable L2 logistic validation models on identical row sets within each scope. The model families were descriptor-only, quality-only, PF-ERI evidence-only, descriptor plus quality, descriptor plus PF-ERI, and descriptor plus quality plus PF-ERI. The pooled scope used all 400 reviewed pairs. Descriptor-specific scopes repeated the comparison for the MegaDescriptor and DINOv2 queues.

The metrics were AUROC, AUPRC, Brier score, five-bin expected calibration error, and bootstrap confidence intervals for AUROC and AUPRC. We treated the full model against descriptor plus quality as the strict active-control comparison. We treated PF-ERI-only against quality-only and descriptor-only as construct-alignment evidence rather than as a claim of descriptor replacement. The validation scripts used identical row sets for compared models within each scope and reported bootstrap intervals for the main discrimination metrics. Remaining dependence from repeated queries or identity clusters is a limitation of the current reviewed-table scale and should be handled with larger query-clustered designs in later confirmation.

### Quality And Similarity Sensitivity

We tested two alternative explanations: PF-ERI could be a quality filter, or it could restate descriptor similarity. The quality sensitivity grouped pairs by an explicit quality proxy and tested whether non-quality PF-ERI pair signal separated review-ready from not-ready or uncertain pairs inside estimable quality strata. The high-quality subset repeated the question after restricting to the top quality quartile.

The descriptor-similarity sensitivity used high-similarity subsets and rank/similarity strata. These analyses asked whether PF-ERI remained aligned with reviewability among pairs that already had strong descriptor support or within narrow retrieval positions. Sparse strata were marked as non-estimable when they lacked enough rows or a usable high/low PF-ERI split.

### Review-Budget Routing And Evidence Hygiene

We evaluated whether PF-ERI changed the practical content of a finite expert review queue. In fixed-budget analysis, PF-ERI-prioritized review was compared with descriptor-similarity priority on the same CzechLynx reviewed pair pool. Human labels were used after selection to audit review-ready rate and not-ready or uncertain burden. Known-ID labels were used to report same-ID retention and different-ID candidate burden, but those values were secondary audits rather than identity-performance endpoints.

We also ran a pre-inference evidence hygiene simulation on the reviewed CzechLynx candidate-pair table. The workflow assigned each descriptor-retrieved pair to an admitted or deferred evidence state before expert review or downstream inference. We then audited review-ready rate, not-ready or uncertain burden, same-ID candidate retention, and deferred-evidence concentration.

### Reproducibility Artifacts

The manuscript-facing evidence chain draws from the story-hardening issue package completed on 2026-07-09. The key artifacts are `docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md`, `docs/modeling-validation/2026-07-09_quality_similarity_sensitivity.md`, `docs/modeling-validation/2026-07-09_review_budget_routing_value.md`, `docs/modeling-validation/2026-07-09_pre_inference_evidence_hygiene_simulation.md`, `docs/modeling-validation/2026-07-09_results_evidence_ladder.md`, and `docs/modeling-validation/2026-07-09_reviewer_objection_matrix_and_claim_gate.md`. The final story consistency audit reported zero unsafe positive claim lines in the claim-bearing layer.

## Results

### Human Reviewability Defined The Pair-Level Evidence-Admission Endpoint

The first result established the measurement target and validation contract (Table 1). The reviewed CzechLynx candidate-pair table converted descriptor-retrieved pairs into a human endpoint: whether the pair was review-ready as individual-level visual evidence. This endpoint differs from same-ID truth. Same-ID status can audit candidate coverage, but a same-ID pair with poor visibility can be weak evidence, and a different-ID pair with clear comparable markings can be review-ready because a reviewer can reject it with confidence.

Blind reliability supported this endpoint and is summarized in the validation contract (Table 1). The first reliability packet contained 280 pairs and achieved binary Cohen's kappa 0.859 with 0.939 binary percent agreement. The independent external review packet also contained 280 pairs and achieved binary Cohen's kappa 0.785 with 0.914 binary percent agreement. These agreement levels support reviewability as a usable pair-level construct in the current validation contract. Reviewer disagreement remains part of the measurement uncertainty, and the label does not prove animal identity.

### Model Comparisons Supported Reviewability Alignment Under Active Controls

The pooled model comparison used 400 reviewed pairs, including 275 review-ready pairs and 125 not-ready or uncertain pairs (Figure 2; Table 2). Descriptor similarity alone had limited alignment with reviewability: the descriptor-only model achieved AUROC 0.585 with 95% bootstrap CI 0.531 to 0.641, AUPRC 0.775 with 95% CI 0.728 to 0.829, Brier score 0.215, and five-bin expected calibration error 0.075. The quality-only model performed better, with AUROC 0.724, AUPRC 0.809, Brier score 0.183, and expected calibration error 0.051.

PF-ERI evidence alone achieved AUROC 0.740 with 95% CI 0.691 to 0.795, AUPRC 0.845 with 95% CI 0.795 to 0.892, Brier score 0.179, and expected calibration error 0.020 (Figure 2A; Table 2). PF-ERI features carried reviewability-relevant pair evidence after descriptor retrieval. The descriptor plus quality active-control model achieved AUROC 0.772 and AUPRC 0.882. Adding PF-ERI features to descriptor plus quality increased pooled AUROC to 0.786 and AUPRC to 0.885, with Brier score 0.167 and expected calibration error 0.018.

The active-control increment was small in the pooled table and bounded in the descriptor-specific analyses (Figure 2B; Table 2). AUROC increased by 0.014 over descriptor plus quality, and AUPRC increased by 0.003. Descriptor-specific active-control increments were mixed: the full model changed AUROC by -0.005 and AUPRC by -0.002 in the MegaDescriptor scope, and changed AUROC by -0.008 and AUPRC by -0.016 in the DINOv2 scope. These mixed increments block a universal superiority claim over descriptor plus quality. Figure 2 therefore supports construct alignment rather than a ranking-superiority claim: PF-ERI evidence aligns with reviewability, while descriptor plus quality remains a strong active control.

### Sensitivity Analyses Located Pair-Level Signal Within Quality And Similarity Strata

The quality and similarity sensitivity package tested the two strongest proxy explanations (Figure 3). In the pooled quality-matched analysis, all four estimable quality strata showed positive high-minus-low PF-ERI reviewability contrasts (Figure 3A). In the pooled high-quality subset, the high-minus-low PF-ERI contrast was 0.156 (Figure 3B). These results argue against the quality-only explanation, with a clear boundary: several quality fields were constant or sparse in the reviewed 400-row table, and the DINOv2 high-quality subset showed a negative high-minus-low contrast.

The descriptor-similarity checks addressed whether PF-ERI only restated the descriptor score (Figure 3B-C). In the pooled high-similarity subset, the high-minus-low PF-ERI contrast was 0.176. Across pooled estimable rank/similarity strata, 10 of 10 strata showed positive high-minus-low PF-ERI reviewability contrasts. Among pairs that descriptors already considered similar, PF-ERI still separated more reviewable evidence from weaker or uncertain evidence.

The mechanism supported by these analyses is evidence admission rather than descriptor failure. A descriptor can retrieve a plausible pair, and the pair can still lack the common visual evidence needed for review. PF-ERI's role is to evaluate that second decision.

### Selective Evidence Routing Reduced Not-Ready Or Uncertain Review Burden

PF-ERI changed the content of a finite review queue (Figure 4; Table 3). At a pooled review budget of 100 pairs, PF-ERI priority selected a queue with not-ready or uncertain burden 0.060, compared with 0.090 under descriptor priority. The same comparison retained same-ID candidate coverage of 0.405 under PF-ERI priority and 0.500 under descriptor priority. At a budget of 200 pairs, PF-ERI priority had not-ready or uncertain burden 0.125, compared with 0.210 under descriptor priority.

Across pooled fixed-budget settings, PF-ERI priority reduced not-ready or uncertain burden in four of seven budgets (Figure 4A; Table 3). The tradeoff was visible rather than hidden: descriptor priority retained more same-ID candidates at some budgets (Figure 4B), while PF-ERI priority admitted more review-ready pairs, including different-ID pairs that could support clear exclusion decisions. This pattern supports a review-utility claim rather than an identity-accuracy claim.

The pre-inference evidence hygiene simulation gave the same workflow interpretation (Figure 4C; Table 3). In the pooled queue, PF-ERI admitted 234 pairs and deferred 166 pairs. The admitted set had review-ready rate 0.859 and not-ready or uncertain rate 0.141. The deferred set had review-ready rate 0.446 and not-ready or uncertain rate 0.554. Same-ID candidate retention in the admitted set was 0.655. The deferred set concentrated 92 not-ready or uncertain pairs, compared with 33 in the admitted set. PF-ERI moved weaker or riskier evidence out of the immediate evidence-use path.

### Bobcat Transfer-Stress Preserved The Identity-Claim Boundary

The Bobcat analyses were treated as transfer-stress and workflow-allocation diagnostics, and this boundary is formalized in the validation contract (Table 1). They tested how a pair-level evidence router behaves when moved into unlabeled Bobcat wild and urban contexts, not whether the system identifies Bobcat individuals. This boundary is part of the result rather than a footnote. Without audited Bobcat individual identities or same/different pair labels, the manuscript cannot report Bobcat identity accuracy, false-match accuracy, mAP, MRR, or top-k identity retrieval.

The scientific value of the Bobcat transfer-stress layer is diagnostic. PF-ERI can flag evidence pressure, route burden, and domain-shift stress while keeping identity validation blocked until labeled Bobcat evidence exists. This boundary preserves the main CzechLynx claim and prevents a transfer result from becoming an unsupported identity-performance statement.

## Discussion

This study supports PF-ERI as a post-retrieval pair-level evidence admission layer for wildlife Re-ID candidate review. Strong descriptors make candidate queues searchable. PF-ERI evaluates whether each retrieved pair contains enough comparable visual evidence for review. The results support the central thesis: similarity is not admissibility.

The evidence package combines construct validity, active controls, sensitivity checks, and routing utility. Human reviewability had blind reliability support. PF-ERI evidence alone aligned with reviewability better than descriptor-only similarity and slightly better than the quality-only control in the pooled table. The full model added only a small pooled increment over descriptor plus quality, and descriptor-specific active-control increments were mixed. That model table alone would support only a cautious signal claim. The quality and similarity sensitivity analyses carry the stronger proxy-defense result: PF-ERI remained positively aligned with reviewability in the pooled high-quality subset, high-similarity subset, and all estimable rank/similarity strata. The review-budget analyses then showed that the signal can change which pairs experts see under finite attention.

The distinction between reviewability and identity accuracy is central. A same-ID pair may be poor evidence if the images are not comparable. A different-ID pair may be review-ready if the images allow a confident rejection. PF-ERI evaluates the evidential status of a candidate comparison before identity use. This endpoint matches the operational reality of human-in-the-loop platforms, where algorithms retrieve candidates but experts still decide how to treat them in an evidence chain.

PF-ERI also clarifies its relationship to adjacent methods. Strong descriptor and fusion methods, including MegaDescriptor, DINOv2, WildlifeReID-10k, and WildFusion, address candidate generation, representation quality, dataset scale, or identity-ranking performance. PF-ERI begins after that step. It asks whether a retrieved pair contains admissible evidence for review. Biometric quality and image-quality filtering ask whether a single sample is useful for recognition, but wildlife camera-trap review often requires pair-level comparison across side, pose, body region, and visible pattern. Selective prediction and reject-option models ask when a system should abstain. PF-ERI gives abstention a domain-specific evidence meaning: defer the pair because comparable identity evidence is weak, conflicted, or non-comparable. Conformal risk control offers useful language for bounded-risk selection, yet the current manuscript makes an empirical CzechLynx reviewability claim rather than a distribution-free cross-domain guarantee.

This study has limitations that define the claim's scope. The main validation uses reviewed CzechLynx candidate pairs, not a deployment-wide population estimate over every possible retrieval queue. Several PF-ERI feature fields had limited variation in the final reviewed table, so the manuscript cannot claim that each feature mechanism has independent validation. Human reviewability labels had blind reliability support, but reviewer disagreement remained, and reason-family agreement varied. The active-control increment over descriptor plus quality was small in the pooled table and mixed by descriptor scope. The Bobcat analyses did not include audited identity labels, so Bobcat identity performance remains blocked.

The next validation step should enlarge the reviewed full-queue sample, increase feature variation for non-estimable fields, and add blinded adjudication for disagreement-heavy pairs. A confirmatory extension should sample at least 800-1200 reviewed candidate pairs across descriptor scope, rank stratum, quality stratum, same/different identity audit status, and PF-ERI admission level, with query-clustered or identity-clustered uncertainty analysis. A later Bobcat identity validation would require audited individual labels or audited same/different pair labels before any identity-performance claim. A later risk-control version should predefine calibration splits, route thresholds, loss functions, and target risk levels before testing. These extensions would support the evidence-governance system without changing the core scientific object.

PF-ERI reframes a familiar wildlife Re-ID workflow as an evidence chain. A descriptor-retrieved pair is not ready for ecological use merely because it looks close to a query. The pair must contain comparable, reviewable visual evidence. In the reviewed CzechLynx validation setting, PF-ERI measured that missing pair-level decision and routed weaker evidence away from the immediate review path.

## Data And Code Availability

Data and code availability statement: [to be completed before submission]. The current manuscript draft refers to repository artifacts under `docs/modeling-validation/` and `outputs/modeling-validation/`. Any public release should include the exact frozen manifests, reviewed pair tables permitted by dataset licenses, scripts used to generate the model and routing outputs, and a reproducibility README.

## Ethics Statement

Ethics statement: [to be completed before submission]. The manuscript should report the provenance and license terms for CzechLynx and any Bobcat data, and should state that PF-ERI does not automate management decisions or assign final identities without expert review.

## Author Contributions

Author contributions: [to be completed].

## Competing Interests

Competing interests: [to be completed].

## Generated Display Items

Final manuscript-ready captions and table notes are recorded in `docs/manuscript/2026-07-10_pferi_display_captions_and_table_notes.md`. The generated Figure 2-4 and Table 1-3 files are stored under `outputs/manuscript/2026-07-10_pferi_figures_tables/`, with source-data lineage recorded in `outputs/manuscript/2026-07-10_pferi_figures_tables/manuscript_figures_tables_audit.json` and `outputs/manuscript/2026-07-10_pferi_source_data_package/`.

Figure 1. PF-ERI formalizes pair-level evidence admission after strong descriptor retrieval. Source concept figure: `outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.svg`. Harmonization note: `docs/manuscript/2026-07-10_figure1_harmonization_note.md`.

Figure 2. Reviewability model comparison on the reviewed CzechLynx candidate-pair table. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.svg`, `outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.pdf`, and `outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.png`.

Figure 3. Quality and descriptor-similarity sensitivity analyses. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.svg`, `outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.pdf`, and `outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.png`.

Figure 4. Fixed-budget review utility and pre-inference evidence hygiene. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.svg`, `outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.pdf`, and `outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.png`.

Table 1. Dataset and validation contract. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/table1_dataset_validation_contract.csv` and `outputs/manuscript/2026-07-10_pferi_figures_tables/table1_dataset_validation_contract.md`.

Table 2. Pooled and descriptor-specific model comparison. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/table2_model_comparison.csv` and `outputs/manuscript/2026-07-10_pferi_figures_tables/table2_model_comparison.md`.

Table 3. Review routing and evidence hygiene. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/table3_review_routing_evidence_hygiene.csv` and `outputs/manuscript/2026-07-10_pferi_figures_tables/table3_review_routing_evidence_hygiene.md`.

## References

Adam, L., Cermak, V., Papafitsoros, K., and Picek, L. (2025). WildlifeReID-10k: Wildlife re-identification dataset with 10k individual animals. *IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops*. https://openaccess.thecvf.com/content/CVPR2025W/FGVC/papers/Adam_WildlifeReID-10k_Wildlife_re-identification_dataset_with_10k_individual_animals_CVPRW_2025_paper.pdf

Angelopoulos, A. N., Bates, S., Fisch, A., Lei, L., and Schuster, T. (2024). Conformal risk control. *International Conference on Learning Representations*. https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf

Blount, D., Gero, S., Van Oast, J., Parham, J., and others. (2022). Flukebook: An open-source AI platform for cetacean photo identification. *Mammalian Biology*. https://doi.org/10.1007/s42991-021-00221-3

Cermak, V., Picek, L., Adam, L., and Papafitsoros, K. (2024a). WildlifeDatasets: An open-source toolkit for animal re-identification. *IEEE/CVF Winter Conference on Applications of Computer Vision*. https://doi.org/10.1109/WACV57701.2024.00585

Cermak, V., Picek, L., Adam, L., Neumann, L., and Matas, J. (2024b). WildFusion: Individual animal identification with calibrated similarity fusion. arXiv:2408.12934. https://arxiv.org/abs/2408.12934

Choo, Y. R., Kudavidanage, E. P., Amarasinghe, T. R., Nimalrathna, T., Chua, M. A. H., and Webb, E. L. (2020). Best practices for reporting individual identification using camera trap photographs. *Global Ecology and Conservation*, 24, e01294. https://doi.org/10.1016/j.gecco.2020.e01294

Geifman, Y., and El-Yaniv, R. (2017). Selective classification for deep neural networks. *Advances in Neural Information Processing Systems*. https://arxiv.org/abs/1705.08500

Geifman, Y., and El-Yaniv, R. (2019). SelectiveNet: A deep neural network with an integrated reject option. *Proceedings of Machine Learning Research*. https://proceedings.mlr.press/v97/geifman19a.html

Hendrickx, K., Perini, L., Van der Plas, D., Meert, W., and others. (2024). Machine learning with a reject option: A survey. *Machine Learning*. https://doi.org/10.1007/s10994-024-06534-x

Oquab, M., Darcet, T., Moutakanni, T., Vo, H., Szafraniec, M., and others. (2023). DINOv2: Learning robust visual features without supervision. arXiv:2304.07193. https://arxiv.org/abs/2304.07193

Pereira, K. S., Gibson, L., Biggs, D., Samarasinghe, D., and others. (2022). Individual identification of large felids in field studies: Common methods, challenges, and implications for conservation science. *Frontiers in Ecology and Evolution*. https://doi.org/10.3389/fevo.2022.866403

Picek, L., Straka, J., Jirik, M., Belotti, E., Dula, M., Krausova, J., Bojda, M., Cermak, V., and others. (2026). CzechLynx: A dataset for individual identification and pose estimation of the Eurasian lynx. *Scientific Data*, 13, 511. https://doi.org/10.1038/s41597-026-06853-9

Schneider, S., Taylor, G. W., Linquist, S., and Kremer, S. C. (2019). Past, present and future approaches using computer vision for animal re-identification from camera trap data. *Methods in Ecology and Evolution*. https://doi.org/10.1111/2041-210X.13133

Tuia, D., Kellenberger, B., Beery, S., Costelloe, B. R., and others. (2022). Perspectives in machine learning for wildlife conservation. *Nature Communications*. https://doi.org/10.1038/s41467-022-27980-y

Vidal, M., Wolf, N., Rosenberg, B., Harris, B. P., Mathis, A., and others. (2021). Perspectives on individual animal identification from biology and computer vision. *Integrative and Comparative Biology*. https://doi.org/10.1093/icb/icab107

Villon, S., Mouillot, D., Chaumont, M., Subsol, G., and others. (2020). A new method to control error rates in automated species identification with deep learning algorithms. *Scientific Reports*. https://doi.org/10.1038/s41598-020-67573-7

Whytock, R. C., Swiezewski, J., Zwerts, J. A., Bara-Slupski, T., and others. (2021). Robust ecological analysis of camera trap data labelled by a machine learning model. *Methods in Ecology and Evolution*. https://doi.org/10.1111/2041-210X.13576

Wildbook. (2026a). Matching process documentation. Accessed July 9, 2026. https://wildbook.docs.wildme.org/data/matching-process.html

Wildbook. (2026b). Image analysis pipeline documentation. Accessed July 9, 2026. https://wildbook.docs.wildme.org/introduction/image-analysis-pipeline.html
