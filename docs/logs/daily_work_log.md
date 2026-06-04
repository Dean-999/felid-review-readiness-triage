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

Write entries such as:

Revised the triage rubric to separate species-level tagging from individual-level Re-ID readiness. Added side_comparability and night_ir_artifact as required fields because field images may be species-identifiable but not comparable for identity review.
Daily Entry Template
## YYYY-MM-DD — Short Title

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
Backfilled Initial Entries
2026-05-31 — Project Scope Lock and Research Direction
Work Completed
Narrowed the project from a broad ReID-Audit direction to Review-Readiness Triage for Felid Re-ID in Conservation Camera-Trap Images.
Locked the project around two research questions:
Q1: whether review-ready images show stronger Re-ID reliability than lower-readiness images.
Q2: how filtering low-readiness images changes pairwise false-match risk proxy and retained evidence.
Defined CzechLynx as the quantitative known-ID validation carrier.
Defined UWIN/WildTrax Bobcat and Canada Lynx as field motivation and field-readiness stress test data.
Defined Marbled Cat as a future Asian conservation application scenario only.
Problem Encountered
The original ReID-Audit direction was too broad and overlapped with mature animal Re-ID work.
It risked being misunderstood as a new Re-ID model, a full identity prediction system, or a population estimation project.
Repair / Decision
Removed new model claims, SOTA claims, universal threshold claims, full website claims, RUDI claims, and true individual identity claims.
Reframed Re-ID as an auxiliary measurement signal.
Required all false-match language to use the phrase pairwise false-match risk proxy under known-ID validation.
Files Changed
docs/phase0/project_scope.md
docs/phase0/research_questions.md
docs/phase0/data_roles.md
docs/phase0/claims_and_boundaries.md
docs/phase0/evidence_chain.md
docs/phase0/phase0_decision_log.md
Evidence / Source Notes
Existing animal Re-ID work is mature, so the project must focus on a pre-Re-ID review-readiness gate.
Field tagging experience through UWIN-Atlanta provides the practical motivation.
Remaining Risk
The rubric may still look subjective unless Phase 1 defines observable fields.
CzechLynx license and exact dataset version still need to be verified.
Next Action
Start Phase 1: data access notes, triage rubric, CzechLynx sampling plan, WildTrax field triage plan, Marbled Cat future application note, and Go/No-Go criteria.
2026-06-01 — Phase 1 Documentation and Rubric Setup
Work Completed
Drafted Phase 1 documentation structure.
Added a formal daily work log mechanism.
Defined review-ready, review-limited, and unidentifiable as primary triage labels.
Added required supporting fields, including:
blur level
occlusion level
lighting condition
night IR artifact
visible side
side comparability
visible region
pattern visibility
metadata completeness
reviewer confidence
uncertainty flag
exclusion reason
notes
Problem Encountered
The label review-limited could become too vague if not tied to specific observable fields.
The project could confuse species-level tagging with individual-level Re-ID readiness.
WildTrax/UWIN images have field value but lack verified individual IDs.
Repair / Decision
Required every triage label to be supported by observable fields.
Added the explicit rule: species-level usable does not mean Re-ID-ready.
Restricted WildTrax/UWIN to field-readiness distribution and failure-mode analysis.
Kept CzechLynx as the only current strict validation source.
Files Changed
docs/phase1/triage_rubric.md
docs/phase1/czechlynx_data_access_notes.md
docs/phase1/czechlynx_sampling_plan.md
docs/phase1/wildtrax_field_triage_plan.md
docs/phase1/marbled_cat_application_readiness_note.md
docs/phase1/phase1_go_no_go_criteria.md
docs/logs/daily_work_log.md
Evidence / Source Notes
CzechLynx provides the known-ID validation path.
WildTrax/UWIN tagging experience provides field motivation.
Marbled Cat remains future application only.
Remaining Risk
CzechLynx exact license and local file counts still need to be verified after download.
WildTrax public image display permission should still be confirmed before public release.
The rubric needs a pilot second-review consistency check.
Next Action
Complete CzechLynx access audit.
Create the first CzechLynx pilot triage CSV.
Triage 100–200 pilot images without viewing individual IDs.
Re-triage 30 images after a delay for consistency.
2026-06-01 — CzechLynx Local Technical Access Audit
Work Completed
Completed a local CzechLynx technical access audit.
Verified that CzechLynxDataset-Metadata-Real.csv contains 39,760 rows.
Verified that CzechLynxDataset-Metadata-Synthetic.csv contains 40,000 rows.
Confirmed that the real metadata contains:
319 unique unique_name values
18,782 unique encounters
86 unique locations
659 unique trap IDs
Confirmed that the first 1,000 real metadata image paths exist locally.
Confirmed that the first 100 real images are readable with PIL.
Confirmed the presence of split fields:
split-geo_aware
split-time_open
split-time_closed
split-pose
Problem Encountered
The dataset contains both real and synthetic images.
The dataset includes sensitive location columns such as latitude and longitude.
The exact license, citation format, redistribution rules, and public image display permission were still pending.
The metadata field unique_name appeared to function as the individual ID field, but this still needed to be confirmed against dataset documentation.
Repair / Decision
Decided that primary Q1/Q2 validation will use only CzechLynxDataset-Metadata-Real.csv.
Excluded synthetic images from primary validation.
Treated unique_name as the working individual ID field for sampling and pair construction.
Decided that exact latitude/longitude should not be published unless permission is explicitly confirmed.
Updated CzechLynx status to Conditional Go for internal sampling, but No-Go for public image display until license/display permissions are verified.
Files Changed
docs/phase1/czechlynx_data_access_notes.md
docs/phase1/phase1_go_no_go_criteria.md
docs/logs/daily_work_log.md
Evidence / Source Notes
Local audit showed 39,760 real metadata rows and 319 unique working individual IDs.
First 1,000 metadata paths existed locally.
First 100 real images were readable.
Split fields are available for geo-aware and time-aware analysis.
Remaining Risk
License and citation still need to be recorded.
Public display permission is not yet confirmed.
unique_name should be confirmed against official dataset documentation before final paper wording.
Sampling must avoid overrepresenting high-count individuals such as lynx_278.
Next Action
Create a clean CzechLynx real manifest file.
Generate a blinded pilot triage CSV with 100–200 images.
Avoid showing unique_name, latitude, longitude, and exact location during triage.
2026-06-03 — Completed CzechLynx Pilot Triage and Final Audit
Work Completed
Completed the full 200-image CzechLynx blinded pilot triage.
Manually labeled each image using the review-readiness rubric with three possible labels:
review-ready
review-limited
unidentifiable
Final 200-image label distribution:
review-ready: 34 images
review-limited: 107 images
unidentifiable: 59 images
Ran the final CzechLynx triage consistency audit.
Confirmed:
200 total rows
200 labeled rows
required fields complete
allowed values valid
logical consistency checks passed
Final audit result: PASS.
Problem Encountered
Apple Numbers converted the working CSV into a Numbers/Zip-style document while keeping the .csv filename.
Some exported CSV files included table-title/header issues.
Some early labels used inconsistent controlled vocabulary values such as high_exposure instead of overexposed.
Some early rows had logical inconsistencies, such as full_body with body_fraction_visible = 0-25.
Repair / Decision
Resolved the CSV corruption issue by exporting from Numbers as UTF-8 CSV and validating the exported file before continuing.
Updated the label consistency workflow:
exclusion_reason is a required controlled field.
notes are optional.
review-ready uses exclusion_reason = none.
review-limited and unidentifiable require concrete limitation or exclusion reasons.
consistency audits catch impossible combinations such as full_body + 0-25.
Finalized and used scripts/audit_czechlynx_triage_consistency.py to enforce rubric consistency.
Files Changed

Relevant local data outputs:

data/labels/czechlynx/czechlynx_pilot_triage_working.csv
data/labels/czechlynx/czechlynx_pilot_triage_final.csv
outputs/czechlynx/qc/triage_consistency_final200_report.txt

Relevant scripts:

scripts/audit_czechlynx_triage_consistency.py
scripts/prepare_czechlynx_second_review_subset.py
scripts/audit_czechlynx_second_review_blinding.py
scripts/compare_czechlynx_second_review_consistency.py
Evidence / Source Notes
The 200-image final triage audit passed.
The final label distribution shows that the rubric remained conservative: most images were classified as review-limited, while review-ready remained a smaller subset.
This supports the project framing as a review-readiness gate rather than a direct identity prediction workflow.
Remaining Risk
The 200-image audit confirms completeness and logical consistency, but not reviewer stability.
A delayed intra-reviewer second-review consistency check is still required.
Public image display and redistribution policy must still be handled conservatively.
Next Action
Wait before labeling the second-review subset.
Do not open second-review images or internal mapping before the delayed review.
Continue project work through documentation, citation/license verification, and Phase 2/3 planning.
2026-06-04 — Phase 2/3 Planning, Pair Construction, License Audit, and Mentor-Facing Documentation
Work Completed
Built the Phase 2 data-engineering foundation for CzechLynx known-ID validation.
Created and verified:
scripts/build_czechlynx_validation_table.py
scripts/construct_czechlynx_pair_sets.py
scripts/audit_czechlynx_pair_sets.py
scripts/check_czechlynx_embedding_inputs.py
Generated the Phase 2 validation table and pair set.
Validation table summary:
200 validation rows
100 unique working individual IDs
2 images per ID
Pair set summary:
400 total pairs
100 same-individual pairs
300 fixed-seed sampled different-individual pairs
Pair audit result: PASS.
Embedding input check result: PASS.
Problem Encountered
The project now has enough infrastructure to begin embedding work, but the delayed second-review consistency check is still pending.
Starting embedding analysis before the second-review gate could weaken the research sequence.
CzechLynx license and citation information needed to be separated into article license, dataset license, and project policy.
Repair / Decision
Decided not to run embedding extraction, model inference, final similarity analysis, or final scientific claims yet.
Created Phase 2 planning documentation:
docs/phase2/phase2_validation_plan.md
docs/phase2/embedding_baseline_selection.md
docs/phase2/metrics_plan.md
Created Phase 3 planning documentation:
docs/phase3/risk_coverage_policy_plan.md
Created and updated the license/citation audit:
docs/phase1/czechlynx_license_and_citation_audit.md
Created mentor-facing documentation:
docs/mentor_updates/mentor_progress_update_001.md
Updated:
README.md
Files Changed

Phase 2 scripts:

scripts/build_czechlynx_validation_table.py
scripts/construct_czechlynx_pair_sets.py
scripts/audit_czechlynx_pair_sets.py
scripts/check_czechlynx_embedding_inputs.py

Phase 2 docs:

docs/phase2/phase2_validation_plan.md
docs/phase2/embedding_baseline_selection.md
docs/phase2/metrics_plan.md

Phase 3 docs:

docs/phase3/risk_coverage_policy_plan.md

License and citation documentation:

docs/phase1/czechlynx_license_and_citation_audit.md

Mentor-facing documentation:

docs/mentor_updates/mentor_progress_update_001.md
README.md
Evidence / Source Notes
The Scientific Data paper is the primary paper citation source.
The paper describes CzechLynx as an open-access dataset for individual identification, pose estimation, and instance segmentation of Eurasian lynx, with 39,760 real camera-trap images and 319 unique individuals.
The Zenodo dataset page identifies the dataset record as CzechLynx Dataset (v1.0), DOI 10.5281/zenodo.17592004.
The Zenodo dataset license was recorded as Creative Commons Attribution 4.0 International (CC BY 4.0).
The Scientific Data article license was recorded separately as CC BY-NC-ND 4.0.
Project policy remains conservative:
do not commit raw images;
do not publish contact sheets;
do not publish exact coordinates, trap IDs, cell codes, or sensitive location metadata;
do not place raw CzechLynx images in the public GitHub README for now;
mentor-only slides and poster examples may use a small number of images only with proper attribution.
Remaining Risk
The delayed 30-image intra-reviewer consistency check is still pending.
Phase 2 embedding execution has not started.
Phase 3 risk–coverage analysis has not been executed.
Public image use must continue to follow conservative project policy, even though the dataset license permits attributed reuse.
Next Action
Complete the delayed 30-image second-review labeling after the waiting period.
Run scripts/compare_czechlynx_second_review_consistency.py.
Interpret intra-reviewer consistency.
After the second-review gate is complete, begin Phase 2 embedding extraction and pair similarity validation.
Continue keeping raw data, generated images, contact sheets, internal mappings, and output reports out of Git.