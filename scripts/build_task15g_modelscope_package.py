#!/usr/bin/env python3
"""Build the immutable PF-ERI Task 15G ModelScope execution package."""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/pferi_v2/gpu/packages/task15g_performance_bound"
PACKAGE_NAME = "PF_ERI_TASK15G_MODELSCOPE_PACKAGE"
TASK15E_PACKAGE = (
    ROOT
    / "work/pferi_v2/gpu/packages/task15e_model_comparison"
    / "PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE"
)
TASK15G_FREEZE = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_contract_freeze_v1"
)
CHECKPOINT_NAME = "tabpfn-v2-classifier-finetuned-zk73skhh.ckpt"
CHECKPOINT_SHA256 = "cf8c519c01eaf1613ee91239006d57b1c806ff5f23ac1aeb1315ba1015210e49"
CHECKPOINT_SIZE = 29009539
CHECKPOINT_URL = (
    "https://huggingface.co/Prior-Labs/TabPFN-v2-clf/resolve/"
    "f851f2a3c941544733b712d8c0f96dfae9b28862/"
    f"{CHECKPOINT_NAME}"
)
TABPFN_WHEEL_NAME = "tabpfn-8.0.7-py3-none-any.whl"
TABPFN_WHEEL_SHA256 = "e8b32182b704be026475750f80e51ee025c6b6242eb8e4f0da10bbaad8c9ee18"
TABPFN_WHEEL_SIZE = 747462
TABPFN_WHEEL_URL = (
    "https://files.pythonhosted.org/packages/14/b9/"
    "78ff7e06aaa929fa354d69463fd7f73fb65b07a1c19d397034f7fa9c0628/"
    f"{TABPFN_WHEEL_NAME}"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def download_exact(url: str, target: Path, expected_sha256: str, expected_size: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "PF-ERI-Task15G/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    if target.stat().st_size != expected_size:
        raise RuntimeError(f"download size mismatch: {target.name}")
    if sha256(target) != expected_sha256:
        raise RuntimeError(f"download SHA256 mismatch: {target.name}")


def inspect_tabpfn_fit_signature(wheel: Path) -> dict[str, Any]:
    with zipfile.ZipFile(wheel) as archive:
        source = archive.read("tabpfn/classifier.py").decode("utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "TabPFNClassifier":
            for member in node.body:
                if isinstance(member, ast.FunctionDef) and member.name == "fit":
                    positional = [argument.arg for argument in member.args.args]
                    keyword_only = [argument.arg for argument in member.args.kwonlyargs]
                    supports = "sample_weight" in positional + keyword_only
                    return {
                        "audit_version": "pferi_v2_task15g_tabpfn_api_precheck_v1",
                        "status": "PASS",
                        "package": "tabpfn==8.0.7",
                        "wheel_filename": wheel.name,
                        "wheel_sha256": sha256(wheel),
                        "wheel_size_bytes": wheel.stat().st_size,
                        "source_member": "tabpfn/classifier.py",
                        "fit_signature": f"fit({', '.join(positional + keyword_only)})",
                        "fit_positional_parameters": positional,
                        "fit_keyword_only_parameters": keyword_only,
                        "supports_sample_weight": supports,
                        "disposition": (
                            "ELIGIBLE_FOR_WEIGHTED_FIT"
                            if supports
                            else "PREDECLARED_INELIGIBLE_UNDER_COMMON_WEIGHTING_CONTRACT"
                        ),
                    }
    raise RuntimeError("TabPFNClassifier.fit not found in frozen wheel")


def write_manifest(package: Path) -> None:
    files = sorted(
        path
        for path in package.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256"
    )
    (package / "PACKAGE_MANIFEST.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(package)}\n" for path in files),
        encoding="utf-8",
    )


def verify_manifest(package: Path) -> None:
    declared: set[str] = set()
    for line in (package / "PACKAGE_MANIFEST.sha256").read_text(
        encoding="utf-8"
    ).splitlines():
        expected, relative = line.split("  ", 1)
        declared.add(relative)
        target = package / relative
        if not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package verification failed: {relative}")
    actual = {
        str(path.relative_to(package))
        for path in package.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256"
    }
    if actual != declared:
        raise RuntimeError(
            f"package inventory mismatch: missing={sorted(declared - actual)} "
            f"unexpected={sorted(actual - declared)}"
        )


def requirements_text() -> str:
    return """interpret==0.7.8
catboost==1.2.10
numpy==2.3.3
pandas==2.3.3
scipy==1.16.2
scikit-learn==1.7.2
"""


def readme_text() -> str:
    return """# PF-ERI v2 Task 15G ModelScope execution

This immutable package runs the frozen, development-only E1 Explainable Boosting Machine and E2 shallow CatBoost performance-bound benchmark. E3 is pinned and audited but emits no prediction because the frozen TabPFN API cannot consume the required square-root inverse-probability fitting weights. The package never reads calibration, deployment-confirmation, or mechanism-confirmation outcomes and never selects the final development model.

## Runtime

Use Python 3.12. A CPU runtime is sufficient; CUDA is not required. In a fresh ModelScope terminal or notebook cell:

```bash
python -m pip install -U uv
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python --version
```

Unzip the package and enter `PF_ERI_TASK15G_MODELSCOPE_PACKAGE`. Run exactly:

```bash
python run_task15g.py smoke --package-root . --output-dir PF_ERI_TASK15G_SMOKE
python run_task15g.py run --package-root . --output-dir PF_ERI_TASK15G_RESULTS --smoke-audit PF_ERI_TASK15G_SMOKE/smoke_audit.json
python run_task15g.py validate --results-dir PF_ERI_TASK15G_RESULTS
python run_task15g.py export --results-dir PF_ERI_TASK15G_RESULTS --zip PF_ERI_TASK15G_FINAL_EXPORT.zip
sha256sum PF_ERI_TASK15G_FINAL_EXPORT.zip > PF_ERI_TASK15G_FINAL_EXPORT.sha256
```

The smoke command verifies the exact dependency versions, package manifest, E3 wheel API, E3 checkpoint identity, preprocessing interface, fitting-weight interface, and one real E1/E2 fit. A failed smoke blocks the full run.

The full run evaluates all eight E1 and twelve E2 configurations in the frozen four-fold inner assignments within every outer training set. It then refits the selected configuration and produces one honest out-of-fold probability for each of 445 development pairs and each eligible model. It may take several hours on CPU.

Each completed model-by-outer-fold fit is stored under `PF_ERI_TASK15G_RESULTS/fold_checkpoints`. Re-running the same command resumes only checkpoints whose file hashes and frozen contract hash still match. Keep the entire results directory between sessions and do not edit checkpoints.

Return `PF_ERI_TASK15G_FINAL_EXPORT.zip`, `PF_ERI_TASK15G_FINAL_EXPORT.sha256`, and `PF_ERI_TASK15G_RUN_SUMMARY.txt`. An export is scientifically usable only when validation and export both report `PASS`.
"""


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    sources = {
        "run_task15g.py": ROOT / "scripts/task15g_modelscope_runner.py",
        "pferi_v2_fold_preprocessor.py": ROOT / "scripts/pferi_v2_fold_preprocessor.py",
        "contracts/task15g_exploratory_performance_bound_contract.json": (
            ROOT / "schemas/pferi_v2/task15g_exploratory_performance_bound_contract_v1.json"
        ),
        "contracts/feature_preprocessing_contract.json": (
            TASK15E_PACKAGE / "contracts/feature_preprocessing_contract.json"
        ),
        "contracts/candidate_model_registry.json": (
            TASK15E_PACKAGE / "contracts/model_route_candidate_registry.json"
        ),
        "inputs/development_modeling_input.csv": (
            TASK15E_PACKAGE / "inputs/development_modeling_input.csv"
        ),
        "inputs/outer_fold_assignments.csv": (
            TASK15E_PACKAGE / "inputs/outer_fold_assignments.csv"
        ),
        "inputs/nested_fold_assignments.csv": (
            TASK15E_PACKAGE / "inputs/nested_fold_assignments.csv"
        ),
        "audits/task15f_disposition.json": (
            ROOT
            / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15f_bayesian_sensitivity_result_freeze_v1"
            / "task15f_disposition.json"
        ),
        "audits/task15g_contract_freeze_audit.json": (
            TASK15G_FREEZE / "contract_freeze_audit.json"
        ),
        "audits/TASK15G_CONTRACT_FREEZE_REPORT.md": (
            TASK15G_FREEZE / "TASK15G_CONTRACT_FREEZE_REPORT.md"
        ),
    }
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task15g_package_") as temporary:
        stage_root = Path(temporary)
        package = stage_root / PACKAGE_NAME
        for relative, source in sources.items():
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (package / "requirements.txt").write_text(requirements_text(), encoding="utf-8")
        (package / "README_MODELSCOPE.md").write_text(readme_text(), encoding="utf-8")

        checkpoint = package / "models" / CHECKPOINT_NAME
        wheel = package / "vendor" / TABPFN_WHEEL_NAME
        download_exact(CHECKPOINT_URL, checkpoint, CHECKPOINT_SHA256, CHECKPOINT_SIZE)
        download_exact(
            TABPFN_WHEEL_URL, wheel, TABPFN_WHEEL_SHA256, TABPFN_WHEEL_SIZE
        )
        api_audit = inspect_tabpfn_fit_signature(wheel)
        if api_audit["supports_sample_weight"] is not False:
            raise RuntimeError("frozen TabPFN API unexpectedly supports sample_weight")
        write_json(package / "audits/tabpfn_api_precheck.json", api_audit)

        write_manifest(package)
        verify_manifest(package)
        zip_path = stage_root / f"{PACKAGE_NAME}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(
                        path,
                        arcname=f"{PACKAGE_NAME}/{path.relative_to(package)}",
                    )
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"bad ZIP member: {bad}")

        contract = package / "contracts/task15g_exploratory_performance_bound_contract.json"
        audit = {
            "status": "PASS",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "package_name": PACKAGE_NAME,
            "file_count_excluding_manifest": len(
                [
                    path
                    for path in package.rglob("*")
                    if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256"
                ]
            ),
            "manifest_sha256": sha256(package / "PACKAGE_MANIFEST.sha256"),
            "zip_sha256": sha256(zip_path),
            "zip_size_bytes": zip_path.stat().st_size,
            "runner_source_sha256": sha256(ROOT / "scripts/task15g_modelscope_runner.py"),
            "runner_packaged_sha256": sha256(package / "run_task15g.py"),
            "contract_sha256": sha256(contract),
            "checkpoint_sha256": sha256(checkpoint),
            "checkpoint_size_bytes": checkpoint.stat().st_size,
            "tabpfn_wheel_sha256": sha256(wheel),
            "tabpfn_fit_signature": api_audit["fit_signature"],
            "E3_supports_sample_weight": api_audit["supports_sample_weight"],
            "E3_prediction_rows": 0,
            "locked_stage_outcomes_included": False,
            "model_fitting_performed": False,
        }
        write_json(stage_root / "package_build_audit.json", audit)
        (stage_root / f"{PACKAGE_NAME}.sha256").write_text(
            f"{audit['zip_sha256']}  {PACKAGE_NAME}.zip\n", encoding="utf-8"
        )
        shutil.copytree(stage_root, output)
    return audit


def main() -> int:
    try:
        audit = build()
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
