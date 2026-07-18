# Workstream 02: Measurement Feasibility Pilot

Status: complete — `measurement_ready_with_reduced_feature_set`.  
Primary dependency: Workstream 01.  
Exit dependency: Workstreams 03–05 may use only feature families that pass this gate.

## Purpose

This workstream asks whether PF-ERI’s proposed evidence variables can be measured reliably enough to justify modelling. It is deliberately a pilot, not a hidden small confirmation study. Its value is to reveal constant fields, ambiguous definitions, automation failures, manual correction burden, and reviewer disagreement before the 1,200-pair protocol consumes the scarce outcome-review budget.

## Procedure

Select a new difficult-case pilot that covers the conditions likely to break the measurement system, including weak and strong animal visibility, incompatible and compatible viewpoints, day and infrared images, blur, occlusion, different descriptors, and incomplete feature inference. The pilot must not reuse a v1 outcome label as a target and must remain separate from the two v2 confirmation samples. Its selection logic, seed, image identities, pair identities, and intended coverage are recorded before human annotation begins.

For each structural feature, obtain independent human measurement when human measurement is part of the validation plan, run the automatic extractor without access to outcome labels, and record value distribution, missingness, agreement, computation time, failure rate, and required manual correction. Separately, test the blinded review interface on a small operational run to identify ambiguous wording, image-rendering defects, data leakage, and impractical review duration. The pilot does not choose a model based on which feature happens to correlate most strongly with a preliminary outcome.

Numerical reliability, variation, and operational-time gates must be set before pilot measurements are inspected and applied to the pilot before the main packet is generated. A core feature that is constant, unreliable, unavailable during automatic inference, or more expensive to correct than its plausible value must be removed, redefined, or moved to the oracle-only analysis. The decision and its rationale are frozen before development and confirmation labels are analysed.

## Required Artifacts and Exit Decision

The workstream produces a pilot manifest, feature-variation report, agreement analysis, automatic-versus-human comparison, inference-time and failure log, interface-leakage report, and a dated feature-retention decision. The exit decision is `measurement_ready`, `measurement_ready_with_reduced_feature_set`, or `measurement_not_ready`. The project cannot call a feature independent evidence or include it in the primary model until it has passed this gate.

Task 01 is complete at `01_pilot_isolation_and_preregistered_gates.md`. It fixes the 160-pair outcome-free pilot target, canonical-pair unit, confirmation exclusion, selection boundary, and ten pre-measurement retention gates. Task 02 is complete: the fixed seed selected 160 unique, outcome-free canonical pairs from the fresh 85,182-pair dual-descriptor reservoir, recorded in `outputs/pferi_v2/measurement_feasibility_pilot/`. The independent structural-oracle run is complete on all 160 pairs. All three continuous structural measurements pass their ICC lower-bound gates, and the corrected, pre-specified viewpoint weighted-kappa analysis also passes. These structural fields remain oracle-only by design and are not automatic-model inputs. The automatic-quality branch is complete with a reduced feature set: native pixel count, sharpness, and channel-extreme clipping are retained as automatic quality candidates, while the generic COCO cat-mask coverage proxy is excluded after failing its pre-specified valid-output gate. The remaining hard exit task is the independently audited reviewer-interface dry run before any real outcome collection.

The upstream neutral image-context input is complete at `03_neutral_v2_image_context.md`. Fresh descriptor queues, canonical pairs, and directed memberships have now been generated and audited; the pilot manifest excludes every selected canonical pair from later confirmation sampling.

The fresh MegaDescriptor and independent DINOv2 runs have passed input, output, and mathematical-consistency audits; their frozen dual-queue reservoir is the sole Task 02 sampling source.

The current 160-pair two-annotator structural-oracle batch is complete and has no technical missingness. All three continuous structural field families pass their pre-registered absolute-agreement ICC lower-bound gates. The corrected viewpoint rule fixes the order `incompatible < partial < compatible`, linear weights, unknown handling, pair-level bootstrap count, and seed; the weighted-kappa lower bound also passes. The complete structural-oracle measurement gate is PASS. Oracle fields remain excluded from the primary automatic model by design.

The frozen SuperPoint–LightGlue–RANSAC local-match GPU execution is now archived at `outputs/pferi_v2/measurement_feasibility_pilot/local_match_runs/2026-07-14_gpu_t4_protocol_v2/`. Its output audit, smoke test, and freeze verification pass. The 160 canonical coverage values satisfy the pre-registered local-match feasibility gate: all are valid, 154 are distinct, the exact canonical-minimum rule has zero violations, manual rescue is zero, and the pair-runtime 95th percentile is 1.659 seconds. This is a measurement-feasibility pass only; it is not an identity or Re-ID-performance result. With the automatic-quality reduced-set decision now frozen, Workstream 02 cannot exit as overall `measurement_ready` until the independently audited reviewer-interface dry run has met its required conditions.

The frozen field-level decision is recorded in `07_feature_retention_decision.md`. It retains automatic local-match coverage, native pixel count, sharpness, and channel-extreme clipping as later model candidates; it excludes the generic COCO cat-mask coverage proxy after its 37.0% valid-output rate failed the 90% gate; and it keeps all human structural fields oracle-only.

The v2 reviewer-interface dry run is complete at `11_v2_reviewer_interface_dry_run.md`. Its deterministic twelve-pair, outcome-free package passed the machine static leakage audit, local UI health check, and an independent browser audit. Auditor `A001` completed all eight required checks with no documented exposure; the returned delivery was validated and shown byte-identical to the official reviewer-visible release. The final consolidated evidence and claim boundary are recorded in `12_workstream_02_exit_decision.md`. This closes Workstream 02 only at `measurement_ready_with_reduced_feature_set`; it does not change the project-wide `v2_protocol_prelock` status or authorize collection before later packet-specific gates.
