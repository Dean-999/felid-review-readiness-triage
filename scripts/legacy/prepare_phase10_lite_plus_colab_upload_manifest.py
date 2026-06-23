#!/usr/bin/env python3
"""Prepare a Phase 10-Lite Plus Colab upload manifest.

This script only inspects local paths and writes a CSV manifest. It does not
copy, zip, upload, or train anything.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase10_lite"
UPLOAD_MANIFEST = OUT_DIR / "phase10_lite_plus_colab_upload_manifest.csv"
COLAB_DIR = PROJECT_ROOT / "colab/phase10_lite_metric_learning"

COLAB_UPLOAD_FILES = [
    "train_phase10_lite_plus_metric_learning.py",
    "evaluate_phase10_lite_plus_retrieval.py",
    "run_phase10_lite_plus_k3_training.py",
    "plan_phase10_lite_plus_colab_runs.py",
    "patch_phase10_lite_plus_colab_configs.py",
    "summarize_phase10_lite_plus_results.py",
    "requirements_colab.txt",
    "config_plus_k3_random_matched.yaml",
    "config_plus_k3_quality_proxy_matched.yaml",
    "config_plus_k3_pf_eri_matched.yaml",
    "config_plus_k3_pf_eri_quality_hybrid.yaml",
    "config_plus_e4_pf_eri_weighted_all_train.yaml",
]

REQUIRED_UPLOADS = [
    (OUT_DIR / "phase10_lite_plus_matched_training_manifest_k3.csv", "phase10_lite/phase10_lite_plus_matched_training_manifest_k3.csv", "Plus matched/all-train manifest"),
    (OUT_DIR / "phase10_lite_plus_manifest_audit.csv", "phase10_lite/phase10_lite_plus_manifest_audit.csv", "Plus manifest audit"),
    (OUT_DIR / "phase10_lite_plus_training_package_audit.csv", "phase10_lite/phase10_lite_plus_training_package_audit.csv", "Plus package audit"),
    (OUT_DIR / "phase10_lite_plus_training_readiness_summary.csv", "phase10_lite/phase10_lite_plus_training_readiness_summary.csv", "Plus readiness summary"),
    (PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv", "czechlynx_phase4c_megadescriptor_embeddings.csv", "MegaDescriptor fixed embeddings"),
    (PROJECT_ROOT / "outputs/czechlynx/phase9/pf_eri_metric_learning_prep/phase9d_image_training_manifest_internal.csv", "phase9d_image_training_manifest_internal.csv", "Held-out split/test-role source manifest"),
    (PROJECT_ROOT / "data/interim/czechlynx/expanded_125x4_review_images", "expanded_125x4_review_images", "Image folder only if Colab image path checks are needed"),
    (PROJECT_ROOT / "docs/phase10_lite/phase10_lite_plus_colab_runbook.md", "docs/phase10_lite/phase10_lite_plus_colab_runbook.md", "Runbook"),
]

FORBIDDEN_PATHS = [
    PROJECT_ROOT / ".git",
    COLAB_DIR / "__pycache__",
    COLAB_DIR / "smoke_outputs",
    COLAB_DIR / "full_pilot_outputs",
    OUT_DIR / "metric_learning_plus_results",
    OUT_DIR / "metric_learning_results",
    PROJECT_ROOT / "checkpoints",
]

FORBIDDEN_NOT_CHECKED = [
    "data/raw/",
    "delayed second-review images",
    "delayed second-review mapping files",
    "internal mapping files",
    "raw full CzechLynx dataset",
    "checkpoints",
    "Colab logs",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for name in COLAB_UPLOAD_FILES:
        path = COLAB_DIR / name
        rows.append(
            {
                "local_path": rel(path),
                "exists": path.exists(),
                "recommended_drive_relative_path": f"colab/phase10_lite_metric_learning/{name}",
                "include_for_upload": True,
                "reason": "Required Phase 10-Lite Plus Colab script/config/requirement.",
            }
        )
    for path, drive_path, reason in REQUIRED_UPLOADS:
        rows.append(
            {
                "local_path": rel(path),
                "exists": path.exists(),
                "recommended_drive_relative_path": drive_path,
                "include_for_upload": True,
                "reason": reason,
            }
        )
    for path in FORBIDDEN_PATHS:
        rows.append(
            {
                "local_path": rel(path),
                "exists": path.exists(),
                "recommended_drive_relative_path": "",
                "include_for_upload": False,
                "reason": "Do not upload: generated/cache/checkpoint/output/internal repository material.",
            }
        )
    for label in FORBIDDEN_NOT_CHECKED:
        rows.append(
            {
                "local_path": label,
                "exists": "not_checked",
                "recommended_drive_relative_path": "",
                "include_for_upload": False,
                "reason": "Do not upload and do not inspect for this runbook task.",
            }
        )
    pd.DataFrame(rows).to_csv(UPLOAD_MANIFEST, index=False)
    print("PASS prepare_phase10_lite_plus_colab_upload_manifest")
    print(f"row_count={len(rows)}")
    print(f"upload_manifest={UPLOAD_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
