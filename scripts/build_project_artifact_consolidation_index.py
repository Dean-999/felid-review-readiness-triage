#!/usr/bin/env python3
"""Build a non-destructive consolidation index for legacy-code16/17 outputs."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/project-governance/project-structure/artifact_consolidation_index"
INDEX_CSV = OUTPUT_DIR / "legacy-code16_legacy-code17_artifact_index.csv"
AUDIT_JSON = OUTPUT_DIR / "legacy-code16_legacy-code17_artifact_index_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

SCAN_ROOTS = [
    PROJECT_ROOT / "archive/pferi_v1/outputs/project-governance/safeguards-candidate-scoring",
    PROJECT_ROOT / "archive/pferi_v1/outputs/photo-selection/photo-entry-gates",
    PROJECT_ROOT / "archive/pferi_v1/outputs/photo-selection/bobcat-photo-selection",
    PROJECT_ROOT / "archive/pferi_v1/outputs/data-foundation/czechlynx-historical-validation/strict3000-supplement",
    PROJECT_ROOT / "archive/pferi_v1/outputs/photo-freeze/frozen-modeling-datasets/strict3000-freeze-20260701",
]

CANONICAL_MARKERS = {
    "bobcat-final3000-seed": "final_bobcat_3000_seed",
    "strict3000-supplement": "final_czechlynx_strict3000",
    "strict3000-freeze-20260701": "frozen_modeling_package",
    "czechlynx-real-pair-table": "prior_pair_contract",
    "czechlynx-calibrated-router": "prior_router_control",
}


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def classify(path: Path) -> tuple[str, str]:
    text = project_relative(path)
    for marker, role in CANONICAL_MARKERS.items():
        if marker in text:
            return "canonical_current", role
    if "/photo-selection/" in f"/{text}" and any(token in text for token in ["audit", "review", "clarity", "selected", "seed"]):
        return "selection_experiment_or_review", "legacy-code17_photo_selection_history"
    if "/safeguards-candidate-scoring/" in f"/{text}" and any(token in text for token in ["candidate-model-filter", "score", "recalibrated"]):
        return "model_filter_experiment", "legacy-code16_candidate_scoring_history"
    if "/safeguards-candidate-scoring/" in f"/{text}":
        return "legacy-code16_support", "legacy-code16_supporting_artifact"
    return "supporting_or_historical", "supporting_artifact"


def summarize_dir(path: Path) -> dict[str, Any]:
    files = [item for item in path.rglob("*") if item.is_file()]
    size_bytes = sum(item.stat().st_size for item in files)
    csv_count = sum(1 for item in files if item.suffix.lower() == ".csv")
    json_count = sum(1 for item in files if item.suffix.lower() == ".json")
    image_count = sum(1 for item in files if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    newest_mtime = max((item.stat().st_mtime for item in files), default=path.stat().st_mtime)
    category, active_role = classify(path)
    return {
        "path": project_relative(path),
        "category": category,
        "active_role": active_role,
        "file_count": len(files),
        "csv_count": csv_count,
        "json_count": json_count,
        "image_count": image_count,
        "size_bytes": size_bytes,
        "newest_mtime_utc": datetime.fromtimestamp(newest_mtime, timezone.utc).isoformat(timespec="seconds"),
        "consolidation_action": (
            "keep_as_canonical_entry" if category == "canonical_current"
            else "keep_historical_do_not_use_as_phase18_input"
        ),
    }


def build_index() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        rows.append(summarize_dir(root))
        for child in sorted(item for item in root.iterdir() if item.is_dir()):
            rows.append(summarize_dir(child))
    counts = Counter(row["category"] for row in rows)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scan_roots": [project_relative(root) for root in SCAN_ROOTS],
        "indexed_directories": len(rows),
        "category_counts": dict(sorted(counts.items())),
        "claim_boundary": (
            "Non-destructive structure index only. It does not move, delete, "
            "or revalidate images. Current modeling must use data/frozen/pferi_v2/ "
            "and the modeling-validation contracts."
        ),
    }
    return rows, audit


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "category",
        "active_role",
        "file_count",
        "csv_count",
        "json_count",
        "image_count",
        "size_bytes",
        "newest_mtime_utc",
        "consolidation_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    lines = [
        "# Legacy-Code16/17 Artifact Consolidation Index",
        "",
        "This is a non-destructive structure map. It explains which historical",
        "content directories are current canonical inputs and which are selection",
        "experiments or supporting history.",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in audit["category_counts"].items():
        lines.append(f"- `{category}`: {count}")
    lines.extend(["", "## Canonical Current Entries", ""])
    for row in rows:
        if row["category"] == "canonical_current":
            lines.append(f"- `{row['path']}` -> `{row['active_role']}`")
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "Do not use the many Phase17 selection-condition directories directly as",
            "modeling input. Use the final freeze and modeling contracts; use this index",
            "only as provenance/navigation.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, audit = build_index()
    write_csv(INDEX_CSV, rows)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(rows, audit)
    print("PASS artifact consolidation index")
    print(f"indexed_directories={len(rows)}")
    print(f"WROTE {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
