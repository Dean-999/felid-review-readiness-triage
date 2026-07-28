#!/usr/bin/env python3
"""Freeze Task 15I descriptor results and build outcome-free prelabel artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import shutil
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
IMAGE_MANIFEST = ROOT / "data/candidate-reservoirs/task15i_independent_lynx_v1/eligible_unique_image_manifest.csv"
DEFAULT_OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_prepair_artifacts_v1"
EXPECTED_CONTRACT_SHA = "dae19f93cb59ef940c6349a8980fe3253b54aa4b0daaa360de76ae384317d3ff"
EXPECTED_INPUT_SHA = "2769688dfd60b72171fcca3b2376054f423bf54cac99e8591f1e8c80f2ca42df"
EXPECTED_PACKAGE_SHA = "92d1424752b1c9b4c6886699e38f55544b183e1031cdf32dd92a7211214a77b6"
EXPORT_ROOT = "PF_ERI_TASK15I_DESCRIPTOR_FINAL_EXPORT/"
PAIR_COLUMNS = [
    "candidate_pair_id", "component_id", "endpoint_a_candidate_image_id",
    "endpoint_b_candidate_image_id", "descriptor_support_category", "best_rank_band",
    "development_evidence_state", "endpoint_quality_measurement_failure",
    "local_match_measurement_failure", "mega_rank_a_to_b", "mega_rank_b_to_a",
    "dinov2_rank_a_to_b", "dinov2_rank_b_to_a",
]
QUALITY_COLUMNS = [
    "candidate_image_id", "content_sha256", "image_decode_status", "native_pixel_count",
    "sharpness_measure", "exposure_clipping_fraction", "failure_code", "value_status",
]
LOCAL_COLUMNS = [
    "candidate_pair_id", "failure_code", "value_status", "local_match_coverage_fraction",
    "inlier_count", "source_keypoint_count", "target_keypoint_count", "runtime_seconds",
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def parse_declared_sha(path: Path) -> str:
    declared = path.read_text(encoding="utf-8").strip().split()[0]
    if len(declared) != 64 or any(char not in "0123456789abcdef" for char in declared):
        raise ValueError("invalid external SHA256 declaration")
    return declared


def verify_summary(path: Path, zip_hash: str) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    required = {
        "status": "COMPLETE", "verified_image_count": "4108",
        "megadescriptor_expected_shape": "4108x1536", "dinov2_expected_shape": "4108x1024",
        "expected_directed_candidates_per_descriptor": "82160",
        "locked_stage_outcomes_accessed": "false", "final_export_sha256": zip_hash,
    }
    mismatches = {key: values.get(key) for key, expected in required.items() if values.get(key) != expected}
    if mismatches:
        raise ValueError(f"external run summary mismatch: {mismatches}")
    return values


def archive_csv(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    with archive.open(member) as binary:
        return list(csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8", newline="")))


def validate_external_export(zip_path: Path, manifest: Path) -> dict[str, Any]:
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("external export is not a ZIP")
    reference = read_csv(manifest)
    expected_by_id = {row["candidate_image_id"]: row["sha256"] for row in reference}
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("external export ZIP CRC failure")
        required = {
            EXPORT_ROOT + "run_audit.json", EXPORT_ROOT + "validation_audit.json",
            EXPORT_ROOT + "megadescriptor_l_384/embedding_manifest_v2.csv",
            EXPORT_ROOT + "megadescriptor_l_384/pair_scores.csv",
            EXPORT_ROOT + "dinov2_vitl14/embedding_manifest_v2.csv",
            EXPORT_ROOT + "dinov2_vitl14/scores.csv",
        }
        if not required.issubset(set(archive.namelist())):
            raise ValueError("external export inventory is incomplete")
        audit = json.loads(archive.read(EXPORT_ROOT + "run_audit.json"))
        validation = json.loads(archive.read(EXPORT_ROOT + "validation_audit.json"))
        if audit.get("status") != "PASS" or validation.get("status") != "PASS" or validation.get("failures") != []:
            raise ValueError("external execution validation did not pass")
        if audit.get("contract_sha256") != EXPECTED_CONTRACT_SHA or audit.get("input_manifest_sha256") != EXPECTED_INPUT_SHA or audit.get("package_manifest_sha256") != EXPECTED_PACKAGE_SHA:
            raise ValueError("external export is not bound to the frozen Task 15I package")
        for name in ("megadescriptor_l_384", "dinov2_vitl14"):
            mapping = archive_csv(archive, EXPORT_ROOT + f"{name}/embedding_manifest_v2.csv")
            observed_by_id = {row["image_id"]: row["content_sha256"] for row in mapping}
            if len(mapping) != len(reference) or observed_by_id != expected_by_id:
                raise ValueError(f"{name} embedding manifest does not match the independent image reservoir")
    return {"run_audit": audit, "validation_audit": validation, "source_image_count": len(reference)}


def load_edges(zip_path: Path) -> list[Edge]:
    with zipfile.ZipFile(zip_path) as archive:
        mega = {
            (row["query_image_id"], row["candidate_image_id"]): int(row["candidate_rank"])
            for row in archive_csv(archive, EXPORT_ROOT + "megadescriptor_l_384/pair_scores.csv")
        }
        dino = {
            (row["query_image_id"], row["candidate_image_id"]): int(row["candidate_rank"])
            for row in archive_csv(archive, EXPORT_ROOT + "dinov2_vitl14/scores.csv")
        }
    grouped: dict[tuple[str, str], dict[str, int | None | bool]] = {}
    for left, right in set(mega).intersection(dino):
        a, b = sorted((left, right))
        record = grouped.setdefault((a, b), {"mega_a_to_b": None, "mega_b_to_a": None, "dino_a_to_b": None, "dino_b_to_a": None})
        direction = "a_to_b" if left == a else "b_to_a"
        record[f"mega_{direction}"] = mega[(left, right)]
        record[f"dino_{direction}"] = dino[(left, right)]
    edges: list[Edge] = []
    for (left, right), record in grouped.items():
        ranks = [value for value in record.values() if isinstance(value, int)]
        reciprocal = all(record[f"{model}_{direction}"] is not None for model in ("mega", "dino") for direction in ("a_to_b", "b_to_a"))
        edges.append(Edge(left, right, sum(ranks), max(ranks), reciprocal, record["mega_a_to_b"], record["mega_b_to_a"], record["dino_a_to_b"], record["dino_b_to_a"]))
    if len(edges) < 1600:
        raise ValueError("dual-descriptor consensus pool cannot support target pair count")
    return sorted(edges, key=Edge.key)


def grow_components(pool: list[Edge], initially_used: set[str], target: int, seed: int) -> list[list[Edge]]:
    """Grow vertex-disjoint four-edge trees; omitted candidate edges do not join components."""
    rng = random.Random(seed)
    adjacency: dict[str, list[Edge]] = defaultdict(list)
    for edge in pool:
        adjacency[edge.left].append(edge)
        adjacency[edge.right].append(edge)
    for edges in adjacency.values():
        edges.sort(key=Edge.key)
    seeds = list(pool)
    rng.shuffle(seeds)
    used = set(initially_used)
    components: list[list[Edge]] = []
    for seed_edge in seeds:
        if len(components) >= target or seed_edge.left in used or seed_edge.right in used:
            continue
        nodes, edges = {seed_edge.left, seed_edge.right}, [seed_edge]
        while len(edges) < 4:
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
            edges.append(edge)
        if len(edges) == 4:
            used.update(nodes)
            components.append(edges)
    return components


def select_components(edges: list[Edge], component_target: int = 400) -> tuple[list[list[Edge]], int]:
    strict = [edge for edge in edges if edge.strict_reciprocal]
    best: tuple[tuple[int, int, int], list[list[Edge]], int] | None = None
    for seed in range(300):
        primary = grow_components(strict, set(), component_target, seed)
        used = {node for component in primary for edge in component for node in (edge.left, edge.right)}
        supplementary = grow_components(edges, used, component_target - len(primary), seed + 1000)
        selected = primary + supplementary
        strict_count = sum(edge.strict_reciprocal for component in selected for edge in component)
        rank_sum = sum(edge.rank_sum for component in selected for edge in component)
        score = (len(selected), strict_count, -rank_sum)
        if best is None or score > best[0]:
            best = (score, selected, seed)
    assert best is not None
    if len(best[1]) != component_target:
        raise RuntimeError(f"selection produced {len(best[1])}, not {component_target}, components")
    return best[1], best[2]


def measure_quality(images: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, image_id in enumerate(sorted(images), start=1):
        item = images[image_id]
        path = ROOT / item["local_relative_path"]
        base = {"candidate_image_id": image_id, "content_sha256": item["sha256"]}
        try:
            if not path.is_file() or sha256(path) != item["sha256"]:
                raise OSError("file_unavailable")
            with Image.open(path) as decoded:
                image = np.asarray(decoded.convert("RGB"), dtype=np.uint8)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            rows.append({**base, "image_decode_status": "ok", "native_pixel_count": int(image.shape[0] * image.shape[1]), "sharpness_measure": f"{cv2.Laplacian(gray, cv2.CV_64F, ksize=3).var():.8f}", "exposure_clipping_fraction": f"{np.logical_or((image <= 5).any(axis=2), (image >= 250).any(axis=2)).mean():.8f}", "failure_code": "none", "value_status": "not_missing"})
        except OSError:
            rows.append({**base, "image_decode_status": "not_attempted", "native_pixel_count": "", "sharpness_measure": "", "exposure_clipping_fraction": "", "failure_code": "file_unavailable", "value_status": "upstream_input_absent"})
        except Exception:
            rows.append({**base, "image_decode_status": "failure", "native_pixel_count": "", "sharpness_measure": "", "exposure_clipping_fraction": "", "failure_code": "image_decode_failure", "value_status": "image_decode_failure"})
        if index % 250 == 0 or index == len(images):
            print(f"quality {index}/{len(images)}", flush=True)
    return rows


def local_coverage(left_path: Path, right_path: Path) -> tuple[float, int, int, int]:
    left = cv2.imread(str(left_path), cv2.IMREAD_GRAYSCALE)
    right = cv2.imread(str(right_path), cv2.IMREAD_GRAYSCALE)
    if left is None or right is None:
        raise OSError("image decode failure")
    sift = cv2.SIFT_create(nfeatures=800)
    left_keypoints, left_desc = sift.detectAndCompute(left, None)
    right_keypoints, right_desc = sift.detectAndCompute(right, None)
    if left_desc is None or right_desc is None or len(left_keypoints) < 4 or len(right_keypoints) < 4:
        return 0.0, 0, len(left_keypoints), len(right_keypoints)
    raw = cv2.BFMatcher(cv2.NORM_L2).knnMatch(left_desc, right_desc, k=2)
    good = [pair[0] for pair in raw if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
    if len(good) < 4:
        return 0.0, 0, len(left_keypoints), len(right_keypoints)
    source = np.float32([left_keypoints[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    target = np.float32([right_keypoints[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
    if mask is None:
        return 0.0, 0, len(left_keypoints), len(right_keypoints)
    inliers = [match for match, keep in zip(good, mask.ravel()) if bool(keep)]
    left_fraction = len({match.queryIdx for match in inliers}) / len(left_keypoints)
    right_fraction = len({match.trainIdx for match in inliers}) / len(right_keypoints)
    return float((left_fraction + right_fraction) / 2.0), len(inliers), len(left_keypoints), len(right_keypoints)


def measure_local(pairs: list[dict[str, Any]], images: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for index, pair in enumerate(pairs, start=1):
        started = time.perf_counter()
        left = ROOT / images[pair["endpoint_a_candidate_image_id"]]["local_relative_path"]
        right = ROOT / images[pair["endpoint_b_candidate_image_id"]]["local_relative_path"]
        try:
            coverage, inliers, left_count, right_count = local_coverage(left, right)
            row = {"candidate_pair_id": pair["candidate_pair_id"], "failure_code": "none", "value_status": "not_missing", "local_match_coverage_fraction": f"{coverage:.8f}", "inlier_count": inliers, "source_keypoint_count": left_count, "target_keypoint_count": right_count, "runtime_seconds": f"{time.perf_counter() - started:.6f}"}
        except Exception as error:
            row = {"candidate_pair_id": pair["candidate_pair_id"], "failure_code": "model_runtime_error", "value_status": "model_inference_failure", "local_match_coverage_fraction": "", "inlier_count": "", "source_keypoint_count": "", "target_keypoint_count": "", "runtime_seconds": f"{time.perf_counter() - started:.6f}"}
        rows.append(row)
        if index % 100 == 0 or index == len(pairs):
            print(f"local match {index}/{len(pairs)}", flush=True)
    return rows


def rank_band(edge: Edge) -> str:
    return "top_5" if edge.rank_max <= 5 else "top_10" if edge.rank_max <= 10 else "top_20"


def build_pairs(components: list[list[Edge]], quality: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quality_failure = {row["candidate_image_id"]: row["failure_code"] for row in quality}
    pairs = []
    for component_index, component in enumerate(components, start=1):
        for edge_index, edge in enumerate(component, start=1):
            pair_id = f"task15i_pair_c{component_index:03d}_e{edge_index}_{hashlib.sha256(f'{edge.left}|{edge.right}'.encode()).hexdigest()[:12]}"
            pairs.append({"candidate_pair_id": pair_id, "component_id": f"task15i_component_{component_index:03d}", "endpoint_a_candidate_image_id": edge.left, "endpoint_b_candidate_image_id": edge.right, "descriptor_support_category": "dual_descriptor_reciprocal" if edge.strict_reciprocal else "dual_descriptor_agreement", "best_rank_band": rank_band(edge), "development_evidence_state": "outcome_unopened", "endpoint_quality_measurement_failure": "none" if quality_failure[edge.left] == quality_failure[edge.right] == "none" else "endpoint_quality_failure", "local_match_measurement_failure": "pending", "mega_rank_a_to_b": "" if edge.mega_a_to_b is None else edge.mega_a_to_b, "mega_rank_b_to_a": "" if edge.mega_b_to_a is None else edge.mega_b_to_a, "dinov2_rank_a_to_b": "" if edge.dino_a_to_b is None else edge.dino_a_to_b, "dinov2_rank_b_to_a": "" if edge.dino_b_to_a is None else edge.dino_b_to_a})
    return pairs


def finalize_pairs(pairs: list[dict[str, Any]], local: list[dict[str, Any]]) -> None:
    by_id = {row["candidate_pair_id"]: row for row in local}
    for pair in pairs:
        pair["local_match_measurement_failure"] = "none" if by_id[pair["candidate_pair_id"]]["failure_code"] == "none" else "local_match_failure"


def validate_selected_graph(pairs: list[dict[str, Any]]) -> dict[str, int]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    per_component: Counter[str] = Counter()
    for row in pairs:
        left, right = row["endpoint_a_candidate_image_id"], row["endpoint_b_candidate_image_id"]
        if left == right or right in adjacency[left]:
            raise ValueError("invalid selected pair graph")
        adjacency[left].add(right); adjacency[right].add(left); per_component[row["component_id"]] += 1
    if len(pairs) != 1600 or len(per_component) != 400 or set(per_component.values()) != {4}:
        raise ValueError("selected graph does not meet exact component/pair target")
    maximum_degree = max(map(len, adjacency.values()))
    if maximum_degree > 6:
        raise ValueError("selected graph exceeds endpoint degree cap")
    return {"pair_count": len(pairs), "component_count": len(per_component), "maximum_endpoint_degree": maximum_degree, "selected_image_count": len(adjacency)}


def build(zip_path: Path, sha_path: Path, summary_path: Path, output: Path) -> dict[str, Any]:
    zip_path, sha_path, summary_path, output = (path.resolve() for path in (zip_path, sha_path, summary_path, output))
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    if parse_declared_sha(sha_path) != sha256(zip_path):
        raise ValueError("external descriptor ZIP SHA256 mismatch")
    summary = verify_summary(summary_path, sha256(zip_path))
    external = validate_external_export(zip_path, IMAGE_MANIFEST)
    image_rows = read_csv(IMAGE_MANIFEST)
    images = {row["candidate_image_id"]: row for row in image_rows}
    if len(images) != 4108:
        raise ValueError("unexpected independent image reservoir size")
    components, selected_seed = select_components(load_edges(zip_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        source = stage / "source_delivery"; source.mkdir(parents=True)
        shutil.copy2(zip_path, source / zip_path.name); shutil.copy2(sha_path, source / sha_path.name); shutil.copy2(summary_path, source / summary_path.name)
        results = stage / "descriptor_results"; results.mkdir()
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.namelist():
                if member.startswith(EXPORT_ROOT) and not member.endswith("/"):
                    destination = results / Path(member).relative_to(EXPORT_ROOT)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(member))
        quality = measure_quality(images)
        pairs = build_pairs(components, quality)
        local = measure_local(pairs, images)
        finalize_pairs(pairs, local)
        graph = validate_selected_graph(pairs)
        artifact_dir = stage / "prelabel_inputs"; artifact_dir.mkdir()
        write_csv(artifact_dir / "candidate_pairs.csv", pairs, PAIR_COLUMNS)
        write_csv(artifact_dir / "automatic_quality_measurements.csv", quality, QUALITY_COLUMNS)
        write_csv(artifact_dir / "local_match_measurements.csv", local, LOCAL_COLUMNS)
        audit = {"status": "PASS", "created_at_utc": utc_now(), "source_export_sha256": sha256(zip_path), "source_summary": summary, "external_validation_status": external["validation_audit"]["status"], "contract_sha256": EXPECTED_CONTRACT_SHA, "input_manifest_sha256": EXPECTED_INPUT_SHA, "selection_seed": selected_seed, "selection_rule": "Optimize deterministic two-stage vertex-disjoint four-edge trees over 300 fixed seeds: first dual-descriptor reciprocal edges, then dual-descriptor same-direction agreement edges only as needed to reach capacity. No labels, identity truth, human outcomes, or locked-stage outcomes are read.", "selected_descriptor_support_counts": dict(Counter(row["descriptor_support_category"] for row in pairs)), "selected_rank_band_counts": dict(Counter(row["best_rank_band"] for row in pairs)), "quality_failure_counts": dict(Counter(row["failure_code"] for row in quality)), "local_failure_counts": dict(Counter(row["failure_code"] for row in local)), "selected_graph": graph, "outcome_accessed": False, "claim_boundary": "These are outcome-free candidate and measurement artifacts. They authorize neither outcome collection nor any identity, performance, calibration, confirmation, or 90-percent correctness claim."}
        write_json(stage / "prepair_artifact_audit.json", audit)
        files = sorted(path for path in stage.rglob("*") if path.is_file())
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--sha256", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build(args.zip, args.sha256, args.summary, args.output)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
