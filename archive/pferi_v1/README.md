# PF-ERI v1 exploratory archive

This root preserves PF-ERI v1 exploratory results, audits, failure analyses and
historical provenance. Nothing here is a PF-ERI v2 development, calibration,
confirmation or deployment input.

Historical files remain byte-preserved under `outputs/`. Their embedded original
paths describe the execution state at creation time and are intentionally not
rewritten. Use the repository relocation manifest to resolve an old path to its
current archive location.

Exact Phase 7–17 source and directly coupled test bytes are preserved under
`reproducibility/`. Use the 2026-07-18 phase-code archive manifest to restore the
original paths in a separate Git worktree.

Workbook04 may consume only the frozen summary and source hashes in
`schemas/pferi_v2/ws04_exploratory_context_v1.json`; it must not read this tree
directly.
