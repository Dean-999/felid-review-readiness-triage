# Workstream 04: Dual-Sample Confirmatory Design

Status: in progress — design, automatic measurement, formal sampling, human outcome collection, adjudication, final endpoint assembly, and stage-isolated analysis entry are complete; only the development stage is open for model construction, while calibration and both confirmation stages remain locked.
Primary dependency: Workstreams 01–03.
Exit dependency: Workstream 05 may analyse deployment utility only after this workstream locks the representative queue.

## Purpose

PF-ERI v2 needs two samples because a sample designed to expose mechanisms is not automatically representative of the real candidate queue. The 400-pair mechanism-confirmation sample tests whether pair evidence remains meaningful across the conditions that could explain it away. The 800-pair deployment-queue sample estimates calibration, coverage, risk, review time, and cost under a documented candidate distribution. Treating the two samples as interchangeable would reproduce one of v1’s central inferential errors.

## Procedure

First, run and archive a power-and-cost simulation that uses the graph structure, reviewer workload, anticipated missingness, and the minimum practical Brier-score increment selected before outcome review. The accepted programme now contains 2,000 analyzable pairs: 400 development, 400 calibration, 400 mechanism confirmation, and 800 deployment confirmation. With the accepted 0.90 planning completion fraction, it prepares 2,224 unique unordered pairs. This pre-outcome decision replaces the historical 1,200-pair default because development and calibration require their own outcome information and cannot reuse confirmation outcomes.

Second, construct the 400-pair mechanism sample with pre-specified coverage across descriptor family, similarity or rank, independent quality state, laterality or viewpoint, visible evidence state, known same/different identity status, camera or site, and illumination when available. The sample intentionally makes difficult comparisons visible. It therefore estimates conditional mechanisms and feature failures, not ordinary queue prevalence.

Third, probability-sample 800 additional canonical pairs from the frozen candidate queue, retaining inclusion probabilities and both descriptor memberships where relevant. A duplicate pair retrieved by two descriptors is reviewed once but retains both memberships in the hidden analysis manifest. The packet builder writes a reviewer-facing export that contains only neutral identifiers, rendered image locations, and response fields. An independent leakage audit must inspect the interface, filenames, columns, sort behaviour, and cached data before reviewers see a single pair.

## Required Artifacts and Exit Decision

The workstream requires a power-and-cost simulation, frozen sampling manifest, duplicate and image-availability audits, inclusion-probability record, reviewer assignment table, blind-interface audit, and raw review-log destination. Its exit decision is `v2_design_locked` only when all numerical gates and packet artifacts are frozen before outcome review. A successful mechanism result cannot substitute for a deployment-queue result, and an attractive deployment result cannot repair an unmeasured mechanism.

Task 01 is complete at `01_power_cost_input_audit_and_simulation_contract.md`. It records the approved outcome-free graph and measurement inputs, labels v1 reviewer summaries as sensitivity context only, fixes the direction of the Brier increment, and exposes the decisions that still require a pre-outcome freeze. Its original blocked result predates the accepted four-stage allocation and does not authorize a sampling seed.

Task 02 is complete at `02_nonbinding_power_cost_sensitivity_simulation.md`. Its timing profiles remain historical, nonbinding sensitivity illustrations and do not set an expected review duration, capacity threshold, or collection window. Task 03 completed an earlier critical readiness review at `03_pre_outcome_numerical_freeze_readiness_review.md`. Subsequent pre-outcome owner decisions have resolved the primary rule, four-stage allocation, dependence/interval specification, reviewer-operation design, and sampling-strata design, while full-frame measurements, seed, and actual role assignment remain unresolved. The working decision record must still be completed before official sampling execution.

Task 04 is documented at `04_timed_operational_rehearsal.md`. The original v1 operational return failed its duplicate-participant-packet gate and was retired without contributing evidence. The replacement v2 package used a distinct 24-pair pilot-excluded set and a restricted allocation manifest that fixed every participant's packet and role before the interface opened. Its 72-row return passed the frozen operational audit, so the project now has limited observed evidence about this interface's completion and workflow duration. The result does not estimate formal-label completion, and the accepted 0.90 planning fraction is not derived from it.

The accepted allocation is versioned in `schemas/pferi_v2/four_stage_sample_allocation_contract_v1.json`. Its readiness audit compares the resulting 445 development, 445 calibration, and combined 1,334 confirmation planned-pair requirements with the archived equal-thirds graph stress evidence. A capacity PASS does not authorize an outcome packet. Full-image quality measurement, the historical-pair exclusion register, and image-strata preflight precede the one-time official seed. Within-role automatic pair measurements and the post-partition capacity audit necessarily follow image allocation and must pass before pair sampling.

The dependence and interval choice is recorded at `03_dependence_and_interval_decision_proposal.md`. The project owner accepted the conservative predeclared planning values and a dyadic cluster-robust primary interval on 15 July 2026, while retaining the explicit precision limitation of the 800-pair deployment sample. This decision is eligible for the final outcome-free execution audit, but it does not authorize sampling until full-frame measurements pass and the official seed is frozen.

The reviewer-operation rule is recorded at `03_reviewer_operation_design.md`. The project owner accepted full double review for all 2,224 prepared pairs and conflict-free third-person adjudication on 15 July 2026. No expected review duration, adjudication rate, total-hour budget, or collection window is part of the design. Actual time and adjudication frequency will be reported from the operational logs supplied after collection. The restricted `03_reviewer_role_assignment_template.md` verifies identity separation and access control before packet release.

The formal strata design is recorded at `03_sampling_strata_design_proposal.md`, with machine-readable rules in `schemas/pferi_v2/four_stage_stratified_sampling_contract_v1.json`. The project owner accepted it pre-outcome on 16 July 2026. It fixes graph- and quality-blocked image allocation, representative proportional sampling for calibration and deployment, balanced outcome-free coverage for development, and a separate challenge-enriched mechanism sample drawn only after deployment selection. Retained full-image measurements, the 160-pair hashed exclusion register, and the image-strata preflight passed. The one-time seed and exact zero-overlap 1,000/1,000/1,000 image allocation are now frozen. Pair sampling and outcome packets remain blocked until within-role measurements and all post-allocation gates pass.

The verified execution state is summarized in `03_sampling_execution_status_20260716.md`. The frozen allocation yields 28,295 eligible within-role pairs across three role frames, all nine retrieval strata are present in every role, and the complete frame has been split into 30 computational shards for frozen automatic local-evidence measurement. These shards are execution units, not formal review samples.

The full-frame execution history and current engineering contract are consolidated
in `05_colab_full_frame_execution_engineering_audit.md`. The failed Kaggle range
inference and abandoned Kaggle-to-Colab continuation are retained there as
iteration history. The accepted package performs one fresh inventory-driven run
over all 30 shards, with input/model binding, resumable execution, global
validation, deterministic merge, and one checksum-protected export.

The completed result is audited in `07_full_frame_measurement_result_audit_20260720.md`
and archived under `archive/pferi_v2/task_runs/measurements/local_match/`.
All 30 shards and 28,295 pairs are present; 28,284 pairs have valid frozen
measurements and 11 retain prespecified scientific failure codes. This closes the
full-frame execution dependency but does not establish identity accuracy or
biological validity. The next authorized action is the outcome-free
post-allocation capacity/strata audit followed by formal role-specific pair
sampling under the accepted contract.

The first post-measurement step is accepted in
`08_post_allocation_sampling_derivation_freeze_proposal.md`, with a
machine-readable operational supplement at
`schemas/pferi_v2/post_allocation_sampling_derivation_contract_v1.json`. It
removes ambiguity in percentile ties, zero-coverage handling, descriptor
percentiles, and deterministic pair-seed namespaces without changing the
accepted scientific design. The project owner accepted it pre-outcome on 20
July 2026. This authorizes the restricted derivation frame and capacity audit
only; no formal pair has been selected and no outcome packet is authorized.

The accepted derivation was implemented and audited in
`09_post_allocation_derivation_and_capacity_audit_20260720.md`. The restricted
28,295-pair master frame joins exactly, preserves all eleven scientific matcher
failures and all finite zero measurements, and reports sufficient capacity for
the accepted 445/445/889/445 collection totals. Exact mechanism challenge cells
remain correctly deferred until the deployment draw is immutable. This PASS
does not itself authorize the formal draw, reviewer packet, or outcome access.

The project owner subsequently authorized the one-time formal draw. Its frozen
execution and independent reconstruction are recorded in
`10_formal_pair_sampling_freeze_20260720.md`. The checksum-protected restricted
manifest contains exactly 445 development, 445 calibration, 889 deployment,
and 445 post-deployment mechanism pairs, with 2,224 unique canonical pair IDs
and zero pair overlap. The formal draw is complete and must not be rerun. The
next blocked gate is reviewer-role assignment plus blinded packet construction
and a fresh leakage audit; no reviewer outcome has been collected.

Reviewer workload and assignment planning is recorded in
`11_reviewer_workload_and_assignment_planning_20260720.md`. The formal sample
requires exactly 4,448 independent first-pass decisions before any
adjudication. A provisional four-code plan balances this to 1,112 tasks per
person and leaves two eligible adjudicators per pair, but it is not released:
the actual number of distinct trained people must be confirmed before packet
IDs, assignments, and reviewer-specific asset tokens can be frozen.

Task 13 is recorded in `13_final_adjudicated_outcome_assembly_20260722.md`.
The accepted human returns contain all 4,448 first-pass decisions and one fresh
adjudication for each of the 250 exact three-category disagreements. The
deterministic merge produced 2,224 unique final endpoints, preserved assignment
and sampling lineage, excluded submission time, and passed checksum and schema
verification. The study owner accepted the returned CSV judgements and declared
use of the supplied collection application nonbinding. This outcome freeze
establishes the response variable but does not establish model performance.

Task 14 is recorded in `14_stage_isolated_analysis_entry_freeze_20260722.md`.
It joins the formal pairs to the frozen outcome-free automatic feature frame,
opens one 445-row development modelling table, and emits separate outcome-free
feature tables for 445 calibration, 889 deployment-confirmation, and 445
mechanism-confirmation pairs. No human outcome column appears in a locked-stage
feature table. Calibration requires a passed development-model freeze, and both
confirmation stages additionally require a frozen calibration policy, analysis
bundle, and active-control and full-model predictions. The next authorized
action is development-only probabilistic model construction under Task 15.
