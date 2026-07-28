#!/usr/bin/env python3
"""Validate and freeze PF-ERI v2 human outcomes after adjudication.

The collection interface is deliberately not an admission criterion. Outcome
admission depends on exact packet coverage, valid human-response fields,
assignment/linkage consistency, and a study-owner acceptance decision. Time
fields are neither copied nor analysed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts import build_v2_formal_reviewer_packages as formal
except ModuleNotFoundError:  # Support direct `python scripts/<name>.py` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import build_v2_formal_reviewer_packages as formal


ADJUDICATION_LINKAGE_COLUMNS = [
    "adjudication_packet_id", "canonical_pair_id", "left_image_id", "right_image_id",
    "adjudicator_alias", "formal_sampling_stage", "first_pass_reviewer_codes",
    "first_pass_packet_ids",
]
SAMPLING_REQUIRED_COLUMNS = [
    "formal_sampling_stage", "canonical_pair_id", "endpoint_a_image_id",
    "endpoint_b_image_id", "sampling_cell_id", "first_order_inclusion_probability",
]
FINAL_OUTCOME_COLUMNS = [
    "canonical_pair_id", "formal_sampling_stage", "endpoint_a_image_id",
    "endpoint_b_image_id", "sampling_cell_id", "first_order_inclusion_probability",
    "first_pass_packet_id_1", "first_pass_reviewer_code_1", "first_pass_decision_1",
    "first_pass_reason_codes_1", "first_pass_confidence_1", "first_pass_packet_id_2",
    "first_pass_reviewer_code_2", "first_pass_decision_2", "first_pass_reason_codes_2",
    "first_pass_confidence_2", "first_pass_exact_agreement", "first_pass_binary_agreement",
    "adjudication_required", "adjudication_packet_id", "adjudicator_alias",
    "adjudication_decision", "adjudication_reason_codes", "adjudication_confidence",
    "final_label_source", "final_three_category_label", "review_ready_label",
    "not_ready_or_uncertain_label",
]
DECISIONS = {"review_ready", "not_review_ready", "uncertain"}
CONFIDENCE = {"low", "medium", "high"}
REASONS = {
    "none_review_ready", "low_evidence", "non_comparable",
    "both_low_evidence_and_non_comparable", "other",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path, required_columns: Iterable[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        missing = sorted(set(required_columns) - set(fields))
        if missing:
            raise ValueError(f"missing columns in {path}: {missing}")
        return list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def validate_response(row: dict[str, str], context: str) -> None:
    packet = row.get("review_packet_id", "")
    decision = row.get("review_decision", "")
    confidence = row.get("confidence", "")
    reasons = set(filter(None, row.get("reason_codes", "").split(";")))
    if decision not in DECISIONS:
        raise ValueError(f"invalid decision in {context}: {packet}")
    if confidence not in CONFIDENCE:
        raise ValueError(f"invalid confidence in {context}: {packet}")
    if not reasons or not reasons.issubset(REASONS):
        raise ValueError(f"invalid reason values in {context}: {packet}")
    if decision == "review_ready" and reasons != {"none_review_ready"}:
        raise ValueError(f"invalid reason combination in {context}: {packet}")
    if decision != "review_ready" and "none_review_ready" in reasons:
        raise ValueError(f"invalid reason combination in {context}: {packet}")
    if row.get("technical_problem_flag") != "no":
        raise ValueError(f"unresolved technical problem in {context}: {packet}")


def collect_responses(directory: Path, context: str) -> tuple[dict[str, dict[str, str]], list[Path]]:
    responses: dict[str, dict[str, str]] = {}
    files = sorted(directory.rglob("raw_responses.csv"))
    if not files:
        return responses, files
    for path in files:
        for row in read_csv(path, formal.RAW_RESPONSE_COLUMNS):
            validate_response(row, context)
            packet = row["review_packet_id"]
            if packet in responses:
                raise ValueError(f"duplicate response packet in {context}: {packet}")
            responses[packet] = row
    response_ids = [row["raw_reviewer_response_id"] for row in responses.values()]
    if len(response_ids) != len(set(response_ids)):
        raise ValueError(f"duplicate raw response id in {context}")
    return responses, files


def binary_label(decision: str) -> str:
    return "1" if decision == "review_ready" else "0"


def finalize(
    *,
    assignment: Path,
    first_pass: Path,
    linkage: Path,
    adjudication: Path,
    sampling: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite: {output_dir}")

    assignments = read_csv(assignment, formal.ASSIGNMENT_COLUMNS)
    assignment_by_packet = {row["review_packet_id"]: row for row in assignments}
    if len(assignment_by_packet) != len(assignments):
        raise ValueError("duplicate first-pass assignment packet")
    first_pass_responses, first_pass_files = collect_responses(first_pass, "first-pass")
    if set(first_pass_responses) != set(assignment_by_packet):
        raise ValueError("first-pass returns do not exactly cover assignments")

    pair_entries: dict[str, list[tuple[dict[str, str], dict[str, str]]]] = defaultdict(list)
    for packet, assignment_row in assignment_by_packet.items():
        pair_entries[assignment_row["canonical_pair_id"]].append(
            (assignment_row, first_pass_responses[packet])
        )
    if any(len(entries) != 2 for entries in pair_entries.values()):
        raise ValueError("every formal pair must have exactly two first-pass responses")
    for pair_id, entries in pair_entries.items():
        if entries[0][0]["reviewer_code"] == entries[1][0]["reviewer_code"]:
            raise ValueError(f"pair has duplicate first-pass reviewer code: {pair_id}")
        if entries[0][0]["formal_sampling_stage"] != entries[1][0]["formal_sampling_stage"]:
            raise ValueError(f"pair has inconsistent sampling stage: {pair_id}")

    disagreements = {
        pair_id
        for pair_id, entries in pair_entries.items()
        if entries[0][1]["review_decision"] != entries[1][1]["review_decision"]
    }
    linkage_rows = read_csv(linkage, ADJUDICATION_LINKAGE_COLUMNS)
    linkage_by_packet = {row["adjudication_packet_id"]: row for row in linkage_rows}
    linkage_by_pair = {row["canonical_pair_id"]: row for row in linkage_rows}
    if len(linkage_by_packet) != len(linkage_rows) or len(linkage_by_pair) != len(linkage_rows):
        raise ValueError("duplicate adjudication linkage")
    if set(linkage_by_pair) != disagreements:
        raise ValueError("adjudication linkage does not exactly cover disagreements")

    adjudication_responses, adjudication_files = collect_responses(adjudication, "adjudication")
    if set(adjudication_responses) != set(linkage_by_packet):
        raise ValueError("adjudication returns do not exactly cover disagreements")

    sampling_rows = read_csv(sampling, SAMPLING_REQUIRED_COLUMNS)
    sampling_by_pair = {row["canonical_pair_id"]: row for row in sampling_rows}
    if len(sampling_by_pair) != len(sampling_rows):
        raise ValueError("duplicate pair in formal sampling manifest")
    if set(sampling_by_pair) != set(pair_entries):
        raise ValueError("formal sampling manifest does not exactly cover outcome pairs")

    final_rows: list[dict[str, str]] = []
    for pair_id in sorted(pair_entries):
        entries = sorted(pair_entries[pair_id], key=lambda item: item[0]["reviewer_code"])
        assignment_1, response_1 = entries[0]
        assignment_2, response_2 = entries[1]
        sample = sampling_by_pair[pair_id]
        assignment_endpoints = {assignment_1["left_image_id"], assignment_1["right_image_id"]}
        sample_endpoints = {sample["endpoint_a_image_id"], sample["endpoint_b_image_id"]}
        if assignment_endpoints != sample_endpoints:
            raise ValueError(f"sampling endpoint mismatch: {pair_id}")
        if assignment_1["formal_sampling_stage"] != sample["formal_sampling_stage"]:
            raise ValueError(f"sampling stage mismatch: {pair_id}")

        exact_agreement = response_1["review_decision"] == response_2["review_decision"]
        binary_agreement = binary_label(response_1["review_decision"]) == binary_label(response_2["review_decision"])
        adjudication_row = linkage_by_pair.get(pair_id)
        adjudication_response: dict[str, str] = {}
        if exact_agreement:
            final_decision = response_1["review_decision"]
            final_source = "first_pass_exact_agreement"
        else:
            if adjudication_row is None:
                raise ValueError(f"missing adjudication linkage: {pair_id}")
            expected_first_pass_packets = {
                assignment_1["review_packet_id"], assignment_2["review_packet_id"]
            }
            if set(adjudication_row["first_pass_packet_ids"].split(";")) != expected_first_pass_packets:
                raise ValueError(f"adjudication first-pass linkage mismatch: {pair_id}")
            if adjudication_row["formal_sampling_stage"] != sample["formal_sampling_stage"]:
                raise ValueError(f"adjudication stage mismatch: {pair_id}")
            adjudication_response = adjudication_responses[adjudication_row["adjudication_packet_id"]]
            final_decision = adjudication_response["review_decision"]
            final_source = "fresh_blinded_adjudication"

        final_rows.append(
            {
                "canonical_pair_id": pair_id,
                "formal_sampling_stage": sample["formal_sampling_stage"],
                "endpoint_a_image_id": sample["endpoint_a_image_id"],
                "endpoint_b_image_id": sample["endpoint_b_image_id"],
                "sampling_cell_id": sample["sampling_cell_id"],
                "first_order_inclusion_probability": sample["first_order_inclusion_probability"],
                "first_pass_packet_id_1": assignment_1["review_packet_id"],
                "first_pass_reviewer_code_1": assignment_1["reviewer_code"],
                "first_pass_decision_1": response_1["review_decision"],
                "first_pass_reason_codes_1": response_1["reason_codes"],
                "first_pass_confidence_1": response_1["confidence"],
                "first_pass_packet_id_2": assignment_2["review_packet_id"],
                "first_pass_reviewer_code_2": assignment_2["reviewer_code"],
                "first_pass_decision_2": response_2["review_decision"],
                "first_pass_reason_codes_2": response_2["reason_codes"],
                "first_pass_confidence_2": response_2["confidence"],
                "first_pass_exact_agreement": "yes" if exact_agreement else "no",
                "first_pass_binary_agreement": "yes" if binary_agreement else "no",
                "adjudication_required": "no" if exact_agreement else "yes",
                "adjudication_packet_id": adjudication_row["adjudication_packet_id"] if adjudication_row else "",
                "adjudicator_alias": adjudication_row["adjudicator_alias"] if adjudication_row else "",
                "adjudication_decision": adjudication_response.get("review_decision", ""),
                "adjudication_reason_codes": adjudication_response.get("reason_codes", ""),
                "adjudication_confidence": adjudication_response.get("confidence", ""),
                "final_label_source": final_source,
                "final_three_category_label": final_decision,
                "review_ready_label": binary_label(final_decision),
                "not_ready_or_uncertain_label": "0" if final_decision == "review_ready" else "1",
            }
        )

    label_counts = dict(sorted(Counter(row["final_three_category_label"] for row in final_rows).items()))
    stage_counts = {
        stage: dict(sorted(Counter(row["final_three_category_label"] for row in final_rows if row["formal_sampling_stage"] == stage).items()))
        for stage in sorted({row["formal_sampling_stage"] for row in final_rows})
    }
    source_hashes = {
        "assignment": sha256_file(assignment),
        "adjudication_linkage": sha256_file(linkage),
        "sampling_manifest": sha256_file(sampling),
        "first_pass_returns": {str(path): sha256_file(path) for path in first_pass_files},
        "adjudication_returns": {str(path): sha256_file(path) for path in adjudication_files},
    }
    audit: dict[str, Any] = {
        "audit_version": "pferi_v2_final_adjudicated_outcome_audit_v1",
        "created_at_utc": utc_now(),
        "status": "PASS",
        "formal_outcome_use_authorized": True,
        "model_analysis_authorized": True,
        "collection_interface_requirement": "nonbinding",
        "time_fields_used": False,
        "first_pass_response_count": len(first_pass_responses),
        "formal_pair_count": len(final_rows),
        "exact_three_category_disagreement_count": len(disagreements),
        "adjudication_response_count": len(adjudication_responses),
        "final_label_counts": label_counts,
        "stage_final_label_counts": stage_counts,
        "source_sha256": source_hashes,
        "acceptance_basis": "Study owner accepts the returned CSV decisions as independent human judgements. Use of the supplied Streamlit application is not an outcome-admission condition.",
    }
    disposition = {
        "disposition_version": "pferi_v2_adjudication_acceptance_disposition_v1",
        "created_at_utc": utc_now(),
        "status": "PASS_OWNER_ACCEPTED_HUMAN_ADJUDICATION",
        "formal_outcome_use_authorized": True,
        "model_analysis_authorized": True,
        "collection_interface_requirement": "nonbinding",
        "accepted_fields": ["review_decision", "reason_codes", "confidence"],
        "excluded_fields": ["submitted_at_utc"],
        "study_owner_declarations": {
            "responses_are_independent_human_judgements": True,
            "adjudicators_are_real_people": True,
            "adjudicators_did_not_see_first_pass_answers": True,
            "no_ai_or_automated_labelling": True,
            "no_label_or_confidence_quota": True,
            "no_hidden_model_or_identity_information": True,
            "returned_csv_files_are_the_outcome_records": True,
        },
        "historical_candidate_status_rule": "Candidate-build release flags describe the earlier packaging state and do not invalidate the study-owner-accepted human CSV outcomes.",
        "claim_boundary": "The accepted endpoint is human reviewability, not identity accuracy. Model success still requires the frozen development, calibration, and deployment-confirmation analyses.",
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output_dir.name + ".staging.", dir=output_dir.parent))
    try:
        write_csv(staging / "final_adjudicated_outcomes.csv", FINAL_OUTCOME_COLUMNS, final_rows)
        (staging / "final_outcome_audit.json").write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (staging / "adjudication_acceptance_disposition.json").write_text(
            json.dumps(disposition, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        checksums = [
            f"{sha256_file(path)}  {path.relative_to(staging)}"
            for path in sorted(staging.rglob("*"))
            if path.is_file() and path.name != "CHECKSUMS.sha256"
        ]
        (staging / "CHECKSUMS.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
        os.replace(staging, output_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assignment", type=Path, required=True)
    parser.add_argument("--first-pass", type=Path, required=True)
    parser.add_argument("--linkage", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--sampling", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    audit = finalize(
        assignment=args.assignment,
        first_pass=args.first_pass,
        linkage=args.linkage,
        adjudication=args.adjudication,
        sampling=args.sampling,
        output_dir=args.output_dir,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
