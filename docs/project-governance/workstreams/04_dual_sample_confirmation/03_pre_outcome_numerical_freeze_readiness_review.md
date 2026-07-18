# Task 03: Pre-Outcome Numerical-Freeze Readiness Review

Status: historical readiness assessment updated after the timed operational rehearsal; later owner decisions are recorded in `03_pre_outcome_numerical_decision_record_draft.md`, and the complete numerical freeze is still not authorized.  
Workstream: 04 — Dual-Sample Confirmatory Design.

## Purpose

This review asks whether the project can now truthfully convert the nonbinding sensitivity map into a binding target, allocation, seed, and decision rule. It evaluates design readiness rather than whether a future PF-ERI result will be favorable. The review uses the frozen candidate graph, outcome-free measurement audits, the Task 02 synthetic sensitivity analysis, and the binding project rules. It does not read a v2 reviewability label, reviewer response, model prediction, calibration result, identity value, or confirmation output.

This document preserves the decision state at the time of that review. On 15 July 2026, the project owner subsequently accepted the primary superiority rule, the four-stage sample allocation, the conservative dependence/interval specification, and the reviewer-operation design. The owner further directed that estimated review time and a calendar collection window are not design inputs; actual time will be reported after execution. On 16 July 2026, the owner accepted the formal outcome-free sampling-strata design. Those later decisions supersede the corresponding unresolved entries below but do not retroactively alter the evidence available when this readiness assessment was written. Full-frame automatic measurements, the official seed, and the actual conflict-free role assignment remain unresolved.

## What the current evidence supports

The project has an unusually strong pre-outcome foundation for a small wildlife reviewability study. The canonical reservoir has 85,182 eligible unordered pairs over 3,000 images, and the Workstream 03 stress test showed that image-disjoint roles retain adequate candidate capacity. The local-match and retained automatic-quality measurements have passed their outcome-free feasibility gates. The Task 02 simulation also correctly rejects the independence fiction: sampled pairs can share image endpoints, so a power calculation must carry a graph-aware variance component rather than treating descriptor directions or pair rows as independent observations.

The v2 timed operational rehearsal now provides a limited but real operating observation. Its locked return audit recorded 72 completed tasks across three opaque participant codes, with all 72 returned `(participant, packet, role)` combinations present in the restricted allocation, no duplicate participant-packet task, no technical interruption, and a 24.270-second P95 elapsed duration. The return is useful evidence that the neutral interface, fixed task queue, and independent-role workflow can be operated under the observed conditions. It is not a direct observation of formal review-label throughput, label validity, adjudication disagreement, or future semantic-review duration. These facts are sufficient to update the decision record with an operational evidence link, but they do not set an expected execution time.

## Critical readiness finding

The numerical freeze cannot yet be signed. First, the study has not allocated the 1,200 analyzable pairs among development, calibration, and confirmation roles. The primary Brier comparison occurs only once on the confirmation partition, whereas the 400-pair mechanism sample and the 800-pair deployment sample answer different questions. A total of 1,200 does not determine the confirmation sample size. A superficially attractive statement that “800 pairs are enough” would be a unit-of-analysis error if some of those pairs are needed for calibration, or if the mechanism sample is used for development rather than a representative confirmation estimate.

Second, neither the practical Brier increment nor the decision rule has a field-operational justification yet. A superiority rule is conceptually more aligned with the central claim than a noninferiority rule: the study asks whether automatic pair evidence adds useful information beyond descriptor similarity and independent image quality, not merely whether it causes no unacceptable harm. However, the size of a practically useful Brier improvement cannot be inferred from the historical v1 increment, which is exploratory, nor selected because one synthetic row produces a preferred power value. The future decision must connect the increment to an accepted prediction-quality or routing consequence before labels are visible.

Third, the current paired-loss variability and endpoint-dependence values are sensitivity assumptions, not measured v2 design parameters. The Task 02 result appropriately spans paired-loss standard deviations of 0.080 and 0.120 and image-variance fractions of 0.00 to 0.10. It demonstrates that the answer changes materially across assumptions. Selecting the optimistic corner to retain a convenient target would be confirmation bias; selecting the pessimistic corner without a plausibility argument would be equally arbitrary. A binding plan needs an explicitly justified conservative scenario, together with a graph-aware confirmation interval procedure to be frozen later in Workstream 05.

Finally, the timed rehearsal removes the previous absence of any observed interface completion and timing record, but it does not estimate the cognitive work of an independent identity or reviewability judgement. Its logs establish three distinct opaque codes; the project owner later attested that those codes represented three different people, although neither the logs nor that attestation establish reviewer reliability. Two durations were below one second and one exceeded one minute; all were within the predeclared maximum and must remain in the archived return. The current return auditor reports an upper order-statistic value for its even-sample median, whereas the conventional median is 9.388 seconds; this descriptive discrepancy does not change the pass gate or the P95. The later accepted reviewer-operation design uses the rehearsal only as interface evidence and deliberately assigns no expected semantic-review time, total-hour requirement, or calendar window.

## Decision implications

The historical decision at the time of this review was `not_ready_to_freeze`. Later pre-outcome decisions have now resolved the primary rule, four-stage allocation, conservative graph-aware planning specification, and reviewer-operation structure without converting workflow seconds into semantic-review estimates. The complete design is still not locked because the immutable sampling strata, official seed, zero-crossing manifests, and conflict-free reviewer assignment have not yet been created and audited.

## Required decision record before a binding simulation

| Decision domain | Required binding content | Current status |
| --- | --- | --- |
| Primary rule | Minimum practical Brier increment, direction, and superiority or noninferiority criterion | Accepted pre-outcome |
| Analytical allocation | Analyzable mechanism, development, calibration, and confirmation counts, with the estimand attached to each | Accepted pre-outcome |
| Dependence and precision | Final graph-aware interval method and justified planning values for paired-loss variability and endpoint dependence | Accepted pre-outcome |
| Reviewer operation | Two independent first-pass roles, conflict-free third-person adjudication, blinding, and actual-time logging | Accepted; actual pair assignment still required before packet release |
| Operational reporting | Report actual elapsed time, disagreement, adjudication, missingness, and technical failure without an estimated-time gate | Accepted |
| Sampling execution | Target, strata, reserve, official seed, and project-owner acceptance timestamp | Prohibited until every preceding row is complete |

The next authorized design task is the immutable sampling-strata rule. After its acceptance, the project may generate the official seed, actual zero-crossing image and pair manifests, and restricted reviewer assignment, then run the final outcome-free audits. Until those artifacts pass, no real outcome packet may be released.
