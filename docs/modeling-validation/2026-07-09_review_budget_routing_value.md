# Review-Budget Routing Value

Date: 2026-07-09

Status: `PASS`

This analysis asks whether PF-ERI changes the practical value of a fixed human review budget after a strong descriptor has already generated candidate pairs. The comparison is intentionally workflow-level: PF-ERI priority is compared with descriptor-similarity priority on the same CzechLynx reviewed pair pool, and human labels are used only after selection to audit reviewability, not to choose the queue. The endpoint is review burden and evidence hygiene, not identity accuracy.

At a budget of 100 reviewed pairs in the pooled table, PF-ERI priority selected a queue with not-ready/uncertain burden 0.060, compared with 0.090 for descriptor priority. The same comparison retained same-ID candidate coverage of 0.405 for PF-ERI priority and 0.500 for descriptor priority. At a budget of 200 pairs, PF-ERI priority had not-ready/uncertain burden 0.125, compared with 0.210 for descriptor priority.

Across pooled fixed-budget settings, PF-ERI priority reduced not-ready/uncertain burden in 4 of 7 budgets. This supports an applied evidence-value claim: PF-ERI can order a review queue so that a limited expert budget often encounters fewer uncertain or not-ready pairs. The tradeoff is explicit rather than hidden: at some budgets, descriptor priority retains more same-ID candidates, while PF-ERI priority admits more review-ready different-ID pairs that may be useful for clear exclusion decisions. This is not a claim that PF-ERI identifies individuals automatically; same-ID retention is reported only as a secondary candidate-coverage audit in the known-ID CzechLynx table.

The analysis remains bounded. False-candidate burden is treated as review burden, because a different-ID pair may still be review-ready if it is easy for a reviewer to reject. Bobcat identity performance remains blocked because Bobcat identity labels are not part of this validated endpoint. The figure accompanying this report visualizes the pooled burden and candidate-coverage tradeoff across budgets using colorblind-safe line encodings.

## Artifact Links

The fixed-budget comparison table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_fixed_budget_review_utility.csv`. The policy-delta table is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_fixed_budget_policy_delta.csv`. The publication-style SVG figure is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/figure_issue5_review_budget_utility.svg`. The audit file is `archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5/issue5_review_budget_value_audit.json`.
