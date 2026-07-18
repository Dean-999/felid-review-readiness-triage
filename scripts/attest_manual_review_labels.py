#!/usr/bin/env python3
"""Attest completed manual review labels and clean misleading proxy notes.

This script does not change label decisions. It adds provenance columns and
normalizes notes that were inherited from review-tool templates.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/manual-review-audits"
AUDIT_JSON = OUTPUT_DIR / "manual_review_attested_audit.json"
AUDIT_MD = OUTPUT_DIR / "manual_review_attested_audit.md"

ATTESTATION_BASIS = (
    "User attested in project chat on 2026-07-08 that these labels were manually reviewed; "
    "automated reference fields were available only as review aids and are not the label source."
)

TABLES = {
    "feature_varied": {
        "path": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/feature-varied-validation-packet/feature_varied_validation_review_working.csv",
        "id_column": "feature_varied_id",
        "status_column": "target_review_ready",
        "complete_values": {"yes", "no", "uncertain"},
        "label_columns": ["target_review_ready", "target_not_ready_reason", "target_secondary_reason"],
    },
    "internal_reason": {
        "path": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/reason-label-enrichment/reason_label_enrichment_review_working.csv",
        "id_column": "enrichment_id",
        "status_column": "reason_label_review_status",
        "complete_values": {"complete"},
        "label_columns": ["target_primary_reason", "target_secondary_reason", "target_body_region_visible"],
    },
    "online_supplement": {
        "path": PROJECT_ROOT
        / "archive/pferi_v1/outputs/modeling-validation/reason-label-enrichment/online-supplement/online_reason_label_review_working.csv",
        "id_column": "online_enrichment_id",
        "status_column": "online_reason_label_review_status",
        "complete_values": {"complete"},
        "label_columns": ["target_review_ready", "target_primary_reason", "target_secondary_reason"],
    },
}

PROVENANCE_COLUMNS = [
    "manual_review_attested",
    "manual_review_attested_by",
    "manual_review_attested_at_utc",
    "manual_review_attestation_basis",
    "label_use_status",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def normalize_notes(table_name: str, row: dict[str, str]) -> str:
    current = str(row.get("target_notes", "")).strip()
    if table_name == "feature_varied":
        return current
    if table_name == "internal_reason":
        primary = row.get("target_primary_reason", "").strip()
        if not primary:
            return "Human reviewer confirmed this control row has no not-ready reason."
        return (
            "Human reviewer assigned the primary reason after pair-level image review; "
            "suggested reference fields were used only as supporting metadata."
        )
    if table_name == "online_supplement":
        readiness = row.get("target_review_ready", "").strip()
        primary = row.get("target_primary_reason", "").strip()
        return (
            f"Human reviewer assigned review_ready={readiness or 'not_recorded'}"
            f" and primary_reason={primary or 'not_recorded'} after pair-level image review; "
            "online feature fields were retained only as metadata."
        )
    return current


def attest_table(table_name: str, config: dict[str, Any], attested_at: str) -> dict[str, Any]:
    path = config["path"]
    rows, fieldnames = read_csv(path)
    original_label_snapshots = [
        tuple(row.get(column, "") for column in config["label_columns"])
        for row in rows
    ]
    complete_values = config["complete_values"]
    for row in rows:
        row["manual_review_attested"] = "yes"
        row["manual_review_attested_by"] = "user_dshen"
        row["manual_review_attested_at_utc"] = attested_at
        row["manual_review_attestation_basis"] = ATTESTATION_BASIS
        row["label_use_status"] = "high_confidence_user_attested_human_label"
        if "target_notes" in row:
            row["target_notes"] = normalize_notes(table_name, row)
    for column in PROVENANCE_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)
    write_csv(path, rows, fieldnames)
    after_label_snapshots = [
        tuple(row.get(column, "") for column in config["label_columns"])
        for row in rows
    ]
    label_values_changed = original_label_snapshots != after_label_snapshots
    status_counts = Counter(row.get(config["status_column"], "") for row in rows)
    note_counts = Counter(row.get("target_notes", "") for row in rows)
    complete_rows = sum(row.get(config["status_column"], "") in complete_values for row in rows)
    return {
        "path": project_relative(path),
        "rows": len(rows),
        "complete_rows": complete_rows,
        "status_counts": dict(sorted(status_counts.items())),
        "label_values_changed": label_values_changed,
        "unique_note_count_after_cleanup": len(note_counts),
        "top_notes_after_cleanup": note_counts.most_common(5),
        "attested_rows": sum(row.get("manual_review_attested") == "yes" for row in rows),
        "label_use_status_counts": dict(sorted(Counter(row.get("label_use_status", "") for row in rows).items())),
    }


def build() -> dict[str, Any]:
    attested_at = utc_now()
    table_audits = {
        table_name: attest_table(table_name, config, attested_at)
        for table_name, config in TABLES.items()
    }
    failures = []
    for table_name, audit in table_audits.items():
        if audit["rows"] != audit["complete_rows"]:
            failures.append(f"{table_name}: incomplete rows remain")
        if audit["label_values_changed"]:
            failures.append(f"{table_name}: label values changed during attestation")
        if audit["attested_rows"] != audit["rows"]:
            failures.append(f"{table_name}: attestation columns missing rows")
    audit = {
        "built_at_utc": utc_now(),
        "manual_review_attested_at_utc": attested_at,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "table_audits": table_audits,
        "attestation_basis": ATTESTATION_BASIS,
        "scientific_status": (
            "high_confidence_user_attested_human_labels"
            if not failures
            else "attestation_failed_requires_review"
        ),
        "claim_boundary": (
            "The labels are user-attested human review labels. This attestation does not imply multi-reviewer "
            "blind consensus unless separate blinded multi-review artifacts exist."
        ),
    }
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Manual Review Attestation Audit",
        "",
        f"Status: `{audit['status']}`",
        f"Scientific status: `{audit['scientific_status']}`",
        "",
        "## Attestation Basis",
        "",
        audit["attestation_basis"],
        "",
        "## Tables",
        "",
    ]
    for table_name, table_audit in audit["table_audits"].items():
        lines.extend(
            [
                f"### {table_name}",
                "",
                f"- rows: `{table_audit['rows']}`",
                f"- complete rows: `{table_audit['complete_rows']}`",
                f"- status counts: `{table_audit['status_counts']}`",
                f"- label values changed during attestation: `{table_audit['label_values_changed']}`",
                f"- attested rows: `{table_audit['attested_rows']}`",
                f"- unique note count after cleanup: `{table_audit['unique_note_count_after_cleanup']}`",
                "",
            ]
        )
    lines.extend(["## Boundary", "", audit["claim_boundary"]])
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
