#!/usr/bin/env python3
"""Extract fixed pretrained image embeddings for the CzechLynx pilot."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import torch
from PIL import Image
from torchvision.models import ResNet50_Weights, resnet50

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_validation_table.csv"
)
EMBEDDINGS_PARQUET = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_embeddings.parquet"
)

EXPECTED_ROWS = 200
EMBEDDING_MODEL = "torchvision_resnet50_imagenet1k_v2_penultimate_cached"
WEIGHTS = ResNet50_Weights.IMAGENET1K_V2


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def resolve_project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def cached_weight_path() -> Path:
    filename = Path(urlparse(WEIGHTS.url).path).name
    return Path(torch.hub.get_dir()) / "checkpoints" / filename


def load_cached_model(device: torch.device) -> torch.nn.Module:
    weight_path = cached_weight_path()
    if not weight_path.exists():
        raise FileNotFoundError(
            "Cached ResNet-50 ImageNet weights were not found at "
            f"{weight_path}. Pre-cache torchvision ResNet50_Weights.IMAGENET1K_V2 "
            "outside this run, then rerun this script. This script will not "
            "download weights automatically."
        )

    model = resnet50(weights=None)
    state_dict = torch.load(weight_path, map_location="cpu")
    model.load_state_dict(state_dict)
    # Remove the classifier head. The remaining module returns 2048 pooled features.
    model.fc = torch.nn.Identity()
    model.eval()
    return model.to(device)


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def extract_embedding(
    image_path: Path,
    model: torch.nn.Module,
    preprocess: torch.nn.Module,
    device: torch.device,
) -> list[float]:
    with Image.open(image_path) as image:
        tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model(tensor).squeeze(0).detach().cpu().float().numpy()
    return embedding.tolist()


def main() -> int:
    if not VALIDATION_TABLE_CSV.exists():
        print(f"FAIL: validation table not found: {VALIDATION_TABLE_CSV}")
        return 1

    df = read_csv_clean(VALIDATION_TABLE_CSV)
    required_columns = {"pilot_image_id", "image_path"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        print("FAIL: validation table missing required column(s): " + ", ".join(missing_columns))
        return 1

    if len(df) != EXPECTED_ROWS:
        print(f"FAIL: validation table has {len(df)} rows; expected {EXPECTED_ROWS}")
        return 1
    if df["pilot_image_id"].duplicated().any():
        print("FAIL: validation table contains duplicate pilot_image_id values")
        return 1

    missing_paths = [
        str(resolve_project_path(path_text))
        for path_text in df["image_path"]
        if not resolve_project_path(path_text).exists()
    ]
    if missing_paths:
        print(f"FAIL: {len(missing_paths)} image path(s) are missing")
        for path in missing_paths[:10]:
            print(f"  missing: {path}")
        return 1

    device = select_device()
    try:
        model = load_cached_model(device)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}")
        return 1

    preprocess = WEIGHTS.transforms()
    records: list[dict[str, object]] = []
    failed_images: list[str] = []

    for _, row in df.sort_values("pilot_image_id").iterrows():
        image_path = resolve_project_path(row["image_path"])
        try:
            vector = extract_embedding(image_path, model, preprocess, device)
        except Exception as exc:  # noqa: BLE001 - report image-level failures clearly.
            failed_images.append(f"{row['pilot_image_id']}: {exc}")
            continue

        records.append(
            {
                "pilot_image_id": row["pilot_image_id"],
                "image_path": row["image_path"],
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dim": len(vector),
                "embedding_vector": vector,
            }
        )

    embeddings = pd.DataFrame(records)
    if failed_images or len(embeddings) != EXPECTED_ROWS:
        print(f"FAIL: embeddings missing for {EXPECTED_ROWS - len(embeddings)} image(s)")
        for item in failed_images[:10]:
            print(f"  failed: {item}")
        return 1

    embedding_dims = set(embeddings["embedding_dim"])
    if len(embedding_dims) != 1:
        print(f"FAIL: inconsistent embedding dimensions: {sorted(embedding_dims)}")
        return 1

    EMBEDDINGS_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    embeddings.to_parquet(EMBEDDINGS_PARQUET, index=False)

    embedding_dim = int(embeddings["embedding_dim"].iloc[0])
    print("CzechLynx pilot embedding extraction")
    print(f"Validation table: {VALIDATION_TABLE_CSV}")
    print(f"Output parquet: {EMBEDDINGS_PARQUET}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Device: {device}")
    print(f"Total images: {len(df)}")
    print(f"Embeddings written: {len(embeddings)}")
    print(f"Embedding dimension: {embedding_dim}")
    print("Missing/failed images: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
