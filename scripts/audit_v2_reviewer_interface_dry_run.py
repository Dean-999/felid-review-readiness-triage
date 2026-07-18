#!/usr/bin/env python3
"""Statically audit a PF-ERI v2 blinded reviewer-interface dry-run package."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = ROOT / "schemas/pferi_v2/reviewer_interface_dry_run_contract_v1.json"
REVIEWER_VIEW_DIRNAME = "reviewer_view"
RESTRICTED_DIRNAME = "restricted"
REQUIRED_PUBLIC_FILES = {"app.py", "reviewer_packet.csv", "raw_response_template.csv", "reviewer_ui_manifest.json"}
PROHIBITED_APP_MARKERS = ("st.dataframe", "st.data_editor", "st.download_button", "st.file_uploader", "st.query_params")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def add_error(audit: dict[str, Any], code: str) -> None:
    audit["error_codes"].append(code)


def public_text_paths(view: Path) -> list[Path]:
    return sorted(path for path in view.rglob("*") if path.is_file() and path.suffix.lower() in {".csv", ".json", ".py", ".md", ".txt"})


def audit_dry_run(output_dir: Path, contract_path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    contract = load_json(contract_path)
    output_dir = output_dir.resolve()
    view = output_dir / REVIEWER_VIEW_DIRNAME
    restricted = output_dir / RESTRICTED_DIRNAME
    audit: dict[str, Any] = {
        "audit_version": "pferi_v2_reviewer_interface_static_audit_v1",
        "contract_version": contract["contract_version"],
        "status": "FAIL",
        "dry_run_directory": str(output_dir),
        "error_codes": [],
        "required_human_browser_checks": contract["required_human_browser_checks"],
    }
    if not view.is_dir():
        add_error(audit, "missing_reviewer_view_directory")
        return audit
    if not restricted.is_dir():
        add_error(audit, "missing_restricted_directory")
    public_top_level = {path.name for path in view.iterdir() if path.is_file()}
    missing_public = sorted(REQUIRED_PUBLIC_FILES - public_top_level)
    if missing_public:
        add_error(audit, "missing_public_files:" + ",".join(missing_public))
    forbidden_public_names = [path.name for path in view.rglob("*") if "restricted" in path.name.lower() or "linkage" in path.name.lower()]
    if forbidden_public_names:
        add_error(audit, "restricted_name_in_reviewer_view:" + ",".join(sorted(forbidden_public_names)))

    packet_path = view / "reviewer_packet.csv"
    if packet_path.is_file():
        packet_rows, packet_headers = read_csv(packet_path)
        audit["reviewer_packet_row_count"] = len(packet_rows)
        if packet_headers != contract["reviewer_packet_allowlist"]:
            add_error(audit, "reviewer_packet_header_mismatch")
        packet_id_pattern = re.compile(contract["review_packet_id_pattern"])
        for row in packet_rows:
            if not packet_id_pattern.fullmatch(row.get("review_packet_id", "")):
                add_error(audit, "invalid_review_packet_id")
                break
    else:
        add_error(audit, "missing_reviewer_packet")
        packet_rows = []

    response_path = view / "raw_response_template.csv"
    if response_path.is_file():
        _, response_headers = read_csv(response_path)
        if response_headers != contract["raw_response_allowlist"]:
            add_error(audit, "raw_response_header_mismatch")
    else:
        add_error(audit, "missing_raw_response_template")

    assets = view / "assets"
    asset_files = sorted(assets.glob("*.png")) if assets.is_dir() else []
    audit["opaque_asset_count"] = len(asset_files)
    if not assets.is_dir():
        add_error(audit, "missing_asset_directory")
    asset_pattern = re.compile(contract["asset_filename_pattern"])
    for asset in asset_files:
        if not asset_pattern.fullmatch(asset.name):
            add_error(audit, "nonopaque_asset_filename")
            break
    expected_asset_names = {
        f"{row.get(token_column, '')}.png"
        for row in packet_rows
        for token_column in ("left_asset_token", "right_asset_token")
    }
    if packet_rows and {asset.name for asset in asset_files} != expected_asset_names:
        add_error(audit, "asset_inventory_does_not_match_reviewer_packet")

    manifest_path = view / "reviewer_ui_manifest.json"
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
        if set(manifest) != {"instrument_version", "review_form_schema_version", "reviewer_packet_filename", "asset_directory"}:
            add_error(audit, "reviewer_ui_manifest_field_mismatch")
    app_path = view / "app.py"
    if app_path.is_file():
        app_text = app_path.read_text(encoding="utf-8").lower()
        for marker in PROHIBITED_APP_MARKERS:
            if marker in app_text:
                add_error(audit, "prohibited_interaction_control:" + marker)

    prohibited = [token.lower() for token in contract["public_view_must_not_contain"]]
    for path in public_text_paths(view):
        text = path.read_text(encoding="utf-8").lower()
        for token in prohibited:
            if token in text:
                add_error(audit, f"forbidden_public_token:{token}:{path.name}")
    linkage_path = restricted / "restricted_linkage.csv"
    if linkage_path.is_file():
        _, linkage_headers = read_csv(linkage_path)
        if linkage_headers != contract["restricted_linkage_allowlist"]:
            add_error(audit, "restricted_linkage_header_mismatch")
    else:
        add_error(audit, "missing_restricted_linkage")

    audit["status"] = "PASS" if not audit["error_codes"] else "FAIL"
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run-dir", required=True, type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    audit = audit_dry_run(args.dry_run_dir, args.contract)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
