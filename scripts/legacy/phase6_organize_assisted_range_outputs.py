#!/usr/bin/env python3
"""Organize assisted annotation range files from Downloads into the workspace."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from phase6_assisted_annotation_workspace import (  # noqa: E402
    ensure_workspace_dirs,
    incoming_range_dir,
    parse_range_id,
    read_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Organize assisted range outputs into workspace.")
    parser.add_argument("--range-id", required=True, help="Range folder id, e.g. range_000_049")
    parser.add_argument(
        "--downloads-dir",
        type=Path,
        default=Path.home() / "Downloads",
        help="Downloads directory to scan",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files from Downloads instead of copying",
    )
    return parser.parse_args()


def find_download_file(downloads_dir: Path, range_id: str, suffix: str) -> Path | None:
    exact = downloads_dir / f"{range_id}_{suffix}"
    if exact.exists():
        return exact
    matches = sorted(downloads_dir.glob(f"{range_id}_{suffix}*"))
    return matches[0] if matches else None


def transfer_file(source: Path, target: Path, move: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if move:
        shutil.move(str(source), str(target))
    else:
        shutil.copy2(source, target)


def validate_csv_rows(path: Path, expected: int | None = None) -> int:
    rows = read_csv(path)
    if expected is not None and len(rows) != expected:
        raise RuntimeError(f"{path.name}: expected {expected} rows, found {len(rows)}")
    return len(rows)


def main() -> int:
    args = parse_args()
    range_id = args.range_id
    downloads_dir = args.downloads_dir.expanduser().resolve()
    start_index, end_index = parse_range_id(range_id)
    expected_rows = end_index - start_index + 1

    ensure_workspace_dirs()
    target_dir = incoming_range_dir(range_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    report_lines = [
        f"Organize report for {range_id}",
        "",
        f"downloads dir: {downloads_dir}",
        f"target dir: {target_dir.relative_to(PROJECT_ROOT)}",
        f"expected row count: {expected_rows}",
        "",
    ]
    copied: list[str] = []

    file_specs = [
        ("annotated.csv", expected_rows),
        ("needs_review.csv", None),
        ("needs_review_streamlit.zip", None),
        ("annotation_results.zip", None),
    ]

    for suffix, expected in file_specs:
        source = find_download_file(downloads_dir, range_id, suffix)
        if source is None:
            report_lines.append(f"missing: {range_id}_{suffix}")
            continue
        target = target_dir / f"{range_id}_{suffix}"
        transfer_file(source, target, args.move)
        copied.append(target.name)
        report_lines.append(f"{'moved' if args.move else 'copied'}: {source.name} -> {target.relative_to(PROJECT_ROOT)}")
        if suffix.endswith(".csv"):
            row_count = validate_csv_rows(target, expected)
            report_lines.append(f"  rows: {row_count}")

    zip_path = target_dir / f"{range_id}_needs_review_streamlit.zip"
    if zip_path.exists():
        extract_dir = target_dir / "needs_review_streamlit"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        nested_candidates = [
            p for p in extract_dir.iterdir() if p.is_dir() and (p / "streamlit").exists()
        ]
        if len(nested_candidates) == 1:
            nested = nested_candidates[0]
            for child in nested.iterdir():
                dest = extract_dir / child.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(child), str(dest))
            nested.rmdir()
        report_lines.append(f"unzipped: {zip_path.name} -> {extract_dir.relative_to(PROJECT_ROOT)}")

    report_path = target_dir / f"{range_id}_organize_report.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    if not copied:
        print(f"Phase 6 organize range: FAIL (no files found for {range_id})", file=sys.stderr)
        return 1

    print("Phase 6 organize range: PASS")
    print(f"range folder: {target_dir.relative_to(PROJECT_ROOT)}")
    print(f"files organized: {len(copied)}")
    print(f"report: {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
