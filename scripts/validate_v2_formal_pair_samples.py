#!/usr/bin/env python3
"""Independently validate the frozen PF-ERI v2 formal pair sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Sequence


CONTRACT_VERSION = "pferi_v2_post_allocation_sampling_derivation_contract_v1"
EXPECTED_COUNTS = {
    "development": 445,
    "calibration": 445,
    "deployment_confirmation": 889,
    "mechanism_confirmation": 445,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_checksum_manifest(directory: Path) -> None:
    checksum_path = directory / "CHECKSUMS.sha256"
    if not checksum_path.is_file():
        raise ValueError("missing CHECKSUMS.sha256")
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, filename = line.split("  ", 1)
        path = directory / filename
        if not path.is_file():
            raise ValueError(f"checksum inventory file missing: {filename}")
        observed = sha256_file(path)
        if observed != digest:
            raise ValueError(f"checksum mismatch for {filename}: expected={digest}, observed={observed}")


def finite_decimal(text: str, field: str) -> Decimal:
    try:
        value = Decimal(str(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} is not a decimal: {text!r}") from exc
    if not value.is_finite():
        raise ValueError(f"{field} is not finite")
    return value


def validate_probability(quota_text: str, capacity_text: str, probability_text: str) -> None:
    quota = Decimal(quota_text)
    capacity = Decimal(capacity_text)
    if capacity <= 0 or quota < 0 or quota > capacity:
        raise ValueError("invalid quota/capacity")
    expected = quota / capacity
    observed = Decimal(probability_text)
    if abs(expected - observed) > Decimal("0.0000000000005"):
        raise ValueError(f"probability mismatch: expected={expected}, observed={observed}")


def digest_for(
    seed_hex: str,
    role: str,
    stage: str,
    cell: str,
    pair_id: str,
) -> str:
    message = json.dumps(
        [CONTRACT_VERSION, role, stage, cell, pair_id],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(bytes.fromhex(seed_hex), message, hashlib.sha256).hexdigest()


def midrank(values: Mapping[str, Decimal]) -> dict[str, Decimal]:
    if not values:
        raise ValueError("empty percentile frame")
    counts = Counter(values.values())
    total = Decimal(len(values))
    below = 0
    by_value = {}
    for value in sorted(counts):
        count = counts[value]
        by_value[value] = (Decimal(below) + Decimal(count) / 2) / total
        below += count
    return {key: by_value[value] for key, value in values.items()}


def truth(row: Mapping[str, str], field: str) -> bool:
    value = row[field].lower()
    if value not in ("true", "false"):
        raise ValueError(f"invalid boolean {field}={value}")
    return value == "true"


def independent_mechanism_frame(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    dual = {
        row["canonical_pair_id"]: finite_decimal(
            row["dual_descriptor_percentile_disagreement"], "dual disagreement"
        )
        for row in rows
        if row["descriptor_support_category"] == "both"
    }
    percentiles = midrank(dual)
    result = []
    for source in rows:
        row = dict(source)
        pair_id = row["canonical_pair_id"]
        if truth(row, "endpoint_quality_measurement_failure") or truth(row, "local_match_measurement_failure"):
            state = "automatic_measurement_failure"
        elif truth(row, "endpoint_frozen_quality_stress"):
            state = "image_quality_stress"
        elif finite_decimal(row["local_match_within_role_percentile"], "local percentile") <= Decimal("0.20"):
            state = "local_correspondence_bottom_quintile"
        elif row["descriptor_support_category"] in ("megadescriptor_only", "dinov2_only"):
            state = "descriptor_exclusive"
        elif row["descriptor_support_category"] != "both":
            raise ValueError("invalid descriptor support")
        elif percentiles[pair_id] >= Decimal("0.80"):
            state = "dual_descriptor_percentile_disagreement_top_quintile"
        else:
            state = "ordinary_reference"
        row["independent_mechanism_state"] = state
        row["independent_mechanism_cell"] = f"{state}__{row['best_rank_band']}"
        row["independent_mechanism_disagreement_percentile"] = (
            f"{percentiles[pair_id]:.12f}" if pair_id in percentiles else ""
        )
        result.append(row)
    return result


def independent_waterfill(capacities: Mapping[str, int], target: int, tie_order: Mapping[str, str]) -> dict[str, int]:
    if sum(capacities.values()) < target:
        raise ValueError("insufficient mechanism capacity")
    ordered = sorted((cell for cell, cap in capacities.items() if cap), key=lambda cell: (tie_order[cell], cell))
    quota = {cell: 0 for cell in ordered}
    remaining = target
    while remaining:
        for cell in ordered:
            if remaining and quota[cell] < capacities[cell]:
                quota[cell] += 1
                remaining -= 1
    return quota


def expected_selected_ids(
    rows: Sequence[Mapping[str, str]],
    quotas: Mapping[str, int],
    *,
    role: str,
    stage: str,
    cell_field: str,
    seed_hex: str,
) -> set[str]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[cell_field]].append(row)
    if set(grouped) != set(quotas):
        raise ValueError(f"validator quota/cell mismatch for {role}")
    expected: set[str] = set()
    for cell, population in grouped.items():
        ordered = sorted(
            population,
            key=lambda row: (
                digest_for(seed_hex, role, stage, cell, row["canonical_pair_id"]),
                row["canonical_pair_id"],
            ),
        )
        expected.update(row["canonical_pair_id"] for row in ordered[: quotas[cell]])
    return expected


def validate(root: Path, formal_dir: Path) -> dict[str, object]:
    required = {
        "restricted_formal_pair_sampling_manifest.csv",
        "mechanism_post_deployment_cell_capacity_and_quota.csv",
        "formal_sample_image_degree.csv",
        "formal_pair_sampling_execution_authorization_v1.json",
        "formal_selection_audit.json",
        "formal_sample_degree_audit.json",
        "immutable_input_hash_audit.json",
        "formal_sampling_freeze_record.json",
        "CHECKSUMS.sha256",
    }
    found = {path.name for path in formal_dir.iterdir() if path.is_file()}
    if found != required:
        raise ValueError(f"formal directory inventory mismatch: missing={sorted(required-found)}, extra={sorted(found-required)}")
    verify_checksum_manifest(formal_dir)
    manifest = read_csv(formal_dir / "restricted_formal_pair_sampling_manifest.csv")
    if len(manifest) != 2224:
        raise ValueError(f"formal manifest row count must be 2224, observed {len(manifest)}")
    ids = [row["canonical_pair_id"] for row in manifest]
    if len(set(ids)) != 2224:
        raise ValueError("formal manifest contains canonical-pair overlap")
    stage_counts = Counter(row["formal_sampling_stage"] for row in manifest)
    if dict(stage_counts) != EXPECTED_COUNTS:
        raise ValueError(f"stage count mismatch: {dict(stage_counts)}")
    expected_source_roles = {
        "development": "development",
        "calibration": "calibration",
        "deployment_confirmation": "confirmation",
        "mechanism_confirmation": "confirmation",
    }
    for row in manifest:
        stage = row["formal_sampling_stage"]
        if row["source_analytical_role"] != expected_source_roles[stage]:
            raise ValueError(f"source role mismatch for {row['canonical_pair_id']}")
        validate_probability(row["cell_quota"], row["cell_capacity"], row["first_order_inclusion_probability"])
        forbidden = ("review", "outcome", "identity", "decision", "label")
        if any(fragment in field.lower() for field in row for fragment in forbidden):
            raise ValueError("formal restricted manifest contains downstream fields")

    auth = json.loads((formal_dir / "formal_pair_sampling_execution_authorization_v1.json").read_text(encoding="utf-8"))
    if auth["execution_guards"]["formal_pair_selection_authorized"] is not True:
        raise ValueError("authorization snapshot does not authorize formal selection")
    input_paths = {
        "post_allocation_derivation_contract_sha256": root / "schemas/pferi_v2/post_allocation_sampling_derivation_contract_v1.json",
        "four_stage_stratified_sampling_contract_sha256": root / "schemas/pferi_v2/four_stage_stratified_sampling_contract_v1.json",
        "official_sampling_seed_record_sha256": root / "archive/pferi_v2/task_runs/partition/image_allocation/official_sampling_seed_record.json",
        "restricted_master_derivation_frame_sha256": root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1/restricted_outcome_free_master_derivation_frame.csv",
        "planned_allocation_quotas_sha256": root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1/planned_allocation_quotas.csv",
        "post_allocation_capacity_audit_sha256": root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1/post_allocation_capacity_audit.json",
        "preflight_checksums_sha256": root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1/CHECKSUMS.sha256",
    }
    for name, path in input_paths.items():
        if sha256_file(path) != auth["immutable_inputs"][name]:
            raise ValueError(f"current authorized input hash mismatch: {name}")
    derivation = json.loads(input_paths["post_allocation_derivation_contract_sha256"].read_text(encoding="utf-8"))
    seed_hex = derivation["seed_derivation"]["official_seed_hex"]
    preflight = root / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1"
    master = read_csv(preflight / "restricted_outcome_free_master_derivation_frame.csv")
    frozen_quota_rows = read_csv(preflight / "planned_allocation_quotas.csv")
    by_role = defaultdict(list)
    for row in master:
        by_role[row["analytical_role"]].append(row)
    frozen_quotas = {
        role: {
            row["cell_id"]: int(row["planned_quota"])
            for row in frozen_quota_rows
            if row["analytical_role"] == role
        }
        for role in ("development", "calibration", "deployment_confirmation")
    }
    reconstruction = {
        "development": expected_selected_ids(
            by_role["development"], frozen_quotas["development"], role="development",
            stage="development_within_cell_order", cell_field="development_sampling_cell_id", seed_hex=seed_hex
        ),
        "calibration": expected_selected_ids(
            by_role["calibration"], frozen_quotas["calibration"], role="calibration",
            stage="calibration_within_cell_order", cell_field="retrieval_stratum_id", seed_hex=seed_hex
        ),
        "deployment_confirmation": expected_selected_ids(
            by_role["confirmation"], frozen_quotas["deployment_confirmation"], role="deployment_confirmation",
            stage="deployment_within_cell_order", cell_field="retrieval_stratum_id", seed_hex=seed_hex
        ),
    }
    observed = {
        stage: {row["canonical_pair_id"] for row in manifest if row["formal_sampling_stage"] == stage}
        for stage in EXPECTED_COUNTS
    }
    for stage in reconstruction:
        if observed[stage] != reconstruction[stage]:
            raise ValueError(f"independent HMAC reconstruction mismatch for {stage}")
    remaining = [row for row in by_role["confirmation"] if row["canonical_pair_id"] not in reconstruction["deployment_confirmation"]]
    if len(remaining) != 8528:
        raise ValueError("independent confirmation remainder mismatch")
    mechanism_frame = independent_mechanism_frame(remaining)
    capacities = Counter(row["independent_mechanism_cell"] for row in mechanism_frame)
    tie_order = {
        cell: digest_for(seed_hex, "mechanism_confirmation", "allocation_tie_break", cell, "")
        for cell in capacities
    }
    quotas = independent_waterfill(capacities, 445, tie_order)
    mechanism_inventory = read_csv(formal_dir / "mechanism_post_deployment_cell_capacity_and_quota.csv")
    inventory_map = {row["cell_id"]: row for row in mechanism_inventory}
    if set(inventory_map) != set(capacities):
        raise ValueError("mechanism cell inventory mismatch")
    for cell in capacities:
        row = inventory_map[cell]
        if int(row["capacity"]) != capacities[cell] or int(row["planned_quota"]) != quotas[cell]:
            raise ValueError(f"mechanism capacity/quota mismatch for {cell}")
        if row["allocation_tie_hmac_sha256"] != tie_order[cell]:
            raise ValueError(f"mechanism allocation tie digest mismatch for {cell}")
    reconstructed_mechanism = expected_selected_ids(
        mechanism_frame, quotas, role="mechanism_confirmation", stage="mechanism_within_cell_order",
        cell_field="independent_mechanism_cell", seed_hex=seed_hex
    )
    if observed["mechanism_confirmation"] != reconstructed_mechanism:
        raise ValueError("independent HMAC reconstruction mismatch for mechanism_confirmation")
    mechanism_manifest = {
        row["canonical_pair_id"]: row
        for row in manifest
        if row["formal_sampling_stage"] == "mechanism_confirmation"
    }
    mechanism_source = {row["canonical_pair_id"]: row for row in mechanism_frame}
    for pair_id, row in mechanism_manifest.items():
        source = mechanism_source[pair_id]
        if row["mechanism_challenge_state"] != source["independent_mechanism_state"]:
            raise ValueError(f"mechanism challenge state mismatch for {pair_id}")
        if row["mechanism_disagreement_remaining_percentile"] != source["independent_mechanism_disagreement_percentile"]:
            raise ValueError(f"mechanism disagreement percentile mismatch for {pair_id}")

    recomputed_degree = Counter()
    per_stage = {stage: Counter() for stage in EXPECTED_COUNTS}
    for row in manifest:
        for endpoint in (row["endpoint_a_image_id"], row["endpoint_b_image_id"]):
            recomputed_degree[endpoint] += 1
            per_stage[row["formal_sampling_stage"]][endpoint] += 1
    degree_rows = read_csv(formal_dir / "formal_sample_image_degree.csv")
    if {row["image_id"] for row in degree_rows} != set(recomputed_degree):
        raise ValueError("image degree inventory mismatch")
    for row in degree_rows:
        image_id = row["image_id"]
        if int(row["total_formal_sample_degree"]) != recomputed_degree[image_id]:
            raise ValueError(f"total image degree mismatch for {image_id}")
        for stage in EXPECTED_COUNTS:
            if int(row[f"{stage}_degree"]) != per_stage[stage][image_id]:
                raise ValueError(f"stage image degree mismatch for {image_id}, {stage}")

    audit = json.loads((formal_dir / "formal_selection_audit.json").read_text(encoding="utf-8"))
    freeze = json.loads((formal_dir / "formal_sampling_freeze_record.json").read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or freeze.get("status") != "FROZEN_PASS":
        raise ValueError("formal audit/freeze status is not passing")
    if freeze["formal_manifest_sha256"] != sha256_file(formal_dir / "restricted_formal_pair_sampling_manifest.csv"):
        raise ValueError("freeze record manifest hash mismatch")
    return {
        "status": "PASS",
        "formal_sample_row_count": len(manifest),
        "unique_canonical_pair_count": len(set(ids)),
        "stage_counts": dict(stage_counts),
        "mechanism_cell_count": len(capacities),
        "maximum_image_degree": max(recomputed_degree.values()),
        "independent_hmac_reconstruction": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--formal-dir",
        type=Path,
        default=Path("archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1"),
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    formal_dir = args.formal_dir if args.formal_dir.is_absolute() else root / args.formal_dir
    print(json.dumps(validate(root, formal_dir.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
