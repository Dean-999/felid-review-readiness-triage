#!/usr/bin/env python3
"""Build the sealed Task15M external-confirmation ModelScope control package."""
from __future__ import annotations

import csv
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
DESIGN = MODEL_ROOT / "2026-07-27_task15m_independent_confirmation_design_freeze_v1"
TASK15I = MODEL_ROOT / "2026-07-26_task15i_prepair_artifacts_v1"
TASK15J = ROOT / "outputs/pferi_v2/models/development"
TASK15L = ROOT / "outputs/pferi_v2/models/calibration/analysis"
TASK15I_DESCRIPTOR_CONTRACT = ROOT / "schemas/pferi_v2/task15i_descriptor_inference_contract_v1.json"
TASK15M_CONTRACT = ROOT / "schemas/pferi_v2/task15m_independent_confirmation_contract_v1.json"
OUTPUT = ROOT / "work/pferi_v2/gpu/packages/task15m_confirmation"
PACKAGE_NAME = "PF_ERI_TASK15M_CONFIRMATION_MODELSCOPE_CONTROL_PACKAGE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(package: Path) -> None:
    files = sorted(path for path in package.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256")
    (package / "PACKAGE_MANIFEST.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(package)}\n" for path in files), encoding="utf-8"
    )


def verify_manifest(package: Path) -> None:
    declared: set[str] = set()
    for line in (package / "PACKAGE_MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        target = package / relative
        if relative in declared or not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package verification failed: {relative}")
        declared.add(relative)
    actual = {str(path.relative_to(package)) for path in package.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256"}
    if actual != declared:
        raise RuntimeError("package manifest inventory mismatch")


def verify_checksums(directory: Path) -> None:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        raise FileNotFoundError(f"missing checksum manifest: {directory}")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        if sha256(directory / relative) != expected:
            raise RuntimeError(f"upstream checksum mismatch: {directory / relative}")


def requirements_text() -> str:
    return """numpy==2.3.3
pandas==2.2.3
pillow==11.3.0
opencv-python-headless==4.10.0.84
timm==1.0.27
transformers==5.12.1
torch==2.11.0+cu128
torchvision==0.26.0+cu128
--extra-index-url https://download.pytorch.org/whl/cu128
"""


def readme_text() -> str:
    return """# PF-ERI Task15M external confirmation control package

This package is the outcome-free measurement and frozen-scoring stage for Task15M. It contains 815 hash-verified full-frame images and 889 pre-frozen external-confirmation candidate pairs. It contains no historical confirmation outcomes, reviewer labels, or identity truth.

It remeasures the current Task15I dual descriptors, endpoint quality, and SIFT/RANSAC local-match coverage. It then uses the frozen Task15J P3/P5 coefficients and fixed Task15L logistic calibration transform. Pairs outside the frozen `both_agreement` / `both_reciprocal` descriptor taxonomy are reported as unsupported and are not scored. This is still not an external-performance conclusion: confirmation outcomes must remain sealed until this package's export is frozen and verified.

Use a CUDA GPU ModelScope environment with Python 3.12 and at least 16 GB VRAM:

```bash
unzip PF_ERI_TASK15M_CONFIRMATION_MODELSCOPE_CONTROL_PACKAGE.zip
cd PF_ERI_TASK15M_CONFIRMATION_MODELSCOPE_CONTROL_PACKAGE
python -m pip install -U uv
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt

python run_task15m_confirmation.py run --package-root . --image-root images --output-dir PF_ERI_TASK15M_CONFIRMATION_RESULTS --batch-size 16
python run_task15m_confirmation.py validate --package-root . --results-dir PF_ERI_TASK15M_CONFIRMATION_RESULTS
python run_task15m_confirmation.py export --results-dir PF_ERI_TASK15M_CONFIRMATION_RESULTS --zip PF_ERI_TASK15M_CONFIRMATION_FINAL_EXPORT.zip
sha256sum PF_ERI_TASK15M_CONFIRMATION_FINAL_EXPORT.zip > PF_ERI_TASK15M_CONFIRMATION_FINAL_EXPORT.sha256
```

Return only the final export ZIP and its SHA256 declaration. Do not add, change, or inspect confirmation outcome files in the ModelScope environment.
"""


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    verify_checksums(DESIGN)
    verify_checksums(TASK15L)
    pairs = DESIGN / "confirmation_candidate_pairs.csv"
    images = DESIGN / "selected_image_manifest.csv"
    quality_reference = TASK15I / "prelabel_inputs/automatic_quality_measurements.csv"
    bundle_path = TASK15J / "final_model_bundle.json"
    with images.open(newline="", encoding="utf-8") as handle:
        image_rows = list(csv.DictReader(handle))
    with pairs.open(newline="", encoding="utf-8") as handle:
        pair_rows = list(csv.DictReader(handle))
    descriptor_contract = json.loads(TASK15I_DESCRIPTOR_CONTRACT.read_text(encoding="utf-8"))
    model_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    calibration = json.loads((TASK15L / "task15l_calibration_analysis_freeze_record.json").read_text(encoding="utf-8"))["calibration"]
    if len(image_rows) != 815 or len(pair_rows) != 889 or len(list(csv.DictReader(quality_reference.open(encoding="utf-8")))) != 4108:
        raise RuntimeError("unexpected Task15M source inventory")
    if set(descriptor_contract["descriptors"]) != {"megadescriptor_l_384", "dinov2_vitl14"} or int(descriptor_contract["top_k"]) != 20:
        raise RuntimeError("unexpected frozen Task15I descriptor configuration")
    execution_contract = {
        "contract_version": "pferi_v2_task15m_confirmation_execution_contract_v1",
        "purpose": "Outcome-free external confirmation remeasurement, frozen scoring, and fixed calibration.",
        "descriptor_inference": {
            "top_k": descriptor_contract["top_k"],
            "descriptors": descriptor_contract["descriptors"],
            "failure_policy": descriptor_contract["failure_policy"],
        },
        "quality_percentile_method": "right-inclusive empirical CDF against the frozen 4,108-image Task15I quality reference distribution; new Task15M images are not added to that reference distribution",
        "descriptor_pair_classification": "both_agreement requires current MegaDescriptor and DINOv2 top-20 retrieval in the same directed endpoint relation; both_reciprocal requires this in both directions",
        "supported_descriptor_categories": ["both_agreement", "both_reciprocal"],
        "unsupported_descriptor_disposition": "Report but do not score unsupported pairs before any confirmation outcome is opened.",
        "fixed_task15l_calibration": {
            "P3": {"intercept": calibration["p3_intercept"], "slope": calibration["p3_slope"]},
            "P5": {"intercept": calibration["p5_intercept"], "slope": calibration["p5_slope"]},
        },
        "execution_binding": {
            "expected_pair_count": len(pair_rows), "expected_image_count": len(image_rows), "quality_reference_image_count": 4108,
            "candidate_pair_manifest_sha256": sha256(pairs), "selected_image_manifest_sha256": sha256(images),
            "quality_reference_sha256": sha256(quality_reference), "final_model_bundle_payload_sha256": model_bundle["bundle_payload_sha256"],
            "task15m_design_contract_sha256": sha256(TASK15M_CONTRACT),
        },
        "prohibited": ["confirmation outcome access", "model refit", "preprocessing change", "lambda change", "P3/P5 reselection", "post-measurement pair-set change"],
        "claim_boundary": "A successful run is an outcome-free measurement and frozen-score export only. It does not establish P5 superiority, external performance, deployment utility, identity accuracy, or project completion.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task15m_modelscope_") as temporary:
        stage = Path(temporary)
        package = stage / PACKAGE_NAME
        sources = {
            "run_task15m_confirmation.py": ROOT / "scripts/task15m_confirmation_modelscope_runner.py",
            "task15i_descriptor_modelscope_runner.py": ROOT / "scripts/task15i_descriptor_modelscope_runner.py",
            "task15k_calibration_modelscope_runner.py": ROOT / "scripts/task15k_calibration_modelscope_runner.py",
            "pferi_v2_fold_preprocessor.py": ROOT / "scripts/pferi_v2_fold_preprocessor.py",
            "inputs/confirmation_candidate_pairs.csv": pairs,
            "inputs/selected_image_manifest.csv": images,
            "inputs/task15i_quality_reference.csv": quality_reference,
            "inputs/final_model_bundle.json": bundle_path,
            "contracts/task15m_independent_confirmation_contract.json": TASK15M_CONTRACT,
        }
        for relative, source in sources.items():
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        execution_path = package / "contracts/task15m_confirmation_execution_contract.json"
        execution_path.write_text(json.dumps(execution_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for row in image_rows:
            source = ROOT / row["local_relative_path"]
            target = package / "images" / row["image_filename"]
            if not source.is_file() or sha256(source) != row["content_sha256"]:
                raise RuntimeError(f"selected image unavailable or mismatched: {row['candidate_image_id']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (package / "requirements.txt").write_text(requirements_text(), encoding="utf-8")
        (package / "README_MODELSCOPE.md").write_text(readme_text(), encoding="utf-8")
        write_manifest(package)
        verify_manifest(package)
        zip_path = stage / f"{PACKAGE_NAME}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=f"{PACKAGE_NAME}/{path.relative_to(package)}")
        if zipfile.ZipFile(zip_path).testzip() is not None:
            raise RuntimeError("package ZIP CRC failure")
        audit = {
            "status": "PASS", "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "package_name": PACKAGE_NAME,
            "zip_sha256": sha256(zip_path), "package_manifest_sha256": sha256(package / "PACKAGE_MANIFEST.sha256"),
            "image_count": len(image_rows), "pair_count": len(pair_rows), "quality_reference_image_count": 4108,
            "image_zip_included": True, "confirmation_outcomes_included": False, "identity_labels_included": False,
            "claim_boundary": execution_contract["claim_boundary"],
        }
        (stage / "package_build_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / f"{PACKAGE_NAME}.sha256").write_text(f"{audit['zip_sha256']}  {PACKAGE_NAME}.zip\n", encoding="utf-8")
        shutil.copytree(stage, output)
    return audit


def main() -> int:
    try:
        print(json.dumps(build(), indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
