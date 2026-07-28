# Task 15E ModelScope CPU Execution Guide

Status: `EXECUTION PACKAGE READY; FULL DEVELOPMENT RUN NOT YET EXECUTED`

## Scientific boundary

This package fits P0–P5 and the two prespecified restricted GAM sensitivities
S1–S2 using only the 445 open development pairs. It never contains or reads
calibration, deployment-confirmation, or mechanism-confirmation outcomes.
Results are descriptive development evidence and do not constitute the final
confirmatory PF-ERI result.

## ModelScope steps

1. Create a CPU Notebook/Studio session with Python 3.11 and upload
   `PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE.zip`.
2. Run:

```bash
unzip -q PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE.zip
cd PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE
python -m pip install -r requirements.txt
python run_task15e.py smoke --package-root . --output-dir PF_ERI_TASK15E_SMOKE
```

The smoke command runs the exact pipeline on outer fold 0. Continue only when
it returns `SMOKE_PASS`.

3. Run all 445 pairs through the frozen five-outer/four-inner nested design:

```bash
python run_task15e.py run --package-root . --output-dir PF_ERI_TASK15E_RESULTS
```

4. Validate and create the single downloadable archive:

```bash
python validate_task15e.py --results-dir PF_ERI_TASK15E_RESULTS
python build_task15e_export.py \
  --results-dir PF_ERI_TASK15E_RESULTS \
  --zip PF_ERI_TASK15E_FINAL_EXPORT.zip
sha256sum PF_ERI_TASK15E_FINAL_EXPORT.zip
```

Return `PF_ERI_TASK15E_FINAL_EXPORT.zip` without editing its contents.

## Gate behavior

The run stops rather than silently continuing if inputs, hashes/scope, folds,
component disjointness, outcome classes, P3/P5 nesting, optimization, OOF
coverage, or probability bounds are invalid. The runner does not redraw folds,
rebalance classes, access locked stages, or substitute another algorithm.

## Reproducibility note

The package records source hashes, package inventory, Python/platform/library
versions, optimizer diagnostics, foldwise selected lambdas, coefficients and
all honest out-of-fold probabilities. Floating-point results may differ at
negligible last-bit precision across BLAS/CPU builds; the scientific inputs,
folds, formulas and validation gates remain fixed.
