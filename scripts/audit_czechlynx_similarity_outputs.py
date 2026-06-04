#!/usr/bin/env python3
"""Audit CzechLynx embedding and pair similarity outputs."""

from __future__ import annotations

import sys
from pathlib import Path

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

EXPECTED_EMBEDDINGS = 200
EXPECTED_SIMILARITIES = 400


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def add_count_check(
    passes: list[str],
    failures: list[str],
    label: str,
    actual: int,
    expected: int,
) -> None:
    if actual == expected:
        passes.append(f"{label} is exactly {expected}.")
    else:
        failures.append(f"{label} is {actual}; expected {expected}.")


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []

    for path, label in (
        (PAIR_CSV, "pair file"),
        (EMBEDDINGS_PARQUET, "embeddings parquet"),
        (SIMILARITIES_CSV, "similarities CSV"),
    ):
        if not path.exists():
            print(f"FAIL: {label} not found: {path}")
            return 1

    pairs = read_csv_clean(PAIR_CSV)
    embeddings = pd.read_parquet(EMBEDDINGS_PARQUET)
    similarities = read_csv_clean(SIMILARITIES_CSV)

    missing_embedding_columns = sorted(
        {"pilot_image_id", "embedding_vector"} - set(embeddings.columns)
    )
    missing_similarity_columns = sorted(
        {"pair_id", "same_individual", "cosine_similarity"} - set(similarities.columns)
    )
    missing_pair_columns = sorted({"pair_id", "same_individual"} - set(pairs.columns))

    if missing_embedding_columns:
        failures.append(
            "Embeddings missing required column(s): "
            + ", ".join(missing_embedding_columns)
        )
    else:
        passes.append("Embeddings file has required columns.")

    if missing_similarity_columns:
        failures.append(
            "Similarities missing required column(s): "
            + ", ".join(missing_similarity_columns)
        )
    else:
        passes.append("Similarities file has required columns.")

    if missing_pair_columns:
        failures.append("Pair file missing required column(s): " + ", ".join(missing_pair_columns))
    else:
        passes.append("Pair file has required columns.")

    if not failures:
        add_count_check(
            passes,
            failures,
            "Embedding row count",
            len(embeddings),
            EXPECTED_EMBEDDINGS,
        )
        add_count_check(
            passes,
            failures,
            "Pair similarity row count",
            len(similarities),
            EXPECTED_SIMILARITIES,
        )

        unique_embedding_ids = embeddings["pilot_image_id"].astype(str).nunique()
        add_count_check(
            passes,
            failures,
            "Unique embedding pilot_image_id count",
            unique_embedding_ids,
            EXPECTED_EMBEDDINGS,
        )

        missing_cosine = int((similarities["cosine_similarity"] == "").sum())
        numeric_cosine = pd.to_numeric(similarities["cosine_similarity"], errors="coerce")
        nan_cosine = int(numeric_cosine.isna().sum())
        if missing_cosine or nan_cosine:
            failures.append(
                f"cosine_similarity has {missing_cosine} blank and {nan_cosine} nonnumeric value(s)."
            )
        else:
            passes.append("No missing cosine_similarity values.")

        pair_ids = set(pairs["pair_id"])
        similarity_pair_ids = set(similarities["pair_id"])
        missing_pair_ids = sorted(pair_ids - similarity_pair_ids)
        extra_pair_ids = sorted(similarity_pair_ids - pair_ids)
        if missing_pair_ids:
            failures.append(f"{len(missing_pair_ids)} pair ID(s) missing from similarities.")
            for pair_id in missing_pair_ids[:10]:
                failures.append(f"  missing pair_id: {pair_id}")
        else:
            passes.append("All pair IDs from pair file are present in similarities.")
        if extra_pair_ids:
            failures.append(f"{len(extra_pair_ids)} extra pair ID(s) found in similarities.")
            for pair_id in extra_pair_ids[:10]:
                failures.append(f"  extra pair_id: {pair_id}")
        else:
            passes.append("No extra pair IDs found in similarities.")

        pair_flags = pairs.set_index("pair_id")["same_individual"]
        similarity_flags = similarities.set_index("pair_id")["same_individual"]
        common_pair_ids = sorted(pair_ids & similarity_pair_ids)
        mismatched_flags = [
            pair_id
            for pair_id in common_pair_ids
            if pair_flags.loc[pair_id] != similarity_flags.loc[pair_id]
        ]
        if mismatched_flags:
            failures.append(
                f"{len(mismatched_flags)} same_individual value(s) do not match pair file."
            )
            for pair_id in mismatched_flags[:10]:
                failures.append(f"  mismatched pair_id: {pair_id}")
        else:
            passes.append("same_individual values match the pair file.")

    print("CzechLynx similarity output audit")
    print(f"Pair file: {PAIR_CSV}")
    print(f"Embeddings parquet: {EMBEDDINGS_PARQUET}")
    print(f"Similarities CSV: {SIMILARITIES_CSV}")
    print()

    if passes:
        print("PASS checks:")
        for item in passes:
            print(f"  [PASS] {item}")
        print()

    if failures:
        print("FAIL checks:")
        for item in failures:
            print(f"  [FAIL] {item}")
        print()
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
