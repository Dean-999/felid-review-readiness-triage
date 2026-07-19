#!/usr/bin/env python3
"""Build Phase18C CzechLynx known-ID top-k pair contract."""

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
        PHASE18C_DIR,
        PHASE18C_PAIRS,
        average_precision,
        calibration_role,
        now_utc,
        project_relative,
        read_csv,
        write_csv,
        write_json,
    )
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import (
        PHASE18B_EMBEDDINGS,
        PHASE18B_MANIFEST,
        PHASE18C_DIR,
        PHASE18C_PAIRS,
        average_precision,
        calibration_role,
        now_utc,
        project_relative,
        read_csv,
        write_csv,
        write_json,
    )


OUTPUT_COLUMNS = [
    "pair_id",
    "descriptor_name",
    "query_image_id",
    "candidate_image_id",
    "query_identity_label",
    "candidate_identity_label",
    "same_identity",
    "candidate_rank_descriptor",
    "descriptor_similarity",
    "query_split_role",
    "split_id",
    "query_freeze_rank",
    "candidate_freeze_rank",
    "query_image_quality_score",
    "candidate_image_quality_score",
    "query_min_dimension",
    "candidate_min_dimension",
    "query_aspect_ratio",
    "candidate_aspect_ratio",
    "claim_boundary",
]


def topk_indices(scores: np.ndarray, top_k: int) -> np.ndarray:
    if len(scores) <= top_k:
        return np.argsort(-scores)
    rough = np.argpartition(-scores, top_k)[:top_k]
    return rough[np.argsort(-scores[rough])]


def build_phase18c(manifest_csv: Path, embeddings_npy: Path, output_dir: Path, top_k: int) -> dict[str, Any]:
    manifest = read_csv(manifest_csv)
    embeddings = np.load(embeddings_npy).astype(np.float32)
    czech_rows = [
        row for row in manifest
        if row["species"] == "czechlynx" and row["has_known_identity"] == "yes"
    ]
    if not czech_rows:
        raise ValueError("0 CzechLynx known-ID rows available")
    czech_embedding_rows = np.asarray([int(row["embedding_row"]) for row in czech_rows], dtype=int)
    czech_embeddings = embeddings[czech_embedding_rows]
    rows: list[dict[str, Any]] = []
    ap_values: list[float] = []
    rr_values: list[float] = []
    for qpos, query in enumerate(czech_rows):
        scores = czech_embeddings @ czech_embeddings[qpos]
        scores[qpos] = -np.inf
        ranked = topk_indices(scores, top_k)
        relevance: list[bool] = []
        for rank, cpos in enumerate(ranked, start=1):
            candidate = czech_rows[int(cpos)]
            same = query["identity_label"] == candidate["identity_label"]
            relevance.append(same)
            split_id = int(query["freeze_rank"]) % 5
            rows.append(
                {
                    "pair_id": f"phase18c_{query['phase18_image_id']}__{candidate['phase18_image_id']}",
                    "descriptor_name": query["descriptor_name"],
                    "query_image_id": query["phase18_image_id"],
                    "candidate_image_id": candidate["phase18_image_id"],
                    "query_identity_label": query["identity_label"],
                    "candidate_identity_label": candidate["identity_label"],
                    "same_identity": "yes" if same else "no",
                    "candidate_rank_descriptor": rank,
                    "descriptor_similarity": round(float(scores[int(cpos)]), 8),
                    "query_split_role": calibration_role(query["identity_label"]),
                    "split_id": split_id,
                    "query_freeze_rank": query["freeze_rank"],
                    "candidate_freeze_rank": candidate["freeze_rank"],
                    "query_image_quality_score": "",
                    "candidate_image_quality_score": "",
                    "query_min_dimension": query["min_dimension"],
                    "candidate_min_dimension": candidate["min_dimension"],
                    "query_aspect_ratio": query["aspect_ratio"],
                    "candidate_aspect_ratio": candidate["aspect_ratio"],
                    "claim_boundary": "CzechLynx known-ID pair contract only; Bobcat identity is not evaluated here.",
                }
            )
        ap_values.append(average_precision(relevance))
        positives = [idx for idx, item in enumerate(relevance, start=1) if item]
        rr_values.append(1.0 / positives[0] if positives else 0.0)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / PHASE18C_PAIRS.name, rows, OUTPUT_COLUMNS)
    audit = {
        "built_at_utc": now_utc(),
        "input_manifest": project_relative(manifest_csv),
        "input_embeddings": project_relative(embeddings_npy),
        "output_pairs": project_relative(output_dir / PHASE18C_PAIRS.name),
        "known_id_image_count": len(czech_rows),
        "identity_count": len({row["identity_label"] for row in czech_rows}),
        "top_k": top_k,
        "pair_rows": len(rows),
        "same_identity_pairs": int(sum(row["same_identity"] == "yes" for row in rows)),
        "query_split_role_counts": dict(sorted(Counter(row["query_split_role"] for row in rows).items())),
        "descriptor_control_mAP_at_k": float(np.mean(ap_values)),
        "descriptor_control_MRR_at_k": float(np.mean(rr_values)),
        "claim_boundary": "Metrics are for the local descriptor-control baseline, not a strong Re-ID descriptor.",
    }
    write_json(output_dir / "phase18c_czechlynx_pair_contract_audit.json", audit)
    (output_dir / "README.md").write_text(
        "# Phase18C CzechLynx Pair Contract\n\n"
        "Known-ID CzechLynx top-k candidate pairs generated from Phase18B local "
        "descriptor-control embeddings.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-csv", type=Path, default=PHASE18B_MANIFEST)
    parser.add_argument("--embeddings-npy", type=Path, default=PHASE18B_EMBEDDINGS)
    parser.add_argument("--output-dir", type=Path, default=PHASE18C_DIR)
    parser.add_argument("--top-k", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase18c(args.manifest_csv, args.embeddings_npy, args.output_dir, args.top_k)
    print("PASS phase18c czechlynx pair contract")
    print(f"pair_rows={audit['pair_rows']}")
    print(f"same_identity_pairs={audit['same_identity_pairs']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
