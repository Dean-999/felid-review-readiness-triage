# Kaggle guide

Upload this ZIP as Dataset slug `pferi-final-local-match-v2`; upload the opaque
input ZIP separately as `pferi-local-match-input`. Enable Internet and GPU,
open the notebook, run each cell exactly once, and download
`PF_ERI_FINAL_RESULTS.zip` unchanged. The output retains its input directory
only during execution; the final ZIP excludes it.

Execution order is mandatory: `freeze` → `smoke_test` (five pairs) → full run
→ validation. A smoke-test interface failure returns nonzero and the notebook
will not advance to the full-run cell.

After inference, run `python validate_final_results.py --output-dir
PF_ERI_FINAL_RESULTS`. Only `FINAL_VALIDATION_PASS` is eligible for the next
gate; `PARTIAL` or `FINAL_VALIDATION_FAIL` is evidence, never a pass.
