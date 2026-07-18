#!/usr/bin/env python3
"""Freeze the Phase17 Bobcat/CzechLynx modeling image dataset.

This script builds a local, self-contained modeling folder from the two
human-confirmed final-entry manifests:

- Bobcat strict final 3000: downloads image URLs into the freeze folder.
- CzechLynx strict final 3000: copies the local clarity-augmented images.

The freeze package is local evidence for modeling. It does not change the
scientific claim boundary: Bobcat is not identity-labeled, and CzechLynx is
visual-quality-first unless a later split derives identity-balanced subsets.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import os
import shutil
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover - optional local validation dependency
    Image = None
    ImageOps = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE_ROOT = PROJECT_ROOT / "outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701"

BOBCAT_MANIFEST = (
    PROJECT_ROOT
    / "outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_manifest.csv"
)
BOBCAT_AUDIT = (
    PROJECT_ROOT
    / "outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_audit.json"
)
BOBCAT_REPORT = (
    PROJECT_ROOT
    / "outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_report.md"
)
CZECHLYNX_MANIFEST = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase17_strict3000_supplement/augmented/"
    "phase17_czechlynx_strict3000_final_confirmed_manifest.csv"
)
CZECHLYNX_AUDIT = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase17_strict3000_supplement/augmented/"
    "phase17_czechlynx_strict3000_clarity_augmentation_audit.json"
)
CZECHLYNX_NOTES = PROJECT_ROOT / "outputs/czechlynx/phase17_strict3000_supplement/augmented/NOTES.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    rooted = PROJECT_ROOT / value
    if rooted.exists():
        return rooted
    raise FileNotFoundError(value)


def safe_token(value: str, fallback: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    text = "_".join(part for part in text.split("_") if part)
    return (text or fallback)[:80]


def extension_from_url(url: str, fallback: str = ".jpg") -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed = mimetypes.guess_extension(fallback)
    return guessed or ".jpg"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int | None, int | None, str]:
    if Image is None:
        return None, None, "not_checked_pillow_unavailable"
    try:
        with Image.open(path) as image:
            if ImageOps is not None:
                image = ImageOps.exif_transpose(image)
            width, height = image.size
            image.verify()
        return int(width), int(height), "ok"
    except Exception as error:
        return None, None, f"decode_failed:{type(error).__name__}:{str(error)[:120]}"


def validate_inputs() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    bobcat_rows = read_csv(BOBCAT_MANIFEST)
    czech_rows = read_csv(CZECHLYNX_MANIFEST)
    bobcat_audit = json.loads(BOBCAT_AUDIT.read_text(encoding="utf-8"))
    czech_audit = json.loads(CZECHLYNX_AUDIT.read_text(encoding="utf-8"))

    checks = {
        "bobcat_rows_3000": len(bobcat_rows) == 3000,
        "bobcat_audit_ready": bobcat_audit.get("remaining_clear_rows_needed") == 0
        and bobcat_audit.get("unique_human_confirmed_clear_rows") == 3000,
        "bobcat_unique_images_3000": len({row.get("canonical_image_key", "") for row in bobcat_rows}) == 3000,
        "bobcat_all_clear": all(row.get("final3000_status") == "human_confirmed_clear_seed" for row in bobcat_rows),
        "czech_rows_3000": len(czech_rows) == 3000,
        "czech_audit_ready": czech_audit.get("augmented_rows") == 3000
        and czech_audit.get("missing_augmented_files") == 0,
        "czech_unique_keys_3000": len({row.get("dedupe_key", "") for row in czech_rows}) == 3000,
        "czech_all_ready": all(
            row.get("phase17_final3000_status") == "human_clear_augmented_ready_for_freeze" for row in czech_rows
        ),
        "czech_strict_gate_all_yes": all(row.get("strict_gate_pass") == "yes" for row in czech_rows),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"freeze input validation failed: {failed}")
    return bobcat_rows, czech_rows, bobcat_audit, czech_audit


def copy_czech_row(rank: int, row: dict[str, str], image_dir: Path) -> dict[str, Any]:
    source = resolve_path(row["algorithm_entry_image_path"])
    name = f"czechlynx_{rank:04d}__{safe_token(row.get('candidate_id', ''), 'candidate')}.jpg"
    dest = image_dir / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or dest.stat().st_size != source.stat().st_size:
        temp = dest.with_suffix(dest.suffix + f".{os.getpid()}.tmp")
        shutil.copy2(source, temp)
        temp.replace(dest)
    width, height, decode_status = image_dimensions(dest)
    return {
        "species": "czechlynx",
        "freeze_rank": rank,
        "source_manifest": project_relative(CZECHLYNX_MANIFEST),
        "source_candidate_id": row.get("candidate_id", ""),
        "source_image_uri": row.get("image_uri", ""),
        "source_image_path": row.get("original_image_path", ""),
        "source_status": row.get("phase17_final3000_status", ""),
        "source_quality_gate": row.get("strict_gate_pass", ""),
        "source_identity_label": row.get("audit_identity_label", ""),
        "license": "",
        "attribution": "",
        "frozen_image_path": project_relative(dest),
        "frozen_file_name": dest.name,
        "download_or_copy_status": "copied",
        "decode_status": decode_status,
        "image_width": width,
        "image_height": height,
        "sha256": sha256_file(dest),
        "bytes": dest.stat().st_size,
    }


def download_url(url: str, dest: Path, timeout: int, retries: int) -> str:
    if dest.exists() and dest.stat().st_size > 0:
        return "already_present"
    headers = {"User-Agent": "felid-review-readiness-freeze/1.0"}
    last_error = ""
    for attempt in range(retries + 1):
        temp = dest.with_suffix(dest.suffix + f".{os.getpid()}.tmp")
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            if temp.stat().st_size <= 0:
                raise RuntimeError("empty download")
            temp.replace(dest)
            return "downloaded" if attempt == 0 else f"downloaded_after_retry_{attempt}"
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as error:
            last_error = f"{type(error).__name__}:{str(error)[:160]}"
            if temp.exists():
                temp.unlink()
            time.sleep(min(2.0 * (attempt + 1), 8.0))
    raise RuntimeError(last_error)


def process_bobcat_row(rank: int, row: dict[str, str], image_dir: Path, timeout: int, retries: int) -> dict[str, Any]:
    url = row.get("image_uri") or row.get("canonical_image_key")
    if not url:
        raise ValueError(f"missing image URL for rank {rank}")
    suffix = extension_from_url(url)
    photo_id = row.get("canonical_photo_id") or row.get("photo_id") or str(rank)
    name = f"bobcat_{rank:04d}__photo_{safe_token(photo_id, str(rank))}{suffix}"
    dest = image_dir / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    status = download_url(url, dest, timeout=timeout, retries=retries)
    width, height, decode_status = image_dimensions(dest)
    return {
        "species": "bobcat",
        "freeze_rank": rank,
        "source_manifest": project_relative(BOBCAT_MANIFEST),
        "source_candidate_id": row.get("candidate_id", ""),
        "source_image_uri": url,
        "source_image_path": "",
        "source_status": row.get("final3000_status", ""),
        "source_quality_gate": "human_confirmed_clear",
        "source_identity_label": "",
        "license": row.get("license") or row.get("photo_license_code", ""),
        "attribution": row.get("attribution") or row.get("photo_attribution", ""),
        "frozen_image_path": project_relative(dest),
        "frozen_file_name": dest.name,
        "download_or_copy_status": status,
        "decode_status": decode_status,
        "image_width": width,
        "image_height": height,
        "sha256": sha256_file(dest),
        "bytes": dest.stat().st_size,
    }


def write_readme(path: Path, audit: dict[str, Any]) -> None:
    lines = [
        "# Phase17 Strict 3000 Modeling Freeze",
        "",
        f"Built at UTC: {audit['built_at_utc']}",
        "",
        "This folder is the local modeling entry package for the strict image sets.",
        "",
        "## Contents",
        "",
        "- `images/bobcat/`: 3,000 downloaded human-confirmed clear Bobcat images.",
        "- `images/czechlynx/`: 3,000 copied clarity-augmented CzechLynx images.",
        "- `manifests/frozen_modeling_manifest.csv`: combined modeling manifest.",
        "- `manifests/bobcat_frozen_manifest.csv`: Bobcat-only manifest.",
        "- `manifests/czechlynx_frozen_manifest.csv`: CzechLynx-only manifest.",
        "- `checksums/sha256_manifest.csv`: file hashes and byte counts.",
        "- `evidence/`: source manifests, audits, reports, and freeze audit.",
        "",
        "## Boundaries",
        "",
        "- Bobcat rows are human-confirmed clear photos, not verified individual identities.",
        "- CzechLynx rows are strict-gated and clarity-augmented, but not automatically identity-balanced.",
        "- CzechLynx augmentation is readability preprocessing; original paths remain in the source manifest.",
        "- Do not use this folder to claim Bobcat identity accuracy without separate identity labels.",
        "",
        "## Counts",
        "",
        f"- Bobcat frozen rows: {audit['species_counts'].get('bobcat', 0)}",
        f"- CzechLynx frozen rows: {audit['species_counts'].get('czechlynx', 0)}",
        f"- Total frozen rows: {audit['frozen_rows']}",
        f"- Missing/failed rows: {audit['failed_rows']}",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_freeze(args: argparse.Namespace) -> dict[str, Any]:
    bobcat_rows, czech_rows, bobcat_audit, czech_audit = validate_inputs()
    freeze_root = Path(args.output_dir)
    image_bobcat = freeze_root / "images/bobcat"
    image_czech = freeze_root / "images/czechlynx"
    manifest_dir = freeze_root / "manifests"
    evidence_dir = freeze_root / "evidence"
    checksum_dir = freeze_root / "checksums"
    for path in [image_bobcat, image_czech, manifest_dir, evidence_dir, checksum_dir]:
        path.mkdir(parents=True, exist_ok=True)

    czech_frozen = [copy_czech_row(index, row, image_czech) for index, row in enumerate(czech_rows, start=1)]

    bobcat_frozen: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_bobcat_row, index, row, image_bobcat, args.timeout, args.retries): index
            for index, row in enumerate(bobcat_rows, start=1)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                bobcat_frozen.append(future.result())
            except Exception as error:
                failures.append(
                    {
                        "species": "bobcat",
                        "freeze_rank": str(index),
                        "source_candidate_id": bobcat_rows[index - 1].get("candidate_id", ""),
                        "source_image_uri": bobcat_rows[index - 1].get("image_uri", ""),
                        "error_type": type(error).__name__,
                        "error": str(error)[:300],
                    }
                )
    bobcat_frozen.sort(key=lambda row: int(row["freeze_rank"]))

    combined = sorted(czech_frozen + bobcat_frozen, key=lambda row: (row["species"], int(row["freeze_rank"])))
    fieldnames = [
        "species",
        "freeze_rank",
        "source_manifest",
        "source_candidate_id",
        "source_image_uri",
        "source_image_path",
        "source_status",
        "source_quality_gate",
        "source_identity_label",
        "license",
        "attribution",
        "frozen_image_path",
        "frozen_file_name",
        "download_or_copy_status",
        "decode_status",
        "image_width",
        "image_height",
        "sha256",
        "bytes",
    ]
    write_csv(manifest_dir / "bobcat_frozen_manifest.csv", bobcat_frozen, fieldnames)
    write_csv(manifest_dir / "czechlynx_frozen_manifest.csv", czech_frozen, fieldnames)
    write_csv(manifest_dir / "frozen_modeling_manifest.csv", combined, fieldnames)
    write_csv(checksum_dir / "sha256_manifest.csv", combined, ["species", "freeze_rank", "frozen_image_path", "sha256", "bytes"])
    if failures:
        write_csv(
            evidence_dir / "freeze_failures.csv",
            failures,
            ["species", "freeze_rank", "source_candidate_id", "source_image_uri", "error_type", "error"],
        )

    for source in [BOBCAT_MANIFEST, BOBCAT_AUDIT, BOBCAT_REPORT, CZECHLYNX_MANIFEST, CZECHLYNX_AUDIT, CZECHLYNX_NOTES]:
        if source.exists():
            shutil.copy2(source, evidence_dir / source.name)

    decode_counts = Counter(row["decode_status"] for row in combined)
    species_counts = Counter(row["species"] for row in combined)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "freeze_root": str(freeze_root),
        "status": "FROZEN" if len(combined) == 6000 and not failures and decode_counts.get("ok") == 6000 else "FAILED",
        "frozen_rows": len(combined),
        "failed_rows": len(failures),
        "species_counts": dict(species_counts),
        "decode_status_counts": dict(decode_counts),
        "bobcat_source_audit_status": bobcat_audit.get("status", ""),
        "bobcat_remaining_clear_rows_needed": bobcat_audit.get("remaining_clear_rows_needed"),
        "czechlynx_missing_augmented_files_source_audit": czech_audit.get("missing_augmented_files"),
        "combined_manifest": project_relative(manifest_dir / "frozen_modeling_manifest.csv"),
        "bobcat_manifest": project_relative(manifest_dir / "bobcat_frozen_manifest.csv"),
        "czechlynx_manifest": project_relative(manifest_dir / "czechlynx_frozen_manifest.csv"),
        "sha256_manifest": project_relative(checksum_dir / "sha256_manifest.csv"),
        "claim_boundary": (
            "Local modeling image freeze only. Bobcat is human-clear but not identity-labeled; "
            "CzechLynx is strict visual-quality-first and may need a derived identity-balanced split."
        ),
    }
    (evidence_dir / "freeze_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_readme(freeze_root / "README.md", audit)
    if audit["status"] != "FROZEN":
        raise RuntimeError(json.dumps(audit, indent=2, sort_keys=True))
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(FREEZE_ROOT))
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--retries", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    audit = build_freeze(parse_args())
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
