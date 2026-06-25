#!/usr/bin/env python3
"""Package Phase 14 CzechLynx refined manual-review rows into 100-image zip batches."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
import zipfile

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IN_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_INPUT = IN_DIR / "czechlynx_phase14_3000_refined_needs_manual_check.csv"
DEFAULT_OUT_DIR = IN_DIR / "czechlynx_phase14_1341_manual_review_zip_batches"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def safe_name(row: pd.Series) -> str:
    source = Path(str(row["review_image_path_local"]))
    suffix = source.suffix.lower() or ".jpg"
    return (
        f"review_{int(row['phase14_review_index']):04d}"
        f"__{str(row['expanded_image_id'])}"
        f"__{source.stem[:32]}{suffix}"
    )


def batch_id(i: int) -> str:
    return f"batch_{i:02d}"


def write_zip(zip_path: Path, batch: pd.DataFrame, manifest_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, arcname=manifest_path.name)
        for _, row in batch.iterrows():
            zf.write(resolve(str(row["review_image_path_local"])), arcname=f"images/{row['review_image_file']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--name-prefix", default=None)
    args = parser.parse_args()

    input_path = resolve(args.input)
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(input_path).copy()
    name_prefix = args.name_prefix or f"czechlynx_phase14_{len(table)}"
    table = table.sort_values(
        ["confidence_refinement_reason", "auto_evidence_score", "phase14_review_index"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
    table.insert(0, "manual_review_order", range(1, len(table) + 1))
    table["review_package_id"] = [batch_id(math.floor(i / args.batch_size) + 1) for i in range(len(table))]
    table["review_image_file"] = table.apply(safe_name, axis=1)
    table["review_image_path_in_zip"] = "images/" + table["review_image_file"]
    table["review_zip_file"] = table["review_package_id"] + ".zip"
    table["manual_correction_status"] = "pending"
    table["manual_reviewer_notes"] = ""

    missing = [str(p) for p in table["review_image_path_local"].map(resolve) if not p.exists()]
    if missing:
        raise FileNotFoundError(f"missing images: {len(missing)} first={missing[0]}")

    full_csv = output_dir / f"{name_prefix}_manual_review_all.csv"
    table.to_csv(full_csv, index=False)
    blank = table.copy()
    manual_cols = [
        "manual_pattern_visibility",
        "manual_side_flank_visibility",
        "manual_body_visibility",
        "manual_blur_level",
        "manual_occlusion_level",
        "manual_background_complexity",
        "manual_modified_background",
        "manual_review_bucket",
        "manual_review_confidence",
        "manual_correction_status",
        "manual_reviewer_notes",
    ]
    for col in manual_cols:
        blank[col] = ""
    blank_csv = output_dir / f"{name_prefix}_manual_blank_template.csv"
    blank.to_csv(blank_csv, index=False)

    index_rows: list[dict[str, Any]] = []
    for idx, (pid, batch) in enumerate(table.groupby("review_package_id", sort=False), start=1):
        manifest = output_dir / f"{pid}_manifest.csv"
        zip_path = output_dir / f"{pid}.zip"
        batch.to_csv(manifest, index=False)
        write_zip(zip_path, batch, manifest)
        index_rows.append(
            {
                "review_package_id": pid,
                "zip_file": zip_path.name,
                "manifest_file": manifest.name,
                "row_count": int(len(batch)),
                "first_manual_review_order": int(batch["manual_review_order"].min()),
                "last_manual_review_order": int(batch["manual_review_order"].max()),
                "reason_counts": {
                    str(k): int(v)
                    for k, v in batch["confidence_refinement_reason"].value_counts().sort_index().items()
                },
            }
        )
    index = pd.DataFrame(index_rows)
    index.to_csv(output_dir / f"{name_prefix}_zip_batch_index.csv", index=False)
    (output_dir / f"{name_prefix}_zip_batch_index.json").write_text(
        json.dumps(index_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    audit = {
        "input": str(input_path.relative_to(PROJECT_ROOT)),
        "output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        "row_count": int(len(table)),
        "zip_count": int(len(index)),
        "batch_size": int(args.batch_size),
        "missing_image_count": 0,
        "claim_boundary": "manual_review_package_for_czechlynx_ai_first_pass_expansion",
    }
    (output_dir / f"{name_prefix}_manual_review_package_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 CzechLynx manual review packages "
        f"rows={len(table)} zips={len(index)} output={output_dir.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
