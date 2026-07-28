# GitHub Repository Governance

Effective date: 2026-07-28

## Purpose

GitHub stores portable implementation and review evidence, not the local scientific runtime payload. The repository therefore tracks source code, tests, schemas, documentation, compact publication displays, manifests, audit summaries, and checksums. It excludes raw photos, reviewer responses, restricted mappings, model weights, embeddings, posterior draws, ZIP deliveries, and temporary run outputs.

## Branch and Pull Request Policy

- Start every change from current `main`; do not continue work on a merged branch.
- Use one descriptive branch and pull request for one coherent objective.
- Require the CI workflow to pass before merge. The private-repository plan does not currently support GitHub branch-protection rules, so this is an operational rule until that capability is available.
- Use squash merge for ordinary changes and enable automatic branch deletion after merge.
- Tag accepted scientific freezes with an annotated tag. The tag contains the portable code and audit layer; binary payloads remain local and are referenced by hash.

## Local Evidence Boundary

`archive/pferi_v2/`, `work/pferi_v2/`, `artifacts/transfers/pferi_v2/`, `data/`, and `outputs/` are local evidence boundaries. Their README, manifest, audit, and hash records explain reconstruction without uploading the underlying payloads to GitHub.

## Required Checks

1. `uv sync --all-groups`
2. `uv run pre-commit run --all-files`
3. `uv run python -m compileall -q scripts tests`
4. `uv run pytest -q`

GitHub Actions runs `uv run pytest -q -m "not local_evidence"`. The excluded marker is only for tests whose asserted inputs are intentionally retained in the non-versioned local evidence boundary. A complete local research checkout runs all tests without the marker filter.

The pull-request template requires confirmation that no restricted or binary payload is staged.
