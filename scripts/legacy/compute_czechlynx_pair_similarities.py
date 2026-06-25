#!/usr/bin/env python3
"""Compute cosine similarities for CzechLynx pilot pairs."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_CSV = PROJECT_ROOT / "data" / "interim" / "czechlynx" / "czechlynx_pilot_pairs.csv"
EMBEDDINGS_PARQUET = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_embeddings.parquet"
)
SIMILARITIES_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pair_similarities.csv"
)

EXPECTED_PAIR_ROWS = 400
OUTPUT_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "same_individual",
    "triage_label_a",
    "triage_label_b",
    "pair_readiness_group",
    "cosine_similarity",
]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def as_vector(value: object) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return value.astype(np.float32)
    if isinstance(value, list):
        return np.asarray(value, dtype=np.float32)
    return np.asarray(list(value), dtype=np.float32)


def cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
    if denominator == 0.0:
        raise ValueError("zero-norm embedding vector")
    return float(np.dot(vector_a, vector_b) / denominator)


def main() -> int:
    if not PAIR_CSV.exists():
        print(f"FAIL: pair file not found: {PAIR_CSV}")
        return 1
    if not EMBEDDINGS_PARQUET.exists():
        print(f"FAIL: embeddings parquet not found: {EMBEDDINGS_PARQUET}")
        return 1

    pairs = read_csv_clean(PAIR_CSV)
    embeddings = pd.read_parquet(EMBEDDINGS_PARQUET)

    required_pair_columns = set(OUTPUT_COLUMNS) - {"cosine_similarity"}
    missing_pair_columns = sorted(required_pair_columns - set(pairs.columns))
    missing_embedding_columns = sorted(
        {"pilot_image_id", "embedding_vector"} - set(embeddings.columns)
    )
    if missing_pair_columns:
        print("FAIL: pair file missing required column(s): " + ", ".join(missing_pair_columns))
        return 1
    if missing_embedding_columns:
        print(
            "FAIL: embeddings file missing required column(s): "
            + ", ".join(missing_embedding_columns)
        )
        return 1
    if len(pairs) != EXPECTED_PAIR_ROWS:
        print(f"FAIL: pair file has {len(pairs)} rows; expected {EXPECTED_PAIR_ROWS}")
        return 1
    if embeddings["pilot_image_id"].duplicated().any():
        print("FAIL: embeddings file contains duplicate pilot_image_id values")
        return 1

    embedding_lookup = {
        clean_cell(row["pilot_image_id"]): as_vector(row["embedding_vector"])
        for _, row in embeddings.iterrows()
    }

    missing_ids = sorted(
        (set(pairs["image_id_a"]) | set(pairs["image_id_b"])) - set(embedding_lookup)
    )
    if missing_ids:
        print(f"FAIL: {len(missing_ids)} pair image ID(s) missing embeddings")
        for image_id in missing_ids[:10]:
            print(f"  missing: {image_id}")
        return 1

    output = pairs[list(required_pair_columns)].copy()
    similarities: list[float] = []
    for _, row in pairs.iterrows():
        try:
            similarities.append(
                cosine_similarity(
                    embedding_lookup[row["image_id_a"]],
                    embedding_lookup[row["image_id_b"]],
                )
            )
        except Exception as exc:  # noqa: BLE001 - fail with pair context.
            print(f"FAIL: could not compute similarity for {row['pair_id']}: {exc}")
            return 1

    output["cosine_similarity"] = similarities
    output = output[OUTPUT_COLUMNS]
    SIMILARITIES_CSV.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(SIMILARITIES_CSV, index=False)

    same_count = int((output["same_individual"] == "True").sum())
    different_count = int((output["same_individual"] == "False").sum())
    similarity_series = output["cosine_similarity"]

    print("CzechLynx pair similarity computation")
    print(f"Pair file: {PAIR_CSV}")
    print(f"Embeddings parquet: {EMBEDDINGS_PARQUET}")
    print(f"Output CSV: {SIMILARITIES_CSV}")
    print(f"Total pairs: {len(output)}")
    print(f"Same-individual pairs: {same_count}")
    print(f"Different-individual pairs: {different_count}")
    print(
        "Similarity min/mean/max: "
        f"{similarity_series.min():.6f} / "
        f"{similarity_series.mean():.6f} / "
        f"{similarity_series.max():.6f}"
    )
    print("Pair readiness group counts:")
    for group, count in output["pair_readiness_group"].value_counts().sort_index().items():
        print(f"  {group}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
