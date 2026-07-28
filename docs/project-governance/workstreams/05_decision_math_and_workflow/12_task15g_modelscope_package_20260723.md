# Task 15G ModelScope Execution Package

Status: **COMPLETE - PACKAGE AND REAL-DEPENDENCY SMOKE PASS**
Date: 23 July 2026
Applies to: Workstream 05 / Task 15G-B

## Package purpose

Task 15G-B converts the frozen exploratory performance-bound contract into a self-contained execution package. The package runs E1 and E2 under the same 445-pair development boundary, component-disjoint nested folds, fold-training preprocessing, square-root inverse-probability fitting weights, and design-weighted validation fixed in Task 15G-A. It includes no calibration, deployment-confirmation, or mechanism-confirmation outcome and cannot select the final development model.

The runner evaluates all eight E1 Explainable Boosting Machine configurations and all twelve E2 shallow CatBoost configurations in each outer-training set. A configuration is eligible for selection only when all four inner folds succeed. The selected configuration is refitted once on the complete outer-training set and must produce one honest out-of-fold probability for every pair in that outer fold. Each completed model-by-outer-fold unit is protected by hashes over its prediction, inner-selection, and selected-configuration files, allowing an interrupted run to resume without silently accepting altered checkpoints.

E3 remains registered but non-executable under the common weighting contract. The package contains the exact 29,009,539-byte TabPFN v2 checkpoint with SHA256 `cf8c519c01eaf1613ee91239006d57b1c806ff5f23ac1aeb1315ba1015210e49` and the official `tabpfn==8.0.7` wheel with SHA256 `e8b32182b704be026475750f80e51ee025c6b6242eb8e4f0da10bbaad8c9ee18`. The builder parses the wheel source and independently confirms the frozen `fit(self, X, y)` signature. Because no native `sample_weight` argument exists, E3 must emit zero predictions; the package does not install TabPFN or use replication, duplication, resampling, or fine-tuning as a substitute.

## Engineering controls

The package manifest binds every included source file, input, contract, audit, dependency specification, wheel, and checkpoint. Manifest verification rejects both missing or altered files and undeclared additions. The runner disables Python bytecode writes before importing the packaged preprocessor, preventing a smoke or full run from mutating the package inventory. Results are written outside the package, validated globally, assigned internal SHA256 checksums, and exported under a single `PF_ERI_TASK15G_RESULTS/` ZIP prefix.

The exact Python 3.12 environment installed `interpret==0.7.8`, `catboost==1.2.10`, `numpy==2.3.3`, `pandas==2.3.3`, `scipy==1.16.2`, and `scikit-learn==1.7.2`. A real-data non-scientific smoke fitted one E1 and one E2 configuration on outer-fold-zero training data, generated sixteen finite probabilities per model, verified the shared frozen preprocessor hash, confirmed the E3 disposition, and accessed no locked-stage outcome. Running smoke did not add a `.pyc` or any other undeclared file to the package.

The package builder is `scripts/build_task15g_modelscope_package.py`, the execution runner is `scripts/task15g_modelscope_runner.py`, and focused tests are in `tests/test_task15g_modelscope_runner.py`. The package is stored at:

`work/pferi_v2/gpu/packages/task15g_performance_bound/`

The final package ZIP SHA256 is `6c5702970bc2ce86ae1b52f90a71ffc27e1311543e52e4b4be50fc0d774fa0e9`. The package manifest SHA256 is `dcd8622b6000d5a2df62adc846e01e9fa0a657d72746c76d898c7f65115a3c57`.

## Next gate

The package passed its real-dependency smoke and authorized the full Task 15G E1/E2 run. Scientific interpretation remains prohibited until the complete export passes global validation and an independent result freeze.
