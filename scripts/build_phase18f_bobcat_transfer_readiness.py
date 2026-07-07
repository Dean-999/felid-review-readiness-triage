#!/usr/bin/env python3
"""Apply Phase18F Bobcat unlabeled transfer-readiness scoring."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.phase18_pipeline_utils import (
        PHASE18B_EMBEDDINGS,
        PHASE18B_MANIFEST,
        PHASE18F_DIR,
        aspect_compatibility,
        clamp01,
        image_quality_from_row,
        now_utc,
        project_relative,
        read_csv,
        size_compatibility,
        to_float,
        write_csv,
        write_json,
    )
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import (
        PHASE18B_EMBEDDINGS,
        PHASE18B_MANIFEST,
        PHASE18F_DIR,
        aspect_compatibility,
        clamp01,
        image_quality_from_row,
        now_utc,
        project_relative,
        read_csv,
        size_compatibility,
        to_float,
        write_csv,
        write_json,
    )


PAIR_COLUMNS = [
    "pair_id",
    "query_image_id",
    "candidate_image_id",
    "candidate_rank_descriptor",
    "descriptor_similarity",
    "query_image_quality_score",
    "candidate_image_quality_score",
    "weakest_image_quality_score",
    "pair_geometry_score",
    "descriptor_evidence_conflict_score",
    "transfer_readiness_score",
    "transfer_readiness_route",
    "claim_boundary",
]

IMAGE_COLUMNS = [
    "phase18_image_id",
    "mean_topk_transfer_readiness_score",
    "max_topk_transfer_readiness_score",
    "review_ready_neighbor_count",
    "non_comparable_neighbor_count",
    "transfer_readiness_route",
    "claim_boundary",
]


def route(score: float, conflict: float) -> str:
    if score >= 0.72 and conflict <= 0.30:
        return "review_ready_transfer_candidate"
    if score >= 0.55:
        return "manual_review_transfer_candidate"
    if score >= 0.38:
        return "defer_low_evidence_transfer_candidate"
    return "non_comparable_transfer_candidate"


def build_phase18f(manifest_csv: Path, embeddings_npy: Path, output_dir: Path, top_k: int) -> dict[str, Any]:
    manifest = read_csv(manifest_csv)
    embeddings = np.load(embeddings_npy).astype(np.float32)
    bobcat_rows = [row for row in manifest if row["species"] == "bobcat"]
    bobcat_embedding_rows = np.asarray([int(row["embedding_row"]) for row in bobcat_rows], dtype=int)
    bobcat_embeddings = embeddings[bobcat_embedding_rows]
    pair_rows: list[dict[str, Any]] = []
    image_rows: list[dict[str, Any]] = []
    for qpos, query in enumerate(bobcat_rows):
        scores = bobcat_embeddings @ bobcat_embeddings[qpos]
        scores[qpos] = -np.inf
        if len(scores) <= top_k:
            ranked = np.argsort(-scores)
        else:
            rough = np.argpartition(-scores, top_k)[:top_k]
            ranked = rough[np.argsort(-scores[rough])]
        query_quality = image_quality_from_row(query)
        per_query_scores: list[float] = []
        routes: list[str] = []
        for rank, cpos in enumerate(ranked, start=1):
            candidate = bobcat_rows[int(cpos)]
            candidate_quality = image_quality_from_row(candidate)
            weakest = min(query_quality, candidate_quality)
            geometry = 0.55 * size_compatibility(
                to_float(query.get("min_dimension", "")),
                to_float(candidate.get("min_dimension", "")),
            ) + 0.45 * aspect_compatibility(
                to_float(query.get("aspect_ratio", "")),
                to_float(candidate.get("aspect_ratio", "")),
            )
            similarity = float(scores[int(cpos)])
            conflict = clamp01(similarity - (0.65 * weakest + 0.35 * geometry))
            readiness = clamp01(0.44 * weakest + 0.26 * geometry + 0.20 * similarity + 0.10 * (1.0 - conflict))
            pair_route = route(readiness, conflict)
            per_query_scores.append(readiness)
            routes.append(pair_route)
            pair_rows.append(
                {
                    "pair_id": f"phase18f_{query['phase18_image_id']}__{candidate['phase18_image_id']}",
                    "query_image_id": query["phase18_image_id"],
                    "candidate_image_id": candidate["phase18_image_id"],
                    "candidate_rank_descriptor": rank,
                    "descriptor_similarity": round(similarity, 8),
                    "query_image_quality_score": round(query_quality, 6),
                    "candidate_image_quality_score": round(candidate_quality, 6),
                    "weakest_image_quality_score": round(weakest, 6),
                    "pair_geometry_score": round(geometry, 6),
                    "descriptor_evidence_conflict_score": round(conflict, 6),
                    "transfer_readiness_score": round(readiness, 6),
                    "transfer_readiness_route": pair_route,
                    "claim_boundary": "Bobcat transfer-readiness only; no identity label or accuracy claim.",
                }
            )
        ready_count = sum(item == "review_ready_transfer_candidate" for item in routes)
        noncomp_count = sum(item == "non_comparable_transfer_candidate" for item in routes)
        mean_score = float(np.mean(per_query_scores)) if per_query_scores else 0.0
        max_score = float(np.max(per_query_scores)) if per_query_scores else 0.0
        image_route = "review_ready_image" if ready_count >= 2 else "manual_review_image" if mean_score >= 0.55 else "defer_image"
        image_rows.append(
            {
                "phase18_image_id": query["phase18_image_id"],
                "mean_topk_transfer_readiness_score": round(mean_score, 6),
                "max_topk_transfer_readiness_score": round(max_score, 6),
                "review_ready_neighbor_count": ready_count,
                "non_comparable_neighbor_count": noncomp_count,
                "transfer_readiness_route": image_route,
                "claim_boundary": "Bobcat image readiness summary only; no identity validation.",
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    pair_csv = output_dir / "phase18f_bobcat_transfer_readiness_pairs.csv"
    image_csv = output_dir / "phase18f_bobcat_transfer_readiness_images.csv"
    write_csv(pair_csv, pair_rows, PAIR_COLUMNS)
    write_csv(image_csv, image_rows, IMAGE_COLUMNS)
    audit = {
        "built_at_utc": now_utc(),
        "input_manifest": project_relative(manifest_csv),
        "input_embeddings": project_relative(embeddings_npy),
        "pair_csv": project_relative(pair_csv),
        "image_csv": project_relative(image_csv),
        "bobcat_image_count": len(bobcat_rows),
        "top_k": top_k,
        "pair_rows": len(pair_rows),
        "pair_route_counts": dict(sorted(Counter(row["transfer_readiness_route"] for row in pair_rows).items())),
        "image_route_counts": dict(sorted(Counter(row["transfer_readiness_route"] for row in image_rows).items())),
        "claim_boundary": "Unlabeled Bobcat transfer-readiness only; no same/different or individual identity claim.",
    }
    write_json(output_dir / "phase18f_bobcat_transfer_readiness_audit.json", audit)
    (output_dir / "README.md").write_text(
        "# Phase18F Bobcat Transfer Readiness\n\n"
        "Applies the Phase18 local-control evidence logic to Bobcat nearest-neighbor "
        "pairs without using or claiming individual identity labels.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-csv", type=Path, default=PHASE18B_MANIFEST)
    parser.add_argument("--embeddings-npy", type=Path, default=PHASE18B_EMBEDDINGS)
    parser.add_argument("--output-dir", type=Path, default=PHASE18F_DIR)
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18f(args.manifest_csv, args.embeddings_npy, args.output_dir, args.top_k)
    print("PASS phase18f bobcat transfer readiness")
    print(f"pair_rows={audit['pair_rows']}")
    print(f"image_route_counts={audit['image_route_counts']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
