#!/usr/bin/env python3
"""Package Phase 16E2 Bobcat remaining URL images for Kaggle local use.

This creates a resumable local image package for filtered manifest rows
iloc[6000:20000]. It does not touch rows 0-5999, does not modify the source
manifest, and does not create any final selection or recalibration artifact.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import time
import zipfile
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_MANIFEST = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e2_bobcat_20k_candidate_pool/phase16e2_bobcat_20k_candidate_manifest.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16e2_bobcat_remaining_local_package"
IMAGE_DIR = OUTPUT_DIR / "images/bobcat"
ZIP_DIR = OUTPUT_DIR / "zips"
BATCH_DIR = OUTPUT_DIR / "batch_manifests"
STATUS_CSV = OUTPUT_DIR / "phase16e2_bobcat_remaining_download_status.csv"
RUNNER_READY_MANIFEST = OUTPUT_DIR / "phase16e2_bobcat_remaining_runner_ready_manifest.csv"
ZIP_MANIFEST = OUTPUT_DIR / "phase16e2_bobcat_remaining_zip_manifest.csv"
AUDIT_JSON = OUTPUT_DIR / "phase16e2_bobcat_remaining_local_package_audit.json"
README = OUTPUT_DIR / "README_PHASE16E2_BOBCAT_REMAINING_LOCAL_KAGGLE_CN.md"

RUNNER_OUT = OUTPUT_DIR / "run_phase16e_candidate_model_filter_colab.py"
RUNNER_SOURCES = [
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter_colab_package/run_phase16e_candidate_model_filter_colab.py",
    PROJECT_ROOT
    / "outputs/phase16/phase16e2_bobcat_20k_candidate_pool/run_phase16e_candidate_model_filter_colab.py",
]

TARGET_QUADRANT = "urban_bobcat_high_confidence"
SOURCE_MODE = "url"
KAGGLE_IMAGE_PREFIX = "/kaggle/working/extracted_images/images/bobcat"
ZIP_PREFIX = "phase16e2_bobcat_remaining_images_part"
REQUESTED_DEFAULT_START = 6000
REQUESTED_DEFAULT_END = 20000
EXPECTED_REQUESTED_ROWS = 14000
DOWNLOAD_TIMEOUT_SECONDS = 30
STATUS_WRITE_EVERY = 25

BATCH_WINDOWS = [
    ("bobcat_remaining_local_06000_09999.csv", 6000, 10000),
    ("bobcat_remaining_local_10000_13999.csv", 10000, 14000),
    ("bobcat_remaining_local_14000_17999.csv", 14000, 18000),
    ("bobcat_remaining_local_18000_19999.csv", 18000, 20000),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = ordered_fieldnames(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def ordered_fieldnames(rows: list[dict]) -> list[str]:
    fields: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fields.append(key)
    return fields


def select_target_rows(rows: list[dict[str, str]], start_index: int, end_index: int) -> list[dict[str, str]]:
    filtered = [
        row
        for row in rows
        if str(row.get("target_quadrant", "")) == TARGET_QUADRANT
        and str(row.get("source_mode", "")) == SOURCE_MODE
    ]
    selected = []
    for requested_position, row in enumerate(filtered):
        if start_index <= requested_position < end_index:
            out = dict(row)
            out["requested_position"] = requested_position
            selected.append(out)
    return selected


def image_path_for_candidate(image_dir: Path, candidate_id: str) -> Path:
    return image_dir / f"{candidate_id}.jpg"


def has_existing_image(image_dir: Path, candidate_id: str) -> bool:
    path = image_path_for_candidate(image_dir, candidate_id)
    return path.exists() and path.stat().st_size > 0


def read_status(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows = read_csv_rows(path)
    return {str(row.get("candidate_id", "")): row for row in rows if row.get("candidate_id")}


def write_status(path: Path, status_by_candidate: dict[str, dict[str, str]]) -> None:
    rows = sorted(
        status_by_candidate.values(),
        key=lambda row: int(row.get("requested_position", -1)),
    )
    fieldnames = [
        "requested_position",
        "candidate_id",
        "image_uri",
        "status",
        "attempts",
        "file_size_bytes",
        "error",
        "updated_at",
    ]
    write_csv_rows(path, rows, fieldnames=fieldnames)


def download_image(
    image_uri: str,
    output_path: Path,
    max_retries: int,
    timeout: int,
    sleep_between_retries: float,
) -> tuple[bool, int, str]:
    import requests

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    last_error = ""
    for attempt in range(1, max_retries + 1):
        try:
            with requests.get(image_uri, timeout=timeout, stream=True) as response:
                response.raise_for_status()
                with temp_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            handle.write(chunk)
            if temp_path.exists() and temp_path.stat().st_size > 0:
                temp_path.replace(output_path)
                return True, attempt, ""
            last_error = "empty_download"
        except Exception as exc:  # noqa: BLE001 - keep the package run resumable.
            last_error = f"{type(exc).__name__}: {exc}"
            if temp_path.exists():
                temp_path.unlink()
        if attempt < max_retries:
            time.sleep(sleep_between_retries)
    return False, max_retries, last_error


def download_target_images(
    rows: list[dict[str, str]],
    image_dir: Path,
    status_csv: Path,
    max_retries: int,
    sleep_between_downloads: float,
    workers: int,
) -> dict[str, dict[str, str]]:
    status_by_candidate = read_status(status_csv)
    pending_rows = []
    for row in rows:
        candidate_id = str(row["candidate_id"])
        image_uri = str(row.get("image_uri", ""))
        existing_status = status_by_candidate.get(candidate_id, {})

        if has_existing_image(image_dir, candidate_id):
            size = image_path_for_candidate(image_dir, candidate_id).stat().st_size
            status_by_candidate[candidate_id] = {
                "requested_position": row["requested_position"],
                "candidate_id": candidate_id,
                "image_uri": image_uri,
                "status": existing_status.get("status") or "success_existing",
                "attempts": existing_status.get("attempts") or "0",
                "file_size_bytes": str(size),
                "error": "",
                "updated_at": utc_now(),
            }
            continue

        if not image_uri:
            status_by_candidate[candidate_id] = {
                "requested_position": row["requested_position"],
                "candidate_id": candidate_id,
                "image_uri": image_uri,
                "status": "failure",
                "attempts": "0",
                "file_size_bytes": "0",
                "error": "missing_image_uri",
                "updated_at": utc_now(),
            }
            continue

        pending_rows.append(row)

    def worker(row: dict[str, str]) -> dict[str, str]:
        candidate_id = str(row["candidate_id"])
        image_uri = str(row.get("image_uri", ""))
        ok, attempts, error = download_image(
            image_uri=image_uri,
            output_path=image_path_for_candidate(image_dir, candidate_id),
            max_retries=max_retries,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
            sleep_between_retries=sleep_between_downloads,
        )
        size = (
            image_path_for_candidate(image_dir, candidate_id).stat().st_size
            if has_existing_image(image_dir, candidate_id)
            else 0
        )
        return {
            "requested_position": row["requested_position"],
            "candidate_id": candidate_id,
            "image_uri": image_uri,
            "status": "success_downloaded" if ok else "failure",
            "attempts": str(attempts),
            "file_size_bytes": str(size),
            "error": "" if ok else error,
            "updated_at": utc_now(),
        }

    completed = 0
    if pending_rows:
        row_iter = iter(pending_rows)
        max_workers = max(1, workers)
        max_inflight = max_workers * 4
        executor = ThreadPoolExecutor(max_workers=max_workers)
        interrupted = False
        futures = set()
        try:
            while len(futures) < max_inflight:
                row = next(row_iter, None)
                if row is None:
                    break
                futures.add(executor.submit(worker, row))
                if max_workers <= 1:
                    time.sleep(sleep_between_downloads)

            while futures:
                done, futures = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    result = future.result()
                    status_by_candidate[str(result["candidate_id"])] = result
                    completed += 1
                    if completed % STATUS_WRITE_EVERY == 0:
                        write_status(status_csv, status_by_candidate)
                    row = next(row_iter, None)
                    if row is not None:
                        futures.add(executor.submit(worker, row))
                        if max_workers <= 1:
                            time.sleep(sleep_between_downloads)
        except KeyboardInterrupt:
            interrupted = True
            write_status(status_csv, status_by_candidate)
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        finally:
            if not interrupted:
                executor.shutdown(wait=True)

    write_status(status_csv, status_by_candidate)
    return status_by_candidate


def successful_candidate_ids(
    rows: list[dict[str, str]], image_dir: Path, status_by_candidate: dict[str, dict[str, str]]
) -> set[str]:
    successes = set()
    for row in rows:
        candidate_id = str(row["candidate_id"])
        status = status_by_candidate.get(candidate_id, {}).get("status", "")
        if status.startswith("success") and has_existing_image(image_dir, candidate_id):
            successes.add(candidate_id)
        elif has_existing_image(image_dir, candidate_id):
            successes.add(candidate_id)
    return successes


def build_runner_ready_rows(rows: list[dict[str, str]], success_candidate_ids: set[str]) -> list[dict[str, str]]:
    ready = []
    for row in rows:
        candidate_id = str(row["candidate_id"])
        if candidate_id not in success_candidate_ids:
            continue
        out = dict(row)
        out["original_image_uri"] = row.get("image_uri", "")
        out["source_mode"] = "packaged_local"
        out["image_uri"] = f"{KAGGLE_IMAGE_PREFIX}/{candidate_id}.jpg"
        ready.append(out)
    return ready


def write_split_zips(
    rows: list[dict],
    image_dir: Path,
    zip_dir: Path,
    zip_part_size_bytes: int,
) -> list[dict]:
    zip_dir.mkdir(parents=True, exist_ok=True)
    for old_zip in zip_dir.glob(f"{ZIP_PREFIX}_*.zip"):
        old_zip.unlink()

    records = []
    current_part = 0
    current_size = 0
    current_zip: zipfile.ZipFile | None = None

    def open_part(part: int) -> zipfile.ZipFile:
        zip_path = zip_dir / f"{ZIP_PREFIX}_{part:03d}.zip"
        return zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True)

    try:
        for row in rows:
            candidate_id = str(row["candidate_id"])
            image_path = image_path_for_candidate(image_dir, candidate_id)
            if not image_path.exists() or image_path.stat().st_size <= 0:
                continue
            file_size = image_path.stat().st_size
            if current_zip is None or (current_size > 0 and current_size + file_size > zip_part_size_bytes):
                if current_zip is not None:
                    current_zip.close()
                current_part += 1
                current_size = 0
                current_zip = open_part(current_part)
            arcname = f"images/bobcat/{candidate_id}.jpg"
            current_zip.write(image_path, arcname=arcname)
            current_size += file_size
            zip_filename = f"{ZIP_PREFIX}_{current_part:03d}.zip"
            records.append(
                {
                    "candidate_id": candidate_id,
                    "requested_position": row.get("requested_position", ""),
                    "zip_part": current_part,
                    "zip_filename": zip_filename,
                    "zip_internal_path": arcname,
                    "file_size_bytes": file_size,
                }
            )
    finally:
        if current_zip is not None:
            current_zip.close()
    return records


def write_batch_manifests(rows: list[dict], output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_csv in output_dir.glob("bobcat_remaining_local_*.csv"):
        old_csv.unlink()
    counts: dict[str, int] = {}
    fieldnames = ordered_fieldnames(rows)
    for filename, start, end in BATCH_WINDOWS:
        batch = [
            row
            for row in rows
            if start <= int(row.get("requested_position", -1)) < end
        ]
        write_csv_rows(output_dir / filename, batch, fieldnames=fieldnames)
        counts[filename] = len(batch)
    return counts


def copy_runner() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for source in RUNNER_SOURCES:
        if source.exists():
            shutil.copy2(source, RUNNER_OUT)
            return source
    raise FileNotFoundError(f"No runner source found in: {RUNNER_SOURCES}")


def counts_for(rows: list[dict], column: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(column, "")) for row in rows).items()))


def write_readme(audit: dict, batch_counts: dict[str, int]) -> None:
    README.write_text(
        f"""# Phase 16E2 Bobcat Remaining Local Kaggle Package

这个包只用于 Phase 16E2 Bobcat 剩余候选图的 Kaggle 本地图片读取，覆盖筛选后
manifest 顺序 `iloc[6000:20000]`。前 6000 张已经通过 Kaggle URL streaming 完成，
本包不重新处理 `00000-05999` 对应的已完成区间。

## 主要文件

```text
run_phase16e_candidate_model_filter_colab.py
phase16e2_bobcat_remaining_runner_ready_manifest.csv
phase16e2_bobcat_remaining_download_status.csv
phase16e2_bobcat_remaining_zip_manifest.csv
zips/phase16e2_bobcat_remaining_images_part_*.zip
batch_manifests/bobcat_remaining_local_*.csv
phase16e2_bobcat_remaining_local_package_audit.json
```

## Kaggle 使用

把 `zips/` 里的 zip 和 `batch_manifests/` 里的 CSV 作为 Kaggle input 上传。
Notebook 中解压到固定目录：

```bash
mkdir -p /kaggle/working/extracted_images
for z in /kaggle/input/*/phase16e2_bobcat_remaining_images_part_*.zip; do
  unzip -q -o "$z" -d /kaggle/working/extracted_images
done
```

batch manifest 的 `image_uri` 已经写成：

```text
/kaggle/working/extracted_images/images/bobcat/{{candidate_id}}.jpg
```

## Batch Manifests

```json
{json.dumps(batch_counts, indent=2, ensure_ascii=False)}
```

## 当前 Audit 摘要

```json
{json.dumps(audit, indent=2, ensure_ascii=False)}
```

## 边界

本包只解决 Kaggle URL streaming 慢的问题，不写 final selection，不做 recalibration，
不生成 final 3000。
""",
        encoding="utf-8",
    )


def build_audit(
    requested_rows: list[dict[str, str]],
    runner_ready_rows: list[dict[str, str]],
    status_by_candidate: dict[str, dict[str, str]],
    zip_records: list[dict],
    start_index: int,
    end_index: int,
) -> dict:
    requested_ids = [str(row["candidate_id"]) for row in requested_rows]
    failures = [
        status_by_candidate.get(candidate_id, {})
        for candidate_id in requested_ids
        if not status_by_candidate.get(candidate_id, {}).get("status", "").startswith("success")
    ]
    missing_image_uri_count = sum(1 for row in requested_rows if not str(row.get("image_uri", "")).strip())
    source_mode_counts = counts_for(runner_ready_rows, "source_mode")
    target_quadrant_counts = counts_for(runner_ready_rows, "target_quadrant")
    zip_paths = sorted(ZIP_DIR.glob(f"{ZIP_PREFIX}_*.zip"))
    pass_status = (
        len(requested_rows) == end_index - start_index
        and not failures
        and len(runner_ready_rows) == len(requested_rows)
        and len(set(row["candidate_id"] for row in runner_ready_rows)) == len(runner_ready_rows)
        and source_mode_counts == {"packaged_local": len(runner_ready_rows)}
    )
    return {
        "input_manifest": str(INPUT_MANIFEST),
        "package_output_path": str(OUTPUT_DIR),
        "requested_start": start_index,
        "requested_end_exclusive": end_index,
        "requested_rows": len(requested_rows),
        "downloaded_success_count": len(runner_ready_rows),
        "downloaded_failure_count": len(failures),
        "zip_part_count": len(zip_paths),
        "zip_sizes_bytes": {path.name: path.stat().st_size for path in zip_paths},
        "manifest_rows": len(runner_ready_rows),
        "candidate_id_unique": len(set(row["candidate_id"] for row in runner_ready_rows))
        == len(runner_ready_rows),
        "source_mode_counts": source_mode_counts,
        "target_quadrant_counts": target_quadrant_counts,
        "missing_image_uri_count": missing_image_uri_count,
        "failed_download_examples": failures[:10],
        "zip_manifest_rows": len(zip_records),
        "status": "PASS" if pass_status else "FAIL",
        "claim_boundary": "packaged local Kaggle images only; no final selection, recalibration, or final 3000",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-index", type=int, default=REQUESTED_DEFAULT_START)
    parser.add_argument("--end-index", type=int, default=REQUESTED_DEFAULT_END)
    parser.add_argument("--zip-part-size-gb", type=float, default=1.5)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--sleep-between-downloads", type=float, default=0.05)
    parser.add_argument("--workers", type=int, default=64)
    return parser.parse_args()


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    ensure_output_dirs()
    runner_source = copy_runner()

    all_rows = read_csv_rows(INPUT_MANIFEST)
    requested_rows = select_target_rows(all_rows, args.start_index, args.end_index)
    if len(requested_rows) != args.end_index - args.start_index:
        raise RuntimeError(
            f"requested row count mismatch: expected {args.end_index - args.start_index}, "
            f"found {len(requested_rows)}"
        )

    status_by_candidate = download_target_images(
        rows=requested_rows,
        image_dir=IMAGE_DIR,
        status_csv=STATUS_CSV,
        max_retries=args.max_retries,
        sleep_between_downloads=args.sleep_between_downloads,
        workers=args.workers,
    )
    success_ids = successful_candidate_ids(requested_rows, IMAGE_DIR, status_by_candidate)
    runner_ready_rows = build_runner_ready_rows(requested_rows, success_ids)
    write_csv_rows(RUNNER_READY_MANIFEST, runner_ready_rows)

    zip_records = write_split_zips(
        rows=runner_ready_rows,
        image_dir=IMAGE_DIR,
        zip_dir=ZIP_DIR,
        zip_part_size_bytes=int(args.zip_part_size_gb * 1024**3),
    )
    write_csv_rows(ZIP_MANIFEST, zip_records)
    batch_counts = write_batch_manifests(runner_ready_rows, BATCH_DIR)
    audit = build_audit(
        requested_rows=requested_rows,
        runner_ready_rows=runner_ready_rows,
        status_by_candidate=status_by_candidate,
        zip_records=zip_records,
        start_index=args.start_index,
        end_index=args.end_index,
    )
    audit["runner_source"] = str(runner_source)
    audit["runner_copied_path"] = str(RUNNER_OUT)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    write_readme(audit, batch_counts)

    print(f"requested rows: {len(requested_rows)}")
    print(f"success downloaded: {audit['downloaded_success_count']}")
    print(f"failed downloaded: {audit['downloaded_failure_count']}")
    print(f"runner-ready manifest rows: {len(runner_ready_rows)}")
    print(f"zip part count: {audit['zip_part_count']}")
    print(f"audit path: {AUDIT_JSON}")
    print(f"package path: {OUTPUT_DIR}")
    print(f"status: {audit['status']}")


if __name__ == "__main__":
    main()
