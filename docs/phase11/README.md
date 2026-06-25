# Phase 11 Pair-Level Learning Diagnostics

Phase 11 tested pair-level PF-ERI reliability ideas and metric-learning scaffolds.

Current role: diagnostic foundation, not active training endpoint.

## What It Contributed

- Pair-level reliability math.
- Positive-pair weighting and unreliable hard-negative concepts.
- Early evidence that training changes must be controlled carefully.
- Motivation to keep fixed descriptor baselines and random/quality controls.

## Boundary

- Metric learning remains optional and diagnostic.
- No PF-ERI metric-learning claim unless held-out identity-split controls beat random and quality-matched baselines.

## Related Scripts

```text
scripts/build_phase11_pair_level_pf_eri_table.py
scripts/build_phase11c_split_level_diagnostics.py
scripts/audit_phase11_pair_level_pf_eri_table.py
scripts/audit_phase11c_split_level_diagnostics.py
```
