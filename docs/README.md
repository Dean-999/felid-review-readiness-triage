# Documentation Map

Date: 2026-06-23

This directory is organized as a layered project record. The project has gone
through several plan iterations; older files are preserved for rationale but no
longer define the active direction.

## Read Order

1. `../README.md` - project overview and claim boundary.
2. `../PROJECT_RULES.md` - binding scientific and implementation rules.
3. `CURRENT_PROJECT_MAP.md` - current phase/layer map and active-vs-archive
   distinction.
4. `phase16/README.md` - current Phase 16 strategy entry point.
5. `superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md` -
   executable next-step plan.
6. `phase15/README.md` - current evidence-routed review layer and model outputs.
7. `phase14/phase14_output_structure_index.md` - Phase 14 2x2 data and output
   structure.
8. `phase14/phase14_implementation_status.md` - Phase 14 data-construction
   status and caveats.
9. `structure/csv_and_artifact_inventory.md` - core CSV/output map.
10. `archive/README.md` - archived plan/spec map.

## Current Layering

### Active Strategy

- `phase16/`: current next-step strategy. Keeps PF-ERI modeling as the core and
  treats laterality, leakage pressure, strong-model benchmarks, augmentation,
  ecological context, and captive imagery as safeguards or extensions.
- `superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md`: active
  executable plan.

### Current Evidence

- `phase15/`: current model evidence: query-level CzechLynx benchmark,
  calibrated ranker validation, evidence-routed review policy, bobcat transfer
  stress test, and bobcat pair-audit package.

### Data Foundation

- `phase14/`: 2x2 wild/urban x high/low evidence dataset construction, detector
  first filtering, MegaDescriptor package, pair comparability, and
  descriptor-evidence conflict tables.

### Historical Foundation

- `phase6/`, `phase8/`, `phase9/`, `phase11/`, `phase12/`, `phase13/`: useful
  evidence history and diagnostic reasoning. These explain why the project moved
  toward pair-level PF-ERI review routing and away from broad metric-learning
  claims.

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

Archived docs are evidence of thinking history, not active instructions.
