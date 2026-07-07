# Documentation Map

Date: 2026-07-07

Docs are compact and English-only. The primary navigation is content-based, not
phase-number based. Historical phase wording may remain inside archived
scientific records where it is part of provenance, but active navigation should
not depend on `phase*` directories or alias-style compatibility paths.

## Read Order

1. `../README.md` - project overview and claim boundary.
2. `../PROJECT_RULES.md` - binding scientific and implementation rules.
3. `CURRENT_PROJECT_MAP.md` - current phase/layer map.
4. `project-governance/structure/content_based_reorganization_plan.md` -
   content-based project map.
5. `project-governance/structure/content_directory_migration_map.csv` -
   old-path to new-path mapping.
6. `project-governance/structure/current_pipeline_manifest.md` - current
   executable chain.
7. `project-governance/safeguards-and-claim-lock/legacy-code16i_gap_rationale.md` - binding gap and claim-direction lock.
8. `photo-freeze/review-utility-and-photo-entry/README.md` - active review-utility validation layer.
9. `photo-freeze/review-utility-and-photo-entry/czechlynx_high3000_strict_audit.md` - CzechLynx strict 3,000 final-ready audit.
10. `bobcat_photo_selection.md` - Bobcat strict final 3,000 selection record.
11. `project-governance/structure/2026-07-01_legacy-code17_strict3000_modeling_freeze.md` - frozen local modeling package.
12. `project-governance/structure/2026-07-01_legacy-code18_gap_research_and_plan.md` - pair-level validation gap research and modeling plan.
13. `modeling-validation/pair-level-validation/README.md` - current algorithm-entry and pair-level modeling layer.
14. `project-governance/safeguards-and-claim-lock/README.md` - safeguards strategy and handoff history.
15. `project-governance/logs/daily_work_log.md` - daily work and direction-change log.
16. `review-routing/evidence-routed-review-layer/README.md` - evidence-routed review evidence.
17. `data-foundation/wild-urban-evidence-foundation/README.md` - data foundation.
18. `project-governance/structure/csv_and_artifact_inventory.md` - core CSV/output map.

## Current Layering

### Active Strategy

- `project-governance/safeguards-and-claim-lock/`: current next-step strategy. Keeps PF-ERI modeling as the core and
  treats laterality, leakage pressure, strong-model benchmarks, augmentation,
  ecological context, and captive imagery as safeguards or extensions.
- `project-governance/safeguards-and-claim-lock/legacy-code16i_gap_rationale.md`: binding rule that PF-ERI is a
  post-retrieval evidence reliability and review-routing layer, not a descriptor
  replacement or unsupported top-k ranking-improvement claim.
- `photo-freeze/review-utility-and-photo-entry/README.md`: first-class entry point for the locked-gap
  review-utility validation layer.
- `photo-freeze/review-utility-and-photo-entry/czechlynx_high3000_strict_audit.md`: strict CzechLynx 3,000 audit,
  supplement, augmentation, and CodeGraph boundary record.
- `bobcat_photo_selection.md`: strict Bobcat final 3,000 selection and manual
  clarity-review record.
- `project-governance/structure/current_pipeline_manifest.md`: current script, output, test, and
  claim-boundary manifest.
- `project-governance/structure/2026-07-01_legacy-code17_strict3000_modeling_freeze.md`: local frozen
  Bobcat/CzechLynx 3,000 x 2 modeling package record.
- `project-governance/structure/2026-07-01_legacy-code18_gap_research_and_plan.md`: pair-level validation plan after
  gap research, including upgraded baseline requirements.
- `project-governance/structure/2026-07-01_project_triage_and_legacy-code18_execution_issues.md`:
  CodeGraph contract, non-destructive safeguards/photo-entry artifact consolidation, and
  pair-level validation vertical slices.
- `modeling-validation/pair-level-validation/README.md`: current algorithm-entry layer, starting from the frozen
  strict 3,000 x 2 image package.
- `project-governance/executable-plans/plans/2026-06-23-legacy-code16-balanced-pf-eri-strategy.md`: active
  executable plan.
- `project-governance/executable-plans/plans/2026-06-29-legacy-code17a-czechlynx-review-utility.md`: active
  review-utility validation plan for the locked claim-lock gap.

### Current Evidence

- `review-routing/evidence-routed-review-layer/`: current model evidence: query-level CzechLynx benchmark,
  calibrated ranker validation, evidence-routed review policy, bobcat transfer
  stress test, and bobcat pair-audit package.

### Data Foundation

- `data-foundation/wild-urban-evidence-foundation/`: 2x2 wild/urban x high/low evidence dataset construction, detector
  first filtering, MegaDescriptor package, pair comparability, and
  descriptor-evidence conflict tables.

### Historical Foundation

- `archive/historical-phases/`, `pair-evidence/`, and `modeling-validation/`
  contain compact historical READMEs. Use for rationale only.

### Placeholder Directories

Some leaf directories intentionally contain only a `README.md`. They are kept
only when that README is the compact entry point for a content area, such as
human review, final reports, historical rationale, or a small final-freeze
exception. Do not create new one-off task reports for routine cleanup or
operational checks; fold durable rules and navigation notes into the nearest
parent README or `PROJECT_RULES.md`.

### Archive

- `archive/superseded_plans/`: older executable plans replaced by the safeguards layer.
- `archive/superseded_specs/`: older specs whose useful content has been
  absorbed into data-foundation, review-routing, or safeguards layers.

### Reserved Content Areas

Final manuscript-ready reports and human-review protocols do not need empty
placeholder folders. When those materials exist, place them under the relevant
content area and link them from this README, `CURRENT_PROJECT_MAP.md`, or the
nearest active validation README.

## Rule For Conflicts

If documents disagree, use this priority:

```text
PROJECT_RULES.md
-> docs/CURRENT_PROJECT_MAP.md
-> docs/project-governance/structure/current_pipeline_manifest.md
-> docs/modeling-validation/pair-level-validation/README.md
-> docs/photo-freeze/review-utility-and-photo-entry/README.md
-> docs/project-governance/safeguards-and-claim-lock/README.md
-> active safeguards/photo-entry plans
-> review-routing evidence docs
-> data-foundation docs
-> historical/archive docs
```

Archived docs are thinking history, not active instructions.

## CodeGraph Rule

CodeGraph is installed at the repository root and is useful for locating code,
but broad queries can surface old `scripts/legacy/` and prototype files because
the project has a long history with repeated scientific vocabulary. For current
state, start from `project-governance/structure/current_pipeline_manifest.md`
and use exact script paths when querying CodeGraph.
