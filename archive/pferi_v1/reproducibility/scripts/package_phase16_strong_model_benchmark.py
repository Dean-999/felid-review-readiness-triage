#!/usr/bin/env python3
"""Package image and pair manifests for external strong-model benchmarking."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_INPUT = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_package/phase14_2x2_descriptor_embedding_manifest.csv"
CZECH_PAIRS = PROJECT_ROOT / "outputs/phase15/evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv"
BOBCAT_PAIRS = PROJECT_ROOT / "outputs/phase15/wild_urban_transfer_stress/phase15e_bobcat_evidence_routed_review_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/strong_model_benchmark"
IMAGE_OUTPUT = OUTPUT_DIR / "phase16_strong_model_benchmark_manifest.csv"
PAIR_OUTPUT = OUTPUT_DIR / "phase16_strong_model_pair_contract.csv"
README = OUTPUT_DIR / "README.md"
AUDIT = OUTPUT_DIR / "phase16_strong_model_benchmark_audit.json"
MAX_PAIRS_PER_DATASET = 50_000

IMAGE_COLUMNS = [
    "phase14_image_evidence_id",
    "image_path",
    "image_path_relative",
    "source_quadrant",
    "environment_axis",
    "species_axis",
    "evidence_axis",
    "image_exists",
]

PAIR_COLUMNS = [
    "query_image_evidence_id",
    "candidate_image_evidence_id",
    "query_image_path",
    "candidate_image_path",
    "descriptor_similarity",
    "same_identity",
    "primary_failure_reason",
]


def _read_images() -> pd.DataFrame:
    header = pd.read_csv(IMAGE_INPUT, nrows=0)
    columns = [column for column in IMAGE_COLUMNS if column in header.columns]
    required = {"phase14_image_evidence_id", "image_path"}
    missing = sorted(required - set(columns))
    if missing:
        raise ValueError(f"Missing required image manifest columns: {missing}")
    return pd.read_csv(IMAGE_INPUT, usecols=columns, low_memory=False).drop_duplicates()


def _read_pair_contract(path: Path, dataset: str) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0)
    columns = [column for column in PAIR_COLUMNS if column in header.columns]
    required = {
        "query_image_evidence_id",
        "candidate_image_evidence_id",
        "query_image_path",
        "candidate_image_path",
        "descriptor_similarity",
    }
    missing = sorted(required - set(columns))
    if missing:
        raise ValueError(f"Missing required pair columns in {path}: {missing}")
    pairs = pd.read_csv(path, usecols=columns, low_memory=False)
    pairs["descriptor_similarity"] = pd.to_numeric(
        pairs["descriptor_similarity"], errors="coerce"
    )
    pairs = pairs.sort_values("descriptor_similarity", ascending=False).head(
        MAX_PAIRS_PER_DATASET
    )
    pairs = pairs.copy()
    pairs.insert(0, "phase16_dataset", dataset)
    for column in PAIR_COLUMNS:
        if column not in pairs.columns:
            pairs[column] = ""
    return pairs[["phase16_dataset", *PAIR_COLUMNS]]


def _write_readme() -> None:
    README.write_text(
        "# Phase 16 Strong-Model Benchmark Package\n\n"
        "Purpose: provide a stable image and pair contract for WildFusion, local "
        "feature matching, or another strong animal Re-ID benchmark.\n\n"
        "This package is an interface only. It does not validate identity and it "
        "does not claim PF-ERI beats any strong model until returned scores are "
        "available.\n\n"
        "Required return columns for pair-level benchmark output:\n\n"
        "```text\n"
        "phase16_dataset\n"
        "query_image_evidence_id\n"
        "candidate_image_evidence_id\n"
        "strong_model_name\n"
        "strong_model_score\n"
        "strong_model_rank\n"
        "strong_model_notes\n"
        "```\n",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    images = _read_images()
    images.to_csv(IMAGE_OUTPUT, index=False)

    pair_contract = pd.concat(
        [
            _read_pair_contract(CZECH_PAIRS, "czechlynx_known_id"),
            _read_pair_contract(BOBCAT_PAIRS, "bobcat_transfer_stress"),
        ],
        ignore_index=True,
    )
    pair_contract.to_csv(PAIR_OUTPUT, index=False)
    _write_readme()

    audit = {
        "image_input": str(IMAGE_INPUT),
        "czech_pair_input": str(CZECH_PAIRS),
        "bobcat_pair_input": str(BOBCAT_PAIRS),
        "image_rows": int(len(images)),
        "pair_rows": int(len(pair_contract)),
        "max_pairs_per_dataset": MAX_PAIRS_PER_DATASET,
        "image_output": str(IMAGE_OUTPUT),
        "pair_output": str(PAIR_OUTPUT),
        "claim_boundary": (
            "strong-model package only; final claims require returned "
            "strong-model scores"
        ),
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(
        "PASS phase16 strong-model benchmark package "
        f"image_rows={len(images)} pair_rows={len(pair_contract)}"
    )
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
