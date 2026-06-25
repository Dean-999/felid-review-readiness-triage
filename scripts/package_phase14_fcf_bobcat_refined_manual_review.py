#!/usr/bin/env python3
"""Package refined low-confidence FCF bobcat images into 100-image review zips."""

from __future__ import annotations

import argparse
import json
import math
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/review_batches"
DEFAULT_INPUT = REVIEW_DIR / "fcf_bobcat_3000_refined_needs_manual_check.csv"
DEFAULT_OUT_DIR = REVIEW_DIR / "refined_manual_review_1126_zip_batches"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def safe_image_name(row: pd.Series) -> str:
    source = Path(str(row["local_relative_path"]))
    suffix = source.suffix.lower() or ".jpg"
    return (
        f"review_{int(row['review_index']):04d}"
        f"__sample_{int(row['sample_index']):04d}"
        f"__{source.stem[:40]}{suffix}"
    )


def package_id(batch_number: int) -> str:
    return f"batch_{batch_number:02d}"


def write_zip(zip_path: Path, batch: pd.DataFrame, manifest_name: str) -> None:
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_name, arcname=Path(manifest_name).name)
        for _, row in batch.iterrows():
            source = resolve(str(row["local_relative_path"]))
            arcname = f"images/{row['review_image_file']}"
            zf.write(source, arcname=arcname)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    input_path = resolve(args.input)
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    table = pd.read_csv(input_path).copy()
    table = table.sort_values(
        ["confidence_refinement_reason", "auto_evidence_score", "review_index"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
    table.insert(0, "manual_review_order", range(1, len(table) + 1))
    table["review_package_id"] = [
        package_id(math.floor(i / args.batch_size) + 1) for i in range(len(table))
    ]
    table["review_image_file"] = table.apply(safe_image_name, axis=1)
    table["review_image_path_in_zip"] = "images/" + table["review_image_file"]
    table["review_zip_file"] = table["review_package_id"] + ".zip"
    table["manual_correction_status"] = "pending"
    table["manual_reviewer_notes"] = ""

    missing = [
        str(path)
        for path in table["local_relative_path"].map(resolve)
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(f"missing image files: {len(missing)} first={missing[0]}")

    full_csv = output_dir / "fcf_bobcat_1126_refined_manual_review_all.csv"
    table.to_csv(full_csv, index=False)

    package_rows: list[dict[str, Any]] = []
    for batch_number, (_, batch) in enumerate(table.groupby("review_package_id", sort=False), start=1):
        pid = package_id(batch_number)
        batch_csv = output_dir / f"{pid}_manifest.csv"
        zip_path = output_dir / f"{pid}.zip"
        batch.to_csv(batch_csv, index=False)
        write_zip(zip_path, batch, str(batch_csv))
        package_rows.append(
            {
                "review_package_id": pid,
                "zip_file": zip_path.name,
                "manifest_file": batch_csv.name,
                "row_count": int(len(batch)),
                "first_manual_review_order": int(batch["manual_review_order"].min()),
                "last_manual_review_order": int(batch["manual_review_order"].max()),
                "reason_counts": {
                    str(k): int(v)
                    for k, v in batch["confidence_refinement_reason"].value_counts().sort_index().items()
                },
            }
        )

    index_csv = output_dir / "fcf_bobcat_1126_zip_batch_index.csv"
    index_json = output_dir / "fcf_bobcat_1126_zip_batch_index.json"
    pd.DataFrame(package_rows).to_csv(index_csv, index=False)
    index_json.write_text(json.dumps(package_rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    audit = {
        "input": str(input_path.relative_to(PROJECT_ROOT)),
        "output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        "full_csv": full_csv.name,
        "row_count": int(len(table)),
        "batch_size": int(args.batch_size),
        "zip_count": int(len(package_rows)),
        "missing_image_count": 0,
        "reason_counts": {
            str(k): int(v)
            for k, v in table["confidence_refinement_reason"].value_counts().sort_index().items()
        },
        "claim_boundary": "manual_review_package_for_low_confidence_ai_labels_not_ground_truth",
    }
    audit_path = output_dir / "fcf_bobcat_1126_manual_review_package_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "PASS phase14 FCF bobcat manual review zip packages "
        f"rows={len(table)} zips={len(package_rows)} output={output_dir.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
