# Review-Budget Routing Recommendations

## Practical Rule

For a target risk alpha, select the feasible PF-ERI prefix that maximizes
the sum of evidence admission scores under the budget. Descriptor rank remains
a retrieval order baseline, not a review-readiness proxy.

## CzechLynx Budget 100 Comparison

- PF-ERI alpha: `0.15`
- PF-ERI selected count: `100`
- PF-ERI mean predicted risk: `0.08859433178833984`
- PF-ERI empirical risk: `0.06`
- PF-ERI evidence-admissible coverage: `0.3418181818181818`
- Descriptor-only empirical risk: `0.09`
- Descriptor-only evidence-admissible coverage: `0.33090909090909093`

## Bobcat Boundary

At budget 100, Bobcat selected pairs are `75`,
with `64` accept-review routes. Empirical risk
is not estimated because Bobcat lacks review labels and same/different identity labels
in this workflow.
