# Task 01: Graph Inventory and Partition Contract

Status: complete — graph inventory PASS; component-level allocation infeasible.
Workstream: 03 — Development, Calibration, and Confirmation Partitioning.

## Objective

Define the empirical units that must remain separated before any outcome can be viewed or any final partition can be created. In PF-ERI, the unit cannot be a CSV row: a row-level split can leak a source image, target image, unordered physical pair, identity, or a connected graph component into more than one analytical role.

## What this task will produce

1. A canonical-pair graph inventory: images as nodes and unique unordered candidate pairs as edges.
2. An identity-connection inventory, limited to identities available under the access protocol.
3. A graph audit recording duplicate directions, repeated canonical pairs, image reuse, component sizes, descriptor overlap, unavailable assets, and any identity overlap that affects partitioning.
4. A partition contract that prohibits image and canonical-pair crossings, specifies the identity-disjoint sensitivity requirement when feasible, and defines the evidence needed to prove the constraints.
5. A reproducible inventory command and immutable input hashes.

## Explicit non-actions

This task will not create a real reviewer packet, import or inspect outcome labels, fit a model, choose a threshold, or assign development/calibration/confirmation membership. It also will not select allocation ratios or sample sizes. Those allocation decisions require the pre-specified power and cost analysis and must be fixed before confirmation data are exposed.

## Acceptance conditions for Task 01

- Every candidate pair is converted to a canonical unordered representation and linked to its two image nodes.
- Every directed row is reconciled to exactly one canonical pair or reported as an exception.
- The audit exposes all connected components and all image/pair reuse relevant to a split.
- Input artifact paths and SHA-256 hashes are recorded.
- The contract states a testable zero-crossing rule for physical images and canonical pairs.

## Next task boundary

Only after this inventory is auditable can the project generate and validate a proposed split. A proposed split cannot be called `partition_locked` until manifests demonstrate that every prohibited overlap count is zero.

## Completed audit

The audit was run on 2026-07-14 using only the frozen outcome-free dual-descriptor candidate reservoir. The canonical-pair manifest SHA-256 was `f6be9f3621576e905ef12b372f5e58fc09512687bba2b5c613e8bc6ced330ead`, and the directed-membership manifest SHA-256 was `78042bbe5adecae39c7d20d2bce0642d478c6a98694ce34db7e68ec12975640a`. It reconciled 85,182 unique, eligible, available canonical pairs with 120,000 directed descriptor-membership rows. There were no duplicate canonical identifiers, duplicate unordered endpoint pairs, self-pairs, missing canonical-pair references, invalid directions, endpoint-orientation mismatches, or contract-version mismatches. The inventory therefore passed its manifest-integrity checks.

The graph contains 3,000 image nodes and 85,182 eligible canonical-pair edges. All nodes belong to one connected component; image degree ranges from 24 to 183 eligible incident pairs, with median 52 and mean 56.788. This is a decisive design constraint rather than a failure of the reservoir. A future split cannot allocate whole connected components, because that would place the entire candidate universe into a single role. Instead, it must allocate disjoint sets of image nodes to development, calibration, and confirmation, retain only canonical pairs whose two endpoints lie within one allocated image set, and record every cross-set candidate edge as excluded. This is the only approach consistent with the rule that no image or canonical pair may cross a prohibited boundary.

The machine-readable audit, node and component inventories, scientific report, and figure are archived at `archive/pferi_v2/task_runs/information_partitioning/2026-07-14_graph_inventory_v1/`. The audit script is `scripts/audit_ws03_graph_inventory.py`; its two synthetic integrity tests passed before the production audit. Neither the audit nor its artifacts read identity truth, outcome labels, review responses, PF-ERI feature values, model outputs, or thresholds.
