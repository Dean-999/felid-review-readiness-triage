# Review-Budget Routing Recommendations

## Practical Rule

Use PF-ERI route priority first, then evidence admission score. Use descriptor rank
only as a retrieval input or secondary tie-breaker, not as a review-readiness proxy.

## CzechLynx Budget 100 Comparison

- PF-ERI empirical risk: `0.06`
- PF-ERI evidence-admissible coverage: `0.3418181818181818`
- Descriptor-only empirical risk: `0.09`
- Descriptor-only evidence-admissible coverage: `0.33090909090909093`

## Bobcat Boundary

At budget 100, Bobcat selected pairs are `100`,
with `64` accept-review routes. Empirical risk
is not estimated because Bobcat lacks review labels and same/different identity labels
in this workflow.
