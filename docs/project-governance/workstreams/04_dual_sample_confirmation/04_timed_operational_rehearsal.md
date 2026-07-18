# Task 04: Timed Outcome-Free Operational Rehearsal

Status: complete — v1 retired after failed return audit; v2 assignment-enforced return passed.  
Workstream: 04 — Dual-Sample Confirmatory Design.

## Aim

This task measures whether the locked neutral interface can be operated within a plausible reviewer workload before the project freezes a collection reserve or a principal review-time budget. It is deliberately not a reviewability study. The rehearsal uses 24 canonical pairs selected only from the 160-pair outcome-free pilot, whose audit permanently excludes them from both v2 confirmation samples. Participants are instructed not to make, record, or discuss an image judgement. The only returned variables are opaque participant code, opaque packet code, role, start and submission timestamps, elapsed seconds, completion status, and technical-interruption category.

## Bias controls and claim boundary

The protocol prevents the most dangerous shortcut: turning a timing rehearsal into covert label collection. The interface contains no review-ready decision, reason, confidence, note, identity, descriptor, feature, rank, score, route, or prior-response field. It writes a separate coordinator-only operational log, and the reviewer delivery ZIP contains only opaque rendered assets, neutral packets, the timing interface, and participant instructions. The timing result cannot be used to choose a model, claim reviewer reliability, estimate an effect size, or reuse a pair in the study. It can inform only the workload, completion, technical-failure, and adjudicator-operation assumptions required before a binding power-and-cost simulation.

## Execution

The original v1 return was retired: although it contained three participants and 98 completed operational rows, it failed the frozen return audit because the free-form interface allowed duplicate `(participant, packet)` submissions. No v1 raw return is used as evidence. The v1 delivery directory was removed at the user's request after its aggregate disposition and the pair-retirement ledger were recorded.

The v2 package uses a distinct set of 24 permanently excluded pilot pairs, enforced by `timed_operational_rehearsal_v1_retired_pair_ids.csv`. The coordinator starts the full v2 package with the restricted allocation manifest available only on the coordinator machine:

```bash
cd outputs/pferi_v2/dual_sample_confirmation/2026-07-15_timed_operational_rehearsal_v2
PF_ERI_V2_ASSIGNMENT_FILE=restricted/participant_task_allocation.csv \
PF_ERI_V2_OPERATIONAL_LOG_DIR=operational_logs \
python -m streamlit run reviewer_view/app.py
```

Give each participant only one assigned opaque code from the restricted allocation manifest. The interface derives the workflow role, supplies only that participant's remaining task queue, and excludes a submitted packet from that participant's queue. Participants must independently complete the interface without opening files or observing another participant. Three codes are allocated 24 tasks each; packets 001–012 and 013–024 exchange first-pass and adjudication workflow roles between the first two codes, while the third code performs an independent first pass. Thus no participant receives a packet twice.

After all sessions, the coordinator runs:

```bash
python scripts/audit_v2_timed_operational_rehearsal.py \
  --rehearsal-dir outputs/pferi_v2/dual_sample_confirmation/2026-07-15_timed_operational_rehearsal_v2 \
  --contract schemas/pferi_v2/timed_operational_rehearsal_contract_v2.json \
  --audit-json outputs/pferi_v2/dual_sample_confirmation/2026-07-15_timed_operational_rehearsal_v2/operational_return_audit.json
```

The auditor rejects wrong headers, semantic response fields, duplicate packets within participant, invalid timing values, insufficient participants, insufficient completions, missing adjudication rehearsal, and any `(participant, packet, role)` absent from the restricted allocation manifest.

## Interpretation

A PASS establishes only that the stated minimum rehearsal workload has been observed under this interface and that a future completion reserve can be justified more honestly. It does not authorize a v2 outcome packet or numerical freeze by itself. The decision record still needs an accepted practical Brier rule, confirmation allocation, conservative dependence scenario, role availability, and a principal transparent cost region.
