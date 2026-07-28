#!/usr/bin/env python3
"""Execute the single authorized PF-ERI v2 formal pair draw.

The draw is deterministic HMAC ordering, never PRNG sampling. Output is built
in a temporary directory and atomically frozen only after all invariants pass.
Existing final output is never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from build_v2_post_allocation_sampling_frame import (
    CONTRACT_VERSION,
    finite_decimal,
    midrank_percentiles,
    seeded_digest,
    sha256_file,
    waterfill_quotas,
    write_csv_atomic,
    write_json_atomic,
)
from validate_v2_formal_pair_samples import validate as independent_validate


AUTHORIZATION_VERSION = "pferi_v2_formal_pair_sampling_execution_authorization_v1"
FINAL_MANIFEST_FIELDS = [
    "sampling_contract_version",
    "authorization_version",
    "formal_sampling_stage",
    "canonical_pair_id",
    "pair_execution_id",
    "source_analytical_role",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "sampling_cell_id",
    "cell_capacity",
    "cell_quota",
    "first_order_inclusion_probability",
    "inclusion_probability_scope",
    "within_cell_order_hmac_sha256",
    "retrieval_stratum_id",
    "best_rank_band",
    "descriptor_support_category",
    "development_evidence_state",
    "mechanism_challenge_state",
    "mechanism_disagreement_remaining_percentile",
    "local_match_measurement_failure",
    "endpoint_quality_measurement_failure",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ensure_fresh_final_path(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing formal sampling directory: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def freeze_after_independent_validation(root: Path, staging: Path, final: Path) -> dict[str, object]:
    result = independent_validate(root, staging)
    if result.get("status") != "PASS":
        raise ValueError(f"independent formal sample validation did not pass: {result}")
    os.replace(staging, final)
    return result


def bool_text(row: Mapping[str, str], field: str) -> bool:
    value = row.get(field, "").strip().lower()
    if value not in ("true", "false"):
        raise ValueError(f"{field} must be true or false for {row.get('canonical_pair_id')}")
    return value == "true"


def select_from_cells(
    rows: Sequence[Mapping[str, str]],
    *,
    quotas: Mapping[str, int],
    analytical_role: str,
    sampling_stage: str,
    cell_field: str,
    seed_hex: str,
    contract_version: str,
) -> list[dict[str, str]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        cell = row.get(cell_field, "")
        if not cell:
            raise ValueError(f"blank {cell_field} for {row.get('canonical_pair_id')}")
        grouped[cell].append(row)
    if set(grouped) != set(quotas):
        raise ValueError(
            f"quota/cell mismatch for {sampling_stage}: missing_quotas={sorted(set(grouped)-set(quotas))}, "
            f"unexpected_quotas={sorted(set(quotas)-set(grouped))}"
        )
    selected: list[dict[str, str]] = []
    for cell in sorted(grouped):
        population = grouped[cell]
        quota = int(quotas[cell])
        if quota < 0 or quota > len(population):
            raise ValueError(
                f"INSUFFICIENT_FRAME_CAPACITY: stage={sampling_stage}, cell={cell}, quota={quota}, capacity={len(population)}"
            )
        ordered: list[tuple[str, str, Mapping[str, str]]] = []
        for row in population:
            pair_id = row["canonical_pair_id"]
            digest = seeded_digest(
                seed_hex=seed_hex,
                contract_version=contract_version,
                analytical_role=analytical_role,
                sampling_stage=sampling_stage,
                cell_id=cell,
                ordering_unit_id=pair_id,
            )
            ordered.append((digest, pair_id, row))
        ordered.sort(key=lambda item: (item[0], item[1]))
        probability = f"{Decimal(quota) / Decimal(len(population)):.12f}"
        for digest, _, source in ordered[:quota]:
            item = dict(source)
            item["formal_sampling_stage"] = analytical_role
            item["sampling_cell_id"] = cell
            item["cell_capacity"] = str(len(population))
            item["cell_quota"] = str(quota)
            item["first_order_inclusion_probability"] = probability
            item["within_cell_order_hmac_sha256"] = digest
            selected.append(item)
    if len(selected) != sum(int(value) for value in quotas.values()):
        raise ValueError(f"selected row total mismatch for {sampling_stage}")
    return sorted(selected, key=lambda item: (item["sampling_cell_id"], item["within_cell_order_hmac_sha256"], item["canonical_pair_id"]))


def derive_mechanism_cells(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    dual_values = {
        row["canonical_pair_id"]: finite_decimal(
            row["dual_descriptor_percentile_disagreement"],
            "dual_descriptor_percentile_disagreement",
        )
        for row in rows
        if row["descriptor_support_category"] == "both"
    }
    dual_percentiles = midrank_percentiles(dual_values)
    derived: list[dict[str, str]] = []
    for source in rows:
        row = dict(source)
        pair_id = row["canonical_pair_id"]
        quality_failure = bool_text(row, "endpoint_quality_measurement_failure")
        local_failure = bool_text(row, "local_match_measurement_failure")
        quality_stress = bool_text(row, "endpoint_frozen_quality_stress")
        support = row["descriptor_support_category"]
        if quality_failure or local_failure:
            state = "automatic_measurement_failure"
        elif quality_stress:
            state = "image_quality_stress"
        else:
            local_percentile = finite_decimal(
                row["local_match_within_role_percentile"], "local_match_within_role_percentile"
            )
            if local_percentile <= Decimal("0.20"):
                state = "local_correspondence_bottom_quintile"
            elif support in ("megadescriptor_only", "dinov2_only"):
                state = "descriptor_exclusive"
            elif support != "both":
                raise ValueError(f"unexpected descriptor support for {pair_id}: {support}")
            elif dual_percentiles[pair_id] >= 0.80:
                state = "dual_descriptor_percentile_disagreement_top_quintile"
            else:
                state = "ordinary_reference"
        row["mechanism_challenge_state"] = state
        row["mechanism_disagreement_remaining_percentile"] = (
            f"{dual_percentiles[pair_id]:.12f}" if pair_id in dual_percentiles else ""
        )
        row["mechanism_sampling_cell_id"] = f"{state}__{row['best_rank_band']}"
        derived.append(row)
    return derived


def assert_zero_pair_overlap(samples: Mapping[str, Sequence[Mapping[str, str]]]) -> None:
    owner: dict[str, str] = {}
    for stage, rows in samples.items():
        for row in rows:
            pair_id = row["canonical_pair_id"]
            if pair_id in owner:
                raise ValueError(f"formal sample pair overlap: {pair_id} occurs in {owner[pair_id]} and {stage}")
            owner[pair_id] = stage


def quota_map(rows: Sequence[Mapping[str, str]], role: str) -> dict[str, int]:
    result = {
        row["cell_id"]: int(row["planned_quota"])
        for row in rows
        if row["analytical_role"] == role
    }
    if not result:
        raise ValueError(f"no frozen quota rows for {role}")
    return result


def verify_authorized_inputs(root: Path, auth: Mapping[str, object]) -> dict[str, object]:
    preflight = root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1"
    paths = {
        "post_allocation_derivation_contract_sha256": root / "schemas/pferi_v2/post_allocation_sampling_derivation_contract_v1.json",
        "four_stage_stratified_sampling_contract_sha256": root / "schemas/pferi_v2/four_stage_stratified_sampling_contract_v1.json",
        "official_sampling_seed_record_sha256": root / "archive/pferi_v2/task_runs/partition/image_allocation/official_sampling_seed_record.json",
        "restricted_master_derivation_frame_sha256": preflight / "restricted_outcome_free_master_derivation_frame.csv",
        "planned_allocation_quotas_sha256": preflight / "planned_allocation_quotas.csv",
        "post_allocation_capacity_audit_sha256": preflight / "post_allocation_capacity_audit.json",
        "preflight_checksums_sha256": preflight / "CHECKSUMS.sha256",
    }
    audit = {}
    for name, path in paths.items():
        expected = auth["immutable_inputs"][name]
        observed = sha256_file(path)
        status = "PASS" if observed == expected else "FAIL"
        audit[name] = {"path": str(path), "expected": expected, "observed": observed, "status": status}
        if status != "PASS":
            raise ValueError(f"formal sampling input hash mismatch: {name}")
    capacity = json.loads(paths["post_allocation_capacity_audit_sha256"].read_text(encoding="utf-8"))
    if capacity.get("status") != "PASS" or capacity.get("formal_pair_selection_authorized_by_this_audit") is not False:
        raise ValueError("unexpected capacity audit state")
    return audit


def output_manifest_row(source: Mapping[str, str], probability_scope: str) -> dict[str, str]:
    return {
        "sampling_contract_version": CONTRACT_VERSION,
        "authorization_version": AUTHORIZATION_VERSION,
        "formal_sampling_stage": source["formal_sampling_stage"],
        "canonical_pair_id": source["canonical_pair_id"],
        "pair_execution_id": source["pair_execution_id"],
        "source_analytical_role": source["analytical_role"],
        "endpoint_a_image_id": source["endpoint_a_image_id"],
        "endpoint_b_image_id": source["endpoint_b_image_id"],
        "sampling_cell_id": source["sampling_cell_id"],
        "cell_capacity": source["cell_capacity"],
        "cell_quota": source["cell_quota"],
        "first_order_inclusion_probability": source["first_order_inclusion_probability"],
        "inclusion_probability_scope": probability_scope,
        "within_cell_order_hmac_sha256": source["within_cell_order_hmac_sha256"],
        "retrieval_stratum_id": source["retrieval_stratum_id"],
        "best_rank_band": source["best_rank_band"],
        "descriptor_support_category": source["descriptor_support_category"],
        "development_evidence_state": source.get("development_evidence_state", ""),
        "mechanism_challenge_state": source.get("mechanism_challenge_state", ""),
        "mechanism_disagreement_remaining_percentile": source.get("mechanism_disagreement_remaining_percentile", ""),
        "local_match_measurement_failure": source["local_match_measurement_failure"],
        "endpoint_quality_measurement_failure": source["endpoint_quality_measurement_failure"],
    }


def execute_selection(
    master_rows: Sequence[Mapping[str, str]],
    frozen_quota_rows: Sequence[Mapping[str, str]],
    *,
    seed_hex: str,
) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, object]]]:
    ids = [row["canonical_pair_id"] for row in master_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("master frame contains duplicate canonical_pair_id")
    roles = defaultdict(list)
    for row in master_rows:
        roles[row["analytical_role"]].append(row)
    if {role: len(rows) for role, rows in roles.items()} != {
        "development": 9445,
        "calibration": 9433,
        "confirmation": 9417,
    }:
        raise ValueError("master frame role cardinalities do not match frozen capacity audit")

    development = select_from_cells(
        roles["development"],
        quotas=quota_map(frozen_quota_rows, "development"),
        analytical_role="development",
        sampling_stage="development_within_cell_order",
        cell_field="development_sampling_cell_id",
        seed_hex=seed_hex,
        contract_version=CONTRACT_VERSION,
    )
    calibration = select_from_cells(
        roles["calibration"],
        quotas=quota_map(frozen_quota_rows, "calibration"),
        analytical_role="calibration",
        sampling_stage="calibration_within_cell_order",
        cell_field="retrieval_stratum_id",
        seed_hex=seed_hex,
        contract_version=CONTRACT_VERSION,
    )
    deployment = select_from_cells(
        roles["confirmation"],
        quotas=quota_map(frozen_quota_rows, "deployment_confirmation"),
        analytical_role="deployment_confirmation",
        sampling_stage="deployment_within_cell_order",
        cell_field="retrieval_stratum_id",
        seed_hex=seed_hex,
        contract_version=CONTRACT_VERSION,
    )
    deployment_ids = {row["canonical_pair_id"] for row in deployment}
    remaining = [row for row in roles["confirmation"] if row["canonical_pair_id"] not in deployment_ids]
    if len(remaining) != 8528:
        raise ValueError(f"post-deployment confirmation remainder must be 8528, observed {len(remaining)}")
    mechanism_frame = derive_mechanism_cells(remaining)
    mechanism_capacities = Counter(row["mechanism_sampling_cell_id"] for row in mechanism_frame)
    mechanism_tie_order = {
        cell: seeded_digest(
            seed_hex=seed_hex,
            contract_version=CONTRACT_VERSION,
            analytical_role="mechanism_confirmation",
            sampling_stage="allocation_tie_break",
            cell_id=cell,
            ordering_unit_id="",
        )
        for cell in mechanism_capacities
    }
    mechanism_quotas = waterfill_quotas(
        mechanism_capacities, target=445, tie_order=mechanism_tie_order
    )
    mechanism = select_from_cells(
        mechanism_frame,
        quotas=mechanism_quotas,
        analytical_role="mechanism_confirmation",
        sampling_stage="mechanism_within_cell_order",
        cell_field="mechanism_sampling_cell_id",
        seed_hex=seed_hex,
        contract_version=CONTRACT_VERSION,
    )
    samples = {
        "development": development,
        "calibration": calibration,
        "deployment_confirmation": deployment,
        "mechanism_confirmation": mechanism,
    }
    assert_zero_pair_overlap(samples)
    expected_counts = {
        "development": 445,
        "calibration": 445,
        "deployment_confirmation": 889,
        "mechanism_confirmation": 445,
    }
    if {stage: len(rows) for stage, rows in samples.items()} != expected_counts:
        raise ValueError("formal sample totals do not match accepted targets")
    mechanism_rows = [
        {
            "analytical_role": "mechanism_confirmation",
            "cell_id": cell,
            "capacity": mechanism_capacities[cell],
            "planned_quota": mechanism_quotas[cell],
            "allocation_tie_hmac_sha256": mechanism_tie_order[cell],
        }
        for cell in sorted(mechanism_capacities)
    ]
    return samples, mechanism_rows


def degree_rows(samples: Mapping[str, Sequence[Mapping[str, str]]]) -> list[dict[str, object]]:
    stages = tuple(samples)
    counts = {stage: Counter() for stage in stages}
    total = Counter()
    for stage, rows in samples.items():
        for row in rows:
            for endpoint in (row["endpoint_a_image_id"], row["endpoint_b_image_id"]):
                counts[stage][endpoint] += 1
                total[endpoint] += 1
    return [
        {
            "image_id": image_id,
            "total_formal_sample_degree": total[image_id],
            **{f"{stage}_degree": counts[stage][image_id] for stage in stages},
        }
        for image_id in sorted(total)
    ]


def build(root: Path, final_dir: Path) -> dict[str, object]:
    ensure_fresh_final_path(final_dir)
    auth_path = root / "schemas/pferi_v2/formal_pair_sampling_execution_authorization_v1.json"
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    if auth.get("status") != "authorized_by_project_owner_20260720":
        raise ValueError("formal sampling authorization is not active")
    guards = auth["execution_guards"]
    if guards.get("formal_pair_selection_authorized") is not True:
        raise ValueError("formal pair selection is not authorized")
    prohibited = (
        guards.get("prng_allowed"),
        guards.get("reroll_allowed"),
        guards.get("manual_replacement_allowed"),
        guards.get("post_selection_degree_optimization_allowed"),
        guards.get("reviewer_packet_authorized"),
        guards.get("outcome_access_authorized"),
    )
    if any(value is not False for value in prohibited):
        raise ValueError("formal authorization guard configuration is unsafe")
    input_audit = verify_authorized_inputs(root, auth)
    preflight = root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1"
    master_rows = read_csv(preflight / "restricted_outcome_free_master_derivation_frame.csv")
    frozen_quota_rows = read_csv(preflight / "planned_allocation_quotas.csv")
    derivation_contract = json.loads(
        (root / "schemas/pferi_v2/post_allocation_sampling_derivation_contract_v1.json").read_text(encoding="utf-8")
    )
    seed_hex = derivation_contract["seed_derivation"]["official_seed_hex"]
    samples, mechanism_rows = execute_selection(master_rows, frozen_quota_rows, seed_hex=seed_hex)

    scopes = {
        "development": "conditional_on_frozen_development_cells_not_for_prevalence",
        "calibration": "unconditional_within_frozen_calibration_stratum",
        "deployment_confirmation": "unconditional_within_frozen_confirmation_retrieval_stratum",
        "mechanism_confirmation": "conditional_on_immutable_deployment_draw_and_post_deployment_mechanism_cells_not_for_prevalence",
    }
    manifest_rows = [
        output_manifest_row(row, scopes[stage])
        for stage, rows in samples.items()
        for row in rows
    ]
    manifest_rows.sort(
        key=lambda row: (
            ("development", "calibration", "deployment_confirmation", "mechanism_confirmation").index(row["formal_sampling_stage"]),
            row["sampling_cell_id"],
            row["within_cell_order_hmac_sha256"],
            row["canonical_pair_id"],
        )
    )
    degrees = degree_rows(samples)
    degree_distribution = Counter(int(row["total_formal_sample_degree"]) for row in degrees)
    stage_counts = {stage: len(rows) for stage, rows in samples.items()}
    failure_counts = {
        stage: sum(
            row["local_match_measurement_failure"] == "true"
            or row["endpoint_quality_measurement_failure"] == "true"
            for row in rows
        )
        for stage, rows in samples.items()
    }

    staging = Path(tempfile.mkdtemp(prefix=".formal_pair_sampling_staging_", dir=final_dir.parent))
    try:
        manifest_path = staging / "restricted_formal_pair_sampling_manifest.csv"
        mechanism_path = staging / "mechanism_post_deployment_cell_capacity_and_quota.csv"
        degree_path = staging / "formal_sample_image_degree.csv"
        write_csv_atomic(manifest_path, FINAL_MANIFEST_FIELDS, manifest_rows)
        write_csv_atomic(
            mechanism_path,
            ["analytical_role", "cell_id", "capacity", "planned_quota", "allocation_tie_hmac_sha256"],
            mechanism_rows,
        )
        degree_fields = [
            "image_id",
            "total_formal_sample_degree",
            "development_degree",
            "calibration_degree",
            "deployment_confirmation_degree",
            "mechanism_confirmation_degree",
        ]
        write_csv_atomic(degree_path, degree_fields, degrees)
        shutil.copy2(auth_path, staging / "formal_pair_sampling_execution_authorization_v1.json")
        selection_audit = {
            "status": "PASS",
            "sampling_contract_version": CONTRACT_VERSION,
            "authorization_version": AUTHORIZATION_VERSION,
            "formal_sample_row_count": len(manifest_rows),
            "unique_canonical_pair_count": len({row["canonical_pair_id"] for row in manifest_rows}),
            "stage_counts": stage_counts,
            "pair_overlap_count": 0,
            "confirmation_frame_count": 9417,
            "post_deployment_mechanism_frame_count": 8528,
            "mechanism_nonempty_cell_count": len(mechanism_rows),
            "scientific_measurement_failure_counts": failure_counts,
            "prng_used": False,
            "reroll_performed": False,
            "manual_replacement_performed": False,
            "degree_optimization_performed": False,
            "reviewer_packet_created": False,
            "outcome_accessed": False,
        }
        write_json_atomic(staging / "formal_selection_audit.json", selection_audit)
        write_json_atomic(
            staging / "formal_sample_degree_audit.json",
            {
                "status": "PASS",
                "unique_image_count": len(degrees),
                "maximum_formal_sample_degree": max(int(row["total_formal_sample_degree"]) for row in degrees),
                "degree_distribution": {str(key): value for key, value in sorted(degree_distribution.items())},
                "post_selection_optimization_performed": False,
            },
        )
        write_json_atomic(staging / "immutable_input_hash_audit.json", {"status": "PASS", "inputs": input_audit})
        script_hash = sha256_file(Path(__file__).resolve())
        write_json_atomic(
            staging / "formal_sampling_freeze_record.json",
            {
                "status": "FROZEN_PASS",
                "sampling_contract_version": CONTRACT_VERSION,
                "authorization_version": AUTHORIZATION_VERSION,
                "official_seed_sha256": sha256_file(root / "archive/pferi_v2/task_runs/partition/image_allocation/official_sampling_seed_record.json"),
                "formal_sampler_sha256": script_hash,
                "formal_manifest_sha256": sha256_file(manifest_path),
                "formal_sample_row_count": len(manifest_rows),
                "reroll_prohibited": True,
                "existing_directory_overwrite_prohibited": True,
            },
        )
        artifacts = sorted(path for path in staging.iterdir() if path.is_file())
        (staging / "CHECKSUMS.sha256").write_text(
            "\n".join(f"{sha256_file(path)}  {path.name}" for path in artifacts) + "\n",
            encoding="utf-8",
        )
        # Terminal assertions immediately before the atomic freeze.
        if len(manifest_rows) != 2224 or len({row["canonical_pair_id"] for row in manifest_rows}) != 2224:
            raise ValueError("terminal formal sample uniqueness assertion failed")
        if stage_counts != {"development": 445, "calibration": 445, "deployment_confirmation": 889, "mechanism_confirmation": 445}:
            raise ValueError("terminal formal sample count assertion failed")
        independent_result = freeze_after_independent_validation(root, staging, final_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "status": "FROZEN_PASS",
        "final_dir": str(final_dir),
        "formal_manifest_sha256": sha256_file(final_dir / "restricted_formal_pair_sampling_manifest.csv"),
        "stage_counts": stage_counts,
        "unique_pair_count": len(manifest_rows),
        "independent_validation": independent_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1"),
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    final_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    result = build(root, final_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
