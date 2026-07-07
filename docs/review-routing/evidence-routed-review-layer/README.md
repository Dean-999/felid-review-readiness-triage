# Evidence-Routed Review Layer

This review-routing layer turns PF-ERI from image/pair diagnostics into a review-routing layer after strong descriptor retrieval.

Core question:

```text
After descriptor retrieval returns candidates, which pairs contain admissible identity evidence and what should a reviewer do?
```

Actions:

```text
accept_for_expert_review
review
defer
species_level_only
non_comparable
```

`accept_for_expert_review` is not automatic identity confirmation.

## Core Outputs

```text
outputs/review-routing/evidence-routed-review-layer/query_level_benchmark/
outputs/review-routing/evidence-routed-review-layer/hybrid_routing_policy/
outputs/review-routing/evidence-routed-review-layer/colab_ranker_package/
outputs/review-routing/evidence-routed-review-layer/calibrated_ranker_results/
outputs/review-routing/evidence-routed-review-layer/repeated_ranker_validation/
outputs/review-routing/evidence-routed-review-layer/evidence_routed_review_policy/
outputs/review-routing/evidence-routed-review-layer/wild_urban_transfer_stress/
outputs/review-routing/evidence-routed-review-layer/bobcat_pair_audit_package/
```

## Main Scripts

```text
scripts/build_legacy-code15_czechlynx_query_benchmark.py
scripts/build_legacy-code15_hybrid_routing_policy.py
scripts/build_legacy-code15c_repeated_ranker_validation.py
scripts/build_legacy-code15d_evidence_routed_review_policy.py
scripts/build_legacy-code15e_wild_urban_transfer_stress.py
scripts/package_legacy-code15f_bobcat_pair_audit.py
```

## Results

- Descriptor-only MegaDescriptor is strong.
- Hand-written gates are insufficient.
- Calibrated nonlinear rankers show signal, but top-k gains are modest.
- Repeated held-out CzechLynx query splits are validation evidence.
- The all-data action table is operational export, not new held-out validation.
- The transfer-stress slice applies policy to bobcat as review-readiness stress only.
- The bobcat pair-audit package contains a 250-pair bobcat manual audit set for pair comparability and action validation.

## Claims Allowed

- PF-ERI can support calibrated review/risk routing after descriptor retrieval.
- PF-ERI features add pair-level discrimination signal beyond descriptor-only
  features in held-out CzechLynx validation.
- Bobcat transfer shows review-readiness, ambiguity, defer, species-level-only, and non-comparability pressure.

## Claims Not Allowed

- No automatic identity assignment.
- No bobcat identity accuracy without verified labels.
- No claim that PF-ERI replaces MegaDescriptor.
- No claim that PF-ERI's main contribution is descriptor-only top-k ranking
  improvement unless later leakage-controlled held-out validation directly
  supports that exact claim.
- No broad Re-ID breakthrough claim from modest top-k gains.

## Current Role

This is the empirical review-routing evidence base. The safeguards layer adds dataset governance, candidate-pool expansion, model scoring, laterality controls, and stronger selection discipline around this review-routing core.
