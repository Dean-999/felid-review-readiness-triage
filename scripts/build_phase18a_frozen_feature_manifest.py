#!/usr/bin/env python3
"""Build the Phase18A image-level feature manifest from the frozen package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    Image = None
    ImageOps = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase18/phase18a_frozen_feature_manifest"

OUTPUT_COLUMNS = [
    "phase18_image_id",
    "species",
    "freeze_rank",
    "modeling_role",
    "train_eval_eligible",
    "has_known_identity",
    "identity_label",
    "frozen_image_path",
    "frozen_file_name",
    "sha256",
    "sha256_verified",
    "bytes",
    "bytes_verified",
    "decode_status",
    "decode_width",
    "decode_height",
    "manifest_width",
    "manifest_height",
    "megapixels",
    "min_dimension",
    "max_dimension",
    "aspect_ratio",
    "source_status",
    "source_quality_gate",
    "source_candidate_id",
    "source_manifest",
    "license",
    "attribution",
    "algorithm_entry_eligible",
    "claim_boundary",
]


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_image(path: Path) -> tuple[str, int | None, int | None]:
    if Image is None:
        return "not_checked_pillow_unavailable", None, None
    try:
        with Image.open(path) as image:
            if ImageOps is not None:
                image = ImageOps.exif_transpose(image)
            width, height = image.size
            image.verify()
        return "ok", int(width), int(height)
    except Exception as error:
        return f"decode_failed:{type(error).__name__}:{str(error)[:120]}", None, None


def modeling_role(species: str) -> str:
    if species == "czechlynx":
        return "czechlynx_known_id"
    if species == "bobcat":
        return "bobcat_unlabeled_transfer"
    return "unknown"


def build_row(row: dict[str, str]) -> dict[str, Any]:
    species = row.get("species", "").strip()
    rank = int(row.get("freeze_rank", "0") or 0)
    image_path = resolve_path(row.get("frozen_image_path", ""))
    actual_sha256 = sha256_file(image_path) if image_path.exists() else ""
    actual_bytes = image_path.stat().st_size if image_path.exists() else -1
    decode_status, width, height = decode_image(image_path)
    identity_label = row.get("source_identity_label", "").strip()
    role = modeling_role(species)
    has_known_identity = species == "czechlynx" and bool(identity_label)
    algorithm_entry_eligible = (
        image_path.exists()
        and actual_sha256 == row.get("sha256", "")
        and str(actual_bytes) == str(row.get("bytes", ""))
        and decode_status == "ok"
    )
    min_dimension = min(width, height) if width and height else ""
    max_dimension = max(width, height) if width and height else ""
    aspect_ratio = round(width / height, 6) if width and height else ""
    megapixels = round((width * height) / 1_000_000, 6) if width and height else ""
    return {
        "phase18_image_id": f"phase18a_{species}_{rank:04d}",
        "species": species,
        "freeze_rank": rank,
        "modeling_role": role,
        "train_eval_eligible": "yes" if has_known_identity else "no",
        "has_known_identity": "yes" if has_known_identity else "no",
        "identity_label": identity_label,
        "frozen_image_path": project_relative(image_path),
        "frozen_file_name": row.get("frozen_file_name", ""),
        "sha256": row.get("sha256", ""),
        "sha256_verified": "yes" if actual_sha256 == row.get("sha256", "") else "no",
        "bytes": row.get("bytes", ""),
        "bytes_verified": "yes" if str(actual_bytes) == str(row.get("bytes", "")) else "no",
        "decode_status": decode_status,
        "decode_width": width or "",
        "decode_height": height or "",
        "manifest_width": row.get("image_width", ""),
        "manifest_height": row.get("image_height", ""),
        "megapixels": megapixels,
        "min_dimension": min_dimension,
        "max_dimension": max_dimension,
        "aspect_ratio": aspect_ratio,
        "source_status": row.get("source_status", ""),
        "source_quality_gate": row.get("source_quality_gate", ""),
        "source_candidate_id": row.get("source_candidate_id", ""),
        "source_manifest": row.get("source_manifest", ""),
        "license": row.get("license", ""),
        "attribution": row.get("attribution", ""),
        "algorithm_entry_eligible": "yes" if algorithm_entry_eligible else "no",
        "claim_boundary": (
            "image-level frozen feature manifest only; descriptor extraction, "
            "pair construction, and identity evaluation are later Phase18 slices"
        ),
    }


def build_phase18a(input_csv: Path, output_dir: Path) -> dict[str, Any]:
    source_rows = read_csv(input_csv)
    output_rows = [build_row(row) for row in source_rows]
    manifest_csv = output_dir / "phase18a_frozen_image_feature_manifest.csv"
    audit_json = output_dir / "phase18a_frozen_image_feature_manifest_audit.json"
    report_md = output_dir / "README.md"
    write_csv(manifest_csv, output_rows, OUTPUT_COLUMNS)

    species_counts = Counter(row["species"] for row in output_rows)
    role_counts = Counter(row["modeling_role"] for row in output_rows)
    decode_counts = Counter(row["decode_status"] for row in output_rows)
    eligible_counts = Counter(row["algorithm_entry_eligible"] for row in output_rows)
    identity_counts = Counter(row["has_known_identity"] for row in output_rows)
    failed_rows = [
        row["phase18_image_id"]
        for row in output_rows
        if row["algorithm_entry_eligible"] != "yes"
    ]
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_csv": project_relative(input_csv),
        "output_manifest": project_relative(manifest_csv),
        "source_rows": len(source_rows),
        "output_rows": len(output_rows),
        "species_counts": dict(sorted(species_counts.items())),
        "modeling_role_counts": dict(sorted(role_counts.items())),
        "decode_status_counts": dict(sorted(decode_counts.items())),
        "algorithm_entry_eligible_counts": dict(sorted(eligible_counts.items())),
        "has_known_identity_counts": dict(sorted(identity_counts.items())),
        "failed_algorithm_entry_rows": failed_rows[:50],
        "failed_algorithm_entry_count": len(failed_rows),
        "claim_boundary": "Phase18A prepares image-level frozen features only.",
    }
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_md, audit)
    return audit


def write_report(path: Path, audit: dict[str, Any]) -> None:
    lines = [
        "# Phase18A Frozen Image Feature Manifest",
        "",
        "This manifest is the first algorithm-entry table derived from the frozen",
        "Phase17 strict 3,000 x 2 package. It preserves the image hash boundary and",
        "separates CzechLynx known-ID evaluation from Bobcat unlabeled transfer use.",
        "",
        "## Counts",
        "",
        f"- Rows: {audit['output_rows']}",
        f"- Species: `{audit['species_counts']}`",
        f"- Modeling roles: `{audit['modeling_role_counts']}`",
        f"- Decode status: `{audit['decode_status_counts']}`",
        f"- Algorithm-entry eligibility: `{audit['algorithm_entry_eligible_counts']}`",
        f"- Known identity: `{audit['has_known_identity_counts']}`",
        "",
        "## Boundary",
        "",
        "This is not descriptor extraction, pair modeling, or identity validation.",
        "Phase18B/C must build those outputs from this manifest.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18a(args.input_csv, args.output_dir)
    failed = audit["failed_algorithm_entry_count"]
    if failed:
        print("FAIL phase18a frozen feature manifest")
        print(f"failed_algorithm_entry_count={failed}")
        return 1
    print("PASS phase18a frozen feature manifest")
    print(f"output_rows={audit['output_rows']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
