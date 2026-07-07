#!/usr/bin/env python3
"""Build Phase18D PF-ERI 2.0 pair features from CzechLynx pair contracts."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.phase18_pipeline_utils import (
        PHASE18C_PAIRS,
        PHASE18D_DIR,
        PHASE18D_FEATURES,
        aspect_compatibility,
        clamp01,
        image_quality_from_row,
        now_utc,
        percentile_ranks,
        project_relative,
        read_csv,
        size_compatibility,
        to_float,
        write_csv,
        write_json,
    )
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import (
        PHASE18C_PAIRS,
        PHASE18D_DIR,
        PHASE18D_FEATURES,
        aspect_compatibility,
        clamp01,
        image_quality_from_row,
        now_utc,
        percentile_ranks,
        project_relative,
        read_csv,
        size_compatibility,
        to_float,
        write_csv,
        write_json,
    )


OUTPUT_COLUMNS = [
    "pair_id",
    "descriptor_name",
    "query_image_id",
    "candidate_image_id",
    "same_identity",
    "candidate_rank_descriptor",
    "descriptor_similarity",
    "descriptor_similarity_percentile",
    "query_split_role",
    "split_id",
    "query_image_quality_score",
    "candidate_image_quality_score",
    "weakest_image_quality_score",
    "pair_size_compatibility_score",
    "pair_aspect_compatibility_score",
    "pair_geometry_score",
    "descriptor_evidence_conflict_score",
    "pf_eri_admissibility_score",
    "pf_eri_review_score",
    "pf_eri_route",
    "claim_boundary",
]


def route_for_score(admissibility: float, conflict: float) -> str:
    if admissibility >= 0.78 and conflict <= 0.20:
        return "accept_review_ready"
    if admissibility >= 0.58 and conflict <= 0.45:
        return "review"
    if admissibility >= 0.40:
        return "defer_low_evidence"
    return "non_comparable"


def enrich_pair(row: dict[str, str], percentile: float) -> dict[str, Any]:
    query_quality = image_quality_from_row(
        {
            "min_dimension": row.get("query_min_dimension", ""),
            "megapixels": "",
        }
    )
    candidate_quality = image_quality_from_row(
        {
            "min_dimension": row.get("candidate_min_dimension", ""),
            "megapixels": "",
        }
    )
    weakest = min(query_quality, candidate_quality)
    size_score = size_compatibility(
        to_float(row.get("query_min_dimension", "")),
        to_float(row.get("candidate_min_dimension", "")),
    )
    aspect_score = aspect_compatibility(
        to_float(row.get("query_aspect_ratio", "")),
        to_float(row.get("candidate_aspect_ratio", "")),
    )
    geometry = round(0.55 * size_score + 0.45 * aspect_score, 6)
    conflict = round(clamp01(percentile - (0.65 * weakest + 0.35 * geometry)), 6)
    admissibility = round(
        clamp01(0.42 * weakest + 0.28 * geometry + 0.20 * (1.0 - conflict) + 0.10 * percentile),
        6,
    )
    review_score = round(clamp01(0.62 * percentile + 0.38 * admissibility - 0.20 * conflict), 6)
    return {
        **row,
        "descriptor_similarity_percentile": round(percentile, 6),
        "query_image_quality_score": query_quality,
        "candidate_image_quality_score": candidate_quality,
        "weakest_image_quality_score": round(weakest, 6),
        "pair_size_compatibility_score": size_score,
        "pair_aspect_compatibility_score": aspect_score,
        "pair_geometry_score": geometry,
        "descriptor_evidence_conflict_score": conflict,
        "pf_eri_admissibility_score": admissibility,
        "pf_eri_review_score": review_score,
        "pf_eri_route": route_for_score(admissibility, conflict),
        "claim_boundary": "PF-ERI pair feature table; descriptor-control baseline only until strong embeddings are added.",
    }


def build_phase18d(input_pairs: Path, output_dir: Path) -> dict[str, Any]:
    rows = read_csv(input_pairs)
    similarities = [to_float(row.get("descriptor_similarity", "")) for row in rows]
    percentiles = percentile_ranks(similarities)
    enriched = [enrich_pair(row, pct) for row, pct in zip(rows, percentiles)]
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / PHASE18D_FEATURES.name, enriched, OUTPUT_COLUMNS)
    same = [row for row in enriched if row["same_identity"] == "yes"]
    different = [row for row in enriched if row["same_identity"] == "no"]
    audit = {
        "built_at_utc": now_utc(),
        "input_pairs": project_relative(input_pairs),
        "output_features": project_relative(output_dir / PHASE18D_FEATURES.name),
        "pair_rows": len(enriched),
        "same_identity_pairs": len(same),
        "different_identity_pairs": len(different),
        "route_counts": dict(sorted(Counter(row["pf_eri_route"] for row in enriched).items())),
        "mean_pf_eri_admissibility_same": float(np.mean([to_float(row["pf_eri_admissibility_score"]) for row in same])) if same else None,
        "mean_pf_eri_admissibility_different": float(np.mean([to_float(row["pf_eri_admissibility_score"]) for row in different])) if different else None,
        "claim_boundary": "Feature engineering only; router evaluation is Phase18E.",
    }
    write_json(output_dir / "phase18d_pf_eri_pair_features_audit.json", audit)
    (output_dir / "README.md").write_text(
        "# Phase18D PF-ERI Pair Features\n\n"
        "Adds admissibility, geometry, conflict, and review-score fields to the "
        "CzechLynx known-ID pair contract.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-pairs", type=Path, default=PHASE18C_PAIRS)
    parser.add_argument("--output-dir", type=Path, default=PHASE18D_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18d(args.input_pairs, args.output_dir)
    print("PASS phase18d pf-eri pair features")
    print(f"pair_rows={audit['pair_rows']}")
    print(f"route_counts={audit['route_counts']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
