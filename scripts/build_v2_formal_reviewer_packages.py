#!/usr/bin/env python3
"""Build isolated, blinded PF-ERI v2 formal-review candidate packages.

The builder never authorizes outcome collection. It verifies frozen source
bytes, renders full-resolution lossless metadata-free PNG assets, creates one
neutral package per reviewer alias, and keeps every linkage field restricted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT_COLUMNS = [
    "assignment_contract_version", "review_packet_id", "canonical_pair_id",
    "formal_sampling_stage", "reviewer_assignment_id", "reviewer_code",
    "peer_reviewer_code", "eligible_adjudicator_codes", "left_image_id",
    "right_image_id", "left_asset_token", "right_asset_token",
    "packet_batch_id", "assignment_status",
]
ROSTER_COLUMNS = [
    "reviewer_code", "restricted_person_name", "eligible_roles",
    "training_confirmed", "pair_or_role_conflicts", "conflict_attestation",
    "signed_at_utc",
]
EXECUTION_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
PUBLIC_PACKET_COLUMNS = [
    "review_packet_id", "left_asset_token", "right_asset_token",
    "instrument_version", "review_form_schema_version",
]
RAW_RESPONSE_COLUMNS = [
    "review_packet_id", "raw_reviewer_response_id", "review_decision",
    "reason_codes", "confidence", "optional_note", "submitted_at_utc",
    "technical_problem_flag",
]
RESTRICTED_LINKAGE_COLUMNS = [
    "review_packet_id", "canonical_pair_id", "left_image_id", "right_image_id",
    "reviewer_assignment_id", "packet_batch_id",
]
ASSET_MAP_COLUMNS = [
    "reviewer_code", "asset_token", "image_id", "source_content_sha256",
    "rendered_content_sha256", "rendered_width_px", "rendered_height_px",
    "rendered_asset_filename", "source_path_resolution",
]
ALIAS_PATTERN = re.compile(r"^reviewer_[A-Z]$")
ASSET_PATTERN = re.compile(r"^asset_[a-f0-9]{20}$")
INSTRUMENT_VERSION = "pair_review_instrument_v2_1"
FORM_SCHEMA_VERSION = "pair_review_response_v1"


APP_SOURCE = '''import csv
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
PACKET_PATH = HERE / "reviewer_packet.csv"
ASSET_DIRECTORY = HERE / "assets"
RESPONSE_PATH = Path(os.environ.get("PAIR_REVIEW_RAW_RESPONSE_PATH", str(HERE.parent / "responses" / "raw_responses.csv")))
RESPONSE_COLUMNS = ["review_packet_id", "raw_reviewer_response_id", "review_decision", "reason_codes", "confidence", "optional_note", "submitted_at_utc", "technical_problem_flag"]
DECISIONS = ["review_ready", "not_review_ready", "uncertain"]
REASONS = ["none_review_ready", "low_evidence", "non_comparable", "both_low_evidence_and_non_comparable", "other"]
CONFIDENCE = ["low", "medium", "high"]


def read_csv_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_response(row):
    RESPONSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not RESPONSE_PATH.exists()
    with RESPONSE_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESPONSE_COLUMNS, extrasaction="raise")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


def completed_packet_ids():
    return {
        row["review_packet_id"]
        for row in read_csv_rows(RESPONSE_PATH)
        if row.get("technical_problem_flag") == "no" and row.get("review_decision") in DECISIONS
    }


st.set_page_config(page_title="Pair review", layout="wide")
packet = read_csv_rows(PACKET_PATH)
completed = completed_packet_ids()
pending = [row for row in packet if row["review_packet_id"] not in completed]
st.title("Pair review")
st.progress(len(completed) / len(packet) if packet else 0.0)
st.caption(f"Completed {len(completed)} of {len(packet)}")
if not packet:
    st.error("No review tasks are available.")
    st.stop()
if not pending:
    st.success("All assigned tasks have been completed. Return the responses/raw_responses.csv file to the study administrator.")
    st.stop()
row = pending[0]
st.caption(row["review_packet_id"])
left, right = st.columns(2)
left.image(str(ASSET_DIRECTORY / (row["left_asset_token"] + ".png")), caption="Left image", use_container_width=True)
right.image(str(ASSET_DIRECTORY / (row["right_asset_token"] + ".png")), caption="Right image", use_container_width=True)
with st.form("review_response", clear_on_submit=True):
    technical = st.checkbox("Technical problem: an image or the interface did not work")
    decision = st.selectbox("Decision", ["", *DECISIONS])
    reasons = st.multiselect("Visible-evidence reason codes", REASONS)
    confidence = st.selectbox("Confidence in this reviewability judgement", ["", *CONFIDENCE])
    note = st.text_area("Optional note")
    submitted = st.form_submit_button("Save and continue")
if submitted:
    error = ""
    if technical:
        decision, reasons, confidence = "", [], ""
    elif not decision or not confidence:
        error = "Decision and confidence are required."
    elif decision == "review_ready" and reasons != ["none_review_ready"]:
        error = "review_ready requires only none_review_ready."
    elif decision in {"not_review_ready", "uncertain"} and (not reasons or "none_review_ready" in reasons):
        error = "not_review_ready and uncertain require a non-none visible-evidence reason."
    if error:
        st.error(error)
    else:
        append_response({
            "review_packet_id": row["review_packet_id"],
            "raw_reviewer_response_id": "response_" + uuid.uuid4().hex,
            "review_decision": decision,
            "reason_codes": ";".join(reasons),
            "confidence": confidence,
            "optional_note": note,
            "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
            "technical_problem_flag": "yes" if technical else "no",
        })
        st.rerun()
'''


README_SOURCE = """# Pair review tool

This tool asks only whether the displayed pair contains enough comparable
visible evidence for responsible individual-level review. It does not ask
whether the animals are the same individual.

Do not inspect source files or metadata, search for the images, discuss a task
with another reviewer, or try to infer hidden model or sampling information.
If an image or interface fails, select the technical-problem option; do not
substitute a semantic judgement.

Run from the extracted package directory:

    python -m pip install -r requirements.txt
    python -m streamlit run reviewer_view/app.py

When all tasks are complete, return only `responses/raw_responses.csv` to the
study administrator. Do not rename or edit that file.
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path, expected: list[str], label: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != expected:
            raise ValueError(f"{label} headers differ from the locked schema")
        return list(reader)


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def resolve_source(project_root: Path, relative_path: str) -> tuple[Path, str]:
    root = project_root.resolve()
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("execution manifest path is not a safe relative path")
    direct = (root / relative).resolve()
    if direct.is_relative_to(root) and direct.is_file():
        return direct, "manifest_relative_path"
    prefix = ("outputs", "final_freeze")
    if relative.parts[:2] == prefix:
        relocated = (root / "data/frozen/pferi_v2" / Path(*relative.parts[2:])).resolve()
        if relocated.is_relative_to(root) and relocated.is_file():
            return relocated, "audited_frozen_root_relocation"
    raise FileNotFoundError(f"source image unavailable for manifest path: {relative_path}")


def render_asset(source: Path, target: Path) -> tuple[int, int, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        converted = ImageOps.exif_transpose(opened).convert("RGB")
        dimensions = converted.size
        # Copy pixels into a fresh image so PNG gamma, chromaticity, ICC, and
        # other source metadata cannot reach a reviewer-visible asset.
        rendered = Image.new("RGB", dimensions)
        rendered.paste(converted)
        rendered.save(target, format="PNG", optimize=False)
    with Image.open(target) as check:
        if check.size != dimensions or check.mode != "RGB" or check.info:
            raise ValueError(f"rendered asset verification failed: {target.name}")
    return dimensions[0], dimensions[1], sha256_file(target)


def zip_tree(source_dir: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir))


def validate_roster(rows: list[dict[str, str]], assignment_codes: set[str]) -> tuple[dict[str, str], bool]:
    if len(rows) != 4 or len({row["reviewer_code"] for row in rows}) != 4:
        raise ValueError("roster must contain four distinct reviewer codes")
    if {row["reviewer_code"] for row in rows} != assignment_codes:
        raise ValueError("roster codes do not exactly match assignment codes")
    aliases = [row["restricted_person_name"] for row in rows]
    if len(set(aliases)) != 4 or not all(ALIAS_PATTERN.fullmatch(alias) for alias in aliases):
        raise ValueError("roster requires four distinct reviewer_A-style aliases")
    if any(row["training_confirmed"] != "yes" for row in rows):
        raise ValueError("reviewer training must be confirmed before candidate build")
    conflict_complete = all(
        row["pair_or_role_conflicts"].strip()
        and row["conflict_attestation"] == "confirmed"
        and row["signed_at_utc"].strip()
        for row in rows
    )
    return {row["reviewer_code"]: row["restricted_person_name"] for row in rows}, conflict_complete


def static_validate_public_view(view: Path, expected_rows: int) -> list[str]:
    errors: list[str] = []
    packet = read_csv(view / "reviewer_packet.csv", PUBLIC_PACKET_COLUMNS, "public packet")
    if len(packet) != expected_rows:
        errors.append("public_packet_row_count_mismatch")
    if len({row["review_packet_id"] for row in packet}) != len(packet):
        errors.append("duplicate_public_packet_id")
    tokens = {
        row[field]
        for row in packet
        for field in ("left_asset_token", "right_asset_token")
    }
    if not all(ASSET_PATTERN.fullmatch(token) for token in tokens):
        errors.append("invalid_asset_token")
    assets = {path.stem for path in (view / "assets").glob("*.png")}
    if assets != tokens:
        errors.append("public_asset_inventory_mismatch")
    if read_csv(view / "raw_response_template.csv", RAW_RESPONSE_COLUMNS, "response template"):
        errors.append("raw_response_template_not_empty")
    public_packet_text = (view / "reviewer_packet.csv").read_text(encoding="utf-8").lower()
    forbidden = ("canonical_pair", "image_id", "sampling_stage", "descriptor", "similarity", "identity", "peer_reviewer", "adjudicator")
    if any(token in public_packet_text for token in forbidden):
        errors.append("restricted_token_in_public_packet")
    return errors


def write_checksums(root: Path, excluded: set[Path] | None = None) -> None:
    excluded = {path.resolve() for path in (excluded or set())}
    checksum_path = root / "CHECKSUMS.sha256"
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != checksum_path and path.resolve() not in excluded:
            lines.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_packages(
    *,
    assignment_path: Path,
    roster_path: Path,
    execution_manifest_path: Path,
    project_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    assignment_rows = read_csv(assignment_path, ASSIGNMENT_COLUMNS, "assignment")
    roster_rows = read_csv(roster_path, ROSTER_COLUMNS, "roster")
    execution_rows = read_csv(execution_manifest_path, EXECUTION_COLUMNS, "execution manifest")
    if not assignment_rows:
        raise ValueError("assignment is empty")
    assignment_codes = {row["reviewer_code"] for row in assignment_rows}
    aliases, conflict_attestations_complete = validate_roster(roster_rows, assignment_codes)
    if len({row["review_packet_id"] for row in assignment_rows}) != len(assignment_rows):
        raise ValueError("assignment packet IDs are not unique")
    if any(row["assignment_status"] != "provisional_not_released" for row in assignment_rows):
        raise ValueError("candidate builder requires the unreleased assignment state")
    execution_by_id = {row["image_id"]: row for row in execution_rows}
    if len(execution_by_id) != len(execution_rows):
        raise ValueError("execution manifest image IDs are not unique")
    required_ids = {
        row[field]
        for row in assignment_rows
        for field in ("left_image_id", "right_image_id")
    }
    if not required_ids.issubset(execution_by_id):
        raise ValueError("execution manifest does not cover every assigned image")

    verified_sources: dict[str, tuple[Path, str]] = {}
    for image_id in sorted(required_ids):
        execution = execution_by_id[image_id]
        source, resolution = resolve_source(project_root, execution["image_path_relative"])
        if sha256_file(source) != execution["content_sha256"]:
            raise ValueError(f"source image hash verification failed: {image_id}")
        verified_sources[image_id] = (source, resolution)

    staging_parent = output_dir.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output_dir.name + ".staging.", dir=staging_parent))
    try:
        unzipped_root = staging / "candidate_reviewer_packages_unzipped"
        zip_root = staging / "candidate_reviewer_packages"
        restricted = staging / "restricted"
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in assignment_rows:
            grouped[row["reviewer_code"]].append(row)
        asset_map_rows: list[dict[str, Any]] = []
        restricted_linkage_rows: list[dict[str, str]] = []
        package_audits: dict[str, Any] = {}
        for reviewer_code in sorted(grouped):
            alias = aliases[reviewer_code]
            reviewer_root = unzipped_root / alias
            view = reviewer_root / "reviewer_view"
            assets = view / "assets"
            rows = sorted(grouped[reviewer_code], key=lambda row: row["review_packet_id"])
            public_rows = []
            token_to_image: dict[str, str] = {}
            for row in rows:
                public_rows.append(
                    {
                        "review_packet_id": row["review_packet_id"],
                        "left_asset_token": row["left_asset_token"],
                        "right_asset_token": row["right_asset_token"],
                        "instrument_version": INSTRUMENT_VERSION,
                        "review_form_schema_version": FORM_SCHEMA_VERSION,
                    }
                )
                for side in ("left", "right"):
                    token, image_id = row[f"{side}_asset_token"], row[f"{side}_image_id"]
                    if not ASSET_PATTERN.fullmatch(token):
                        raise ValueError(f"invalid opaque asset token: {token}")
                    previous = token_to_image.setdefault(token, image_id)
                    if previous != image_id:
                        raise ValueError("one asset token maps to multiple images")
                restricted_linkage_rows.append({field: row[field] for field in RESTRICTED_LINKAGE_COLUMNS})
            for token, image_id in sorted(token_to_image.items()):
                source, resolution = verified_sources[image_id]
                target = assets / f"{token}.png"
                width, height, rendered_hash = render_asset(source, target)
                asset_map_rows.append(
                    {
                        "reviewer_code": reviewer_code,
                        "asset_token": token,
                        "image_id": image_id,
                        "source_content_sha256": execution_by_id[image_id]["content_sha256"],
                        "rendered_content_sha256": rendered_hash,
                        "rendered_width_px": width,
                        "rendered_height_px": height,
                        "rendered_asset_filename": target.name,
                        "source_path_resolution": resolution,
                    }
                )
            write_csv(view / "reviewer_packet.csv", PUBLIC_PACKET_COLUMNS, public_rows)
            write_csv(view / "raw_response_template.csv", RAW_RESPONSE_COLUMNS, [])
            (view / "app.py").write_text(APP_SOURCE, encoding="utf-8")
            (reviewer_root / "README.md").write_text(README_SOURCE, encoding="utf-8")
            (reviewer_root / "requirements.txt").write_text("streamlit>=1.36,<2\n", encoding="utf-8")
            (reviewer_root / "responses").mkdir(parents=True, exist_ok=True)
            errors = static_validate_public_view(view, len(rows))
            if errors:
                raise RuntimeError(f"public package validation failed for {alias}: {errors}")
            zip_path = zip_root / f"PAIR_REVIEW_{alias}.zip"
            zip_tree(reviewer_root, zip_path)
            package_audits[alias] = {
                "first_pass_task_count": len(rows),
                "unique_asset_count": len(token_to_image),
                "zip_sha256": sha256_file(zip_path),
                "static_status": "PASS",
                "stage_counts_restricted": dict(sorted(Counter(row["formal_sampling_stage"] for row in rows).items())),
            }

        write_csv(restricted / "restricted_linkage.csv", RESTRICTED_LINKAGE_COLUMNS, restricted_linkage_rows)
        write_csv(restricted / "restricted_asset_map.csv", ASSET_MAP_COLUMNS, asset_map_rows)
        shutil.copy2(roster_path, restricted / "restricted_four_reviewer_roster.csv")
        shutil.copy2(assignment_path, restricted / "restricted_assignment.csv")
        audit = {
            "built_at_utc": utc_now(),
            "status": "PASS_CANDIDATE_NOT_RELEASED",
            "packet_release_authorized": False,
            "outcome_collection_authorized": False,
            "release_blockers": [
                *([] if conflict_attestations_complete else ["reviewer_conflict_attestations_incomplete"]),
                "independent_real_browser_leakage_audit_not_completed",
            ],
            "assignment_sha256": sha256_file(assignment_path),
            "roster_sha256": sha256_file(roster_path),
            "execution_manifest_sha256": sha256_file(execution_manifest_path),
            "reviewer_package_count": len(package_audits),
            "first_pass_task_count": len(assignment_rows),
            "formal_pair_count": len({row["canonical_pair_id"] for row in assignment_rows}),
            "source_image_count_verified": len(verified_sources),
            "rendered_asset_count": len(asset_map_rows),
            "conflict_attestations_complete": conflict_attestations_complete,
            "reviewer_packages": package_audits,
            "rendering_rule": "EXIF orientation, RGB, full oriented dimensions, lossless PNG, metadata stripped; no resize, crop, enhancement, denoising, or sharpening",
            "claim_boundary": "Candidate build only. No reviewer package may be released and no outcome may be collected until conflict attestations and the independent real-browser leakage audit pass.",
        }
        (staging / "candidate_build_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_checksums(staging)
        os.replace(staging, output_dir)
        return audit
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assignment", type=Path, required=True)
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    audit = build_packages(
        assignment_path=args.assignment,
        roster_path=args.roster,
        execution_manifest_path=args.execution_manifest,
        project_root=args.project_root,
        output_dir=args.output_dir,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
