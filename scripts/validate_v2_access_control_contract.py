#!/usr/bin/env python3
"""Validate the PF-ERI v2 least-privilege access-control and leak-response contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_access_control_and_leak_response_contract_v1"
ROLE_IDS = (
    "protocol_custodian",
    "identity_custodian",
    "packet_builder",
    "measurement_operator",
    "first_pass_reviewer",
    "adjudicator",
    "development_analyst",
    "calibration_analyst",
    "confirmation_release_officer",
    "confirmation_analyst",
    "independent_interface_auditor",
)
ARTIFACT_IDS = (
    "frozen_candidate_manifests",
    "image_partition_manifest",
    "pair_partition_manifest",
    "restricted_identity_map",
    "restricted_identity_sensitivity_manifest",
    "rendered_asset_source",
    "reviewer_visible_packet",
    "restricted_packet_linkage",
    "own_raw_response_submission",
    "prior_or_peer_raw_responses",
    "development_feature_table",
    "development_outcome_table",
    "development_model_artifacts",
    "calibration_feature_table",
    "calibration_outcome_table",
    "calibration_policy_artifacts",
    "confirmation_feature_table",
    "confirmation_outcome_table",
    "frozen_confirmation_analysis_bundle",
    "final_confirmation_analysis_outputs",
    "independent_leakage_audit_evidence",
    "restricted_incident_detail",
    "public_incident_register",
)
PERMISSIONS = ("read", "write", "execute_only")
ISSUE_FIELDS = ("severity", "code", "role_id", "artifact_id", "message")


def build_contract_schema() -> dict[str, Any]:
    access_matrix = {
        "protocol_custodian": {
            "read": [
                "frozen_candidate_manifests",
                "image_partition_manifest",
                "pair_partition_manifest",
                "public_incident_register",
            ],
            "write": ["public_incident_register"],
            "execute_only": [],
        },
        "identity_custodian": {
            "read": ["restricted_identity_map", "restricted_identity_sensitivity_manifest"],
            "write": ["restricted_identity_map", "restricted_identity_sensitivity_manifest"],
            "execute_only": [],
        },
        "packet_builder": {
            "read": [
                "frozen_candidate_manifests",
                "image_partition_manifest",
                "pair_partition_manifest",
                "rendered_asset_source",
                "restricted_packet_linkage",
            ],
            "write": ["reviewer_visible_packet", "restricted_packet_linkage"],
            "execute_only": [],
        },
        "measurement_operator": {
            "read": [
                "frozen_candidate_manifests",
                "image_partition_manifest",
                "pair_partition_manifest",
                "rendered_asset_source",
            ],
            "write": ["development_feature_table", "calibration_feature_table", "confirmation_feature_table"],
            "execute_only": [],
        },
        "first_pass_reviewer": {
            "read": ["reviewer_visible_packet"],
            "write": ["own_raw_response_submission"],
            "execute_only": [],
        },
        "adjudicator": {
            "read": ["reviewer_visible_packet"],
            "write": ["own_raw_response_submission"],
            "execute_only": [],
        },
        "development_analyst": {
            "read": [
                "frozen_candidate_manifests",
                "image_partition_manifest",
                "pair_partition_manifest",
                "development_feature_table",
                "development_outcome_table",
            ],
            "write": ["development_model_artifacts"],
            "execute_only": [],
        },
        "calibration_analyst": {
            "read": [
                "frozen_candidate_manifests",
                "image_partition_manifest",
                "pair_partition_manifest",
                "development_model_artifacts",
                "calibration_feature_table",
                "calibration_outcome_table",
            ],
            "write": ["calibration_policy_artifacts"],
            "execute_only": [],
        },
        "confirmation_release_officer": {
            "read": ["confirmation_feature_table", "confirmation_outcome_table", "frozen_confirmation_analysis_bundle"],
            "write": [],
            "execute_only": ["frozen_confirmation_analysis_bundle"],
        },
        "confirmation_analyst": {
            "read": [
                "confirmation_outcome_table",
                "confirmation_feature_table",
                "frozen_confirmation_analysis_bundle",
                "calibration_policy_artifacts",
            ],
            "write": ["final_confirmation_analysis_outputs"],
            "execute_only": ["frozen_confirmation_analysis_bundle"],
        },
        "independent_interface_auditor": {
            "read": ["reviewer_visible_packet", "independent_leakage_audit_evidence"],
            "write": ["independent_leakage_audit_evidence"],
            "execute_only": [],
        },
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "purpose": (
            "Preserve development, calibration, and one-shot confirmation independence through default-deny "
            "artifact access, role separation, and an immutable leak-response procedure."
        ),
        "default_access_rule": "deny_unlisted_access",
        "roles": list(ROLE_IDS),
        "artifacts": list(ARTIFACT_IDS),
        "permissions": list(PERMISSIONS),
        "access_matrix": access_matrix,
        "hard_prohibitions": [
            "First-pass reviewers and adjudicators receive no canonical-pair identifiers, image identifiers, restricted linkage, identity truth, feature values, descriptor scores, ranks, routes, thresholds, prior responses, or derived labels.",
            "Packet builders receive no outcome labels, model artifacts, calibration policies, or confirmation outputs.",
            "Measurement operators receive no outcome labels, identity truth, model artifacts, calibration policies, or confirmation outputs.",
            "Identity custodians receive no review outcomes, model artifacts, calibration policies, or confirmation outputs.",
            "Development and calibration analysts receive no confirmation outcomes before the frozen confirmation release.",
            "The confirmation analyst cannot write development-model, calibration-policy, partition, packet, or confirmation-analysis-bundle artifacts.",
            "The confirmation release officer cannot alter the frozen confirmation analysis bundle or final confirmation outputs.",
            "Independent interface auditors receive no restricted linkage, identity truth, outcomes, prior responses, model artifacts, or calibration policies.",
        ],
        "role_assignment_template_columns": [
            "access_control_contract_version",
            "actor_opaque_id",
            "role_id",
            "scope_id",
            "assignment_status",
            "conflict_attestation",
            "signed_at_utc",
        ],
        "incident_register_template_columns": [
            "incident_id",
            "detected_at_utc",
            "detected_by_role",
            "affected_scope_id",
            "affected_artifact_class",
            "exposure_type",
            "confirmation_exposed_before_freeze",
            "immediate_containment",
            "evidence_hashes",
            "restricted_incident_detail_pointer",
            "remediation_summary",
            "retest_audit_id",
            "final_disposition",
            "release_authority_role",
            "closed_at_utc",
        ],
        "leak_disposition_rule": (
            "A confirmed exposure before confirmation freeze of a confirmation outcome, directly or by an inferable "
            "derivative, to any person who can still alter model form, features, loss, threshold, sampling, or reporting "
            "choices permanently invalidates that confirmation partition for v2. The affected data and logs are preserved; "
            "the project may only proceed with a newly drawn, unseen confirmation set under a successor protocol."
        ),
        "packet_leak_rule": (
            "Any exposure of a forbidden reviewer condition invalidates the affected packet batch. Affected raw responses "
            "are retained but cannot enter primary analysis. Remediation requires containment, evidence preservation, "
            "independent retest, and a replacement packet drawn under the frozen allocation rule."
        ),
    }


def add_issue(
    issues: list[dict[str, str]], severity: str, code: str, message: str, role_id: str = "", artifact_id: str = ""
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "role_id": role_id,
            "artifact_id": artifact_id,
            "message": message,
        }
    )


def validate_contract(contract: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    if contract != build_contract_schema():
        add_issue(
            issues,
            "ERROR",
            "contract_content_mismatch",
            "this frozen v1 contract differs from its executable specification; create a new version for any change",
        )
    if contract.get("contract_version") != CONTRACT_VERSION:
        add_issue(issues, "ERROR", "contract_version_mismatch", "unexpected contract version")
    if contract.get("default_access_rule") != "deny_unlisted_access":
        add_issue(issues, "ERROR", "default_deny_missing", "default access rule must deny unlisted access")
    if set(contract.get("roles", [])) != set(ROLE_IDS):
        add_issue(issues, "ERROR", "role_set_mismatch", "role set differs from the fixed contract")
    if set(contract.get("artifacts", [])) != set(ARTIFACT_IDS):
        add_issue(issues, "ERROR", "artifact_set_mismatch", "artifact set differs from the fixed contract")
    matrix = contract.get("access_matrix", {})
    if set(matrix) != set(ROLE_IDS):
        add_issue(issues, "ERROR", "access_matrix_role_mismatch", "access matrix must enumerate every fixed role")
    for role_id in ROLE_IDS:
        grants = matrix.get(role_id, {})
        for permission in PERMISSIONS:
            values = grants.get(permission)
            if not isinstance(values, list):
                add_issue(issues, "ERROR", "invalid_permission_list", "permission grant must be a list", role_id)
                continue
            for artifact_id in values:
                if artifact_id not in ARTIFACT_IDS:
                    add_issue(issues, "ERROR", "unknown_artifact_grant", "unknown artifact in grant", role_id, str(artifact_id))
            if len(values) != len(set(values)):
                add_issue(issues, "ERROR", "duplicate_artifact_grant", "duplicate artifact grant", role_id)

    def granted(role_id: str, artifact_id: str) -> bool:
        return any(artifact_id in matrix.get(role_id, {}).get(permission, []) for permission in PERMISSIONS)

    reviewer_roles = ("first_pass_reviewer", "adjudicator")
    reviewer_allowlist = {"reviewer_visible_packet", "own_raw_response_submission"}
    for role_id in reviewer_roles:
        for permission in PERMISSIONS:
            for artifact_id in matrix.get(role_id, {}).get(permission, []):
                if artifact_id not in reviewer_allowlist:
                    add_issue(
                        issues,
                        "ERROR",
                        "reviewer_boundary_violation",
                        "reviewer/adjudicator has forbidden artifact access",
                        role_id,
                        artifact_id,
                    )
        if "reviewer_visible_packet" not in matrix.get(role_id, {}).get("read", []):
            add_issue(issues, "ERROR", "reviewer_packet_missing", "reviewer packet read access is required", role_id)
        if "own_raw_response_submission" not in matrix.get(role_id, {}).get("write", []):
            add_issue(issues, "ERROR", "raw_response_write_missing", "own raw response write access is required", role_id)

    outcome_artifacts = {"development_outcome_table", "calibration_outcome_table", "confirmation_outcome_table"}
    outcome_forbidden_roles = {
        "identity_custodian",
        "packet_builder",
        "measurement_operator",
        "independent_interface_auditor",
        *reviewer_roles,
    }
    for role_id in outcome_forbidden_roles:
        for artifact_id in outcome_artifacts:
            if granted(role_id, artifact_id):
                add_issue(issues, "ERROR", "forbidden_outcome_access", "role must not access outcome artifacts", role_id, artifact_id)

    for role_id in ("development_analyst", "calibration_analyst"):
        if granted(role_id, "confirmation_outcome_table"):
            add_issue(
                issues,
                "ERROR",
                "premature_confirmation_access",
                "development/calibration role must not access confirmation outcomes",
                role_id,
                "confirmation_outcome_table",
            )
    partition_feature_table = {
        "development_analyst": "development_feature_table",
        "calibration_analyst": "calibration_feature_table",
        "confirmation_analyst": "confirmation_feature_table",
        "confirmation_release_officer": "confirmation_feature_table",
    }
    all_feature_tables = {"development_feature_table", "calibration_feature_table", "confirmation_feature_table"}
    for role_id, required_feature_table in partition_feature_table.items():
        if required_feature_table not in matrix.get(role_id, {}).get("read", []):
            add_issue(
                issues,
                "ERROR",
                "partition_feature_access_missing",
                "analysis role must read its own partition-scoped feature table",
                role_id,
                required_feature_table,
            )
        for artifact_id in all_feature_tables - {required_feature_table}:
            if granted(role_id, artifact_id):
                add_issue(
                    issues,
                    "ERROR",
                    "cross_partition_feature_access",
                    "analysis role must not access another partition's feature table",
                    role_id,
                    artifact_id,
                )
    for artifact_id in all_feature_tables:
        if artifact_id not in matrix.get("measurement_operator", {}).get("write", []):
            add_issue(
                issues,
                "ERROR",
                "measurement_feature_write_missing",
                "measurement operator must write each partition-scoped feature table",
                "measurement_operator",
                artifact_id,
            )
    for role_id in ("confirmation_release_officer", "confirmation_analyst"):
        forbidden_writes = {
            "development_model_artifacts",
            "calibration_policy_artifacts",
            "image_partition_manifest",
            "pair_partition_manifest",
            "reviewer_visible_packet",
            "frozen_confirmation_analysis_bundle",
        }
        for artifact_id in matrix.get(role_id, {}).get("write", []):
            if artifact_id in forbidden_writes:
                add_issue(
                    issues,
                    "ERROR",
                    "confirmation_mutability_violation",
                    "confirmation role may not alter pre-release decision artifacts",
                    role_id,
                    artifact_id,
                )
    if "confirmation_outcome_table" not in matrix.get("confirmation_release_officer", {}).get("read", []):
        add_issue(issues, "ERROR", "release_officer_outcome_missing", "release officer requires read access to confirmation outcome", "confirmation_release_officer")
    if "confirmation_outcome_table" not in matrix.get("confirmation_analyst", {}).get("read", []):
        add_issue(issues, "ERROR", "confirmation_outcome_missing", "confirmation analyst requires read access at release", "confirmation_analyst")
    if "final_confirmation_analysis_outputs" not in matrix.get("confirmation_analyst", {}).get("write", []):
        add_issue(issues, "ERROR", "confirmation_output_write_missing", "confirmation analyst must write final outputs", "confirmation_analyst")

    required_incident_columns = set(build_contract_schema()["incident_register_template_columns"])
    if set(contract.get("incident_register_template_columns", [])) != required_incident_columns:
        add_issue(issues, "ERROR", "incident_schema_mismatch", "incident register schema differs from fixed contract")
    for key in ("leak_disposition_rule", "packet_leak_rule"):
        if not isinstance(contract.get(key), str) or not contract[key].strip():
            add_issue(issues, "ERROR", "missing_leak_disposition_rule", f"{key} must be a nonempty rule")

    error_count = sum(issue["severity"] == "ERROR" for issue in issues)
    audit = {
        "audit_version": "pferi_v2_access_control_contract_audit_v1",
        "contract_version": contract.get("contract_version", ""),
        "status": "PASS" if error_count == 0 else "FAIL",
        "error_count": error_count,
        "role_count": len(contract.get("roles", [])),
        "artifact_count": len(contract.get("artifacts", [])),
        "claim_boundary": (
            "This validates the abstract least-privilege contract. It does not assign real people, create a partition, "
            "or authorize outcome review."
        ),
    }
    return audit, issues


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ISSUE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--issue-csv", type=Path, required=True)
    parser.add_argument("--write-schema", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    audit, issues = validate_contract(contract)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(args.issue_csv, issues)
    if args.write_schema:
        args.write_schema.parent.mkdir(parents=True, exist_ok=True)
        args.write_schema.write_text(json.dumps(build_contract_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(audit["status"])
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
