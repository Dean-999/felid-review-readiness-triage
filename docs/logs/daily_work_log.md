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

## 2026-06-08 Asia/Shanghai - reconstructed

### Work Completed

- Opened Phase 4A visual-factor and mechanism-annotation infrastructure.
- Added and aligned annotation schemas for mechanism-level evidence capture.
- Built support for moving beyond coarse triage labels into more explicit visual
  reliability factors.

### Problem Encountered

- The early review-ready/review-limited/unidentifiable labels were useful but
  too coarse to explain why an image pair would or would not support individual
  Re-ID review.

### Repair / Decision

- Expanded the project toward visual mechanism annotation: body visibility,
  side/flank comparability, pattern evidence, viewpoint, and other factors that
  could later become PF-ERI components.

### Files Changed

- Phase 4A annotation infrastructure files, per commits `5570acc`, `fb901a3`,
  `4dcb13e`, `bcfba26`, `f371e6b`, and `73b6f8a`.

### Evidence / Source Notes

- Reconstructed from git commit history for 2026-06-08.

### Remaining Risk

- The richer annotation schema still needed validation against actual labeled
  images and pair-level reliability behavior.

### Next Action

- Build pair-level mechanism tables from the expanded annotation fields.

## 2026-06-11 Asia/Shanghai - reconstructed

### Work Completed

- Added Phase 4B balanced pair-level mechanism table infrastructure.
- Shifted the evidence unit from single-image readiness toward pair-level
  comparability and mechanism behavior.

### Problem Encountered

- Individual-level Re-ID risk depends on whether two images are comparable as a
  pair, not only whether each image is individually review-ready.

### Repair / Decision

- Built pair-level tables so PF-ERI could reason about weakest-image evidence,
  side compatibility, pattern comparability, and same/different pair behavior.

### Files Changed

- Phase 4B pair-level mechanism table infrastructure, per commit `67708cc`.

### Evidence / Source Notes

- Reconstructed from git commit history for 2026-06-11.

### Remaining Risk

- Pair-level signals still needed reliability analysis, uncertainty handling,
  and clear claim boundaries.

### Next Action

- Consolidate Phase 4 results and prepare mentor/manuscript materials.

## 2026-06-12 Asia/Shanghai - reconstructed

### Work Completed

- Added Phase 4D reliability mechanism analysis.
- Added Phase 4E result consolidation tables and figures.
- Added uncertainty analysis and final review pack.
- Added manuscript and mentor review materials.
- Clarified Phase 4 docs and project rules.

### Problem Encountered

- The project had accumulated evidence, but the story needed clearer separation
  between mechanism analysis, mentor-facing explanation, manuscript language, and
  blocked claims.

### Repair / Decision

- Consolidated Phase 4 evidence into tables/figures and strengthened project
  rules so the work would not be mistaken for automatic identity recognition or
  a new Re-ID model.

### Files Changed

- Phase 4D/4E analysis outputs and documentation, mentor materials, manuscript
  materials, and project rules, per commits `82416a1`, `b84286d`, `0dd16c7`,
  `d1ae4b1`, and `28ea187`.

### Evidence / Source Notes

- Reconstructed from git commit history for 2026-06-12.

### Remaining Risk

- The project still needed stronger annotation stability and a clean frozen
  label set before larger validation claims.

### Next Action

- Freeze the balanced image annotations and prepare the next PF-ERI validation
  layer.

## 2026-06-13 Asia/Shanghai - reconstructed

### Work Completed

- Froze Phase 6 v2 balanced image annotations.

### Problem Encountered

- Without a frozen annotation set, later reliability and model comparisons would
  be hard to audit or reproduce.

### Repair / Decision

- Treated the Phase 6 v2 balanced annotation table as a stable evidence
  foundation for downstream validation.

### Files Changed

- Phase 6 v2 balanced image annotation artifacts, per commit `f1d1909`.

### Evidence / Source Notes

- Reconstructed from git commit history for 2026-06-13.

### Remaining Risk

- The frozen image-level annotation set still needed to be connected to
  retrieval, pair-level evidence, and later review-routing endpoints.

### Next Action

- Continue building the later PF-ERI evidence chain from frozen annotations into
  pair/retrieval analysis.

## 2026-06-14 Asia/Shanghai - reconstructed from artifact times

### Work Completed

- Ran a dense Phase 7A/Phase 8 evidence-control and retrieval evaluation wave.
- Generated PF-ERI algorithm confidence audits, policy optimization outputs,
  retrieval-tool benchmark outputs, full-retrieval benchmark outputs, failure
  diagnosis outputs, PF-ERI retrieval-control v2 outputs, descriptor
  disagreement controls, utility-constrained policy selection, and PF-ERI v4
  deep-algorithm outputs.
- Created the source note later tracked as
  `sources/phase8_reid_tool_dataset_search_summary.md`.

### Problem Encountered

- The earlier evidence-selection story was promising but unstable: PF-ERI could
  reduce false-candidate/review burden, but the project had to test whether that
  translated into robust fixed-descriptor retrieval improvement.

### Repair / Decision

- Pushed the project through stricter retrieval and policy-control evaluations
  rather than relying on simple review-ready filtering.
- Began separating two endpoints:
  1. Re-ID ranking/accuracy improvement.
  2. Review/risk-control utility.

### Files Changed

- Generated outputs under:
  - `outputs/czechlynx/phase7a/pf_eri_algorithm_confidence_audit/`
  - `outputs/czechlynx/phase7a/pf_eri_policy_optimization/`
  - `outputs/czechlynx/phase8/reid_tool_benchmark/`
  - `outputs/czechlynx/phase8/full_retrieval_benchmark/`
  - `outputs/czechlynx/phase8/full_retrieval_failure_diagnosis/`
  - `outputs/czechlynx/phase8/pf_eri_retrieval_control_v2/`
  - `outputs/czechlynx/phase8/descriptor_disagreement_confidence_control/`
  - `outputs/czechlynx/phase8/utility_constrained_policy_selection/`
  - `outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/`
  - `outputs/czechlynx/phase8/reid_accuracy_evidence_selection/`

### Evidence / Source Notes

- Reconstructed from output modification times on 2026-06-14 and current file
  birth time for `sources/phase8_reid_tool_dataset_search_summary.md`.
- Later Phase 8 documentation says the accuracy-improvement claim had to be
  weakened because held-out query-level evaluation did not robustly improve mAP.

### Remaining Risk

- A reviewer could attack the project if it claimed PF-ERI robustly improves
  fixed-descriptor Re-ID accuracy.

### Next Action

- Complete query-level calibration/evaluation and then decide whether to pivot
  from accuracy-improvement language to evidence utility / review burden.

## 2026-06-15 Asia/Shanghai - reconstructed from artifact times

### Work Completed

- Completed Phase 8 Slice 3E query-calibration and downstream-sensitivity
  outputs.
- Opened Phase 9 fixed-descriptor reranking and refinement.
- Generated lightweight-learning feasibility and metric-learning preparation
  outputs.
- Prepared Phase 10 lite matched metric-learning manifests and Colab upload
  readiness artifacts.

### Problem Encountered

- Phase 8 made the project more technically ambitious, but also exposed the
  central weakness: simple PF-ERI filtering was not enough to claim reliable
  descriptor-ranking improvement.

### Repair / Decision

- Revised the direction toward a PF-ERI evidence utility model:
  image evidence -> pair evidence -> candidate utility -> reranking/weighting.
- Tested whether PF-ERI could do more than filter: rerank descriptor candidates,
  support lightweight learning, and prepare metric-learning experiments.

### Files Changed

- Generated outputs under:
  - `outputs/czechlynx/phase8/reid_accuracy_query_calibration/`
  - `outputs/czechlynx/phase8/downstream_sensitivity/`
  - `outputs/czechlynx/phase9/pf_eri_fixed_descriptor_reranking/`
  - `outputs/czechlynx/phase9/pf_eri_reranking_refinement/`
  - `outputs/czechlynx/phase9/pf_eri_lightweight_learning_feasibility/`
  - `outputs/czechlynx/phase9/pf_eri_metric_learning_prep/`
  - `outputs/czechlynx/phase10_lite/`

### Evidence / Source Notes

- Reconstructed from output modification times on 2026-06-15.
- Later archived `docs/phase9/phase9a_pf_eri_evidence_utility_model_direction_revision.md`
  describes this pivot: PF-ERI should become a pair-level/candidate-level
  evidence utility model, not just a review filter.

### Remaining Risk

- Metric learning could become an overclaim if it was not controlled against
  descriptor-only, random matched, and quality-proxy matched baselines.

### Next Action

- Build pair-level PF-ERI tables and training-control manifests with explicit
  matched controls.

## 2026-06-16 Asia/Shanghai - reconstructed from artifact times

### Work Completed

- Built Phase 11 pair-level PF-ERI table outputs.
- Generated Phase 11 training-package audits and Phase 11B/11C/11D diagnostic
  package outputs.
- Produced split-level diagnostics, quality distribution diagnostics, hard
  negative diagnostics, and positive-pair reliability diagnostics.
- Explored conditional pair weighting, revised positive rescue, and target-rate
  positive rescue package previews.

### Problem Encountered

- The project needed to know whether PF-ERI was actually useful as pair-level
  training signal or whether it was mostly an image-level review heuristic.

### Repair / Decision

- Moved the unit of evidence further from image-level readiness toward
  pair-level reliability and training-control diagnostics.
- Treated Phase 11 as a controlled bridge toward RQ4 metric-learning experiments,
  not as proof of metric-learning improvement.

### Files Changed

- Generated outputs under:
  - `outputs/czechlynx/phase11/`
  - `outputs/czechlynx/phase11b/`
  - `outputs/czechlynx/phase11c/`
  - `outputs/czechlynx/phase11d/`

### Evidence / Source Notes

- Reconstructed from output modification times on 2026-06-16.
- Later Phase 11 documentation, compacted on 2026-06-23 and 2026-06-25, preserves
  this as pair-reliability math and early pair-level learning implementation.

### Remaining Risk

- Pair-level reliability might not translate into improved retrieval geometry if
  the metric-learning objective damages strong fixed descriptors.

### Next Action

- Build the Phase 12 unified pair/candidate analysis table and confidence
  evidence needed to judge whether the effect is real or only diagnostic.

## 2026-06-17 Asia/Shanghai - reconstructed from document and artifact times

### Work Completed

- Created literature/source notes for patterned-felid Re-ID evidence utility and
  PF-ERI gap positioning.
- Created structure/artifact inventory and cleanup audit documents.
- Rebuilt Phase 7A/1000-image embedding inputs and audits.
- Built Phase 12 pair/candidate analysis table, RQ1/RQ3 evidence analysis,
  confidence evidence, and failure-diagnosis/policy-revision outputs.
- Built Phase 13 learned candidate utility, quality-boundary diagnosis, and RQ4
  training-control manifest outputs.

### Problem Encountered

- The project had signal, but the research gap was still vulnerable: it could be
  dismissed as a quality filter, a minor reranker, or a weak post-processing
  heuristic unless the gap was grounded in literature and pair-level mechanism.

### Repair / Decision

- Formalized the gap as pair-level evidence admissibility for patterned-felid
  Re-ID.
- Compared PF-ERI against animal Re-ID models, biometric quality, selective
  prediction, camera-trap AI review, and pairwise visibility/occlusion
  literatures.
- Used Phase 12/13 outputs to decide whether modest effects were positive,
  negative, or diagnostic.

### Files Changed

- Source/docs created by file birth time:
  - `sources/2026-06-17_patterned_felid_reid_evidence_utility_literature_scan.md`
  - `sources/2026-06-17_pferi_gap_model_map.md`
  - `sources/2026-06-17_pferi_research_gap_workflow_assessment.md`
  - `sources/README.md`
  - `docs/structure/csv_and_artifact_inventory.md`
  - `docs/structure/project_structure_and_cleanup_audit.md`
- Generated outputs under:
  - `outputs/czechlynx/phase12/`
  - `outputs/czechlynx/phase13/`

### Evidence / Source Notes

- Reconstructed from document birth times and output modification times on
  2026-06-17.
- Later archived `docs/phase12/phase12e_upgrade_strategy_after_modest_effects.md`
  states that the effect was positive as diagnostic signal but insufficient as a
  final contribution.

### Remaining Risk

- The fixed-reranking gains were too modest to be the final claim.

### Next Action

- Test whether PF-ERI-informed training can help under RQ4 without damaging
  descriptor geometry.

## 2026-06-18 Asia/Shanghai - reconstructed from document and artifact times

### Work Completed

- Ran Phase 13 RQ4 fixed-embedding training and split diagnostics.
- Downloaded/organized a large FCF bobcat image/data foundation.
- Built early Phase 14 UWIN/bobcat inventory and cross-context evidence tables.
- Wrote the Phase 14 same-genus wild-to-urban reliability plan.

### Problem Encountered

- Phase 13D underperformed: projection-head training damaged or failed to beat
  the raw fixed descriptor geometry.
- The project could not safely claim "PF-ERI improves metric learning."

### Repair / Decision

- Treated metric learning as diagnostic/optional rather than the main claim.
- Reframed the next direction as same-genus wild-to-urban evidence reliability:
  CzechLynx remains known-ID validation; bobcat becomes urban/peri-urban
  transfer-stress context.
- Defined the mechanism chain:
  image-level evidence shift -> pair-level comparability shift ->
  retrieval/review contamination.

### Files Changed

- Document birth time:
  - `docs/archive/superseded_plans/2026-06-18-phase14-same-genus-wild-urban-reid-reliability.md`
- Generated outputs/data under:
  - `outputs/czechlynx/phase13/rq4_fixed_embedding_training/`
  - `outputs/czechlynx/phase13/rq4_split_diagnostics/`
  - `data/external/felidae_conservation_fund/`
  - `outputs/phase14/`

### Evidence / Source Notes

- Reconstructed from document birth time and output/data modification times.
- Archived `docs/phase13/phase13e_rq4_failure_diagnosis_and_upgrade_plan.md`
  states that current projection-head training could not support a metric
  learning improvement claim.

### Remaining Risk

- Bobcat data did not provide verified identity validation; it could support
  stress testing and review readiness only.

### Next Action

- Build a 2x2 wild/urban x high/low evidence design and avoid Bobcat identity
  overclaiming.

## 2026-06-19 Asia/Shanghai - reconstructed from document and artifact times

### Work Completed

- Wrote/iterated the wild-urban risk-controlled evidence design.
- Created the 2x2 risk-controlled wild/urban evidence design.
- Added detector-first AI-assisted evidence admission design.
- Generated Phase 14 2x2 evidence sets, strict 2x2 evidence sets, detector-first
  admission outputs, MegaDetector evidence-gate outputs, and related FCF/CzechLynx
  manifests.

### Problem Encountered

- Strict rule-only high-confidence selection was not enough; it risked either
  underfilling clean sets or admitting weak evidence.

### Repair / Decision

- Changed the strategy from hand-tuned rules to detector-first evidence
  admission.
- Treated low-evidence cases as stress-test evidence rather than waste.
- Required every image to be routed into an explicit role: core training,
  retrieval evaluation, stress test, manual audit, or exclusion with reason.

### Files Changed

- Document birth times:
  - `docs/archive/superseded_specs/2026-06-19-wild-urban-risk-controlled-evidence-design.md`
  - `docs/archive/superseded_specs/2026-06-19-2x2-risk-controlled-wild-urban-evidence-design.md`
  - `docs/archive/superseded_specs/2026-06-19-detector-first-ai-assisted-evidence-admission-design.md`
- Generated outputs under:
  - `outputs/phase14/phase14_2x2_evidence_sets/`
  - `outputs/phase14/phase14_strict_2x2_evidence_sets/`
  - `outputs/phase14/phase14_detector_first_admission/`
  - `outputs/phase14/phase14_megadetector_evidence_gate*/`

### Evidence / Source Notes

- Reconstructed from document birth times and output modification times on
  2026-06-19.

### Remaining Risk

- The detector-first admission layer still needed stronger actual detector or
  MegaDetector support rather than only proxy image features.

### Next Action

- Package and run MegaDetector-style high-confidence and low-evidence screening
  for CzechLynx and bobcat candidate pools.

## 2026-06-20 Asia/Shanghai - reconstructed from document and artifact times

### Work Completed

- Built LILA/FCF bobcat source inventories and candidate source tables.
- Generated Bobcat high-confidence inventory, local image inventory, detector
  first auto-high candidates, MegaDetector sampled auto-high candidates, and
  selected strict-high 3000 outputs.
- Built CzechLynx high top-up candidate manifests and Colab/MegaDetector
  packages.
- Produced high-confidence working-final labels and expanded high-confidence
  candidate outputs.

### Problem Encountered

- The project needed enough clean bobcat high-confidence evidence, but available
  public bobcat images were messy, distributed, and not verified identity data.

### Repair / Decision

- Treated FCF/LILA bobcat as a public, species-level, urban/peri-urban stress
  source.
- Kept Bobcat high-confidence selection as evidence-quality/readiness selection,
  not identity validation.

### Files Changed

- Document/source birth times:
  - `sources/lila/lila_camera_trap_datasets.csv`
  - `sources/lila/phase14_candidate_lila_sources.csv`
- Generated outputs under:
  - `outputs/phase14/phase14_bobcat_high_confidence_inventory/`
  - `outputs/phase14/phase14_lila_md_prefilter/`
  - `outputs/phase14/phase14_czechlynx_high_topup*/`
  - `outputs/phase14/phase14_colab_megadetector_final_selection/`
  - `outputs/phase14/phase14_expanded_high_confidence_candidates/`
  - `outputs/phase14/phase14_final_2x2_working_labels/`

### Evidence / Source Notes

- Reconstructed from source file birth times and output modification times on
  2026-06-20.

### Remaining Risk

- High-confidence source expansion could create source/domain bias or duplicate
  pressure if not audited.

### Next Action

- Complete low-evidence/stress-set top-up and recovery so the 2x2 design has all
  four quadrants.

## 2026-06-21 Asia/Shanghai - reconstructed from document and artifact times

### Work Completed

- Wrote Phase 14 algorithm logic source notes.
- Ran low-evidence MegaDetector package/final-selection work.
- Restored missing Bobcat high/low working-final and retry artifacts after disk
  cleanup or package churn.
- Completed working-final labels/top-ups for CzechLynx and Bobcat high/low
  evidence sets.

### Problem Encountered

- The pipeline was operationally messy: low-evidence packages, Colab returns,
  missing local images, and retry/restore steps had to be tracked without
  corrupting the scientific quadrants.

### Repair / Decision

- Added explicit source notes for algorithm logic.
- Treated low-evidence images as required stress-test material and restored
  missing artifacts through auditable manifests/status files.

### Files Changed

- Document birth time:
  - `sources/2026-06-21_phase14_algorithm_logic_sources.md`
- Generated outputs under:
  - `outputs/phase14/phase14_colab_megadetector_low_evidence_final_selection/`
  - `outputs/phase14/phase14_colab_megadetector_low_evidence_package/`
  - `outputs/phase14/phase14_low_evidence_topup_colab_package/`
  - `outputs/phase14/phase14_disk_cleanup/`
  - `outputs/phase14/phase14_final_2x2_working_labels/`

### Evidence / Source Notes

- Reconstructed from document birth time and output modification times on
  2026-06-21.

### Remaining Risk

- Disk cleanup and restore operations could make lineage hard to follow unless
  manifests and audits are preserved.

### Next Action

- Convert the completed 2x2 image foundation into algorithm inputs, descriptor
  embeddings, pair comparability, conflict analysis, and review policy.

## 2026-06-22 Asia/Shanghai - reconstructed from document and artifact times

### Work Completed

- Wrote the PF-ERI evidence-routed review layer design.
- Built Phase 14 algorithm inputs: image evidence tables and pair comparability
  tables.
- Built descriptor-evidence conflict outputs, descriptor embedding packages,
  MegaDescriptor embeddings, disk cleanup audit outputs, risk-controlled review
  policy outputs, and statistical analysis outputs.
- Opened Phase 15: query-level benchmark, hybrid routing policy, calibrated
  ranker package/results, repeated ranker validation, evidence-routed review
  policy, wild-urban transfer stress, and Bobcat pair audit package.

### Problem Encountered

- Phase 14 had become a complete evidence foundation, but the project still
  needed to answer: what does PF-ERI add after a strong descriptor already
  produces candidate rankings?

### Repair / Decision

- Reframed PF-ERI as an evidence-routed review layer after descriptor retrieval:
  accept, review, defer, species-level only, or non-comparable.
- Kept descriptor-only as a strong baseline and shifted value toward
  false-candidate burden, review burden, conflict enrichment, and transfer-stress
  diagnostics.

### Files Changed

- Document birth time:
  - `docs/archive/superseded_specs/2026-06-22-pf-eri-evidence-routed-review-layer-design.md`
- Generated outputs under:
  - `outputs/phase14/phase14_algorithm_inputs/`
  - `outputs/phase14/phase14_descriptor_conflict/`
  - `outputs/phase14/phase14_descriptor_embedding*/`
  - `outputs/phase14/phase14_risk_controlled_review_policy/`
  - `outputs/phase14/phase14_statistical_analysis/`
  - `outputs/phase15/query_level_benchmark/`
  - `outputs/phase15/hybrid_routing_policy/`
  - `outputs/phase15/calibrated_ranker_results/`
  - `outputs/phase15/repeated_ranker_validation/`
  - `outputs/phase15/evidence_routed_review_policy/`
  - `outputs/phase15/wild_urban_transfer_stress/`
  - `outputs/phase15/bobcat_pair_audit_package/`

### Evidence / Source Notes

- Reconstructed from document birth time and output modification times on
  2026-06-22.

### Remaining Risk

- The review-layer framing was stronger than a ranking-improvement claim, but it
  still needed later safeguards against descriptor-only baselines and
  selected-set bias.

### Next Action

- Consolidate the many Phase 6-15 documents into a cleaner project map and then
  open Phase 16 safeguards.

## 2026-06-23 Asia/Shanghai - log restoration note

### Work Completed

- Restored the original daily work log that began before project initialization and was deleted during the 2026-06-23 documentation restructure.
- Appended reconstructed 2026-06-23 to 2026-06-29 entries after the original historical log.

### Problem Encountered

- The live `docs/logs/daily_work_log.md` had been recreated from recent history only, which made it look as if the project began on 2026-06-23.
- Git history shows the original log was created on 2026-06-01 and already contained a 2026-05-31 backfilled initial entry.

### Repair / Decision

- Preserve the original log verbatim up to the deletion point.
- Mark later entries as reconstructed when they come from git/file timestamps rather than live daily writing.

### Files Changed

- docs/logs/daily_work_log.md

### Evidence / Source Notes

- Original log source: `git show 468cf80^:docs/logs/daily_work_log.md`.
- Deletion source: commit `468cf80 docs: restructure project phase documentation`.

### Remaining Risk

- Some 2026-06-06 to 2026-06-22 work may still need compact reconstruction from commit history if the original daily log did not cover every day.

### Next Action

- Rebuild any missing 2026-06-06 to 2026-06-22 daily summaries from git history and generated artifact timestamps.


## 2026-06-23 Asia/Shanghai - reconstructed

Main work:

- Restructured project documentation into current maps, archives, phase folders,
  and source caches.
- Marked the old report draft as historical.
- Organized Colab and script archives.
- Added literature/source cache for PF-ERI, animal Re-ID, uncertainty,
  selective prediction, MegaDescriptor/WildlifeTools, and related evidence.
- Opened the Phase16 strategy line with laterality, leakage-pressure, and
  strong-model benchmark safeguards.

Key files and commits:

- `docs/CURRENT_PROJECT_MAP.md`
- `PROJECT_RULES.md`
- `README.md`
- `docs/archive/`
- `sources/`
- `paper/project_report_draft.md`
- `scripts/build_phase16_laterality_aware_pair_audit.py`
- `scripts/build_phase16_leakage_pressure_audit.py`
- `scripts/package_phase16_strong_model_benchmark.py`

Generated evidence:

- `outputs/phase16/laterality_aware_pair_audit/`
- `outputs/phase16/laterality_audit/`
- `outputs/phase16/leakage_pressure/`
- `outputs/phase16/strong_model_benchmark/`

Direction change:

- The project moved from diffuse historical PF-ERI/metric-learning exploration
  into a Phase16 strategy: protect the main PF-ERI pair-evidence line with data
  governance, laterality, leakage, and benchmark controls.

Claim-boundary impact:

- Historical metric-learning and broad Re-ID improvement claims were pushed into
  supporting/background status.

Next action recorded by project state:

- Build and audit the Phase16 dataset foundation before treating the 3000 x 4
  base as clean modeling evidence.

## 2026-06-24 Asia/Shanghai - reconstructed

Main work:

- Built the Phase16 dataset foundation audit.
- Added external clean dataset/source strategy.
- Packaged high-confidence quality/viewpoint rescoring.
- Expanded high-confidence candidate pools.
- Packaged Phase16E CzechLynx direct zips and candidate model-filter runners.
- Built Bobcat 20k candidate-pool packaging.

Key files and commits:

- `scripts/build_phase16_dataset_foundation_audit.py`
- `tests/test_phase16_dataset_foundation_audit.py`
- `docs/phase16/phase16_dataset_foundation_audit_interpretation_cn.md`
- `docs/phase16/phase16b_high_confidence_quality_viewpoint_plan_cn.md`
- `docs/phase16/phase16c_external_clean_dataset_source_strategy_cn.md`
- `docs/phase16/phase16d_expanded_high_candidate_pool_cn.md`
- `scripts/package_phase16_high_confidence_quality_viewpoint_rescore.py`
- `scripts/package_phase16_expanded_high_confidence_candidate_pool.py`
- `scripts/package_phase16e_candidate_model_filter_colab.py`
- `scripts/package_phase16e_czechlynx_direct_split_zips.py`
- `scripts/package_phase16e2_bobcat_20k_candidate_pool.py`

Generated evidence:

- `outputs/phase16/high_confidence_quality_viewpoint_rescore/`
- `outputs/phase16/expanded_high_confidence_candidate_pool/`
- `outputs/phase16/phase16e_czechlynx_direct_zips/`
- `outputs/phase16/phase16e_candidate_model_filter_*_smoke/`
- `outputs/phase16/phase16e2_bobcat_20k_candidate_pool/`

Direction change:

- The project shifted from planning the candidate foundation to actually
  preparing high-confidence scoring and model-filter inputs for CzechLynx and
  Bobcat.

Claim-boundary impact:

- Phase16E scoring was treated as proxy evidence scoring, not identity evidence.
- Bobcat remained a same-genus urban/peri-urban transfer-stress dataset, not a
  verified identity-validation dataset.

Next action recorded by project state:

- Harden Phase16E scoring, recalibration, and acceptance criteria before using
  returned scores.

## 2026-06-25 Asia/Shanghai - reconstructed

Main work:

- Consolidated phase documentation into compact READMEs.
- Hardened Phase16E scoring and recalibration.
- Added Phase16E result acceptance criteria.
- Packaged remaining CzechLynx Kaggle/Colab scoring batches.
- Produced dataset-foundation audit outputs.

Key files and commits:

- `docs/README.md`
- `docs/phase11/README.md`
- `docs/phase12/README.md`
- `docs/phase13/README.md`
- `docs/phase14/README.md`
- `docs/phase15/README.md`
- `docs/phase16/README.md`
- `docs/phase16/phase16e_colab_batch_execution.md`
- `docs/phase16/phase16e_result_acceptance_criteria.md`
- `scripts/recalibrate_phase16e_candidate_scores.py`
- `scripts/package_phase16e_candidate_model_filter_colab.py`
- `scripts/package_phase16e_czechlynx_kaggle_remaining_package.py`

Generated evidence:

- `outputs/phase16/dataset_foundation_audit/`
- `outputs/phase16/phase16e_recalibrated_candidate_scores_smoke/`
- `outputs/phase16/phase16e_candidate_model_filter_colab_package/`

Direction change:

- The project moved from package preparation to acceptance-gated scoring:
  returned model scores would need recalibration and audit before influencing
  candidate selection.

Claim-boundary impact:

- The documents increasingly separated score eligibility from identity evidence.

Next action recorded by project state:

- Wait for or receive scored CzechLynx/Bobcat batches, then run calibrated
  selection instead of taking raw top-ranked rows.

## 2026-06-26 Asia/Shanghai - reconstructed

Main work:

- Local cleanup and artifact hygiene around Phase16 zip/output directories.

Observed file-time evidence:

- `outputs/phase16/zip_cleanup_audit_20260626.json`
- local `.DS_Store` updates under docs, colab, data, and output folders.

Direction change:

- No major scientific direction change is visible from committed files.

Claim-boundary impact:

- None visible.

Next action recorded by project state:

- Continue waiting for scored outputs and keep artifacts organized.

## 2026-06-27 Asia/Shanghai - reconstructed

Main work:

- No committed project changes are visible for this day.
- File-time evidence mainly shows local data-folder activity.

Observed file-time evidence:

- `data/labels/czechlynx/.DS_Store`

Direction change:

- No major direction change is visible from available evidence.

Claim-boundary impact:

- None visible.

Next action recorded by project state:

- Resume once CzechLynx/Bobcat scoring artifacts are available.

## 2026-06-28 Asia/Shanghai - reconstructed

Main work:

- Received/merged CzechLynx Phase16E scoring outputs.
- Recalibrated CzechLynx scores and analyzed candidate-score distributions.
- Built Phase16F constrained CzechLynx 3000 selection and publication summary.
- Prepared Bobcat remaining local image package while Bobcat scoring was still
  pending/running.
- Designed and implemented Phase16G pair-level contract and real CzechLynx pair
  table.
- Built Phase16H readiness controls and calibrated-router diagnostic validation.

Key files and commits:

- `scripts/package_phase16e2_bobcat_remaining_local_images.py`
- `tests/test_package_phase16e2_bobcat_remaining_local_images.py`
- `scripts/build_phase16f_czechlynx_constrained_selection.py`
- `tests/test_phase16f_czechlynx_constrained_selection.py`
- `scripts/summarize_phase16f_czechlynx_publication_selection.py`
- `tests/test_phase16f_czechlynx_publication_summary.py`
- `scripts/analyze_phase16e_bobcat_scores.py`
- `tests/test_phase16e_bobcat_receiver.py`
- `docs/phase16/phase16g_pair_level_contract.md`
- `scripts/build_phase16g_pair_feature_schema.py`
- `scripts/audit_phase16g_pair_table.py`
- `scripts/run_phase16g_real_czechlynx_pair_table.py`
- `scripts/build_phase16h_czechlynx_readiness_controls.py`
- `scripts/build_phase16h_czechlynx_calibrated_router.py`

Generated evidence:

- `outputs/phase16/phase16e_candidate_model_filter/`
- `outputs/phase16/phase16e_recalibrated_czechlynx_scores/`
- `outputs/phase16/phase16e_czechlynx_analysis/`
- `outputs/phase16/phase16f_czechlynx_constrained_selection/`
- `outputs/phase16/phase16f_czechlynx_publication_summary/`
- `outputs/phase16/phase16e2_bobcat_remaining_local_package/`
- `outputs/phase16/phase16g_pair_contract/`
- `outputs/phase16/phase16g_czechlynx_real_pair_table/`
- `outputs/phase16/phase16h_czechlynx_readiness_controls/`
- `outputs/phase16/phase16h_czechlynx_calibrated_router/`

Direction change:

- CzechLynx moved from image-level candidate scoring into pair-level evidence
  modeling and controls.
- Phase16H showed useful diagnostic signal but did not justify a descriptor-only
  top-k ranking-improvement claim.

Claim-boundary impact:

- The project needed to avoid forcing a descriptor-replacement story.
- The correct next direction became review utility, risk coverage,
  false-candidate burden, positive retention, and expert-audit readiness.

Next action recorded by project state:

- Lock the gap explicitly and open Phase17A review-utility validation.

## 2026-06-29 Asia/Shanghai - reconstructed/live

Main work:

- Locked the Phase16I gap rationale.
- Updated root/project docs to prevent descriptor-replacement and unsupported
  top-k improvement drift.
- Added Phase17A CzechLynx review-utility validation.
- Installed and initialized CodeGraph.
- Added `.codegraph/` to `.gitignore`.
- Ran a CodeGraph-backed project structure/content audit.
- Added first-class Phase17 documentation, a current pipeline manifest, and this
  reconstructed daily log.
- Received and merged the completed 20,000-row Bobcat URL scoring batch.
- Ran Bobcat Phase16E score analysis and wrote a tier-separated result summary.
- Added Phase17B Bobcat transfer-stress statistics and manual-audit queue
  generation.

Key files and commits:

- `docs/phase16/phase16i_gap_rationale.md`
- `PROJECT_RULES.md`
- `README.md`
- `docs/CURRENT_PROJECT_MAP.md`
- `docs/README.md`
- `scripts/README.md`
- `docs/superpowers/plans/2026-06-29-phase17a-czechlynx-review-utility.md`
- `scripts/build_phase17a_czechlynx_review_utility.py`
- `tests/test_phase17a_czechlynx_review_utility.py`
- `.gitignore`
- `docs/structure/2026-06-29_codegraph_project_structure_content_audit.md`
- `docs/phase17/README.md`
- `docs/structure/current_pipeline_manifest.md`
- `docs/phase16/phase16e_bobcat_url_batch_result_analysis.md`
- `scripts/build_phase17b_bobcat_transfer_stress.py`
- `tests/test_phase17b_bobcat_transfer_stress.py`

Generated evidence:

- `outputs/phase17/phase17a_czechlynx_review_utility/`
- `.codegraph/` local index, ignored by git.
- `outputs/phase16/phase16e_bobcat_candidate_model_filter/`
- `outputs/phase16/phase16e_bobcat_score_analysis/`
- `outputs/phase17/phase17b_bobcat_transfer_stress/`

Direction change:

- The project direction is now explicitly locked: PF-ERI is a review-utility and
  evidence-reliability layer after descriptor retrieval, not a descriptor or
  top-k replacement.
- Phase17 becomes the active validation layer while Bobcat scoring continues.

Claim-boundary impact:

- Phase17A supports review-utility endpoints only.
- Descriptor-only remains the strong ranking baseline.
- Bobcat remains transfer-stress/review-readiness evidence until verified
  identity labels or audited same/different pair labels exist.
- Bobcat Tier 1 and Tier 2 must be routed separately because the Tier 2 top-up
  rows lack MD geometry evidence and should not be collapsed into a single clean
  high-confidence pool.
- Phase17B uses non-parametric effect sizes and bootstrap intervals because the
  score distributions are bounded, skewed, and structurally affected by missing
  top-up geometry fields.

Next action:

- Complete Bobcat manual audit on the Phase17B 200-row stratified sheet, then
  analyze auditor agreement with the routing labels.
- Extend Phase17 only through review-utility, expert-audit, and
  transfer-stress endpoints unless stronger labels become available.

## 2026-06-30 Asia/Shanghai - live

Main work:

- Built the Phase17C Bobcat provisional 3000 algorithm-prep selector.
- Added a throwaway Phase17C logic prototype to compare clean-backbone and
  transfer-sentinel quota choices.
- Ran the provisional selection on the completed Bobcat 20,000-row score table.

Key files:

- `scripts/build_phase17c_bobcat_provisional_3000.py`
- `scripts/prototypes/prototype_phase17c_bobcat_3000_logic.py`
- `tests/test_phase17c_bobcat_provisional_3000.py`
- `docs/phase17/README.md`
- `docs/structure/current_pipeline_manifest.md`
- `scripts/README.md`

Generated evidence:

- `outputs/phase17/phase17c_bobcat_provisional_3000/`

Result:

- Phase17C selected 3,000 provisional Bobcat review-readiness rows.
- The default split is 2,700 Tier 1 strict clean-backbone rows and 300 Tier 2
  strict transfer-sentinel rows.
- No broad-reserve rows were needed.
- Candidate IDs and image URIs are unique in the selected manifest.
- The largest hashed balance group has 45 selected rows, below the cap of 80.

Claim-boundary impact:

- The selected 3,000 rows are an algorithm-prep review-readiness foundation.
- They are not a final Bobcat identity-labeled high-confidence set.
- The next gate is manual audit and agreement analysis before freezing any final
  Bobcat 3000.

Next action:

- Complete and analyze the Phase17C manual-audit expansion sheet.
- Decide whether the 300 transfer-sentinel rows remain in the final algorithm
  entry manifest or move to a separate stress-test split after audit.

Phase17D continuation:

- Added a manual-audit final-freeze gate for the Phase17C Bobcat provisional
  3000.
- Added a throwaway Phase17D logic prototype to validate `BLOCKED_PENDING_AUDIT`,
  `PASS`, `PASS_WITH_SPLIT`, and `REVISE` transitions.
- Ran Phase17D on the current real Phase17C audit sheet.

Key files:

- `scripts/build_phase17d_bobcat_manual_audit_gate.py`
- `scripts/prototypes/prototype_phase17d_manual_audit_gate.py`
- `tests/test_phase17d_bobcat_manual_audit_gate.py`

Generated evidence:

- `outputs/phase17/phase17d_bobcat_manual_audit_gate/`

Result:

- The current Phase17D decision is `BLOCKED_PENDING_AUDIT`.
- This is expected because the Phase17C manual-audit fields are still blank.
- The gate now prevents the provisional Bobcat 3000 from being treated as a
  final algorithm-entry set before human review.

Next action:

- Fill enough Phase17C manual-audit rows for both `clean_backbone` and
  `transfer_sentinel`, then rerun Phase17D.

Manual-audit tooling:

- Added a Streamlit image-review app for filling the Phase17D Bobcat working
  audit CSV while viewing each public `image_uri`.
- The app preserves the original Phase17C expansion sheet and writes a working
  copy under `outputs/phase17/phase17d_bobcat_manual_audit_gate/`.

Key file:

- `scripts/streamlit_phase17d_bobcat_manual_audit_app.py`

Run command:

```text
python -m streamlit run scripts/streamlit_phase17d_bobcat_manual_audit_app.py
```

Phase17K clarity-gate correction:

- Diagnosed the iNaturalist Bobcat replacement path as still failing visual
  clarity expectations: Phase17H had 8/104 YES and Phase17J had 13/51 YES at
  the time of review, so metadata filters were not sufficient for algorithm
  entry.
- Locked a new clarity-first rule: Bobcat final 3000 cannot be frozen until
  3000 rows pass `phase17k_clarity_gate_decision=clear`.
- Added a builder and Streamlit app specifically for CLEAR / NOT CLEAR visual
  clarity review.

Key files:

- `PROJECT_RULES.md`
- `docs/CURRENT_PROJECT_MAP.md`
- `docs/phase17/README.md`
- `scripts/build_phase17k_bobcat_clarity_gate.py`
- `scripts/streamlit_phase17k_bobcat_clarity_gate_app.py`

Generated evidence:

- `outputs/phase17/phase17k_bobcat_clarity_gate/phase17k_bobcat_clarity_gate_pool.csv`
- `outputs/phase17/phase17k_bobcat_clarity_gate/phase17k_bobcat_clarity_gate_audit.json`
- `outputs/phase17/phase17k_bobcat_clarity_gate/phase17k_bobcat_clarity_gate_report.md`

Result:

- Input iNaturalist organism photo rows: 11,378.
- Phase17K review pool rows after automatic removal of dead/sign/track/scat,
  prior unusable labels, and duplicate observation extra photos: 4,727.
- Prior human YES rows safely seeded as `clear`: 39.
- Pending clarity rows: 4,688.

Direction change:

- Phase17H and Phase17J are now treated as diagnostic failed metadata-first
  candidate pools, not final Bobcat 3000 manifests.
- Visual clarity is a hard algorithm-entry gate. Unclear images can still be
  used as low-evidence stress-test material, but cannot enter clean training or
  algorithm-entry 3000.

Next action:

- Use the Phase17K Streamlit app to accumulate 3,000 manually clear Bobcat
  images, or obtain a stronger source/vision-filtered pool if the clear yield is
  too low.

Phase17L multisource strict-clarity optimization:

- Built a throwaway multisource prototype to answer whether a broader open
  source pool can provide a much stricter 5,000-row Bobcat review queue.
- Sources included iNaturalist organism candidates, GBIF `Lynx rufus` occurrence
  media, and Wikimedia Commons image search.
- Added pixel-level proxy scoring from downloaded images: dimensions,
  megapixels, file size, contrast, edge strength, Laplacian sharpness proxy,
  entropy, and dark/bright clipping.
- Added a dedicated Streamlit review app for the Phase17L queue.

Key files:

- `scripts/prototypes/prototype_phase17l_multisource_bobcat_strict_clarity_queue.py`
- `scripts/streamlit_phase17l_bobcat_strict_clarity_review_app.py`
- `docs/phase17/README.md`

Generated evidence:

- `outputs/phase17/phase17l_multisource_strict_clarity_queue/phase17l_multisource_bobcat_pre_score_candidates.csv`
- `outputs/phase17/phase17l_multisource_strict_clarity_queue/phase17l_multisource_bobcat_scored_all.csv`
- `outputs/phase17/phase17l_multisource_strict_clarity_queue/phase17l_bobcat_strict_clarity_review_queue_5000.csv`
- `outputs/phase17/phase17l_multisource_strict_clarity_queue/phase17l_bobcat_strict_clarity_rescore_audit.json`
- `outputs/phase17/phase17l_multisource_strict_clarity_review/phase17l_bobcat_strict_clarity_review_working.csv`

Result:

- Candidate rows before dedupe: 33,253.
- Candidate rows after dedupe: 15,745.
- Successfully scored image rows: 14,225.
- Download/decode failures: 1,520.
- Strict-or-near rows available: 7,811.
- Final review queue rows: 5,000.
- Final queue proxy tiers: 1,496 `strict_pass` and 3,504 `near_strict`.
- Final queue source counts: 3,535 GBIF, 1,463 iNaturalist, 2 Wikimedia
  Commons.

Direction change:

- Phase17L supersedes Phase17K as the preferred Bobcat review queue because it
  is multisource and uses actual image-pixel proxy metrics.
- It does not supersede the manual clarity gate. The final Bobcat 3000 still
  requires human CLEAR decisions.

Next action:

- Review the first 200 Phase17L rows, starting with `strict_pass`.
- If CLEAR yield is high, continue until 3,000 clear rows are accumulated.
- If CLEAR yield is still poor, stop metadata/proxy filtering and move to an
  object-detection or vision-model gate for subject size and comparability.

Phase17M annotation-aware correction:

- Checked the user's live Phase17L progress after reports of scat/track and poor
  clarity leakage.
- Live Phase17L review progress at inspection: 182 completed, 77 clear, 105
  not_clear, 4,818 pending; CLEAR rate about 42.3%.
- Diagnosis: the Phase17L pixel proxy was ranking image-level sharpness, but
  not evidence type or subject comparability. GBIF contributed 3,535 rows to the
  5,000 queue, and almost all GBIF selected rows were iNaturalist photo mirrors
  without the direct iNaturalist observation annotation gates. This allowed sign,
  scat, track, dead, or species-level-only material to re-enter.
- Built Phase17M to prefer direct iNaturalist annotation-aware rows over GBIF
  mirrors.

Key file:

- `scripts/prototypes/prototype_phase17m_inat_annotation_aware_strict_clarity_queue.py`

Generated evidence:

- `outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue/phase17m_inat_annotation_aware_scored_all.csv`
- `outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue/phase17m_inat_annotation_aware_strict_clarity_review_queue_5000.csv`
- `outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue/phase17m_inat_annotation_aware_deduped_rebuild_audit.json`
- `outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_review/phase17l_bobcat_strict_clarity_review_working.csv`

Result:

- Input direct iNaturalist photo rows: 11,378.
- Rows after annotation and prior-human-label filters: 10,229.
- Deduplicated strict-or-near rows available: 5,220.
- Final review queue rows: 5,000.
- Final queue tiers: 945 `strict_pass`, 4,055 `near_strict`.
- Duplicate selected image URI count: 0.
- Duplicate selected photo ID count: 0.

Direction change:

- Phase17M supersedes Phase17L as the preferred Bobcat review queue while
  evidence-type leakage is the main failure mode.
- GBIF remains useful for source discovery, but GBIF iNaturalist mirrors should
  not be treated as clean unless rehydrated through direct iNaturalist
  annotation metadata.

Next action:

- Review Phase17M first. If scat/track/dead leakage is fixed but many images are
  still tiny or not comparable, move next to object-detection/vision-model
  subject-size gating.

Phase17N final-3000 seed:

- Built a repeatable script to collect all previous human-confirmed Bobcat
  `YES` / `CLEAR` rows into the locked final-3000 seed manifest.
- Included Phase17E/F/G/H/J yes/no audit files, Phase17K clarity review,
  Phase17L multisource strict review, and Phase17M annotation-aware strict
  review.
- Deduplicated by canonical image URI and photo ID.

Key file:

- `scripts/build_phase17n_bobcat_final3000_seed_from_human_clear.py`

Generated evidence:

- `outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_manifest.csv`
- `outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_audit.json`
- `outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_report.md`

Result:

- Raw prior positive rows found: 346.
- Deduplicated human-confirmed clear photos: 137.
- Duplicate canonical image keys: 0.
- Duplicate photo IDs: 0.
- Remaining clear rows needed to reach final 3000: 2,863.

Rule:

- These 137 rows are locked into the final Bobcat 3000 seed. Future top-up
  selection must append around them, not replace them, unless a label is
  explicitly reversed.

## 2026-07-01

Phase17 CzechLynx strict 3000 final-ready pass:

- User inspected the CzechLynx strict 3,000 review queue and reported that image
  quality was acceptable, with only a final clarity-enhancement pass needed.
- Built `scripts/prototypes/prototype_czechlynx_strict3000_clarity_augmentation.py`.
- Ran full-frame mild clarity augmentation over the strict CzechLynx 3,000.
- Wrote a final confirmed manifest while preserving the original image path for
  every row.

Generated evidence:

- `outputs/czechlynx/phase17_strict3000_supplement/augmented/phase17_czechlynx_strict3000_augmented_manifest.csv`
- `outputs/czechlynx/phase17_strict3000_supplement/augmented/phase17_czechlynx_strict3000_final_confirmed_manifest.csv`
- `outputs/czechlynx/phase17_strict3000_supplement/augmented/phase17_czechlynx_strict3000_clarity_augmentation_audit.json`
- `outputs/czechlynx/phase17_strict3000_supplement/augmented/images/`

Result:

- Source rows: 3,000.
- Augmented rows: 3,000.
- Augmented files present: 3,000.
- Missing augmented files: 0.
- Unique dedupe keys: 3,000.
- Strict gate pass: 3,000 `yes`.
- Final status: 3,000 `human_clear_augmented_ready_for_freeze`.

Direction change:

- CzechLynx now has a final-freeze candidate manifest for a
  visual-quality-first strict 3,000.
- The manifest is not an identity-balanced training/evaluation split. If the
  algorithm needs balanced identities, derive that as a separate subset rather
  than weakening the image-quality gate.

CodeGraph issue check:

- CodeGraph located the current strict3000 supplement script, but broad
  CzechLynx supplement/augmentation queries also returned older Bobcat
  strict-clarity and legacy CzechLynx paths.
- Recorded the rule that CodeGraph is valid for locating code and blast radius,
  but CzechLynx/Bobcat data state must be verified from CSV/JSON/report
  artifacts and direct file counts.

Project structure / CodeGraph triage:

- Confirmed CodeGraph is installed at the project root and the index is current:
  369 indexed files, 7,529 nodes, 18,409 edges.
- Diagnosed the remaining CodeGraph issue as retrieval noise from
  `scripts/legacy/`, `scripts/prototypes/`, and archived Colab files, not an
  installation failure.
- Updated the current pipeline/read-order docs so Phase17 Bobcat final 3,000
  and CzechLynx strict final-ready 3,000 are visible as current state.
- Added `docs/structure/2026-07-01_codegraph_root_cleanup_triage.md` with a
  triage matrix for naming, consolidation, and pruning decisions.

Phase17 strict 3000 modeling freeze:

- Built `scripts/freeze_phase17_modeling_dataset.py`.
- Validated that Bobcat Phase17N has 3,000 deduplicated human-confirmed clear
  rows and remaining clear rows needed is 0.
- Validated that CzechLynx strict final-ready manifest has 3,000 strict-gated,
  clarity-augmented rows and 0 missing augmented files.
- Copied CzechLynx enhanced images and downloaded all Bobcat final image URLs
  into one local modeling package.

Frozen package:

- `outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701/`

Verification:

- combined manifest rows: 6,000;
- Bobcat frozen rows/files: 3,000;
- CzechLynx frozen rows/files: 3,000;
- checksum rows: 6,000;
- decode status: 6,000 `ok`;
- failed rows: 0;
- package size: about 4.7 GB.

Boundary:

- This is the local modeling image-entry package. Bobcat is not identity-labeled.
  CzechLynx is visual-quality-first and requires a derived split if the next
  algorithm step needs identity-balanced train/evaluation sets.

## 2026-07-01 23:32-24:02 CST - CodeGraph Contract, Structure Consolidation, Phase18A Entry

Work type: live session.

Changed files:

- Added `scripts/check_codegraph_project_contract.py`.
- Added `scripts/build_project_artifact_consolidation_index.py`.
- Added `scripts/build_phase18a_frozen_feature_manifest.py`.
- Added `tests/test_phase18a_frozen_feature_manifest.py`.
- Added `docs/phase18/README.md`.
- Added `docs/structure/2026-07-01_project_triage_and_phase18_execution_issues.md`.
- Updated `PROJECT_RULES.md`, `docs/README.md`,
  `docs/structure/current_pipeline_manifest.md`, and `scripts/README.md`.

Generated artifacts:

- `outputs/project_structure/codegraph_contract/`
- `outputs/project_structure/artifact_consolidation_index/`
- `outputs/phase18/phase18a_frozen_feature_manifest/`

Verification:

- `codegraph status`: root index present and up to date.
- `scripts/check_codegraph_project_contract.py`: PASS.
- `scripts/build_project_artifact_consolidation_index.py`: PASS, 62 indexed
  Phase16/17-related directories.
- `scripts/build_phase18a_frozen_feature_manifest.py`: PASS, 6,000 rows.
- `tests/test_phase18a_frozen_feature_manifest.py`: PASS.

Scientific decision:

- Phase16/17 output folders are provenance and selection-history assets, not
  direct Phase18 inputs.
- Phase18 starts from the frozen 6,000-image package only.
- Phase18A is an image-level entry manifest with hash/decode verification and
  explicit modeling roles:
  - 3,000 `czechlynx_known_id`;
  - 3,000 `bobcat_unlabeled_transfer`.

Direction boundary:

- Pair-level PF-ERI remains the main idea.
- Strong descriptor baselines are required before claims.
- Bobcat remains transfer/readiness only unless identity labels or audited
  same/different pairs are added.

## 2026-07-02 CST - Phase18A-F Automated Local-Control Pipeline

Work type: live session.

Changed files:

- Added `scripts/phase18_pipeline_utils.py`.
- Added `scripts/build_phase18b_local_descriptor_control.py`.
- Added `scripts/build_phase18c_czechlynx_pair_contract.py`.
- Added `scripts/build_phase18d_pf_eri_pair_features.py`.
- Added `scripts/build_phase18e_review_router.py`.
- Added `scripts/build_phase18f_bobcat_transfer_readiness.py`.
- Added `scripts/run_phase18_all.py`.
- Added `tests/test_phase18_pipeline.py`.
- Updated `docs/phase18/README.md`,
  `docs/structure/2026-07-01_project_triage_and_phase18_execution_issues.md`,
  `docs/structure/current_pipeline_manifest.md`, and `scripts/README.md`.

Generated artifacts:

- `outputs/phase18/phase18b_local_descriptor_control/`
- `outputs/phase18/phase18c_czechlynx_pair_contract/`
- `outputs/phase18/phase18d_pf_eri_pair_features/`
- `outputs/phase18/phase18e_review_router/`
- `outputs/phase18/phase18f_bobcat_transfer_readiness/`
- `outputs/phase18/phase18_all_pipeline/`

Verification:

- `scripts/run_phase18_all.py`: PASS, 6 executed steps.
- Phase18B: 6,000 local descriptor-control rows, embedding shape 6,000 x 822.
- Phase18C: 3,000 CzechLynx known-ID images, 235 identities, 60,000 pair rows.
- Phase18D: 60,000 PF-ERI pair-feature rows.
- Phase18E: 5 deterministic router policies, 10 metric rows.
- Phase18F: 3,000 Bobcat images, 30,000 transfer-readiness pair rows.
- Phase18G: added strong-baseline handoff and claim gate.

Scientific decision:

- The full Phase18 contract now runs automatically end-to-end.
- Because the current runtime lacks `torch` and `timm`, Phase18B is a local
  descriptor-control baseline, not a strong descriptor baseline.
- These outputs are valid for pipeline/schema debugging and first-pass review
  utility diagnostics, but not for final claims against MegaDescriptor,
  WildFusion, or modern foundation-model baselines.
- Phase18G is the explicit repair: it writes the strong-baseline handoff package
  and blocks final scientific claims until strong descriptor embeddings or pair
  scores are returned.
