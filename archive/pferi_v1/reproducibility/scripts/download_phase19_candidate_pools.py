#!/usr/bin/env python3
"""Download Phase19 candidate image pools.

This script stages raw candidate pools for Phase19. It deliberately downloads
candidate images, not final clean images. Final 3000 selection still requires
the strict visual-evidence review gate documented in docs/phase19.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO / "data/phase19_candidate_pools"
USER_AGENT = "felid-review-readiness-triage/phase19-candidate-pools"

FCF_PREFILTER = REPO / "outputs/phase14/phase14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_all_passed.csv"
CALTECH_METADATA_URL = "https://storage.googleapis.com/public-datasets-lila/caltechcameratraps/labels/caltech_camera_traps.json.zip"
CALTECH_IMAGE_BASE = "https://storage.googleapis.com/public-datasets-lila/caltech-unzipped/cct_images"
WSU_METADATA_URL = "https://lilawildlife.blob.core.windows.net/lila-wildlife/wsu-lynx/wsu-lynx.26.02.13.1705.zip"
WSU_IMAGE_BASE = "https://storage.googleapis.com/public-datasets-lila/wsu-lynx"


def request_url(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, timeout: int = 60) -> dict:
    return json.loads(request_url(url, timeout=timeout).decode("utf-8"))


def safe_name(value: str, fallback: str) -> str:
    value = value or fallback
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value[:180] or fallback


def sha1_short(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def ext_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def write_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def lila_rows_from_coco_zip(
    metadata_url: str,
    image_base: str,
    category_names: set[str],
    source_dataset: str,
    limit: int,
) -> list[dict]:
    raw = request_url(metadata_url, timeout=180)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".json")]
        if not names:
            return []
        data = json.loads(archive.read(names[0]).decode("utf-8"))
    categories = {cat["id"]: str(cat["name"]).lower() for cat in data.get("categories", [])}
    image_by_id = {img["id"]: img for img in data.get("images", [])}
    rows: list[dict] = []
    seen: set[str] = set()
    for ann in data.get("annotations", []):
        cat_name = categories.get(ann.get("category_id"), "")
        if cat_name not in category_names:
            continue
        image_id = ann.get("image_id")
        if image_id in seen:
            continue
        img = image_by_id.get(image_id)
        if not img:
            continue
        file_name = img.get("file_name") or str(image_id)
        url = f"{image_base.rstrip('/')}/{file_name}"
        rows.append(
            {
                "phase19_cell": "bobcat_wild_camera_trap",
                "source_dataset": source_dataset,
                "source_platform": "LILA",
                "source_candidate_id": str(image_id),
                "source_image_uri": url,
                "source_image_path": "",
                "species": "bobcat",
                "domain_label": "wild_camera_trap",
                "license": "LILA_dataset_license_check_required",
                "attribution": source_dataset,
                "selection_basis": f"category={cat_name}",
            }
        )
        seen.add(image_id)
        if len(rows) >= limit:
            break
    return rows


def build_bobcat_wild(limit: int) -> list[dict]:
    rows: list[dict] = []
    for row in read_csv(FCF_PREFILTER):
        rows.append(
            {
                "phase19_cell": "bobcat_wild_camera_trap",
                "source_dataset": "Felidae Conservation Fund 2020-2025",
                "source_platform": "LILA",
                "source_candidate_id": row.get("image_id", ""),
                "source_image_uri": row.get("download_url") or row.get("azure_url", ""),
                "source_image_path": "",
                "species": "bobcat",
                "domain_label": "wild_camera_trap",
                "license": "LILA_dataset_license_check_required",
                "attribution": "Felidae Conservation Fund / LILA",
                "selection_basis": "local_phase14_md_high_evidence_prefilter",
            }
        )
        if len(rows) >= limit:
            return rows
    remaining = limit - len(rows)
    if remaining > 0:
        rows.extend(
            lila_rows_from_coco_zip(
                CALTECH_METADATA_URL,
                CALTECH_IMAGE_BASE,
                {"bobcat"},
                "Caltech Camera Traps",
                remaining,
            )
        )
    remaining = limit - len(rows)
    if remaining > 0:
        rows.extend(
            lila_rows_from_coco_zip(
                WSU_METADATA_URL,
                WSU_IMAGE_BASE,
                {"lynx rufus"},
                "WSU Lynx",
                remaining,
            )
        )
    return rows[:limit]


def inat_photo_url(photo: dict) -> str:
    url = photo.get("url") or ""
    if "square." in url:
        return url.replace("square.", "large.")
    if "small." in url:
        return url.replace("small.", "large.")
    if "medium." in url:
        return url.replace("medium.", "large.")
    return url


def build_inat_rows(
    taxon_id: int,
    species: str,
    phase19_cell: str,
    domain_label: str,
    limit: int,
    captive: str | None = None,
) -> list[dict]:
    rows: list[dict] = []
    page = 1
    per_page = 200
    while len(rows) < limit:
        params = {
            "taxon_id": taxon_id,
            "photos": "true",
            "quality_grade": "research",
            "per_page": per_page,
            "page": page,
            "order_by": "created_at",
            "order": "desc",
        }
        if captive is not None:
            params["captive"] = captive
        url = "https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(params)
        data = fetch_json(url, timeout=90)
        results = data.get("results", [])
        if not results:
            break
        for obs in results:
            photos = obs.get("photos") or []
            for photo in photos:
                image_url = inat_photo_url(photo)
                if not image_url:
                    continue
                photo_id = str(photo.get("id") or "")
                obs_id = str(obs.get("id") or "")
                rows.append(
                    {
                        "phase19_cell": phase19_cell,
                        "source_dataset": "iNaturalist",
                        "source_platform": "iNaturalist",
                        "source_candidate_id": f"{obs_id}_{photo_id}",
                        "source_image_uri": image_url,
                        "source_image_path": "",
                        "species": species,
                        "domain_label": domain_label,
                        "license": str(photo.get("license_code") or obs.get("license_code") or ""),
                        "attribution": str(photo.get("attribution") or ""),
                        "selection_basis": "research_grade_photo",
                    }
                )
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        page += 1
        total = int(data.get("total_results") or 0)
        if page > (total // per_page) + 2:
            break
        time.sleep(0.2)
    return rows[:limit]


def build_gbif_rows(
    taxon_key: int,
    species: str,
    phase19_cell: str,
    domain_label: str,
    limit: int,
    existing_ids: set[str],
) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    page_limit = 300
    while len(rows) < limit:
        params = {
            "taxon_key": taxon_key,
            "media_type": "StillImage",
            "basis_of_record": "HUMAN_OBSERVATION",
            "limit": page_limit,
            "offset": offset,
        }
        url = "https://api.gbif.org/v1/occurrence/search?" + urllib.parse.urlencode(params)
        data = fetch_json(url, timeout=90)
        results = data.get("results", [])
        if not results:
            break
        for occ in results:
            key = str(occ.get("key") or "")
            for media in occ.get("media") or []:
                image_url = media.get("identifier") or media.get("references") or ""
                if not image_url or image_url in existing_ids:
                    continue
                rows.append(
                    {
                        "phase19_cell": phase19_cell,
                        "source_dataset": "GBIF",
                        "source_platform": "GBIF",
                        "source_candidate_id": key,
                        "source_image_uri": image_url,
                        "source_image_path": "",
                        "species": species,
                        "domain_label": domain_label,
                        "license": str(media.get("license") or occ.get("license") or ""),
                        "attribution": str(media.get("rightsHolder") or occ.get("rightsHolder") or ""),
                        "selection_basis": "gbif_human_observation_still_image",
                    }
                )
                existing_ids.add(image_url)
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        offset += page_limit
        if data.get("endOfRecords"):
            break
        time.sleep(0.2)
    return rows[:limit]


def build_bobcat_urban(limit: int) -> list[dict]:
    rows = build_inat_rows(
        taxon_id=41976,
        species="bobcat",
        phase19_cell="bobcat_urban_heterogeneous",
        domain_label="urban_heterogeneous_proxy",
        limit=limit,
        captive=None,
    )
    remaining = limit - len(rows)
    if remaining > 0:
        existing = {row["source_image_uri"] for row in rows}
        rows.extend(
            build_gbif_rows(
                taxon_key=2435246,
                species="bobcat",
                phase19_cell="bobcat_urban_heterogeneous",
                domain_label="urban_heterogeneous_proxy",
                limit=remaining,
                existing_ids=existing,
            )
        )
    return rows[:limit]


def build_lynx_aux(limit: int) -> list[dict]:
    rows = build_inat_rows(
        taxon_id=41979,
        species="eurasian_lynx",
        phase19_cell="lynx_external_heterogeneous_supplement",
        domain_label="external_heterogeneous_auxiliary",
        limit=limit,
        captive=None,
    )
    remaining = limit - len(rows)
    if remaining > 0:
        existing = {row["source_image_uri"] for row in rows}
        rows.extend(
            build_gbif_rows(
                taxon_key=2435240,
                species="eurasian_lynx",
                phase19_cell="lynx_external_heterogeneous_supplement",
                domain_label="external_heterogeneous_auxiliary",
                limit=remaining,
                existing_ids=existing,
            )
        )
    return rows[:limit]


def local_path_for(row: dict, index: int) -> Path:
    cell = row["phase19_cell"]
    source = safe_name(row["source_dataset"], "source")
    ext = ext_from_url(row["source_image_uri"])
    stem = safe_name(row["source_candidate_id"], f"row_{index:05d}")
    name = f"{index:05d}__{source}__{stem}__{sha1_short(row['source_image_uri'])}{ext}"
    return OUT_ROOT / cell / "images" / name


def download_one(row: dict, index: int, timeout: int = 90) -> dict:
    path = local_path_for(row, index)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = dict(row)
    out["source_image_path"] = str(path.relative_to(REPO))
    if path.exists() and path.stat().st_size > 0:
        out["download_status"] = "already_present"
        out["bytes"] = str(path.stat().st_size)
        return out
    try:
        data = request_url(row["source_image_uri"], timeout=timeout)
        if len(data) < 1024:
            out["download_status"] = "failed_too_small"
            out["bytes"] = str(len(data))
            return out
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        out["download_status"] = "ok"
        out["bytes"] = str(len(data))
    except Exception as exc:  # noqa: BLE001 - recorded in manifest
        out["download_status"] = "failed"
        out["download_error"] = repr(exc)
        out["bytes"] = "0"
    return out


def download_rows(rows: list[dict], workers: int) -> list[dict]:
    completed: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(download_one, row, i + 1): i
            for i, row in enumerate(rows)
        }
        for n, future in enumerate(as_completed(futures), start=1):
            completed.append(future.result())
            if n % 100 == 0:
                ok = sum(1 for row in completed if row.get("download_status") in {"ok", "already_present"})
                print(f"downloaded {n}/{len(rows)} rows; ok_or_present={ok}", flush=True)
    completed.sort(key=lambda row: row.get("source_image_path", ""))
    return completed


def audit_existing_rows(rows: list[dict]) -> list[dict]:
    completed: list[dict] = []
    for index, row in enumerate(rows, start=1):
        path = local_path_for(row, index)
        out = dict(row)
        out["source_image_path"] = str(path.relative_to(REPO))
        if path.exists() and path.stat().st_size > 0:
            out["download_status"] = "already_present"
            out["bytes"] = str(path.stat().st_size)
        else:
            out["download_status"] = "missing_not_retried"
            out["bytes"] = "0"
        completed.append(out)
    return completed


def build_pool(pool: str, limit: int) -> list[dict]:
    if pool == "bobcat_wild_camera_trap":
        return build_bobcat_wild(limit)
    if pool == "bobcat_urban_heterogeneous":
        return build_bobcat_urban(limit)
    if pool == "lynx_external_heterogeneous_supplement":
        return build_lynx_aux(limit)
    raise ValueError(f"Unknown pool: {pool}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", choices=[
        "bobcat_wild_camera_trap",
        "bobcat_urban_heterogeneous",
        "lynx_external_heterogeneous_supplement",
        "all",
    ], default="all")
    parser.add_argument("--limit-bobcat-wild", type=int, default=20000)
    parser.add_argument("--limit-bobcat-urban", type=int, default=20000)
    parser.add_argument("--limit-lynx-aux", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--use-existing-manifest", action="store_true")
    parser.add_argument("--audit-existing-only", action="store_true")
    args = parser.parse_args()

    pool_limits = {
        "bobcat_wild_camera_trap": args.limit_bobcat_wild,
        "bobcat_urban_heterogeneous": args.limit_bobcat_urban,
        "lynx_external_heterogeneous_supplement": args.limit_lynx_aux,
    }
    selected = list(pool_limits) if args.pool == "all" else [args.pool]
    audit: dict[str, dict] = {}

    for pool in selected:
        pool_dir = OUT_ROOT / pool
        manifest_path = pool_dir / f"{pool}_candidate_manifest.csv"
        if args.use_existing_manifest and manifest_path.exists():
            print(f"using existing manifest for {pool}: {manifest_path}", flush=True)
            rows = read_csv(manifest_path)
        else:
            print(f"building manifest for {pool}", flush=True)
            rows = build_pool(pool, pool_limits[pool])
            write_manifest(manifest_path, rows)
        if args.metadata_only:
            final_rows = rows
        elif args.audit_existing_only:
            print(f"auditing existing files only for {pool}", flush=True)
            final_rows = audit_existing_rows(rows)
            write_manifest(pool_dir / f"{pool}_download_manifest.csv", final_rows)
        else:
            print(f"downloading {len(rows)} images for {pool}", flush=True)
            final_rows = download_rows(rows, args.workers)
            write_manifest(pool_dir / f"{pool}_download_manifest.csv", final_rows)
        ok_count = sum(1 for row in final_rows if row.get("download_status") in {"ok", "already_present"})
        fail_count = sum(
            1
            for row in final_rows
            if row.get("download_status", "") not in {"ok", "already_present", ""}
        )
        byte_sum = sum(int(row.get("bytes") or 0) for row in final_rows)
        audit[pool] = {
            "candidate_rows": len(rows),
            "download_ok_or_present": ok_count,
            "download_failed": fail_count,
            "bytes": byte_sum,
            "gb": round(byte_sum / (1024 ** 3), 3),
            "metadata_only": args.metadata_only,
        }
        (pool_dir / f"{pool}_audit.json").write_text(json.dumps(audit[pool], indent=2), encoding="utf-8")
        print(json.dumps(audit[pool], indent=2), flush=True)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "phase19_candidate_pools_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
