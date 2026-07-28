#!/usr/bin/env python3
"""Build the immutable PF-ERI Task 15F ModelScope CPU execution package."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/pferi_v2/gpu/packages/task15f_bayesian_sensitivity"
PACKAGE_NAME = "PF_ERI_TASK15F_MODELSCOPE_CPU_PACKAGE"
TASK15E_PACKAGE = ROOT / "work/pferi_v2/gpu/packages/task15e_model_comparison/PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE"
TASK15E_FREEZE = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15e_development_model_comparison_freeze_v1"
TASK15F_FREEZE = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15f_bayesian_sensitivity_contract_freeze_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(package: Path) -> None:
    files = sorted(path for path in package.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256")
    text = "".join(f"{sha256(path)}  {path.relative_to(package)}\n" for path in files)
    (package / "PACKAGE_MANIFEST.sha256").write_text(text, encoding="utf-8")


def verify_manifest(package: Path) -> None:
    lines = (package / "PACKAGE_MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    for line in lines:
        expected, relative = line.split("  ", 1)
        target = package / relative
        if not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package verification failed: {relative}")


def main() -> None:
    sources = {
        "run_task15f.py": ROOT / "scripts/task15f_modelscope_runner.py",
        "pferi_v2_fold_preprocessor.py": ROOT / "scripts/pferi_v2_fold_preprocessor.py",
        "contracts/task15f_bayesian_sensitivity_contract.json": ROOT / "schemas/pferi_v2/task15f_bayesian_sensitivity_contract_v1.json",
        "contracts/feature_preprocessing_contract.json": TASK15E_PACKAGE / "contracts/feature_preprocessing_contract.json",
        "inputs/development_modeling_input.csv": TASK15E_PACKAGE / "inputs/development_modeling_input.csv",
        "inputs/outer_fold_assignments.csv": TASK15E_PACKAGE / "inputs/outer_fold_assignments.csv",
        "audits/task15e_development_disposition.json": TASK15E_FREEZE / "development_disposition.json",
        "audits/separation_trigger_audit.json": TASK15F_FREEZE / "separation_trigger_audit.json",
        "audits/task15f_contract_freeze_audit.json": TASK15F_FREEZE / "contract_freeze_audit.json",
        "audits/TASK15F_CONTRACT_FREEZE_REPORT.md": TASK15F_FREEZE / "TASK15F_CONTRACT_FREEZE_REPORT.md",
    }
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)

    requirements = """pymc[nutpie]==6.0.1
arviz==1.2.0
nutpie==0.16.11
numpy==2.3.3
pandas==2.3.3
scipy==1.16.2
h5netcdf==1.7.3
"""
    readme = """# PF-ERI v2 Task 15F — ModelScope CPU execution

This immutable package runs the frozen, development-only S3/S4 Bayesian sensitivity analysis and the triggered S5 Firth/FLIC diagnostic. It never reads calibration, deployment-confirmation, or mechanism-confirmation outcomes and it does not select the final model.

## Runtime

Use a CPU notebook with Python 3.12. The runner rejects another Python or PyMC version. In a fresh ModelScope terminal/notebook cell:

```bash
python -m pip install -U uv
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python --version
```

Unzip the package, `cd` into `PF_ERI_TASK15F_MODELSCOPE_CPU_PACKAGE`, then run exactly:

```bash
python run_task15f.py smoke --package-root . --output-dir PF_ERI_TASK15F_SMOKE
python run_task15f.py run --package-root . --output-dir PF_ERI_TASK15F_RESULTS --smoke-audit PF_ERI_TASK15F_SMOKE/smoke_audit.json
python run_task15f.py validate --results-dir PF_ERI_TASK15F_RESULTS
python run_task15f.py export --results-dir PF_ERI_TASK15F_RESULTS --zip PF_ERI_TASK15F_FINAL_EXPORT.zip
sha256sum PF_ERI_TASK15F_FINAL_EXPORT.zip > PF_ERI_TASK15F_FINAL_EXPORT.sha256
```

The smoke gate loads the real inputs, constructs both exact PyMC models, runs 2,000 prior-predictive draws per model, and checks the fixed 20-node Gauss–Hermite implementation. A failed smoke blocks the full run.

The full run contains 10 posterior fits: S3 and S4 in each of five component-disjoint outer folds. Four chains, 1,500 tune draws, 2,000 retained draws, target acceptance 0.95 and maximum tree depth 12 are frozen. A failed convergence gate triggers only the single prespecified retry (3,000 tune draws, target acceptance 0.99). No other retry or parameter change is allowed.

Re-running the same full-run command resumes only fold/model checkpoints that already passed and match the frozen contract hash. Keep the entire results directory between sessions. Do not edit checkpoint JSON or CSV files.

Return `PF_ERI_TASK15F_FINAL_EXPORT.zip` and `PF_ERI_TASK15F_FINAL_EXPORT.sha256`. A ZIP is scientifically usable only when the `validate` and `export` commands report `PASS`.
"""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT.parent, prefix=".task15f_package_") as temporary:
        stage_root = Path(temporary)
        package = stage_root / PACKAGE_NAME
        for relative, source in sources.items():
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (package / "requirements.txt").write_text(requirements, encoding="utf-8")
        (package / "README_MODELSCOPE.md").write_text(readme, encoding="utf-8")
        write_manifest(package)
        verify_manifest(package)

        zip_path = stage_root / f"{PACKAGE_NAME}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=f"{PACKAGE_NAME}/{path.relative_to(package)}")
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"bad ZIP member: {bad}")

        audit = {
            "status": "PASS",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "package_name": PACKAGE_NAME,
            "file_count_excluding_manifest": len(sources) + 2,
            "manifest_sha256": sha256(package / "PACKAGE_MANIFEST.sha256"),
            "zip_sha256": sha256(zip_path),
            "runner_source_sha256": sha256(ROOT / "scripts/task15f_modelscope_runner.py"),
            "runner_packaged_sha256": sha256(package / "run_task15f.py"),
            "contract_sha256": sha256(package / "contracts/task15f_bayesian_sensitivity_contract.json"),
            "locked_stage_outcomes_included": False,
        }
        (stage_root / "package_build_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage_root / f"{PACKAGE_NAME}.sha256").write_text(f"{audit['zip_sha256']}  {PACKAGE_NAME}.zip\n", encoding="utf-8")
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        shutil.copytree(stage_root, OUTPUT)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
