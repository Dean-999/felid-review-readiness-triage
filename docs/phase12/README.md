# Phase 12 Pairwise Evidence Learning Plan

Phase 12 consolidated RQ1-RQ4 around pairwise evidence reliability.

Current role: research-question foundation.

## Research Questions

- RQ1: Can PF-ERI predict unreliable candidate edges in known-ID CzechLynx?
- RQ2: Do descriptor-evidence conflicts explain false or uncertain candidates?
- RQ3: Can PF-ERI improve risk-coverage tradeoffs over descriptor-only, random, and quality-only controls?
- RQ4: Can PF-ERI-conditioned weighting support representation learning without damaging strong descriptor geometry?

## What It Contributed

- Pair/candidate analysis table design.
- Descriptor-evidence conflict formalization.
- Confidence and literature grounding.
- Rule that weak results should trigger model diagnosis before claim downgrade.

## Boundary

- RQ4 training is optional and must pass strict controls.
- Pair-level admissibility and review routing are stronger current endpoints than broad metric-learning claims.

## Related Scripts

```text
scripts/build_phase12_pair_candidate_analysis_table.py
scripts/build_phase12_rq1_rq3_evidence_analysis.py
scripts/build_phase12c_confidence_evidence.py
scripts/build_phase12d_failure_diagnosis_and_policy_revision.py
```
