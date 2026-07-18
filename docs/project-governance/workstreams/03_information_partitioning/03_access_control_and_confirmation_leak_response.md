# Task 03: Access Control and Confirmation-Leak Response

Status: complete — least-privilege contract and adversarial validation PASS.  
Workstream: 03 — Development, Calibration, and Confirmation Partitioning.

## Purpose

Partitioning is not sufficient if the people or systems surrounding a partition can move information across its boundary. This protocol therefore treats each file class as a controlled artifact and gives every role only the minimum access needed for its assigned operation. The governing rule is default deny: an access path that is not explicitly listed is prohibited. The protocol is deliberately independent of any named individual. Names are introduced only later through opaque role assignments, so a change in personnel cannot silently change the scientific boundary.

## Role and artifact boundary

The protocol custodian may inspect the frozen candidate and partition manifests and may maintain the public incident register, but cannot access outcomes, identity truth, linkage, model artifacts, or confirmation outputs. The identity custodian may create and inspect restricted identity artifacts required for the later sensitivity analysis, but cannot access outcomes or modelling artifacts. The packet builder may use the frozen candidate and partition manifests, rendered image sources, and restricted packet linkage to construct reviewer-visible packets. This role cannot access outcomes, model artifacts, calibration policies, or confirmation results.

First-pass reviewers and adjudicators receive only the neutral reviewer-visible packet and may submit only their own raw response. They cannot access canonical pair identifiers, image identifiers, restricted linkage, identity truth, automatic measurements, descriptor values, ranks, thresholds, routes, peer responses, prior decisions, majority labels, adjudicated labels, or model-ready recodes. An adjudicator is deliberately not shown prior responses; adjudication is an independent reassessment of the rendered pair rather than a vote influenced by the first pass. The independent interface auditor receives only the reviewer-visible packet and the audit evidence needed to inspect it, and is subject to the same prohibition on restricted artifacts and outcomes.

The measurement operator is the only role that writes the partition-scoped automatic feature tables and has no access to outcomes or identity truth. The development analyst may use only development features and development outcomes to establish the model form and feature treatment. The calibration analyst receives the frozen development model artifact together with only calibration features and calibration outcomes. Neither analyst receives a confirmation feature or outcome table. The confirmation release officer holds the controlled confirmation feature and outcome artifacts and may execute, but not alter, the frozen confirmation analysis bundle. The confirmation analyst can read the confirmation feature and outcome tables only at formal release, can execute the frozen bundle, and can write final confirmation outputs. This role cannot modify the partition, reviewer packet, development model, calibration policy, or frozen analysis bundle. The access matrix is intentionally stricter than a convenience-based workflow because even outcome-free confirmation feature values could otherwise influence preprocessing or model choices before the final test.

## Role assignments and separation in practice

Before any real packet is built, each real participant must sign an opaque role-assignment record that names the role, scope, status, conflict attestation, and timestamp. A first-pass reviewer cannot adjudicate the same packet or access its prior response. Packet builders, identity custodians, and interface auditors cannot become first-pass reviewers for packets whose restricted artifacts they handled. The same analysis lead may perform development and calibration in sequence, but confirmation outcomes remain unavailable until all model, feature, loss, threshold, sampling, code, and reporting choices are frozen. Once that person or any other authorized confirmation analyst has viewed the confirmation outcome, no change informed by it is permitted within v2; a changed analysis is v3 and requires a new unseen confirmation set.

## Leak detection and immediate containment

A leak includes direct display, exported field, filename, URL, browser history or cache, hidden or network field, error trace, shared directory, access-control misconfiguration, or an inferable derivative that exposes a forbidden condition. On detection, the operator stops the affected interface or analysis process, revokes the relevant link or credential, preserves the artifact and logs without overwriting them, computes or records evidence hashes, and opens an incident register entry. The public incident register contains only scope and disposition information. Any sensitive detail is stored through a restricted pointer so that documenting the leak does not create a second leak.

If a reviewer-visible packet leaks a forbidden field, the affected batch is invalid. Any raw responses already collected are retained as historical evidence but excluded from the primary analysis; they are not silently edited, relabelled, or deleted. The packet must be rebuilt from the frozen allocation, independently re-audited in a real browser, and replaced before further review. If restricted identity information is exposed in a way that could influence selection or assessment, the affected sensitivity selection must be re-evaluated and the relevant partition repaired before outcome review continues.

The most serious case is premature confirmation exposure. If a confirmation outcome, or a derivative from which it can be inferred, reaches a person who can still change model form, feature treatment, loss, threshold, sampling, or reporting choices, that confirmation partition is permanently contaminated for v2. It cannot be repaired by asking the recipient to disregard it, by deleting a file, or by collecting another response for the same pair. The affected evidence and incident logs remain preserved. A future analysis must use a newly drawn confirmation set under a successor protocol. This asymmetry is intentional: a one-shot confirmation estimate is valuable precisely because it has not influenced analytical choices.

## Evidence and decision boundary

The executable contract defines ten abstract roles, twenty artifact classes, and a default-deny allowlist. It includes a public incident-register schema and a separate role-assignment schema, both of which use opaque actors and scope identifiers. The validator rejects an altered frozen contract, outcome access granted to packet builders or reviewers, restricted linkage granted to reviewers, and any confirmation role that can rewrite a pre-release model or calibration policy. Its PASS means only that this abstract least-privilege contract is internally consistent. It does not assign real people, generate a split, create a reviewer packet, or authorize outcome review.

## Reproducible verification

The contract is stored in `schemas/pferi_v2/access_control_and_leak_response_contract_v1.json` and can be checked as follows:

```bash
python scripts/validate_v2_access_control_contract.py \
  --contract schemas/pferi_v2/access_control_and_leak_response_contract_v1.json \
  --audit-json PATH/access_control_audit.json \
  --issue-csv PATH/access_control_issues.csv
```

The role-assignment and incident-register templates are stored beside the contract. They remain blank until the numerical allocation and real operational roles are frozen. This task therefore creates a verifiable boundary without prematurely assigning people or exposing confirmation information.
