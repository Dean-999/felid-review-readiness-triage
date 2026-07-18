#!/usr/bin/env python3
"""Extract Phase 6 v2 embeddings and merge Phase 7A 1000-image embeddings."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import timm
import torch
from PIL import Image
from torchvision.models import ResNet50_Weights, resnet50

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a"
PHASE6_MANIFEST = OUT_DIR / "czechlynx_phase6_v2_500_embedding_input_manifest.csv"
PHASE4_MEGA = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv"
PHASE4_RESNET = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_resnet50_embeddings.csv"
PHASE6_MEGA = OUT_DIR / "czechlynx_phase6_v2_500_megadescriptor_embeddings.csv"
PHASE6_RESNET = OUT_DIR / "czechlynx_phase6_v2_500_resnet50_embeddings.csv"
PHASE7A_MEGA = OUT_DIR / "czechlynx_phase7a_1000_megadescriptor_embeddings.csv"
PHASE7A_RESNET = OUT_DIR / "czechlynx_phase7a_1000_resnet50_embeddings.csv"
OUT_AUDIT = OUT_DIR / "phase7a_1000_embedding_build_audit.json"

MEGADESCRIPTOR_MODEL = "BVRA/MegaDescriptor-S-224"
RESNET_MODEL = "torchvision_resnet50_imagenet1k_v2_penultimate_cached"


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def resolve_path(path_text: object) -> Path:
    path = Path(str(path_text))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def vector_to_text(vector: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.9g}" for x in vector.tolist()) + "]"


def parse_vector(value: object) -> np.ndarray:
    return np.asarray(ast.literal_eval(str(value)), dtype=np.float32)


def load_resnet_model(device: torch.device) -> tuple[torch.nn.Module, Any]:
    weights = ResNet50_Weights.IMAGENET1K_V2
    model = resnet50(weights=weights)
    model.fc = torch.nn.Identity()
    model.eval()
    return model.to(device), weights.transforms()


def load_megadescriptor_model(device: torch.device) -> tuple[torch.nn.Module, Any]:
    model = timm.create_model(f"hf_hub:{MEGADESCRIPTOR_MODEL}", pretrained=True, num_classes=0)
    model.eval()
    config = timm.data.resolve_model_data_config(model)
    transform = timm.data.create_transform(**config, is_training=False)
    return model.to(device), transform


def extract_frame(
    manifest: pd.DataFrame,
    descriptor: str,
    model: torch.nn.Module,
    transform: Any,
    device: torch.device,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, item in manifest.sort_values("expanded_image_id").iterrows():
        image_path = resolve_path(item["review_image_path_local"])
        with Image.open(image_path) as image:
            tensor = transform(image.convert("RGB")).unsqueeze(0).to(device)
        with torch.inference_mode():
            vector = model(tensor).squeeze(0).detach().cpu().float().numpy()
        rows.append(
            {
                "expanded_image_id": str(item["expanded_image_id"]),
                "embedding_model": descriptor,
                "embedding_dim": int(vector.shape[0]),
                "embedding_vector": vector_to_text(vector),
            }
        )
    return pd.DataFrame(rows)


def validate_embeddings(frame: pd.DataFrame, expected_rows: int, expected_dim: int, path: Path) -> None:
    required = {"expanded_image_id", "embedding_model", "embedding_dim", "embedding_vector"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    if len(frame) != expected_rows:
        raise ValueError(f"{path} has {len(frame)} rows, expected {expected_rows}")
    if frame["expanded_image_id"].astype(str).nunique() != expected_rows:
        raise ValueError(f"{path} has duplicate expanded_image_id values")
    dims = set(pd.to_numeric(frame["embedding_dim"], errors="raise").astype(int))
    if dims != {expected_dim}:
        raise ValueError(f"{path} has embedding dims {sorted(dims)}, expected {expected_dim}")
    sample = np.vstack([parse_vector(value) for value in frame["embedding_vector"].head(min(5, len(frame)))])
    if sample.shape[1] != expected_dim or not np.isfinite(sample).all():
        raise ValueError(f"{path} contains malformed embedding vectors")


def write_or_reuse_phase6(
    manifest: pd.DataFrame,
    output: Path,
    descriptor: str,
    expected_dim: int,
    force: bool,
    device: torch.device,
) -> str:
    if output.exists() and not force:
        frame = pd.read_csv(output)
        validate_embeddings(frame, len(manifest), expected_dim, output)
        return "reused_existing"

    if descriptor == MEGADESCRIPTOR_MODEL:
        model, transform = load_megadescriptor_model(device)
    elif descriptor == RESNET_MODEL:
        model, transform = load_resnet_model(device)
    else:
        raise ValueError(f"unsupported descriptor: {descriptor}")
    frame = extract_frame(manifest, descriptor, model, transform, device)
    validate_embeddings(frame, len(manifest), expected_dim, output)
    frame.to_csv(output, index=False)
    return "extracted"


def merge_embeddings(phase4_path: Path, phase6_path: Path, output: Path, expected_dim: int) -> None:
    phase4 = pd.read_csv(phase4_path)
    phase6 = pd.read_csv(phase6_path)
    merged = pd.concat([phase4, phase6], ignore_index=True)
    validate_embeddings(merged, 1000, expected_dim, output)
    merged.to_csv(output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-extract Phase 6 embeddings even if cached CSVs exist.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(PHASE6_MANIFEST)
    if len(manifest) != 500:
        raise ValueError(f"{PHASE6_MANIFEST} must contain 500 rows")
    missing_paths = [str(resolve_path(path)) for path in manifest["review_image_path_local"] if not resolve_path(path).exists()]
    if missing_paths:
        raise FileNotFoundError(f"missing image paths: {missing_paths[:5]}")

    device = select_device()
    mega_status = write_or_reuse_phase6(manifest, PHASE6_MEGA, MEGADESCRIPTOR_MODEL, 768, args.force, device)
    resnet_status = write_or_reuse_phase6(manifest, PHASE6_RESNET, RESNET_MODEL, 2048, args.force, device)

    merge_embeddings(PHASE4_MEGA, PHASE6_MEGA, PHASE7A_MEGA, 768)
    merge_embeddings(PHASE4_RESNET, PHASE6_RESNET, PHASE7A_RESNET, 2048)

    audit: dict[str, Any] = {
        "device": str(device),
        "phase6_manifest": rel(PHASE6_MANIFEST),
        "phase6_image_count": int(len(manifest)),
        "phase6_megadescriptor_status": mega_status,
        "phase6_resnet50_status": resnet_status,
        "phase6_megadescriptor_embeddings": rel(PHASE6_MEGA),
        "phase6_resnet50_embeddings": rel(PHASE6_RESNET),
        "phase7a_1000_megadescriptor_embeddings": rel(PHASE7A_MEGA),
        "phase7a_1000_resnet50_embeddings": rel(PHASE7A_RESNET),
        "phase7a_1000_megadescriptor_rows": int(len(pd.read_csv(PHASE7A_MEGA, usecols=["expanded_image_id"]))),
        "phase7a_1000_resnet50_rows": int(len(pd.read_csv(PHASE7A_RESNET, usecols=["expanded_image_id"]))),
    }
    OUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote {rel(PHASE6_MEGA)} status={mega_status}")
    print(f"Wrote {rel(PHASE6_RESNET)} status={resnet_status}")
    print(f"Wrote {rel(PHASE7A_MEGA)}")
    print(f"Wrote {rel(PHASE7A_RESNET)}")
    print(f"Wrote {rel(OUT_AUDIT)}")


if __name__ == "__main__":
    main()
