#!/usr/bin/env python3
"""Download Phase 14 FCF/LILA bobcat images from a manifest."""

from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_manifest.csv"
DEFAULT_STATUS = PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_download_status.csv"
DEFAULT_AUDIT = PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_download_audit.json"
USER_AGENT = "felid-review-readiness-triage/phase14"


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def local_path(row: pd.Series) -> Path:
    return PROJECT_ROOT / str(row["local_relative_path"])


def download_one(row_dict: dict[str, Any], timeout: int, retries: int, overwrite: bool) -> dict[str, Any]:
    row = pd.Series(row_dict)
    path = local_path(row)
    urls = [str(row["download_url"])]
    if "azure_url" in row and pd.notna(row["azure_url"]) and str(row["azure_url"]) not in urls:
        urls.append(str(row["azure_url"]))
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and path.stat().st_size > 0 and not overwrite:
        return {
            "sample_index": row.get("sample_index"),
            "image_id": row["image_id"],
            "local_relative_path": relative(path),
            "download_status": "exists",
            "bytes": int(path.stat().st_size),
            "attempts": 0,
            "error": "",
        }

    last_error = ""
    total_attempts = 0
    for url_index, url in enumerate(urls, start=1):
        for attempt in range(1, retries + 2):
            total_attempts += 1
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    data = response.read()
                if len(data) == 0:
                    raise ValueError("empty response")
                tmp_path = path.with_suffix(path.suffix + ".tmp")
                tmp_path.write_bytes(data)
                tmp_path.replace(path)
                return {
                    "sample_index": row.get("sample_index"),
                    "image_id": row["image_id"],
                    "local_relative_path": relative(path),
                    "download_status": "downloaded",
                    "bytes": int(path.stat().st_size),
                    "attempts": total_attempts,
                    "url_source_index": url_index,
                    "error": "",
                }
            except (urllib.error.URLError, TimeoutError, ValueError, OSError, http.client.IncompleteRead) as exc:
                last_error = repr(exc)
                time.sleep(min(2 * attempt, 10))

    return {
        "sample_index": row.get("sample_index"),
        "image_id": row["image_id"],
        "local_relative_path": relative(path),
        "download_status": "failed",
        "bytes": int(path.stat().st_size) if path.exists() else 0,
        "attempts": total_attempts,
        "url_source_index": "",
        "error": last_error,
    }


def write_audit(status: pd.DataFrame, audit_path: Path, manifest_path: Path) -> None:
    status_counts = {str(k): int(v) for k, v in status["download_status"].value_counts().sort_index().items()}
    bytes_total = int(status["bytes"].fillna(0).sum())
    audit = {
        "manifest": relative(manifest_path),
        "status_csv": relative(DEFAULT_STATUS if audit_path == DEFAULT_AUDIT else audit_path.with_suffix(".csv")),
        "row_count": int(len(status)),
        "status_counts": status_counts,
        "downloaded_or_exists_count": int(status["download_status"].isin(["downloaded", "exists"]).sum()),
        "failed_count": int(status["download_status"].eq("failed").sum()),
        "bytes_total": bytes_total,
        "gb_total": round(bytes_total / (1024**3), 3),
        "claim_boundary": "downloaded_images_are_for_phase14_urban_bobcat_evidence_stress_testing_not_identity_validation",
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--status", default=str(DEFAULT_STATUS))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    status_path = Path(args.status)
    audit_path = Path(args.audit)
    if not manifest_path.is_absolute():
        manifest_path = PROJECT_ROOT / manifest_path
    if not status_path.is_absolute():
        status_path = PROJECT_ROOT / status_path
    if not audit_path.is_absolute():
        audit_path = PROJECT_ROOT / audit_path

    manifest = pd.read_csv(manifest_path)
    if args.limit is not None:
        manifest = manifest.head(args.limit).copy()

    rows = manifest.to_dict(orient="records")
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(download_one, row, args.timeout, args.retries, args.overwrite)
            for row in rows
        ]
        for i, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if i % 100 == 0 or i == len(futures):
                ok = sum(r["download_status"] in {"downloaded", "exists"} for r in results)
                failed = sum(r["download_status"] == "failed" for r in results)
                print(f"progress {i}/{len(futures)} ok={ok} failed={failed}")

    status = pd.DataFrame(results).sort_values("sample_index")
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status.to_csv(status_path, index=False)
    write_audit(status, audit_path, manifest_path)

    failed = int(status["download_status"].eq("failed").sum())
    print(
        f"{'PASS' if failed == 0 else 'FAIL'} phase14 FCF bobcat download "
        f"rows={len(status)} failed={failed} status={relative(status_path)} audit={relative(audit_path)}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
