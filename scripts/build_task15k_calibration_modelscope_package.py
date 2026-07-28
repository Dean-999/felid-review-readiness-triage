#!/usr/bin/env python3
"""Build the immutable Task15K ModelScope measurement and frozen-score package."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
DESIGN = MODEL_ROOT / "2026-07-27_task15k_independent_calibration_design_freeze_v1"
TASK15J = ROOT / "outputs/pferi_v2/models/development"
CONTRACT = ROOT / "schemas/pferi_v2/task15k_independent_calibration_contract_v1.json"
OUTPUT = ROOT / "work/pferi_v2/gpu/packages/task15k_calibration"
PACKAGE_NAME = "PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(package: Path) -> None:
    files = sorted(path for path in package.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256")
    (package / "PACKAGE_MANIFEST.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(package)}\n" for path in files), encoding="utf-8")


def verify_manifest(package: Path) -> None:
    declared = set()
    for line in (package / "PACKAGE_MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1); target = package / relative
        if relative in declared or not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package verification failed: {relative}")
        declared.add(relative)
    actual = {str(path.relative_to(package)) for path in package.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256"}
    if actual != declared:
        raise RuntimeError("package manifest inventory mismatch")


def readme() -> str:
    return """# PF-ERI Task15K calibration control package

This standalone ModelScope package contains 560 hash-verified calibration-candidate images, 448 outcome-free pair records, frozen quality-reference percentiles, and the immutable Task15J P3/P5 model bundle. It does not contain calibration labels, identity labels, deployment-confirmation outcomes, or mechanism-confirmation outcomes.

Use a CPU image with Python 3.10+ and run:

```bash
unzip PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE.zip
cd PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE
python -m pip install -r requirements.txt
python run_task15k_controls.py run --package-root . --image-root images --output-dir PF_ERI_TASK15K_CALIBRATION_RESULTS
python run_task15k_controls.py validate --package-root . --results-dir PF_ERI_TASK15K_CALIBRATION_RESULTS
python run_task15k_controls.py export --results-dir PF_ERI_TASK15K_CALIBRATION_RESULTS --zip PF_ERI_TASK15K_CALIBRATION_FINAL_EXPORT.zip
sha256sum PF_ERI_TASK15K_CALIBRATION_FINAL_EXPORT.zip > PF_ERI_TASK15K_CALIBRATION_FINAL_EXPORT.sha256
```

The runner verifies the control-package manifest, every image SHA256, frozen selected-pair manifest hash, and frozen Task15J bundle hash before measurement. It remeasures endpoint quality and frozen SIFT/RANSAC local-match coverage, then emits raw uncalibrated P3/P5 probabilities. Any endpoint-quality failure stops scoring; a local-match failure is explicitly represented as a failure feature and is never converted to zero evidence.

Return only the final export ZIP and SHA256 declaration. Do not create reviewer labels in the ModelScope environment.
"""


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    if not (DESIGN / "CHECKSUMS.sha256").is_file():
        raise FileNotFoundError("Task15K design freeze is required")
    pairs = DESIGN / "calibration_candidate_pairs.csv"; images = DESIGN / "selected_image_manifest.csv"; refs = DESIGN / "quality_reference_percentiles.csv"
    import csv
    with images.open(encoding="utf-8", newline="") as handle:
        image_rows = list(csv.DictReader(handle))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["execution_binding"] = {
        "expected_pair_count": 448, "expected_image_count": len(image_rows),
        "candidate_pair_manifest_sha256": sha256(pairs), "selected_image_manifest_sha256": sha256(images),
        "quality_reference_percentiles_sha256": sha256(refs),
        "final_model_bundle_payload_sha256": json.loads((TASK15J / "final_model_bundle.json").read_text(encoding="utf-8"))["bundle_payload_sha256"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task15k_modelscope_") as temporary:
        stage = Path(temporary); package = stage / PACKAGE_NAME
        sources = {
            "run_task15k_controls.py": ROOT / "scripts/task15k_calibration_modelscope_runner.py",
            "pferi_v2_fold_preprocessor.py": ROOT / "scripts/pferi_v2_fold_preprocessor.py",
            "inputs/calibration_candidate_pairs.csv": pairs, "inputs/selected_image_manifest.csv": images,
            "inputs/quality_reference_percentiles.csv": refs, "inputs/final_model_bundle.json": TASK15J / "final_model_bundle.json",
        }
        for relative, source in sources.items():
            target = package / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        contract_path = package / "contracts/task15k_independent_calibration_contract.json"; contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for row in image_rows:
            source = ROOT / row["local_relative_path"]
            target = package / "images" / row["image_filename"]
            if not source.is_file() or sha256(source) != row["content_sha256"]:
                raise RuntimeError(f"selected image unavailable or mismatched: {row['candidate_image_id']}")
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        (package / "requirements.txt").write_text("numpy==1.26.4\npandas==2.2.3\npillow==10.4.0\nopencv-python-headless==4.10.0.84\n", encoding="utf-8")
        (package / "README_MODELSCOPE.md").write_text(readme(), encoding="utf-8")
        write_manifest(package); verify_manifest(package)
        zip_path = stage / f"{PACKAGE_NAME}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file(): archive.write(path, arcname=f"{PACKAGE_NAME}/{path.relative_to(package)}")
        if zipfile.ZipFile(zip_path).testzip() is not None:
            raise RuntimeError("package ZIP CRC failure")
        audit = {
            "status": "PASS", "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "package_name": PACKAGE_NAME,
            "zip_sha256": sha256(zip_path), "package_manifest_sha256": sha256(package / "PACKAGE_MANIFEST.sha256"),
            "image_count": len(image_rows), "pair_count": 448, "image_zip_included": True,
            "calibration_outcomes_included": False, "locked_stage_outcomes_included": False,
            "claim_boundary": contract["claim_boundary"],
        }
        (stage / "package_build_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / f"{PACKAGE_NAME}.sha256").write_text(f"{audit['zip_sha256']}  {PACKAGE_NAME}.zip\n", encoding="utf-8")
        shutil.copytree(stage, output)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, default=OUTPUT); args = parser.parse_args()
    try:
        print(json.dumps(build(args.output), indent=2, sort_keys=True)); return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
