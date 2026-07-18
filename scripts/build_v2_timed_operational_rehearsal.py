#!/usr/bin/env python3
"""Build an opaque, outcome-free timed operational rehearsal for PF-ERI v2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_timed_operational_rehearsal_contract_v2"
PILOT_COLUMNS = [
    "contract_version", "pilot_pair_id", "canonical_pair_id", "selection_seed_id",
    "selection_stratum", "pair_availability_status", "pilot_inclusion_status", "exclusion_reason",
]
CANONICAL_COLUMNS = [
    "contract_version", "canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id",
    "source_dataset", "pair_availability_status", "pair_inclusion_status", "exclusion_reason",
]
EXECUTION_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
RESTRICTED_LINKAGE_COLUMNS = ["rehearsal_packet_id", "canonical_pair_id", "left_image_id", "right_image_id"]
RESTRICTED_ASSET_COLUMNS = ["asset_token", "image_id", "content_sha256", "rendered_asset_filename"]
ALLOCATION_COLUMNS = ["rehearsal_participant_id", "rehearsal_packet_id", "rehearsal_role", "task_order"]
V2_PARTICIPANT_CODES = ("T04V2-N4K8C", "T04V2-Q7M2H", "T04V2-X5R9L")


APP_SOURCE = r'''import csv
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
PACKET_PATH = HERE / "rehearsal_packet.csv"
ASSET_DIRECTORY = HERE / "assets"
LOG_DIRECTORY = Path(os.environ.get("PF_ERI_V2_OPERATIONAL_LOG_DIR", str(HERE.parent / "operational_logs")))
ASSIGNMENT_PATH_TEXT = os.environ.get("PF_ERI_V2_ASSIGNMENT_FILE", "")
RESPONSE_COLUMNS = ["rehearsal_packet_id", "operational_response_id", "rehearsal_participant_id", "rehearsal_role", "task_started_at_utc", "task_submitted_at_utc", "elapsed_seconds", "completion_status", "technical_problem_category"]
ALLOCATION_COLUMNS = ["rehearsal_participant_id", "rehearsal_packet_id", "rehearsal_role", "task_order"]


def read_packet():
    with PACKET_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_participant_id(value):
    candidate = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,40}", candidate):
        raise ValueError("Use the assigned opaque participant code.")
    return candidate


def read_assignments():
    if not ASSIGNMENT_PATH_TEXT:
        raise RuntimeError("The coordinator must set PF_ERI_V2_ASSIGNMENT_FILE before starting the rehearsal.")
    assignment_path = Path(ASSIGNMENT_PATH_TEXT)
    with assignment_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != ALLOCATION_COLUMNS:
            raise RuntimeError("The restricted assignment manifest has an unexpected schema.")
        rows = list(reader)
    if not rows:
        raise RuntimeError("The restricted assignment manifest is empty.")
    assignment_keys = [(row["rehearsal_participant_id"], row["rehearsal_packet_id"]) for row in rows]
    if len(assignment_keys) != len(set(assignment_keys)):
        raise RuntimeError("The restricted assignment manifest contains a duplicate participant-packet task.")
    return rows


def submitted_packets(participant_id):
    target = LOG_DIRECTORY / (participant_id + ".csv")
    if not target.exists():
        return set()
    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row["rehearsal_packet_id"] for row in rows if row.get("rehearsal_participant_id") == participant_id}


def start_task_clock():
    st.session_state.started_at = datetime.now(timezone.utc)
    st.session_state.started_perf_counter = time.perf_counter()


def append_response(participant_id, row):
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    target = LOG_DIRECTORY / (participant_id + ".csv")
    write_header = not target.exists()
    with target.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESPONSE_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


st.set_page_config(page_title="Operational rehearsal", layout="wide")
packet_rows = read_packet()
packet = {row["rehearsal_packet_id"]: row for row in packet_rows}
if not packet_rows:
    st.error("No rehearsal packets are available.")
    st.stop()
try:
    assignments = read_assignments()
except (OSError, RuntimeError) as error:
    st.error(str(error))
    st.stop()
st.title("Operational rehearsal")
st.caption("This is a workflow-timing rehearsal, not an image-judgement task. Do not record or discuss an opinion about the images.")

if "participant_id" not in st.session_state:
    with st.form("participant_access", clear_on_submit=True):
        submitted_participant = st.text_input("Assigned participant code")
        begin = st.form_submit_button("Begin assigned operational rehearsal")
    if begin:
        try:
            participant_id = safe_participant_id(submitted_participant)
        except ValueError as error:
            st.error(str(error))
            st.stop()
        if not any(row["rehearsal_participant_id"] == participant_id for row in assignments):
            st.error("This code has no assigned operational rehearsal tasks.")
            st.stop()
        st.session_state.participant_id = participant_id
        start_task_clock()
        st.rerun()
    st.stop()

participant = st.session_state.participant_id
assigned = sorted(
    (row for row in assignments if row["rehearsal_participant_id"] == participant),
    key=lambda row: int(row["task_order"]),
)
completed_packet_ids = submitted_packets(participant)
remaining = [row for row in assigned if row["rehearsal_packet_id"] not in completed_packet_ids]
if not remaining:
    st.success("All assigned operational tasks are recorded. Stop here and notify the coordinator.")
    st.stop()

assignment = remaining[0]
row = packet.get(assignment["rehearsal_packet_id"])
if row is None:
    st.error("The assigned packet is not present in the public packet manifest.")
    st.stop()
if "started_at" not in st.session_state or "started_perf_counter" not in st.session_state:
    start_task_clock()
st.caption(row["rehearsal_packet_id"])
st.caption("Assigned workflow role: " + assignment["rehearsal_role"])
left, right = st.columns(2)
left.image(ASSET_DIRECTORY / (row["left_asset_token"] + ".png"), caption="Left image", use_container_width=True)
right.image(ASSET_DIRECTORY / (row["right_asset_token"] + ".png"), caption="Right image", use_container_width=True)
with st.form("operational_response", clear_on_submit=True):
    completion = st.selectbox("Task status", ["completed", "technical_interruption"])
    technical_category = st.selectbox("Technical issue category", ["none", "image_display", "page_or_network", "save_or_session", "other_technical"])
    submitted = st.form_submit_button("Record operational completion")
if submitted:
    finished_at = datetime.now(timezone.utc)
    elapsed = max(0.0, time.perf_counter() - st.session_state.started_perf_counter)
    append_response(participant, {
        "rehearsal_packet_id": row["rehearsal_packet_id"],
        "operational_response_id": "operation_" + uuid.uuid4().hex,
        "rehearsal_participant_id": participant,
        "rehearsal_role": assignment["rehearsal_role"],
        "task_started_at_utc": st.session_state.started_at.isoformat(),
        "task_submitted_at_utc": finished_at.isoformat(),
        "elapsed_seconds": round(elapsed, 3),
        "completion_status": completion,
        "technical_problem_category": technical_category,
    })
    start_task_clock()
    st.success("Operational entry recorded. Continue to the next task.")
    st.rerun()
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


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


def render(source: Path, target: Path) -> None:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((1600, 1600))
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format="PNG")


def select_pilot_pairs(pilot_rows: list[dict[str, str]], canonical_rows: list[dict[str, str]], count: int, seed: str, excluded_pair_ids: set[str] | None = None) -> list[dict[str, str]]:
    eligible = {
        row["canonical_pair_id"] for row in pilot_rows
        if row["pilot_inclusion_status"] == "included" and row["pair_availability_status"] == "available"
    }
    eligible -= excluded_pair_ids or set()
    canonical = {row["canonical_pair_id"]: row for row in canonical_rows if row["canonical_pair_id"] in eligible}
    if len(canonical) != len(eligible) or len(canonical) < count:
        raise ValueError("Pilot pairs do not resolve to enough available canonical pairs")
    return sorted(canonical.values(), key=lambda row: hashlib.sha256(f"{seed}|{row['canonical_pair_id']}".encode("utf-8")).hexdigest())[:count]


def read_retired_pair_ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    rows, headers = read_csv(path)
    require_headers(headers, ["canonical_pair_id"], "retired rehearsal-pair ledger")
    retired = {row["canonical_pair_id"] for row in rows if row["canonical_pair_id"]}
    if len(retired) != len(rows):
        raise ValueError("Retired rehearsal-pair ledger contains a blank or duplicate canonical_pair_id")
    return retired


def default_v2_allocation(packet_ids: list[str]) -> list[dict[str, str]]:
    if len(packet_ids) != 24:
        raise ValueError("The v2 default allocation requires exactly 24 rehearsal packets")
    first_half = set(packet_ids[:12])
    role_by_participant = {
        V2_PARTICIPANT_CODES[0]: {packet_id: "first_pass_rehearsal" if packet_id in first_half else "adjudication_rehearsal" for packet_id in packet_ids},
        V2_PARTICIPANT_CODES[1]: {packet_id: "adjudication_rehearsal" if packet_id in first_half else "first_pass_rehearsal" for packet_id in packet_ids},
        V2_PARTICIPANT_CODES[2]: {packet_id: "first_pass_rehearsal" for packet_id in packet_ids},
    }
    return [
        {"rehearsal_participant_id": participant, "rehearsal_packet_id": packet_id, "rehearsal_role": role_by_participant[participant][packet_id], "task_order": str(index)}
        for participant in V2_PARTICIPANT_CODES
        for index, packet_id in enumerate(packet_ids, start=1)
    ]


def static_audit(output_dir: Path, contract: dict[str, Any]) -> dict[str, Any]:
    view = output_dir / "reviewer_view"
    audit: dict[str, Any] = {"audit_version": "pferi_v2_timed_operational_rehearsal_static_audit_v1", "status": "FAIL", "error_codes": []}
    packet, headers = read_csv(view / "rehearsal_packet.csv")
    if headers != contract["reviewer_packet_allowlist"]:
        audit["error_codes"].append("packet_header_mismatch")
    assets = sorted((view / "assets").glob("*.png"))
    expected = {f"{row['left_asset_token']}.png" for row in packet} | {f"{row['right_asset_token']}.png" for row in packet}
    if {item.name for item in assets} != expected:
        audit["error_codes"].append("asset_inventory_mismatch")
    import re
    asset_pattern = re.compile(contract["asset_filename_pattern"])
    packet_pattern = re.compile(contract["rehearsal_packet_id_pattern"])
    if any(not asset_pattern.fullmatch(item.name) for item in assets):
        audit["error_codes"].append("nonopaque_asset_filename")
    if any(not packet_pattern.fullmatch(row["rehearsal_packet_id"]) for row in packet):
        audit["error_codes"].append("nonopaque_packet_id")
    forbidden = [item.lower() for item in contract["public_view_must_not_contain"]]
    for path in sorted(view.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".py", ".md", ".txt"}:
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                if token in text:
                    audit["error_codes"].append(f"forbidden_public_token:{token}:{path.name}")
    audit["packet_count"] = len(packet)
    audit["opaque_asset_count"] = len(assets)
    audit["status"] = "PASS" if not audit["error_codes"] else "FAIL"
    return audit


def reviewer_instructions(*, assignment_enforced: bool) -> str:
    assignment_note = "Your opaque participant code determines the only task order and workflow role available to you; do not attempt to change it or reopen completed tasks. " if assignment_enforced else "Use only your assigned opaque participant code. "
    return f"""# PF-ERI v2 Timed Operational Rehearsal\n\nThis is a workflow-timing rehearsal, not a scientific annotation task. {assignment_note}For each displayed pair, inspect the page sufficiently to complete the operational task, then record either `completed` or `technical_interruption` and, if needed, its technical category. Do not record, discuss, save, or report an opinion about whether the images are comparable, review-ready, similar, or from the same individual. Do not open saved files, inspect browser developer tools, or view another participant's activity. At the end of the assigned session, stop and tell the coordinator only that the session is complete or technically interrupted.\n\nYour response measures elapsed workflow time and technical friction. It is permanently excluded from the v2 outcome dataset and cannot be used to assess PF-ERI, the images, or any future reviewer.\n"""


def build_rehearsal(*, pilot_manifest: Path, pilot_audit: Path, canonical_pairs: Path, execution_manifest: Path, project_root: Path, output_dir: Path, contract_path: Path, excluded_pair_ids: set[str] | None = None) -> dict[str, Any]:
    contract = load_json(contract_path)
    contract_version = str(contract.get("contract_version", ""))
    if not contract_version.startswith("pferi_v2_timed_operational_rehearsal_contract_v") or contract.get("binding_status") != "outcome_free_operational_rehearsal_not_confirmation":
        raise ValueError("Unexpected rehearsal contract")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing rehearsal output: {output_dir}")
    pilot_audit_data = load_json(pilot_audit)
    if pilot_audit_data.get("status") != "PASS" or pilot_audit_data.get("confirmation_overlap_rule") != "pilot_pairs_are_ineligible_for_v2_confirmation_samples":
        raise ValueError("Pilot audit does not establish confirmation exclusion")
    pilot_rows, pilot_headers = read_csv(pilot_manifest)
    canonical_rows, canonical_headers = read_csv(canonical_pairs)
    execution_rows, execution_headers = read_csv(execution_manifest)
    require_headers(pilot_headers, PILOT_COLUMNS, "pilot manifest")
    require_headers(canonical_headers, CANONICAL_COLUMNS, "canonical manifest")
    require_headers(execution_headers, EXECUTION_COLUMNS, "execution manifest")
    excluded_pair_ids = excluded_pair_ids or set()
    pairs = select_pilot_pairs(pilot_rows, canonical_rows, int(contract["rehearsal_pair_count"]), contract["selection_seed"], excluded_pair_ids)
    execution = {row["image_id"]: row for row in execution_rows}
    image_ids = {image for pair in pairs for image in (pair["endpoint_a_image_id"], pair["endpoint_b_image_id"])}
    if len(execution) != len(execution_rows) or not image_ids.issubset(execution):
        raise ValueError("Execution manifest does not uniquely cover rehearsal images")
    view, assets, restricted = output_dir / "reviewer_view", output_dir / "reviewer_view" / "assets", output_dir / "restricted"
    asset_rows: list[dict[str, str]] = []
    for image_id in sorted(image_ids):
        row = execution[image_id]
        source = (project_root / row["image_path_relative"]).resolve()
        if not source.is_relative_to(project_root.resolve()) or not source.is_file() or sha256(source) != row["content_sha256"]:
            raise ValueError(f"Image integrity check failed: {image_id}")
        token = opaque_token(contract["selection_seed"], image_id)
        filename = token + ".png"
        render(source, assets / filename)
        asset_rows.append({"asset_token": token, "image_id": image_id, "content_sha256": row["content_sha256"], "rendered_asset_filename": filename})
    assets_by_image = {row["image_id"]: row["asset_token"] for row in asset_rows}
    packet_rows, linkage_rows = [], []
    for index, pair in enumerate(pairs, start=1):
        packet_id = f"rehearsal_packet_{index:03d}"
        packet_rows.append({"rehearsal_packet_id": packet_id, "left_asset_token": assets_by_image[pair["endpoint_a_image_id"]], "right_asset_token": assets_by_image[pair["endpoint_b_image_id"]], "interface_version": "pferi_v2_timed_operational_rehearsal_v2", "form_schema_version": "pferi_v2_operational_response_v1"})
        linkage_rows.append({"rehearsal_packet_id": packet_id, "canonical_pair_id": pair["canonical_pair_id"], "left_image_id": pair["endpoint_a_image_id"], "right_image_id": pair["endpoint_b_image_id"]})
    write_csv(view / "rehearsal_packet.csv", contract["reviewer_packet_allowlist"], packet_rows)
    write_csv(view / "operational_response_template.csv", contract["operational_response_allowlist"], [])
    write_csv(restricted / "restricted_linkage.csv", RESTRICTED_LINKAGE_COLUMNS, linkage_rows)
    write_csv(restricted / "restricted_asset_map.csv", RESTRICTED_ASSET_COLUMNS, asset_rows)
    assignment_enforced = bool(contract.get("assignment_enforcement") == "required")
    allocation_rows = default_v2_allocation([row["rehearsal_packet_id"] for row in packet_rows]) if assignment_enforced else []
    if allocation_rows:
        write_csv(restricted / "participant_task_allocation.csv", ALLOCATION_COLUMNS, allocation_rows)
    (view / "app.py").write_text(APP_SOURCE, encoding="utf-8")
    (view / "REVIEWER_INSTRUCTIONS.md").write_text(reviewer_instructions(assignment_enforced=assignment_enforced), encoding="utf-8")
    (view / "rehearsal_ui_manifest.json").write_text(json.dumps({"interface_version": contract_version.replace("_contract", ""), "packet_filename": "rehearsal_packet.csv", "asset_directory": "assets", "response_schema_version": "pferi_v2_operational_response_v1"}, indent=2) + "\n", encoding="utf-8")
    (output_dir / "operational_logs").mkdir(parents=True, exist_ok=True)
    (output_dir / "operational_logs" / "README.md").write_text("Coordinator-only destination for operational rehearsal logs. These files are not reviewer-visible and must not be merged with v2 outcome responses.\n", encoding="utf-8")
    static = static_audit(output_dir, contract)
    (output_dir / "machine_static_audit.json").write_text(json.dumps(static, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if static["status"] != "PASS":
        raise RuntimeError("Generated rehearsal failed static public-view audit")
    delivery = output_dir / "PF_ERI_V2_TIMED_OPERATIONAL_REHEARSAL_DELIVERY.zip"
    with zipfile.ZipFile(delivery, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(view.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output_dir))
    audit = {
        "build_version": "pferi_v2_timed_operational_rehearsal_builder_v2",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "PACKAGE_READY_PENDING_OPERATIONAL_LOGS",
        "contract_sha256": sha256(contract_path),
        "pilot_manifest_sha256": sha256(pilot_manifest),
        "pilot_audit_sha256": sha256(pilot_audit),
        "canonical_pairs_sha256": sha256(canonical_pairs),
        "execution_manifest_sha256": sha256(execution_manifest),
        "selected_pair_count": len(pairs),
        "selected_image_count": len(image_ids),
        "excluded_prior_rehearsal_pair_count": len(excluded_pair_ids),
        "overlap_with_excluded_prior_rehearsal_pair_count": len({pair["canonical_pair_id"] for pair in pairs} & excluded_pair_ids),
        "assignment_enforcement": "required" if assignment_enforced else "not_required",
        "allocated_task_count": len(allocation_rows),
        "delivery_zip_sha256": sha256(delivery),
        "machine_static_audit_status": static["status"],
        "outcome_access": "none; the package contains no review decision, reason, confidence, note, identity, descriptor, feature, score, route, or v2 outcome field.",
        "claim_boundary": contract["claim_boundary"],
    }
    (restricted / "build_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-manifest", type=Path, default=ROOT / "outputs/pferi_v2/measurement_feasibility_pilot/restricted_pilot_manifest.csv")
    parser.add_argument("--pilot-audit", type=Path, default=ROOT / "outputs/pferi_v2/measurement_feasibility_pilot/restricted_pilot_manifest_audit.json")
    parser.add_argument("--canonical-pairs", type=Path, default=ROOT / "outputs/pferi_v2/dual_descriptor_queue/canonical_pairs.csv")
    parser.add_argument("--execution-manifest", type=Path, default=ROOT / "outputs/pferi_v2/restricted_descriptor_execution_manifest.csv")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=ROOT / "schemas/pferi_v2/timed_operational_rehearsal_contract_v2.json")
    parser.add_argument("--exclude-pair-ids", type=Path, default=None, help="One-column canonical_pair_id CSV of prior rehearsal pairs that v2 must not reuse.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/pferi_v2/dual_sample_confirmation/2026-07-15_timed_operational_rehearsal_v2")
    args = parser.parse_args()
    audit = build_rehearsal(pilot_manifest=args.pilot_manifest, pilot_audit=args.pilot_audit, canonical_pairs=args.canonical_pairs, execution_manifest=args.execution_manifest, project_root=args.project_root, output_dir=args.output_dir, contract_path=args.contract, excluded_pair_ids=read_retired_pair_ids(args.exclude_pair_ids))
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
