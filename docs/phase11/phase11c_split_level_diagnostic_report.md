# Phase 11C Split-Level Diagnostic Report

## Scope

This report is retained because the active scripts `build_phase11c_split_level_diagnostics.py` and `audit_phase11c_split_level_diagnostics.py` write to and audit this path.

## Summary

Phase 11C diagnostics evaluate split-level evidence structure for pair-level PF-ERI metric-learning experiments. The diagnostics are not a scientific-success claim; they identify whether failures are likely due to image-set composition, positive-pair reliability, hard-negative structure, or calibration limits in the pair reliability score.

## Current Interpretation

- C3/H3 image-set differences were not enough to explain all training instability.
- Split-level pair structure and hard negatives remain important.
- R formula recalibration should be considered if held-out failures persist despite similar image-quality and pair-reliability distributions.

## Boundary

This file is an active diagnostic report location, not a planning document. It should remain in `docs/phase11/` unless the active scripts are updated.
