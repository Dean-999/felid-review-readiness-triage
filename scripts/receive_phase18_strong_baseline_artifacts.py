#!/usr/bin/env python3
"""Receive and audit external Phase18 strong-descriptor artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.phase18_pipeline_utils import (
        PHASE18A_MANIFEST,
        PROJECT_ROOT,
        l2_normalize,
        now_utc,
        project_relative,
        read_csv,
        write_csv,
        write_json,
    )
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import (
        PHASE18A_MANIFEST,
        PROJECT_ROOT,
        l2_normalize,
        now_utc,
        project_relative,
        read_csv,
        write_csv,
        write_json,
    )


STRONG_ROOT = PROJECT_ROOT / "outputs/phase18/phase18_strong_baselines"

OUTPUT_COLUMNS = [
    "embedding_row",
    "phase18_image_id",
    "species",
    "freeze_rank",
    "modeling_role",
    "train_eval_eligible",
    "has_known_identity",
    "identity_label",
    "frozen_image_path",
    "decode_width",
    "decode_height",
    "megapixels",
    "min_dimension",
    "max_dimension",
    "aspect_ratio",
    "sha256",
    "descriptor_name",
    "descriptor_dim",
    "descriptor_status",
    "claim_boundary",
]

REQUIRED_EMBEDDING_COLUMNS = {
    "phase18_image_id",
    "descriptor_name",
    "embedding_row",
    "embedding_dim",
    "sha256",
}

REQUIRED_PAIR_SCORE_COLUMNS = {
    "query_image_id",
    "candidate_image_id",
    "descriptor_name",
    "strong_descriptor_similarity",
    "strong_descriptor_rank",
}


def require_columns(rows: list[dict[str, str]], required: set[str], label: str) -> None:
    if not rows:
        raise ValueError(f"{label} has 0 rows")
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")


def duplicate_values(rows: list[dict[str, str]], column: str) -> list[str]:
    counts = Counter(row[column] for row in rows)
    return sorted(value for value, count in counts.items() if count > 1)


def validate_pair_scores(
    pair_rows: list[dict[str, str]],
    phase18a_by_id: dict[str, dict[str, str]],
    descriptor_name: str,
) -> None:
    require_columns(pair_rows, REQUIRED_PAIR_SCORE_COLUMNS, "pair score artifact")
    for idx, row in enumerate(pair_rows, start=2):
        if row["descriptor_name"] != descriptor_name:
            raise ValueError(f"pair score row {idx} descriptor_name mismatch")
        query = phase18a_by_id.get(row["query_image_id"])
        candidate = phase18a_by_id.get(row["candidate_image_id"])
        if query is None or candidate is None:
            raise ValueError(f"pair score row {idx} references unknown image id")
        if row["query_image_id"] == row["candidate_image_id"]:
            raise ValueError(f"pair score row {idx} is a self-pair")
        if query["species"] != "czechlynx" or candidate["species"] != "czechlynx":
            raise ValueError("pair score artifact must contain CzechLynx known-ID pairs only")
        if query["has_known_identity"] != "yes" or candidate["has_known_identity"] != "yes":
            raise ValueError("pair score artifact contains a CzechLynx row without known identity")


def build_manifest_rows(
    phase18a_rows: list[dict[str, str]],
    embedding_rows: list[dict[str, str]],
    embeddings: np.ndarray,
    descriptor_name: str,
) -> list[dict[str, Any]]:
    phase18a_by_id = {row["phase18_image_id"]: row for row in phase18a_rows}
    if len(phase18a_by_id) != len(phase18a_rows):
        raise ValueError("Phase18A manifest has duplicate phase18_image_id values")
    require_columns(embedding_rows, REQUIRED_EMBEDDING_COLUMNS, "embedding manifest")
    duplicates = duplicate_values(embedding_rows, "phase18_image_id")
    if duplicates:
        raise ValueError(f"embedding manifest has duplicate phase18_image_id values: {duplicates[:5]}")
    embedding_by_id = {row["phase18_image_id"]: row for row in embedding_rows}
    expected_ids = set(phase18a_by_id)
    returned_ids = set(embedding_by_id)
    missing = sorted(expected_ids - returned_ids)
    extra = sorted(returned_ids - expected_ids)
    if missing or extra:
        raise ValueError(f"embedding manifest id coverage mismatch: missing={len(missing)} extra={len(extra)}")
    if len(embedding_rows) != embeddings.shape[0]:
        raise ValueError("embedding manifest row count does not match embeddings row count")

    output_rows: list[dict[str, Any]] = []
    seen_embedding_rows: set[int] = set()
    for phase_row in phase18a_rows:
        returned = embedding_by_id[phase_row["phase18_image_id"]]
        if returned["descriptor_name"] != descriptor_name:
            raise ValueError(f"descriptor_name mismatch for {phase_row['phase18_image_id']}")
        if returned["sha256"] != phase_row["sha256"]:
            raise ValueError(f"sha256 mismatch for {phase_row['phase18_image_id']}")
        if phase_row["species"] == "bobcat":
            if returned.get("identity_label", "") or returned.get("same_identity", ""):
                raise ValueError("Bobcat strong artifact must not contain identity or same/different labels")
        embedding_row = int(returned["embedding_row"])
        embedding_dim = int(returned["embedding_dim"])
        if embedding_row < 0 or embedding_row >= embeddings.shape[0]:
            raise ValueError(f"embedding_row out of range for {phase_row['phase18_image_id']}")
        if embedding_row in seen_embedding_rows:
            raise ValueError(f"duplicate embedding_row value: {embedding_row}")
        seen_embedding_rows.add(embedding_row)
        if embedding_dim != embeddings.shape[1]:
            raise ValueError(f"embedding_dim mismatch for {phase_row['phase18_image_id']}")
        output_rows.append(
            {
                "embedding_row": embedding_row,
                "phase18_image_id": phase_row["phase18_image_id"],
                "species": phase_row["species"],
                "freeze_rank": phase_row["freeze_rank"],
                "modeling_role": phase_row["modeling_role"],
                "train_eval_eligible": phase_row["train_eval_eligible"],
                "has_known_identity": phase_row["has_known_identity"],
                "identity_label": phase_row["identity_label"],
                "frozen_image_path": phase_row["frozen_image_path"],
                "decode_width": phase_row["decode_width"],
                "decode_height": phase_row["decode_height"],
                "megapixels": phase_row["megapixels"],
                "min_dimension": phase_row["min_dimension"],
                "max_dimension": phase_row["max_dimension"],
                "aspect_ratio": phase_row["aspect_ratio"],
                "sha256": phase_row["sha256"],
                "descriptor_name": descriptor_name,
                "descriptor_dim": embedding_dim,
                "descriptor_status": "STRONG_BASELINE_EXTERNAL_ARTIFACT",
                "claim_boundary": (
                    "Strong descriptor artifact for upstream candidate generation; "
                    "PF-ERI pair-level review utility is evaluated downstream."
                ),
            }
        )
    return output_rows


def receive_phase18_strong_baseline_artifacts(
    descriptor_name: str,
    embedding_manifest: Path,
    embeddings_npy: Path,
    pair_scores: Path,
    output_dir: Path,
    phase18a_manifest: Path = PHASE18A_MANIFEST,
) -> dict[str, Any]:
    phase18a_rows = read_csv(phase18a_manifest)
    embedding_rows = read_csv(embedding_manifest)
    pair_rows = read_csv(pair_scores)
    embeddings = np.load(embeddings_npy).astype(np.float32)
    if embeddings.ndim != 2:
        raise ValueError("embeddings artifact must be a 2D matrix")
    manifest_rows = build_manifest_rows(phase18a_rows, embedding_rows, embeddings, descriptor_name)
    phase18a_by_id = {row["phase18_image_id"]: row for row in phase18a_rows}
    validate_pair_scores(pair_rows, phase18a_by_id, descriptor_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_manifest = output_dir / "phase18_strong_embedding_manifest.csv"
    output_embeddings = output_dir / "phase18_strong_embeddings.npy"
    output_pair_scores = output_dir / "phase18_strong_pair_scores.csv"
    write_csv(output_manifest, manifest_rows, OUTPUT_COLUMNS)
    np.save(output_embeddings, l2_normalize(embeddings))
    write_csv(output_pair_scores, pair_rows, list(pair_rows[0].keys()))

    audit = {
        "built_at_utc": now_utc(),
        "descriptor_name": descriptor_name,
        "phase18a_manifest": project_relative(phase18a_manifest),
        "input_embedding_manifest": project_relative(embedding_manifest),
        "input_embeddings_npy": project_relative(embeddings_npy),
        "input_pair_scores": project_relative(pair_scores),
        "output_manifest": project_relative(output_manifest),
        "output_embeddings": project_relative(output_embeddings),
        "output_pair_scores": project_relative(output_pair_scores),
        "embedding_rows": len(manifest_rows),
        "embedding_shape": list(embeddings.shape),
        "pair_score_rows": len(pair_rows),
        "species_counts": dict(sorted(Counter(row["species"] for row in manifest_rows).items())),
        "bobcat_identity_label_violations": 0,
        "status": "PASS",
        "claim_boundary": (
            "Strong descriptor artifacts are accepted only as upstream candidate "
            "generation controls. They do not create Bobcat identity claims."
        ),
    }
    write_json(output_dir / "phase18_strong_baseline_audit.json", audit)
    (output_dir / "README.md").write_text(
        f"# Phase18 Strong Baseline: {descriptor_name}\n\n"
        "External strong descriptor artifacts passed manifest, checksum, species, "
        "and Bobcat claim-boundary audits.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor-name", required=True)
    parser.add_argument("--embedding-manifest", type=Path, required=True)
    parser.add_argument("--embeddings-npy", type=Path, required=True)
    parser.add_argument("--pair-scores", type=Path, required=True)
    parser.add_argument("--phase18a-manifest", type=Path, default=PHASE18A_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or STRONG_ROOT / args.descriptor_name
    audit = receive_phase18_strong_baseline_artifacts(
        descriptor_name=args.descriptor_name,
        embedding_manifest=args.embedding_manifest,
        embeddings_npy=args.embeddings_npy,
        pair_scores=args.pair_scores,
        output_dir=output_dir,
        phase18a_manifest=args.phase18a_manifest,
    )
    print("PASS phase18 strong baseline artifact receiver")
    print(f"descriptor_name={audit['descriptor_name']}")
    print(f"embedding_rows={audit['embedding_rows']}")
    print(f"pair_score_rows={audit['pair_score_rows']}")
    print(f"WROTE {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
