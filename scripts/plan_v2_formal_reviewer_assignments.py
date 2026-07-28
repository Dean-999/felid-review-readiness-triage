#!/usr/bin/env python3
"""Plan balanced double-review assignments without releasing outcome packets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import itertools
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Sequence


CONTRACT_VERSION = "pferi_v2_formal_review_instrument_contract_v1"
FORMAL_MANIFEST_SHA256 = "8c8407e155d92b0bc51d2300b365f4ab30f96bc70404f47217dba377ef0bdabf"
PLANNING_KEY_HEX = hashlib.sha256(b"pferi_v2_reviewer_assignment_planning_only_v1").hexdigest()
REVIEWER_PACKET_COLUMNS = [
    "review_packet_id",
    "left_asset_token",
    "right_asset_token",
    "instrument_version",
    "review_form_schema_version",
]
ASSIGNMENT_COLUMNS = [
    "assignment_contract_version",
    "review_packet_id",
    "canonical_pair_id",
    "formal_sampling_stage",
    "reviewer_assignment_id",
    "reviewer_code",
    "peer_reviewer_code",
    "eligible_adjudicator_codes",
    "left_image_id",
    "right_image_id",
    "left_asset_token",
    "right_asset_token",
    "packet_batch_id",
    "assignment_status",
]


def keyed_hex(key_hex: str, *parts: str) -> str:
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise ValueError("assignment key must decode to 32 bytes")
    message = json.dumps(list(parts), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def opaque_reviewer_codes(count: int, key_hex: str) -> list[str]:
    if count < 3:
        raise ValueError("at least three distinct reviewers are required")
    return ["rv_" + keyed_hex(key_hex, "reviewer_code", str(index))[:10] for index in range(count)]


def reviewer_visible_row(assignment: Mapping[str, str]) -> dict[str, str]:
    return {
        "review_packet_id": assignment["review_packet_id"],
        "left_asset_token": assignment["left_asset_token"],
        "right_asset_token": assignment["right_asset_token"],
        "instrument_version": "blind_pair_review_v1",
        "review_form_schema_version": "raw_response_v1",
    }


def workload_scenario(pair_count: int, reviewer_count: int) -> dict[str, object]:
    if reviewer_count < 3:
        raise ValueError("at least three distinct reviewers are required")
    decisions = pair_count * 2
    return {
        "distinct_reviewer_count": reviewer_count,
        "formal_pair_count": pair_count,
        "first_pass_decision_count": decisions,
        "minimum_first_pass_tasks_per_reviewer": decisions // reviewer_count,
        "maximum_first_pass_tasks_per_reviewer": (decisions + reviewer_count - 1) // reviewer_count,
        "eligible_adjudicators_per_pair": reviewer_count - 2,
        "adjudication_task_count": "unknown_until_first_pass_disagreement_audit",
    }


def plan_assignments(
    pair_rows: Sequence[Mapping[str, str]], reviewer_codes: Sequence[str], key_hex: str
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    codes = sorted(set(reviewer_codes))
    if len(codes) < 3:
        raise ValueError("at least three distinct reviewers are required")
    if len(codes) != len(reviewer_codes):
        raise ValueError("reviewer codes must be unique")
    pair_ids = [row["canonical_pair_id"] for row in pair_rows]
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("pair rows must have unique canonical_pair_id")
    stage_order = {
        "development": 0,
        "calibration": 1,
        "deployment_confirmation": 2,
        "mechanism_confirmation": 3,
    }
    if not set(row["formal_sampling_stage"] for row in pair_rows).issubset(stage_order):
        raise ValueError("unexpected formal_sampling_stage")
    ordered = sorted(
        pair_rows,
        key=lambda row: (
            stage_order[row["formal_sampling_stage"]],
            keyed_hex(key_hex, "pair_assignment_order", row["canonical_pair_id"]),
            row["canonical_pair_id"],
        ),
    )
    reviewer_load = Counter({code: 0 for code in codes})
    stage_load: dict[str, Counter[str]] = defaultdict(lambda: Counter({code: 0 for code in codes}))
    edge_load = Counter()
    stage_edge_load: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    assignments: list[dict[str, str]] = []
    eligibility: list[dict[str, str]] = []
    edges = list(itertools.combinations(codes, 2))
    for pair in ordered:
        pair_id = pair["canonical_pair_id"]
        stage = pair["formal_sampling_stage"]

        def edge_score(edge: tuple[str, str]) -> tuple[object, ...]:
            prospective = dict(reviewer_load)
            prospective[edge[0]] += 1
            prospective[edge[1]] += 1
            values = list(prospective.values())
            prospective_stage = dict(stage_load[stage])
            prospective_stage[edge[0]] += 1
            prospective_stage[edge[1]] += 1
            stage_values = list(prospective_stage.values())
            return (
                stage_edge_load[stage][edge],
                max(stage_values) - min(stage_values),
                max(stage_values),
                edge_load[edge],
                max(values) - min(values),
                max(values),
                sum(value * value for value in stage_values),
                sum(value * value for value in values),
                keyed_hex(key_hex, "edge_tie", pair_id, edge[0], edge[1]),
                edge,
            )

        first, second = min(edges, key=edge_score)
        edge = (first, second)
        edge_load[edge] += 1
        stage_edge_load[stage][edge] += 1
        reviewer_load[first] += 1
        reviewer_load[second] += 1
        stage_load[stage][first] += 1
        stage_load[stage][second] += 1
        eligible = [code for code in codes if code not in edge]
        orientation_swap = int(keyed_hex(key_hex, "orientation", pair_id), 16) % 2 == 1
        image_a = pair["endpoint_a_image_id"]
        image_b = pair["endpoint_b_image_id"]
        left_image, right_image = (image_b, image_a) if orientation_swap else (image_a, image_b)
        for reviewer, peer in ((first, second), (second, first)):
            packet_id = "task_" + keyed_hex(key_hex, "packet", pair_id, reviewer)[:24]
            assignment_id = "assignment_" + keyed_hex(key_hex, "assignment", pair_id, reviewer)[:24]
            assignments.append(
                {
                    "assignment_contract_version": CONTRACT_VERSION,
                    "review_packet_id": packet_id,
                    "canonical_pair_id": pair_id,
                    "formal_sampling_stage": pair["formal_sampling_stage"],
                    "reviewer_assignment_id": assignment_id,
                    "reviewer_code": reviewer,
                    "peer_reviewer_code": peer,
                    "eligible_adjudicator_codes": ";".join(eligible),
                    "left_image_id": left_image,
                    "right_image_id": right_image,
                    "left_asset_token": "asset_" + keyed_hex(key_hex, "asset", reviewer, left_image)[:20],
                    "right_asset_token": "asset_" + keyed_hex(key_hex, "asset", reviewer, right_image)[:20],
                    "packet_batch_id": "formal_first_pass_pending_roster_v3",
                    "assignment_status": "provisional_not_released",
                }
            )
        eligibility.append(
            {
                "canonical_pair_id": pair_id,
                "first_pass_reviewer_code_1": first,
                "first_pass_reviewer_code_2": second,
                "eligible_adjudicator_codes": ";".join(eligible),
                "eligibility_status": "provisional_pending_distinct_person_roster",
            }
        )
    assignments.sort(key=lambda row: (row["reviewer_code"], row["review_packet_id"]))
    eligibility.sort(key=lambda row: row["canonical_pair_id"])
    loads = Counter(row["reviewer_code"] for row in assignments)
    if max(loads.values()) - min(loads.values()) > 1:
        raise ValueError(f"reviewer workload balance invariant failed: {dict(loads)}")
    return assignments, eligibility


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build(root: Path, output_dir: Path) -> dict[str, object]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite reviewer assignment planning directory: {output_dir}")
    formal_dir = root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1"
    manifest_path = formal_dir / "restricted_formal_pair_sampling_manifest.csv"
    if sha256_file(manifest_path) != FORMAL_MANIFEST_SHA256:
        raise ValueError("frozen formal manifest hash mismatch")
    pairs = read_csv(manifest_path)
    if len(pairs) != 2224:
        raise ValueError("formal manifest must contain exactly 2224 pairs")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".reviewer_assignment_plan_", dir=output_dir.parent))
    try:
        scenario_rows = [workload_scenario(len(pairs), count) for count in range(3, 9)]
        codes = opaque_reviewer_codes(4, PLANNING_KEY_HEX)
        assignments, eligibility = plan_assignments(pairs, codes, PLANNING_KEY_HEX)
        loads = Counter(row["reviewer_code"] for row in assignments)
        write_csv(
            staging / "reviewer_count_workload_scenarios.csv",
            [
                "distinct_reviewer_count",
                "formal_pair_count",
                "first_pass_decision_count",
                "minimum_first_pass_tasks_per_reviewer",
                "maximum_first_pass_tasks_per_reviewer",
                "eligible_adjudicators_per_pair",
                "adjudication_task_count",
            ],
            scenario_rows,
        )
        write_csv(staging / "provisional_four_reviewer_assignment.csv", ASSIGNMENT_COLUMNS, assignments)
        write_csv(
            staging / "provisional_adjudicator_eligibility.csv",
            [
                "canonical_pair_id",
                "first_pass_reviewer_code_1",
                "first_pass_reviewer_code_2",
                "eligible_adjudicator_codes",
                "eligibility_status",
            ],
            eligibility,
        )
        roster = [
            {
                "reviewer_code": code,
                "restricted_person_name": "",
                "eligible_roles": "first_pass_reviewer;adjudicator",
                "training_confirmed": "no",
                "pair_or_role_conflicts": "",
                "conflict_attestation": "pending",
                "signed_at_utc": "",
            }
            for code in codes
        ]
        write_csv(
            staging / "restricted_four_reviewer_roster_template.csv",
            [
                "reviewer_code",
                "restricted_person_name",
                "eligible_roles",
                "training_confirmed",
                "pair_or_role_conflicts",
                "conflict_attestation",
                "signed_at_utc",
            ],
            roster,
        )
        (staging / "REVIEWER_TASK_GUIDE_zh.md").write_text(
            "# PF-ERI v2 Reviewer 任务说明（正式包释放前草案）\n\n"
            "每一项只判断：两张图是否包含足够、可比较的可见证据，使负责任的人员能够进行个体层面的比较。不要判断两张图是否一定属于同一个个体。不同个体若能可靠排除，也可以是 review_ready。\n\n"
            "选择 review_ready、not_review_ready 或 uncertain。not_review_ready/uncertain 必须选择可见原因；每项记录对该 reviewability 判断的 low/medium/high confidence。图片未加载、渲染错误或界面泄漏隐藏信息属于 technical problem，不是语义标签。\n\n"
            "不得搜索原图、查看文件或开发者元数据、讨论 pair、使用另一个 reviewer 的答案、尝试推断 descriptor/score/rank/identity/sampling stage。发现可能泄漏时立即停止该项并报告。\n",
            encoding="utf-8",
        )
        audit = {
            "status": "PASS_PROVISIONAL_NOT_RELEASED",
            "contract_version": CONTRACT_VERSION,
            "formal_manifest_sha256": FORMAL_MANIFEST_SHA256,
            "formal_pair_count": 2224,
            "first_pass_decision_count": 4448,
            "recommended_reviewer_count": 4,
            "recommended_reviewer_loads": dict(sorted(loads.items())),
            "every_pair_two_distinct_opaque_codes": True,
            "eligible_adjudicators_per_pair": 2,
            "actual_distinct_person_roster_complete": False,
            "packet_release_authorized": False,
            "outcome_collection_authorized": False,
        }
        (staging / "planning_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        artifacts = sorted(path for path in staging.iterdir() if path.is_file())
        (staging / "CHECKSUMS.sha256").write_text(
            "\n".join(f"{sha256_file(path)}  {path.name}" for path in artifacts) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, output_dir)
    except Exception:
        import shutil

        shutil.rmtree(staging, ignore_errors=True)
        raise
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "archive/pferi_v2/task_runs/dual_sample_confirmation/"
            "2026-07-20_reviewer_assignment_planning/iterations/v3"
        ),
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    print(json.dumps(build(root, output.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
