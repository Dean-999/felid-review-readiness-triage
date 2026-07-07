# CodeGraph Root And Cleanup Triage

Date: 2026-07-01

Scope: CodeGraph installation state, repository naming, content consolidation,
and documentation pruning risk.

## Executive Finding

CodeGraph is installed in the project root and the index is current. The problem
is not installation. The problem is retrieval noise caused by a large historical
code surface with repeated CzechLynx/Bobcat/PF-ERI vocabulary.

Status check:

```text
project root: /Users/dshen/Desktop/scientific project/felid-review-readiness-triage
.codegraph/: present
codegraph CLI: /opt/homebrew/bin/codegraph
index status: up to date
indexed files: 369
nodes: 7,529
edges: 18,409
languages: python 286, yaml 67, javascript 16
```

## What Went Wrong

Broad CodeGraph queries for current CzechLynx/Bobcat work can return a mixture
of:

- current legacy-code17 scripts;
- `scripts/prototypes/` throwaway scripts;
- `scripts/legacy/` CzechLynx Phase6/8/old-manifest scripts;
- archived Colab metric-learning files.

Empirical failure:

```text
Query: prototype_czechlynx_strict3000_clarity_augmentation exact current CzechLynx final confirmed manifest
Result: CodeGraph returned legacy CzechLynx manifest scripts and legacy-code14 manifest code before the current augmentation script.
```

Exact path lookup still works:

```text
codegraph node scripts/prototypes/prototype_czechlynx_strict3000_clarity_augmentation.py
```

Therefore the issue is retrieval ranking and repository noise, not missing
installation.

## Triage Matrix

| ID | Category | State | Finding | Action |
| --- | --- | --- | --- | --- |
| CG-1 | bug | ready-for-agent | Broad CodeGraph queries can route current CzechLynx/Bobcat decisions into legacy scripts. | Use exact paths from `docs/structure/current_pipeline_manifest.md`; never use CodeGraph as data-state authority. |
| CG-2 | enhancement | ready-for-agent | Current pipeline manifest was behind the latest legacy-code17 image-entry state. | Updated it to include Bobcat final 3,000 and CzechLynx strict final-ready manifest. |
| DOC-1 | enhancement | ready-for-agent | `docs/README.md` did not put CzechLynx strict 3,000 and Bobcat final 3,000 high enough in read order. | Updated read order and CodeGraph usage note. |
| DOC-2 | enhancement | ready-for-agent | `scripts/README.md` under-described legacy-code17k/N/O and CzechLynx strict prototypes. | Added legacy-code17 image-entry and CzechLynx final-ready sections. |
| DOC-3 | enhancement | ready-for-human | `docs/logs/daily_work_log.md` is useful but too long for first-pass navigation. | Keep it as audit log; do not prune unless a separate monthly index is created. |
| CLEAN-1 | enhancement | ready-for-human | `scripts/legacy/` has 113 Python scripts and `colab/archive_metric_learning/` is indexed by CodeGraph. | Preserve for reproducibility; consider CodeGraph-query discipline first, physical moves only after import/reference audit. |
| CLEAN-2 | enhancement | ready-for-agent | `.DS_Store` files exist locally. | Safe to remove locally with a non-destructive cleanup command, but they are already ignored. |
| CLEAN-3 | enhancement | ready-for-human | Some prototype scripts generated durable final manifests but still live under `scripts/prototypes/`. | Do not rename now; after freeze, promote reusable logic into production scripts or archive the prototype with notes. |

## Naming And Structure Findings

Good:

- phase-prefixed scripts make chronology auditable;
- `scripts/legacy/` correctly marks many older files as historical;
- `docs/CURRENT_PROJECT_MAP.md`, `PROJECT_RULES.md`, and
  `docs/structure/current_pipeline_manifest.md` are the right authority layer.

Needs tightening:

- current legacy-code17 work is split across `outputs/legacy-code17/`,
  `outputs/bobcat_photo_selection/`, and `outputs/czechlynx/legacy-code17_*`;
- final-entry prototypes are scientifically important but named as prototypes;
- CodeGraph indexes historical code because it is real Python/YAML code, even
  when scientifically inactive.

## Merge / Prune Recommendations

Do now:

1. Keep `PROJECT_RULES.md`, `docs/CURRENT_PROJECT_MAP.md`, and
   `docs/structure/current_pipeline_manifest.md` synchronized after every
   direction change.
2. Use `docs/legacy-code17/czechlynx_high3000_strict_audit.md` as the CzechLynx strict
   3,000 record.
3. Use `docs/bobcat_photo_selection.md` as the Bobcat strict final 3,000 record.
4. Use exact CodeGraph file queries from the manifest, not broad scientific
   natural-language queries, when editing current scripts.

Do later, after final freeze:

1. Promote the durable CzechLynx/Bobcat final-entry prototype logic into
   production-named scripts, or archive the prototype shell and keep only the
   manifest/audit docs.
2. Create a short monthly index for `docs/logs/daily_work_log.md` instead of
   deleting log detail.
3. Review whether `scripts/legacy/` and `colab/archive_metric_learning/` should
   be excluded from CodeGraph by configuration if CodeGraph later supports
   project-specific excludes. Do not solve this with deletion.

Do not do:

1. Do not delete `scripts/legacy/` to improve search results; it is
   reproducibility evidence.
2. Do not move final manifests out of `outputs/` until a freeze/export package
   is explicitly created.
3. Do not use CodeGraph output to decide photo validity, final counts, image
   clarity, or phase completion.

## Current Rule

```text
CodeGraph can answer: where is the code?
The artifact layer answers: what is scientifically true?
The project docs answer: what is current?
```
