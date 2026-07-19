# PF-ERI v1 reproducibility source

This directory preserves the exact Phase 7–19 Python sources and their directly
coupled regression tests after those exploratory implementations left the active
PF-ERI v2 execution tree.

The files are retained for inspection and historical reconstruction, not as an
active package. Their original project-root assumptions and `scripts.*` imports
are intentionally unchanged. To reproduce an old run, restore the source paths
listed in `docs/project-governance/structure/2026-07-18_pferi_v1_phase_code_archive_manifest.csv`
or check out the recorded source commit in a separate Git worktree. Do not copy
individual archived scripts into the active v2 pipeline.

Phase 18 and Phase 19 joined the archive on 19 July 2026 after their active-tree
files were verified clean. Their original paths, hashes, sizes, and source commit
are appended to the same archive manifest.
