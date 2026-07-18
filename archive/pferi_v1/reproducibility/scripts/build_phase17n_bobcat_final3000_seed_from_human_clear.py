#!/usr/bin/env python3
"""Build the Bobcat final-3000 seed manifest from human-confirmed clear rows."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17n_bobcat_final3000_seed"
SEED_CSV = OUTPUT_DIR / "phase17n_bobcat_final3000_human_clear_seed_manifest.csv"
AUDIT_JSON = OUTPUT_DIR / "phase17n_bobcat_final3000_human_clear_seed_audit.json"
REPORT_MD = OUTPUT_DIR / "phase17n_bobcat_final3000_human_clear_seed_report.md"

SOURCES = [
    (
        "phase17e_mixed_inat_yesno",
        PROJECT_ROOT / "outputs/phase17/phase17e_inat_yesno_audit/phase17e_inat_bobcat_yesno_working.csv",
        "human_quality_yes_no",
        "yes",
    ),
    (
        "phase17f_organism_inat_yesno",
        PROJECT_ROOT / "outputs/phase17/phase17f_inat_organism_yesno_audit/phase17e_inat_bobcat_yesno_working.csv",
        "human_quality_yes_no",
        "yes",
    ),
    (
        "phase17g_alive_inat_yesno",
        PROJECT_ROOT / "outputs/phase17/phase17g_inat_alive_yesno_audit/phase17e_inat_bobcat_yesno_working.csv",
        "human_quality_yes_no",
        "yes",
    ),
    (
        "phase17h_auto_selected_spot",
        PROJECT_ROOT / "outputs/phase17/phase17h_inat_auto_selected_3000_spot_audit/phase17e_inat_bobcat_yesno_working.csv",
        "human_quality_yes_no",
        "yes",
    ),
    (
        "phase17j_human_calibrated_spot",
        PROJECT_ROOT / "outputs/phase17/phase17j_inat_human_calibrated_3000_spot_audit/phase17e_inat_bobcat_yesno_working.csv",
        "human_quality_yes_no",
        "yes",
    ),
    (
        "phase17k_clarity_review",
        PROJECT_ROOT / "outputs/phase17/phase17k_bobcat_clarity_review/phase17k_bobcat_clarity_gate_working.csv",
        "phase17k_clarity_gate_decision",
        "clear",
    ),
    (
        "phase17l_multisource_strict_clarity_review",
        PROJECT_ROOT
        / "outputs/phase17/phase17l_multisource_strict_clarity_review/phase17l_bobcat_strict_clarity_review_working.csv",
        "phase17l_clarity_gate_decision",
        "clear",
    ),
    (
        "phase17m_annotation_aware_strict_clarity_review",
        PROJECT_ROOT
        / "outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_review/phase17l_bobcat_strict_clarity_review_working.csv",
        "phase17l_clarity_gate_decision",
        "clear",
    ),
    (
        "bobcat_photo_selection_subject20_multisource_interim_4k",
        PROJECT_ROOT
        / "outputs/bobcat_photo_selection/reviews/subject20_multisource_interim_4k/bobcat_photo_selection_review_working.csv",
        "human_subject40_clear_decision",
        "clear",
    ),
    (
        "bobcat_photo_selection_subject20_multisource_full_complete_priority",
        PROJECT_ROOT
        / "outputs/bobcat_photo_selection/reviews/subject20_multisource_full_complete_priority/bobcat_photo_selection_review_working.csv",
        "human_subject40_clear_decision",
        "clear",
    ),
    (
        "bobcat_photo_selection_phase14_day_ultra_bbox224_crop_rescue",
        PROJECT_ROOT
        / "outputs/bobcat_photo_selection/reviews/phase14_day_ultra_bbox224_crop_rescue/bobcat_photo_selection_review_working.csv",
        "human_subject40_clear_decision",
        "clear",
    ),
    (
        "bobcat_photo_selection_phase17o_strict_final902_rescue",
        PROJECT_ROOT
        / "outputs/bobcat_photo_selection/reviews/phase17o_strict_final902_rescue/bobcat_photo_selection_review_working.csv",
        "human_subject40_clear_decision",
        "clear",
    ),
]

OUTPUT_FIELDS = [
    "final3000_seed_rank",
    "final3000_status",
    "final3000_entry_rule",
    "canonical_image_key",
    "canonical_photo_id",
    "canonical_observation_id",
    "candidate_id",
    "image_uri",
    "thumbnail_uri",
    "source_uri",
    "observation_uri",
    "photo_id",
    "observation_id",
    "place_guess",
    "observed_on",
    "license",
    "photo_license_code",
    "attribution",
    "photo_attribution",
    "phase17n_confirmed_sources",
    "phase17n_confirmation_count",
    "phase17n_latest_confirmation_source",
    "phase17n_latest_confirmation_timestamp",
    "phase17n_claim_boundary",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_image_url(url: str) -> str:
    return (
        str(url or "")
        .replace("/original.", "/large.")
        .replace("/medium.", "/large.")
        .replace("/small.", "/large.")
        .replace("/square.", "/large.")
        .split("?")[0]
    )


def observation_id_from_row(row: dict[str, str]) -> str:
    if row.get("observation_id"):
        return row["observation_id"]
    candidate_id = row.get("candidate_id", "")
    parts = candidate_id.split("_")
    for part in parts:
        if part.isdigit() and len(part) >= 5:
            return part
    uri = row.get("observation_uri") or row.get("source_uri") or ""
    marker = "/observations/"
    if marker in uri:
        return uri.split(marker, 1)[1].split("/", 1)[0].split("?", 1)[0]
    return ""


def photo_id_from_row(row: dict[str, str]) -> str:
    if row.get("photo_id"):
        return row["photo_id"]
    candidate_id = row.get("candidate_id", "")
    digits = [part for part in candidate_id.split("_") if part.isdigit()]
    if len(digits) >= 2:
        return digits[-1]
    uri = row.get("image_uri", "")
    if "/photos/" in uri:
        return uri.split("/photos/", 1)[1].split("/", 1)[0]
    return ""


def source_uri_from_row(row: dict[str, str]) -> str:
    return row.get("source_uri") or row.get("observation_uri") or ""


def row_timestamp(row: dict[str, str]) -> str:
    for key in [
        "phase17l_clarity_audited_at_utc",
        "phase17k_clarity_audited_at_utc",
        "human_audited_at_utc",
        "human_reviewed_at_utc",
    ]:
        if row.get(key):
            return row[key]
    return ""


def collect_confirmed_rows() -> tuple[list[dict[str, str]], dict[str, object]]:
    collected: list[dict[str, str]] = []
    source_counts: dict[str, dict[str, int]] = {}
    for source_name, path, decision_column, positive_value in SOURCES:
        rows = read_rows(path)
        positive = [row for row in rows if row.get(decision_column) == positive_value]
        source_counts[source_name] = {
            "path_exists": int(path.exists()),
            "rows": len(rows),
            "positive_rows": len(positive),
        }
        for row in positive:
            out = dict(row)
            out["phase17n_source_name"] = source_name
            out["phase17n_source_path"] = str(path)
            out["phase17n_confirmation_timestamp"] = row_timestamp(row)
            collected.append(out)
    audit = {"source_counts": source_counts, "raw_positive_rows": len(collected)}
    return collected, audit


def merge_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        image_key = normalize_image_url(row.get("image_uri", ""))
        photo_id = photo_id_from_row(row)
        observation_id = observation_id_from_row(row)
        key = image_key or f"photo:{photo_id}" or f"obs:{observation_id}:{row.get('candidate_id', '')}"
        grouped[key].append(row)

    merged: list[dict[str, str]] = []
    for image_key, group in grouped.items():
        group = sorted(
            group,
            key=lambda row: (
                row.get("phase17n_confirmation_timestamp", ""),
                row.get("phase17n_source_name", ""),
            ),
        )
        representative = group[-1]
        sources = sorted({row.get("phase17n_source_name", "") for row in group if row.get("phase17n_source_name", "")})
        timestamps = [row.get("phase17n_confirmation_timestamp", "") for row in group if row.get("phase17n_confirmation_timestamp", "")]
        image_uri = normalize_image_url(representative.get("image_uri", ""))
        photo_id = photo_id_from_row(representative)
        observation_id = observation_id_from_row(representative)
        merged.append(
            {
                "final3000_seed_rank": "",
                "final3000_status": "human_confirmed_clear_seed",
                "final3000_entry_rule": "human CLEAR/yes required; seed set must be extended to 3000 before final freeze",
                "canonical_image_key": image_uri or image_key,
                "canonical_photo_id": photo_id,
                "canonical_observation_id": observation_id,
                "candidate_id": representative.get("candidate_id", ""),
                "image_uri": image_uri,
                "thumbnail_uri": representative.get("thumbnail_uri", ""),
                "source_uri": source_uri_from_row(representative),
                "observation_uri": representative.get("observation_uri", "") or source_uri_from_row(representative),
                "photo_id": photo_id,
                "observation_id": observation_id,
                "place_guess": representative.get("place_guess", ""),
                "observed_on": representative.get("observed_on", ""),
                "license": representative.get("license", ""),
                "photo_license_code": representative.get("photo_license_code", ""),
                "attribution": representative.get("attribution", ""),
                "photo_attribution": representative.get("photo_attribution", ""),
                "phase17n_confirmed_sources": ";".join(sources),
                "phase17n_confirmation_count": str(len(group)),
                "phase17n_latest_confirmation_source": representative.get("phase17n_source_name", ""),
                "phase17n_latest_confirmation_timestamp": max(timestamps) if timestamps else "",
                "phase17n_claim_boundary": "Confirmed clear image seed only; not identity-labeled and not a complete final 3000 until row_count reaches 3000.",
            }
        )
    merged.sort(
        key=lambda row: (
            -int(row["phase17n_confirmation_count"]),
            row["phase17n_latest_confirmation_timestamp"],
            row["candidate_id"],
        )
    )
    for rank, row in enumerate(merged, start=1):
        row["final3000_seed_rank"] = str(rank)
    return merged


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows, audit = collect_confirmed_rows()
    merged = merge_rows(rows)
    write_csv(SEED_CSV, merged)
    audit.update(
        {
            "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "output_csv": str(SEED_CSV),
            "unique_human_confirmed_clear_rows": len(merged),
            "target_final3000_rows": 3000,
            "remaining_clear_rows_needed": max(0, 3000 - len(merged)),
            "status": "SEED_INCOMPLETE" if len(merged) < 3000 else "READY_FOR_FINAL_FREEZE_AUDIT",
            "confirmed_source_overlap_counts": dict(Counter(row["phase17n_confirmation_count"] for row in merged)),
            "latest_source_counts": dict(Counter(row["phase17n_latest_confirmation_source"] for row in merged)),
            "claim_boundary": "This file contains every deduplicated human-confirmed clear/yes Bobcat photo found in prior Phase17 working CSVs.",
        }
    )
    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "# Phase17N Bobcat Final-3000 Human-Clear Seed",
        "",
        "This manifest places all previously human-confirmed Bobcat clear/YES photos into the final-3000 seed set.",
        "",
        "## Counts",
        "",
        f"- Raw positive rows found: {audit['raw_positive_rows']}",
        f"- Deduplicated human-confirmed clear photos: {len(merged)}",
        f"- Final target: 3000",
        f"- Remaining clear rows needed: {audit['remaining_clear_rows_needed']}",
        f"- Status: `{audit['status']}`",
        "",
        "## Boundary",
        "",
        "This is a seed manifest, not a complete final 3000, until the row count reaches 3000 and receives a final freeze audit.",
    ]
    REPORT_MD.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
