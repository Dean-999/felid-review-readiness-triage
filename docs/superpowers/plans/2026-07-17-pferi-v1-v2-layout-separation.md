# PF-ERI v1/v2 Layout Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Physically separate PF-ERI v1 exploratory evidence, PF-ERI v2 Workbook04 results, frozen v2 inputs, reproducible work packages, and transfer archives without losing scientific provenance.

**Architecture:** `outputs/` will contain only current PF-ERI v2 generated results. Immutable v2 photo inputs move to `data/frozen/pferi_v2/`; historical v1 output bytes move unchanged to `archive/pferi_v1/outputs/`; reconstructable execution packages move to `work/pferi_v2/`; transfer ZIPs move to `artifacts/transfers/pferi_v2/`. A dry-run-first migration command records old/new paths, sizes, and SHA-256 values, while a separate deduplication manifest allows work-package images to be reconstructed from the frozen canonical image store.

**Tech Stack:** Python 3.12 standard library, `unittest`/`pytest`, CSV/JSON manifests, SHA-256, existing PF-ERI validation scripts.

## Global Constraints

- Preserve the current dirty worktree; do not reset, discard, or overwrite unrelated user changes.
- PF-ERI v1 remains `v1_exploratory_not_confirmatory` and cannot become a v2 input.
- Do not classify files by a bare `_v1` suffix; `pferi_v2_*_contract_v1` is a v2 artifact.
- Preserve historical and frozen scientific file bytes; update active source/document paths and record relocation rather than rewriting archived evidence.
- `outputs/` may contain only current generated PF-ERI v2 results and its README after migration.
- All destructive cleanup is allowlisted, dry-run-first, hash-verified, and reversible from a canonical retained file plus manifest.
- Do not deduplicate the 158 cross-label Bobcat urban/wild pairs until a separate scientific audit resolves them.

---

### Task 1: Layout migration command

**Files:**
- Create: `scripts/migrate_pferi_v1_v2_layout.py`
- Create: `tests/test_migrate_pferi_v1_v2_layout.py`
- Create at runtime: `docs/project-governance/structure/2026-07-17_pferi_v1_v2_relocation_manifest.csv`

**Interfaces:**
- Consumes: repository root, fixed source/destination mapping, optional `--apply`.
- Produces: `build_plan(root) -> list[Move]`, `rewrite_active_references(root, mappings) -> list[str]`, and a relocation CSV containing `source_path,destination_path,size_bytes,sha256`.

- [ ] **Step 1: Write failing layout tests**

```python
def test_plan_separates_scientific_generations(tmp_path):
    seed_minimal_repository(tmp_path)
    plan = migration.build_plan(tmp_path)
    assert destination(plan, "outputs/final_freeze/a.jpg") == "data/frozen/pferi_v2/a.jpg"
    assert destination(plan, "outputs/modeling-validation/v1.csv") == "archive/pferi_v1/outputs/modeling-validation/v1.csv"
    assert destination(plan, "outputs/v2_candidate_reservoir/ws04.csv") == "archive/pferi_v2/task_runs/ws04.csv"
```

- [ ] **Step 2: Run tests and confirm they fail before implementation**

Run: `pytest -q tests/test_migrate_pferi_v1_v2_layout.py`

Expected: import or attribute failure because the migration module is not implemented.

- [ ] **Step 3: Implement dry-run planning, collision checks, hashing, moving, and active-reference rewriting**

```python
@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path

def relocate_path(relative_path: str) -> str | None:
    for old, new in sorted(PATH_MAPPINGS, key=lambda pair: len(pair[0]), reverse=True):
        if relative_path == old or relative_path.startswith(old + "/"):
            return new + relative_path[len(old):]
    return None
```

- [ ] **Step 4: Run focused tests**

Run: `pytest -q tests/test_migrate_pferi_v1_v2_layout.py`

Expected: all migration tests pass without modifying the real repository.

### Task 2: Execute the physical separation

**Files:**
- Move: `outputs/final_freeze/` → `data/frozen/pferi_v2/`
- Move: legacy output areas → `archive/pferi_v1/outputs/`
- Move: `outputs/v2_candidate_reservoir/` → `archive/pferi_v2/task_runs/`
- Move: v2 execution packages → `work/pferi_v2/`
- Move: transfer ZIPs → `artifacts/transfers/pferi_v2/`
- Move: `outputs/.ua/` → `.ua/outputs-analysis/`
- Modify mechanically: active references in `scripts/`, `tests/`, `docs/`, `schemas/`, root project documentation, and GPU code.

**Interfaces:**
- Consumes: the validated plan from Task 1.
- Produces: the new directory structure plus the relocation manifest.

- [ ] **Step 1: Run migration dry-run**

Run: `python scripts/migrate_pferi_v1_v2_layout.py`

Expected: a collision-free move/rewrite summary and no filesystem changes.

- [ ] **Step 2: Apply migration**

Run: `python scripts/migrate_pferi_v1_v2_layout.py --apply`

Expected: all planned paths moved, manifest written, old roots absent.

- [ ] **Step 3: Scan for live old-path references**

Run: `rg -n 'outputs/(final_freeze|v2_candidate_reservoir)' scripts tests docs schemas gpu README.md PROJECT_RULES.md`

Expected: no active references, excluding explicitly quoted historical migration documentation.

### Task 3: Reconstructable work-image deduplication

**Files:**
- Create: `scripts/deduplicate_pferi_v2_work_images.py`
- Create: `scripts/materialize_pferi_v2_work_images.py`
- Create: `tests/test_pferi_v2_work_image_dedup.py`
- Create at runtime: `artifacts/manifests/pferi_v2_work_image_dedup.csv`

**Interfaces:**
- `find_duplicates(work_root, frozen_root) -> list[Duplicate]`
- `deduplicate(..., apply=False)` removes only files whose SHA-256 exactly matches a retained frozen file.
- `materialize(manifest, apply=False, mode="copy")` restores missing work paths after rechecking the canonical hash.

- [ ] **Step 1: Write failing round-trip tests**

```python
def test_deduplicate_and_materialize_round_trip(tmp_path):
    frozen, work = seed_same_image(tmp_path)
    rows = dedup.find_duplicates(work, frozen)
    dedup.apply(rows)
    assert not work.exists()
    materialize.restore(rows)
    assert work.read_bytes() == frozen.read_bytes()
```

- [ ] **Step 2: Implement strict same-hash deletion and restoration**

Deletion must refuse missing canonical files, mismatched hashes, paths outside `work/pferi_v2`, or canonical paths outside `data/frozen/pferi_v2`.

- [ ] **Step 3: Test, dry-run, and apply**

Run: `pytest -q tests/test_pferi_v2_work_image_dedup.py`

Run: `python scripts/deduplicate_pferi_v2_work_images.py`

Run after reviewing counts: `python scripts/deduplicate_pferi_v2_work_images.py --apply`

Expected: only reconstructable duplicate work images are removed; no frozen file is modified.

### Task 4: Contracts, documentation, and full verification

**Files:**
- Modify: `.gitignore`
- Modify: `outputs/README.md`
- Create: `archive/pferi_v1/README.md`
- Create: `work/pferi_v2/README.md`
- Create: `artifacts/transfers/pferi_v2/README.md`
- Modify: `docs/CURRENT_PROJECT_MAP.md`
- Modify: `docs/project-governance/structure/current_pipeline_manifest.md`
- Modify: `docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`

**Interfaces:**
- Documents define the only authoritative physical locations and the no-direct-v1-input rule for Workbook04.

- [ ] **Step 1: Update boundary documentation and ignore rules**

Document `data/frozen/pferi_v2`, `archive/pferi_v2/task_runs`, `archive/pferi_v1`, `work/pferi_v2`, and `artifacts/transfers/pferi_v2`, including how to materialize deduplicated work images.

- [ ] **Step 2: Run Workbook04 and v2 regression tests**

Run: `pytest -q tests/test_audit_ws04_power_cost_inputs.py tests/test_simulate_ws04_power_cost_sensitivity.py tests/test_audit_ws04_four_stage_allocation.py tests/test_v2_timed_operational_rehearsal.py tests/test_v2_canonical_pair_contract.py tests/test_build_v2_czechlynx_image_context.py`

Expected: all tests pass.

- [ ] **Step 3: Run path and byte-integrity verification**

Verify that old roots are absent, every relocation manifest destination exists unless it is listed in the dedup manifest, frozen file hashes match their pre-migration hashes, and `outputs/` contains only `README.md` plus `pferi_v2/`.

- [ ] **Step 4: Run the complete test suite**

Run: `pytest -q`

Expected: zero failures, or explicitly report pre-existing unrelated failures with evidence.

## Self-Review

- Spec coverage: physical v1/v2 separation, output-boundary cleanup, reproducibility, temporary/archive handling, Workbook04 isolation, and no ambiguous cross-label deletion are covered.
- Placeholder scan: no deferred implementation placeholders are present.
- Type consistency: `Move`, `Duplicate`, relocation CSV fields, and materialization interfaces are consistent across tasks.
