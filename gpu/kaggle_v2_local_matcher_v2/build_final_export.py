#!/usr/bin/env python3
"""Build the single audited PF-ERI full-frame execution export ZIP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from full_frame_execution_common import (
    ExecutionPaths,
    ShardSpec,
    load_inventory,
    read_json,
    sha256_file,
)
from validate_full_frame_results import REQUIRED_RESULT_FILES, validate_full_execution


ARCHIVE_ROOT = "PF_ERI_FINAL_EXPORT"
REQUIRED_CONTROL_FILES = (
    "full_frame_local_match_runner.py",
    "local_match_runner_v2.py",
    "local_match_execution_protocol_v2.json",
    "requirements.txt",
)
OPTIONAL_REPRODUCIBILITY_FILES = (
    "full_frame_execution_common.py",
    "full_frame_execution_orchestrator.py",
    "validate_full_frame_results.py",
    "merge_full_frame_results.py",
    "build_final_export.py",
    "README.md",
)
REQUIRED_EXECUTION_CONTROL_FILES = (
    "matcher_freeze_record.json",
    "environment_report.json",
    "full_frame_smoke_test.json",
    "smoke_gate_binding.json",
    "execution_image_inventory.json",
    "model_weight_inventory.json",
    "execution_state.json",
)
REQUIRED_MERGED_FILES = (
    "canonical_measurements.csv",
    "directional_measurements.csv",
    "region_provenance.csv",
    "runtime_errors.json",
    "shard_audit_index.csv",
    "merge_audit.json",
)
REQUIRED_VALIDATION_FILES = (
    "full_frame_validation.json",
    "per_shard_validation.csv",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _arc(relative: str) -> str:
    return f"{ARCHIVE_ROOT}/{relative}"


def _csv_bytes(fieldnames: list[str], rows: list[dict[str, Any]]) -> bytes:
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _entry_bytes(source: Path | bytes) -> bytes:
    return source if isinstance(source, bytes) else source.read_bytes()


def _write_entry(archive: zipfile.ZipFile, name: str, source: Path | bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    with archive.open(info, "w") as target:
        if isinstance(source, bytes):
            target.write(source)
        else:
            with source.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    target.write(block)


def _require_file(path: Path) -> Path:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"required regular file missing: {path}")
    return path


def _verify_merge(paths: ExecutionPaths, expected_pair_count: int) -> dict[str, Any]:
    for name in REQUIRED_MERGED_FILES:
        _require_file(paths.merged_root / name)
    audit = read_json(paths.merged_root / "merge_audit.json")
    if not isinstance(audit, dict) or audit.get("status") != "PASS":
        raise RuntimeError("final export requires merge audit PASS")
    if int(audit.get("canonical_row_count", -1)) != expected_pair_count:
        raise RuntimeError("merge audit pair count does not match inventory")
    hashes = audit.get("output_sha256")
    if not isinstance(hashes, dict):
        raise RuntimeError("merge audit lacks output hashes")
    for name in REQUIRED_MERGED_FILES[:-1]:
        if hashes.get(name) != sha256_file(paths.merged_root / name):
            raise RuntimeError(f"merged output hash mismatch: {name}")
    return audit


def build_final_export(paths: ExecutionPaths, specs: Sequence[ShardSpec]) -> dict[str, Any]:
    """Create one deterministic ZIP only after current global validation passes."""
    stored_validation_path = _require_file(paths.validation_root / "full_frame_validation.json")
    stored_validation = read_json(stored_validation_path)
    if not isinstance(stored_validation, dict) or stored_validation.get("status") != "PASS":
        raise RuntimeError("final export requires stored global validation PASS")
    state_path = _require_file(paths.control_state_dir / "execution_state.json")
    state = read_json(state_path)
    if state.get("status") != "RUN_COMPLETE":
        raise RuntimeError("final export requires RUN_COMPLETE; current state is not export-eligible")
    if not state.get("execution_fingerprint"):
        raise RuntimeError("final export requires a complete execution control fingerprint")
    current_validation = validate_full_execution(specs, paths)
    if current_validation.get("status") != "PASS":
        raise RuntimeError(
            "final export requires current global validation PASS: "
            + ",".join(current_validation.get("error_codes", []))
        )
    for field in ("expected_pair_count", "execution_fingerprints"):
        if stored_validation.get(field) != current_validation.get(field):
            raise RuntimeError("stored validation is stale or belongs to another execution")
    merge_audit = _verify_merge(paths, current_validation["expected_pair_count"])

    for name in REQUIRED_EXECUTION_CONTROL_FILES:
        _require_file(paths.control_state_dir / name)
    smoke = read_json(paths.control_state_dir / "full_frame_smoke_test.json")
    if smoke.get("status") != "PASS":
        raise RuntimeError("final export requires smoke gate PASS")

    entries: dict[str, Path | bytes] = {}
    entries[_arc("control/shard_inventory.json")] = _require_file(paths.inventory_path)
    for spec in specs:
        entries[_arc(f"control/public_pair_manifests/{spec.manifest_path.name}")] = _require_file(
            spec.manifest_path
        )
    for name in REQUIRED_CONTROL_FILES:
        entries[_arc(f"control/software/{name}")] = _require_file(paths.control_root / name)
    for name in OPTIONAL_REPRODUCIBILITY_FILES:
        path = paths.control_root / name
        if path.is_file() and not path.is_symlink():
            entries[_arc(f"control/software/{name}")] = path
    for name in REQUIRED_EXECUTION_CONTROL_FILES:
        entries[_arc(f"execution_control/{name}")] = _require_file(paths.control_state_dir / name)
    for spec in specs:
        for name in REQUIRED_RESULT_FILES:
            entries[_arc(f"shard_results/{spec.shard_id}/{name}")] = _require_file(
                paths.shard_results_root / spec.output_dir_name / name
            )
    for name in REQUIRED_VALIDATION_FILES:
        entries[_arc(f"validation/{name}")] = _require_file(paths.validation_root / name)
    for name in REQUIRED_MERGED_FILES:
        entries[_arc(f"merged/{name}")] = _require_file(paths.merged_root / name)

    forbidden = [
        name for name in entries
        if "pair_checkpoints" in name
        or name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"))
    ]
    if forbidden:
        raise RuntimeError(f"forbidden image/checkpoint payload in final export: {forbidden[:3]}")

    payload_rows = []
    for name in sorted(entries):
        data = _entry_bytes(entries[name])
        payload_rows.append(
            {
                "relative_path": name,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest_name = _arc("export_manifest.csv")
    entries[manifest_name] = _csv_bytes(["relative_path", "size_bytes", "sha256"], payload_rows)
    summary_name = _arc("EXECUTION_SUMMARY.md")
    entries[summary_name] = (
        "# PF-ERI v2 full-frame execution summary\n\n"
        f"- Status: PASS\n- Shards: {len(specs)}\n"
        f"- Pairs: {current_validation['expected_pair_count']}\n"
        f"- Execution fingerprint: `{current_validation['execution_fingerprints'][0]}`\n"
        "- Scope: engineering completeness and reproducibility; this is not an accuracy claim.\n"
    ).encode("utf-8")
    audit_name = _arc("FINAL_EXPORT_AUDIT.json")
    export_audit_inside = {
        "export_version": "pferi_v2_full_frame_final_export_v2",
        "created_at_utc": now_utc(),
        "status": "PASS",
        "shard_count": len(specs),
        "pair_count": current_validation["expected_pair_count"],
        "execution_fingerprints": current_validation["execution_fingerprints"],
        "payload_file_count": len(payload_rows) + 1,
        "payload_manifest_sha256": hashlib.sha256(entries[manifest_name]).hexdigest(),
        "merge_audit_sha256": sha256_file(paths.merged_root / "merge_audit.json"),
        "validation_sha256": sha256_file(stored_validation_path),
        "excludes_images": True,
        "excludes_pair_checkpoints": True,
    }
    entries[audit_name] = _json_bytes(export_audit_inside)

    checksum_name = _arc("CHECKSUMS.sha256")
    checksum_lines = []
    for name in sorted(entries):
        digest = hashlib.sha256(_entry_bytes(entries[name])).hexdigest()
        checksum_lines.append(f"{digest}  {name}")
    entries[checksum_name] = ("\n".join(checksum_lines) + "\n").encode("utf-8")

    paths.export_root.mkdir(parents=True, exist_ok=True)
    unexpected_existing = [path for path in paths.export_root.iterdir() if path != paths.final_export_zip]
    if unexpected_existing:
        raise RuntimeError("EXPORT_ROOT must contain only the final ZIP target")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".PF_ERI_FINAL_EXPORT.", suffix=".zip.tmp", dir=paths.export_root
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            for name in sorted(entries):
                _write_entry(archive, name, entries[name])
        with zipfile.ZipFile(temporary) as archive:
            bad_member = archive.testzip()
            names = archive.namelist()
            checksum_rows = archive.read(checksum_name).decode("utf-8").splitlines()
            for row in checksum_rows:
                digest, member = row.split("  ", 1)
                if hashlib.sha256(archive.read(member)).hexdigest() != digest:
                    raise RuntimeError(f"final ZIP checksum mismatch: {member}")
            manifest_rows = list(csv.DictReader(io.StringIO(archive.read(manifest_name).decode("utf-8"))))
            for row in manifest_rows:
                data = archive.read(row["relative_path"])
                if len(data) != int(row["size_bytes"]) or hashlib.sha256(data).hexdigest() != row["sha256"]:
                    raise RuntimeError(f"final ZIP manifest mismatch: {row['relative_path']}")
        if bad_member is not None or set(names) != set(entries):
            raise RuntimeError(f"final ZIP integrity/inventory failure: bad_member={bad_member}")
        os.replace(temporary, paths.final_export_zip)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    external_audit = {
        **export_audit_inside,
        "zip_path": str(paths.final_export_zip),
        "zip_sha256": sha256_file(paths.final_export_zip),
        "zip_file_count": len(entries),
        "zip_integrity": "PASS",
    }
    return external_audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    args = parser.parse_args(argv)
    paths = ExecutionPaths.from_roots(
        control_root=args.control_root,
        image_root=Path("."),
        result_root=args.result_root,
        export_root=args.export_root,
    )
    specs = load_inventory(paths.inventory_path, paths.manifest_root)
    audit = build_final_export(paths, specs)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
