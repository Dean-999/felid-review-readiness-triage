# Core Incremental Model Evidence

Date: 2026-07-09

Status: `PASS`

This result addresses the central modeling question in the current project story: whether PF-ERI carries pair-level evidence-admission signal after a strong descriptor has already returned a candidate pair. The endpoint is human reviewability and evidential admissibility on CzechLynx reviewed pairs. The endpoint is not identity accuracy, retrieval ranking quality, Bobcat identity performance, mean average precision, mean reciprocal rank, or top-k identity improvement.

All six model families were evaluated on identical row sets within each scope. The pooled scope uses the combined reviewed candidate-pair table, and the descriptor-specific scopes repeat the same comparison separately for MegaDescriptor and DINOv2. Each model is an interpretable L2 logistic validation model evaluated by component-group cross-validation, with AUROC, AUPRC, Brier score, five-bin expected calibration error, and bootstrap intervals for AUROC and AUPRC.

In the pooled analysis, the descriptor_only model achieved AUROC 0.585 (95% bootstrap CI 0.531-0.641), AUPRC 0.775 (95% bootstrap CI 0.728-0.829), Brier score 0.215, and five-bin ECE 0.075.
In the pooled analysis, the quality_only model achieved AUROC 0.724 (95% bootstrap CI 0.670-0.785), AUPRC 0.809 (95% bootstrap CI 0.749-0.869), Brier score 0.183, and five-bin ECE 0.051.
In the pooled analysis, the pf_eri_evidence_only model achieved AUROC 0.740 (95% bootstrap CI 0.691-0.795), AUPRC 0.845 (95% bootstrap CI 0.795-0.892), Brier score 0.179, and five-bin ECE 0.020.
In the pooled analysis, the descriptor_plus_quality model achieved AUROC 0.772 (95% bootstrap CI 0.723-0.824), AUPRC 0.882 (95% bootstrap CI 0.840-0.918), Brier score 0.178, and five-bin ECE 0.060.
In the pooled analysis, the descriptor_plus_quality_plus_pf_eri model achieved AUROC 0.786 (95% bootstrap CI 0.741-0.839), AUPRC 0.885 (95% bootstrap CI 0.845-0.923), Brier score 0.167, and five-bin ECE 0.018.

The strongest active-control comparison is the full model against descriptor plus quality. In the pooled table, adding PF-ERI features to descriptor similarity and image-quality controls changed AUROC by 0.014 and AUPRC by 0.003. PF-ERI evidence alone exceeded the quality-only control by AUROC 0.017 and AUPRC 0.035. The descriptor-specific active-control increments were not uniformly positive: megadescriptor_l_384 changed AUROC by -0.005 and AUPRC by -0.002. dinov2_vitl14 changed AUROC by -0.008 and AUPRC by -0.016. This pattern supports the bounded statement that PF-ERI carries reviewability-relevant pair evidence, while the incremental advantage over a descriptor-plus-quality control is small in the pooled table and requires the planned quality and similarity sensitivity package before it should be treated as a strong standalone superiority claim.

The interpretation remains deliberately bounded. These models test whether pair-level evidence features align with human reviewability labels after descriptor retrieval. They do not establish automatic individual identification, they do not validate Bobcat identity labels, and they do not claim that PF-ERI improves mAP, MRR, or top-k identity retrieval. The paper-ready table for this issue is the source of truth for the incremental model evidence.

## Artifact Links

The paper-ready comparison table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue3/issue3_core_incremental_model_comparison.csv`. The full validation metrics table is `archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_model_metrics.csv`. The calibration bins are `archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_calibration_bins.csv`. The Issue 3 audit file is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue3/issue3_core_incremental_model_evidence_audit.json`.
