#!/usr/bin/env python3
"""Build an opaque, byte-verified local-matching package for the v2 pilot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIR_COLUMNS = ["pair_execution_id", "left_asset_filename", "right_asset_filename"]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--restricted-linkage", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--asset-directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_directory.exists() or args.output_zip.exists():
        raise FileExistsError("refusing to overwrite local-match package")
    packets = rows(args.packet_manifest)
    linkage = {row["annotation_packet_id"]: row for row in rows(args.restricted_linkage)}
    execution = {row["image_id"]: row for row in rows(args.execution_manifest)}
    if len(packets) != 160 or len({row["annotation_packet_id"] for row in packets}) != 160:
        raise ValueError("expected exactly 160 unique opaque annotation packets")
    pairs, asset_hashes = [], {}
    for packet in packets:
        link = linkage.get(packet["annotation_packet_id"])
        if link is None:
            raise ValueError("opaque packet lacks restricted linkage")
        filenames = []
        for image_key, asset_key in (("left_image_id", "left_asset_token"), ("right_image_id", "right_asset_token")):
            source = execution.get(link[image_key])
            if source is None:
                raise ValueError("restricted linkage lacks execution image")
            matches = list(args.asset_directory.glob(f"{packet[asset_key]}.*"))
            if len(matches) != 1 or sha(matches[0]) != source["content_sha256"]:
                raise ValueError("opaque asset byte integrity failure")
            filenames.append(matches[0].name)
            asset_hashes[matches[0].name] = source["content_sha256"]
        pairs.append({"pair_execution_id": packet["annotation_packet_id"], "left_asset_filename": filenames[0], "right_asset_filename": filenames[1]})
    with tempfile.TemporaryDirectory(dir=args.output_directory.parent, prefix=".v2_local_match_") as temp:
        package = Path(temp) / "v2_local_match_execution_package"; image_dir = package / "images"; image_dir.mkdir(parents=True)
        for filename in sorted(asset_hashes): shutil.copyfile(args.asset_directory / filename, image_dir / filename)
        with (package / "pair_execution_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=PAIR_COLUMNS); writer.writeheader(); writer.writerows(pairs)
        archive_path = Path(temp) / args.output_zip.name
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
            for item in sorted(package.rglob("*")):
                if item.is_file(): archive.write(item, item.relative_to(package.parent))
        with zipfile.ZipFile(archive_path) as archive:
            for filename, expected in asset_hashes.items():
                member = f"v2_local_match_execution_package/images/{filename}"
                if hashlib.sha256(archive.read(member)).hexdigest() != expected: raise ValueError("ZIP asset integrity failure")
        shutil.move(str(package), args.output_directory); shutil.move(str(archive_path), args.output_zip)
    audit = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS", "pair_count": len(pairs), "asset_count": len(asset_hashes), "zip_sha256": sha(args.output_zip), "byte_verification": "PASS", "claim_boundary": "Opaque outcome-free local-match execution input only; no canonical IDs, image IDs, identity, descriptor, score, rank, route, or outcome fields are present."}
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
