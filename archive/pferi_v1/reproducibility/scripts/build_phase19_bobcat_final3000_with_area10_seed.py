#!/usr/bin/env python3
"""Build a Bobcat final-3000 manifest that includes the Phase19 area>=10 batch."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OLD_FINAL3000 = (
    PROJECT_ROOT
    / "outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_manifest.csv"
)
AREA10_QUEUE = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_inat_area10_gate/phase19_bobcat_inat_area10_review_queue.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_final3000_with_area10_seed"
FULL_POOL_CSV = OUT_DIR / "phase19_bobcat_final3000_with_area10_full_ranked_pool.csv"
FINAL3000_CSV = OUT_DIR / "phase19_bobcat_final3000_with_area10_manifest.csv"
AUDIT_JSON = OUT_DIR / "phase19_bobcat_final3000_with_area10_audit.json"
REPORT_MD = OUT_DIR / "phase19_bobcat_final3000_with_area10_report.md"

OUTPUT_FIELDS = [
    "final3000_rank",
    "final3000_status",
    "final3000_entry_rule",
    "phase19_final_source_batch",
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
    "attribution",
    "image_width",
    "image_height",
    "phase19_area10_area_fraction",
    "phase19_area10_area_bin",
    "phase19_area10_confidence",
    "phase19_clarity_second_pass_tier",
    "phase19_clarity_second_pass_score",
    "phase19_confirmed_sources",
    "phase19_priority_score",
    "phase19_claim_boundary",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_image_url(url: str) -> str:
    return (
        str(url or "")
        .replace("/original.", "/large.")
        .replace("/medium.", "/large.")
        .replace("/small.", "/large.")
        .replace("/square.", "/large.")
        .split("?", 1)[0]
    )


def photo_id_from_url(url: str) -> str:
    if "/photos/" in url:
        return url.split("/photos/", 1)[1].split("/", 1)[0]
    return ""


def observation_id_from_uri(uri: str) -> str:
    marker = "/observations/"
    if marker in uri:
        return uri.split(marker, 1)[1].split("/", 1)[0].split("?", 1)[0]
    return ""


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        text = str(row.get(key, "")).strip()
        if text in {"", "nan", "None"}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def area10_row(row: dict[str, str]) -> dict[str, Any]:
    image_uri = normalize_image_url(row.get("source_image_uri", ""))
    source_uri = row.get("source_record_uri", "")
    photo_id = photo_id_from_url(image_uri)
    obs_id = observation_id_from_uri(source_uri)
    tier_bonus = 100.0 if row.get("phase19_clarity_second_pass_tier") == "tier1_second_pass_high_clarity" else 50.0
    priority = 10_000.0 + tier_bonus + f(row, "phase19_area10_area_fraction") * 100.0 + f(row, "phase19_clarity_second_pass_score")
    return {
        "final3000_rank": "",
        "final3000_status": "phase19_area10_strategy_accepted_seed",
        "final3000_entry_rule": "user accepted Phase19 iNaturalist clean+clarity+area>=10% batch for final-3000 inclusion",
        "phase19_final_source_batch": "phase19_inat_clean_clarity_area_ge_10_user_accepted",
        "canonical_image_key": image_uri,
        "canonical_photo_id": row.get("photo_id", "") or photo_id,
        "canonical_observation_id": obs_id,
        "candidate_id": row.get("phase19_review_id", "") or row.get("source_candidate_id", ""),
        "image_uri": image_uri,
        "thumbnail_uri": "",
        "source_uri": source_uri,
        "observation_uri": source_uri,
        "photo_id": row.get("photo_id", "") or photo_id,
        "observation_id": obs_id,
        "place_guess": row.get("place_guess", ""),
        "observed_on": row.get("observed_on", ""),
        "license": row.get("license", ""),
        "attribution": row.get("attribution", ""),
        "image_width": row.get("image_width", ""),
        "image_height": row.get("image_height", ""),
        "phase19_area10_area_fraction": row.get("phase19_area10_area_fraction", ""),
        "phase19_area10_area_bin": row.get("phase19_area10_area_bin", ""),
        "phase19_area10_confidence": row.get("phase19_area10_confidence", ""),
        "phase19_clarity_second_pass_tier": row.get("phase19_clarity_second_pass_tier", ""),
        "phase19_clarity_second_pass_score": row.get("phase19_clarity_second_pass_score", ""),
        "phase19_confirmed_sources": "phase19_area10_user_batch_acceptance",
        "phase19_priority_score": f"{priority:.6f}",
        "phase19_claim_boundary": "Accepted clean-photo seed; still not identity-labeled.",
    }


def old_seed_row(row: dict[str, str]) -> dict[str, Any]:
    image_uri = normalize_image_url(row.get("image_uri", ""))
    priority = 1_000.0 - f(row, "final3000_seed_rank") / 10_000.0
    return {
        "final3000_rank": "",
        "final3000_status": "prior_phase17n_final3000_seed_retained",
        "final3000_entry_rule": row.get("final3000_entry_rule", "prior Phase17N final-3000 seed retained after de-duplication"),
        "phase19_final_source_batch": "phase17n_prior_final3000_seed",
        "canonical_image_key": image_uri or row.get("canonical_image_key", ""),
        "canonical_photo_id": row.get("canonical_photo_id", "") or row.get("photo_id", ""),
        "canonical_observation_id": row.get("canonical_observation_id", "") or row.get("observation_id", ""),
        "candidate_id": row.get("candidate_id", ""),
        "image_uri": image_uri,
        "thumbnail_uri": row.get("thumbnail_uri", ""),
        "source_uri": row.get("source_uri", "") or row.get("observation_uri", ""),
        "observation_uri": row.get("observation_uri", "") or row.get("source_uri", ""),
        "photo_id": row.get("photo_id", "") or row.get("canonical_photo_id", ""),
        "observation_id": row.get("observation_id", "") or row.get("canonical_observation_id", ""),
        "place_guess": row.get("place_guess", ""),
        "observed_on": row.get("observed_on", ""),
        "license": row.get("license", "") or row.get("photo_license_code", ""),
        "attribution": row.get("attribution", "") or row.get("photo_attribution", ""),
        "image_width": "",
        "image_height": "",
        "phase19_area10_area_fraction": "",
        "phase19_area10_area_bin": "",
        "phase19_area10_confidence": "",
        "phase19_clarity_second_pass_tier": "",
        "phase19_clarity_second_pass_score": "",
        "phase19_confirmed_sources": row.get("phase17n_confirmed_sources", ""),
        "phase19_priority_score": f"{priority:.6f}",
        "phase19_claim_boundary": "Prior clear seed retained; not identity-labeled.",
    }


def dedupe_key(row: dict[str, Any]) -> str:
    image_key = normalize_image_url(row.get("canonical_image_key", "") or row.get("image_uri", ""))
    if image_key:
        return f"image:{image_key}"
    if row.get("canonical_photo_id", ""):
        return f"photo:{row['canonical_photo_id']}"
    return f"candidate:{row.get('candidate_id', '')}"


def build() -> dict[str, Any]:
    area_rows = [area10_row(row) for row in read_csv(AREA10_QUEUE)]
    old_rows = [old_seed_row(row) for row in read_csv(OLD_FINAL3000)]
    all_rows = area_rows + old_rows
    by_key: dict[str, dict[str, Any]] = {}
    duplicate_counts: Counter[str] = Counter()
    for row in all_rows:
        key = dedupe_key(row)
        duplicate_counts[key] += 1
        existing = by_key.get(key)
        if existing is None or f(row, "phase19_priority_score") > f(existing, "phase19_priority_score"):
            by_key[key] = row
    pool = sorted(
        by_key.values(),
        key=lambda row: (
            -f(row, "phase19_priority_score"),
            row.get("phase19_final_source_batch", ""),
            row.get("candidate_id", ""),
        ),
    )
    for rank, row in enumerate(pool, start=1):
        row["final3000_rank"] = str(rank)
    final3000 = pool[:3000]
    write_csv(FULL_POOL_CSV, pool)
    write_csv(FINAL3000_CSV, final3000)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "old_phase17n_rows": len(old_rows),
        "phase19_area10_rows": len(area_rows),
        "full_unique_pool_rows": len(pool),
        "final3000_rows": len(final3000),
        "dropped_from_pool_to_exact3000": max(0, len(pool) - 3000),
        "duplicate_key_count": sum(1 for count in duplicate_counts.values() if count > 1),
        "final3000_source_batch_counts": dict(Counter(row["phase19_final_source_batch"] for row in final3000)),
        "full_pool_source_batch_counts": dict(Counter(row["phase19_final_source_batch"] for row in pool)),
        "phase19_area10_in_final3000": sum(
            row["phase19_final_source_batch"] == "phase19_inat_clean_clarity_area_ge_10_user_accepted"
            for row in final3000
        ),
        "outputs": {
            "full_pool_csv": str(FULL_POOL_CSV.relative_to(PROJECT_ROOT)),
            "final3000_csv": str(FINAL3000_CSV.relative_to(PROJECT_ROOT)),
            "audit_json": str(AUDIT_JSON.relative_to(PROJECT_ROOT)),
            "report_md": str(REPORT_MD.relative_to(PROJECT_ROOT)),
        },
        "status": "READY_EXACT_3000_WITH_PHASE19_AREA10_INCLUDED" if len(final3000) == 3000 else "NOT_EXACT_3000",
        "claim_boundary": "Final-3000 photo manifest only; rows are not individual-identity labels.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "# Phase19 Bobcat Final-3000 With Area10 Seed",
        "",
        "This manifest incorporates the user-accepted Phase19 iNaturalist clean + second-pass clarity + bobcat detector area >=10% batch into the Bobcat final-3000 photo set.",
        "",
        "## Counts",
        "",
        f"- Prior Phase17N rows: {len(old_rows)}",
        f"- Phase19 area>=10 accepted rows: {len(area_rows)}",
        f"- Unique ranked pool rows after de-duplication: {len(pool)}",
        f"- Exact final manifest rows: {len(final3000)}",
        f"- Phase19 area>=10 rows included in exact final manifest: {audit['phase19_area10_in_final3000']}",
        "",
        "## Boundary",
        "",
        "This is a final photo manifest for Bobcat clean-image selection. It is not an identity-labeled Re-ID table.",
    ]
    REPORT_MD.write_text("\n".join(report) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    print(json.dumps(build(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
