#!/usr/bin/env python3
"""Freeze the Task 15I 400-component, 1,600-pair prelabel contract and folds."""
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

from scripts import build_pferi_v2_component_disjoint_folds as fold_builder
PREPAIR = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_prepair_artifacts_v1"
CAPACITY = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_independent_redevelopment_capacity_audit/current/capacity_audit.json"
CONDITIONAL = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_conditional_90pct_feasibility_analysis_v1/conditional_90pct_feasibility_record.json"
CONTRACT = ROOT / "schemas/pferi_v2/task15i_90pct_prepair_contract_v1.json"
REGISTRY = ROOT / "schemas/pferi_v2/task15i_90pct_component_fold_design_v1.json"
OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_90pct_prepair_contract_freeze_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader(); writer.writerows(rows)


def load_verified_inputs() -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    capacity = json.loads(CAPACITY.read_text(encoding="utf-8"))
    prepair = json.loads((PREPAIR / "prepair_artifact_audit.json").read_text(encoding="utf-8"))
    conditional = json.loads(CONDITIONAL.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if capacity.get("status") != "READY_FOR_PRELABEL_AMENDMENT" or not capacity.get("prelabel_contract_amendment_authorized"):
        raise ValueError("capacity audit does not authorize the prelabel amendment")
    graph = capacity.get("pair_graph_audit", {})
    required = {"unique_valid_pair_count": 1600, "component_count": 400, "maximum_component_pair_count": 4}
    if any(graph.get(key) != value for key, value in required.items()) or graph.get("maximum_endpoint_degree", 99) > 6:
        raise ValueError("capacity audit is inconsistent with the 90-percent prelabel design")
    screen = conditional.get("recommended_90pct_screen_design", {})
    if conditional.get("status") != "FROZEN_CONDITIONAL_90PCT_FEASIBILITY_ANALYSIS" or screen.get("component_count") != 400 or screen.get("analyzable_pair_count") != 1600:
        raise ValueError("conditional feasibility record does not support the frozen design")
    if prepair.get("status") != "PASS" or prepair.get("outcome_accessed") is not False:
        raise ValueError("prepair source was not a passing outcome-free artifact")
    with (PREPAIR / "prelabel_inputs/candidate_pairs.csv").open(newline="", encoding="utf-8") as handle:
        pairs = list(csv.DictReader(handle))
    if len(pairs) != 1600 or any("outcome" in key.lower() or "label" in key.lower() for key in pairs[0]):
        raise ValueError("candidate input violates prelabel boundary")
    return pairs, capacity, conditional, contract


def build_fold_inputs(pairs: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    master, formal = [], []
    for row in pairs:
        pair_id = row["candidate_pair_id"]
        master.append({
            "canonical_pair_id": pair_id,
            "pair_execution_id": pair_id,
            "analytical_role": "development",
            "endpoint_a_image_id": row["endpoint_a_candidate_image_id"],
            "endpoint_b_image_id": row["endpoint_b_candidate_image_id"],
            "development_sampling_cell_id": "__".join([row["descriptor_support_category"], row["best_rank_band"], row["development_evidence_state"], row["endpoint_quality_measurement_failure"], row["local_match_measurement_failure"]]),
            "descriptor_support_category": row["descriptor_support_category"],
            "development_evidence_state": row["development_evidence_state"],
            "best_rank_band": row["best_rank_band"],
            "local_match_measurement_failure": row["local_match_measurement_failure"],
            "endpoint_quality_measurement_failure": row["endpoint_quality_measurement_failure"],
        })
        formal.append({"formal_sampling_stage": "development", "canonical_pair_id": pair_id, "pair_execution_id": pair_id, "source_analytical_role": "development", "first_order_inclusion_probability": "1.0"})
    return master, formal


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    pairs, capacity, conditional, contract = load_verified_inputs()
    master, formal = build_fold_inputs(pairs)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name; stage.mkdir()
        inputs = stage / "prelabel_execution_inputs"; inputs.mkdir()
        master_columns = list(master[0]); formal_columns = list(formal[0])
        write_csv(inputs / "outcome_free_development_master.csv", master, master_columns)
        write_csv(inputs / "outcome_free_formal_development_manifest.csv", formal, formal_columns)
        shutil.copy2(CONTRACT, stage / "task15i_90pct_prepair_contract_frozen.json")
        shutil.copy2(REGISTRY, stage / "task15i_90pct_fold_registry_frozen.json")
        fold_audit = fold_builder.run(inputs / "outcome_free_development_master.csv", inputs / "outcome_free_formal_development_manifest.csv", REGISTRY, stage / "component_disjoint_folds", expected_rows=1600)
        if fold_audit["status"] != "PASS" or fold_audit["endpoint_leakage_count"] != 0 or fold_audit["component_count"] != 400:
            raise RuntimeError("component-disjoint fold freeze failed")
        record = {
            "record_version": "pferi_v2_task15i_90pct_prepair_contract_freeze_v1",
            "status": "FROZEN_PRELABEL_90PCT_REDEVELOPMENT_EXECUTION",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "design": contract["design"],
            "conditional_operating_characteristic": contract["conditional_operating_characteristic"],
            "model_rules": contract["model_rules"],
            "outcomes_accessed": False,
            "identity_labels_accessed": False,
            "calibration_authorized": False,
            "confirmation_authorized": False,
            "new_outcome_collection_authorized_by_this_freeze": False,
            "next_authorized_action": "Prepare a separately governed blinded new-development outcome collection package using the frozen 1600-pair execution manifest and folds.",
            "source_hashes": {"capacity_audit": sha256(CAPACITY), "prepair_artifact_audit": sha256(PREPAIR / "prepair_artifact_audit.json"), "conditional_feasibility_record": sha256(CONDITIONAL), "contract": sha256(CONTRACT), "fold_registry": sha256(REGISTRY)},
            "fold_audit_sha256": sha256(stage / "component_disjoint_folds/fold_validation_audit.json"),
            "claim_boundary": contract["claim_boundary"],
        }
        write_json(stage / "prelabel_contract_freeze_record.json", record)
        write_json(stage / "prelabel_contract_freeze_audit.json", {"status": "PASS", "outcomes_accessed": False, "identity_labels_accessed": False, "capacity_status": capacity["status"], "fold_status": fold_audit["status"], "fold_component_count": fold_audit["component_count"], "fold_endpoint_leakage_count": fold_audit["endpoint_leakage_count"], "conditional_success_probability": conditional["recommended_90pct_screen_design"]["point_threshold_success_probability"], "conditional_not_actual_pass_probability": True})
        (stage / "TASK15I_90PCT_PRELABEL_CONTRACT_REPORT.md").write_text(
            "# Task 15I 90% Conditional Prelabel Contract Freeze\n\n"
            "Status: `FROZEN_PRELABEL_90PCT_REDEVELOPMENT_EXECUTION`\n\n"
            "The frozen outcome-free execution frame contains 1,600 pairs in 400 endpoint-disjoint components and five component-disjoint outer folds. Lambda 100 is fixed for P3 and P5. No outcome or identity label was read. The 92.8% figure is conditional on the registered synthetic operating-characteristic assumptions; it is not a correctness estimate or an actual model-pass probability.\n",
            encoding="utf-8",
        )
        shutil.copy2(Path(__file__), stage / "contract_freeze_builder_snapshot.py")
        files = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return record


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2, sort_keys=True))
