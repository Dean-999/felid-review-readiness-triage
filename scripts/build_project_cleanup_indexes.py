#!/usr/bin/env python3
"""Build non-destructive indexes for repeated review and selection outputs."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/project-governance/project-structure/cleanup_indexes"
REVIEW_INDEX_CSV = OUTPUT_DIR / "review_packet_index.csv"
PHOTO_GATE_INDEX_CSV = OUTPUT_DIR / "photo_selection_gate_index.csv"
AUDIT_JSON = OUTPUT_DIR / "cleanup_indexes_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

REVIEW_ROOTS = [
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/manual-review-audits",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation",
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/blind-reliability-packet",
]
PHOTO_GATE_ROOT = PROJECT_ROOT / "archive/pferi_v1/outputs/photo-selection/photo-entry-gates"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def summarize_directory(path: Path) -> dict[str, int]:
    files = [item for item in path.rglob("*") if item.is_file() and item.name != ".DS_Store"]
    return {
        "file_count": len(files),
        "csv_count": sum(1 for item in files if item.suffix.lower() == ".csv"),
        "json_count": sum(1 for item in files if item.suffix.lower() == ".json"),
        "md_count": sum(1 for item in files if item.suffix.lower() == ".md"),
        "html_count": sum(1 for item in files if item.suffix.lower() == ".html"),
        "image_count": sum(1 for item in files if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}),
        "size_bytes": sum(item.stat().st_size for item in files),
    }


def classify_review_packet(path: Path) -> tuple[str, str]:
    name = path.name
    text = project_relative(path)
    if "identity-balanced-analysis" in text:
        return "final_claim_evidence", "identity-balanced reviewability confirmation"
    if "descriptor-controlled-analysis" in text:
        return "supporting_claim_evidence", "descriptor-controlled reviewability analysis"
    if "reviewer-agreement-analysis" in text or "agreement-analysis" in text:
        return "reviewer_reliability", "reviewer agreement analysis"
    if "manual-review-audits" in text:
        return "manual_review_attestation", "manual review completion and attestation"
    if "streamlit" in name or "review-packet" in name or "external-reviews" in text:
        return "review_working_packet", "human review packet or Streamlit working folder"
    if "targeted" in name:
        return "mechanism_probe", "targeted reviewability mechanism probe"
    if "full-queue" in name:
        return "full_queue_sample", "full-queue stratified sample"
    if "adjudication" in name:
        return "adjudication_packet", "reviewer-disagreement adjudication packet"
    return "analysis_or_support", "pair-level validation support output"


def classify_photo_gate(path: Path) -> tuple[str, str]:
    name = path.name
    if name == "bobcat-final3000-seed":
        return "final_seed", "accepted Bobcat final 3000 seed provenance"
    if name in {"bobcat-clarity-gate", "bobcat-clarity-review", "bobcat-manual-audit-gate"}:
        return "accepted_gate_or_review", "accepted Bobcat clarity/manual review gate"
    if name in {"bobcat-provisional-3000", "bobcat-transfer-stress", "czechlynx-review-utility"}:
        return "supporting_validation", "supporting review utility or transfer-stress validation"
    if name in {"external-source-probe", "inat-auto-selected-3000", "inat-human-calibrated-3000"}:
        return "candidate_attempt", "candidate source-selection attempt, not final freeze"
    if "audit" in name or "review" in name:
        return "working_review", "manual spot-check or working review folder"
    if "queue" in name or "rescore" in name or "probe" in name:
        return "candidate_queue", "candidate queue or source probe"
    return "diagnostic_or_historical", "photo-selection diagnostic or historical output"


def directory_rows(roots: list[Path], classifier) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(item for item in root.iterdir() if item.is_dir()):
            category, role = classifier(path)
            summary = summarize_directory(path)
            rows.append(
                {
                    "path": project_relative(path),
                    "category": category,
                    "role": role,
                    "safe_action": "index_only_do_not_move_or_delete",
                    **summary,
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "category",
        "role",
        "safe_action",
        "file_count",
        "csv_count",
        "json_count",
        "md_count",
        "html_count",
        "image_count",
        "size_bytes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_report(review_rows: list[dict[str, Any]], photo_rows: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    lines = [
        "# Cleanup Indexes",
        "",
        "These indexes consolidate navigation for repeated review-packet and",
        "photo-selection outputs without moving or deleting scientific artifacts.",
        "",
        "## Outputs",
        "",
        f"- Review packets: `{project_relative(REVIEW_INDEX_CSV)}`",
        f"- Photo-selection gates: `{project_relative(PHOTO_GATE_INDEX_CSV)}`",
        f"- Audit: `{project_relative(AUDIT_JSON)}`",
        "",
        "## Review Packet Categories",
        "",
    ]
    for category, count in sorted(Counter(row["category"] for row in review_rows).items()):
        lines.append(f"- `{category}`: {count}")
    lines.extend(["", "## Photo-Selection Categories", ""])
    for category, count in sorted(Counter(row["category"] for row in photo_rows).items()):
        lines.append(f"- `{category}`: {count}")
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "Use these indexes as the merged entry point. The indexed directories",
            "remain provenance unless a separate promotion document names them as",
            "current final inputs.",
            "",
            f"Status: `{audit['status']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    review_rows = directory_rows(REVIEW_ROOTS, classify_review_packet)
    photo_rows = directory_rows([PHOTO_GATE_ROOT], classify_photo_gate)
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS",
        "review_packet_rows": len(review_rows),
        "photo_selection_gate_rows": len(photo_rows),
        "review_category_counts": dict(sorted(Counter(row["category"] for row in review_rows).items())),
        "photo_gate_category_counts": dict(sorted(Counter(row["category"] for row in photo_rows).items())),
        "claim_boundary": "Index-only cleanup. Does not move, delete, or reinterpret scientific artifacts.",
    }
    write_csv(REVIEW_INDEX_CSV, review_rows)
    write_csv(PHOTO_GATE_INDEX_CSV, photo_rows)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(review_rows, photo_rows, audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
