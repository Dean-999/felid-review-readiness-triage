# Phase17A CzechLynx Review-Utility Validation Plan

Date: 2026-06-29

## Objective

Validate PF-ERI as a post-retrieval review-utility layer on known-ID CzechLynx
pairs. The phase must not attempt to prove descriptor replacement or top-k
identity-ranking superiority.

## Confidence Loop

Current high-confidence strategy:

```text
descriptor candidate queue
-> PF-ERI evidence/risk features
-> leakage-excluded review-utility validation
-> endpoints: false-candidate burden, positive retention, review burden,
   abstention/risk coverage, conflict enrichment, and proxy review actions
```

Rejected strategy:

```text
optimize until PF-ERI beats descriptor-only top-k ranking
```

Reason rejected: Phase16H already showed no conservative descriptor-only top-k
improvement claim. Forcing that endpoint would create a claim vulnerability.

## Tasks

1. Build `scripts/build_phase17a_czechlynx_review_utility.py`.
2. Use Phase16H scored CzechLynx pairs as input.
3. Exclude `source_leakage_pressure_flag == True` by default.
4. Compare descriptor-only, quality-only, evidence-only,
   conflict-penalized-descriptor, and diagnostic PF-ERI policies.
5. Report:
   - fixed review-budget metrics;
   - fixed positive-retention metrics;
   - risk/abstention coverage metrics;
   - descriptor-evidence conflict enrichment;
   - proxy evidence-routed action distribution.
6. Add focused unit tests.
7. Run on real CzechLynx outputs.
8. Update docs to point to Phase17A.

## Verification

Run:

```text
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test*.py' -v
python scripts/build_phase17a_czechlynx_review_utility.py
```

Expected boundary:

```text
Review-utility validation only; no descriptor replacement, automatic identity
assignment, or Bobcat identity-accuracy claim.
```
