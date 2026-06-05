# Daily Work Log

## Purpose

This file records daily project progress, problems, repairs, and decisions.

It is not a personal diary. It is a research audit trail.

The goal is to show:

- what was done each day;
- what problem appeared;
- how the problem was repaired;
- what decision was made;
- what evidence or file changed;
- what remains unresolved.

This log will be useful for mentor meetings, paper writing, science fair process documentation, and project management.

## Logging Rule

Add one entry for every day when project work happens.

Each entry should be short but specific.

Do not write vague entries such as:

```text
Worked on project.
```

Write entries such as:

```text
Revised the triage rubric to separate species-level tagging from individual-level Re-ID readiness. Added side_comparability and night_ir_artifact as required fields because field images may be species-identifiable but not comparable for identity review.
```

## Daily Entry Template

```markdown
## YYYY-MM-DD

### Work Completed

- 

### Problem Encountered

- 

### Repair / Decision

- 

### Files Changed

- 

### Evidence / Source Notes

- 

### Remaining Risk

- 

### Next Action

- 
```

## Backfilled Initial Entries

## 2026-05-31

### Work Completed

- Narrowed the project from a broad ReID-Audit direction to Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images.
- Locked the project around two research questions: Q1 reliability and Q2 risk–coverage trade-off.
- Defined CzechLynx as the quantitative known-ID validation carrier.
- Defined UWIN/WildTrax Bobcat and Canada Lynx as field motivation and field-readiness stress test data.
- Defined Marbled Cat as a future Asian conservation application scenario only.

### Problem Encountered

- The original ReID-Audit direction was too broad and overlapped with mature animal Re-ID work.
- It risked being misunderstood as a new Re-ID model, a full identity prediction system, or a population estimation project.

### Repair / Decision

- Removed new model claims, SOTA claims, universal threshold claims, full website claims, RUDI claims, and true individual identity claims.
- Reframed Re-ID as an auxiliary measurement signal.
- Required all false-match language to use the phrase pairwise false-match risk proxy under known-ID validation.

### Files Changed

- docs/phase0/project_scope.md
- docs/phase0/research_questions.md
- docs/phase0/data_roles.md
- docs/phase0/claims_and_boundaries.md
- docs/phase0/evidence_chain.md
- docs/phase0/phase0_decision_log.md

### Evidence / Source Notes

- Existing animal Re-ID work is mature, so the project must focus on a pre-Re-ID review-readiness gate.
- Field tagging experience through UWIN-Atlanta provides the practical motivation.

### Remaining Risk

- The rubric may still look subjective unless Phase 1 defines observable fields.
- CzechLynx license and exact dataset version still need to be verified.

### Next Action

- Start Phase 1: data access notes, triage rubric, CzechLynx sampling plan, WildTrax field triage plan, Marbled Cat future application note, and Go/No-Go criteria.

## 2026-06-01

### Work Completed

- Drafted Phase 1 documentation structure.
- Added a formal daily work log mechanism.
- Defined `review-ready`, `review-limited`, and `unidentifiable` as primary triage labels.
- Added required supporting fields including blur level, occlusion level, lighting condition, night IR artifact, visible side, side comparability, visible region, pattern visibility, metadata completeness, confidence, uncertainty flag, exclusion reason, and notes.

### Problem Encountered

- The label `review-limited` could become too vague if not tied to specific observable fields.
- The project could confuse species-level tagging with individual-level Re-ID readiness.
- WildTrax/UWIN images have field value but lack verified individual IDs.

### Repair / Decision

- Required every triage label to be supported by observable fields.
- Added explicit rule: species-level usable does not mean Re-ID-ready.
- Restricted WildTrax/UWIN to field-readiness distribution and failure-mode analysis.
- Kept CzechLynx as the only current strict validation source.

### Files Changed

- docs/phase1/triage_rubric.md
- docs/phase1/czechlynx_data_access_notes.md
- docs/phase1/czechlynx_sampling_plan.md
- docs/phase1/wildtrax_field_triage_plan.md
- docs/phase1/marbled_cat_application_readiness_note.md
- docs/phase1/phase1_go_no_go_criteria.md
- docs/logs/daily_work_log.md

### Evidence / Source Notes

- CzechLynx provides the known-ID validation path.
- WildTrax/UWIN tagging experience provides field motivation.
- Marbled Cat remains future application only.

### Remaining Risk

- CzechLynx exact license and local file counts still need to be verified after download.
- WildTrax public image display permission should still be confirmed before public release.
- The rubric needs a pilot second-review consistency check.

### Next Action

- Complete CzechLynx access audit.
- Create the first CzechLynx pilot triage CSV.
- Triage 100-200 pilot images without viewing individual IDs.
- Re-triage 30 images after 48 hours for consistency.


## 2026-06-01

### Work Completed

- Completed a local CzechLynx technical access audit.
- Verified that `CzechLynxDataset-Metadata-Real.csv` contains 39,760 rows.
- Verified that `CzechLynxDataset-Metadata-Synthetic.csv` contains 40,000 rows.
- Confirmed that the real metadata contains 319 unique `unique_name` values, 18,782 unique encounters, 86 unique locations, and 659 unique trap IDs.
- Confirmed that the first 1,000 real metadata image paths exist locally.
- Confirmed that the first 100 real images are readable with PIL.
- Confirmed the presence of split fields: `split-geo_aware`, `split-time_open`, `split-time_closed`, and `split-pose`.

### Problem Encountered

- The dataset contains both real and synthetic images.
- The dataset includes sensitive location columns such as latitude and longitude.
- The exact license, citation format, redistribution rules, and public image display permission are still pending.
- The metadata field `unique_name` appears to function as the individual ID field, but this should still be confirmed against dataset documentation.

### Repair / Decision

- Decided that primary Q1/Q2 validation will use only `CzechLynxDataset-Metadata-Real.csv`.
- Synthetic images will be excluded from primary validation.
- Treated `unique_name` as the working individual ID field for sampling and pair construction.
- Decided that exact latitude/longitude should not be published unless permission is explicitly confirmed.
- Updated CzechLynx status to Conditional Go for internal sampling, but No-Go for public image display until license/display permissions are verified.

### Files Changed

- docs/phase1/czechlynx_data_access_notes.md
- docs/phase1/phase1_go_no_go_criteria.md
- docs/logs/daily_work_log.md

### Evidence / Source Notes

- Local audit showed 39,760 real metadata rows and 319 unique working individual IDs.
- First 1,000 metadata paths existed locally.
- First 100 real images were readable.
- Split fields are available for geo-aware and time-aware analysis.

### Remaining Risk

- License and citation still need to be recorded.
- Public display permission is not yet confirmed.
- `unique_name` should be confirmed against official dataset documentation before final paper wording.
- Sampling must avoid overrepresenting high-count individuals such as `lynx_278`.

### Next Action

- Create a clean CzechLynx real manifest file.
- Generate a blinded pilot triage CSV with 100-200 images.
- Avoid showing `unique_name`, latitude, longitude, and exact location during triage.

## 2026-06-02 — Completed CzechLynx Pilot Triage and Final Audit

### Work completed

Completed the full 200-image CzechLynx blinded pilot triage. Each image was manually labeled using the review-readiness rubric with three possible triage labels: `review-ready`, `review-limited`, and `unidentifiable`.

The final 200-image label distribution was:

- `review-ready`: 34 images
- `review-limited`: 107 images
- `unidentifiable`: 59 images

Ran the final CzechLynx triage consistency audit. The audit confirmed:

- 200 total rows
- 200 labeled rows
- required fields complete
- allowed values valid
- logical consistency checks passed

The final audit result was `PASS`.

### Problems encountered

Several CSV and spreadsheet workflow issues occurred during manual labeling:

- Apple Numbers converted the working CSV into a Numbers/Zip-style document while keeping the `.csv` filename.
- Some exported CSV files included table-title/header issues.
- Some early labels used inconsistent controlled vocabulary values such as `high_exposure` instead of `overexposed`.
- Some early rows had logical inconsistencies, such as `full_body` with `body_fraction_visible = 0-25`.

### Fixes applied

Resolved the CSV corruption issue by exporting from Numbers as UTF-8 CSV and validating the exported file before continuing.

Updated the label consistency workflow so that:

- `exclusion_reason` is a required controlled field.
- `notes` are optional.
- `review-ready` uses `exclusion_reason = none`.
- `review-limited` and `unidentifiable` require concrete limitation or exclusion reasons.
- consistency audits catch impossible combinations such as `full_body + 0-25`.

Finalized and used `scripts/audit_czechlynx_triage_consistency.py` to enforce rubric consistency.

### Files and outputs created or updated

Relevant local data outputs:

- `data/labels/czechlynx/czechlynx_pilot_triage_working.csv`
- `data/labels/czechlynx/czechlynx_pilot_triage_final.csv`
- `outputs/czechlynx/qc/triage_consistency_final200_report.txt`

Relevant scripts:

- `scripts/audit_czechlynx_triage_consistency.py`

### Second-review preparation

Prepared a 30-image stratified second-review subset for intra-reviewer consistency checking. The subset was designed to include:

- 10 `review-ready` images
- 10 `review-limited` images
- 10 `unidentifiable` images

Created neutral second-review filenames to reduce memory and label leakage.

Created and verified:

- `scripts/prepare_czechlynx_second_review_subset.py`
- `scripts/audit_czechlynx_second_review_blinding.py`
- `scripts/compare_czechlynx_second_review_consistency.py`

The second-review blinding audit returned `PASS`.

### Current status at end of day

Phase 1 manual triage is complete. The 200-image final audit passed. The second-review subset is prepared but should not be labeled immediately. A delayed second-review step will be completed later to reduce memory contamination.

### Next steps

- Wait before labeling the second-review subset.
- Do not open second-review images or internal mapping before the delayed review.
- Continue project work through documentation, citation/license verification, and Phase 2/3 planning.

## 2026-06-03 — Phase 2/3 Planning, Pair Construction, License Audit, and Mentor-Facing Documentation

### Work completed

Built the Phase 2 data-engineering foundation for CzechLynx known-ID validation.

Created and verified:

- `scripts/build_czechlynx_validation_table.py`
- `scripts/construct_czechlynx_pair_sets.py`
- `scripts/audit_czechlynx_pair_sets.py`
- `scripts/check_czechlynx_embedding_inputs.py`

The Phase 2 validation table and pair set were successfully generated.

Validation table summary:

- 200 validation rows
- 100 unique working individual IDs
- 2 images per ID

Pair set summary:

- 400 total pairs
- 100 same-individual pairs
- 300 fixed-seed sampled different-individual pairs

The pair audit returned `PASS`. The embedding input check also returned `PASS`.

### Phase 2 planning documents created

Created Phase 2 planning documentation:

- `docs/phase2/phase2_validation_plan.md`
- `docs/phase2/embedding_baseline_selection.md`
- `docs/phase2/metrics_plan.md`

These documents define how the project will later test whether `review-ready` images show stronger same/different Re-ID similarity separation than lower-readiness images. No embedding extraction or model inference was run yet.

### Phase 3 planning completed

Created:

- `docs/phase3/risk_coverage_policy_plan.md`

This document defines the planned risk-coverage policy comparison:

- No filter: all images enter candidate review.
- Balanced filter: `review-ready` plus selected `review-limited` images enter candidate review.
- Strict filter: only `review-ready` images enter candidate review.

The plan defines retained evidence metrics and pairwise false-match risk proxy metrics, but no Phase 3 result analysis has been executed yet.

### License and citation audit progress

Created and updated:

- `docs/phase1/czechlynx_license_and_citation_audit.md`

Reviewed CzechLynx source information from the Scientific Data paper, Zenodo dataset page, Kaggle mirror, and arXiv preprint.

Confirmed that the Scientific Data paper is the primary paper citation source. The paper describes CzechLynx as an open-access dataset for individual identification, pose estimation, and instance segmentation of Eurasian lynx, with 39,760 real camera-trap images and 319 unique individuals. :contentReference[oaicite:0]{index=0}

Confirmed from the Zenodo page screenshot that the dataset record is `CzechLynx Dataset (v1.0)`, DOI `10.5281/zenodo.17592004`, and the dataset license is Creative Commons Attribution 4.0 International (`CC BY 4.0`).

Separated the article license from the dataset license:

- Scientific Data article license: `CC BY-NC-ND 4.0`
- Zenodo dataset license: `CC BY 4.0`

Project policy remains conservative:

- Do not commit raw images.
- Do not publish contact sheets.
- Do not publish exact coordinates, trap IDs, cell codes, or sensitive location metadata.
- Do not place raw CzechLynx images in the public GitHub README for now.
- Mentor-only slides and poster examples may use a small number of images only with proper attribution.

### Mentor-facing documentation

Created:

- `docs/mentor_updates/mentor_progress_update_001.md`

Updated:

- `README.md`

The README now includes:

- project title
- one-sentence definition
- core boundary
- Q1/Q2 research questions
- data roles
- completed and pending status
- repository safety rules
- folder structure
- explicit “No Final Claims Yet” section

### Problems encountered

The main unresolved issue is not technical code failure but research sequencing. The project now has enough infrastructure to begin embedding work, but the delayed second-review consistency check is still pending.

### Current status at end of day

The project now has:

- completed 200-image manual triage
- final audit `PASS`
- prepared second-review subset and blinding audit `PASS`
- Phase 2 validation table and pair set ready
- Phase 2 planning docs complete
- Phase 3 risk-coverage plan complete
- license/citation audit mostly verified
- mentor-facing README and progress update created

No model inference, embedding extraction, final similarity analysis, or final scientific claims were made.

### Next steps

- Complete the delayed 30-image second-review labeling after the waiting period.
- Run `scripts/compare_czechlynx_second_review_consistency.py`.
- Interpret intra-reviewer consistency.
- After the second-review gate is complete, begin Phase 2 embedding extraction and pair similarity validation.
- Continue keeping raw data, generated images, contact sheets, internal mappings, and output reports out of Git.


## 2026-06-05 — Second-Review Completion, Phase 2 Reliability Analysis, and Phase 3 Risk–Coverage Results

### Work Completed

- Completed the delayed 30-image CzechLynx second-review labeling step.
- Ran the second-review blinding audit and confirmed that the second-review CSV remained blinded.
- Ran the second-review consistency comparison script.
- Created `docs/phase1/czechlynx_second_review_consistency_summary.md`.
- Completed Phase 2 embedding extraction using a fixed generic ResNet-50 ImageNet baseline.
- Extracted embeddings for all 200 CzechLynx pilot images.
- Computed cosine similarities for all 400 constructed image pairs.
- Ran the Phase 2 similarity output audit and confirmed `RESULT: PASS`.
- Implemented and ran the Phase 2 Re-ID reliability analysis.
- Created `docs/phase2/phase2_reliability_analysis_notes.md`.
- Created `docs/phase2/phase2_reliability_results_summary.md`.
- Implemented and ran the Phase 3 risk–coverage policy analysis.
- Created `docs/phase3/phase3_risk_coverage_results_notes.md`.
- Created `docs/phase3/phase3_risk_coverage_results_summary.md`.

### Problem Encountered

- The second-review consistency check showed that some boundary image decisions remain unstable.
- Supporting fields such as `side_comparability`, `pattern_visibility`, and `exclusion_reason` were less stable than the main `triage_label`.
- The Phase 2 ResNet-50 baseline produced only weak-to-moderate overall same/different separation.
- The `ready_ready` group showed a positive signal, but the pair count was sparse.
- The Phase 3 strict filter reduced pairwise false-positive proxy counts strongly, but retained very little known same-individual evidence.

### Repair / Decision

- Accepted the second-review result as pilot-level intra-reviewer consistency evidence.
- Kept `data/labels/czechlynx/czechlynx_pilot_triage_final.csv` unchanged.
- Decided that Phase 1 is acceptable for pilot-level Phase 2 progression.
- Treated Phase 2 results as preliminary validation under a fixed generic embedding baseline, not as final animal-identification evidence.
- Interpreted Q1 as partial / mixed support rather than strong proof.
- Interpreted Q2 as a risk–coverage trade-off rather than a simple strict-filter success.
- Decided that the most defensible workflow interpretation is tiered review:
  - `review-ready`: high-confidence candidate Re-ID review;
  - `review-limited`: secondary or cautious manual review;
  - `unidentifiable`: excluded from individual-level Re-ID review.

### Files Changed

Documentation:

- `docs/phase1/czechlynx_second_review_consistency_summary.md`
- `docs/phase2/phase2_reliability_analysis_notes.md`
- `docs/phase2/phase2_reliability_results_summary.md`
- `docs/phase3/phase3_risk_coverage_results_notes.md`
- `docs/phase3/phase3_risk_coverage_results_summary.md`
- `docs/logs/daily_work_log.md`

Scripts:

- `scripts/extract_czechlynx_embeddings.py`
- `scripts/compute_czechlynx_pair_similarities.py`
- `scripts/audit_czechlynx_similarity_outputs.py`
- `scripts/analyze_czechlynx_phase2_reid_reliability.py`
- `scripts/analyze_czechlynx_phase3_risk_coverage.py`

Generated local outputs, not committed:

- `data/interim/czechlynx/czechlynx_pilot_embeddings.parquet`
- `data/interim/czechlynx/czechlynx_pair_similarities.csv`
- `outputs/czechlynx/qc/second_review_consistency_report.txt`
- `outputs/czechlynx/qc/phase2_reliability_report.txt`
- `outputs/czechlynx/qc/phase3_risk_coverage_report.txt`
- `outputs/czechlynx/analysis/phase2_overall_similarity_summary.csv`
- `outputs/czechlynx/analysis/phase2_readiness_group_similarity_summary.csv`
- `outputs/czechlynx/analysis/phase2_threshold_proxy_summary.csv`
- `outputs/czechlynx/analysis/phase3_policy_comparison.csv`
- `outputs/czechlynx/analysis/phase3_threshold_policy_summary.csv`
- `outputs/czechlynx/figures/phase2_same_different_similarity_histogram.png`
- `outputs/czechlynx/figures/phase2_readiness_group_similarity_boxplot.png`
- `outputs/czechlynx/figures/phase3_policy_retained_evidence_bar_chart.png`
- `outputs/czechlynx/figures/phase3_policy_false_positive_proxy_bar_chart.png`

### Evidence / Source Notes

- Second-review blinding audit result: `PASS`.
- Second-review reviewed rows: 30.
- Exact `triage_label` agreement: 24/30 = 0.800.
- Cohen's kappa for `triage_label`: 0.700.
- `pattern_visibility` agreement: 20/30 = 0.667.
- `side_comparability` agreement: 16/30 = 0.533.
- `exclusion_reason` agreement: 20/30 = 0.667.
- Phase 2 embedding baseline: `torchvision_resnet50_imagenet1k_v2_penultimate_cached`.
- Phase 2 device: `mps`.
- Embeddings extracted: 200/200.
- Embedding dimension: 2048.
- Pair similarities computed: 400/400.
- Phase 2 overall same-individual mean similarity: 0.579955.
- Phase 2 overall different-individual mean similarity: 0.493990.
- Phase 2 overall same-minus-different gap: 0.085966.
- Phase 2 ROC-AUC: 0.618667.
- `ready_ready` mean gap: 0.119379.
- `limited_limited` mean gap: 0.035978.
- Phase 3 no-filter policy retained 100% of images, identities, and same-individual pairs.
- Phase 3 balanced filter retained 70.5% of images, 86% of identities, and 55% of same-individual pairs.
- Phase 3 strict filter retained 17% of images, 31% of identities, and 3% of same-individual pairs.
- Strict filtering reduced pairwise false-positive proxy counts most strongly, but with severe evidence loss.

### Remaining Risk

- The second-review subset is small and measures intra-reviewer consistency only, not independent inter-rater reliability.
- Supporting fields are less stable than the main `triage_label`.
- The ResNet-50 baseline is generic and not wildlife-specialized.
- Phase 2 results provide weak-to-moderate separation, not strong Re-ID validation.
- The `ready_ready` group has sparse pair counts.
- Phase 3 thresholds are pilot-specific and model-specific.
- Pairwise false-positive proxy counts are not real-world false-match rates.
- The current results should not be described as field deployment readiness.

### Next Action

- Commit documentation and scripts only.
- Do not commit `data/`, `outputs/`, raw images, generated figures, embeddings, pair similarities, internal mappings, or label CSVs.
- Prepare a mentor-facing results update summarizing Phase 1, Phase 2, and Phase 3.
- Begin a paper-style project report draft with conservative interpretation.
- Consider a future wildlife-specialized embedding baseline comparison, such as a MegaDescriptor / WildlifeDatasets-based baseline.


## 2026-06-06 — Colab MegaDescriptor Baseline Integration and Phase 3B Analysis

### Work Completed

- Exported a sanitized Colab package for the CzechLynx wildlife-specialized baseline extension.
- Uploaded the sanitized package to Colab and ran fixed pretrained MegaDescriptor-S-224 inference.
- Extracted MegaDescriptor-S-224 embeddings for all 200 CzechLynx pilot images.
- Computed MegaDescriptor-S-224 cosine similarities for all 400 pilot pairs.
- Compared the generic ResNet-50 ImageNet baseline with the wildlife-specialized MegaDescriptor-S-224 baseline.
- Copied Colab outputs back into the local repository under `outputs/`.
- Created and ran a local audit script for the Colab MegaDescriptor outputs.
- Ran Phase 3B MegaDescriptor-specific risk–coverage analysis.
- Created local Phase 3B output tables, reports, and figures.
- Prepared mentor-facing interpretation for the new MegaDescriptor results.

### Problem Encountered

- Google Colab initially had runtime and Google Drive mount issues.
- The Colab workflow required switching from Drive-mounted package loading to direct package upload and output download.
- Colab outputs needed local audit because notebook execution is less reproducible than a pure local script.
- MegaDescriptor cosine values used a different embedding scale than ResNet-50, so ResNet-50 thresholds could not be reused.

### Repair / Decision

- Used a sanitized Colab package instead of uploading the full CzechLynx dataset.
- Avoided using raw paths, `unique_name`, location metadata, trap IDs, cell codes, and second-review mapping in the Colab package.
- Treated MegaDescriptor outputs as local generated outputs and kept them uncommitted.
- Added a local audit step for Colab output completeness and consistency.
- Used MegaDescriptor-specific quantile thresholds for Phase 3B.
- Interpreted MegaDescriptor as a fixed wildlife-specialized measurement baseline, not as an identity-decision model.
- Decided that MegaDescriptor strengthens Q1 from partial / mixed support to moderate pilot-level support.
- Decided that Phase 3B strengthens the tiered workflow interpretation.

### Files Changed

Scripts:

- `scripts/audit_czechlynx_colab_megadescriptor_outputs.py`
- `scripts/analyze_czechlynx_phase3_risk_coverage_megadescriptor.py`

Documentation:

- `docs/phase2/baseline_comparison_results_summary.md`
- `docs/phase3/phase3_megadescriptor_risk_coverage_plan.md`
- `docs/phase3/phase3_megadescriptor_risk_coverage_results_summary.md`
- `docs/mentor_updates/mentor_progress_update_003.md`
- `docs/logs/daily_work_log.md`

Generated local outputs, not committed:

- `outputs/czechlynx/colab_megadescriptor/czechlynx_wildlife_baseline_outputs/czechlynx_pilot_embeddings_megadescriptor_s224.parquet`
- `outputs/czechlynx/colab_megadescriptor/czechlynx_wildlife_baseline_outputs/czechlynx_pair_similarities_megadescriptor_s224.csv`
- `outputs/czechlynx/colab_megadescriptor/czechlynx_wildlife_baseline_outputs/phase2_baseline_comparison.csv`
- `outputs/czechlynx/colab_megadescriptor/czechlynx_wildlife_baseline_outputs/phase2_baseline_readiness_group_comparison.csv`
- `outputs/czechlynx/colab_megadescriptor/czechlynx_wildlife_baseline_outputs/phase2_baseline_comparison_report.txt`
- `outputs/czechlynx/qc/megadescriptor_colab_output_audit.txt`
- `outputs/czechlynx/qc/phase3_megadescriptor_risk_coverage_report.txt`
- `outputs/czechlynx/analysis/phase3_megadescriptor_policy_comparison.csv`
- `outputs/czechlynx/analysis/phase3_megadescriptor_threshold_policy_summary.csv`
- `outputs/czechlynx/figures/phase3_megadescriptor_policy_retained_evidence_bar_chart.png`
- `outputs/czechlynx/figures/phase3_megadescriptor_policy_false_positive_proxy_bar_chart.png`

### Evidence / Source Notes

- Colab MegaDescriptor output audit result: `PASS`.
- MegaDescriptor pair similarity rows: 400.
- MegaDescriptor same-individual pairs: 100.
- MegaDescriptor different-individual pairs: 300.
- MegaDescriptor embeddings: 200 pilot images.
- ResNet-50 ROC-AUC: 0.618667.
- MegaDescriptor-S-224 ROC-AUC: 0.690400.
- ResNet-50 same-minus-different gap: 0.085966.
- MegaDescriptor-S-224 same-minus-different gap: 0.117479.
- MegaDescriptor AUC gain: 0.071733.
- MegaDescriptor gap gain: 0.031513.
- Relative gap increase: approximately 36.7%.
- MegaDescriptor Phase 3B no-filter gap: 0.117479.
- MegaDescriptor Phase 3B balanced-filter gap: 0.108253.
- MegaDescriptor Phase 3B strict-filter gap: 0.207133.
- MegaDescriptor-specific thresholds:
  - 0.50 quantile: 0.116324
  - 0.75 quantile: 0.194070
  - 0.90 quantile: 0.348698
  - 0.95 quantile: 0.459079

### Remaining Risk

- The pilot still uses only 200 images.
- The `ready_ready` group remains sparse.
- Strict filtering still retains only 3 same-individual pairs.
- MegaDescriptor may still capture background or encounter-level similarity.
- Colab inference requires careful local audit documentation for reproducibility.
- Thresholds are model-specific and pilot-specific.
- The result is not a real-world false-match rate.
- The result does not prove true individual identification or field deployment readiness.

### Next Action

- Commit scripts and documentation only.
- Do not commit `outputs/`, `data/`, embeddings, pair similarities, generated figures, or Colab packages.
- Update the paper-style project report draft with MegaDescriptor Phase 2B and Phase 3B results.
- Update the mentor package index to include the new MegaDescriptor documents.
- Plan a larger-pair or larger-image extension to stabilize the `ready_ready` result.