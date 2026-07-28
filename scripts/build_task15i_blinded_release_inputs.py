#!/usr/bin/env python3
"""Prepare restricted Task 15I reviewer-package inputs without releasing assets."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLANNING = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_blinded_collection_planning_v1"
EXECUTION_MANIFEST = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_descriptor_execution_manifest_v1/descriptor_execution_manifest.csv"
OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_blinded_release_inputs_v1"
EXECUTION_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path, expected: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != expected:
            raise ValueError(f"unexpected columns in {path.name}")
        return list(reader)


def select_execution_rows(assignment: list[dict[str, str]], execution: list[dict[str, str]]) -> list[dict[str, str]]:
    required = {row[field] for row in assignment for field in ("left_image_id", "right_image_id")}
    by_id = {row["image_id"]: row for row in execution}
    if len(by_id) != len(execution):
        raise ValueError("execution manifest contains duplicate image IDs")
    missing = required - set(by_id)
    if missing:
        raise ValueError(f"execution manifest omits {len(missing)} assigned images")
    return [row for row in execution if row["image_id"] in required]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader(); writer.writerows(rows)


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    planning_audit = json.loads((PLANNING / "blinded_collection_planning_audit.json").read_text(encoding="utf-8"))
    if planning_audit.get("status") != "PASS_PROVISIONAL_NOT_RELEASED" or planning_audit.get("packet_release_authorized") or planning_audit.get("outcome_collection_authorized"):
        raise ValueError("planning state does not permit restricted release-input preparation")
    assignment_path = PLANNING / "restricted/provisional_four_reviewer_assignment.csv"
    with assignment_path.open(newline="", encoding="utf-8") as handle:
        assignment = list(csv.DictReader(handle))
    if len(assignment) != 3200 or any(row.get("assignment_status") != "provisional_not_released" for row in assignment):
        raise ValueError("unexpected or releasable reviewer assignment")
    execution = read_csv(EXECUTION_MANIFEST, EXECUTION_COLUMNS)
    selected = select_execution_rows(assignment, execution)
    if len(selected) != 2000:
        raise ValueError(f"expected 2,000 selected endpoint images, found {len(selected)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name; stage.mkdir()
        restricted = stage / "restricted"; restricted.mkdir()
        write_csv(restricted / "selected_image_execution_manifest.csv", EXECUTION_COLUMNS, selected)
        shutil.copy2(PLANNING / "restricted/provisional_four_reviewer_assignment.csv", restricted / "provisional_four_reviewer_assignment.csv")
        shutil.copy2(PLANNING / "restricted/restricted_four_reviewer_roster_template.csv", restricted / "restricted_four_reviewer_roster_template.csv")
        audit = {
            "status": "PASS_RELEASE_INPUTS_PREPARED_NOT_RELEASED",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "assigned_pair_count": len({row["canonical_pair_id"] for row in assignment}),
            "first_pass_task_count": len(assignment),
            "selected_image_count": len(selected),
            "planning_audit_sha256": sha256(PLANNING / "blinded_collection_planning_audit.json"),
            "source_execution_manifest_sha256": sha256(EXECUTION_MANIFEST),
            "selected_execution_manifest_sha256": sha256(restricted / "selected_image_execution_manifest.csv"),
            "reviewer_roster_complete": False,
            "reviewer_asset_packages_created": False,
            "packet_release_authorized": False,
            "outcome_collection_authorized": False,
            "outcomes_accessed": False,
            "claim_boundary": "Restricted release inputs only. This directory contains no rendered reviewer assets, no response, and no released outcome-collection package.",
        }
        (stage / "release_input_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "RELEASE_GATES.md").write_text(
            "# Task15I Release Gates\n\n"
            "Do not create or distribute reviewer assets until the restricted roster maps all four codes to distinct people, confirms training and conflicts, and an independent browser leakage audit is scheduled. The selected image execution manifest is restricted administrator input, not a reviewer-visible artifact.\n",
            encoding="utf-8",
        )
        shutil.copy2(Path(__file__), stage / "release_input_builder_snapshot.py")
        files = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return audit


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
