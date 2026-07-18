#!/usr/bin/env python3
"""Validate PF-ERI v2 image/pair partition manifests without reading outcomes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_partition_constraint_contract_v1"
ACTIVE_ROLES = ("development", "calibration", "confirmation")
IMAGE_ROLES = (*ACTIVE_ROLES, "unassigned")
PAIR_ROLES = (*ACTIVE_ROLES, "excluded")
FORBIDDEN_PUBLIC_COLUMN_TOKENS = (
    "outcome",
    "review",
    "decision",
    "label",
    "score",
    "feature",
    "threshold",
    "route",
    "identity",
    "model",
)

CANONICAL_PAIR_COLUMNS = (
    "contract_version",
    "canonical_pair_id",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "source_dataset",
    "pair_availability_status",
    "pair_inclusion_status",
    "exclusion_reason",
)
IMAGE_PARTITION_COLUMNS = (
    "partition_contract_version",
    "image_id",
    "partition_role",
    "allocation_status",
    "exclusion_reason",
)
PAIR_PARTITION_COLUMNS = (
    "partition_contract_version",
    "canonical_pair_id",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "partition_role",
    "allocation_status",
    "exclusion_reason",
)
IDENTITY_MAP_COLUMNS = (
    "partition_contract_version",
    "image_id",
    "identity_id",
    "access_class",
)
IDENTITY_SENSITIVITY_COLUMNS = (
    "partition_contract_version",
    "canonical_pair_id",
    "sensitivity_set_id",
)
ISSUE_COLUMNS = ("severity", "code", "artifact", "row_key", "message")


def build_contract_schema() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "description": "Outcome-free PF-ERI v2 graph-aware partition constraint contract.",
        "claim_boundary": (
            "A validator PASS establishes structural accounting and zero prohibited image/pair crossings only. "
            "It is not partition_locked and does not authorize outcome review."
        ),
        "active_partition_roles": list(ACTIVE_ROLES),
        "image_partition_manifest": {
            "required_columns": list(IMAGE_PARTITION_COLUMNS),
            "allowed_partition_roles": list(IMAGE_ROLES),
            "allowed_allocation_status": ["assigned", "unassigned"],
            "rules": [
                "every image endpoint in the eligible canonical-pair universe appears exactly once",
                "no image outside the eligible canonical-pair universe appears",
                "development, calibration, and confirmation require allocation_status assigned and blank exclusion_reason",
                "unassigned requires allocation_status unassigned and a nonblank exclusion_reason",
                "outcome, review, model, feature, threshold, route, and identity fields are forbidden",
            ],
        },
        "pair_partition_manifest": {
            "required_columns": list(PAIR_PARTITION_COLUMNS),
            "allowed_partition_roles": list(PAIR_ROLES),
            "allowed_allocation_status": ["assigned", "excluded"],
            "rules": [
                "every eligible available canonical pair appears exactly once",
                "manifest endpoints exactly equal the frozen canonical endpoints",
                "an assigned pair and both endpoint images have the same active partition role",
                "a pair whose endpoint image roles differ cannot be assigned and must be excluded",
                "excluded pairs require allocation_status excluded and a nonblank exclusion_reason",
                "outcome, review, model, feature, threshold, route, and identity fields are forbidden",
            ],
        },
        "restricted_identity_sensitivity_interface": {
            "required_identity_map_columns": list(IDENTITY_MAP_COLUMNS),
            "required_sensitivity_pair_columns": list(IDENTITY_SENSITIVITY_COLUMNS),
            "rules": [
                "identity artifacts are optional at the base-constraint stage but must be supplied together",
                "a supplied sensitivity pair manifest must contain at least one assigned confirmation pair",
                "access_class is restricted for every identity-map row",
                "every sensitivity pair is an assigned confirmation pair",
                "all development and calibration images and all sensitivity-pair endpoints have resolved identity IDs",
                "no identity represented by a sensitivity-pair endpoint occurs in development or calibration",
                "identity results are reported only as aggregate counts in the public audit",
            ],
        },
        "lock_rule": (
            "The validator never writes partition_locked. A later freeze may do so only after this structural audit, "
            "the authorized identity-sensitivity decision, fixed numerical allocation/seed, access controls, and "
            "immutable manifest hashes are all complete."
        ),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def recorded_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_issue(
    issues: list[dict[str, str]],
    severity: str,
    code: str,
    artifact: str,
    message: str,
    row_key: str = "",
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "artifact": artifact,
            "row_key": row_key,
            "message": message,
        }
    )


def check_columns(
    headers: list[str],
    required: Iterable[str],
    artifact: str,
    issues: list[dict[str, str]],
    *,
    forbid_public_tokens: bool,
) -> None:
    for column in sorted(set(required) - set(headers)):
        add_issue(issues, "ERROR", "missing_required_column", artifact, f"missing required column: {column}")
    if forbid_public_tokens:
        required_set = set(required)
        for column in headers:
            lowered = column.lower()
            if column not in required_set and any(token in lowered for token in FORBIDDEN_PUBLIC_COLUMN_TOKENS):
                add_issue(
                    issues,
                    "ERROR",
                    "forbidden_public_column",
                    artifact,
                    f"forbidden information-bearing column: {column}",
                )


def duplicate_keys(rows: list[dict[str, str]], key: str) -> set[str]:
    counts = Counter(row.get(key, "") for row in rows)
    return {value for value, count in counts.items() if value and count > 1}


def validate_partitions(
    canonical_pairs_path: Path,
    image_partitions_path: Path,
    pair_partitions_path: Path,
    *,
    identity_map_path: Path | None = None,
    identity_sensitivity_path: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    canonical_headers, canonical_rows_all = read_csv(canonical_pairs_path)
    image_headers, image_rows = read_csv(image_partitions_path)
    pair_headers, pair_rows = read_csv(pair_partitions_path)
    check_columns(canonical_headers, CANONICAL_PAIR_COLUMNS, "canonical_pairs", issues, forbid_public_tokens=False)
    check_columns(image_headers, IMAGE_PARTITION_COLUMNS, "image_partitions", issues, forbid_public_tokens=True)
    check_columns(pair_headers, PAIR_PARTITION_COLUMNS, "pair_partitions", issues, forbid_public_tokens=True)

    canonical_rows = [
        row
        for row in canonical_rows_all
        if row.get("pair_availability_status") == "available" and row.get("pair_inclusion_status") == "eligible"
    ]
    canonical_by_id: dict[str, dict[str, str]] = {}
    candidate_images: set[str] = set()
    for row in canonical_rows:
        pair_id = row.get("canonical_pair_id", "")
        if pair_id in canonical_by_id:
            add_issue(issues, "ERROR", "duplicate_source_canonical_pair", "canonical_pairs", "duplicate source pair", pair_id)
        canonical_by_id[pair_id] = row
        candidate_images.update((row.get("endpoint_a_image_id", ""), row.get("endpoint_b_image_id", "")))
    candidate_images.discard("")

    for image_id in sorted(duplicate_keys(image_rows, "image_id")):
        add_issue(issues, "ERROR", "duplicate_image_partition_row", "image_partitions", "image appears more than once", image_id)
    image_by_id: dict[str, dict[str, str]] = {}
    invalid_image_role_count = 0
    image_status_mismatch_count = 0
    for row in image_rows:
        image_id = row.get("image_id", "")
        image_by_id[image_id] = row
        role = row.get("partition_role", "")
        status = row.get("allocation_status", "")
        reason = row.get("exclusion_reason", "").strip()
        if row.get("partition_contract_version") != CONTRACT_VERSION:
            add_issue(issues, "ERROR", "image_contract_version_mismatch", "image_partitions", "wrong contract version", image_id)
        if role not in IMAGE_ROLES:
            invalid_image_role_count += 1
            add_issue(issues, "ERROR", "invalid_image_partition_role", "image_partitions", f"invalid role: {role}", image_id)
        elif role in ACTIVE_ROLES and (status != "assigned" or reason):
            image_status_mismatch_count += 1
            add_issue(
                issues,
                "ERROR",
                "active_image_status_mismatch",
                "image_partitions",
                "active image requires assigned status and blank exclusion_reason",
                image_id,
            )
        elif role == "unassigned" and (status != "unassigned" or not reason):
            image_status_mismatch_count += 1
            add_issue(
                issues,
                "ERROR",
                "unassigned_image_status_mismatch",
                "image_partitions",
                "unassigned image requires unassigned status and nonblank exclusion_reason",
                image_id,
            )

    missing_images = candidate_images - set(image_by_id)
    unexpected_images = set(image_by_id) - candidate_images
    for image_id in sorted(missing_images):
        add_issue(issues, "ERROR", "missing_candidate_image", "image_partitions", "candidate image is not accounted", image_id)
    for image_id in sorted(unexpected_images):
        add_issue(issues, "ERROR", "unexpected_image", "image_partitions", "image is outside candidate universe", image_id)

    for pair_id in sorted(duplicate_keys(pair_rows, "canonical_pair_id")):
        add_issue(issues, "ERROR", "duplicate_pair_partition_row", "pair_partitions", "pair appears more than once", pair_id)
    pair_by_id: dict[str, dict[str, str]] = {}
    endpoint_mismatch_count = 0
    active_pair_role_mismatch_count = 0
    excluded_pair_rule_mismatch_count = 0
    cross_role_pair_count = 0
    cross_role_pair_not_excluded_count = 0
    pair_role_counts = Counter()
    for row in pair_rows:
        pair_id = row.get("canonical_pair_id", "")
        pair_by_id[pair_id] = row
        role = row.get("partition_role", "")
        status = row.get("allocation_status", "")
        reason = row.get("exclusion_reason", "").strip()
        pair_role_counts[role] += 1
        if row.get("partition_contract_version") != CONTRACT_VERSION:
            add_issue(issues, "ERROR", "pair_contract_version_mismatch", "pair_partitions", "wrong contract version", pair_id)
        source = canonical_by_id.get(pair_id)
        if source is None:
            add_issue(issues, "ERROR", "unexpected_canonical_pair", "pair_partitions", "pair is outside eligible candidate universe", pair_id)
            continue
        observed_endpoints = (row.get("endpoint_a_image_id", ""), row.get("endpoint_b_image_id", ""))
        expected_endpoints = (source.get("endpoint_a_image_id", ""), source.get("endpoint_b_image_id", ""))
        if observed_endpoints != expected_endpoints:
            endpoint_mismatch_count += 1
            add_issue(issues, "ERROR", "canonical_endpoint_mismatch", "pair_partitions", "endpoints differ from frozen source", pair_id)
        endpoint_roles = tuple(image_by_id.get(image_id, {}).get("partition_role", "missing") for image_id in expected_endpoints)
        roles_differ = endpoint_roles[0] != endpoint_roles[1]
        any_unassigned = "unassigned" in endpoint_roles or "missing" in endpoint_roles
        if roles_differ:
            cross_role_pair_count += 1
        if role in ACTIVE_ROLES:
            if status != "assigned" or reason or endpoint_roles != (role, role):
                active_pair_role_mismatch_count += 1
                if roles_differ:
                    cross_role_pair_not_excluded_count += 1
                add_issue(
                    issues,
                    "ERROR",
                    "active_pair_endpoint_role_mismatch",
                    "pair_partitions",
                    f"active pair role {role} is inconsistent with endpoint roles {endpoint_roles}",
                    pair_id,
                )
        elif role == "excluded":
            if status != "excluded" or not reason:
                excluded_pair_rule_mismatch_count += 1
                add_issue(
                    issues,
                    "ERROR",
                    "excluded_pair_status_mismatch",
                    "pair_partitions",
                    "excluded pair requires excluded status and nonblank reason",
                    pair_id,
                )
            if roles_differ and not any_unassigned and reason != "cross_partition_endpoints":
                excluded_pair_rule_mismatch_count += 1
                add_issue(
                    issues,
                    "ERROR",
                    "cross_role_exclusion_reason_mismatch",
                    "pair_partitions",
                    "cross-role endpoints require exclusion_reason cross_partition_endpoints",
                    pair_id,
                )
            if any_unassigned and reason != "unassigned_endpoint":
                excluded_pair_rule_mismatch_count += 1
                add_issue(
                    issues,
                    "ERROR",
                    "unassigned_endpoint_exclusion_reason_mismatch",
                    "pair_partitions",
                    "an unassigned endpoint requires exclusion_reason unassigned_endpoint",
                    pair_id,
                )
        else:
            add_issue(issues, "ERROR", "invalid_pair_partition_role", "pair_partitions", f"invalid role: {role}", pair_id)

    missing_pairs = set(canonical_by_id) - set(pair_by_id)
    unexpected_pairs = set(pair_by_id) - set(canonical_by_id)
    for pair_id in sorted(missing_pairs):
        add_issue(issues, "ERROR", "missing_candidate_pair", "pair_partitions", "candidate pair is not accounted", pair_id)

    identity_status = "NOT_EVALUATED"
    identity_counts: dict[str, int] = {
        "identity_map_row_count": 0,
        "sensitivity_pair_count": 0,
        "unresolved_required_image_count": 0,
        "sensitivity_identity_overlap_count": 0,
        "invalid_sensitivity_pair_count": 0,
        "unexpected_identity_map_image_count": 0,
    }
    if (identity_map_path is None) != (identity_sensitivity_path is None):
        identity_status = "FAIL"
        add_issue(
            issues,
            "ERROR",
            "incomplete_identity_sensitivity_interface",
            "restricted_identity",
            "identity map and sensitivity pair manifest must be supplied together",
        )
    elif identity_map_path is not None and identity_sensitivity_path is not None:
        identity_headers, identity_rows = read_csv(identity_map_path)
        sensitivity_headers, sensitivity_rows = read_csv(identity_sensitivity_path)
        check_columns(identity_headers, IDENTITY_MAP_COLUMNS, "restricted_identity_map", issues, forbid_public_tokens=False)
        check_columns(
            sensitivity_headers,
            IDENTITY_SENSITIVITY_COLUMNS,
            "restricted_identity_sensitivity_pairs",
            issues,
            forbid_public_tokens=False,
        )
        identity_counts["identity_map_row_count"] = len(identity_rows)
        identity_counts["sensitivity_pair_count"] = len(sensitivity_rows)
        identity_by_image: dict[str, str] = {}
        identity_interface_error_count = 0
        if not sensitivity_rows:
            identity_interface_error_count += 1
            add_issue(
                issues,
                "ERROR",
                "empty_identity_sensitivity_manifest",
                "restricted_identity_sensitivity_pairs",
                "a supplied identity-sensitivity manifest must contain at least one confirmation pair",
            )
        for image_id in duplicate_keys(identity_rows, "image_id"):
            identity_interface_error_count += 1
            add_issue(issues, "ERROR", "duplicate_identity_map_image", "restricted_identity_map", "image appears more than once", image_id)
        for row in identity_rows:
            image_id = row.get("image_id", "")
            identity_id = row.get("identity_id", "").strip()
            identity_is_resolved = identity_id.lower() not in {"", "unknown", "unresolved", "na", "n/a", "none"}
            if image_id not in candidate_images:
                identity_counts["unexpected_identity_map_image_count"] += 1
                identity_interface_error_count += 1
                add_issue(
                    issues,
                    "ERROR",
                    "unexpected_identity_map_image",
                    "restricted_identity_map",
                    "identity-map image is outside the eligible candidate universe",
                    image_id,
                )
            if (
                row.get("partition_contract_version") != CONTRACT_VERSION
                or row.get("access_class") != "restricted"
                or not identity_is_resolved
            ):
                identity_interface_error_count += 1
                add_issue(
                    issues,
                    "ERROR",
                    "invalid_restricted_identity_row",
                    "restricted_identity_map",
                    "identity row requires current contract, resolved identity, and restricted access",
                    image_id,
                )
            identity_by_image[image_id] = identity_id

        selected_pair_ids: set[str] = set()
        for pair_id in duplicate_keys(sensitivity_rows, "canonical_pair_id"):
            identity_interface_error_count += 1
            add_issue(
                issues,
                "ERROR",
                "duplicate_sensitivity_pair",
                "restricted_identity_sensitivity_pairs",
                "pair appears more than once",
                pair_id,
            )
        for row in sensitivity_rows:
            pair_id = row.get("canonical_pair_id", "")
            selected_pair_ids.add(pair_id)
            pair = pair_by_id.get(pair_id)
            if (
                row.get("partition_contract_version") != CONTRACT_VERSION
                or not row.get("sensitivity_set_id", "").strip()
                or pair is None
                or pair.get("partition_role") != "confirmation"
                or pair.get("allocation_status") != "assigned"
            ):
                identity_counts["invalid_sensitivity_pair_count"] += 1
                identity_interface_error_count += 1
                add_issue(
                    issues,
                    "ERROR",
                    "invalid_identity_sensitivity_pair",
                    "restricted_identity_sensitivity_pairs",
                    "sensitivity pair must be a valid assigned confirmation pair",
                    pair_id,
                )

        build_images = {
            image_id
            for image_id, row in image_by_id.items()
            if row.get("partition_role") in {"development", "calibration"}
        }
        sensitivity_images: set[str] = set()
        for pair_id in selected_pair_ids:
            source = canonical_by_id.get(pair_id)
            if source:
                sensitivity_images.update((source["endpoint_a_image_id"], source["endpoint_b_image_id"]))
        required_identity_images = build_images | sensitivity_images
        unresolved = required_identity_images - set(identity_by_image)
        identity_counts["unresolved_required_image_count"] = len(unresolved)
        if unresolved:
            identity_interface_error_count += len(unresolved)
            for image_id in sorted(unresolved):
                add_issue(
                    issues,
                    "ERROR",
                    "unresolved_required_identity",
                    "restricted_identity_map",
                    "required image has no identity mapping",
                    image_id,
                )
        build_identities = {identity_by_image[image_id] for image_id in build_images if image_id in identity_by_image}
        sensitivity_identities = {
            identity_by_image[image_id] for image_id in sensitivity_images if image_id in identity_by_image
        }
        identity_overlap = build_identities & sensitivity_identities
        identity_counts["sensitivity_identity_overlap_count"] = len(identity_overlap)
        if identity_overlap:
            identity_interface_error_count += len(identity_overlap)
            add_issue(
                issues,
                "ERROR",
                "sensitivity_identity_overlap",
                "restricted_identity",
                f"{len(identity_overlap)} sensitivity identities also occur in development/calibration",
            )
        identity_status = "PASS" if identity_interface_error_count == 0 else "FAIL"

    error_count = sum(issue["severity"] == "ERROR" for issue in issues)
    structural_status = "PASS" if error_count == 0 else "FAIL"
    lock_eligibility = (
        "PENDING_IDENTITY_AND_FREEZE_GATES"
        if structural_status == "PASS" and identity_status == "NOT_EVALUATED"
        else "PENDING_FREEZE_GATES"
        if structural_status == "PASS" and identity_status == "PASS"
        else "REPAIR_REQUIRED"
    )
    audit = {
        "audit_version": "pferi_v2_partition_constraint_audit_v1",
        "contract_version": CONTRACT_VERSION,
        "status": structural_status,
        "identity_sensitivity_status": identity_status,
        "partition_lock_eligibility": lock_eligibility,
        "claim_boundary": (
            "PASS means the supplied manifests satisfy this outcome-free structural contract. "
            "It never means partition_locked and never authorizes outcome review."
        ),
        "input_artifacts": {
            "canonical_pairs": {"path": recorded_path(canonical_pairs_path), "sha256": sha256(canonical_pairs_path)},
            "image_partitions": {"path": recorded_path(image_partitions_path), "sha256": sha256(image_partitions_path)},
            "pair_partitions": {"path": recorded_path(pair_partitions_path), "sha256": sha256(pair_partitions_path)},
            "identity_map": (
                {"path": recorded_path(identity_map_path), "sha256": sha256(identity_map_path)} if identity_map_path else None
            ),
            "identity_sensitivity_pairs": (
                {"path": recorded_path(identity_sensitivity_path), "sha256": sha256(identity_sensitivity_path)}
                if identity_sensitivity_path
                else None
            ),
        },
        "counts": {
            "eligible_candidate_image_count": len(candidate_images),
            "image_partition_row_count": len(image_rows),
            "missing_candidate_image_count": len(missing_images),
            "unexpected_image_count": len(unexpected_images),
            "eligible_candidate_pair_count": len(canonical_by_id),
            "pair_partition_row_count": len(pair_rows),
            "missing_candidate_pair_count": len(missing_pairs),
            "unexpected_pair_count": len(unexpected_pairs),
            "image_role_counts": dict(sorted(Counter(row.get("partition_role", "") for row in image_rows).items())),
            "pair_role_counts": dict(sorted(pair_role_counts.items())),
            "cross_role_candidate_pair_count": cross_role_pair_count,
            "cross_role_pair_not_excluded_count": cross_role_pair_not_excluded_count,
            "active_pair_endpoint_role_mismatch_count": active_pair_role_mismatch_count,
            "canonical_endpoint_mismatch_count": endpoint_mismatch_count,
            "excluded_pair_rule_mismatch_count": excluded_pair_rule_mismatch_count,
            "invalid_image_role_count": invalid_image_role_count,
            "image_status_mismatch_count": image_status_mismatch_count,
            **identity_counts,
            "error_count": error_count,
        },
    }
    return audit, issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-pairs", type=Path, required=True)
    parser.add_argument("--image-partitions", type=Path, required=True)
    parser.add_argument("--pair-partitions", type=Path, required=True)
    parser.add_argument("--identity-map", type=Path)
    parser.add_argument("--identity-sensitivity-pairs", type=Path)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--issue-csv", type=Path, required=True)
    parser.add_argument("--write-schema", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    audit, issues = validate_partitions(
        args.canonical_pairs.resolve(),
        args.image_partitions.resolve(),
        args.pair_partitions.resolve(),
        identity_map_path=args.identity_map.resolve() if args.identity_map else None,
        identity_sensitivity_path=args.identity_sensitivity_pairs.resolve() if args.identity_sensitivity_pairs else None,
    )
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(args.issue_csv, issues, ISSUE_COLUMNS)
    if args.write_schema:
        args.write_schema.parent.mkdir(parents=True, exist_ok=True)
        args.write_schema.write_text(json.dumps(build_contract_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(audit["status"])
    print(json.dumps(audit["counts"], indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
