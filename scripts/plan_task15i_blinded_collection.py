#!/usr/bin/env python3
"""Create a non-released, blinded Task 15I new-development collection plan."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import plan_v2_formal_reviewer_assignments as planner


FREEZE = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_90pct_prepair_contract_freeze_v1"
OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_blinded_collection_planning_v1"
PLANNING_KEY = hashlib.sha256(b"PF-ERI-Task15I-blinded-development-planning-20260726").hexdigest()
ASSIGNMENT_VERSION = "pferi_v2_task15i_blinded_collection_assignment_v1"
RAW_RESPONSE_COLUMNS = ["review_packet_id", "raw_reviewer_response_id", "review_decision", "reason_codes", "confidence", "optional_note", "submitted_at_utc", "technical_problem_flag"]
PUBLIC_PACKET_COLUMNS = ["review_packet_id", "left_asset_token", "right_asset_token", "instrument_version", "review_form_schema_version"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader(); writer.writerows(rows)


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    freeze = json.loads((FREEZE / "prelabel_contract_freeze_record.json").read_text(encoding="utf-8"))
    fold_audit = json.loads((FREEZE / "component_disjoint_folds/fold_validation_audit.json").read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_PRELABEL_90PCT_REDEVELOPMENT_EXECUTION" or fold_audit.get("status") != "PASS" or fold_audit.get("endpoint_leakage_count") != 0:
        raise ValueError("prelabel contract/fold freeze is not eligible for blinded collection planning")
    with (FREEZE / "prelabel_execution_inputs/outcome_free_development_master.csv").open(newline="", encoding="utf-8") as handle:
        pairs = list(csv.DictReader(handle))
    # This restricted administrator input retains outcome-free design strata,
    # but the planner reads only the four fields copied into planner_rows.
    forbidden_headers = [field for field in pairs[0] if any(token in field.lower() for token in ("label", "outcome", "identity", "review"))]
    if forbidden_headers or len(pairs) != 1600 or len({row["canonical_pair_id"] for row in pairs}) != 1600:
        raise ValueError("prelabel frame violates blinded-collection boundary")
    planner_rows = [{"canonical_pair_id": row["canonical_pair_id"], "formal_sampling_stage": "development", "endpoint_a_image_id": row["endpoint_a_image_id"], "endpoint_b_image_id": row["endpoint_b_image_id"]} for row in pairs]
    reviewer_codes = planner.opaque_reviewer_codes(4, PLANNING_KEY)
    assignments, eligibility = planner.plan_assignments(planner_rows, reviewer_codes, PLANNING_KEY)
    for row in assignments:
        row["assignment_contract_version"] = ASSIGNMENT_VERSION
        row["packet_batch_id"] = "task15i_development_first_pass_pending_roster_v1"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name; stage.mkdir()
        restricted = stage / "restricted"; restricted.mkdir()
        write_csv(restricted / "provisional_four_reviewer_assignment.csv", planner.ASSIGNMENT_COLUMNS, assignments)
        write_csv(restricted / "provisional_adjudicator_eligibility.csv", ["canonical_pair_id", "first_pass_reviewer_code_1", "first_pass_reviewer_code_2", "eligible_adjudicator_codes", "eligibility_status"], eligibility)
        roster = [{"reviewer_code": code, "restricted_person_name": "", "eligible_roles": "first_pass_reviewer;adjudicator", "training_confirmed": "no", "pair_or_role_conflicts": "", "conflict_attestation": "pending", "signed_at_utc": ""} for code in reviewer_codes]
        write_csv(restricted / "restricted_four_reviewer_roster_template.csv", ["reviewer_code", "restricted_person_name", "eligible_roles", "training_confirmed", "pair_or_role_conflicts", "conflict_attestation", "signed_at_utc"], roster)
        write_csv(stage / "reviewer_visible_packet_schema.csv", PUBLIC_PACKET_COLUMNS, [])
        write_csv(stage / "raw_response_template.csv", RAW_RESPONSE_COLUMNS, [])
        (stage / "REVIEWER_GUIDE_zh.md").write_text(
            "# Task 15I 盲法新开发评审\n\n"
            "每项只回答：两张图是否包含足够、可比较的可见证据，使负责任的人员能够进行个体层面的比较。不要判断是否属于同一个个体。\n\n"
            "可选结果为 `review_ready`、`not_review_ready` 或 `uncertain`。首评者不得查看元数据、来源、文件名、descriptor、分数、组件、折号、质量或局部匹配信息；不得搜索图片、讨论任务或查看他人回应。首评不一致时，未参与首评的第三人进行独立盲法裁决。\n",
            encoding="utf-8",
        )
        audit = {"status": "PASS_PROVISIONAL_NOT_RELEASED", "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pair_count": 1600, "first_pass_task_count": len(assignments), "reviewer_codes": reviewer_codes, "reviewer_loads": {code: sum(row["reviewer_code"] == code for row in assignments) for code in reviewer_codes}, "every_pair_has_two_distinct_first_pass_codes": all(row["first_pass_reviewer_code_1"] != row["first_pass_reviewer_code_2"] for row in eligibility), "eligible_adjudicators_per_pair": 2, "actual_distinct_person_roster_complete": False, "packet_release_authorized": False, "outcome_collection_authorized": False, "release_gates": ["map four opaque codes to four distinct accountable people", "complete reviewer training and conflict attestations", "build neutral PNG reviewer packages after source-image hash verification", "pass independent real-browser leakage audit"], "outcomes_accessed": False, "identity_labels_accessed": False, "source_contract_freeze_sha256": sha256(FREEZE / "prelabel_contract_freeze_record.json"), "claim_boundary": "Planning only. No reviewer-visible assets are created, no packet is released, and no new outcome is collected."}
        (stage / "blinded_collection_planning_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.copy2(Path(__file__), stage / "planning_builder_snapshot.py")
        files = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return audit


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
