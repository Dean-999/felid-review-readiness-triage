#!/usr/bin/env python3
"""Build an outcome-free, opaque v2 reviewer-interface dry-run package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v2_reviewer_interface_dry_run as static_auditor


DEFAULT_CONTRACT_PATH = ROOT / "schemas/pferi_v2/reviewer_interface_dry_run_contract_v1.json"
PILOT_COLUMNS = ["contract_version", "pilot_pair_id", "canonical_pair_id", "selection_seed_id", "selection_stratum", "pair_availability_status", "pilot_inclusion_status", "exclusion_reason"]
CANONICAL_COLUMNS = ["contract_version", "canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id", "source_dataset", "pair_availability_status", "pair_inclusion_status", "exclusion_reason"]
EXECUTION_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
REVIEWER_PACKET_COLUMNS = ["review_packet_id", "left_asset_token", "right_asset_token", "instrument_version", "review_form_schema_version"]
RAW_RESPONSE_COLUMNS = ["review_packet_id", "raw_reviewer_response_id", "review_decision", "reason_codes", "confidence", "optional_note", "submitted_at_utc", "technical_problem_flag"]
RESTRICTED_LINKAGE_COLUMNS = ["review_packet_id", "canonical_pair_id", "left_image_id", "right_image_id", "reviewer_assignment_id", "packet_batch_id"]
RESTRICTED_ASSET_COLUMNS = ["asset_token", "image_id", "content_sha256", "rendered_asset_filename"]
HUMAN_AUDIT_COLUMNS = ["check_id", "required_check", "status", "prohibited_exposure_observed", "exposed_records_or_na", "leak_source_or_na", "remediation_or_na", "retest_evidence_or_na", "final_disposition", "auditor_id", "auditor_role", "audited_at_utc", "notes"]


APP_SOURCE = '''import csv
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
PACKET_PATH = HERE / "reviewer_packet.csv"
ASSET_DIRECTORY = HERE / "assets"
RESPONSE_PATH = Path(os.environ.get("PF_ERI_V2_RAW_RESPONSE_PATH", str(HERE.parent / "private_responses" / "raw_responses.csv")))
RESPONSE_COLUMNS = ["review_packet_id", "raw_reviewer_response_id", "review_decision", "reason_codes", "confidence", "optional_note", "submitted_at_utc", "technical_problem_flag"]


def read_packet():
    with PACKET_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_response(row):
    RESPONSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not RESPONSE_PATH.exists()
    with RESPONSE_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESPONSE_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


st.set_page_config(page_title="Pair review", layout="wide")
packet = read_packet()
if not packet:
    st.error("No review packets are available.")
    st.stop()
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
row = packet[st.session_state.current_index]
st.title("Pair review")
st.caption(row["review_packet_id"])
left, right = st.columns(2)
left.image(ASSET_DIRECTORY / (row["left_asset_token"] + ".png"), caption="Left image", use_container_width=True)
right.image(ASSET_DIRECTORY / (row["right_asset_token"] + ".png"), caption="Right image", use_container_width=True)
with st.form("review_response", clear_on_submit=True):
    decision = st.selectbox("Decision", ["review_ready", "not_review_ready", "uncertain"])
    reason_codes = st.text_input("Reason codes")
    confidence = st.selectbox("Confidence", ["low", "medium", "high"])
    optional_note = st.text_area("Optional note")
    technical_problem_flag = st.checkbox("Technical problem")
    submitted = st.form_submit_button("Save response")
if submitted:
    append_response({
        "review_packet_id": row["review_packet_id"],
        "raw_reviewer_response_id": "response_" + uuid.uuid4().hex,
        "review_decision": decision,
        "reason_codes": reason_codes,
        "confidence": confidence,
        "optional_note": optional_note,
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "technical_problem_flag": "yes" if technical_problem_flag else "no",
    })
    st.session_state.current_index = (st.session_state.current_index + 1) % len(packet)
    st.success("Response saved.")
'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def require_headers(headers: list[str], expected: list[str], label: str) -> None:
    if headers != expected:
        raise ValueError(f"{label} headers differ from the locked contract")


def opaque_token(seed: str, image_id: str) -> str:
    return "asset_" + hashlib.sha256(f"{seed}|{image_id}".encode("utf-8")).hexdigest()[:20]


def source_path(project_root: Path, relative_path: str) -> Path:
    candidate = (project_root / relative_path).resolve()
    if not candidate.is_relative_to(project_root.resolve()):
        raise ValueError("execution manifest image path escapes project root")
    return candidate


def render_opaque_asset(source: Path, target: Path) -> None:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((1600, 1600))
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format="PNG")


def selected_pairs(pilot_rows: list[dict[str, str]], canonical_rows: list[dict[str, str]], count: int, seed: str) -> list[dict[str, str]]:
    included = {
        row["canonical_pair_id"]
        for row in pilot_rows
        if row["pilot_inclusion_status"] == "included" and row["pair_availability_status"] == "available"
    }
    canonical = {row["canonical_pair_id"]: row for row in canonical_rows if row["canonical_pair_id"] in included}
    if len(canonical) != len(included):
        raise ValueError("every included pilot pair must resolve exactly once in the canonical manifest")
    if len(canonical) < count:
        raise ValueError("not enough outcome-free pilot pairs for the configured dry run")
    return sorted(canonical.values(), key=lambda row: hashlib.sha256(f"{seed}|{row['canonical_pair_id']}".encode("utf-8")).hexdigest())[:count]


def validate_pilot_audit(path: Path) -> None:
    audit = load_json(path)
    if audit.get("status") != "PASS" or audit.get("confirmation_overlap_rule") != "pilot_pairs_are_ineligible_for_v2_confirmation_samples":
        raise ValueError("pilot audit does not establish the required confirmation exclusion")


def human_audit_rows(contract: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "check_id": f"check_{index:02d}",
            "required_check": requirement,
            "status": "not_started",
            "prohibited_exposure_observed": "not_recorded",
            "exposed_records_or_na": "",
            "leak_source_or_na": "",
            "remediation_or_na": "",
            "retest_evidence_or_na": "",
            "final_disposition": "pending",
            "auditor_id": "",
            "auditor_role": "",
            "audited_at_utc": "",
            "notes": "",
        }
        for index, requirement in enumerate(contract["required_human_browser_checks"], start=1)
    ]


def write_independent_auditor_delivery(view: Path, audit_dir: Path) -> None:
    guide = audit_dir / "INDEPENDENT_AUDITOR_GUIDE_zh.md"
    guide.write_text(
        "# PF-ERI v2 独立浏览器泄漏审计指南\n\n"
        "你收到的是 outcome collection 之前的测试界面，不是正式标注任务。你不得成为之后的 first-pass reviewer 或 adjudicator，且不要向项目负责人报告任何关于图像内容的判断。\n\n"
        "解压本包后，在根目录运行 `python -m streamlit run reviewer_view/app.py`，只通过浏览器审计。逐项完成 `human_browser_leakage_checklist.csv`：检查可见页面文字、图片 alt text 与 token、URL 和浏览器历史、开发者工具的 DOM 和网络请求、可下载文件、搜索/排序/筛选控件，以及保存回答后是否可能看到他人的回答。\n\n"
        "若发现 descriptor、分数、rank、route、feature、身份、相机或来源信息、既往回答、majority/adjudication 或任何能够推断这些条件的信息，请将相应行标记为 `fail`，记录暴露的 packet、泄漏源、修复和复测证据。不要删除或改写泄漏痕迹。只有所有行均为 `pass`、`prohibited_exposure_observed=no`、`final_disposition=no_leak_confirmed`，且你以 `independent_interface_auditor` 身份签署，验证器才可能通过。\n",
        encoding="utf-8",
    )
    delivery = audit_dir / "PF_ERI_V2_INTERFACE_AUDIT_DELIVERY.zip"
    with zipfile.ZipFile(delivery, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(view.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(view.parent))
        archive.write(audit_dir / "human_browser_leakage_checklist.csv", "human_browser_leakage_checklist.csv")
        archive.write(guide, guide.name)


def build_dry_run(*, pilot_manifest: Path, pilot_audit: Path, canonical_pairs: Path, execution_manifest: Path, project_root: Path, output_dir: Path, contract_path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    contract = load_json(contract_path)
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing dry-run directory: {output_dir}")
    validate_pilot_audit(pilot_audit)
    pilot_rows, pilot_headers = read_csv(pilot_manifest)
    canonical_rows, canonical_headers = read_csv(canonical_pairs)
    execution_rows, execution_headers = read_csv(execution_manifest)
    require_headers(pilot_headers, PILOT_COLUMNS, "pilot manifest")
    require_headers(canonical_headers, CANONICAL_COLUMNS, "canonical-pair manifest")
    require_headers(execution_headers, EXECUTION_COLUMNS, "execution manifest")
    pairs = selected_pairs(pilot_rows, canonical_rows, int(contract["dry_run_pair_count"]), contract["selection_seed"])
    execution_by_id = {row["image_id"]: row for row in execution_rows}
    required_image_ids = {image_id for pair in pairs for image_id in (pair["endpoint_a_image_id"], pair["endpoint_b_image_id"])}
    if len(execution_by_id) != len(execution_rows) or not required_image_ids.issubset(execution_by_id):
        raise ValueError("execution manifest does not uniquely cover every selected dry-run image")
    view = output_dir / "reviewer_view"
    assets = view / "assets"
    restricted = output_dir / "restricted"
    asset_rows: list[dict[str, str]] = []
    for image_id in sorted(required_image_ids):
        execution = execution_by_id[image_id]
        source = source_path(project_root, execution["image_path_relative"])
        if not source.is_file() or sha256_file(source) != execution["content_sha256"]:
            raise ValueError(f"input image verification failed: {image_id}")
        token = opaque_token(contract["selection_seed"], image_id)
        filename = token + ".png"
        render_opaque_asset(source, assets / filename)
        asset_rows.append({"asset_token": token, "image_id": image_id, "content_sha256": execution["content_sha256"], "rendered_asset_filename": filename})
    asset_by_image = {row["image_id"]: row["asset_token"] for row in asset_rows}
    packet_rows: list[dict[str, str]] = []
    linkage_rows: list[dict[str, str]] = []
    for index, pair in enumerate(pairs, start=1):
        packet_id = f"dryrun_packet_{index:03d}"
        packet_rows.append({"review_packet_id": packet_id, "left_asset_token": asset_by_image[pair["endpoint_a_image_id"]], "right_asset_token": asset_by_image[pair["endpoint_b_image_id"]], "instrument_version": "pferi_v2_review_instrument_v1", "review_form_schema_version": "pferi_v2_raw_response_v1"})
        linkage_rows.append({"review_packet_id": packet_id, "canonical_pair_id": pair["canonical_pair_id"], "left_image_id": pair["endpoint_a_image_id"], "right_image_id": pair["endpoint_b_image_id"], "reviewer_assignment_id": "independent_interface_auditor_only", "packet_batch_id": "pferi_v2_interface_dry_run_20260714"})
    write_csv(view / "reviewer_packet.csv", REVIEWER_PACKET_COLUMNS, packet_rows)
    write_csv(view / "raw_response_template.csv", RAW_RESPONSE_COLUMNS, [])
    write_csv(restricted / "restricted_linkage.csv", RESTRICTED_LINKAGE_COLUMNS, linkage_rows)
    write_csv(restricted / "restricted_asset_map.csv", RESTRICTED_ASSET_COLUMNS, asset_rows)
    audit_dir = output_dir / "independent_browser_audit"
    write_csv(audit_dir / "human_browser_leakage_checklist.csv", HUMAN_AUDIT_COLUMNS, human_audit_rows(contract))
    (audit_dir / "README.md").write_text(
        "# Independent Browser Leakage Audit\n\n"
        "This checklist must be completed by a person who will not act as a first-pass reviewer or adjudicator. "
        "Launch `streamlit run reviewer_view/app.py` from the dry-run directory and inspect the rendered browser, not only CSV files. "
        "Check every required row using page content, browser URL/history, image names and alt text, downloads, controls, developer-tools DOM and network requests, and response isolation. "
        "If any prohibited exposure is found, set the row to `fail`, record the affected packet(s), source, remediation, and retest evidence, and do not start real outcome collection. "
        "Only an all-pass checklist can be evaluated with `scripts/validate_v2_reviewer_interface_human_audit.py`.\n",
        encoding="utf-8",
    )
    (view / "reviewer_ui_manifest.json").write_text(json.dumps({"instrument_version": "pferi_v2_review_instrument_v1", "review_form_schema_version": "pferi_v2_raw_response_v1", "reviewer_packet_filename": "reviewer_packet.csv", "asset_directory": "assets"}, indent=2) + "\n", encoding="utf-8")
    (view / "app.py").write_text(APP_SOURCE, encoding="utf-8")
    write_independent_auditor_delivery(view, audit_dir)
    build_audit = {"build_version": "pferi_v2_reviewer_interface_dry_run_builder_v1", "status": "PASS", "contract_version": contract["contract_version"], "pilot_manifest_sha256": sha256_file(pilot_manifest), "pilot_audit_sha256": sha256_file(pilot_audit), "canonical_pairs_sha256": sha256_file(canonical_pairs), "execution_manifest_sha256": sha256_file(execution_manifest), "selected_pair_count": len(pairs), "selected_image_count": len(required_image_ids), "claim_boundary": contract["claim_boundary"]}
    (restricted / "build_audit.json").write_text(json.dumps(build_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    static_audit = static_auditor.audit_dry_run(output_dir, contract_path)
    (output_dir / "machine_static_audit.json").write_text(json.dumps(static_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if static_audit["status"] != "PASS":
        raise RuntimeError("generated dry-run package failed its static leakage audit")
    return {**build_audit, "machine_static_audit_status": static_audit["status"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-manifest", type=Path, required=True)
    parser.add_argument("--pilot-audit", type=Path, required=True)
    parser.add_argument("--canonical-pairs", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    args = parser.parse_args(argv)
    audit = build_dry_run(pilot_manifest=args.pilot_manifest, pilot_audit=args.pilot_audit, canonical_pairs=args.canonical_pairs, execution_manifest=args.execution_manifest, project_root=args.project_root, output_dir=args.output_dir, contract_path=args.contract)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
