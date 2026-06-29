# Documentation Map

Date: 2026-06-25

Docs are compact and English-only. Each phase keeps one core `README.md` unless an execution standard is still active.

## Read Order

1. `../README.md` - project overview and claim boundary.
2. `../PROJECT_RULES.md` - binding scientific and implementation rules.
3. `CURRENT_PROJECT_MAP.md` - current phase/layer map.
4. `phase16/README.md` - active Phase 16 strategy.
5. `phase16/phase16i_gap_rationale.md` - binding gap and claim-direction lock.
6. `phase16/phase16e_colab_batch_execution.md` - Phase 16E runner usage.
7. `phase16/phase16e_result_acceptance_criteria.md` - Phase 16E result gate.
8. `superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md` - compact active plan.
9. `phase15/README.md` - current evidence-routed review evidence.
10. `phase14/README.md` - data foundation.
11. `structure/csv_and_artifact_inventory.md` - core CSV/output map.

## Current Layering

### Active Strategy

- `phase16/`: current next-step strategy. Keeps PF-ERI modeling as the core and
  treats laterality, leakage pressure, strong-model benchmarks, augmentation,
  ecological context, and captive imagery as safeguards or extensions.
- `phase16/phase16i_gap_rationale.md`: binding rule that PF-ERI is a
  post-retrieval evidence reliability and review-routing layer, not a descriptor
  replacement or unsupported top-k ranking-improvement claim.
- `superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md`: active
  executable plan.
- `superpowers/plans/2026-06-29-phase17a-czechlynx-review-utility.md`: active
  review-utility validation plan for the locked Phase16I gap.

### Current Evidence

- `phase15/`: current model evidence: query-level CzechLynx benchmark,
  calibrated ranker validation, evidence-routed review policy, bobcat transfer
  stress test, and bobcat pair-audit package.

### Data Foundation

- `phase14/`: 2x2 wild/urban x high/low evidence dataset construction, detector
  first filtering, MegaDescriptor package, pair comparability, and
  descriptor-evidence conflict tables.

### Historical Foundation

- `phase6/`, `phase8/`, `phase9/`, `phase11/`, `phase12/`, `phase13/`: compact historical READMEs. Use for rationale only.

### Archive

- `archive/superseded_plans/`: older executable plans replaced by Phase 16.
- `archive/superseded_specs/`: older specs whose useful content has been
  absorbed into Phase 14/15/16.

## Rule For Conflicts

If documents disagree, use this priority:

```text
PROJECT_RULES.md
-> docs/CURRENT_PROJECT_MAP.md
-> docs/phase16/README.md
-> active Phase 16 plan
-> Phase 15 evidence docs
-> Phase 14 data foundation docs
-> historical/archive docs
```

Archived docs are thinking history, not active instructions.
