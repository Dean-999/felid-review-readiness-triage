#!/usr/bin/env python3
"""Freeze a Task15J-compatible, outcome-free Task15K calibration candidate set."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
OUTPUT = MODEL_ROOT / "2026-07-27_task15k_independent_calibration_design_freeze_v1"
CONTRACT_PATH = ROOT / "schemas/pferi_v2/task15k_independent_calibration_contract_v1.json"
TASK15J = ROOT / "outputs/pferi_v2/models/development"
TASK15I_PREPAIR = MODEL_ROOT / "2026-07-26_task15i_prepair_artifacts_v1"
IMAGE_MANIFEST = ROOT / "data/candidate-reservoirs/task15i_independent_lynx_v1/eligible_unique_image_manifest.csv"
LEGACY_ROOT = ROOT / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1"

PAIR_COLUMNS = [
    "canonical_pair_id", "component_id", "formal_sampling_stage",
    "endpoint_a_image_id", "endpoint_b_image_id", "descriptor_support_category",
    "best_rank_band", "megadescriptor_rank_a_to_b", "megadescriptor_rank_b_to_a",
    "dinov2_rank_a_to_b", "dinov2_rank_b_to_a", "selection_evidence_state",
]
IMAGE_COLUMNS = ["candidate_image_id", "content_sha256", "local_relative_path", "image_filename"]
QUALITY_REFERENCE_COLUMNS = [
    "candidate_image_id", "content_sha256", "endpoint_native_pixel_quality_percentile",
    "endpoint_sharpness_quality_percentile", "endpoint_exposure_quality_percentile",
]


@dataclass(frozen=True)
class Edge:
    left: str
    right: str
    rank_sum: int
    rank_max: int
    strict_reciprocal: bool
    mega_a_to_b: int | None
    mega_b_to_a: int | None
    dino_a_to_b: int | None
    dino_b_to_a: int | None

    def key(self) -> tuple[int, int, int, str, str]:
        return (0 if self.strict_reciprocal else 1, self.rank_sum, self.rank_max, self.left, self.right)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def verify_checksum_manifest(directory: Path) -> list[str]:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        return ["missing:CHECKSUMS.sha256"]
    declared, failures = set(), []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        target = directory / relative
        declared.add(relative)
        if not target.is_file() or sha256(target) != expected:
            failures.append(relative)
    actual = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and path.name not in {"CHECKSUMS.sha256", ".DS_Store"}
    }
    if actual != declared:
        failures.append("inventory")
    return failures


def load_edges() -> list[Edge]:
    descriptor_root = TASK15I_PREPAIR / "descriptor_results"
    with (descriptor_root / "megadescriptor_l_384/pair_scores.csv").open(encoding="utf-8", newline="") as handle:
        mega = {(row["query_image_id"], row["candidate_image_id"]): int(row["candidate_rank"])
                for row in csv.DictReader(handle)}
    with (descriptor_root / "dinov2_vitl14/scores.csv").open(encoding="utf-8", newline="") as handle:
        dino = {(row["query_image_id"], row["candidate_image_id"]): int(row["candidate_rank"])
                for row in csv.DictReader(handle)}
    grouped: dict[tuple[str, str], dict[str, int | None]] = {}
    for left, right in set(mega).intersection(dino):
        a, b = sorted((left, right))
        record = grouped.setdefault((a, b), {"mega_a_to_b": None, "mega_b_to_a": None, "dino_a_to_b": None, "dino_b_to_a": None})
        direction = "a_to_b" if left == a else "b_to_a"
        record[f"mega_{direction}"] = mega[left, right]
        record[f"dino_{direction}"] = dino[left, right]
    edges = []
    for (left, right), record in grouped.items():
        ranks = [value for value in record.values() if value is not None]
        reciprocal = all(record[f"{model}_{direction}"] is not None for model in ("mega", "dino") for direction in ("a_to_b", "b_to_a"))
        edges.append(Edge(left, right, sum(ranks), max(ranks), reciprocal, record["mega_a_to_b"], record["mega_b_to_a"], record["dino_a_to_b"], record["dino_b_to_a"]))
    return sorted(edges, key=Edge.key)


def grow_components(pool: list[Edge], initially_used: set[str], target: int, seed: int) -> list[list[Edge]]:
    rng = random.Random(seed)
    adjacency: dict[str, list[Edge]] = defaultdict(list)
    for edge in pool:
        adjacency[edge.left].append(edge); adjacency[edge.right].append(edge)
    for values in adjacency.values():
        values.sort(key=Edge.key)
    seeds = list(pool); rng.shuffle(seeds)
    used, components = set(initially_used), []
    for seed_edge in seeds:
        if len(components) >= target or seed_edge.left in used or seed_edge.right in used:
            continue
        nodes, component = {seed_edge.left, seed_edge.right}, [seed_edge]
        while len(component) < 4:
            candidates: set[Edge] = set()
            for node in nodes:
                for edge in adjacency[node]:
                    other = edge.right if edge.left == node else edge.left
                    if other not in used and other not in nodes:
                        candidates.add(edge)
            if not candidates:
                break
            ordered = sorted(candidates, key=Edge.key)
            edge = ordered[rng.randrange(min(10, len(ordered)))]
            nodes.add(edge.right if edge.left in nodes else edge.left)
            component.append(edge)
        if len(component) == 4:
            used.update(nodes); components.append(component)
    return components


def select_components(edges: list[Edge], development_endpoints: set[str], component_target: int, seed: int) -> list[list[Edge]]:
    # Edge ordering prioritizes reciprocal evidence, but component growth uses the
    # complete consensus pool. A strict-only first stage exhausts scarce endpoints
    # and cannot reach the frozen 112-component target.
    return grow_components(edges, development_endpoints, component_target, seed)


def rank_band(edge: Edge) -> str:
    return "top_5" if edge.rank_max <= 5 else "top_10" if edge.rank_max <= 10 else "top_20"


def validate_sources(contract: dict[str, Any]) -> dict[str, Any]:
    record = json.loads((TASK15J / "development_model_freeze_record_v2.json").read_text(encoding="utf-8"))
    bundle = json.loads((TASK15J / "final_model_bundle.json").read_text(encoding="utf-8"))
    failures = {"task15j": verify_checksum_manifest(TASK15J), "task15i_prepair": verify_checksum_manifest(TASK15I_PREPAIR)}
    failures = {name: values for name, values in failures.items() if values}
    if record.get("status") != contract["upstream_model_requirement"]["development_freeze_status"] or not record.get("calibration_authorized"):
        raise RuntimeError("Task15J does not authorize calibration")
    if record.get("confirmation_authorized") is not False or bundle.get("fixed_lambda") != 100.0:
        raise RuntimeError("Task15J model bundle has unexpected authorization or lambda")
    category_spec = next(spec for spec in bundle["P3_preprocessor"]["categorical"] if spec["column"] == "descriptor_support_category")
    supported = set(category_spec["observed_levels"])
    if supported != set(contract["independent_candidate_design"]["descriptor_categories"]):
        raise RuntimeError(f"unexpected frozen descriptor taxonomy: {supported}")
    if failures:
        raise RuntimeError(f"source checksum failures: {failures}")
    return {"record": record, "bundle": bundle, "supported_categories": sorted(supported)}


def legacy_compatibility_audit(supported_categories: set[str]) -> dict[str, Any]:
    legacy = pd.read_csv(LEGACY_ROOT / "outcome_free_locked_features/calibration_features.csv", dtype=str)
    category_counts = dict(sorted(legacy["descriptor_support_category"].value_counts().items()))
    legacy_categories = set(category_counts)
    return {
        "status": "INCOMPATIBLE_DESCRIPTOR_TAXONOMY",
        "legacy_pair_count": int(len(legacy)),
        "legacy_endpoint_count": int(len(set(legacy.endpoint_a_image_id) | set(legacy.endpoint_b_image_id))),
        "legacy_descriptor_categories": sorted(legacy_categories),
        "task15j_supported_descriptor_categories": sorted(supported_categories),
        "unsupported_legacy_categories": sorted(legacy_categories - supported_categories),
        "all_legacy_categories_would_be_unknown_under_frozen_P3": legacy_categories.isdisjoint(supported_categories),
        "calibration_outcomes_accessed": False,
        "disposition": "Do not use the legacy 445-pair calibration labels with Task15J. The legacy category both must not be post-hoc mapped to both_agreement or both_reciprocal.",
    }


def build_selected_rows(components: list[list[Edge]]) -> list[dict[str, Any]]:
    rows = []
    for component_index, component in enumerate(components, start=1):
        for edge_index, edge in enumerate(component, start=1):
            raw = f"task15k|{component_index}|{edge_index}|{edge.left}|{edge.right}".encode("utf-8")
            rows.append({
                "canonical_pair_id": "task15k_calibration_pair_" + hashlib.sha256(raw).hexdigest()[:20],
                "component_id": f"task15k_calibration_component_{component_index:03d}",
                "formal_sampling_stage": "calibration", "endpoint_a_image_id": edge.left, "endpoint_b_image_id": edge.right,
                "descriptor_support_category": "both_reciprocal" if edge.strict_reciprocal else "both_agreement",
                "best_rank_band": rank_band(edge),
                "megadescriptor_rank_a_to_b": "" if edge.mega_a_to_b is None else edge.mega_a_to_b,
                "megadescriptor_rank_b_to_a": "" if edge.mega_b_to_a is None else edge.mega_b_to_a,
                "dinov2_rank_a_to_b": "" if edge.dino_a_to_b is None else edge.dino_a_to_b,
                "dinov2_rank_b_to_a": "" if edge.dino_b_to_a is None else edge.dino_b_to_a,
                "selection_evidence_state": "outcome_unopened",
            })
    return rows


def quality_reference(selected_ids: set[str], manifest: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    quality = pd.read_csv(TASK15I_PREPAIR / "prelabel_inputs/automatic_quality_measurements.csv")
    if len(quality) != 4108 or set(quality.candidate_image_id) != set(manifest):
        raise RuntimeError("Task15I quality reference inventory mismatch")
    if set(quality.failure_code) != {"none"}:
        raise RuntimeError("Task15I quality reference contains failures")
    result = quality.set_index("candidate_image_id")
    rows = []
    for identifier in sorted(selected_ids):
        rows.append({
            "candidate_image_id": identifier, "content_sha256": manifest[identifier]["sha256"],
            "endpoint_native_pixel_quality_percentile": f"{result['native_pixel_count'].rank(pct=True, method='average')[identifier]:.12f}",
            "endpoint_sharpness_quality_percentile": f"{result['sharpness_measure'].rank(pct=True, method='average')[identifier]:.12f}",
            "endpoint_exposure_quality_percentile": f"{result['exposure_clipping_fraction'].rank(pct=True, method='average')[identifier]:.12f}",
        })
    return rows


def validate_graph(rows: list[dict[str, Any]], target: int) -> dict[str, int]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    per_component: Counter[str] = Counter()
    for row in rows:
        left, right = row["endpoint_a_image_id"], row["endpoint_b_image_id"]
        if left == right or right in adjacency[left]:
            raise RuntimeError("invalid Task15K selected graph")
        adjacency[left].add(right); adjacency[right].add(left); per_component[row["component_id"]] += 1
    if len(rows) != target * 4 or len(per_component) != target or set(per_component.values()) != {4}:
        raise RuntimeError("Task15K component geometry mismatch")
    return {"pair_count": len(rows), "component_count": len(per_component), "selected_image_count": len(adjacency), "maximum_endpoint_degree": max(map(len, adjacency.values()))}


def report_text(audit: dict[str, Any]) -> str:
    return f"""# Task15K Independent Calibration Design Freeze

Status: **PASS - OUTCOME-FREE COMPATIBLE CALIBRATION CANDIDATE FROZEN**

Task15J froze P5 as the full primary model and P3 as its active control, authorizing calibration but not confirmation. Task15K first audited the historical 445-pair calibration feature set without opening any label. Its descriptor categories do not exist in the Task15J preprocessor taxonomy, so that route is permanently recorded as `{audit['legacy_calibration']['status']}` for this model bundle.

The replacement candidate uses only unused endpoints from the independent Task15I Eurasian-lynx reservoir. Fixed seed `{audit['selection_seed']}` selected {audit['selected_graph']['pair_count']} pairs in {audit['selected_graph']['component_count']} independent four-edge components, spanning {audit['selected_graph']['selected_image_count']} images. No selected endpoint overlaps the 1,600-pair Task15I development set. All selected descriptor categories are within the frozen P3/P5 taxonomy.

The accompanying ModelScope control package must verify the selected image hashes, remeasure quality and local-match coverage with the frozen Task15I methods, and emit uncalibrated P3/P5 raw probabilities. It contains no outcome labels. No calibration label may be accessed until the scoring inputs, calibration analysis contract, reviewer assignments, and blinded review packages are separately frozen.

Calibration may estimate only a logistic intercept and slope on each frozen model's raw logit probability. P3/P5 features, preprocessing, coefficients, lambda, and selection are immutable. Deployment and mechanism confirmation remain locked.
"""


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    evidence = validate_sources(contract)
    legacy = legacy_compatibility_audit(set(evidence["supported_categories"]))
    with IMAGE_MANIFEST.open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    manifest = {row["candidate_image_id"]: row for row in manifest_rows}
    development = pd.read_csv(TASK15I_PREPAIR / "prelabel_inputs/candidate_pairs.csv", dtype=str)
    development_endpoints = set(development.endpoint_a_candidate_image_id) | set(development.endpoint_b_candidate_image_id)
    components = select_components(load_edges(), development_endpoints, contract["independent_candidate_design"]["component_count"], contract["independent_candidate_design"]["selection_seed"])
    if len(components) != contract["independent_candidate_design"]["component_count"]:
        raise RuntimeError(f"fixed seed did not reach target: {len(components)} components")
    rows = build_selected_rows(components)
    graph = validate_graph(rows, contract["independent_candidate_design"]["component_count"])
    selected_ids = {row["endpoint_a_image_id"] for row in rows} | {row["endpoint_b_image_id"] for row in rows}
    if selected_ids & development_endpoints:
        raise RuntimeError("Task15K endpoint overlap with Task15I development")
    if not set(row["descriptor_support_category"] for row in rows).issubset(set(evidence["supported_categories"])):
        raise RuntimeError("selected descriptor category unsupported by frozen model")
    image_rows = [{"candidate_image_id": item, "content_sha256": manifest[item]["sha256"], "local_relative_path": manifest[item]["local_relative_path"], "image_filename": Path(manifest[item]["local_relative_path"]).name} for item in sorted(selected_ids)]
    references = quality_reference(selected_ids, manifest)
    source_hashes = {
        "task15j_record": sha256(TASK15J / "development_model_freeze_record_v2.json"),
        "task15j_bundle": sha256(TASK15J / "final_model_bundle.json"),
        "task15i_candidate_pairs": sha256(TASK15I_PREPAIR / "prelabel_inputs/candidate_pairs.csv"),
        "task15i_quality_reference": sha256(TASK15I_PREPAIR / "prelabel_inputs/automatic_quality_measurements.csv"),
        "independent_image_manifest": sha256(IMAGE_MANIFEST),
        "legacy_calibration_features": sha256(LEGACY_ROOT / "outcome_free_locked_features/calibration_features.csv"),
    }
    audit = {
        "audit_version": "pferi_v2_task15k_independent_calibration_design_freeze_audit_v1", "status": "PASS", "frozen_at_utc": now(),
        "contract_sha256": sha256(CONTRACT_PATH), "task15j_model_bundle_sha256": source_hashes["task15j_bundle"],
        "legacy_calibration": legacy, "selection_seed": contract["independent_candidate_design"]["selection_seed"],
        "selection_algorithm": contract["independent_candidate_design"]["selection_algorithm"], "selected_graph": graph,
        "selected_descriptor_support_counts": dict(sorted(Counter(row["descriptor_support_category"] for row in rows).items())),
        "selected_rank_band_counts": dict(sorted(Counter(row["best_rank_band"] for row in rows).items())),
        "task15i_development_endpoint_count": len(development_endpoints), "task15k_task15i_development_endpoint_overlap_count": 0,
        "calibration_outcomes_accessed": False, "deployment_confirmation_outcomes_accessed": False, "mechanism_confirmation_outcomes_accessed": False,
        "source_hashes": source_hashes,
        "next_authorized_action": "Build and execute the Task15K hash-verified ModelScope measurement package; calibration labels remain unopened.",
        "claim_boundary": contract["claim_boundary"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name; stage.mkdir()
        write_csv(stage / "calibration_candidate_pairs.csv", rows, PAIR_COLUMNS)
        write_csv(stage / "selected_image_manifest.csv", image_rows, IMAGE_COLUMNS)
        write_csv(stage / "quality_reference_percentiles.csv", references, QUALITY_REFERENCE_COLUMNS)
        write_json(stage / "task15k_calibration_design_audit.json", audit)
        (stage / "TASK15K_INDEPENDENT_CALIBRATION_DESIGN_REPORT.md").write_text(report_text(audit), encoding="utf-8")
        shutil.copy2(Path(__file__), stage / "freeze_builder_snapshot.py")
        files = sorted(path for path in stage.iterdir() if path.is_file())
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(freeze(args.output), indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
