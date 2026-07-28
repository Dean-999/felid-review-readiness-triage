#!/usr/bin/env python3
"""Immutable Task 15I image-only dual-descriptor ModelScope runner."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


MANIFEST_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
EMBEDDING_COLUMNS = [
    "image_id", "row_index", "embedding_dim", "content_sha256", "model_id",
    "extractor_version", "status",
]
SCORE_COLUMNS = [
    "query_image_id", "candidate_image_id", "candidate_rank",
    "descriptor_similarity", "descriptor_name",
]


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


def package_root_from_args(value: Path) -> Path:
    root = value.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"package root does not exist: {root}")
    return root


def verify_package_manifest(package_root: Path) -> str:
    manifest = package_root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        raise FileNotFoundError("missing PACKAGE_MANIFEST.sha256")
    declared: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        target = package_root / relative
        if relative in declared or not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package manifest verification failed: {relative}")
        declared.add(relative)
    # Python may create __pycache__ beside this runner after the first command;
    # it is runtime residue, never a declared package artifact.
    actual = {
        str(path.relative_to(package_root)) for path in package_root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256" and "__pycache__" not in path.parts
    }
    if declared != actual:
        raise RuntimeError("package manifest inventory mismatch")
    return sha256(manifest)


def load_contract(package_root: Path) -> tuple[dict[str, Any], str]:
    path = package_root / "contracts/task15i_descriptor_inference_contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("input_manifest_columns") != MANIFEST_COLUMNS:
        raise ValueError("unexpected input manifest contract")
    return contract, sha256(path)


def load_and_verify_images(manifest_path: Path, image_root: Path, contract: dict[str, Any]) -> list[dict[str, str]]:
    manifest_path, image_root = manifest_path.resolve(), image_root.resolve()
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MANIFEST_COLUMNS:
            raise ValueError("manifest columns must be exactly image_id,image_path_relative,content_sha256")
        rows = list(reader)
    if len(rows) != int(contract["expected_image_count"]):
        raise ValueError(f"expected {contract['expected_image_count']} images, found {len(rows)}")
    ids, hashes, names = set(), set(), set()
    verified: list[dict[str, str]] = []
    for row in rows:
        image_id, relative, expected = (row[key].strip() for key in MANIFEST_COLUMNS)
        if not image_id or not relative or len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise ValueError("invalid image manifest value")
        filename = Path(relative).name
        if filename != relative.rsplit("/", 1)[-1] or not filename or filename in names:
            raise ValueError(f"unsafe or duplicate image filename: {relative}")
        target = image_root / filename
        if not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"image integrity failure: {image_id}")
        if image_id in ids or expected in hashes:
            raise ValueError("image ids and content hashes must be unique")
        ids.add(image_id); hashes.add(expected); names.add(filename)
        verified.append({"image_id": image_id, "content_sha256": expected, "image_path": str(target)})
    return verified


def normalized(array: np.ndarray) -> np.ndarray:
    values = np.asarray(array, dtype=np.float32)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise RuntimeError("invalid embedding array")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if np.any(~np.isfinite(norms)) or np.any(norms <= 1e-12):
        raise RuntimeError("zero or non-finite embedding norm")
    return values / norms


def _batches(rows: list[dict[str, str]], batch_size: int):
    for index in range(0, len(rows), batch_size):
        yield rows[index:index + batch_size]


def infer_mega(rows: list[dict[str, str]], descriptor: dict[str, Any], batch_size: int, device: str) -> tuple[np.ndarray, dict[str, str]]:
    import torch
    import timm
    from PIL import Image
    from timm.data import create_transform, resolve_model_data_config

    model = timm.create_model(descriptor["model_id"], pretrained=True).to(device).eval()
    transform = create_transform(**resolve_model_data_config(model), is_training=False)
    chunks: list[np.ndarray] = []
    with torch.inference_mode():
        for batch in _batches(rows, batch_size):
            images = []
            for row in batch:
                with Image.open(row["image_path"]) as image:
                    images.append(transform(image.convert("RGB")))
            output = model(torch.stack(images).to(device, non_blocking=True))
            if isinstance(output, (tuple, list)):
                output = output[0]
            chunks.append(output.detach().float().cpu().numpy())
    return normalized(np.concatenate(chunks, axis=0)), {"torch": torch.__version__, "timm": timm.__version__}


def infer_dino(rows: list[dict[str, str]], descriptor: dict[str, Any], batch_size: int, device: str) -> tuple[np.ndarray, dict[str, str]]:
    import torch
    import torchvision
    import transformers
    from PIL import Image
    from torchvision import transforms
    from transformers import Dinov2Model

    transform = transforms.Compose([
        transforms.Resize(int(descriptor["resize_shorter_side"])),
        transforms.CenterCrop(int(descriptor["center_crop"])),
        transforms.ToTensor(),
        transforms.Normalize(mean=descriptor["normalization_mean"], std=descriptor["normalization_std"]),
    ])
    model = Dinov2Model.from_pretrained(descriptor["model_id"]).to(device).eval()
    chunks: list[np.ndarray] = []
    with torch.inference_mode():
        for batch in _batches(rows, batch_size):
            images = []
            for row in batch:
                with Image.open(row["image_path"]) as image:
                    images.append(transform(image.convert("RGB")))
            result = model(pixel_values=torch.stack(images).to(device, non_blocking=True))
            chunks.append(result.last_hidden_state[:, 0, :].detach().float().cpu().numpy())
    return normalized(np.concatenate(chunks, axis=0)), {"torch": torch.__version__, "torchvision": torchvision.__version__, "transformers": transformers.__version__}


def score_rows(ids: list[str], embeddings: np.ndarray, descriptor_name: str, top_k: int) -> list[dict[str, Any]]:
    if len(ids) <= top_k:
        raise ValueError("not enough images for requested top-k")
    output: list[dict[str, Any]] = []
    vectors = normalized(embeddings)
    for begin in range(0, len(ids), 128):
        finish = min(begin + 128, len(ids))
        scores = vectors[begin:finish] @ vectors.T
        scores[np.arange(finish - begin), np.arange(begin, finish)] = -np.inf
        selected = np.argpartition(-scores, kth=top_k - 1, axis=1)[:, :top_k]
        selected_scores = np.take_along_axis(scores, selected, axis=1)
        order = np.argsort(-selected_scores, axis=1, kind="mergesort")
        selected = np.take_along_axis(selected, order, axis=1)
        selected_scores = np.take_along_axis(selected_scores, order, axis=1)
        for row_index, candidates in enumerate(selected):
            query_index = begin + row_index
            for rank, candidate_index in enumerate(candidates, start=1):
                output.append({"query_image_id": ids[query_index], "candidate_image_id": ids[int(candidate_index)], "candidate_rank": rank, "descriptor_similarity": float(selected_scores[row_index, rank - 1]), "descriptor_name": descriptor_name})
    return output


def write_descriptor_output(output_dir: Path, descriptor_name: str, descriptor: dict[str, Any], rows: list[dict[str, str]], embeddings: np.ndarray, runtime: dict[str, str], contract_sha: str, top_k: int) -> dict[str, Any]:
    dimension = int(descriptor["embedding_dimension"])
    if embeddings.shape != (len(rows), dimension):
        raise RuntimeError(f"{descriptor_name} embedding shape mismatch: {embeddings.shape}")
    target = output_dir / descriptor_name
    target.mkdir(parents=True, exist_ok=False)
    np.save(target / "embeddings.npy", embeddings)
    with (target / "embedding_manifest_v2.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EMBEDDING_COLUMNS)
        writer.writeheader()
        writer.writerows({"image_id": row["image_id"], "row_index": index, "embedding_dim": dimension, "content_sha256": row["content_sha256"], "model_id": descriptor["model_id"], "extractor_version": "pferi_v2_task15i_descriptor_inference_v1", "status": "success"} for index, row in enumerate(rows))
    scores = score_rows([row["image_id"] for row in rows], embeddings, descriptor_name, top_k)
    score_file = "pair_scores.csv" if descriptor_name == "megadescriptor_l_384" else "scores.csv"
    with (target / score_file).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_COLUMNS)
        writer.writeheader(); writer.writerows(scores)
    audit = {"status": "PASS", "descriptor_name": descriptor_name, "model_id": descriptor["model_id"], "contract_sha256": contract_sha, "embedding_shape": list(embeddings.shape), "embedding_l2_normalized": True, "score_rows": len(scores), "top_k": top_k, "runtime": runtime, "embeddings_sha256": sha256(target / "embeddings.npy"), "embedding_manifest_sha256": sha256(target / "embedding_manifest_v2.csv"), "scores_sha256": sha256(target / score_file)}
    write_json(target / "run_audit.json", audit)
    return audit


def smoke(package_root: Path, manifest: Path, image_root: Path, output_dir: Path) -> dict[str, Any]:
    package_sha = verify_package_manifest(package_root)
    contract, contract_sha = load_contract(package_root)
    rows = load_and_verify_images(manifest, image_root, contract)
    try:
        import torch
        cuda = bool(torch.cuda.is_available())
    except ImportError as error:
        raise RuntimeError("missing torch dependency") from error
    audit = {"status": "PASS", "created_at_utc": utc_now(), "package_manifest_sha256": package_sha, "contract_sha256": contract_sha, "input_manifest_sha256": sha256(manifest), "verified_image_count": len(rows), "cuda_available": cuda, "python": platform.python_version(), "locked_stage_outcomes_accessed": False, "claim_boundary": contract["claim_boundary"]}
    if not cuda:
        raise RuntimeError("CUDA GPU is required for this Task 15I ModelScope package")
    write_json(output_dir / "smoke_audit.json", audit)
    return audit


def run(package_root: Path, manifest: Path, image_root: Path, output_dir: Path, batch_size: int) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite results directory: {output_dir}")
    contract, contract_sha = load_contract(package_root)
    rows = load_and_verify_images(manifest, image_root, contract)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for this Task 15I ModelScope package")
    output_dir.mkdir(parents=True)
    device = "cuda"
    mega, mega_runtime = infer_mega(rows, contract["descriptors"]["megadescriptor_l_384"], batch_size, device)
    mega_audit = write_descriptor_output(output_dir, "megadescriptor_l_384", contract["descriptors"]["megadescriptor_l_384"], rows, mega, mega_runtime, contract_sha, int(contract["top_k"]))
    dino, dino_runtime = infer_dino(rows, contract["descriptors"]["dinov2_vitl14"], batch_size, device)
    dino_audit = write_descriptor_output(output_dir, "dinov2_vitl14", contract["descriptors"]["dinov2_vitl14"], rows, dino, dino_runtime, contract_sha, int(contract["top_k"]))
    audit = {"status": "PASS", "created_at_utc": utc_now(), "package_manifest_sha256": verify_package_manifest(package_root), "contract_sha256": contract_sha, "input_manifest_sha256": sha256(manifest), "verified_image_count": len(rows), "batch_size": batch_size, "device": torch.cuda.get_device_name(0), "locked_stage_outcomes_accessed": False, "descriptor_runs": [mega_audit, dino_audit], "claim_boundary": contract["claim_boundary"]}
    write_json(output_dir / "run_audit.json", audit)
    return audit


def validate_results(package_root: Path, manifest: Path, results_dir: Path) -> dict[str, Any]:
    contract, contract_sha = load_contract(package_root)
    with manifest.open(newline="", encoding="utf-8") as handle:
        expected_rows = list(csv.DictReader(handle))
    if [*expected_rows[0]] != MANIFEST_COLUMNS or len(expected_rows) != int(contract["expected_image_count"]):
        raise ValueError("input manifest does not match contract")
    expected_ids = [row["image_id"] for row in expected_rows]
    failures: list[str] = []
    for name, descriptor in contract["descriptors"].items():
        target = results_dir / name
        score_file = "pair_scores.csv" if name == "megadescriptor_l_384" else "scores.csv"
        try:
            embeddings = np.load(target / "embeddings.npy", allow_pickle=False)
            if embeddings.shape != (len(expected_ids), int(descriptor["embedding_dimension"])) or not np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, rtol=1e-4, atol=1e-4):
                raise ValueError("invalid embedding shape or normalization")
            with (target / "embedding_manifest_v2.csv").open(newline="", encoding="utf-8") as handle:
                mapping = list(csv.DictReader(handle))
            if len(mapping) != len(expected_ids) or [row["image_id"] for row in mapping] != expected_ids:
                raise ValueError("embedding manifest image order mismatch")
            with (target / score_file).open(newline="", encoding="utf-8") as handle:
                scores = list(csv.DictReader(handle))
            if len(scores) != len(expected_ids) * int(contract["top_k"]):
                raise ValueError("score row count mismatch")
            for index, row in enumerate(scores):
                if list(row) != SCORE_COLUMNS or row["query_image_id"] not in expected_ids or row["candidate_image_id"] not in expected_ids or row["query_image_id"] == row["candidate_image_id"] or int(row["candidate_rank"]) != index % int(contract["top_k"]) + 1 or row["descriptor_name"] != name or not np.isfinite(float(row["descriptor_similarity"])):
                    raise ValueError("invalid directed score row")
        except Exception as error:
            failures.append(f"{name}:{type(error).__name__}:{error}")
    run_audit = results_dir / "run_audit.json"
    if not run_audit.is_file() or json.loads(run_audit.read_text(encoding="utf-8")).get("contract_sha256") != contract_sha:
        failures.append("run_audit_contract_mismatch")
    audit = {"status": "PASS" if not failures else "FAIL", "validated_at_utc": utc_now(), "contract_sha256": contract_sha, "input_manifest_sha256": sha256(manifest), "expected_image_count": len(expected_ids), "top_k": int(contract["top_k"]), "failures": failures, "locked_stage_outcomes_accessed": False}
    write_json(results_dir / "validation_audit.json", audit)
    if failures:
        raise RuntimeError("validation failed: " + "; ".join(failures))
    return audit


def export_results(results_dir: Path, zip_path: Path) -> dict[str, Any]:
    validation = results_dir / "validation_audit.json"
    if not validation.is_file() or json.loads(validation.read_text(encoding="utf-8")).get("status") != "PASS":
        raise RuntimeError("a passing validate command is required before export")
    if zip_path.exists():
        raise FileExistsError(f"refusing to overwrite export: {zip_path}")
    required = [results_dir / "run_audit.json", validation]
    for name, score in (("megadescriptor_l_384", "pair_scores.csv"), ("dinov2_vitl14", "scores.csv")):
        required.extend([results_dir / name / "embeddings.npy", results_dir / name / "embedding_manifest_v2.csv", results_dir / name / score, results_dir / name / "run_audit.json"])
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("result inventory incomplete")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in required:
            archive.write(path, arcname=f"PF_ERI_TASK15I_DESCRIPTOR_FINAL_EXPORT/{path.relative_to(results_dir)}")
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"bad export ZIP member: {bad}")
    audit = {"status": "PASS", "created_at_utc": utc_now(), "zip": zip_path.name, "zip_sha256": sha256(zip_path), "file_count": len(required)}
    write_json(results_dir / "export_audit.json", audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("smoke", "run"):
        item = sub.add_parser(command)
        item.add_argument("--package-root", type=Path, default=Path("."))
        item.add_argument("--manifest", type=Path, required=True)
        item.add_argument("--image-root", type=Path, required=True)
        item.add_argument("--output-dir", type=Path, required=True)
        if command == "run":
            item.add_argument("--batch-size", type=int, default=16)
    item = sub.add_parser("validate")
    item.add_argument("--package-root", type=Path, default=Path("."))
    item.add_argument("--manifest", type=Path, required=True)
    item.add_argument("--results-dir", type=Path, required=True)
    item = sub.add_parser("export")
    item.add_argument("--results-dir", type=Path, required=True)
    item.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "smoke":
            result = smoke(package_root_from_args(args.package_root), args.manifest, args.image_root, args.output_dir)
        elif args.command == "run":
            if args.batch_size < 1:
                raise ValueError("batch size must be positive")
            result = run(package_root_from_args(args.package_root), args.manifest, args.image_root, args.output_dir, args.batch_size)
        elif args.command == "validate":
            result = validate_results(package_root_from_args(args.package_root), args.manifest, args.results_dir)
        else:
            result = export_results(args.results_dir.resolve(), args.zip.resolve())
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
