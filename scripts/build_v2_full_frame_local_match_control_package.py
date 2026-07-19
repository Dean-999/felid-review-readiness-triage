#!/usr/bin/env python3
"""Build the single self-auditing PF-ERI v2 full-frame control ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
GPU_DIR = ROOT / "gpu/kaggle_v2_local_matcher_v2"
sys.path.insert(0, str(GPU_DIR))

from full_frame_execution_common import load_inventory  # noqa: E402
from full_frame_execution_orchestrator import build_parser  # noqa: E402


OUTPUT_NAME = "PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip"
EXPECTED_SHARD_COUNT = 30
EXPECTED_PAIR_COUNT = 28_295
CONTROL_FILES = (
    "full_frame_local_match_runner.py",
    "local_match_runner_v2.py",
    "local_match_execution_protocol_v2.json",
    "requirements.txt",
    "full_frame_execution_common.py",
    "full_frame_execution_orchestrator.py",
    "validate_full_frame_results.py",
    "merge_full_frame_results.py",
    "build_final_export.py",
    "README.md",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _zip_write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def build(
    shard_directory: Path,
    output_zip: Path,
    audit_json: Path,
    *,
    replace_existing: bool = False,
    test_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and independently audit the one canonical execution package."""
    if output_zip.name != OUTPUT_NAME:
        raise ValueError(f"output filename must be {OUTPUT_NAME}")
    if output_zip.exists() and not replace_existing:
        raise FileExistsError(f"refusing to overwrite control package: {output_zip}")

    inventory_path = shard_directory / "shard_inventory.json"
    manifest_root = shard_directory / "public_pair_manifests"
    specs = load_inventory(inventory_path, manifest_root)
    pair_count = sum(spec.pair_count for spec in specs)
    if len(specs) != EXPECTED_SHARD_COUNT or pair_count != EXPECTED_PAIR_COUNT:
        raise ValueError(
            "canonical package requires "
            f"{EXPECTED_SHARD_COUNT} shards and {EXPECTED_PAIR_COUNT} pairs; "
            f"found {len(specs)} shards and {pair_count} pairs"
        )
    if specs[0].shard_id != "calibration_shard_001" or specs[-1].shard_id != "development_shard_010":
        raise ValueError("inventory order does not match the frozen 30-shard design")
    declared = {f"{spec.shard_id}.csv" for spec in specs}
    actual = {path.name for path in manifest_root.glob("*.csv")}
    if actual != declared:
        raise ValueError(
            f"manifest inventory mismatch: missing={sorted(declared - actual)} "
            f"unexpected={sorted(actual - declared)}"
        )

    args = build_parser().parse_args([
        "--control-root", "/control",
        "--image-root", "/images",
        "--result-root", "/results",
        "--export-root", "/exports",
    ])
    if hasattr(args, "start_index") or args.max_shards_per_run != 1:
        raise RuntimeError("orchestrator is not configured for a fresh one-shard default")

    entries: dict[str, bytes] = {}
    for name in CONTROL_FILES:
        path = GPU_DIR / name
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"required control file missing: {path}")
        entries[name] = path.read_bytes()

    normalized_inventory = [
        {
            "shard_id": spec.shard_id,
            "manifest_path": f"public_pair_manifests/{spec.manifest_path.name}",
            "pair_count": spec.pair_count,
            "manifest_sha256": spec.manifest_sha256,
        }
        for spec in specs
    ]
    entries["shard_inventory.json"] = (
        json.dumps(normalized_inventory, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    for spec in specs:
        entries[f"public_pair_manifests/{spec.manifest_path.name}"] = spec.manifest_path.read_bytes()

    if test_summary is not None:
        entries["TEST_SUMMARY.json"] = (
            json.dumps(test_summary, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")

    package_audit = {
        "audit_version": "pferi_v2_full_frame_control_package_audit_v2",
        "status": "PASS",
        "run_mode": "fresh_full_inventory",
        "declared_shard_count": len(specs),
        "declared_pair_count": pair_count,
        "first_shard": specs[0].shard_id,
        "last_shard": specs[-1].shard_id,
        "default_max_shards_per_run": args.max_shards_per_run,
        "contains_images": False,
        "contains_restricted_linkage": False,
        "contains_prior_results": False,
        "scientific_core_sha256": sha256_bytes(entries["local_match_runner_v2.py"]),
        "wrapper_sha256": sha256_bytes(entries["full_frame_local_match_runner.py"]),
        "protocol_sha256": sha256_bytes(entries["local_match_execution_protocol_v2.json"]),
        "inventory_sha256": sha256_bytes(entries["shard_inventory.json"]),
        "claim_boundary": "Execution-control integrity only; no matcher-accuracy or biological-validity claim.",
    }
    entries["CONTROL_PACKAGE_AUDIT.json"] = (
        json.dumps(package_audit, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    entries["CHECKSUMS.sha256"] = (
        "\n".join(f"{sha256_bytes(entries[name])}  {name}" for name in sorted(entries)) + "\n"
    ).encode("utf-8")

    forbidden = [
        name
        for name in entries
        if "restricted" in name.lower()
        or name.lower().endswith((".jpg", ".jpeg", ".png", ".npy"))
    ]
    if forbidden:
        raise RuntimeError(f"forbidden control-package member: {forbidden[:3]}")

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_zip.name}.", suffix=".tmp", dir=output_zip.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            for name in sorted(entries):
                _zip_write(archive, name, entries[name])
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None or set(archive.namelist()) != set(entries):
                raise RuntimeError("control ZIP integrity or inventory check failed")
            for line in archive.read("CHECKSUMS.sha256").decode("utf-8").splitlines():
                digest, name = line.split("  ", 1)
                if sha256_bytes(archive.read(name)) != digest:
                    raise RuntimeError(f"control ZIP checksum mismatch: {name}")
        os.replace(temporary, output_zip)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    audit = {
        **package_audit,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zip_path": str(output_zip.resolve().relative_to(ROOT)),
        "zip_sha256": sha256_file(output_zip),
        "zip_file_count": len(entries),
        "zip_inventory": sorted(entries),
    }
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-directory", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--test-summary-json", type=Path)
    parser.add_argument("--replace-existing", action="store_true")
    args = parser.parse_args(argv)
    test_summary = (
        json.loads(args.test_summary_json.read_text(encoding="utf-8"))
        if args.test_summary_json
        else None
    )
    audit = build(
        args.shard_directory,
        args.output_zip,
        args.audit_json,
        replace_existing=args.replace_existing,
        test_summary=test_summary,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
