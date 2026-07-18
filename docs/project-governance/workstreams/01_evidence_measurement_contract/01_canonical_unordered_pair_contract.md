# Task 01: Canonical Unordered-Pair Contract

Status: complete.  
Contract version: `pferi_v2_canonical_pair_contract_v1`.

## Purpose

PF-ERI v2 treats a physical image pair, rather than a directed retrieval row, as the unit of evidence. This contract prevents one image pair from being counted twice merely because it appears in both query directions or in several descriptor queues. At the same time, it preserves every retrieval membership needed later for descriptor-specific analysis and representative queue sampling. The contract is deliberately outcome-free: no reviewability decision, PF-ERI value, route, feature value, or identity truth may be placed in a reviewer-facing pair manifest.

## Three Separated Manifests

The canonical-pairs manifest contains one row for each unordered image pair. Its endpoints are sorted lexicographically and its opaque identifier is computed from the ordered endpoint pair using SHA-256. The manifest records source dataset, image-pair availability, inclusion status, and an exclusion reason where applicable. It does not contain known identity or any future outcome information.

The candidate-memberships manifest contains one row for each directed descriptor-queue membership. It references a canonical pair while retaining descriptor name, queue and snapshot, directed query and candidate image IDs, candidate rank, descriptor similarity, and direction. Several rows may legitimately reference the same canonical pair; this is how the contract preserves cross-descriptor and reverse-direction retrieval evidence without treating it as independent pair evidence.

The restricted identity-audit manifest is optional and separate. When known CzechLynx identity truth is needed for later sampling or subgroup analysis, it records only the canonical pair, same/different/unknown truth, truth source, and restricted access class. It is never a reviewer-facing export and cannot be merged into an outcome-review packet.

## Validation and Failure Rules

The validator rejects self-pairs, unsorted endpoints, canonical identifiers that do not match the endpoints, duplicate canonical pairs, memberships that refer to unknown pairs, memberships whose directed endpoints do not equal the canonical endpoints, invalid rank or similarity values, and duplicate directed memberships. It also rejects forbidden field names in canonical and membership manifests. This provides a structural defence against the v1 failure in which pair-direction duplication and assignment information could contaminate inference.

The checked-in machine-readable schema is `schemas/pferi_v2/canonical_pair_contract_v1.json`. The implementation is `scripts/build_v2_canonical_pair_contract.py`. Once a future Workstream 04 manifest exists, validate it with the command below; the command writes an audit and exits nonzero on any contract violation.

```bash
python3 scripts/build_v2_canonical_pair_contract.py \
  --canonical-pairs path/to/canonical_pairs.csv \
  --candidate-memberships path/to/candidate_memberships.csv \
  --identity-audit path/to/restricted_identity_audit.csv \
  --audit-json path/to/canonical_pair_contract_audit.json
```

## Boundary

This task creates a data contract and validator, not a v2 candidate dataset or a model result. It does not select pairs, compute a feature, reveal identity truth, collect a reviewability outcome, or set a route threshold. Those operations remain in later Workstreams.
