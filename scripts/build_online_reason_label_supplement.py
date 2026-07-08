#!/usr/bin/env python3
"""Build an online supplement queue for reason-label enrichment.

The supplement is intentionally separate from the internal reason-label packet.
It is for human labeling of evidence-risk reasons, not for identity accuracy or
descriptor-performance claims.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/reason-label-enrichment/online-supplement"
DATA_DIR = PROJECT_ROOT / "data/reason_label_online_supplement"
USER_AGENT = "felid-review-readiness-triage/reason-label-online-supplement"

INAT_OBSERVATIONS_URL = "https://api.inaturalist.org/v1/observations"
INAT_CC_PHOTO_LICENSES = ["cc0", "cc-by", "cc-by-nc", "cc-by-sa", "cc-by-nc-sa"]

WSU_METADATA_ZIP_URL = "https://lilawildlife.blob.core.windows.net/lila-wildlife/wsu-lynx/wsu-lynx.26.02.13.1705.zip"
WSU_IMAGE_BASE_URL = "https://storage.googleapis.com/public-datasets-lila/wsu-lynx"

DEFAULT_SLICE_TARGETS = {
    "bobcat_inat_research_cc": 100,
    "bobcat_wsu_camera_trap": 0,
    "eurasian_lynx_inat_research_cc": 50,
    "inat_low_evidence_challenge_cc": 30,
}

PAIR_COLUMNS = [
    "online_enrichment_id",
    "online_source_slice",
    "reason_enrichment_target",
    "species",
    "domain_label",
    "query_source_image_path",
    "candidate_source_image_path",
    "query_source_image_uri",
    "candidate_source_image_uri",
    "query_source_record_uri",
    "candidate_source_record_uri",
    "query_license",
    "candidate_license",
    "query_attribution",
    "candidate_attribution",
    "query_source_candidate_id",
    "candidate_source_candidate_id",
    "target_primary_reason",
    "target_secondary_reason",
    "target_body_region_visible",
    "target_notes",
    "claim_boundary",
]

IMAGE_COLUMNS = [
    "online_image_id",
    "online_source_slice",
    "species",
    "domain_label",
    "source_dataset",
    "source_platform",
    "source_candidate_id",
    "source_record_uri",
    "source_image_uri",
    "source_image_path",
    "license",
    "attribution",
    "selection_basis",
    "download_status",
    "bytes",
    "download_error",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def request_json(url: str, timeout: int = 60) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


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


def safe_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or fallback).strip())
    return cleaned[:180] or fallback


def sha1_short(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def ext_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def normalize_inat_photo_url(photo: dict[str, Any]) -> str:
    url = str(photo.get("url") or "")
    for size in ["square", "small", "medium"]:
        url = url.replace(f"/{size}.", "/large.").replace(f"{size}.jpg", "large.jpg")
    return url


def source_record_uri_for_inat(observation_id: str) -> str:
    return f"https://www.inaturalist.org/observations/{observation_id}"


def build_inat_rows(
    *,
    online_source_slice: str,
    taxon_id: int,
    species: str,
    domain_label: str,
    quality_grade: str,
    limit_images: int,
    selection_basis: str,
    order_by: str = "created_at",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_photo_ids: set[str] = set()
    page = 1
    per_page = 200
    while len(rows) < limit_images:
        params = {
            "taxon_id": taxon_id,
            "photos": "true",
            "quality_grade": quality_grade,
            "photo_license": INAT_CC_PHOTO_LICENSES,
            "per_page": per_page,
            "page": page,
            "order_by": order_by,
            "order": "desc",
        }
        url = INAT_OBSERVATIONS_URL + "?" + urllib.parse.urlencode(params, doseq=True)
        data = request_json(url, timeout=90)
        results = data.get("results") or []
        if not results:
            break
        for obs in results:
            obs_id = str(obs.get("id") or "")
            for photo in obs.get("photos") or []:
                photo_id = str(photo.get("id") or "")
                if not photo_id or photo_id in seen_photo_ids:
                    continue
                image_url = normalize_inat_photo_url(photo)
                license_code = str(photo.get("license_code") or obs.get("license_code") or "")
                if license_code not in INAT_CC_PHOTO_LICENSES:
                    continue
                rows.append(
                    {
                        "online_image_id": f"{online_source_slice}_{len(rows) + 1:05d}",
                        "online_source_slice": online_source_slice,
                        "species": species,
                        "domain_label": domain_label,
                        "source_dataset": "iNaturalist",
                        "source_platform": "iNaturalist",
                        "source_candidate_id": f"inat_obs_{obs_id}_photo_{photo_id}",
                        "source_record_uri": source_record_uri_for_inat(obs_id),
                        "source_image_uri": image_url,
                        "source_image_path": "",
                        "license": license_code,
                        "attribution": str(photo.get("attribution") or ""),
                        "selection_basis": selection_basis,
                        "download_status": "",
                        "bytes": "",
                        "download_error": "",
                    }
                )
                seen_photo_ids.add(photo_id)
                if len(rows) >= limit_images:
                    break
            if len(rows) >= limit_images:
                break
        total = int(data.get("total_results") or 0)
        page += 1
        if page > (total // per_page) + 2:
            break
        time.sleep(0.2)
    return rows[:limit_images]


def build_wsu_rows(limit_images: int, metadata_zip_url: str = WSU_METADATA_ZIP_URL) -> list[dict[str, Any]]:
    """Return WSU lynx rufus rows using jq streaming to avoid loading the full JSON."""
    query = (
        '. as $root | '
        '($root.images | map({(.id): .}) | add) as $imgs | '
        '$root.annotations[] | select(.category_id==7) | '
        '$imgs[.image_id] | select(. != null) | '
        '[.id, .file_name] | @tsv'
    )
    command = f"curl -L -s {shell_quote(metadata_zip_url)} | unzip -p - | jq -r {shell_quote(query)}"
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    assert proc.stdout is not None
    for line in proc.stdout:
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 2:
            continue
        image_id, file_name = parts
        if image_id in seen:
            continue
        seen.add(image_id)
        rows.append(
            {
                "online_image_id": f"bobcat_wsu_camera_trap_{len(rows) + 1:05d}",
                "online_source_slice": "bobcat_wsu_camera_trap",
                "species": "bobcat",
                "domain_label": "wild_camera_trap",
                "source_dataset": "WSU Lynx",
                "source_platform": "LILA",
                "source_candidate_id": image_id,
                "source_record_uri": "https://lila.science/datasets/wsu-lynx/",
                "source_image_uri": f"{WSU_IMAGE_BASE_URL}/{urllib.parse.quote(file_name, safe='/()_.-')}",
                "source_image_path": "",
                "license": "CDLA-Permissive-2.0 per LILA dataset page",
                "attribution": "WSU Lynx / LILA",
                "selection_basis": "lila_wsu_lynx_category_lynx_rufus",
                "download_status": "",
                "bytes": "",
                "download_error": "",
            }
        )
        if len(rows) >= limit_images:
            break
    if proc.stdout:
        proc.stdout.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    if not rows:
        stderr = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(f"WSU metadata extraction produced no rows: {stderr[:500]}")
    return rows[:limit_images]


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def local_image_path(row: dict[str, Any]) -> Path:
    slice_name = safe_name(str(row["online_source_slice"]), "slice")
    source = safe_name(str(row["source_dataset"]), "source")
    candidate = safe_name(str(row["source_candidate_id"]), "candidate")
    ext = ext_from_url(str(row["source_image_uri"]))
    filename = f"{source}__{candidate}__{sha1_short(str(row['source_image_uri']))}{ext}"
    return DATA_DIR / slice_name / "images" / filename


def download_one(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    path = local_image_path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    out["source_image_path"] = project_relative(path)
    if path.exists() and path.stat().st_size > 1024:
        out["download_status"] = "already_present"
        out["bytes"] = str(path.stat().st_size)
        return out
    try:
        data = request_bytes(str(out["source_image_uri"]), timeout=90)
        if len(data) < 1024:
            out["download_status"] = "failed_too_small"
            out["bytes"] = str(len(data))
            return out
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        out["download_status"] = "ok"
        out["bytes"] = str(len(data))
    except Exception as exc:  # noqa: BLE001 - audit artifact records failures
        out["download_status"] = "failed"
        out["download_error"] = repr(exc)
        out["bytes"] = "0"
    return out


def download_rows(rows: list[dict[str, Any]], workers: int) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(download_one, row) for row in rows]
        for future in as_completed(futures):
            completed.append(future.result())
    completed.sort(key=lambda row: row["online_image_id"])
    return completed


def pair_reason_for_slice(slice_name: str, pair_index: int) -> str:
    if slice_name == "bobcat_wsu_camera_trap":
        return "camera_trap_motion_or_partial_body"
    if slice_name == "inat_low_evidence_challenge_cc":
        return ["subject_too_small", "partial_body", "low_image_evidence"][pair_index % 3]
    if slice_name == "eurasian_lynx_inat_research_cc":
        return "external_lynx_source_shift_or_non_comparability"
    return "heterogeneous_viewpoint_or_source_shift"


def build_pairs(downloaded_rows: list[dict[str, Any]], slice_targets: dict[str, int]) -> list[dict[str, Any]]:
    by_slice: dict[str, list[dict[str, Any]]] = {}
    for row in downloaded_rows:
        if row.get("download_status") not in {"ok", "already_present"}:
            continue
        by_slice.setdefault(str(row["online_source_slice"]), []).append(row)
    pairs: list[dict[str, Any]] = []
    for slice_name, target_pairs in slice_targets.items():
        rows = by_slice.get(slice_name, [])
        max_pairs = min(target_pairs, len(rows) // 2)
        for idx in range(max_pairs):
            query = rows[2 * idx]
            candidate = rows[2 * idx + 1]
            pairs.append(
                {
                    "online_enrichment_id": f"online_reason_{len(pairs) + 1:04d}",
                    "online_source_slice": slice_name,
                    "reason_enrichment_target": pair_reason_for_slice(slice_name, idx),
                    "species": query["species"],
                    "domain_label": query["domain_label"],
                    "query_source_image_path": query["source_image_path"],
                    "candidate_source_image_path": candidate["source_image_path"],
                    "query_source_image_uri": query["source_image_uri"],
                    "candidate_source_image_uri": candidate["source_image_uri"],
                    "query_source_record_uri": query["source_record_uri"],
                    "candidate_source_record_uri": candidate["source_record_uri"],
                    "query_license": query["license"],
                    "candidate_license": candidate["license"],
                    "query_attribution": query["attribution"],
                    "candidate_attribution": candidate["attribution"],
                    "query_source_candidate_id": query["source_candidate_id"],
                    "candidate_source_candidate_id": candidate["source_candidate_id"],
                    "target_primary_reason": "",
                    "target_secondary_reason": "",
                    "target_body_region_visible": "",
                    "target_notes": "",
                    "claim_boundary": (
                        "Online supplement for reason-label enrichment only; not identity-labeled "
                        "and not evidence for descriptor accuracy."
                    ),
                }
            )
    return pairs


def build_source_rows(slice_targets: dict[str, int], include_wsu: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if slice_targets.get("bobcat_inat_research_cc", 0):
        rows.extend(
            build_inat_rows(
                online_source_slice="bobcat_inat_research_cc",
                taxon_id=41976,
                species="bobcat",
                domain_label="heterogeneous_handheld_external",
                quality_grade="research",
                limit_images=slice_targets["bobcat_inat_research_cc"] * 2,
                selection_basis="iNaturalist research-grade CC photo",
            )
        )
    if include_wsu and slice_targets.get("bobcat_wsu_camera_trap", 0):
        rows.extend(build_wsu_rows(slice_targets["bobcat_wsu_camera_trap"] * 2))
    if slice_targets.get("eurasian_lynx_inat_research_cc", 0):
        rows.extend(
            build_inat_rows(
                online_source_slice="eurasian_lynx_inat_research_cc",
                taxon_id=41979,
                species="eurasian_lynx",
                domain_label="external_heterogeneous_lynx",
                quality_grade="research",
                limit_images=slice_targets["eurasian_lynx_inat_research_cc"] * 2,
                selection_basis="iNaturalist Eurasian lynx research-grade CC photo",
            )
        )
    if slice_targets.get("inat_low_evidence_challenge_cc", 0):
        rows.extend(
            build_inat_rows(
                online_source_slice="inat_low_evidence_challenge_cc",
                taxon_id=41976,
                species="bobcat",
                domain_label="low_evidence_challenge_external",
                quality_grade="casual",
                limit_images=slice_targets["inat_low_evidence_challenge_cc"] * 2,
                selection_basis="iNaturalist casual CC photo deliberately sampled for reason-label challenge",
                order_by="observed_on",
            )
        )
    return rows


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Online Reason-Label Supplement",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This supplement creates a separate online review queue for evidence-risk reason labels.",
        "It must remain separate from the internal packet until human review passes.",
        "",
        "## Counts",
        "",
        f"- source image rows: {audit['source_image_rows']}",
        f"- downloaded or already present images: {audit['download_ok_or_present']}",
        f"- review pairs: {audit['review_pair_rows']}",
        "",
        "## Slice Pair Counts",
        "",
    ]
    for slice_name, count in sorted(audit["pair_counts_by_slice"].items()):
        lines.append(f"- `{slice_name}`: {count}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            audit["claim_boundary"],
        ]
    )
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_slice_targets(args: argparse.Namespace) -> dict[str, int]:
    return {
        "bobcat_inat_research_cc": args.bobcat_inat_pairs,
        "bobcat_wsu_camera_trap": args.wsu_pairs,
        "eurasian_lynx_inat_research_cc": args.eurasian_lynx_inat_pairs,
        "inat_low_evidence_challenge_cc": args.challenge_pairs,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    slice_targets = parse_slice_targets(args)
    source_rows = build_source_rows(slice_targets, include_wsu=not args.skip_wsu)
    write_csv(OUTPUT_DIR / "online_reason_label_source_images.csv", source_rows, IMAGE_COLUMNS)
    if args.metadata_only:
        downloaded_rows = source_rows
    else:
        downloaded_rows = download_rows(source_rows, workers=args.workers)
    write_csv(OUTPUT_DIR / "online_reason_label_download_manifest.csv", downloaded_rows, IMAGE_COLUMNS)
    pairs = build_pairs(downloaded_rows, slice_targets)
    write_csv(OUTPUT_DIR / "online_reason_label_review_queue.csv", pairs, PAIR_COLUMNS)
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if pairs else ("METADATA_ONLY_PASS" if args.metadata_only and source_rows else "FAIL"),
        "metadata_only": args.metadata_only,
        "skip_wsu": args.skip_wsu,
        "target_pairs_by_slice": slice_targets,
        "source_image_rows": len(source_rows),
        "download_ok_or_present": sum(row.get("download_status") in {"ok", "already_present"} for row in downloaded_rows),
        "download_failed": sum(row.get("download_status") == "failed" for row in downloaded_rows),
        "review_pair_rows": len(pairs),
        "pair_counts_by_slice": dict(Counter(row["online_source_slice"] for row in pairs)),
        "outputs": {
            "source_images_csv": project_relative(OUTPUT_DIR / "online_reason_label_source_images.csv"),
            "download_manifest_csv": project_relative(OUTPUT_DIR / "online_reason_label_download_manifest.csv"),
            "review_queue_csv": project_relative(OUTPUT_DIR / "online_reason_label_review_queue.csv"),
            "audit_json": project_relative(OUTPUT_DIR / "online_reason_label_supplement_audit.json"),
            "report_md": project_relative(OUTPUT_DIR / "README.md"),
        },
        "claim_boundary": (
            "Online source supplement supports reason-label enrichment and feature-varied validation only. "
            "It does not support Bobcat identity metrics, descriptor accuracy claims, or unqualified "
            "domain-shift guarantees."
        ),
    }
    write_json(OUTPUT_DIR / "online_reason_label_supplement_audit.json", audit)
    write_report(audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bobcat-inat-pairs", type=int, default=DEFAULT_SLICE_TARGETS["bobcat_inat_research_cc"])
    parser.add_argument("--wsu-pairs", type=int, default=DEFAULT_SLICE_TARGETS["bobcat_wsu_camera_trap"])
    parser.add_argument(
        "--eurasian-lynx-inat-pairs",
        type=int,
        default=DEFAULT_SLICE_TARGETS["eurasian_lynx_inat_research_cc"],
    )
    parser.add_argument("--challenge-pairs", type=int, default=DEFAULT_SLICE_TARGETS["inat_low_evidence_challenge_cc"])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--skip-wsu", action="store_true")
    args = parser.parse_args()
    audit = build(args)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
