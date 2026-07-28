#!/usr/bin/env python3
"""Build the hash-bound PF-ERI v2 manuscript evidence manifest."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "schemas/pferi_v2/manuscript_source_manifest_contract_v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    def safe(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines.extend(
        "| " + " | ".join(safe(row.get(column, "")) for column in columns) + " |"
        for row in rows
    )
    return "\n".join(lines) + "\n"


def close(actual: float, expected: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance)


def semantic_failures(root: Path, paths: dict[str, Path]) -> list[str]:
    failures: list[str] = []
    task15i = read_json(paths["TASK15I_RESULT_FREEZE"])
    if task15i.get("source_analysis_status") != "PASS_TASK15I_DEVELOPMENT_SCREEN":
        failures.append("task15i_status")
    if task15i.get("pair_count") != 1600 or task15i.get("component_count") != 400:
        failures.append("task15i_inventory")
    if task15i.get("nonnegative_outer_fold_count") != 5:
        failures.append("task15i_fold_direction")
    if not close(float(task15i.get("p3_minus_p5_weighted_brier", math.nan)), 0.00586289868561593):
        failures.append("task15i_increment")

    task15j = read_json(paths["TASK15J_MODEL_FREEZE"])
    if task15j.get("status") != "QUALIFIED_P5_DEVELOPMENT_MODEL_FROZEN_CALIBRATION_AUTHORIZED":
        failures.append("task15j_status")
    if task15j.get("development_model_frozen") is not True or task15j.get("calibration_authorized") is not True:
        failures.append("task15j_freeze")

    task15l = read_json(paths["TASK15L_CALIBRATION_FREEZE"])
    if task15l.get("status") != "PASS" or task15l.get("calibratability", {}).get("total_pairs") != 448:
        failures.append("task15l_status_or_inventory")
    if task15l.get("calibration", {}).get("original_models_refit") is not False:
        failures.append("task15l_refit")

    task15m_contract = read_json(paths["TASK15M_CONFIRMATION_CONTRACT"])
    primary = task15m_contract.get("primary_confirmation_analysis", {})
    if primary.get("positive_direction") != "positive favors P5" or not close(float(primary.get("minimum_practical_increment", math.nan)), 0.005):
        failures.append("task15m_primary_rule")

    execution = read_json(paths["TASK15N_EXECUTION_FREEZE"])
    counts = execution.get("evidence", {})
    if execution.get("status") != "PASS_TASK15M_EXECUTION_VALIDATION":
        failures.append("task15n_status")
    if (counts.get("candidate_pair_count"), counts.get("supported_pair_count"), counts.get("unsupported_pair_count"), counts.get("prediction_count")) != (889, 252, 637, 504):
        failures.append("task15m_execution_inventory")

    descriptor_rows = read_csv(paths["TASK15M_DESCRIPTOR_PAIR_MEASUREMENTS"])
    if {row["support_status"] for row in descriptor_rows} != {"supported", "unsupported"}:
        failures.append("task15m_support_statuses")
    supported = [row for row in descriptor_rows if row["support_status"] == "supported"]
    if {row["descriptor_support_category"] for row in supported} != {"both_agreement", "both_reciprocal"}:
        failures.append("task15m_supported_taxonomy")
    unsupported = read_csv(paths["TASK15M_UNSUPPORTED_PAIRS"])
    if {row["unsupported_reason"] for row in unsupported} != {"no_same_direction_dual_descriptor_top20_consensus"}:
        failures.append("task15m_unsupported_reason")

    outcomes = read_csv(paths["FINAL_ADJUDICATED_OUTCOMES"])
    deployment = [row for row in outcomes if row["formal_sampling_stage"] == "deployment_confirmation"]
    if len(deployment) != 889:
        failures.append("deployment_outcome_inventory")
    if {row["not_ready_or_uncertain_label"] for row in deployment} != {"0", "1"}:
        failures.append("deployment_outcome_labels")

    outcome_audit = read_json(paths["FINAL_OUTCOME_AUDIT"])
    if outcome_audit.get("status") != "PASS" or outcome_audit.get("model_analysis_authorized") is not True:
        failures.append("final_outcome_audit")

    authorship = read_json(paths["HUMAN_AUTHORSHIP_DISPOSITION"])
    if authorship.get("status") != "PASS_HUMAN_AUTHORSHIP_ATTESTED_WITH_MAJOR_PROTOCOL_DEVIATION":
        failures.append("human_authorship_status")
    if authorship.get("formal_confirmatory_claim_authorized") is not False:
        failures.append("human_authorship_claim_boundary")

    confirmation = read_json(paths["PRIMARY_CONFIRMATION_RESULT"])
    if confirmation.get("status") != "FAIL_PRIMARY_CONFIRMATION":
        failures.append("primary_confirmation_status")
    sample = confirmation.get("sample", {})
    if (sample.get("supported_pair_count"), sample.get("unsupported_pair_count")) != (252, 637):
        failures.append("primary_confirmation_inventory")
    estimand = confirmation.get("estimand", {})
    interval = confirmation.get("interval", {})
    if not close(float(estimand.get("point_estimate", math.nan)), -0.20186978157257945):
        failures.append("primary_confirmation_estimate")
    if not close(float(interval.get("lower_95", math.nan)), -0.22467140021941134) or not close(float(interval.get("upper_95", math.nan)), -0.17906816292574756):
        failures.append("primary_confirmation_interval")

    closure = read_json(paths["PROJECT_CLOSURE_RECORD"])
    if closure.get("status") != "CONFIRMED" or closure.get("project_status") != "CLOSED":
        failures.append("project_closure_status")
    if closure.get("confirmation_scope") != "TASK15M_EXECUTION_VALIDATION":
        failures.append("project_closure_scope")
    return failures


def build(
    root: Path = ROOT,
    contract_path: Path = CONTRACT,
    output_directory: Optional[Path] = None,
) -> dict[str, Any]:
    contract = read_json(contract_path)
    output = output_directory or root / contract["output_directory"]
    source_rows: list[dict[str, Any]] = []
    failures: list[str] = []
    paths: dict[str, Path] = {}
    source_ids = [spec["source_id"] for spec in contract["sources"]]
    claim_ids = [claim["claim_id"] for claim in contract["claims"]]
    if len(source_ids) != len(set(source_ids)):
        failures.append("duplicate_source_id")
    if len(claim_ids) != len(set(claim_ids)):
        failures.append("duplicate_claim_id")
    unknown_evidence = sorted(
        {
            evidence_id
            for claim in contract["claims"]
            for evidence_id in claim["evidence_ids"]
            if evidence_id not in set(source_ids)
        }
    )
    failures.extend(f"unknown_evidence_id:{evidence_id}" for evidence_id in unknown_evidence)
    for spec in contract["sources"]:
        path = root / spec["path"]
        paths[spec["source_id"]] = path
        exists = path.is_file()
        observed_hash = sha256(path) if exists else ""
        data_rows = len(read_csv(path)) if exists and spec["file_type"] == "csv" else ""
        expected_rows = spec.get("expected_data_row_count", "")
        hash_match = exists and observed_hash == spec["expected_sha256"]
        row_match = expected_rows == "" or data_rows == expected_rows
        if not exists:
            failures.append(f"missing:{spec['source_id']}")
        elif not hash_match:
            failures.append(f"sha256:{spec['source_id']}")
        if exists and not row_match:
            failures.append(f"row_count:{spec['source_id']}")
        source_rows.append(
            {
                "source_id": spec["source_id"],
                "stage": spec["stage"],
                "scientific_role": spec["scientific_role"],
                "source_path": spec["path"],
                "file_type": spec["file_type"],
                "access_class": spec["access_class"],
                "exists": str(exists).lower(),
                "size_bytes": path.stat().st_size if exists else "",
                "sha256": observed_hash,
                "expected_sha256": spec["expected_sha256"],
                "hash_match": str(hash_match).lower(),
                "data_row_count": data_rows,
                "expected_data_row_count": expected_rows,
                "row_count_match": str(row_match).lower(),
            }
        )
    if not failures:
        failures.extend(semantic_failures(root, paths))
    if failures:
        raise RuntimeError("manuscript source manifest validation failed: " + "; ".join(failures))

    claim_rows = [
        {
            "claim_id": claim["claim_id"],
            "manuscript_sections": claim["manuscript_sections"],
            "statement": claim["statement"],
            "evidence_ids": "; ".join(claim["evidence_ids"]),
            "disposition": claim["disposition"],
            "interpretation_boundary": claim["interpretation_boundary"],
        }
        for claim in contract["claims"]
    ]
    source_columns = list(source_rows[0])
    claim_columns = list(claim_rows[0])
    audit = {
        "audit_version": "pferi_v2_manuscript_source_manifest_audit_v1",
        "status": "PASS",
        "contract_sha256": sha256(contract_path),
        "source_count": len(source_rows),
        "claim_count": len(claim_rows),
        "all_sources_exist": True,
        "all_source_hashes_match": True,
        "all_declared_row_counts_match": True,
        "semantic_validation_passed": True,
        "failures": [],
        "claim_boundary": "This package maps frozen evidence to manuscript claims. It does not change any scientific result or authorize a broader claim.",
    }
    readme = """# PF-ERI v2 manuscript source-data manifest

This directory is the paper-facing evidence map for the new PF-ERI v2 manuscript. It is separate from the historical v1 source-data package in the parent directory.

`evidence_source_manifest.csv` and `.md` bind each manuscript evidence source to its path, SHA-256, file size, row count where applicable, scientific role, stage, and access class. `claim_evidence_map.csv` and `.md` map every planned manuscript claim to its supporting evidence and interpretation boundary. `source_manifest_audit.json` records fail-closed validation of hashes, declared row counts, and the principal cross-stage scientific invariants. `CHECKSUMS.sha256` covers the generated package.

Regenerate with `python3 scripts/build_pferi_v2_manuscript_source_manifest.py`. The command refuses to write a passing package when a frozen source is missing, changed, row-count inconsistent, or semantically inconsistent with the declared Task15I-through-closure evidence chain.
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".pferi_v2_source_manifest.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_csv(stage / "evidence_source_manifest.csv", source_rows, source_columns)
        (stage / "evidence_source_manifest.md").write_text(markdown_table(source_rows, source_columns), encoding="utf-8")
        write_csv(stage / "claim_evidence_map.csv", claim_rows, claim_columns)
        (stage / "claim_evidence_map.md").write_text(markdown_table(claim_rows, claim_columns), encoding="utf-8")
        write_json(stage / "source_manifest_audit.json", audit)
        (stage / "README.md").write_text(readme, encoding="utf-8")
        generated = sorted(path for path in stage.iterdir() if path.is_file())
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in generated),
            encoding="utf-8",
        )
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(stage), str(output))
    return audit


def main() -> int:
    try:
        print(json.dumps(build(), indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error), "error_type": type(error).__name__}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
