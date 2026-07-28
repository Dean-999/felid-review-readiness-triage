# Task 02: Partition Constraints and Leakage Validator

Status: complete — executable contract and synthetic validation PASS.
Workstream: 03 — Development, Calibration, and Confirmation Partitioning.

## Scientific objective

This task converts the Workstream 03 information-boundary principle into a falsifiable machine contract. Its purpose is not to generate the development, calibration, and confirmation split. Its purpose is to define what a valid future split must prove and to ensure that a script cannot declare success merely because it produced three files. The validator reads only the frozen outcome-free canonical-pair universe and proposed partition manifests. Outcome labels, review decisions, measured PF-ERI features, fitted model values, thresholds, and routes are prohibited from the public partition artifacts.

## Why two manifests are required

A pair-only manifest cannot establish image independence. One image can participate in many canonical pairs and could silently appear in different analytical roles even if every canonical pair identifier appears only once. The contract therefore requires an image-partition manifest and a pair-partition manifest. The image manifest assigns each of the 3,000 candidate image nodes to exactly one of `development`, `calibration`, `confirmation`, or `unassigned`. The pair manifest accounts for every eligible canonical pair exactly once as `development`, `calibration`, `confirmation`, or `excluded`.

An active pair is valid only when its two endpoint images and the pair itself have the same active role. If the endpoint images have different roles, the pair must be excluded with the explicit reason `cross_partition_endpoints`. If either endpoint is unassigned, the pair must be excluded with the reason `unassigned_endpoint`. A pair whose endpoints share one active role may still be excluded under a later preregistered sampling rule, but the reason cannot be blank. These rules allow the single connected 3,000-image graph to be partitioned through disjoint image sets while preventing cross-set edges from becoming observations.

## Complete accounting and integrity conditions

The validator requires every image endpoint in the eligible candidate universe to appear exactly once and rejects images outside that universe. It likewise requires every eligible, available canonical pair to appear exactly once and rejects missing, duplicated, or unexpected pair identifiers. Pair endpoints must reproduce the frozen canonical endpoint order exactly. Manifest contract versions, role/status combinations, and exclusion reasons are validated independently. Additional columns whose names imply outcome, review, decision, label, score, feature, threshold, route, or identity information are rejected from the public image and pair partition manifests.

Complete accounting is essential because an omitted row is analytically ambiguous. Without it, investigators could not distinguish a legitimate prespecified exclusion from accidental loss or selective removal. The validator therefore treats a missing candidate as a structural failure even when the remaining assigned rows contain no obvious overlap.

## Restricted identity-disjoint sensitivity interface

Identity truth remains outside the public image and pair partition manifests. The validator provides a separate optional restricted interface consisting of an image-to-identity map and an identity-sensitivity pair manifest. These two artifacts must be supplied together. If neither is supplied, the structural audit may pass, but identity sensitivity is reported as `NOT_EVALUATED` and the partition is explicitly ineligible for locking.

When the restricted interface is used, every identity row must have `access_class = restricted`, refer to an image inside the candidate universe, and contain a resolved identity rather than an empty or `unknown` placeholder. The sensitivity manifest must be nonempty, and every sensitivity pair must already be an assigned confirmation pair. Identity mappings must cover all development and calibration images and every endpoint in the proposed sensitivity subset. The validator then tests whether any identity represented in that confirmation sensitivity subset also occurs in development or calibration. Only aggregate counts are written to the public audit; raw identities are not copied into it. An overlap, unresolved required identity, invalid confirmation pair, empty sensitivity set, or incomplete restricted interface is a failure.

## Decision semantics

The top-level validator status is `PASS` only when all supplied structural and restricted-interface checks have zero errors. A PASS with no restricted identity artifacts has `identity_sensitivity_status = NOT_EVALUATED` and `partition_lock_eligibility = PENDING_IDENTITY_AND_FREEZE_GATES`. A PASS with a successful identity audit has `partition_lock_eligibility = PENDING_FREEZE_GATES`. Any structural or identity-interface violation produces `REPAIR_REQUIRED`.

The validator is intentionally unable to write `partition_locked`. That later decision additionally requires the power-and-cost-supported numerical allocation, frozen random seed, access-control map, immutable hashes, and confirmation concealment evidence. This prevents a technically clean but scientifically incomplete split from being promoted into an authorized outcome packet.

## Artifacts and reproducible command

The executable contract is `schemas/pferi_v2/partition_constraint_contract_v1.json`, and blank templates for the two public manifests and two restricted identity artifacts are stored beside it. The validator is `scripts/validate_v2_partition_constraints.py`. A future proposed split is checked with the following command after its image and pair manifests exist:

```bash
python scripts/validate_v2_partition_constraints.py \
  --canonical-pairs work/pferi_v2/pipeline/dual_descriptor_queue/canonical_pairs.csv \
  --image-partitions PATH/partition_images.csv \
  --pair-partitions PATH/partition_pairs.csv \
  --audit-json PATH/partition_constraint_audit.json \
  --issue-csv PATH/partition_constraint_issues.csv
```

The restricted identity options are appended only within an authorized environment. The checked-in test suite covers a valid complete partition, hidden pair omission, a cross-role pair incorrectly assigned as active, a forbidden outcome-bearing column, a valid identity-disjoint sensitivity subset, an identity overlap with development, schema synchronization, and CLI artifact serialization. Task 02 does not create or imply a real split.
