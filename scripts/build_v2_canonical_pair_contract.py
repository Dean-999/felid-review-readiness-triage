#!/usr/bin/env python3
"""Validate the PF-ERI v2 canonical unordered-pair manifest contract.

This validator deliberately accepts no reviewability outcome, PF-ERI score,
route, or identity-truth column in the canonical-pair or candidate-membership
manifest. Identity truth, when available, is supplied through a separate
restricted manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CONTRACT_VERSION = "pferi_v2_canonical_pair_contract_v1"

CANONICAL_PAIR_COLUMNS = [
    "contract_version",
    "canonical_pair_id",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "source_dataset",
    "pair_availability_status",
    "pair_inclusion_status",
    "exclusion_reason",
]

CANDIDATE_MEMBERSHIP_COLUMNS = [
    "contract_version",
    "canonical_pair_id",
    "descriptor_name",
    "queue_name",
    "queue_snapshot_id",
    "query_image_id",
    "candidate_image_id",
    "candidate_rank",
    "descriptor_similarity",
    "membership_direction",
]

IDENTITY_AUDIT_COLUMNS = [
    "canonical_pair_id",
    "same_identity_known_id",
    "identity_truth_source",
    "access_class",
]

FORBIDDEN_PAIR_MANIFEST_TOKENS = (
    "review",
    "decision",
    "route",
    "pferi",
    "outcome",
    "label",
    "feature",
    "identity",
)
FORBIDDEN_IDENTITY_AUDIT_TOKENS = ("review", "decision", "route", "pferi", "outcome", "feature")


def canonical_pair_id(image_id_a: str, image_id_b: str) -> str:
    """Return an order-invariant opaque identifier for two distinct image IDs."""
    left = str(image_id_a).strip()
    right = str(image_id_b).strip()
    if not left or not right:
        raise ValueError("canonical pair endpoints must be non-empty")
    if left == right:
        raise ValueError("canonical pairs cannot be self-pairs")
    ordered = sorted((left, right))
    payload = json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))
    return "pferi_v2_pair_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_contract_schema() -> dict[str, Any]:
    """Return the machine-readable v2 manifest contract."""
    return {
        "contract_version": CONTRACT_VERSION,
        "description": "PF-ERI v2 canonical unordered-pair contract.",
        "canonical_pairs": {
            "required_columns": CANONICAL_PAIR_COLUMNS,
            "forbidden_column_tokens": list(FORBIDDEN_PAIR_MANIFEST_TOKENS),
            "rules": [
                "endpoint_a_image_id is lexicographically smaller than endpoint_b_image_id",
                "canonical_pair_id equals the SHA-256-derived opaque ID of the two endpoints",
                "self-pairs and duplicate canonical_pair_id values are invalid",
                "identity truth, review outcomes, routes, PF-ERI values, and feature values are excluded",
            ],
        },
        "candidate_memberships": {
            "required_columns": CANDIDATE_MEMBERSHIP_COLUMNS,
            "forbidden_column_tokens": list(FORBIDDEN_PAIR_MANIFEST_TOKENS),
            "rules": [
                "many descriptor and directed memberships may reference one canonical pair",
                "query and candidate endpoints must equal the canonical endpoints in either direction",
                "membership_direction must match a_to_b or b_to_a",
                "candidate_rank is a positive integer and descriptor_similarity is finite",
            ],
        },
        "restricted_identity_audit": {
            "required_columns": IDENTITY_AUDIT_COLUMNS,
            "forbidden_column_tokens": list(FORBIDDEN_IDENTITY_AUDIT_TOKENS),
            "rules": [
                "identity truth is stored separately from the pair and membership manifests",
                "access_class must be restricted",
                "same_identity_known_id is yes, no, or unknown",
            ],
        },
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _forbidden_columns(headers: Iterable[str], forbidden_tokens: Sequence[str]) -> list[str]:
    return sorted(
        header
        for header in headers
        if any(token in header.lower() for token in forbidden_tokens)
    )


def _missing_columns(headers: Iterable[str], required_columns: Sequence[str]) -> list[str]:
    header_set = set(headers)
    return [column for column in required_columns if column not in header_set]


def _as_finite_float(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _add_issue(issues: list[dict[str, str]], code: str, message: str, row_id: str = "") -> None:
    issues.append({"code": code, "message": message, "row_id": row_id})


def validate_contract(
    canonical_pairs: Sequence[Mapping[str, str]],
    candidate_memberships: Sequence[Mapping[str, str]],
    identity_audit_rows: Sequence[Mapping[str, str]],
    canonical_headers: Sequence[str] | None = None,
    membership_headers: Sequence[str] | None = None,
    identity_headers: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate v2 manifests and return a deterministic audit dictionary."""
    issues: list[dict[str, str]] = []
    canonical_headers = list(canonical_headers or (list(canonical_pairs[0].keys()) if canonical_pairs else []))
    membership_headers = list(membership_headers or (list(candidate_memberships[0].keys()) if candidate_memberships else []))
    identity_headers = list(identity_headers or (list(identity_audit_rows[0].keys()) if identity_audit_rows else []))

    if not canonical_pairs:
        _add_issue(issues, "canonical_pairs_empty", "canonical_pairs manifest cannot be empty")
    for column in _missing_columns(canonical_headers, CANONICAL_PAIR_COLUMNS):
        _add_issue(issues, f"missing_column_in_canonical_pairs:{column}", "canonical_pairs is missing a required column")
    for column in _forbidden_columns(canonical_headers, FORBIDDEN_PAIR_MANIFEST_TOKENS):
        _add_issue(issues, f"forbidden_column_in_canonical_pairs:{column}", "canonical_pairs contains a forbidden field")
    if membership_headers:
        for column in _missing_columns(membership_headers, CANDIDATE_MEMBERSHIP_COLUMNS):
            _add_issue(issues, f"missing_column_in_candidate_memberships:{column}", "candidate_memberships is missing a required column")
        for column in _forbidden_columns(membership_headers, FORBIDDEN_PAIR_MANIFEST_TOKENS):
            _add_issue(issues, f"forbidden_column_in_candidate_memberships:{column}", "candidate_memberships contains a forbidden field")
    if identity_audit_rows:
        for column in _missing_columns(identity_headers, IDENTITY_AUDIT_COLUMNS):
            _add_issue(issues, f"missing_column_in_identity_audit:{column}", "identity audit is missing a required column")
        for column in _forbidden_columns(identity_headers, FORBIDDEN_IDENTITY_AUDIT_TOKENS):
            _add_issue(issues, f"forbidden_column_in_identity_audit:{column}", "identity audit contains a forbidden field")

    canonical_by_id: dict[str, Mapping[str, str]] = {}
    duplicate_canonical_ids = 0
    for row in canonical_pairs:
        pair_id = str(row.get("canonical_pair_id", ""))
        left = str(row.get("endpoint_a_image_id", "")).strip()
        right = str(row.get("endpoint_b_image_id", "")).strip()
        if row.get("contract_version") != CONTRACT_VERSION:
            _add_issue(issues, "invalid_contract_version_in_canonical_pairs", "unexpected canonical contract version", pair_id)
        if not left or not right:
            _add_issue(issues, "canonical_pair_endpoint_missing", "canonical pair endpoint is missing", pair_id)
            continue
        if left == right:
            _add_issue(issues, "canonical_pair_self_pair", "canonical pair is a self-pair", pair_id)
            continue
        if left >= right:
            _add_issue(issues, "canonical_endpoints_not_lexicographically_sorted", "canonical endpoints must be sorted", pair_id)
        expected_id = canonical_pair_id(left, right)
        if pair_id != expected_id:
            _add_issue(issues, "canonical_pair_id_mismatch", "canonical pair ID does not match endpoints", pair_id)
        if row.get("pair_inclusion_status") not in {"eligible", "excluded"}:
            _add_issue(issues, "invalid_pair_inclusion_status", "pair inclusion status must be eligible or excluded", pair_id)
        if row.get("pair_inclusion_status") == "excluded" and not str(row.get("exclusion_reason", "")).strip():
            _add_issue(issues, "excluded_pair_missing_reason", "excluded pair requires an exclusion reason", pair_id)
        if pair_id in canonical_by_id:
            duplicate_canonical_ids += 1
            _add_issue(issues, "duplicate_canonical_pair_id", "canonical pair ID occurs more than once", pair_id)
        else:
            canonical_by_id[pair_id] = row

    membership_keys: Counter[tuple[str, str, str, str, str]] = Counter()
    membership_by_pair: Counter[str] = Counter()
    for row in candidate_memberships:
        pair_id = str(row.get("canonical_pair_id", ""))
        query = str(row.get("query_image_id", "")).strip()
        candidate = str(row.get("candidate_image_id", "")).strip()
        if row.get("contract_version") != CONTRACT_VERSION:
            _add_issue(issues, "invalid_contract_version_in_candidate_memberships", "unexpected membership contract version", pair_id)
        canonical = canonical_by_id.get(pair_id)
        if canonical is None:
            _add_issue(issues, "membership_references_unknown_canonical_pair", "membership does not reference a canonical pair", pair_id)
            continue
        left = str(canonical["endpoint_a_image_id"])
        right = str(canonical["endpoint_b_image_id"])
        if {query, candidate} != {left, right} or query == candidate:
            _add_issue(issues, "membership_endpoints_do_not_match_canonical_pair", "membership endpoints do not match canonical pair", pair_id)
        expected_direction = "a_to_b" if (query, candidate) == (left, right) else "b_to_a"
        if row.get("membership_direction") != expected_direction:
            _add_issue(issues, "membership_direction_mismatch", "membership direction does not match endpoints", pair_id)
        rank = str(row.get("candidate_rank", ""))
        if not rank.isdigit() or int(rank) < 1:
            _add_issue(issues, "invalid_candidate_rank", "candidate rank must be a positive integer", pair_id)
        if not _as_finite_float(str(row.get("descriptor_similarity", ""))):
            _add_issue(issues, "invalid_descriptor_similarity", "descriptor similarity must be finite", pair_id)
        key = (
            pair_id,
            str(row.get("descriptor_name", "")),
            str(row.get("queue_snapshot_id", "")),
            query,
            candidate,
        )
        membership_keys[key] += 1
        membership_by_pair[pair_id] += 1

    for count in membership_keys.values():
        if count > 1:
            _add_issue(issues, "duplicate_candidate_membership", "candidate membership occurs more than once")

    identity_ids: Counter[str] = Counter()
    for row in identity_audit_rows:
        pair_id = str(row.get("canonical_pair_id", ""))
        if pair_id not in canonical_by_id:
            _add_issue(issues, "identity_audit_references_unknown_canonical_pair", "identity audit references unknown canonical pair", pair_id)
        if row.get("same_identity_known_id") not in {"yes", "no", "unknown"}:
            _add_issue(issues, "invalid_same_identity_known_id", "identity truth must be yes, no, or unknown", pair_id)
        if row.get("access_class") != "restricted":
            _add_issue(issues, "identity_audit_not_restricted", "identity audit must have restricted access", pair_id)
        identity_ids[pair_id] += 1
    for pair_id, count in identity_ids.items():
        if count > 1:
            _add_issue(issues, "duplicate_identity_audit_row", "identity audit contains duplicate canonical pair", pair_id)

    error_codes = sorted({issue["code"] for issue in issues})
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "canonical_pair_count": len(canonical_pairs),
        "candidate_membership_count": len(candidate_memberships),
        "identity_audit_row_count": len(identity_audit_rows),
        "multi_membership_pair_count": sum(count > 1 for count in membership_by_pair.values()),
        "duplicate_canonical_pair_count": duplicate_canonical_ids,
        "error_codes": error_codes,
        "issues": issues,
        "claim_boundary": "Contract validation only; no outcome labels, PF-ERI scores, routes, or identity truth enter reviewer-facing pair manifests.",
    }


def write_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_contract_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-pairs", type=Path, required=True)
    parser.add_argument("--candidate-memberships", type=Path, required=True)
    parser.add_argument("--identity-audit", type=Path)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--write-schema", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    canonical_pairs, canonical_headers = read_csv(args.canonical_pairs)
    memberships, membership_headers = read_csv(args.candidate_memberships)
    identity_rows: list[dict[str, str]] = []
    identity_headers: list[str] = []
    if args.identity_audit is not None:
        identity_rows, identity_headers = read_csv(args.identity_audit)
    audit = validate_contract(
        canonical_pairs,
        memberships,
        identity_rows,
        canonical_headers=canonical_headers,
        membership_headers=membership_headers,
        identity_headers=identity_headers,
    )
    if args.write_schema is not None:
        write_schema(args.write_schema)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
