# PF-ERI v2 Workstreams

Status: `v2_protocol_prelock`  
Date: 2026-07-10

This directory is the operational map for the PF-ERI v2 rebuild. Each numbered folder converts one workstream from the adversarial project review into a bounded scientific task. A workstream is complete only when its stated source artifacts, audit conditions, and exit decision exist. Completing code, creating a spreadsheet, or producing a visually attractive result is not sufficient by itself.

The workstreams are intentionally ordered. Workstream 00 protects the historical record and prevents v1 results from leaking into a prospective claim. Workstreams 01 and 02 establish whether the proposed construct can actually be measured. Workstream 03 creates the information boundaries required for honest modelling. Workstream 04 creates the two confirmation samples. Workstream 05 then evaluates the probabilistic decision and its human-workflow consequences. Workstream 06 is an extension pathway, not a shortcut around CzechLynx confirmation.

The scientific rationale and original upgrade logic are recorded in `paper/reviews/2026-07-10_pferi_full_project_adversarial_hv_report.md`. The existing saved literature record is used rather than duplicated here: `sources/2026-06-17_pferi_gap_model_map.md` anchors the pair-admissibility gap, while `sources/2026-06-17_pferi_research_gap_workflow_assessment.md` anchors the relationship to animal Re-ID, biometric quality, selective prediction, and human-in-the-loop wildlife workflows. The binding rules remain in `PROJECT_RULES.md`; these documents explain how to implement them without changing their claim boundary.

Each folder contains a single implementation note written as a protocol rather than a results report. The note specifies the purpose, inputs, procedure, required artifacts, dependencies, and exit decision. Generated manifests, raw logs, images, and numerical outputs belong in their appropriate data or output locations and must be linked from the corresponding workstream only after direct audit.
