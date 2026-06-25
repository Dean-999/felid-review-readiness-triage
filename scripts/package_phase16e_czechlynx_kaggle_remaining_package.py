#!/usr/bin/env python3
"""Package Phase 16E CzechLynx remaining batches for Kaggle.

This script converts the CzechLynx rows from unavailable local paths to
Kaggle-ready packaged-local paths using the direct zip manifest. It does not
rerun the first 20000 rows, does not copy the 7.3 GB zip files, does not freeze
final 3000, and does not run recalibration.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_MANIFEST = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter_colab_package/phase16e_candidate_model_filter_manifest.csv"
)
ZIP_MANIFEST = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_direct_zip_manifest.csv"
)
RUNNER_SOURCE = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter_colab_package/run_phase16e_candidate_model_filter_colab.py"
)
ZIP_DIR = PROJECT_ROOT / "outputs/phase16/phase16e_czechlynx_direct_zips"

OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16e_czechlynx_remaining_kaggle_package"
RUNNER_OUT = OUTPUT_DIR / "run_phase16e_candidate_model_filter_colab.py"
FULL_MANIFEST_OUT = OUTPUT_DIR / "phase16e_czechlynx_kaggle_runner_ready_manifest.csv"
RUN_CELLS_OUT = OUTPUT_DIR / "phase16e_czechlynx_remaining_kaggle_run_cells.py"
README_OUT = OUTPUT_DIR / "README_PHASE16E_CZECHLYNX_KAGGLE_REMAINING_CN.md"
AUDIT_OUT = OUTPUT_DIR / "phase16e_czechlynx_remaining_kaggle_package_audit.json"

TARGET_QUADRANT = "wild_czechlynx_high_confidence"
EXPECTED_FULL_ROWS = 39_760
KAGGLE_EXTRACT_ROOT = "/kaggle/working/phase16e_work/extracted_images"
EXPECTED_REMAINING_ROWS = 19_760

BATCHES = [
    ("phase16e_czechlynx_remaining_batch_20000_24999.csv", 20_000, 25_000),
    ("phase16e_czechlynx_remaining_batch_25000_29999.csv", 25_000, 30_000),
    ("phase16e_czechlynx_remaining_batch_30000_34999.csv", 30_000, 35_000),
    ("phase16e_czechlynx_remaining_batch_35000_39759.csv", 35_000, 39_760),
]

SENSITIVE_COLUMNS = {
    "unique_name",
    "identity",
    "identity_label",
    "individual",
    "individual_id",
    "animal_id",
    "lynx_id",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "location_id",
    "cell_code",
    "camera",
    "camera_id",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def build_runner_ready_manifest() -> pd.DataFrame:
    base = read_csv(BASE_MANIFEST)
    zips = read_csv(ZIP_MANIFEST)

    czech = base[base["target_quadrant"].astype(str).eq(TARGET_QUADRANT)].copy()
    if len(czech) != EXPECTED_FULL_ROWS:
        raise ValueError(f"Expected {EXPECTED_FULL_ROWS} CzechLynx rows, found {len(czech)}")
    if not czech["candidate_id"].is_unique:
        raise ValueError("Base CzechLynx candidate_id values are not unique")
    if not zips["candidate_id"].is_unique:
        raise ValueError("Zip manifest candidate_id values are not unique")

    zip_keep = [
        "candidate_id",
        "zip_part",
        "zip_filename",
        "zip_internal_path",
        "file_size_bytes",
        "file_sha256",
    ]
    missing = [column for column in zip_keep if column not in zips.columns]
    if missing:
        raise ValueError(f"Zip manifest missing required columns: {missing}")

    merged = czech.merge(zips[zip_keep], on="candidate_id", how="left", validate="one_to_one")
    if merged["zip_internal_path"].isna().any():
        missing_ids = merged.loc[merged["zip_internal_path"].isna(), "candidate_id"].head(10).tolist()
        raise ValueError(f"Missing zip_internal_path for candidate IDs: {missing_ids}")

    leaked = sorted(SENSITIVE_COLUMNS.intersection(merged.columns))
    if leaked:
        merged = merged.drop(columns=leaked)

    merged["source_mode"] = "packaged_local"
    merged["image_uri"] = KAGGLE_EXTRACT_ROOT.rstrip("/") + "/" + merged["zip_internal_path"].astype(str)
    merged["phase16e_model_filter_status"] = "pending_kaggle_remaining_or_merge"
    merged["selection_eligible_pre_model"] = True

    if not merged["image_uri"].astype(str).str.startswith(KAGGLE_EXTRACT_ROOT).all():
        raise ValueError("Not all image_uri values use the Kaggle extracted-images prefix")
    return merged


def write_batches(full_manifest: pd.DataFrame) -> dict[str, int]:
    counts = {}
    for filename, start, end in BATCHES:
        batch = full_manifest.iloc[start:end].copy()
        out = OUTPUT_DIR / filename
        batch.to_csv(out, index=False)
        counts[filename] = int(len(batch))
    return counts


def required_zip_paths(full_manifest: pd.DataFrame) -> list[str]:
    names = sorted(full_manifest["zip_filename"].dropna().astype(str).unique())
    return [str(ZIP_DIR / name) for name in names]


def write_run_cells(required_zips: list[str]) -> None:
    batch_names = [filename for filename, _, _ in BATCHES]
    zip_names = [Path(path).name for path in required_zips]
    RUN_CELLS_OUT.write_text(
        f'''# Phase 16E CzechLynx remaining Kaggle run cells.
# Copy cells into a Kaggle notebook. Do not use --allow-missing-models for formal scoring.

# %% [markdown]
# # Phase 16E CzechLynx remaining batches
# Runs only rows 20000-39759. Rows 0-19999 were already completed elsewhere.

# %% path setup
from pathlib import Path
import glob
import json
import os
import shutil
import subprocess
import sys

WORK = Path("/kaggle/working/phase16e_work")
EXTRACTED = WORK / "extracted_images"
OUT_ROOT = Path("/kaggle/working/phase16e_czechlynx_remaining_outputs")
DATASET_ROOTS = [Path("/kaggle/input"), Path("/kaggle/working")]
EXTRACTED.mkdir(parents=True, exist_ok=True)
OUT_ROOT.mkdir(parents=True, exist_ok=True)
print("WORK", WORK)

# %% check runner supports --allow-missing-models
runner = Path("/kaggle/working/run_phase16e_candidate_model_filter_colab.py")
if not runner.exists():
    runner = Path("run_phase16e_candidate_model_filter_colab.py")
assert runner.exists(), f"Runner not found: {{runner}}"
help_text = subprocess.check_output([sys.executable, str(runner), "--help"], text=True)
assert "--allow-missing-models" in help_text
print("Runner fail-fast version detected:", runner)

# %% install dependencies
subprocess.check_call([
    sys.executable,
    "-m",
    "pip",
    "install",
    "-q",
    "pandas",
    "pillow",
    "tqdm",
    "pyiqa",
    "open_clip_torch",
])

# %% import checks
import torch
import pyiqa
import open_clip
print("torch", torch.__version__)
print("cuda available", torch.cuda.is_available())
print("pyiqa ok", pyiqa.__name__)
print("open_clip ok", open_clip.__name__)

# %% unzip five CzechLynx zip files
required_zip_names = {zip_names!r}
found_zips = {{}}
for root in DATASET_ROOTS:
    for path in root.rglob("phase16e_czechlynx_images_part_*.zip"):
        found_zips[path.name] = path
missing = [name for name in required_zip_names if name not in found_zips]
assert not missing, f"Missing zip files in Kaggle input/working: {{missing}}"
for name in required_zip_names:
    path = found_zips[name]
    print("unzipping", path)
    subprocess.check_call(["unzip", "-q", "-o", str(path), "-d", str(EXTRACTED)])

# %% verify extracted count
images = sorted((EXTRACTED / "images/czechlynx").glob("*.jpg"))
print("extracted_count", len(images))
assert len(images) == 39760, len(images)

# %% locate batch manifests
batch_names = {batch_names!r}
batch_paths = []
for name in batch_names:
    candidates = list(Path("/kaggle/input").rglob(name)) + list(Path("/kaggle/working").rglob(name))
    assert candidates, f"Batch manifest not found: {{name}}"
    batch_paths.append(candidates[0])
print(batch_paths)

# %% run remaining batches with real-time stdout
device = "cuda" if torch.cuda.is_available() else "cpu"
for batch_path in batch_paths:
    batch_name = batch_path.stem
    out_dir = OUT_ROOT / batch_name
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(runner),
        "--manifest",
        str(batch_path),
        "--output-dir",
        str(out_dir),
        "--device",
        device,
    ]
    print("\\nRUN", " ".join(cmd), flush=True)
    process = subprocess.Popen(cmd)
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Batch failed {{batch_name}} return_code={{return_code}}")

# %% check completed scores
import pandas as pd
for batch_path in batch_paths:
    batch_name = batch_path.stem
    out_dir = OUT_ROOT / batch_name
    scores_path = out_dir / "phase16e_candidate_model_filter_scores.csv"
    audit_path = out_dir / "phase16e_candidate_model_filter_audit.json"
    assert scores_path.exists(), scores_path
    scores = pd.read_csv(scores_path)
    print("\\n", batch_name, "rows", len(scores))
    print("image_load_success", scores["image_load_success"].value_counts(dropna=False).to_dict())
    print("scoring_valid_for_selection", scores["scoring_valid_for_selection"].value_counts(dropna=False).to_dict())
    print("model_fallback_mode", scores["model_fallback_mode"].value_counts(dropna=False).to_dict())
    assert not scores["model_fallback_mode"].fillna(False).any()
    assert scores["scoring_valid_for_selection"].fillna(False).any()
    if audit_path.exists():
        print(json.load(open(audit_path)).get("scoring_valid_for_selection_counts"))

# %% zip each completed batch output for download
for batch_path in batch_paths:
    batch_name = batch_path.stem
    out_dir = OUT_ROOT / batch_name
    zip_base = Path("/kaggle/working") / batch_name
    archive = shutil.make_archive(str(zip_base), "zip", root_dir=str(out_dir))
    print("created", archive)
''',
        encoding="utf-8",
    )


def write_readme(required_zips: list[str], batch_counts: dict[str, int]) -> None:
    README_OUT.write_text(
        f"""# Phase 16E CzechLynx Kaggle Remaining Package

This package is only for running the remaining CzechLynx Phase 16E batches on
Kaggle. It does not rerun rows 0-19999, does not freeze final 3000, and does not
run recalibration.

## Already Completed Elsewhere

```text
czechlynx_batch_00000_04999
czechlynx_batch_05000_09999
czechlynx_batch_10000_14999
czechlynx_batch_15000_19999
```

## Remaining Kaggle Batches

```json
{json.dumps(batch_counts, indent=2)}
```

The batch files cover rows 20000-39759 only. Total remaining rows: {sum(batch_counts.values())}.

## Required External Zip Files

The large CzechLynx image zip files are not copied into this package. Upload
these files from `outputs/phase16/phase16e_czechlynx_direct_zips/` together with
this package as a Kaggle dataset:

```text
{chr(10).join(required_zips)}
```

## Formal Scoring Rule

Do not use `--allow-missing-models` for formal scoring. Formal outputs must have:

```text
scoring_valid_for_selection=true
model_fallback_mode=false
```

If dependency loading fails, the fail-fast runner must stop with a non-zero
return code. Fix the Kaggle environment instead of accepting fallback scores.

## After Kaggle Finishes

Download or save each completed batch output zip. Later, merge these Kaggle
outputs with the already completed Colab/Drive rows 0-19999. Recalibration
should run only after the full CzechLynx scores are merged.
""",
        encoding="utf-8",
    )


def build_audit(full_manifest: pd.DataFrame, batch_counts: dict[str, int], required_zips: list[str]) -> dict:
    runner_text = RUNNER_OUT.read_text(encoding="utf-8")
    sensitive_leaks = sorted(SENSITIVE_COLUMNS.intersection(full_manifest.columns))
    batch_total = int(sum(batch_counts.values()))
    audit = {
        "package_output_path": str(OUTPUT_DIR),
        "runner_copied_path": str(RUNNER_OUT),
        "runner_supports_allow_missing_models": "--allow-missing-models" in runner_text,
        "runner_failfast_markers_present": all(
            marker in runner_text
            for marker in [
                "raise RuntimeError(message)",
                "model_fallback_mode",
                "scoring_valid_for_selection",
            ]
        ),
        "full_czechlynx_rows": int(len(full_manifest)),
        "candidate_id_unique": bool(full_manifest["candidate_id"].is_unique),
        "source_mode_counts": {
            str(key): int(value)
            for key, value in full_manifest["source_mode"].value_counts(dropna=False).sort_index().items()
        },
        "image_uri_prefix_pass": bool(
            full_manifest["image_uri"].astype(str).str.startswith(KAGGLE_EXTRACT_ROOT).all()
        ),
        "remaining_batch_row_counts": batch_counts,
        "total_remaining_rows": batch_total,
        "expected_remaining_rows": EXPECTED_REMAINING_ROWS,
        "remaining_rows_match_expected": batch_total == EXPECTED_REMAINING_ROWS,
        "sensitive_columns_leaked": sensitive_leaks,
        "required_external_zip_paths": required_zips,
        "required_external_zip_exists": {path: Path(path).exists() for path in required_zips},
        "claim_boundary": "Kaggle remaining-batch package only; no final 3000 freeze and no recalibration",
    }
    return audit


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not RUNNER_SOURCE.exists():
        raise FileNotFoundError(RUNNER_SOURCE)
    shutil.copy2(RUNNER_SOURCE, RUNNER_OUT)

    full_manifest = build_runner_ready_manifest()
    full_manifest.to_csv(FULL_MANIFEST_OUT, index=False)
    batch_counts = write_batches(full_manifest)
    required_zips = required_zip_paths(full_manifest)
    write_run_cells(required_zips)
    write_readme(required_zips, batch_counts)
    audit = build_audit(full_manifest, batch_counts, required_zips)
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    if audit["full_czechlynx_rows"] != EXPECTED_FULL_ROWS:
        raise RuntimeError("Full CzechLynx row count mismatch")
    if audit["total_remaining_rows"] != EXPECTED_REMAINING_ROWS:
        raise RuntimeError("Remaining row count mismatch")
    if not audit["candidate_id_unique"]:
        raise RuntimeError("candidate_id is not unique")
    if audit["source_mode_counts"] != {"packaged_local": EXPECTED_FULL_ROWS}:
        raise RuntimeError(f"Unexpected source_mode distribution: {audit['source_mode_counts']}")
    if not audit["image_uri_prefix_pass"]:
        raise RuntimeError("image_uri prefix check failed")
    if audit["sensitive_columns_leaked"]:
        raise RuntimeError(f"Sensitive columns leaked: {audit['sensitive_columns_leaked']}")
    if not audit["runner_supports_allow_missing_models"]:
        raise RuntimeError("Runner does not support --allow-missing-models")

    print(f"PASS phase16e CzechLynx Kaggle remaining package rows={len(full_manifest)}")
    print(json.dumps({
        "remaining_batch_row_counts": batch_counts,
        "total_remaining_rows": audit["total_remaining_rows"],
        "required_external_zip_paths": required_zips,
    }, indent=2))
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
