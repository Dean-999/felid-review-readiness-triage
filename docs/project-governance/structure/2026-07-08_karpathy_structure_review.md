# Karpathy Structure Review

Date: 2026-07-08

Status: `STRUCTURE_REVIEW_COMPLETE_WITH_SURGICAL_FIXES`

## Purpose

This review checks the repository as a working scientific codebase: what each
folder says, whether the navigation matches the current PF-ERI claim, where the
project is over-split, and which names still make the CodeGraph/tooling story
harder than it needs to be.

The review follows three rules:

- change only navigation and contract files that can mislead current work;
- do not move images, CSVs, JSON manifests, review labels, or provenance;
- treat CodeGraph as a code-navigation tool, not a scientific source of truth.

## Current Project Shape

The active project is no longer a phase ladder. The current shape is:

```text
final photo freeze
-> pair construction
-> pair-level PF-ERI evidence features
-> known-ID evidence-sufficiency validation
-> calibrated selective evidence admission
-> review-budget utility and robustness gates
-> paper-ready claim package
```

The scientific claim remains unchanged:

```text
PF-ERI is a post-retrieval pair-level evidence governance and reviewability
layer after strong descriptor retrieval.
```

It is not a new descriptor, not automatic individual identity assignment, and
not a Bobcat identity-accuracy claim.

## Folder Audit

| Folder | What it says now | Current role | Review |
| --- | --- | --- | --- |
| `README.md` | Project overview and final modeling freeze. | Primary entry. | Keep. It states the claim boundary and points to the final freeze note. |
| `PROJECT_RULES.md` | Binding claim rules. | Scientific contract. | Keep. This is the source of truth for allowed/blocked claims. |
| `AGENTS.md` | CodeGraph and project-specific tool guardrails. | Agent/tool contract. | Keep. It prevents CodeGraph from being used as data truth. |
| `CLAUDE.md` | Session/memory bridge. | Tooling support. | Keep unless the `.claude`/sessions setup is removed later. |
| `docs/` | Tracked scientific interpretation and governance. | Human-readable project brain. | Keep. Current docs are content-based; old phase vocabulary should remain only as provenance. |
| `docs/project-governance/` | Rules, maps, logs, structure plans. | Navigation and decisions. | Keep. This is the right home for structure contracts. |
| `docs/modeling-validation/` | Final modeling and pair-level validation reports. | Active scientific evidence. | Keep. This is the current algorithm/modeling documentation layer. |
| `docs/photo-freeze/` | Photo-entry and freeze rules. | Freeze provenance. | Keep. It protects final image-entry assumptions. |
| `docs/data-foundation/` | Dataset foundation records. | Provenance and data construction. | Keep. Not the current modeling entry point. |
| `docs/pair-evidence/` | Pair evidence rationale and research questions. | Rationale. | Keep, but avoid adding new current work here if it belongs in modeling validation. |
| `docs/review-routing/` | Earlier evidence-routed review layer. | Empirical predecessor. | Keep as evidence history. |
| `docs/candidate-reservoirs/` | Candidate pools and source-selection experiments. | Non-final candidate provenance. | Keep, with clear "not final freeze" language. |
| `docs/archive/` | Superseded plans and historical phases. | Historical record. | Keep. Do not clean it by deletion. |
| `data/frozen/pferi_v2/` | Current image-bearing freeze. | Primary data entry for modeling. | Keep as the only current image-entry root. |
| `archive/pferi_v1/outputs/modeling-validation/` | Current modeling outputs and validation packages. | Active result layer. | Keep. This is where algorithm/modeling outputs belong. |
| `archive/pferi_v1/outputs/photo-freeze/` | Frozen package provenance. | Freeze support. | Keep, but do not treat as a second active entry over `final_freeze/`. |
| `archive/pferi_v1/outputs/photo-selection/` | Selection gates, reviews, rescue queues. | Provenance and candidate selection history. | Keep. It is over-split but should not be moved without an index. |
| `archive/pferi_v1/outputs/project-governance/` | Generated structure and governance audits. | Current generated governance output. | Keep. This should replace the old `outputs/project_structure/`. |
| `outputs/project_structure/` | Old generated CodeGraph contract root. | Compatibility residue. | Do not write new outputs here. Archive or delete only after confirming no consumer references it. |
| `archive/pferi_v1/outputs/review-routing/` | Earlier review-routing outputs. | Pre-final empirical evidence. | Keep as provenance. |
| `archive/pferi_v1/outputs/candidate-reservoirs/` | Raw candidate reservoirs. | Non-final candidates. | Keep out of claim gates. |
| `data/` | Local manifests, labels, raw/external data. | Local data store. | Keep out of Git assumptions; use only with direct audits. |
| `scripts/` | Active builders plus historical phase scripts. | Executable layer. | Keep, but navigation should favor content-based current builders. |
| `scripts/prototypes/` | Throwaway and selection-policy prototypes. | Reproducibility/provenance. | Keep until each prototype is either archived or replaced by a documented builder. |
| `scripts/legacy/` | Older utilities and audits. | Historical reproduction. | Keep, but do not use for current state unless a report names it. |
| `tests/` | Regression tests. | Verification. | Keep. Current Phase18/modeling tests remain the fastest safety check. |
| `colab/` | Cloud/runtime packaging. | External compute support. | Keep. Archive metric-learning branches remain diagnostic history. |
| `models/` | Model artifacts, mostly candidate-reservoir models. | Support artifacts. | Keep; not a claim source. |
| `paper/` | Paper/manuscript workspace. | Reporting. | Keep; should consume frozen outputs, not regenerate science. |
| `sources/` | Literature/source cache. | Citation support. | Keep. It is evidence support, not model output. |
| `sessions/` and `.claude/` | Agent/session tooling. | Workflow support. | Keep unless the tooling system is removed. |

## CodeGraph Tooling Review

CodeGraph is useful for:

- locating scripts;
- reading relevant functions with blast radius;
- tracing implementation relationships before edits.

CodeGraph is not reliable for:

- final row counts;
- photo validity;
- human review status;
- phase completion;
- scientific claim boundaries.

The contract now points to the current content-based navigation layer:

```text
docs/project-governance/structure/current_pipeline_manifest.md
archive/pferi_v1/outputs/project-governance/project-structure/codegraph_contract/
```

The old path `outputs/project_structure/` should no longer receive new
generated contract output.

## Over-Splitting

The project has four real over-splitting patterns.

| Pattern | Example | Why it is risky | Recommended treatment |
| --- | --- | --- | --- |
| Repeated review-packet folders | `streamlit-full-queue-review`, `streamlit-full-queue-review-100`, descriptor-controlled, identity-balanced variants | Readers can confuse packet variants with independent evidence tiers. | Keep outputs, but add a single index under `archive/pferi_v1/outputs/modeling-validation/manual-review-audits/` if more review rounds are added. |
| Photo-selection rescue/gate folders | many `inat-*`, `multisource-*`, `bobcat-*` gates under `archive/pferi_v1/outputs/photo-selection/photo-entry-gates/` | Candidate attempts can look like final freeze alternatives. | Keep as provenance; never link them before `data/frozen/pferi_v2/` in active docs. |
| Project-structure roots | `outputs/project_structure/` and `archive/pferi_v1/outputs/project-governance/project-structure/` | Two roots imply two current contracts. | New output goes only to `archive/pferi_v1/outputs/project-governance/project-structure/`; old root can be archived after consumer check. |
| Phase and content names mixed | `phase18`, `legacy-code18`, `pair-level-validation` | Same scientific layer has three names. | Use content names in active prose; keep phase/legacy names only for old artifact identity. |

## Naming Issues

High priority:

- `outputs/project_structure/` is stale. New scripts now write to
  `archive/pferi_v1/outputs/project-governance/project-structure/`.
- Active docs must not point to `docs/structure/...`; the current path is
  `docs/project-governance/structure/...`.
- Active docs must not point to `docs/legacy-code18/README.md`; the current
  pair-level validation doc is
  `docs/modeling-validation/pair-level-validation/README.md`.

Medium priority:

- `scripts/README.md` still contains many phase-script sections. That is fine
  as a catalog, but the first screen must name the current content-based
  builders first.
- `archive/pferi_v1/outputs/modeling-validation/pair-level-validation/` contains many completed
  review-packet variants. This is acceptable as result provenance, but future
  packets should be indexed rather than adding another sibling for every UI
  change.
- `archive/pferi_v1/outputs/photo-selection/photo-entry-gates/` contains many candidate attempts.
  This is scientifically useful but visually noisy. Future cleanup should add a
  compact index that marks `final`, `candidate`, `failed`, and `audit-only`.

Low priority:

- Historical `phase*` names under
  `archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/` are acceptable
  because they are inside a historical-validation folder.
- `scripts/prototypes/` includes prototypes that generated important freeze
  artifacts. Do not delete them until the durable outputs and docs are
  sufficient to reproduce the decision.

## Changes Made In This Review

- Updated `scripts/check_codegraph_project_contract.py` to use
  `archive/pferi_v1/outputs/project-governance/project-structure/codegraph_contract/`.
- Updated the CodeGraph contract required paths to current docs and current
  modeling bootstrap script.
- Updated `scripts/build_project_artifact_consolidation_index.py` to write into
  `archive/pferi_v1/outputs/project-governance/project-structure/artifact_consolidation_index/`.
- Updated that consolidation script to scan current content-based output roots
  instead of missing old phase roots.
- Updated active navigation references in:
  - `docs/project-governance/structure/current_pipeline_manifest.md`;
  - `docs/project-governance/structure/2026-07-07_codegraph_project_structure_map.md`;
  - `docs/project-governance/structure/content_based_reorganization_plan.md`;
  - `scripts/README.md`.
- Added `scripts/build_project_cleanup_indexes.py` as the merged navigation
  entry for repeated review-packet and photo-selection output directories.

## What Not To Do Now

- Do not move image folders.
- Do not delete historical CSV/JSON/manifests.
- Do not merge `archive/pferi_v1/outputs/modeling-validation/pair-level-validation/` by hand.
- Do not remove phase-named historical folders that still explain provenance.
- Do not let CodeGraph output override `PROJECT_RULES.md`, final freeze
  manifests, or human-review labels.

## Recommended Next Cleanup

1. Run the governance scripts after any future structure migration:

```bash
python3 scripts/check_codegraph_project_contract.py
python3 scripts/build_project_artifact_consolidation_index.py
python3 scripts/build_project_cleanup_indexes.py
```

2. Use the generated review-packet index if another human-review batch is
created:

```text
archive/pferi_v1/outputs/modeling-validation/manual-review-audits/review_packet_index.csv
archive/pferi_v1/outputs/project-governance/project-structure/cleanup_indexes/review_packet_index.csv
```

3. Use the generated photo-selection gate index before deleting or moving any
selection attempts:

```text
archive/pferi_v1/outputs/project-governance/project-structure/cleanup_indexes/photo_selection_gate_index.csv
```

4. After a consumer-reference search, archive the stale
`outputs/project_structure/` directory or leave it with a README that marks it
as superseded.

## Bottom Line

The codebase is scientifically coherent, but the names lagged behind the
project. The active story is now content-based and modeling-centered; phase
labels are artifact provenance. The correct CodeGraph framing is:

```text
Use CodeGraph to find code.
Use project rules, manifests, audits, and review outputs to decide science.
```
