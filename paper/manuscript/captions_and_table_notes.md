# PF-ERI Manuscript Display Captions And Table Notes

Date: 2026-07-10

Status: `ISSUE_1_COMPLETE`

Issue source:

```text
docs/project-governance/executable-plans/plans/2026-07-10-manuscript-submission-readiness-issue-pack.md
```

Claim boundary:

```text
These captions and notes describe CzechLynx human reviewability / evidential
admissibility, review routing, and transfer-stress evidence allocation. They do
not claim automated identity assignment, Bobcat identity accuracy, retrieval
mAP, MRR, top-k identity improvement, or universal cross-domain risk control.
```

## Figure Captions

**Figure 1. PF-ERI separates candidate retrieval from pair-level evidence admission.** A strong upstream descriptor first retrieves visually similar candidate images from an archive. PF-ERI then evaluates each retrieved query-candidate pair as an evidential object: whether the two images contain comparable visual information for responsible human review. The layer can route pairs into admitted, cautious review, conflict review, deferred low-evidence, or non-comparable evidence states before expert review or downstream ecological use. The figure illustrates the manuscript's central distinction: descriptor similarity can generate a candidate queue, but similarity alone does not establish that a pair is admissible evidence. PF-ERI is therefore shown as a post-retrieval evidence-governance layer, not as a new descriptor and not as an automated identity classifier. Source file: `outputs/modeling-validation/story-hardening-issue1/figure1_pair_level_evidence_admission_chain.svg`.

**Figure 2. PF-ERI evidence aligns with human reviewability, while strict active-control increments remain bounded.** Model comparisons were performed on the reviewed CzechLynx candidate-pair validation table, with human reviewability / evidential admissibility as the endpoint. Panel A shows pooled AUROC and AUPRC with 95% bootstrap confidence intervals for descriptor-only, quality-only, PF-ERI evidence-only, descriptor plus quality, descriptor plus PF-ERI, and descriptor plus quality plus PF-ERI models evaluated on identical rows. Panel B shows the strict active-control comparison: adding PF-ERI to descriptor plus quality produced a small positive pooled increment, but descriptor-specific increments were mixed and should not be interpreted as universal superiority over descriptor plus quality. Panel C reports pooled calibration diagnostics using Brier score and five-bin expected calibration error, where lower values indicate better calibration. The figure supports a bounded reviewability signal claim: PF-ERI captures pair-level evidence relevant to reviewability, but the display does not report identity accuracy, retrieval mAP, MRR, top-k identity improvement, or Bobcat identity performance. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.svg`, `outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.pdf`, and `outputs/manuscript/2026-07-10_pferi_figures_tables/figure2_model_comparison.png`.

**Figure 3. Quality and descriptor-similarity sensitivity analyses test the main proxy explanations.** The sensitivity analyses ask whether PF-ERI is merely an image-quality proxy or a descriptor-similarity proxy. Panel A compares high versus low PF-ERI pair signal within pooled quality-matched strata. Panel B repeats the comparison in the high-quality and high-similarity subsets for the pooled table and each descriptor scope. The DINOv2 high-quality subset is retained as a visible boundary because its high-minus-low PF-ERI contrast is negative, preventing an overbroad universal claim. Panel C shows pooled rank/similarity strata in which the high-minus-low PF-ERI reviewability contrast was estimable; sparse or non-splittable strata are not converted into positive evidence. Together, these analyses support the narrower interpretation that quality and similarity do not fully exhaust the human reviewability construct in the reviewed CzechLynx candidate pairs. They do not prove that every PF-ERI feature mechanism is independently validated or that PF-ERI universally outperforms descriptor plus quality. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.svg`, `outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.pdf`, and `outputs/manuscript/2026-07-10_pferi_figures_tables/figure3_quality_similarity_sensitivity.png`.

**Figure 4. Selective evidence routing changes the content of a finite expert-review queue.** Fixed-budget analyses compare PF-ERI priority against descriptor-similarity priority on the same reviewed CzechLynx pair pool. Panel A reports the primary workflow endpoint: the fraction of selected pairs that were human-labeled not-ready or uncertain. Panel B reports same-ID candidate retention as a secondary known-ID audit, not as identity assignment or automated recognition accuracy. Panel C summarizes a pre-inference evidence-hygiene simulation in which pairs are admitted or deferred before downstream evidence use; admitted pairs have a higher review-ready rate, while deferred pairs concentrate not-ready or uncertain evidence. The figure supports a review-utility and evidence-routing claim under finite attention. It does not claim that PF-ERI improves identity accuracy, mAP, MRR, or top-k retrieval. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.svg`, `outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.pdf`, and `outputs/manuscript/2026-07-10_pferi_figures_tables/figure4_review_budget_utility.png`.

## Table Notes

**Table 1. Dataset and validation contract.** This table defines the evidence contract used by the manuscript. CzechLynx reviewed candidate pairs provide the known-ID validation context and the human reviewability / evidential admissibility endpoint. MegaDescriptor and DINOv2 are treated as strong upstream descriptor queues and active controls. Blind reliability packets support the stability of the reviewability construct, while Bobcat is restricted to unlabeled transfer-stress and workflow-allocation analysis. Known-ID fields are used for audit quantities such as same-ID retention, not for automated identity assignment. Bobcat identity accuracy, Bobcat false-match accuracy, retrieval mAP, MRR, top-k identity improvement, and universal cross-species threshold claims are outside the current validation contract. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/table1_dataset_validation_contract.csv` and `outputs/manuscript/2026-07-10_pferi_figures_tables/table1_dataset_validation_contract.md`.

**Table 2. Pooled and descriptor-specific model comparison.** This table reports the model comparison used to evaluate whether PF-ERI features carry human-reviewability signal after descriptor retrieval. All model families are evaluated on identical row sets within each scope. AUROC and AUPRC are reported with 95% bootstrap confidence intervals; Brier score and five-bin expected calibration error summarize calibration. The strict active-control columns compare each model with descriptor plus quality. The pooled full model shows a small positive increment over descriptor plus quality, while MegaDescriptor and DINOv2 descriptor-specific active-control increments are mixed. The table should therefore be cited as evidence that PF-ERI contains reviewability-relevant pair-level signal, not as evidence of universal superiority over descriptor plus quality and not as identity-performance evidence. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/table2_model_comparison.csv` and `outputs/manuscript/2026-07-10_pferi_figures_tables/table2_model_comparison.md`.

**Table 3. Review routing and evidence hygiene.** This table summarizes the practical review-routing outputs. The fixed-budget section compares PF-ERI priority and descriptor priority at matched review budgets using review-ready rate, not-ready/uncertain burden, same-ID retention, and false-candidate burden. Same-ID retention and false-candidate burden are known-ID audits of queue composition; they are not identity assignment, accuracy, or false-match performance. The pre-inference evidence-hygiene section summarizes admitted and deferred pair states before downstream evidence use. The table supports a workflow claim: PF-ERI can change which pairs enter immediate review or evidence use under finite attention while keeping weaker evidence in deferred routes. Generated files: `outputs/manuscript/2026-07-10_pferi_figures_tables/table3_review_routing_evidence_hygiene.csv` and `outputs/manuscript/2026-07-10_pferi_figures_tables/table3_review_routing_evidence_hygiene.md`.

## Build Audit

The display-item generation audit is:

```text
outputs/manuscript/2026-07-10_pferi_figures_tables/manuscript_figures_tables_audit.json
```

The build script is:

```text
scripts/build_manuscript_figures_tables.py
```
