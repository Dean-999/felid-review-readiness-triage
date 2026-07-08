#!/usr/bin/env python3
"""Build blind reliability packets for external reviewer validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/blind-reliability-packet"
MASTER_PACKET_CSV = OUTPUT_DIR / "blind_reliability_master_packet.csv"
REVIEW_TEMPLATE_CSV = OUTPUT_DIR / "blind_reliability_review_template.csv"
AUDIT_JSON = OUTPUT_DIR / "blind_reliability_packet_audit.json"
README_MD = OUTPUT_DIR / "README.md"
EXTERNAL_REVIEWS_DIR = OUTPUT_DIR / "external-reviews"
REVIEWER2_CORRECTED_NOTE = (
    "metadata correction: independent external blind review confirmed; "
    "see provenance_correction.md"
)

FEATURE_WORKING_CSV = (
    PROJECT_ROOT / "outputs/modeling-validation/feature-varied-validation-packet/feature_varied_validation_review_working.csv"
)
INTERNAL_REASON_CSV = (
    PROJECT_ROOT / "outputs/modeling-validation/reason-label-enrichment/reason_label_enrichment_review_working.csv"
)
ONLINE_REASON_CSV = (
    PROJECT_ROOT
    / "outputs/modeling-validation/reason-label-enrichment/online-supplement/online_reason_label_review_working.csv"
)

DEFAULT_TARGETS = {
    "feature_varied": 150,
    "internal_reason": 80,
    "online_supplement": 50,
}

MASTER_COLUMNS = [
    "blind_pair_id",
    "source_packet",
    "source_row_id",
    "query_image_path",
    "candidate_image_path",
    "original_target_review_ready",
    "original_primary_reason",
    "original_secondary_reason",
    "selection_stratum",
    "selection_basis",
    "claim_boundary",
]

TEMPLATE_COLUMNS = [
    "blind_pair_id",
    "source_packet",
    "query_image_path",
    "candidate_image_path",
    "reviewer_id",
    "review_ready",
    "primary_reason",
    "secondary_reason",
    "body_region_visible",
    "reviewer_confidence",
    "reviewer_notes",
]

REASONS = [
    "",
    "low_image_evidence",
    "motion_or_blur",
    "night_or_low_light",
    "subject_too_small",
    "partial_body",
    "occlusion",
    "non_comparable_viewpoint",
    "non_overlapping_body_region",
    "descriptor_evidence_conflict",
    "source_domain_stress",
    "wrong_species_or_non_target",
    "other",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def stable_score(key: str) -> int:
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:12], 16)


def path_exists(path_text: str) -> bool:
    path = Path(path_text)
    if path.is_absolute():
        return path.exists()
    return (PROJECT_ROOT / path).exists()


def source_rows() -> dict[str, list[dict[str, str]]]:
    feature_rows = []
    for row in read_csv(FEATURE_WORKING_CSV):
        feature_rows.append(
            {
                "source_packet": "feature_varied",
                "source_row_id": row["feature_varied_id"],
                "query_image_path": row["query_image_path"],
                "candidate_image_path": row["candidate_image_path"],
                "original_target_review_ready": row["target_review_ready"],
                "original_primary_reason": row.get("target_not_ready_reason", ""),
                "original_secondary_reason": row.get("target_secondary_reason", ""),
                "selection_stratum": row.get("target_review_ready", ""),
            }
        )
    internal_rows = []
    for row in read_csv(INTERNAL_REASON_CSV):
        primary = row.get("target_primary_reason", "")
        internal_rows.append(
            {
                "source_packet": "internal_reason",
                "source_row_id": row["enrichment_id"],
                "query_image_path": row["query_image_path"],
                "candidate_image_path": row["candidate_image_path"],
                "original_target_review_ready": "yes" if not primary else "no_or_uncertain",
                "original_primary_reason": primary,
                "original_secondary_reason": row.get("target_secondary_reason", ""),
                "selection_stratum": primary or "review_ready_control",
            }
        )
    online_rows = []
    for row in read_csv(ONLINE_REASON_CSV):
        online_rows.append(
            {
                "source_packet": "online_supplement",
                "source_row_id": row["online_enrichment_id"],
                "query_image_path": row["query_source_image_path"],
                "candidate_image_path": row["candidate_source_image_path"],
                "original_target_review_ready": row.get("target_review_ready", ""),
                "original_primary_reason": row.get("target_primary_reason", ""),
                "original_secondary_reason": row.get("target_secondary_reason", ""),
                "selection_stratum": f"{row.get('target_review_ready', '')}:{row.get('target_primary_reason', '')}",
            }
        )
    return {
        "feature_varied": feature_rows,
        "internal_reason": internal_rows,
        "online_supplement": online_rows,
    }


def sample_balanced(rows: list[dict[str, str]], target: int, packet_name: str) -> list[dict[str, str]]:
    by_stratum: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_stratum[row["selection_stratum"] or "blank"].append(row)
    strata = sorted(by_stratum)
    selected: list[dict[str, str]] = []
    per_stratum = max(1, target // max(1, len(strata)))
    leftovers: list[dict[str, str]] = []
    for stratum in strata:
        ordered = sorted(
            by_stratum[stratum],
            key=lambda row: stable_score(f"{packet_name}:{stratum}:{row['source_row_id']}"),
        )
        selected.extend(ordered[:per_stratum])
        leftovers.extend(ordered[per_stratum:])
    if len(selected) < target:
        leftovers.sort(key=lambda row: stable_score(f"{packet_name}:fill:{row['source_row_id']}"))
        selected.extend(leftovers[: target - len(selected)])
    selected = selected[:target]
    selected.sort(key=lambda row: stable_score(f"blind-order:{packet_name}:{row['source_row_id']}"))
    return selected


def blind_row(source: dict[str, str], index: int) -> dict[str, str]:
    return {
        "blind_pair_id": f"blind_pair_{index:04d}",
        **source,
        "selection_basis": "stratified_blind_reliability_sample",
        "claim_boundary": "External reviewers must not see original labels or feature scores.",
    }


def build(targets: dict[str, int]) -> dict[str, Any]:
    all_sources = source_rows()
    master: list[dict[str, str]] = []
    for packet_name, target in targets.items():
        for row in sample_balanced(all_sources[packet_name], target, packet_name):
            master.append(blind_row(row, len(master) + 1))
    template = [
        {
            "blind_pair_id": row["blind_pair_id"],
            "source_packet": row["source_packet"],
            "query_image_path": row["query_image_path"],
            "candidate_image_path": row["candidate_image_path"],
            "reviewer_id": "",
            "review_ready": "",
            "primary_reason": "",
            "secondary_reason": "",
            "body_region_visible": "",
            "reviewer_confidence": "",
            "reviewer_notes": "",
        }
        for row in master
    ]
    write_csv(MASTER_PACKET_CSV, master, MASTER_COLUMNS)
    write_csv(REVIEW_TEMPLATE_CSV, template, TEMPLATE_COLUMNS)
    missing_images = [
        row["blind_pair_id"]
        for row in master
        if not path_exists(row["query_image_path"]) or not path_exists(row["candidate_image_path"])
    ]
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if not missing_images and len(master) == sum(targets.values()) else "FAIL",
        "targets": targets,
        "master_rows": len(master),
        "review_template_rows": len(template),
        "source_packet_counts": dict(sorted(Counter(row["source_packet"] for row in master).items())),
        "original_review_ready_counts": dict(sorted(Counter(row["original_target_review_ready"] for row in master).items())),
        "original_primary_reason_counts": dict(sorted(Counter(row["original_primary_reason"] or "<blank>" for row in master).items())),
        "missing_image_count": len(missing_images),
        "missing_image_rows": missing_images[:20],
        "outputs": {
            "master_packet_csv": project_relative(MASTER_PACKET_CSV),
            "review_template_csv": project_relative(REVIEW_TEMPLATE_CSV),
            "audit_json": project_relative(AUDIT_JSON),
            "readme_md": project_relative(README_MD),
        },
        "claim_boundary": (
            "The master packet contains original labels for later agreement analysis. "
            "External reviewers must receive only the blind review template or Streamlit app."
        ),
    }
    write_json(AUDIT_JSON, audit)
    write_readme(audit)
    return audit


def write_readme(audit: dict[str, Any]) -> None:
    lines = [
        "# Blind Reliability Packet",
        "",
        f"Status: `{audit['status']}`",
        "",
        "Purpose: independent external review of a stratified subset of the completed user-attested labels.",
        "",
        "## What to send reviewers",
        "",
        f"- Blind review template: `{audit['outputs']['review_template_csv']}`",
        "- Streamlit app: `scripts/streamlit_blind_reliability_review_app.py`",
        "",
        "Do not send the master packet to reviewers. It contains original labels for agreement analysis.",
        "",
        "## Counts",
        "",
        f"- Total blind pairs: `{audit['master_rows']}`",
        f"- Source packet counts: `{audit['source_packet_counts']}`",
        f"- Original review-ready counts, hidden from reviewers: `{audit['original_review_ready_counts']}`",
        "",
        "## Reviewer Instructions",
        "",
        "- Judge whether the pair is review-ready as pair-level evidence.",
        "- Use `yes`, `no`, or `uncertain` for `review_ready`.",
        "- If not yes, choose the strongest `primary_reason`.",
        "- Do not infer identity for Bobcat/external rows.",
        "- Do not use metadata outside the displayed images.",
        "",
        "## Effect on Modeling",
        "",
        "The current user-attested labels remain valid for provisional modeling. This blind packet estimates reliability. "
        "High agreement upgrades final claim strength; low agreement triggers adjudication or narrower claims.",
    ]
    README_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_reviewer_working_packet(reviewer_id: str) -> dict[str, Any]:
    if not reviewer_id:
        raise ValueError("reviewer_id is required")
    master = read_csv(MASTER_PACKET_CSV)
    reviewer_dir = EXTERNAL_REVIEWS_DIR / reviewer_id
    working_csv = reviewer_dir / "blind_reliability_review_working.csv"
    instructions_md = reviewer_dir / "README.md"
    rows = [
        {
            "blind_pair_id": row["blind_pair_id"],
            "source_packet": row["source_packet"],
            "query_image_path": row["query_image_path"],
            "candidate_image_path": row["candidate_image_path"],
            "reviewer_id": reviewer_id,
            "review_ready": "",
            "primary_reason": "",
            "secondary_reason": "",
            "body_region_visible": "",
            "reviewer_confidence": "",
            "reviewer_notes": "",
            "reviewed_at_utc": "",
        }
        for row in master
    ]
    write_csv(working_csv, rows, [*TEMPLATE_COLUMNS, "reviewed_at_utc"])
    lines = [
        f"# Blind Reliability Review: {reviewer_id}",
        "",
        "Use this CSV or the Streamlit app to complete the second blind reliability review.",
        "",
        "## File To Fill",
        "",
        f"`{project_relative(working_csv)}`",
        "",
        "## Instructions",
        "",
        "- Judge whether each pair is review-ready as pair-level individual Re-ID evidence.",
        "- Use `yes`, `no`, or `uncertain` for `review_ready`.",
        "- If `review_ready` is not `yes`, choose the strongest `primary_reason`.",
        "- Do not infer or assign animal identity.",
        "- Do not use metadata outside the displayed images.",
        "- Do not open or use `blind_reliability_master_packet.csv`.",
        "",
        "## Streamlit Launch",
        "",
        "```bash",
        f"BLIND_RELIABILITY_REVIEWER_ID={reviewer_id} streamlit run scripts/streamlit_blind_reliability_review_app.py",
        "```",
    ]
    instructions_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if len(rows) == len(master) else "FAIL",
        "reviewer_id": reviewer_id,
        "master_rows": len(master),
        "working_rows": len(rows),
        "working_csv": project_relative(working_csv),
        "instructions_md": project_relative(instructions_md),
        "claim_boundary": "Reviewer working packet hides original labels and is suitable for independent blind review.",
    }
    write_json(reviewer_dir / "reviewer_packet_audit.json", audit)
    return audit


def build_corrected_reviewer_copy(
    reviewer_id: str,
    corrected_note: str = REVIEWER2_CORRECTED_NOTE,
) -> dict[str, Any]:
    if not reviewer_id:
        raise ValueError("reviewer_id is required")
    reviewer_dir = EXTERNAL_REVIEWS_DIR / reviewer_id
    original_csv = reviewer_dir / "blind_reliability_review_working.csv"
    corrected_csv = reviewer_dir / "blind_reliability_review_working.corrected.csv"
    correction_md = reviewer_dir / "provenance_correction.md"
    correction_json = reviewer_dir / "provenance_correction.json"
    audit_json = reviewer_dir / "corrected_copy_audit.json"

    rows = read_csv(original_csv)
    if not rows:
        raise ValueError(f"no reviewer rows found in {original_csv}")
    fieldnames = list(rows[0].keys())
    if "reviewer_notes" not in fieldnames:
        raise ValueError("reviewer_notes column is required for metadata correction")
    original_columns = [name for name in fieldnames if name.startswith("original_")]
    corrected_rows = []
    changed_rows = 0
    stale_note_rows = 0
    for row in rows:
        corrected = dict(row)
        old_note = corrected.get("reviewer_notes", "")
        if "not independent blind evidence" in old_note:
            stale_note_rows += 1
        if old_note != corrected_note:
            changed_rows += 1
        corrected["reviewer_notes"] = corrected_note
        corrected_rows.append(corrected)

    write_csv(corrected_csv, corrected_rows, fieldnames)
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if corrected_rows and not original_columns else "FAIL",
        "reviewer_id": reviewer_id,
        "original_csv": project_relative(original_csv),
        "corrected_csv": project_relative(corrected_csv),
        "correction_md": project_relative(correction_md),
        "correction_json": project_relative(correction_json),
        "row_count": len(corrected_rows),
        "changed_reviewer_notes_rows": changed_rows,
        "stale_not_independent_note_rows": stale_note_rows,
        "original_label_columns_present": original_columns,
        "labels_changed": False,
        "corrected_reviewer_notes": corrected_note,
        "claim_boundary": (
            "Corrected copy changes only reviewer_notes metadata. Review labels remain unchanged, "
            "and the original CSV is preserved as the raw received file."
        ),
    }
    write_json(audit_json, audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-varied", type=int, default=DEFAULT_TARGETS["feature_varied"])
    parser.add_argument("--internal-reason", type=int, default=DEFAULT_TARGETS["internal_reason"])
    parser.add_argument("--online-supplement", type=int, default=DEFAULT_TARGETS["online_supplement"])
    parser.add_argument("--reviewer-id", help="Create a blank working CSV for this reviewer from the current master packet")
    parser.add_argument("--correct-reviewer-copy", help="Create a corrected metadata copy for an existing reviewer CSV")
    args = parser.parse_args()
    if args.correct_reviewer_copy:
        audit = build_corrected_reviewer_copy(args.correct_reviewer_copy)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["status"] == "PASS" else 1
    if args.reviewer_id:
        audit = build_reviewer_working_packet(args.reviewer_id)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["status"] == "PASS" else 1
    audit = build(
        {
            "feature_varied": args.feature_varied,
            "internal_reason": args.internal_reason,
            "online_supplement": args.online_supplement,
        }
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
