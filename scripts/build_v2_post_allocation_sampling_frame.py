#!/usr/bin/env python3
"""Build the frozen outcome-free PF-ERI v2 derivation frame and capacity audit.

This program deliberately does not order or select formal pairs.  It verifies
immutable inputs, performs deterministic joins and percentile derivations, and
checks that accepted role totals are feasible before selection is authorized.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import io
import json
import math
import os
import tempfile
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence


CONTRACT_VERSION = "pferi_v2_post_allocation_sampling_derivation_contract_v1"
MERGED_MEMBER = "PF_ERI_FINAL_EXPORT/merged/canonical_measurements.csv"
VALIDATION_MEMBER = "PF_ERI_FINAL_EXPORT/validation/full_frame_validation.json"

RESTRICTED_MASTER_FIELDNAMES = [
    "derivation_contract_version",
    "canonical_pair_id",
    "pair_execution_id",
    "analytical_role",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "descriptor_support_category",
    "best_rank_band",
    "retrieval_stratum_id",
    "megadescriptor_similarity",
    "dinov2_similarity",
    "megadescriptor_within_role_percentile",
    "dinov2_within_role_percentile",
    "dual_descriptor_percentile_disagreement",
    "dual_descriptor_disagreement_within_role_percentile",
    "endpoint_native_pixel_quality_percentile_min",
    "endpoint_sharpness_quality_percentile_min",
    "endpoint_exposure_quality_percentile_min",
    "endpoint_quality_measurement_failure",
    "endpoint_frozen_quality_stress",
    "local_match_coverage_fraction",
    "local_match_within_role_percentile",
    "local_match_measurement_failure",
    "development_evidence_state",
    "development_sampling_cell_id",
]

FORBIDDEN_OUTPUT_FRAGMENTS = ("selected", "packet", "review", "outcome", "identity", "label")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_decimal(text: str, field: str) -> Decimal:
    try:
        value = Decimal(str(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a finite base-10 decimal: {text!r}") from exc
    if not value.is_finite():
        raise ValueError(f"{field} must be finite: {text!r}")
    return value


def midrank_percentiles(values: Mapping[str, object]) -> Dict[str, float]:
    """Return empirical midrank percentiles without splitting numeric ties."""
    if not values:
        raise ValueError("midrank percentile frame must be nonempty")
    parsed = {key: finite_decimal(str(value), f"value[{key}]") for key, value in values.items()}
    counts = Counter(parsed.values())
    below = 0
    percentile_by_value: Dict[Decimal, float] = {}
    total = len(parsed)
    for value in sorted(counts):
        count = counts[value]
        percentile_by_value[value] = float((Decimal(below) + Decimal(count) / 2) / Decimal(total))
        below += count
    return {key: percentile_by_value[value] for key, value in parsed.items()}


def seeded_digest(
    *,
    seed_hex: str,
    contract_version: str,
    analytical_role: str,
    sampling_stage: str,
    cell_id: str,
    ordering_unit_id: str,
) -> str:
    key = bytes.fromhex(seed_hex)
    if len(key) != 32:
        raise ValueError("official seed must decode to exactly 32 bytes")
    message = json.dumps(
        [contract_version, analytical_role, sampling_stage, cell_id, ordering_unit_id],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _validate_capacities(capacities: Mapping[str, int], target: int) -> None:
    if target < 0 or any(value < 0 for value in capacities.values()):
        raise ValueError("capacities and target must be nonnegative")
    if sum(capacities.values()) < target:
        raise ValueError(
            f"INSUFFICIENT_FRAME_CAPACITY: target={target}, capacity={sum(capacities.values())}"
        )


def waterfill_quotas(
    capacities: Mapping[str, int], *, target: int, tie_order: Mapping[str, str]
) -> Dict[str, int]:
    """Near-equal deterministic water filling across nonempty cells."""
    active = [cell for cell, capacity in capacities.items() if capacity > 0]
    _validate_capacities({cell: capacities[cell] for cell in active}, target)
    ordered = sorted(active, key=lambda cell: (tie_order[cell], cell))
    quotas = {cell: 0 for cell in ordered}
    remaining = target
    while remaining:
        progressed = False
        for cell in ordered:
            if quotas[cell] < capacities[cell] and remaining:
                quotas[cell] += 1
                remaining -= 1
                progressed = True
        if not progressed:
            raise ValueError("INSUFFICIENT_FRAME_CAPACITY: water filling exhausted all cells")
    return quotas


def hamilton_quotas(
    capacities: Mapping[str, int],
    *,
    target: int,
    tie_order: Mapping[str, str],
    minimum_one: bool = True,
) -> Dict[str, int]:
    """Capacity-bounded Hamilton proportional integer allocation."""
    active = {cell: cap for cell, cap in capacities.items() if cap > 0}
    _validate_capacities(active, target)
    if minimum_one and target < len(active):
        raise ValueError("INSUFFICIENT_FRAME_CAPACITY: target cannot give every nonempty cell one row")
    total = sum(active.values())
    ideals = {cell: Decimal(target) * Decimal(cap) / Decimal(total) for cell, cap in active.items()}
    lower = 1 if minimum_one else 0
    quotas = {
        cell: min(cap, max(lower, int(ideals[cell] // Decimal(1))))
        for cell, cap in active.items()
    }
    while sum(quotas.values()) < target:
        eligible = [cell for cell in active if quotas[cell] < active[cell]]
        cell = min(
            eligible,
            key=lambda item: (-(ideals[item] - int(ideals[item] // Decimal(1))), tie_order[item], item),
        )
        quotas[cell] += 1
    while sum(quotas.values()) > target:
        eligible = [cell for cell in active if quotas[cell] > lower]
        if not eligible:
            raise ValueError("INSUFFICIENT_FRAME_CAPACITY: minimum cell allocation exceeds target")
        cell = min(
            eligible,
            key=lambda item: (ideals[item] - int(ideals[item] // Decimal(1)), tie_order[item], item),
        )
        quotas[cell] -= 1
    return quotas


def development_evidence_state(
    *,
    quality_failure: bool,
    local_failure: bool,
    quality_stress: bool,
    local_bottom: bool,
    descriptor_disagreement_top: bool,
) -> str:
    if quality_failure or local_failure:
        return "measurement_failure"
    if quality_stress or local_bottom or descriptor_disagreement_top:
        return "evidence_stress"
    return "ordinary"


def validate_descriptor_support(pair_id: str, declared: str, scores: Mapping[str, object]) -> None:
    present = frozenset(scores)
    expected = {
        "both": frozenset(("megadescriptor_l_384", "dinov2_vitl14")),
        "megadescriptor_only": frozenset(("megadescriptor_l_384",)),
        "dinov2_only": frozenset(("dinov2_vitl14",)),
    }
    if declared not in expected or present != expected[declared]:
        raise ValueError(
            f"descriptor support mismatch for {pair_id}: declared={declared}, observed={sorted(present)}"
        )


def read_csv_path(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_bytes(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def unique_index(rows: Iterable[dict[str, str]], key: str, source: str) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(key, "")
        if not value:
            raise ValueError(f"{source}: blank {key}")
        if value in index:
            raise ValueError(f"{source}: duplicate {key}={value}")
        index[value] = row
    return index


def write_csv_atomic(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temp_name = tmp.name
    os.replace(temp_name, path)


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True, ensure_ascii=True)
        tmp.write("\n")
        temp_name = tmp.name
    os.replace(temp_name, path)


def tie_summary(values: Mapping[str, Decimal], percentiles: Mapping[str, float]) -> dict[str, object]:
    counts = Counter(values.values())
    return {
        "row_count": len(values),
        "unique_numeric_value_count": len(counts),
        "tied_numeric_value_count": sum(1 for count in counts.values() if count > 1),
        "rows_in_ties": sum(count for count in counts.values() if count > 1),
        "bottom_quintile_row_count": sum(1 for value in percentiles.values() if value <= 0.20),
        "top_quintile_row_count": sum(1 for value in percentiles.values() if value >= 0.80),
        "minimum_percentile": min(percentiles.values()),
        "maximum_percentile": max(percentiles.values()),
    }


def default_paths(root: Path) -> dict[str, Path]:
    return {
        "derivation_contract": root / "schemas/pferi_v2/post_allocation_sampling_derivation_contract_v1.json",
        "sampling_contract": root / "schemas/pferi_v2/four_stage_stratified_sampling_contract_v1.json",
        "seed_record": root / "archive/pferi_v2/task_runs/partition/image_allocation/official_sampling_seed_record.json",
        "allocation": root / "archive/pferi_v2/task_runs/partition/image_allocation/official_image_role_allocation.csv",
        "frame": root / "archive/pferi_v2/task_runs/partition/image_allocation/within_role_pair_frame.csv",
        "linkage": root / "work/pferi_v2/gpu/local_match/pilot/restricted_pair_execution_linkage.csv",
        "memberships": root / "work/pferi_v2/pipeline/dual_descriptor_queue/candidate_memberships.csv",
        "quality": root / "archive/pferi_v2/task_runs/measurements/image_quality/automatic_quality_measurements.csv",
        "quality_strata": root / "archive/pferi_v2/task_runs/measurements/image_quality/image_allocation_strata_preflight.csv",
        "execution_zip": root / "archive/pferi_v2/task_runs/measurements/local_match/PF_ERI_FINAL_EXPORT.zip",
    }


def verify_inputs(paths: Mapping[str, Path], contract: Mapping[str, object]) -> tuple[dict[str, object], bytes]:
    expected = contract["immutable_inputs"]
    checks = [
        ("four_stage_sampling_contract_sha256", paths["sampling_contract"]),
        ("official_seed_record_sha256", paths["seed_record"]),
        ("official_image_role_allocation_sha256", paths["allocation"]),
        ("within_role_pair_frame_sha256", paths["frame"]),
        ("restricted_pair_execution_linkage_sha256", paths["linkage"]),
        ("candidate_memberships_sha256", paths["memberships"]),
        ("automatic_quality_measurements_sha256", paths["quality"]),
        ("image_allocation_strata_preflight_sha256", paths["quality_strata"]),
        ("final_execution_export_sha256", paths["execution_zip"]),
    ]
    audit: dict[str, object] = {}
    for name, path in checks:
        observed = sha256_file(path)
        audit[name] = {"path": str(path), "expected": expected[name], "observed": observed, "status": "PASS" if observed == expected[name] else "FAIL"}
        if observed != expected[name]:
            raise ValueError(f"immutable input hash mismatch: {name}")
    with zipfile.ZipFile(paths["execution_zip"]) as archive:
        merged = archive.read(MERGED_MEMBER)
        validation = archive.read(VALIDATION_MEMBER)
    for name, data, member in [
        ("merged_canonical_measurements_sha256", merged, MERGED_MEMBER),
        ("full_frame_validation_sha256", validation, VALIDATION_MEMBER),
    ]:
        observed = sha256_bytes(data)
        audit[name] = {"zip_member": member, "expected": expected[name], "observed": observed, "status": "PASS" if observed == expected[name] else "FAIL"}
        if observed != expected[name]:
            raise ValueError(f"immutable ZIP member hash mismatch: {name}")
    return audit, merged


def build(root: Path, output_dir: Path) -> dict[str, object]:
    paths = default_paths(root)
    contract = json.loads(paths["derivation_contract"].read_text(encoding="utf-8"))
    if contract.get("status") != "accepted_pre_outcome_owner_approved_20260720":
        raise ValueError("derivation contract is not accepted")
    authorization = contract["authorization"]
    if not authorization.get("outcome_free_derivation_frame_authorized") or not authorization.get("capacity_audit_authorized"):
        raise ValueError("outcome-free derivation/capacity audit is not authorized")
    if any(authorization.get(name) for name in ("formal_pair_selection_authorized", "reviewer_packet_authorized", "outcome_collection_authorized")):
        raise ValueError("scope violation: downstream authorization must remain false")
    input_audit, merged_bytes = verify_inputs(paths, contract)
    sampling_contract = json.loads(paths["sampling_contract"].read_text(encoding="utf-8"))
    seed_record = json.loads(paths["seed_record"].read_text(encoding="utf-8"))
    seed_hex = contract["seed_derivation"]["official_seed_hex"]
    if seed_hex not in json.dumps(seed_record, sort_keys=True):
        raise ValueError("official seed record disagrees with derivation contract")

    frame_rows = read_csv_path(paths["frame"])
    linkage_rows = read_csv_path(paths["linkage"])
    measurement_rows = read_csv_bytes(merged_bytes)
    allocation_rows = read_csv_path(paths["allocation"])
    quality_rows = read_csv_path(paths["quality"])
    quality_strata_rows = read_csv_path(paths["quality_strata"])
    membership_rows = read_csv_path(paths["memberships"])

    frame = unique_index(frame_rows, "canonical_pair_id", "within_role_pair_frame")
    linkage_by_pair = unique_index(linkage_rows, "canonical_pair_id", "restricted_pair_execution_linkage")
    linkage_by_execution = unique_index(linkage_rows, "pair_execution_id", "restricted_pair_execution_linkage")
    measurements = unique_index(measurement_rows, "pair_execution_id", "canonical_measurements")
    allocation = unique_index(allocation_rows, "image_id", "official_image_role_allocation")
    quality = unique_index(quality_rows, "image_id", "automatic_quality_measurements")
    quality_strata = unique_index(quality_strata_rows, "image_id", "image_allocation_strata_preflight")

    required_pair_count = int(contract["join_contract"]["required_pair_count"])
    required_image_count = int(contract["join_contract"]["required_image_count"])
    if not (len(frame) == len(linkage_by_pair) == len(measurements) == required_pair_count):
        raise ValueError("fatal pair cardinality mismatch")
    if not (len(allocation) == len(quality) == len(quality_strata) == required_image_count):
        raise ValueError("fatal image cardinality mismatch")
    if set(frame) != set(linkage_by_pair):
        raise ValueError("frame/linkage canonical pair set mismatch")
    if set(linkage_by_execution) != set(measurements):
        raise ValueError("linkage/measurement execution pair set mismatch")
    if set(allocation) != set(quality) or set(allocation) != set(quality_strata):
        raise ValueError("allocation/quality image set mismatch")

    image_metric_values: dict[str, dict[str, Decimal]] = {
        "native": {}, "sharpness": {}, "exposure": {}
    }
    quality_failure: dict[str, bool] = {}
    for image_id, row in quality.items():
        failures = (
            row["image_decode_status"] != "ok"
            or row["native_pixel_count_value_status"] != "not_missing"
            or row["native_pixel_count_failure_code"] != "none"
            or row["sharpness_value_status"] != "not_missing"
            or row["sharpness_failure_code"] != "none"
            or row["exposure_value_status"] != "not_missing"
            or row["exposure_failure_code"] != "none"
        )
        quality_failure[image_id] = failures
        if not failures:
            image_metric_values["native"][image_id] = finite_decimal(row["native_pixel_count"], "native_pixel_count")
            image_metric_values["sharpness"][image_id] = finite_decimal(row["sharpness_measure"], "sharpness_measure")
            image_metric_values["exposure"][image_id] = -finite_decimal(row["exposure_clipping_fraction"], "exposure_clipping_fraction")
    if any(quality_failure.values()):
        raise ValueError("image-quality measurement failures require an explicitly supported partial percentile frame")
    image_percentiles = {metric: midrank_percentiles(values) for metric, values in image_metric_values.items()}

    descriptor_scores: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for row in membership_rows:
        pair_id = row["canonical_pair_id"]
        if pair_id not in frame:
            continue
        descriptor = row["descriptor_name"]
        if descriptor not in ("megadescriptor_l_384", "dinov2_vitl14"):
            raise ValueError(f"unexpected descriptor_name: {descriptor}")
        score = finite_decimal(row["descriptor_similarity"], "descriptor_similarity")
        old = descriptor_scores[pair_id].get(descriptor)
        if old is None or score > old:
            descriptor_scores[pair_id][descriptor] = score
    if set(descriptor_scores) != set(frame):
        raise ValueError("one or more frame pairs have no descriptor membership")
    for pair_id, scores in descriptor_scores.items():
        validate_descriptor_support(pair_id, frame[pair_id]["descriptor_support_category"], scores)

    descriptor_percentiles: dict[tuple[str, str, str], float] = {}
    percentile_audit: dict[str, object] = {"image_metrics": {}, "role_metrics": {}}
    for metric, values in image_metric_values.items():
        percentile_audit["image_metrics"][metric] = tie_summary(values, image_percentiles[metric])
    roles = ("development", "calibration", "confirmation")
    for role in roles:
        percentile_audit["role_metrics"][role] = {}
        for descriptor in ("megadescriptor_l_384", "dinov2_vitl14"):
            values = {
                pair_id: scores[descriptor]
                for pair_id, scores in descriptor_scores.items()
                if descriptor in scores and frame[pair_id]["partition_role"] == role
            }
            percentiles = midrank_percentiles(values)
            for pair_id, percentile in percentiles.items():
                descriptor_percentiles[(role, descriptor, pair_id)] = percentile
            percentile_audit["role_metrics"][role][descriptor] = tie_summary(values, percentiles)

    local_values_by_role: dict[str, dict[str, Decimal]] = {role: {} for role in roles}
    local_failure: dict[str, bool] = {}
    local_text: dict[str, str] = {}
    join_role_mismatches = 0
    endpoint_role_mismatches = 0
    for pair_id, row in frame.items():
        role = row["partition_role"]
        link = linkage_by_pair[pair_id]
        measurement = measurements[link["pair_execution_id"]]
        if link["partition_role"] != role or measurement["partition_role"] != role:
            join_role_mismatches += 1
        for endpoint in (row["endpoint_a_image_id"], row["endpoint_b_image_id"]):
            if endpoint not in allocation or allocation[endpoint]["partition_role"] != role:
                endpoint_role_mismatches += 1
        failure = measurement["failure_code"] != "none" or measurement["value_status"] != "not_missing"
        local_text[pair_id] = measurement["local_match_coverage_fraction"]
        if not failure:
            try:
                value = finite_decimal(local_text[pair_id], "local_match_coverage_fraction")
            except ValueError:
                failure = True
            else:
                local_values_by_role[role][pair_id] = value
        local_failure[pair_id] = failure
    if join_role_mismatches or endpoint_role_mismatches:
        raise ValueError("fatal role or endpoint disagreement")
    local_percentiles: dict[str, float] = {}
    for role, values in local_values_by_role.items():
        percentiles = midrank_percentiles(values)
        local_percentiles.update(percentiles)
        percentile_audit["role_metrics"][role]["local_match_coverage_fraction"] = tie_summary(values, percentiles)

    disagreement: dict[str, float] = {}
    disagreement_percentile: dict[str, float] = {}
    for role in roles:
        values: dict[str, Decimal] = {}
        for pair_id, scores in descriptor_scores.items():
            if frame[pair_id]["partition_role"] != role or len(scores) != 2:
                continue
            diff = abs(
                Decimal(str(descriptor_percentiles[(role, "megadescriptor_l_384", pair_id)]))
                - Decimal(str(descriptor_percentiles[(role, "dinov2_vitl14", pair_id)]))
            )
            values[pair_id] = diff
            disagreement[pair_id] = float(diff)
        percentiles = midrank_percentiles(values)
        disagreement_percentile.update(percentiles)
        percentile_audit["role_metrics"][role]["dual_descriptor_percentile_disagreement"] = tie_summary(values, percentiles)

    master_rows: list[dict[str, object]] = []
    for pair_id in sorted(frame):
        row = frame[pair_id]
        role = row["partition_role"]
        a, b = row["endpoint_a_image_id"], row["endpoint_b_image_id"]
        pair_quality_failure = quality_failure[a] or quality_failure[b]
        quality_mins = {
            metric: min(image_percentiles[metric][a], image_percentiles[metric][b])
            for metric in ("native", "sharpness", "exposure")
        }
        frozen_quality_stress = (
            quality_strata[a]["quality_state"] == "quality_stress_bottom_quintile"
            or quality_strata[b]["quality_state"] == "quality_stress_bottom_quintile"
        )
        quality_bottom = any(value <= 0.20 for value in quality_mins.values())
        local_bottom = not local_failure[pair_id] and local_percentiles[pair_id] <= 0.20
        disagreement_top = pair_id in disagreement_percentile and disagreement_percentile[pair_id] >= 0.80
        evidence_state = ""
        development_cell = ""
        if role == "development":
            evidence_state = development_evidence_state(
                quality_failure=pair_quality_failure,
                local_failure=local_failure[pair_id],
                quality_stress=quality_bottom,
                local_bottom=local_bottom,
                descriptor_disagreement_top=disagreement_top,
            )
            development_cell = f"{row['retrieval_stratum_id']}__{evidence_state}"
        scores = descriptor_scores[pair_id]
        link = linkage_by_pair[pair_id]
        master_rows.append({
            "derivation_contract_version": CONTRACT_VERSION,
            "canonical_pair_id": pair_id,
            "pair_execution_id": link["pair_execution_id"],
            "analytical_role": role,
            "endpoint_a_image_id": a,
            "endpoint_b_image_id": b,
            "descriptor_support_category": row["descriptor_support_category"],
            "best_rank_band": row["best_rank_band"],
            "retrieval_stratum_id": row["retrieval_stratum_id"],
            "megadescriptor_similarity": str(scores.get("megadescriptor_l_384", "")),
            "dinov2_similarity": str(scores.get("dinov2_vitl14", "")),
            "megadescriptor_within_role_percentile": descriptor_percentiles.get((role, "megadescriptor_l_384", pair_id), ""),
            "dinov2_within_role_percentile": descriptor_percentiles.get((role, "dinov2_vitl14", pair_id), ""),
            "dual_descriptor_percentile_disagreement": disagreement.get(pair_id, ""),
            "dual_descriptor_disagreement_within_role_percentile": disagreement_percentile.get(pair_id, ""),
            "endpoint_native_pixel_quality_percentile_min": quality_mins["native"],
            "endpoint_sharpness_quality_percentile_min": quality_mins["sharpness"],
            "endpoint_exposure_quality_percentile_min": quality_mins["exposure"],
            "endpoint_quality_measurement_failure": str(pair_quality_failure).lower(),
            "endpoint_frozen_quality_stress": str(frozen_quality_stress).lower(),
            "local_match_coverage_fraction": local_text[pair_id],
            "local_match_within_role_percentile": local_percentiles.get(pair_id, ""),
            "local_match_measurement_failure": str(local_failure[pair_id]).lower(),
            "development_evidence_state": evidence_state,
            "development_sampling_cell_id": development_cell,
        })

    if any(any(fragment in field.lower() for fragment in FORBIDDEN_OUTPUT_FRAGMENTS) for field in RESTRICTED_MASTER_FIELDNAMES):
        raise ValueError("restricted master schema contains a prohibited downstream field")

    targets = {
        role: int(sampling_contract["analytical_samples"][role]["planned_collection_pairs"])
        for role in ("development", "calibration", "deployment_confirmation", "mechanism_confirmation")
    }
    capacity_rows: list[dict[str, object]] = []
    quota_rows: list[dict[str, object]] = []
    role_master = defaultdict(list)
    for row in master_rows:
        role_master[row["analytical_role"]].append(row)

    def digest_order(role: str, cell: str) -> str:
        return seeded_digest(
            seed_hex=seed_hex,
            contract_version=CONTRACT_VERSION,
            analytical_role=role,
            sampling_stage="allocation_tie_break",
            cell_id=cell,
            ordering_unit_id="",
        )

    development_cap = Counter(row["development_sampling_cell_id"] for row in role_master["development"])
    development_order = {cell: digest_order("development", cell) for cell in development_cap}
    development_quota = waterfill_quotas(development_cap, target=targets["development"], tie_order=development_order)
    calibration_cap = Counter(row["retrieval_stratum_id"] for row in role_master["calibration"])
    calibration_order = {cell: digest_order("calibration", cell) for cell in calibration_cap}
    calibration_quota = hamilton_quotas(calibration_cap, target=targets["calibration"], tie_order=calibration_order)
    confirmation_cap = Counter(row["retrieval_stratum_id"] for row in role_master["confirmation"])
    deployment_order = {cell: digest_order("deployment_confirmation", cell) for cell in confirmation_cap}
    deployment_quota = hamilton_quotas(confirmation_cap, target=targets["deployment_confirmation"], tie_order=deployment_order)

    for role, capacities, quotas, status in [
        ("development", development_cap, development_quota, "EXACT_PRESELECTION_CELL_CAPACITY"),
        ("calibration", calibration_cap, calibration_quota, "EXACT_PRESELECTION_CELL_CAPACITY"),
        ("deployment_confirmation", confirmation_cap, deployment_quota, "EXACT_PRESELECTION_CELL_CAPACITY"),
    ]:
        for cell in sorted(capacities):
            capacity_rows.append({"analytical_role": role, "cell_id": cell, "capacity": capacities[cell], "capacity_status": status})
            quota_rows.append({"analytical_role": role, "cell_id": cell, "planned_quota": quotas[cell], "quota_status": "FROZEN_PRESELECTION_QUOTA"})

    mechanism_remaining = len(role_master["confirmation"]) - targets["deployment_confirmation"]
    if mechanism_remaining < targets["mechanism_confirmation"]:
        raise ValueError("INSUFFICIENT_FRAME_CAPACITY: confirmation remainder cannot fill mechanism sample")
    capacity_rows.append({
        "analytical_role": "mechanism_confirmation",
        "cell_id": "POST_DEPLOYMENT_CELLS_DEFERRED_BY_ACCEPTED_SELECTION_ORDER",
        "capacity": mechanism_remaining,
        "capacity_status": "GUARANTEED_TOTAL_AFTER_ANY_FROZEN_DEPLOYMENT_SAMPLE",
    })
    quota_rows.append({
        "analytical_role": "mechanism_confirmation",
        "cell_id": "POST_DEPLOYMENT_CELLS_DEFERRED_BY_ACCEPTED_SELECTION_ORDER",
        "planned_quota": targets["mechanism_confirmation"],
        "quota_status": "TOTAL_ONLY_EXACT_CELLS_REQUIRE_IMMUTABLE_DEPLOYMENT_SAMPLE",
    })

    role_counts = Counter(row["analytical_role"] for row in master_rows)
    failure_counts = Counter(
        row["analytical_role"] for row in master_rows if row["local_match_measurement_failure"] == "true"
    )
    join_audit = {
        "status": "PASS",
        "required_pair_count": required_pair_count,
        "master_row_count": len(master_rows),
        "frame_row_count": len(frame),
        "linkage_row_count": len(linkage_by_pair),
        "measurement_row_count": len(measurements),
        "required_image_count": required_image_count,
        "allocation_image_count": len(allocation),
        "quality_image_count": len(quality),
        "quality_strata_image_count": len(quality_strata),
        "role_counts": dict(sorted(role_counts.items())),
        "local_measurement_failure_counts": dict(sorted(failure_counts.items())),
        "role_mismatch_count": join_role_mismatches,
        "endpoint_role_mismatch_count": endpoint_role_mismatches,
        "formal_pair_selection_performed": False,
        "outcome_accessed": False,
    }
    capacity_audit = {
        "status": "PASS",
        "claim": "Accepted collection totals are feasible without changing or merging frozen cells.",
        "targets": targets,
        "available_role_frame_counts": dict(sorted(role_counts.items())),
        "mechanism_confirmation": {
            "confirmation_frame_before_deployment": len(role_master["confirmation"]),
            "deployment_target": targets["deployment_confirmation"],
            "guaranteed_remaining_after_any_deployment_sample": mechanism_remaining,
            "mechanism_target": targets["mechanism_confirmation"],
            "exact_challenge_cells": "DEFERRED_BY_ACCEPTED_SEQUENTIAL_SELECTION_ORDER",
            "reason": "Challenge cells, including the dual-descriptor disagreement percentile, must be recomputed only after the deployment sample is immutable.",
        },
        "formal_pair_selection_authorized_by_this_audit": False,
        "reviewer_packet_authorized": False,
        "outcome_collection_authorized": False,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "restricted_outcome_free_master_derivation_frame.csv"
    join_path = output_dir / "join_cardinality_audit.json"
    percentile_path = output_dir / "percentile_and_tie_audit.json"
    capacity_path = output_dir / "role_by_cell_capacity.csv"
    quota_path = output_dir / "planned_allocation_quotas.csv"
    audit_path = output_dir / "post_allocation_capacity_audit.json"
    input_path = output_dir / "immutable_input_hash_audit.json"
    write_csv_atomic(master_path, RESTRICTED_MASTER_FIELDNAMES, master_rows)
    write_json_atomic(join_path, join_audit)
    write_json_atomic(percentile_path, percentile_audit)
    write_csv_atomic(capacity_path, ["analytical_role", "cell_id", "capacity", "capacity_status"], capacity_rows)
    write_csv_atomic(quota_path, ["analytical_role", "cell_id", "planned_quota", "quota_status"], quota_rows)
    write_json_atomic(audit_path, capacity_audit)
    write_json_atomic(input_path, {"status": "PASS", "inputs": input_audit})
    artifacts = [master_path, join_path, percentile_path, capacity_path, quota_path, audit_path, input_path]
    checksum_lines = [f"{sha256_file(path)}  {path.name}" for path in sorted(artifacts, key=lambda item: item.name)]
    (output_dir / "CHECKSUMS.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return {"status": "PASS", "output_dir": str(output_dir), "master_row_count": len(master_rows), "role_counts": dict(role_counts), "targets": targets}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1"),
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    result = build(root, output_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
