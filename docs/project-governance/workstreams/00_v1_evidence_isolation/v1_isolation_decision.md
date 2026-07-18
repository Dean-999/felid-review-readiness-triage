# Workstream 00 Evidence-Isolation Decision

Status: `isolated_with_provenance_pending`  
Date: 2026-07-10

## Summary

Workstream 00 audited the historical PF-ERI v1 evidence chain: candidate-pair packets, completed review records, reliability records, derived model and routing outputs, and claim-bearing presentation materials. The inventory is in `v1_evidence_inventory.csv`, and claim-bearing entry points are tracked in `v1_claim_bearing_file_audit.csv`. The result is an evidence-preservation decision, not a deletion decision. V1 remains scientifically useful as exploratory material but cannot satisfy any PF-ERI v2 measurement, calibration, confirmation, workflow, or external-validation requirement.

## Strengths Retained

V1 has genuine strengths. It contains preserved raw Phase18M working records, a reproducible derived 400-row CzechLynx table, explicit model and routing artifacts, and an unusually detailed historical trail of the project’s design changes. These records allow v2 to target real failure mechanisms rather than inventing a new problem. The study also already distinguishes its endpoint from automatic identity assignment and retains known identity truth separately from the reviewability concept in many derived artifacts.

## Critical Threats to Validity

The principal threat is outcome-ascertainment bias. The Phase18M review application exposed PF-ERI evidence group, same/different identity stratum, and candidate rank while reviewers made the outcome decision. This directly compromises blinding and makes the apparent relationship between the experimental condition and reviewability vulnerable to observer expectation and circular construct measurement. The presence of 1,200 filled records does not repair this problem; it establishes that the historical outcome was collected, not that it was independently assessed.

The second critical threat is provenance failure in the reliability evidence. The source audit labels the 0.859305 result as synthetic and the corresponding nominal external-reviewer file contains no completed reviews. The 0.785098 result is associated with a filled file whose own notes describe synthetic calibration, whereas a later corrected copy asserts independent external review without supplying the primary documentation needed to resolve the contradiction. Reliability statistics are only as credible as the provenance of the ratings they compare.

The third critical threat is the temptation to treat a rich set of derived outputs as independent replication. The model table, calibration bins, routing analyses, figures, and manuscript claims are all downstream of the same v1 labels and feature environment. Their agreement is not convergence from independent methods; it is dependence within one evidence chain. In addition, the Phase18N packet’s collapsed quality strata and duplicate unordered pairs show that an apparently larger future packet was not yet a valid repair.

## Evidence Grade and Permitted Conclusion

For the prospective CzechLynx claim, v1 is graded as very low confidence: it is a single-project exploratory evidence package with serious risk of bias, construct contamination, provenance inconsistency, and indirectness to a deployment workflow. This grade concerns the strength of the confirmatory claim, not the value of the research question. The supported conclusion is that v1 generated a plausible and testable hypothesis: pair-level evidence may matter after descriptor retrieval. The unsupported conclusion is that PF-ERI v1 has already validated that hypothesis, calibrated a safe route, or demonstrated human-review reliability.

## Required Safeguards Now in Force

All listed source records remain unchanged and are anchored by the hashes in the inventory. Every claim-bearing entry point is marked or covered by a visible v1 historical or submission-lock notice. The synthetic reviewer result is prohibited from human-reliability reporting. The reviewer-2 result is provenance pending. The retired Phase18N packet must not be distributed. No v1 image, pair, outcome label, feature result, threshold, or derived route may cross into a v2 development, calibration, or confirmation estimate except as an explicitly labelled exploratory input to a design simulation.

## Exit Decision

The workstream is complete at `isolated_with_provenance_pending`. The only unresolved item is reviewer-2 provenance, which is not a blocker because PF-ERI v2 collects new blinded outcome records. Workstream 01 may begin, but its feature contract must not inherit a v1 constant proxy, v1 outcome-reviewer judgement, or v1 threshold merely because it produced an attractive historical chart.
