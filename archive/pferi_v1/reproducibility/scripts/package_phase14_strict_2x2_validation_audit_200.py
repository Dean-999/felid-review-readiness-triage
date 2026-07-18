#!/usr/bin/env python3
"""Package 200-image validation audit for strict Phase 14 2x2 sets."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets"
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_validation_audit_200"

SETS = {
    "bobcat_high_confidence": INPUT_DIR / "phase14_strict_2x2_bobcat_high_confidence_3000.csv",
    "bobcat_low_evidence_stress": INPUT_DIR / "phase14_strict_2x2_bobcat_low_evidence_stress_3000.csv",
    "czechlynx_high_confidence": INPUT_DIR / "phase14_strict_2x2_czechlynx_high_confidence_3000.csv",
    "czechlynx_low_evidence_stress": INPUT_DIR / "phase14_strict_2x2_czechlynx_low_evidence_stress_3000.csv",
}

MANUAL_COLUMNS = [
    "manual_pattern_visibility",
    "manual_side_flank_visibility",
    "manual_body_visibility",
    "manual_blur_level",
    "manual_occlusion_level",
    "manual_background_complexity",
    "manual_modified_background",
    "manual_review_bucket",
    "manual_review_confidence",
    "manual_training_eligible",
    "manual_stress_test_eligible",
    "manual_evidence_tier",
    "manual_error_type",
    "manual_notes",
]

KEEP_COLUMNS = [
    "audit_id",
    "audit_quadrant",
    "audit_order",
    "review_image_file",
    "review_image_path_in_zip",
    "dataset_role",
    "environment_context",
    "strict_evidence_tier",
    "strict_evidence_role",
    "strict_training_eligible",
    "strict_stress_test_eligible",
    "human_review_bucket",
    "human_review_confidence",
    "human_pattern_visibility",
    "human_side_flank_visibility",
    "human_body_visibility",
    "human_blur_level",
    "human_occlusion_level",
    "human_background_complexity",
    "human_modified_background",
    "auto_evidence_score",
    "auto_quality_score",
    "pool_source",
    "identity_label",
    "location_id",
    "year",
    "evidence_image_path",
]


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def safe_image_name(row: pd.Series) -> str:
    source = Path(str(row["evidence_image_path"]))
    suffix = source.suffix.lower() or ".jpg"
    return f"{row['audit_id']}__{source.stem[:36]}{suffix}"


def spread_sample(table: pd.DataFrame, n: int) -> pd.DataFrame:
    if len(table) < n:
        raise ValueError(f"table has {len(table)} rows, requested {n}")
    sort_cols = [c for c in ["identity_label", "location_id", "auto_evidence_score", "evidence_image_path"] if c in table.columns]
    ordered = table.sort_values(sort_cols).reset_index(drop=True)
    step = len(ordered) / n
    idx = [min(int(i * step), len(ordered) - 1) for i in range(n)]
    return ordered.iloc[idx].copy().reset_index(drop=True)


def write_zip(zip_path: Path, manifest_path: Path, rows: pd.DataFrame) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, arcname=manifest_path.name)
        for _, row in rows.iterrows():
            zf.write(resolve(row["evidence_image_path"]), arcname=f"images/{row['review_image_file']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--sample-size-per-quadrant", type=int, default=50)
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_samples: list[pd.DataFrame] = []
    package_rows: list[dict[str, Any]] = []

    for quadrant, source_path in SETS.items():
        table = pd.read_csv(source_path, low_memory=False)
        sample = spread_sample(table, args.sample_size_per_quadrant)
        sample.insert(0, "audit_order", range(1, len(sample) + 1))
        sample.insert(0, "audit_quadrant", quadrant)
        sample.insert(0, "audit_id", [f"strict_{quadrant}_{i:03d}" for i in range(1, len(sample) + 1)])
        sample["review_image_file"] = sample.apply(safe_image_name, axis=1)
        sample["review_image_path_in_zip"] = "images/" + sample["review_image_file"]

        missing = [str(resolve(p)) for p in sample["evidence_image_path"] if not resolve(p).exists()]
        if missing:
            raise FileNotFoundError(f"{quadrant} missing images: {len(missing)} first={missing[0]}")

        columns = [c for c in KEEP_COLUMNS if c in sample.columns]
        reference = sample[columns].copy()
        blank = reference.copy()
        for col in MANUAL_COLUMNS:
            blank[col] = ""

        qdir = out_dir / quadrant
        qdir.mkdir(parents=True, exist_ok=True)
        reference_path = qdir / f"{quadrant}_strict_ai_reference.csv"
        blank_path = qdir / f"{quadrant}_strict_manual_blank.csv"
        zip_path = qdir / f"{quadrant}_strict_images.zip"
        reference.to_csv(reference_path, index=False)
        blank.to_csv(blank_path, index=False)
        write_zip(zip_path, reference_path, sample)

        all_samples.append(sample)
        package_rows.append(
            {
                "audit_quadrant": quadrant,
                "source_csv": rel(source_path),
                "row_count": int(len(sample)),
                "reference_csv": rel(reference_path),
                "blank_csv": rel(blank_path),
                "zip_file": rel(zip_path),
                "bucket_counts": {str(k): int(v) for k, v in sample["human_review_bucket"].value_counts().sort_index().items()},
                "pattern_counts": {str(k): int(v) for k, v in sample["human_pattern_visibility"].value_counts().sort_index().items()},
                "body_counts": {str(k): int(v) for k, v in sample["human_body_visibility"].value_counts().sort_index().items()},
            }
        )

    combined = pd.concat(all_samples, ignore_index=True)
    combined_reference = out_dir / "phase14_strict_2x2_validation_audit_200_ai_reference.csv"
    combined_blank = out_dir / "phase14_strict_2x2_validation_audit_200_blank.csv"
    combined[[c for c in KEEP_COLUMNS if c in combined.columns]].to_csv(combined_reference, index=False)
    blank = pd.read_csv(combined_reference)
    for col in MANUAL_COLUMNS:
        blank[col] = ""
    blank.to_csv(combined_blank, index=False)
    index_path = out_dir / "phase14_strict_2x2_validation_audit_200_package_index.csv"
    pd.DataFrame(package_rows).to_csv(index_path, index=False)
    audit = {
        "output_dir": rel(out_dir),
        "row_count": int(len(combined)),
        "sample_size_per_quadrant": int(args.sample_size_per_quadrant),
        "combined_reference_csv": rel(combined_reference),
        "combined_blank_csv": rel(combined_blank),
        "package_index_csv": rel(index_path),
        "packages": package_rows,
        "unique_image_paths": int(combined["evidence_image_path"].astype(str).nunique()),
        "duplicate_image_paths": int(combined["evidence_image_path"].astype(str).duplicated().sum()),
        "claim_boundary": "validation audit for strict 2x2 rules; intended to test 90_percent_precision_target",
    }
    audit_path = out_dir / "phase14_strict_2x2_validation_audit_200_package_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS phase14 strict validation audit package rows={len(combined)} output={rel(out_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
