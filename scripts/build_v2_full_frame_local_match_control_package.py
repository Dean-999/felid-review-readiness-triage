#!/usr/bin/env python3
"""Package the full-frame runner and public shard manifests without restricted linkage or images."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
GPU_DIR = ROOT / "gpu/kaggle_v2_local_matcher_v2"
CONTROL_FILES = (
    "full_frame_local_match_runner.py",
    "local_match_runner_v2.py",
    "local_match_execution_protocol_v2.json",
    "requirements.txt",
    "README_FULL_FRAME_KAGGLE.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(
    shard_directory: Path,
    output_zip: Path,
    audit_json: Path,
    *,
    replace_existing: bool = False,
) -> dict[str, object]:
    if output_zip.exists():
        if not replace_existing:
            raise FileExistsError(f"refusing to overwrite control package: {output_zip}")
        output_zip.unlink()
    public_manifest_dir = shard_directory / "public_pair_manifests"
    inventory = shard_directory / "shard_inventory.json"
    manifests = sorted(public_manifest_dir.glob("*.csv"))
    if len(manifests) != 30 or not inventory.is_file():
        raise ValueError("expected exactly 30 public shard manifests and one inventory")
    files = [GPU_DIR / name for name in CONTROL_FILES]
    if any(not path.is_file() for path in files):
        raise FileNotFoundError("one or more full-frame control files are missing")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=path.name)
        archive.write(inventory, arcname="shard_inventory.json")
        for path in manifests:
            archive.write(path, arcname=f"public_pair_manifests/{path.name}")
    with zipfile.ZipFile(output_zip) as archive:
        bad_member = archive.testzip()
        names = archive.namelist()
    forbidden = [name for name in names if "restricted" in name.lower() or name.lower().endswith(('.jpg', '.jpeg', '.png'))]
    status = "PASS" if bad_member is None and not forbidden and len(names) == len(files) + 1 + len(manifests) else "FAIL"
    audit = {
        "audit_version": "pferi_v2_full_frame_local_match_control_package_audit_v1",
        "status": status,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zip_path": str(output_zip.resolve().relative_to(ROOT)),
        "zip_sha256": sha256_file(output_zip),
        "file_count": len(names),
        "zip_inventory": names,
        "zip_integrity_bad_member": bad_member,
        "forbidden_member_count": len(forbidden),
        "forbidden_members": forbidden,
        "contains_images": False,
        "contains_restricted_linkage": False,
        "public_shard_manifest_count": len(manifests),
        "latest_runner_sha256": sha256_file(GPU_DIR / "local_match_runner_v2.py"),
        "full_frame_wrapper_sha256": sha256_file(GPU_DIR / "full_frame_local_match_runner.py"),
        "claim_boundary": "Code and opaque computational shard manifests only; no images, canonical linkage, outcomes, or identity truth.",
    }
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-directory", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--replace-existing", action="store_true")
    args = parser.parse_args(argv)
    audit = build(
        args.shard_directory,
        args.output_zip,
        args.audit_json,
        replace_existing=args.replace_existing,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
