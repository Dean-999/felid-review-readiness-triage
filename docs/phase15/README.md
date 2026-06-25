# Phase 15 Evidence-Routed Review Layer

Phase 15 turns PF-ERI from image/pair diagnostics into a review-routing layer after strong descriptor retrieval.

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
outputs/phase15/query_level_benchmark/
outputs/phase15/hybrid_routing_policy/
outputs/phase15/colab_ranker_package/
outputs/phase15/calibrated_ranker_results/
outputs/phase15/repeated_ranker_validation/
outputs/phase15/evidence_routed_review_policy/
outputs/phase15/wild_urban_transfer_stress/
outputs/phase15/bobcat_pair_audit_package/
```

## Main Scripts

```text
scripts/build_phase15_czechlynx_query_benchmark.py
scripts/build_phase15_hybrid_routing_policy.py
scripts/build_phase15c_repeated_ranker_validation.py
scripts/build_phase15d_evidence_routed_review_policy.py
scripts/build_phase15e_wild_urban_transfer_stress.py
scripts/package_phase15f_bobcat_pair_audit.py
```

## Results

- Descriptor-only MegaDescriptor is strong.
- Hand-written gates are insufficient.
- Calibrated nonlinear rankers show signal, but top-k gains are modest.
- Phase 15C repeated held-out CzechLynx query splits are validation evidence.
- Phase 15D all-data action table is operational export, not new held-out validation.
- Phase 15E transfers policy to bobcat as review-readiness stress only.
- Phase 15F packages a 250-pair bobcat manual audit set for pair comparability and action validation.

## Claims Allowed

- PF-ERI can support calibrated review/risk routing after descriptor retrieval.
- PF-ERI features add signal beyond descriptor-only ranking in held-out CzechLynx validation.
- Bobcat transfer shows review-readiness, ambiguity, defer, species-level-only, and non-comparability pressure.

## Claims Not Allowed

- No automatic identity assignment.
- No bobcat identity accuracy without verified labels.
- No claim that PF-ERI replaces MegaDescriptor.
- No broad Re-ID breakthrough claim from modest top-k gains.

## Current Role

Phase 15 is the current empirical evidence base. Phase 16 adds dataset governance, candidate-pool expansion, model scoring, laterality controls, and stronger selection discipline around this review-routing core.
