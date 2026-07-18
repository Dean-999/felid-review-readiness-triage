# Workstream 03: Development, Calibration, and Confirmation Partitioning

Status: started — Task 01 graph inventory and partition contract.  
Primary dependency: Workstreams 00–02.  
Exit dependency: Workstream 04 cannot release a review packet without these boundaries.

## Purpose

This workstream creates the information barriers that make a favourable v2 result interpretable. Model development, probability calibration, and final confirmation answer different questions and must not share the same empirical information. In pairwise Re-ID, an ordinary random row split is inadequate because the same image, unordered pair, identity, or connected component can appear in several apparent observations.

## Procedure

Build the canonical image-pair graph from the candidate universe. Images are nodes and canonical unordered pairs are edges; a separate identity graph records known identity connections where they can be used for partitioning. The audit describes duplicated directions, repeated physical pairs, component sizes, identity overlap, descriptor overlap, and unavailable images. These graphs, rather than raw rows, define the allocation unit.

Allocate non-overlapping development, calibration, and confirmation partitions with a recorded random seed and a fixed allocation rule. No image or canonical unordered pair may cross partitions. The confirmation partition must also support a planned identity-disjoint sensitivity analysis whenever the CzechLynx identity structure permits it. Development is the only place where feature engineering, model-family comparison, and error analysis may respond to labels. Calibration is the only place where probability calibration and action thresholds may be fitted. Confirmation remains concealed until the model, feature schema, loss, code, and reporting choices are frozen.

The workstream also writes the access protocol. It specifies who can see identity truth, who can prepare blind packets, who may inspect outcome labels, and how generated files prevent forbidden fields from crossing into reviewer interfaces. It records the condition under which a confirmed data leak or accidental confirmation inspection invalidates a partition and forces a new confirmation set.

## Required Artifacts and Exit Decision

The required outputs are the canonical-pair manifest, image-pair and identity-graph audit, split manifest, access-control map, leakage-response procedure, and a reproducible split-generation command. The exit decision is `partition_locked` only when the manifests prove that no physical image or canonical pair crosses its prohibited boundary. Otherwise the decision is `partition_repair_required`, and no outcome review packet may be generated.

Task 01 is recorded in `01_graph_inventory_and_partition_contract.md`. It deliberately inventories the candidate graph and fixes the no-leakage rules before assigning any pair. It does not create an outcome packet, inspect outcome labels, or choose allocation ratios. Those material allocation choices must be supported by the later pre-specified power and cost analysis rather than invented after examining future confirmation results.

Task 02 is complete at `02_partition_constraints_and_leakage_validator.md`. It establishes separate full-accounting image and pair manifests, an executable zero-crossing validator, and a restricted identity-sensitivity interface. The contract refuses to equate structural PASS with `partition_locked`; no actual partition membership, sample allocation, or outcome packet has yet been created.

Task 03 is complete at `03_access_control_and_confirmation_leak_response.md`. It establishes a default-deny artifact access matrix, opaque future role assignments, a restricted identity boundary, and an irreversible response to premature confirmation exposure. It does not assign real people, create a split, or authorize any outcome review.

Task 04 is complete at `04_nonbinding_graph_capacity_stress_test.md`. It demonstrates that disjoint image sets leave adequate within-role pair and descriptor-family capacity under three explicitly nonbinding stress scenarios. On 15 July 2026 the owner subsequently accepted equal 1,000-image development, calibration, and confirmation roles plus a 2,000-analyzable-pair four-stage programme with a 2,224-pair planning reserve. On 16 July 2026 the owner accepted the formal outcome-free image-blocking and pair-stratification rules in `schemas/pferi_v2/four_stage_stratified_sampling_contract_v1.json`. No actual partition or official seed has been created, and the required full-frame automatic measurements and post-partition capacity audit remain incomplete, so the workstream is not `partition_locked`.
