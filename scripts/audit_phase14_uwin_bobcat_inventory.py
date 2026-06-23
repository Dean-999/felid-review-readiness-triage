#!/usr/bin/env python3
"""Audit local UWIN bobcat candidate metadata for Phase 14.

The audit is intentionally metadata-only: it scans tabular/source files for
UWIN/bobcat/Lynx rufus signals and records field availability without copying
raw images or exposing sensitive location/path values in public documentation.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/phase14/uwin_bobcat_inventory.csv"
DEFAULT_SUMMARY = PROJECT_ROOT / "outputs/phase14/uwin_bobcat_inventory_summary.json"

CANDIDATE_TOKENS = {
    "uwin",
    "bobcat",
    "lynx rufus",
    "lynx_rufus",
    "lynx-rufus",
    "rufus",
}

SENSITIVE_HINTS = {
    "lat",
    "latitude",
    "lon",
    "long",
    "longitude",
    "coord",
    "coordinate",
    "utm",
    "site",
    "trap",
    "camera",
    "station",
    "cell",
    "location",
    "grid",
    "path",
    "filepath",
    "file_path",
    "image_path",
    "gps",
}

IDENTITY_HINTS = {
    "individual",
    "individual_id",
    "animal_id",
    "identity",
    "identity_id",
    "id_individual",
    "tag_id",
    "collar_id",
}

PAIR_AUDIT_HINTS = {
    "pair",
    "same",
    "different",
    "uncertain",
    "non_comparable",
    "non-comparable",
    "review_confidence",
    "reviewer",
    "human_label",
}

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".json", ".jsonl"}


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def token_match(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in CANDIDATE_TOKENS)


def pipe_join(values: list[str]) -> str:
    return "|".join(sorted(set(values)))


def classify_columns(columns: list[str]) -> dict[str, list[str]]:
    lower = [(column, column.lower()) for column in columns]
    sensitive = [
        column
        for column, lc in lower
        if any(hint in lc.replace(" ", "_") for hint in SENSITIVE_HINTS)
    ]
    identity = [
        column
        for column, lc in lower
        if any(hint in lc.replace(" ", "_") for hint in IDENTITY_HINTS)
    ]
    pair_audit = [
        column
        for column, lc in lower
        if any(hint in lc.replace(" ", "_") for hint in PAIR_AUDIT_HINTS)
    ]
    bobcat = [column for column, lc in lower if token_match(lc)]
    return {
        "sensitive_columns": sensitive,
        "identity_like_columns": identity,
        "pair_audit_like_columns": pair_audit,
        "bobcat_like_columns": bobcat,
    }


def read_table_sample(path: Path, nrows: int) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, nrows=nrows)
    if suffix in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t", nrows=nrows)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, nrows=nrows)
    if suffix == ".jsonl":
        return pd.read_json(path, lines=True, nrows=nrows)
    if suffix == ".json":
        try:
            return pd.read_json(path, nrows=nrows)
        except ValueError:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return pd.DataFrame(data[:nrows])
            if isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, list):
                        return pd.DataFrame(value[:nrows])
                return pd.DataFrame([data])
            return pd.DataFrame()
    raise ValueError(f"unsupported extension: {suffix}")


def sampled_value_token_hits(frame: pd.DataFrame, max_columns: int = 30) -> dict[str, int]:
    """Count candidate-token hits without returning any raw values."""

    hits: dict[str, int] = {token: 0 for token in sorted(CANDIDATE_TOKENS)}
    object_columns = list(frame.select_dtypes(include=["object", "string"]).columns)[:max_columns]
    for column in object_columns:
        values = frame[column].dropna().astype(str).head(200)
        lower_values = values.str.lower()
        for token in hits:
            hits[token] += int(lower_values.str.contains(token, regex=False).sum())
    return {token: count for token, count in hits.items() if count > 0}


def summarize_file(path: Path, nrows: int) -> dict[str, Any]:
    frame = read_table_sample(path, nrows=nrows)
    columns = [str(column) for column in frame.columns]
    column_classes = classify_columns(columns)
    value_hits = sampled_value_token_hits(frame)
    rel = relative(path)
    name_or_path_candidate = token_match(relative(path))
    column_candidate = bool(column_classes["bobcat_like_columns"])
    value_candidate = bool(value_hits)
    candidate = name_or_path_candidate or column_candidate or value_candidate
    source_category = "local_data" if rel.startswith("data/") else "literature_or_source" if rel.startswith("sources/") else "other"
    identity_available = bool(column_classes["identity_like_columns"])
    pair_audit_available = bool(column_classes["pair_audit_like_columns"])
    sensitive_present = bool(column_classes["sensitive_columns"])
    return {
        "candidate": candidate,
        "relative_path": rel,
        "source_category": source_category,
        "file_extension": path.suffix.lower(),
        "rows_sampled": int(len(frame)),
        "n_columns": int(len(columns)),
        "candidate_signal": "|".join(
            signal
            for signal, present in [
                ("path_or_filename", name_or_path_candidate),
                ("column_name", column_candidate),
                ("sampled_value", value_candidate),
            ]
            if present
        ),
        "sensitive_columns": pipe_join(column_classes["sensitive_columns"]),
        "identity_like_columns": pipe_join(column_classes["identity_like_columns"]),
        "pair_audit_like_columns": pipe_join(column_classes["pair_audit_like_columns"]),
        "bobcat_like_columns": pipe_join(column_classes["bobcat_like_columns"]),
        "sampled_value_token_hit_counts": json.dumps(value_hits, sort_keys=True),
        "sensitive_fields_present": "yes" if sensitive_present else "no",
        "identity_like_fields_present": "yes" if identity_available else "no",
        "pair_audit_like_fields_present": "yes" if pair_audit_available else "no",
    }


def iter_supported_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(root)
        elif root.exists():
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    files.append(path)
    return sorted(files)


def write_summary(rows: list[dict[str, Any]], scanned_count: int, summary_path: Path) -> None:
    candidate_count = len(rows)
    local_data_count = sum(row.get("source_category") == "local_data" for row in rows)
    identity_count = sum(row["identity_like_fields_present"] == "yes" for row in rows)
    pair_audit_count = sum(row["pair_audit_like_fields_present"] == "yes" for row in rows)
    sensitive_count = sum(row["sensitive_fields_present"] == "yes" for row in rows)
    summary = {
        "scanned_file_count": scanned_count,
        "candidate_file_count": candidate_count,
        "local_data_candidate_file_count": local_data_count,
        "literature_or_source_candidate_file_count": sum(
            row.get("source_category") == "literature_or_source" for row in rows
        ),
        "identity_like_candidate_file_count": identity_count,
        "pair_audit_like_candidate_file_count": pair_audit_count,
        "sensitive_candidate_file_count": sensitive_count,
        "verified_individual_labels": "unknown" if identity_count else "no",
        "human_pair_audit_labels": "unknown" if pair_audit_count else "no",
        "public_reporting_rule": (
            "Do not expose exact site, trap, coordinate, raw image path, or internal path fields."
        ),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        default=None,
        help="Root file or directory to scan. May be passed multiple times. Defaults to data and sources.",
    )
    parser.add_argument("--nrows", type=int, default=5000, help="Maximum rows sampled per table-like file.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output CSV path.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Output JSON summary path.")
    args = parser.parse_args()

    roots = [PROJECT_ROOT / "data", PROJECT_ROOT / "sources"] if args.root is None else [Path(root) for root in args.root]
    out = Path(args.output)
    summary_path = Path(args.summary)
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    if not summary_path.is_absolute():
        summary_path = PROJECT_ROOT / summary_path

    files = iter_supported_files(roots)
    rows: list[dict[str, Any]] = []
    errors = 0
    for path in files:
        try:
            summary = summarize_file(path, nrows=args.nrows)
            if summary.pop("candidate"):
                rows.append(summary)
        except Exception as exc:  # noqa: BLE001 - audit should report unreadable candidate-looking files.
            if token_match(relative(path)):
                errors += 1
                rows.append(
                    {
                        "relative_path": relative(path),
                        "source_category": "local_data"
                        if relative(path).startswith("data/")
                        else "literature_or_source"
                        if relative(path).startswith("sources/")
                        else "other",
                        "file_extension": path.suffix.lower(),
                        "rows_sampled": math.nan,
                        "n_columns": math.nan,
                        "candidate_signal": "path_or_filename",
                        "sensitive_columns": "",
                        "identity_like_columns": "",
                        "pair_audit_like_columns": "",
                        "bobcat_like_columns": "",
                        "sampled_value_token_hit_counts": "{}",
                        "sensitive_fields_present": "unknown",
                        "identity_like_fields_present": "unknown",
                        "pair_audit_like_fields_present": "unknown",
                        "read_error": repr(exc),
                    }
                )

    out.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "relative_path",
        "source_category",
        "file_extension",
        "rows_sampled",
        "n_columns",
        "candidate_signal",
        "sensitive_fields_present",
        "identity_like_fields_present",
        "pair_audit_like_fields_present",
        "sensitive_columns",
        "identity_like_columns",
        "pair_audit_like_columns",
        "bobcat_like_columns",
        "sampled_value_token_hit_counts",
        "read_error",
    ]
    pd.DataFrame(rows, columns=columns).to_csv(out, index=False)
    write_summary(rows=rows, scanned_count=len(files), summary_path=summary_path)

    print(
        "PASS phase14 UWIN bobcat inventory "
        f"scanned={len(files)} candidates={len(rows)} read_errors={errors} "
        f"output={relative(out)} summary={relative(summary_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
