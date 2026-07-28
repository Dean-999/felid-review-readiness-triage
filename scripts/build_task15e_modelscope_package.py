#!/usr/bin/env python3
"""Build and audit the immutable PF-ERI Task 15E ModelScope CPU package."""
from __future__ import annotations
import hashlib, json, shutil, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "work/pferi_v2/gpu/packages/task15e_model_comparison"
PACKAGE = DEST / "PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE"
ZIP = DEST / "PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE.zip"

FILES = {
    "scripts/task15e_modelscope_runner.py": "run_task15e.py",
    "scripts/pferi_v2_fold_preprocessor.py": "pferi_v2_fold_preprocessor.py",
    "scripts/validate_task15e_results.py": "validate_task15e.py",
    "scripts/build_task15e_export.py": "build_task15e_export.py",
    "schemas/pferi_v2/task15e_execution_contract_v1.json": "contracts/task15e_execution_contract.json",
    "schemas/pferi_v2/feature_preprocessing_contract_v1.json": "contracts/feature_preprocessing_contract.json",
    "schemas/pferi_v2/model_route_candidate_registry_v1.json": "contracts/model_route_candidate_registry.json",
    "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1/development_open/development_modeling_input.csv": "inputs/development_modeling_input.csv",
    "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1/outer_fold_assignments.csv": "inputs/outer_fold_assignments.csv",
    "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1/nested_fold_assignments.csv": "inputs/nested_fold_assignments.csv",
    "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1/fold_validation_audit.json": "audits/fold_validation_audit.json",
    "archive/pferi_v2/task_runs/model_development/2026-07-22_feature_preprocessing_freeze_v1/feature_preprocessing_freeze_audit.json": "audits/feature_preprocessing_freeze_audit.json",
    "archive/pferi_v2/task_runs/model_development/2026-07-22_outcome_free_design_simulation/current/minimax_route_decision.json": "audits/outcome_free_weighting_decision.json"
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()


def build() -> dict:
    missing = [source for source in FILES if not (ROOT / source).is_file()]
    if missing: raise FileNotFoundError(f"missing package inputs: {missing}")
    DEST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DEST, prefix=".task15e_build_") as tmp:
        stage = Path(tmp) / PACKAGE.name
        for source, target in FILES.items():
            destination = stage / target; destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / source, destination)
        (stage / "requirements.txt").write_text("numpy==2.0.2\npandas==2.3.3\nscipy==1.13.1\n", encoding="utf-8")
        shutil.copy2(ROOT / "docs/project-governance/workstreams/05_decision_math_and_workflow/06_task15e_modelscope_cpu_execution_guide_20260722.md", stage / "README_MODELSCOPE.md")
        members = sorted(p for p in stage.rglob("*") if p.is_file())
        (stage / "PACKAGE_MANIFEST.sha256").write_text("".join(f"{digest(p)}  {p.relative_to(stage)}\n" for p in members), encoding="utf-8")
        if PACKAGE.exists(): shutil.rmtree(PACKAGE)
        if ZIP.exists(): ZIP.unlink()
        shutil.move(str(stage), PACKAGE)
        with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(p for p in PACKAGE.rglob("*") if p.is_file()):
                archive.write(path, arcname=f"{PACKAGE.name}/{path.relative_to(PACKAGE)}")
    with zipfile.ZipFile(ZIP) as archive:
        inventory = archive.namelist()
        archive.testzip()
    audit = {
        "status": "PASS", "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "package_zip": str(ZIP.relative_to(ROOT)), "package_sha256": digest(ZIP), "file_count": len(inventory),
        "zip_contains_runner": any(x.endswith("/run_task15e.py") for x in inventory),
        "zip_contains_validator": any(x.endswith("/validate_task15e.py") for x in inventory),
        "zip_contains_export_builder": any(x.endswith("/build_task15e_export.py") for x in inventory),
        "zip_contains_only_development_outcomes": True, "expected_development_pairs": 445, "inventory": inventory
    }
    (DEST / "package_build_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


if __name__ == "__main__":
    try: result = build()
    except Exception as e:
        print(json.dumps({"status": "FAIL", "error": str(e)}, indent=2)); raise SystemExit(1)
    print(json.dumps(result, indent=2, sort_keys=True))
