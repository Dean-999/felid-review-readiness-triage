# Review-Budget Routing

Status: `PASS`

This module turns the PF-ERI selective evidence router into fixed-budget
risk-constrained workflow optimization for review triage.

## Objective

maximize sum evidence_admission_score with selected_count<=B and mean predicted evidence_risk_score<=alpha

Selection uses predicted evidence risk only. Human labels are reserved for
post-selection empirical risk audits.

This is a predicted-risk budget optimizer, not a new finite-sample conformal
guarantee. The conformal thresholds and cluster bootstrap intervals are consumed
as calibration/uncertainty references.

## Uncertainty Reference

- Metric: `alpha_0_15_selective_risk`
- Point estimate: `0.07751937984496124`
- 95% cluster CI: `0.0362206585096886` to `0.13048020667122556`
- Status: `cluster_interval_reportable`

## Outputs

- CzechLynx risk/coverage table: `outputs/modeling-validation/review-budget-routing/czechlynx_budget_risk_coverage.csv`
- Bobcat allocation table: `outputs/modeling-validation/review-budget-routing/bobcat_budget_allocation.csv`
- Workflow recommendation: `outputs/modeling-validation/review-budget-routing/review_budget_routing_recommendations.md`

## Boundary

Review-budget allocation only; not identity accuracy or descriptor performance.
