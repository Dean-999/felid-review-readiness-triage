#!/usr/bin/env python3
"""Freeze Task15M's outcome-free external confirmation measurement design."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
FORMAL = ROOT / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1/restricted_formal_pair_sampling_manifest.csv"
PUBLIC = ROOT / "work/pferi_v2/gpu/local_match/pilot/public_pair_manifests"
IMAGE_ROOT = ROOT / "data/frozen/pferi_v2/lynx-wild/images"
IMAGE_MANIFEST = ROOT / "data/frozen/pferi_v2/lynx-wild/manifest.csv"
TASK15I = MODEL_ROOT / "2026-07-26_task15i_prepair_artifacts_v1/prelabel_inputs/candidate_pairs.csv"
TASK15K = MODEL_ROOT / "2026-07-27_task15k_independent_calibration_design_freeze_v1"
TASK15J = ROOT / "outputs/pferi_v2/models/development"
TASK15L = ROOT / "outputs/pferi_v2/models/calibration/analysis"
CONTRACT = ROOT / "schemas/pferi_v2/task15m_independent_confirmation_contract_v1.json"
OUTPUT = MODEL_ROOT / "2026-07-27_task15m_independent_confirmation_design_freeze_v1"

PAIR_COLUMNS = [
    "canonical_pair_id", "component_id", "formal_sampling_stage", "endpoint_a_image_id", "endpoint_b_image_id",
    "descriptor_support_category", "best_rank_band", "selection_evidence_state",
]
IMAGE_COLUMNS = ["candidate_image_id", "content_sha256", "local_relative_path", "image_filename"]
LINKAGE_COLUMNS = ["task15m_confirmation_pair_id", "historical_canonical_pair_id", "historical_pair_execution_id"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def write_checksums(directory: Path) -> None:
    files = sorted(path for path in directory.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (directory / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(directory)}\n" for path in files), encoding="utf-8"
    )


def connected_components(rows: list[dict[str, str]]) -> dict[str, int]:
    parent: dict[str, str] = {}
    def find(node: str) -> str:
        parent.setdefault(node, node)
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]
    def union(left: str, right: str) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left
    for row in rows:
        union(row["left_asset_filename"], row["right_asset_filename"])
    roots = sorted({find(node) for node in parent})
    index = {root: position for position, root in enumerate(roots, start=1)}
    return {node: index[find(node)] for node in parent}


def load_source_rows() -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    formal = pd.read_csv(FORMAL, dtype=str)
    chosen = formal.loc[formal["formal_sampling_stage"].eq("deployment_confirmation")]
    if len(chosen) != 889 or chosen["pair_execution_id"].nunique() != 889:
        raise RuntimeError("unexpected historical confirmation pair inventory")
    public: dict[str, dict[str, str]] = {}
    for path in sorted(PUBLIC.glob("confirmation_shard_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                public[row["pair_execution_id"]] = row
    rows = []
    for item in chosen.to_dict("records"):
        visible = public.get(item["pair_execution_id"])
        if visible is None:
            raise RuntimeError("historical confirmation pair missing public image mapping")
        rows.append({**item, **visible})
    manifest = pd.read_csv(IMAGE_MANIFEST, dtype=str)
    lookup: dict[str, dict[str, str]] = {}
    for row in manifest.to_dict("records"):
        # Historical pair manifests reference final-freeze names, while the
        # manifest preserves an earlier frozen_file_name for some images.
        filename = Path(row["final_freeze_image_path"]).name
        if filename in lookup:
            raise RuntimeError(f"ambiguous final-freeze image mapping: {filename}")
        lookup[filename] = row
    return rows, lookup


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    task15j = json.loads((TASK15J / "development_model_freeze_record_v2.json").read_text(encoding="utf-8"))
    task15l = json.loads((TASK15L / "task15l_calibration_analysis_freeze_record.json").read_text(encoding="utf-8"))
    if task15j.get("status") != contract["upstream_requirements"]["task15j_status"] or task15l.get("status") != "PASS":
        raise RuntimeError("required Task15J/Task15L freeze status not present")
    source_rows, image_lookup = load_source_rows()
    components = connected_components(source_rows)
    images: dict[str, dict[str, str]] = {}
    pairs, linkage = [], []
    for source in source_rows:
        endpoints = []
        for filename in (source["left_asset_filename"], source["right_asset_filename"]):
            item = image_lookup.get(filename)
            if item is None:
                raise RuntimeError(f"unmapped frozen confirmation image: {filename}")
            path = IMAGE_ROOT / filename
            if not path.is_file() or sha256(path) != item["final_freeze_sha256"]:
                raise RuntimeError(f"confirmation image unavailable or hash-mismatched: {filename}")
            image_id = "task15m_image_" + item["final_freeze_sha256"]
            images[image_id] = {"candidate_image_id": image_id, "content_sha256": item["final_freeze_sha256"], "local_relative_path": str(path.relative_to(ROOT)), "image_filename": filename}
            endpoints.append(image_id)
        raw = f"task15m|{source['pair_execution_id']}".encode("utf-8")
        pair_id = "task15m_confirmation_pair_" + hashlib.sha256(raw).hexdigest()[:20]
        pairs.append({"canonical_pair_id": pair_id, "component_id": f"task15m_confirmation_component_{components[source['left_asset_filename']]:03d}", "formal_sampling_stage": "deployment_confirmation", "endpoint_a_image_id": endpoints[0], "endpoint_b_image_id": endpoints[1], "descriptor_support_category": "PENDING_CURRENT_DESCRIPTOR_INFERENCE", "best_rank_band": "PENDING_CURRENT_DESCRIPTOR_INFERENCE", "selection_evidence_state": "outcome_unopened"})
        linkage.append({"task15m_confirmation_pair_id": pair_id, "historical_canonical_pair_id": source["canonical_pair_id"], "historical_pair_execution_id": source["pair_execution_id"]})
    if len(pairs) != 889 or len(images) != 815:
        raise RuntimeError("Task15M source coverage mismatch")
    development = pd.read_csv(TASK15I, dtype=str)
    calibration = pd.read_csv(TASK15K / "selected_image_manifest.csv", dtype=str)
    development_hashes = set()
    for image_id in set(development.endpoint_a_candidate_image_id) | set(development.endpoint_b_candidate_image_id):
        development_hashes.add(image_id.removeprefix("task15i_image_"))
    calibration_hashes = {item.removeprefix("task15i_image_") for item in calibration.candidate_image_id}
    confirmation_hashes = {row["content_sha256"] for row in images.values()}
    degree = Counter(endpoint for pair in pairs for endpoint in (pair["endpoint_a_image_id"], pair["endpoint_b_image_id"]))
    component_pairs = Counter(pair["component_id"] for pair in pairs)
    audit = {
        "audit_version": "pferi_v2_task15m_independent_confirmation_design_audit_v1",
        "status": "PASS_OUTCOME_FREE_CONFIRMATION_MEASUREMENT_DESIGN",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pair_count": len(pairs), "image_count": len(images), "component_count": len(component_pairs),
        "largest_component_pair_count": max(component_pairs.values()), "maximum_endpoint_degree": max(degree.values()),
        "task15i_development_content_hash_overlap_count": len(confirmation_hashes & development_hashes),
        "task15k_calibration_content_hash_overlap_count": len(confirmation_hashes & calibration_hashes),
        "confirmation_outcomes_accessed": False,
        "selected_pair_set_mutable_after_measurement": False,
        "task15l_calibration_parameters": {model: {key: task15l["calibration"][f"{model.lower()}_{key}"] for key in ("intercept", "slope")} for model in ("P3", "P5")},
        "next_authorized_action": "Build a hash-verified ModelScope package that remeasures the frozen 815 images and 889 pairs before any confirmation outcome is read.",
        "claim_boundary": contract["claim_boundary"],
    }
    if audit["task15i_development_content_hash_overlap_count"] or audit["task15k_calibration_content_hash_overlap_count"]:
        raise RuntimeError("Task15M endpoint overlap with development or calibration")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name; stage.mkdir(); (stage / "restricted").mkdir()
        write_csv(stage / "confirmation_candidate_pairs.csv", PAIR_COLUMNS, pairs)
        write_csv(stage / "selected_image_manifest.csv", IMAGE_COLUMNS, sorted(images.values(), key=lambda row: row["candidate_image_id"]))
        write_csv(stage / "restricted/legacy_confirmation_linkage.csv", LINKAGE_COLUMNS, linkage)
        write_json(stage / "task15m_confirmation_design_audit.json", audit)
        write_json(stage / "task15m_confirmation_contract.json", contract)
        (stage / "TASK15M_INDEPENDENT_CONFIRMATION_DESIGN_REPORT.md").write_text(
            "# Task15M Independent Confirmation Measurement Design\n\n"
            "Status: **PASS - OUTCOME-FREE DESIGN FROZEN**\n\n"
            f"The design retains {len(pairs)} historical deployment-confirmation pairs over {len(images)} available frozen full-frame images. "
            "It does not reuse old descriptor categories or old feature values. All images must be remeasured under the Task15I descriptor, quality, and local-match methods before the frozen Task15J P3/P5 models are scored and the Task15L calibration transform is applied.\n\n"
            f"The pair graph contains {len(component_pairs)} connected components, with a largest component of {max(component_pairs.values())} pairs and maximum endpoint degree {max(degree.values())}. The future primary interval is therefore the predeclared dyadic cluster-robust interval, not an independent-row interval. Confirmation outcomes remain unopened.\n",
            encoding="utf-8",
        )
        write_checksums(stage)
        shutil.move(str(stage), str(output))
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, default=OUTPUT); args = parser.parse_args()
    try:
        print(json.dumps(freeze(args.output), indent=2, sort_keys=True)); return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, sort_keys=True)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
