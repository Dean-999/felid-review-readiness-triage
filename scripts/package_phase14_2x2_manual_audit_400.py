#!/usr/bin/env python3
"""Package Phase 14 2x2 400-image manual audit calibration set."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_2x2_evidence_sets"
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_2x2_manual_audit_400"

SETS = {
    "bobcat_high_confidence": INPUT_DIR / "phase14_2x2_bobcat_high_confidence_3000.csv",
    "bobcat_low_evidence_stress": INPUT_DIR / "phase14_2x2_bobcat_low_evidence_stress_3000.csv",
    "czechlynx_high_confidence": INPUT_DIR / "phase14_2x2_czechlynx_high_confidence_3000.csv",
    "czechlynx_low_evidence_stress": INPUT_DIR / "phase14_2x2_czechlynx_low_evidence_stress_3000.csv",
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
    "evidence_tier",
    "evidence_role",
    "training_eligible",
    "stress_test_eligible",
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
    stem = source.stem[:36]
    return f"{row['audit_id']}__{stem}{suffix}"


def select_spread(table: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    if sample_size > len(table):
        raise ValueError(f"sample_size={sample_size} exceeds table rows={len(table)}")
    ordered = table.copy().reset_index(drop=True)
    if "identity_label" in ordered.columns and ordered["identity_label"].fillna("").astype(str).str.strip().ne("").any():
        ordered = ordered.sort_values(["identity_label", "auto_evidence_score", "evidence_image_path"]).reset_index(drop=True)
        parts = []
        depth = 0
        groups = {str(k): g.reset_index(drop=True) for k, g in ordered.groupby("identity_label", sort=True)}
        while len(parts) < sample_size:
            added = 0
            for identity in sorted(groups):
                group = groups[identity]
                if depth >= len(group):
                    continue
                parts.append(group.iloc[depth])
                added += 1
                if len(parts) >= sample_size:
                    break
            if added == 0:
                break
            depth += 1
        return pd.DataFrame(parts).reset_index(drop=True)

    sort_columns = [col for col in ["location_id", "year", "auto_evidence_score", "evidence_image_path"] if col in ordered.columns]
    ordered = ordered.sort_values(sort_columns).reset_index(drop=True)
    step = len(ordered) / sample_size
    indices = [min(int(i * step), len(ordered) - 1) for i in range(sample_size)]
    return ordered.iloc[indices].copy().reset_index(drop=True)


def package_zip(zip_path: Path, manifest_path: Path, rows: pd.DataFrame) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, arcname=manifest_path.name)
        for _, row in rows.iterrows():
            image_path = resolve(row["evidence_image_path"])
            zf.write(image_path, arcname=f"images/{row['review_image_file']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--sample-size-per-quadrant", type=int, default=100)
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[pd.DataFrame] = []
    package_rows: list[dict[str, Any]] = []
    for quadrant, path in SETS.items():
        table = pd.read_csv(path).copy()
        sample = select_spread(table, args.sample_size_per_quadrant)
        sample.insert(0, "audit_order", range(1, len(sample) + 1))
        sample.insert(0, "audit_quadrant", quadrant)
        sample.insert(0, "audit_id", [f"{quadrant}_{i:03d}" for i in range(1, len(sample) + 1)])
        sample["review_image_file"] = sample.apply(safe_image_name, axis=1)
        sample["review_image_path_in_zip"] = "images/" + sample["review_image_file"]

        missing = [str(resolve(path_text)) for path_text in sample["evidence_image_path"] if not resolve(path_text).exists()]
        if missing:
            raise FileNotFoundError(f"{quadrant} missing images: {len(missing)} first={missing[0]}")

        columns = [col for col in KEEP_COLUMNS if col in sample.columns]
        reference = sample[columns].copy()
        blank = reference.copy()
        for col in MANUAL_COLUMNS:
            blank[col] = ""

        quadrant_dir = out_dir / quadrant
        quadrant_dir.mkdir(parents=True, exist_ok=True)
        reference_path = quadrant_dir / f"{quadrant}_ai_reference.csv"
        blank_path = quadrant_dir / f"{quadrant}_manual_blank.csv"
        zip_path = quadrant_dir / f"{quadrant}_images.zip"
        reference.to_csv(reference_path, index=False)
        blank.to_csv(blank_path, index=False)
        package_zip(zip_path, reference_path, sample)

        all_rows.append(sample)
        package_rows.append(
            {
                "audit_quadrant": quadrant,
                "source_csv": rel(path),
                "row_count": int(len(sample)),
                "reference_csv": rel(reference_path),
                "blank_csv": rel(blank_path),
                "zip_file": rel(zip_path),
                "bucket_counts": {
                    str(k): int(v) for k, v in sample["human_review_bucket"].value_counts().sort_index().items()
                },
                "confidence_counts": {
                    str(k): int(v) for k, v in sample["human_review_confidence"].value_counts().sort_index().items()
                },
                "pool_source_counts": {
                    str(k): int(v) for k, v in sample["pool_source"].value_counts().sort_index().items()
                },
            }
        )

    combined = pd.concat(all_rows, ignore_index=True)
    combined_reference = out_dir / "phase14_2x2_manual_audit_400_ai_reference.csv"
    combined_blank = out_dir / "phase14_2x2_manual_audit_400_blank.csv"
    combined[[col for col in KEEP_COLUMNS if col in combined.columns]].to_csv(combined_reference, index=False)
    combined_blank_frame = pd.read_csv(combined_reference)
    for col in MANUAL_COLUMNS:
        combined_blank_frame[col] = ""
    combined_blank_frame.to_csv(combined_blank, index=False)

    index_csv = out_dir / "phase14_2x2_manual_audit_400_package_index.csv"
    pd.DataFrame(package_rows).to_csv(index_csv, index=False)
    audit = {
        "output_dir": rel(out_dir),
        "row_count": int(len(combined)),
        "sample_size_per_quadrant": int(args.sample_size_per_quadrant),
        "quadrant_count": int(len(package_rows)),
        "combined_reference_csv": rel(combined_reference),
        "combined_blank_csv": rel(combined_blank),
        "package_index_csv": rel(index_csv),
        "packages": package_rows,
        "unique_image_paths": int(combined["evidence_image_path"].astype(str).nunique()),
        "duplicate_image_paths": int(combined["evidence_image_path"].astype(str).duplicated().sum()),
        "claim_boundary": "manual calibration audit package for AI-assisted 2x2 evidence routing",
    }
    audit_path = out_dir / "phase14_2x2_manual_audit_400_package_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 2x2 manual audit package "
        f"rows={len(combined)} quadrants={len(package_rows)} output={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
