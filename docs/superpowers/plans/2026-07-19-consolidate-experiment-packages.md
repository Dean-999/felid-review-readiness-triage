# Experiment Package Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce repeated Colab/Kaggle packages, superseded execution versions, exact-copy manifests, and duplicated explanation documents while retaining scientific outputs and a reproducible iteration history.

**Architecture:** One algorithm family owns one canonical runner, package builder, execution README, and current ZIP. Historical failures and platform changes are recorded as dated decisions instead of copied implementations. Scientific outputs remain immutable unless two files are byte-identical or an older manifest is a proven strict subset of its replacement.

**Tech Stack:** Python 3.12, unittest, ZIP/SHA-256 validation, Markdown, Git.

## Global Constraints

- Preserve every unique scientific result, review return, source archive, and annotation batch.
- Never treat an unimported CLI entry point as dead code without checking documentation and tests.
- Do not modify frozen v2 scientific matcher logic while consolidating execution packaging.
- Keep Kaggle/Colab failure history in the canonical workstream document.
- Existing uncommitted full-frame engineering work is authoritative input and must not be overwritten.

---

### Task 1: Canonical full-frame execution package

**Files:**
- Modify: `scripts/build_v2_full_frame_local_match_control_package.py`
- Delete: `scripts/build_v2_full_frame_fresh_run_control_package.py`
- Modify: `gpu/kaggle_v2_local_matcher_v2/README.md`
- Delete: `gpu/kaggle_v2_local_matcher_v2/README_FULL_FRAME_KAGGLE.md`
- Delete: `gpu/kaggle_v2_local_matcher_v2/README_FULL_FRAME_COLAB.md`
- Modify: `gpu/kaggle_v2_local_matcher_v2/build_final_export.py`
- Modify: `tests/test_full_frame_execution_engineering.py`

**Interfaces:**
- Consumes: the frozen 30-shard inventory and existing full-frame execution modules.
- Produces: one deterministic `PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip` with embedded audit, checksums, and optional test summary.

- [x] Merge deterministic ZIP writing, 30-shard/28,295-pair validation, embedded audit, and checksums into the canonical builder.
- [x] Point all package documentation and export allowlists at `README.md`.
- [x] Add package-builder tests for canonical naming, inventory enforcement, checksums, and member allowlisting.
- [x] Run `python3.12 -m unittest discover -s tests -p 'test_full_frame_execution_engineering.py' -v`; expect all tests to pass.
- [x] Build the canonical ZIP from the real shard inventory and verify `ZipFile.testzip()` and embedded checksums.
- [x] Remove the two superseded Colab ZIPs and replace the old canonical ZIP with the validated package.

### Task 2: Consolidate full-frame history documents

**Files:**
- Modify: `docs/project-governance/workstreams/04_dual_sample_confirmation/05_colab_full_frame_execution_engineering_audit.md`
- Delete: `docs/project-governance/workstreams/04_dual_sample_confirmation/06_colab_continuation_after_kaggle_audit.md`
- Modify: `docs/project-governance/workstreams/04_dual_sample_confirmation/README.md`
- Delete: `docs/superpowers/plans/2026-07-18-pferi-full-frame-colab-engineering-layer.md`

**Interfaces:**
- Consumes: the Kaggle failure, attempted continuation, and accepted fresh-run engineering evidence.
- Produces: one current audit with an explicit supersession timeline and one workstream pointer.

- [x] Rewrite the audit around the accepted fresh 30-shard run while retaining the failed/abandoned version history.
- [x] Remove obsolete continuation commands, hashes, paths, and duplicated implementation prose.
- [x] Search the repository for deleted document/package names; expect no live references outside cleanup/relocation history.

### Task 3: Remove proven duplicate and superseded artifacts

**Files:**
- Delete: `outputs/pferi_v2/fresh_descriptor_runs/megadescriptor_l_384/embedding_manifest.csv`
- Delete: exact-copy Phase 14/15/16 package members identified by SHA-256 inventory.
- Delete: exact-copy v2 work manifests while retaining the canonical package manifest.
- Delete: `scripts/build_final_local_match_package_v2.py`
- Modify: `scripts/README.md`
- Modify: `docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`

**Interfaces:**
- Consumes: byte hashes, column-subset checks, and prior package-family inventory.
- Produces: one retained copy per identical data object and a documented replacement path.

- [x] Recompute hashes immediately before each deletion and abort on mismatch.
- [x] Record every removed path, retained canonical path, hash, size, and rationale in the cleanup manifest and supersession document.
- [x] Verify the v2 descriptor manifest replacement has identical ordered image IDs before deleting the old subset.
- [x] Verify no active script or document names the removed pilot packager outside historical manifests.

### Task 4: Separate remaining v1 Phase 18–19 activity

**Files:**
- Modify: `scripts/README.md`
- Modify: `docs/project-governance/structure/current_pipeline_manifest.md`
- Modify: `docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`

**Interfaces:**
- Consumes: the existing v1 reproducibility archive and current dirty-worktree boundary.
- Produces: an explicit archive manifest for Phase 18–19 without mixing those scripts into v2 routing.

- [x] Inventory Phase 18–19 source/tests and their Git status.
- [x] Move only clean, tracked historical files with preserved source hashes; no modified/untracked Phase 18–19 source was encountered.
- [x] Run archive-boundary tests and the full project test suite.

### Task 5: Final verification and cleanup accounting

**Files:**
- Modify: `docs/superpowers/plans/2026-07-19-consolidate-experiment-packages.md`

**Interfaces:**
- Consumes: all preceding changes.
- Produces: checked task boxes, exact reclaimed-byte count, and reproducible verification commands.

- [x] Run Python compile checks for changed Python files.
- [x] Run the targeted full-frame, archive, cleanup-safety, and descriptor-contract tests.
- [x] Run the full test suite and `git diff --check`.
- [x] Record retained/deleted artifact hashes and reclaimed bytes below this plan.

## Execution Record

This section is updated only from command output generated during execution.

- Canonical control ZIP: 43 members, 30 shards, 28,295 pairs, SHA-256
  `362c5bb0d180ee3734d1fdb8d75750d54c19eb78a6e37c004bee94c50363f603`.
  `ZipFile.testzip()` and every embedded `CHECKSUMS.sha256` entry passed.
- Artifact cleanup: 78 non-cache duplicate/superseded files, 209,219,704 bytes
  removed. The replacement ZIP plus external audit occupy 1,022,380 bytes, for
  a net artifact reduction of 208,197,324 bytes.
- Rebuildable metadata cleanup: 570 cache/metadata files, 7,752,879 bytes.
- Total physical removal during the run: 648 files and 216,972,583 bytes;
  after adding the canonical ZIP/audit, net workspace reduction was 215,950,203
  bytes.
- V1 separation: 48 Phase 18–19 scripts and 2 coupled tests moved to
  `archive/pferi_v1/reproducibility/`. The 50 appended archive records passed
  source/destination SHA-256 comparison; a follow-up dry run selected zero files.
- Targeted verification: cleanup safety 4/4, archive boundary 2/2, full-frame
  engineering 31/31.
- Full active test suite: 295 passed, 3 skipped.
- `git diff --check`: PASS.
