#!/usr/bin/env python3
"""Add descriptor-evidence conflict fields to Phase 14 pair comparability.

The script requires descriptor embeddings for every image referenced by the
pair table. If coverage is incomplete, it writes a blocked audit and exits
without producing a partial scientific result.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALGO_DIR = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs"
PAIR_TABLE = ALGO_DIR / "phase14_2x2_pair_comparability_table.csv"
EMBEDDINGS = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_conflict"
OUT_TABLE = OUT_DIR / "phase14_2x2_descriptor_evidence_conflict_table.csv"
OUT_SUMMARY = OUT_DIR / "phase14_2x2_descriptor_evidence_conflict_summary.csv"
OUT_AUDIT = OUT_DIR / "phase14_2x2_descriptor_evidence_conflict_audit.json"

REQUIRED_EMBEDDING_COLUMNS = {
    "phase14_image_evidence_id",
    "embedding_model",
    "embedding_dim",
    "embedding_vector",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def parse_vector(value: object) -> np.ndarray:
    text = str(value).strip()
    try:
        vector = np.asarray(json.loads(text), dtype=np.float32)
    except Exception:
        vector = np.asarray(ast.literal_eval(text), dtype=np.float32)
    if vector.ndim != 1 or vector.size == 0 or not np.isfinite(vector).all():
        raise ValueError("Malformed embedding vector")
    return vector


def load_embeddings(path: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    frame = pd.read_csv(path, low_memory=False)
    missing = REQUIRED_EMBEDDING_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    if frame["phase14_image_evidence_id"].duplicated().any():
        raise ValueError(f"{path} contains duplicate phase14_image_evidence_id values")
    vectors = {}
    dims = set()
    for _, row in frame.iterrows():
        vector = parse_vector(row["embedding_vector"])
        norm = float(np.linalg.norm(vector))
        if norm <= 0 or not np.isfinite(norm):
            raise ValueError(f"Zero or invalid embedding vector for {row['phase14_image_evidence_id']}")
        vector = vector / norm
        vectors[str(row["phase14_image_evidence_id"])] = vector.astype(np.float32)
        dims.add(int(vector.size))
    if len(dims) != 1:
        raise ValueError(f"Mixed embedding dimensions detected: {sorted(dims)}")
    return frame, vectors


def coverage_audit(pair_table: pd.DataFrame, embedding_ids: set[str], embeddings_path: Path) -> dict[str, Any]:
    needed = set(pair_table["query_image_evidence_id"].astype(str)) | set(pair_table["candidate_image_evidence_id"].astype(str))
    missing = sorted(needed - embedding_ids)
    return {
        "pair_table": rel(PAIR_TABLE),
        "embeddings": rel(embeddings_path),
        "needed_unique_images": int(len(needed)),
        "available_embedding_images": int(len(embedding_ids)),
        "covered_needed_images": int(len(needed & embedding_ids)),
        "missing_needed_images": int(len(missing)),
        "missing_examples": missing[:20],
        "coverage_complete": len(missing) == 0,
    }


def percentile_by_group(series: pd.Series) -> pd.Series:
    return series.rank(method="average", pct=True).fillna(0.0).clip(0, 1)


def conflict_band(score: float) -> str:
    if score >= 0.75:
        return "high_conflict"
    if score >= 0.50:
        return "medium_conflict"
    if score >= 0.25:
        return "low_conflict"
    return "minimal_conflict"


def descriptor_decision(pair_score: float, similarity_pct: float, conflict: float) -> str:
    if conflict >= 0.75:
        return "defer_descriptor_evidence_conflict"
    if similarity_pct >= 0.90 and pair_score >= 0.70:
        return "descriptor_supported_review_candidate"
    if similarity_pct >= 0.90 and pair_score < 0.40:
        return "defer_high_similarity_low_evidence"
    if pair_score < 0.30:
        return "species_level_or_non_comparable"
    return "review_or_rank_by_descriptor"


def add_conflict(pair_table: pd.DataFrame, vectors: dict[str, np.ndarray], embedding_model: str) -> pd.DataFrame:
    rows = []
    for qid, cid in zip(pair_table["query_image_evidence_id"].astype(str), pair_table["candidate_image_evidence_id"].astype(str)):
        rows.append(float(np.dot(vectors[qid], vectors[cid])))
    out = pair_table.copy()
    out["descriptor_model"] = embedding_model
    out["descriptor_similarity"] = np.asarray(rows, dtype=np.float32)
    out["descriptor_similarity_percentile_global"] = percentile_by_group(out["descriptor_similarity"])
    out["descriptor_similarity_percentile_block"] = out.groupby("pair_block")["descriptor_similarity"].transform(percentile_by_group)
    pair_score = pd.to_numeric(out["pair_comparability_score"], errors="coerce").fillna(0.0).clip(0, 1)
    block_pct = pd.to_numeric(out["descriptor_similarity_percentile_block"], errors="coerce").fillna(0.0).clip(0, 1)
    global_pct = pd.to_numeric(out["descriptor_similarity_percentile_global"], errors="coerce").fillna(0.0).clip(0, 1)
    out["descriptor_evidence_conflict_score"] = (block_pct * (1.0 - pair_score)).clip(0, 1)
    out["descriptor_evidence_conflict_global_score"] = (global_pct * (1.0 - pair_score)).clip(0, 1)
    out["descriptor_evidence_support_score"] = (block_pct * pair_score).clip(0, 1)
    out["descriptor_conflict_band"] = out["descriptor_evidence_conflict_score"].map(conflict_band)
    out["descriptor_evidence_decision"] = [
        descriptor_decision(float(pair), float(pct), float(conflict))
        for pair, pct, conflict in zip(pair_score, block_pct, out["descriptor_evidence_conflict_score"])
    ]
    if "same_identity" in out.columns:
        out["known_false_candidate"] = np.where(out["same_identity"].eq("no"), "yes", np.where(out["same_identity"].eq("yes"), "no", "unknown"))
    return out


def summarize(table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = table.groupby(["species_axis", "pair_block", "pair_sampling_role"], dropna=False)
    for keys, frame in grouped:
        known_false = frame["known_false_candidate"].eq("yes") if "known_false_candidate" in frame else pd.Series(False, index=frame.index)
        high_conflict = frame["descriptor_conflict_band"].eq("high_conflict")
        rows.append(
            {
                "species_axis": keys[0],
                "pair_block": keys[1],
                "pair_sampling_role": keys[2],
                "pair_count": int(len(frame)),
                "mean_descriptor_similarity": float(frame["descriptor_similarity"].mean()),
                "mean_pair_comparability": float(frame["pair_comparability_score"].mean()),
                "mean_conflict_score": float(frame["descriptor_evidence_conflict_score"].mean()),
                "high_conflict_count": int(high_conflict.sum()),
                "high_conflict_rate": float(high_conflict.mean()) if len(frame) else float("nan"),
                "known_false_candidate_count": int(known_false.sum()),
                "known_false_candidate_high_conflict_count": int((known_false & high_conflict).sum()),
                "decision_counts": json.dumps(
                    {str(k): int(v) for k, v in frame["descriptor_evidence_decision"].value_counts().sort_index().items()},
                    sort_keys=True,
                ),
            }
        )
    return pd.DataFrame(rows)


def write_blocked_audit(args: argparse.Namespace, reason: str, details: dict[str, Any]) -> None:
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "blocked",
        "reason": reason,
        "details": details,
        "scientific_boundary": "descriptor-evidence conflict requires complete descriptor coverage for the pair table",
    }
    args.audit.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-table", type=Path, default=PAIR_TABLE)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS)
    parser.add_argument("--output", type=Path, default=OUT_TABLE)
    parser.add_argument("--summary", type=Path, default=OUT_SUMMARY)
    parser.add_argument("--audit", type=Path, default=OUT_AUDIT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.pair_table.exists():
        raise FileNotFoundError(f"Missing pair comparability table: {args.pair_table}")
    pair_table = pd.read_csv(args.pair_table, low_memory=False)
    if not args.embeddings.exists():
        write_blocked_audit(
            args,
            "missing_descriptor_embeddings",
            {
                "pair_table": rel(args.pair_table),
                "expected_embeddings": rel(args.embeddings),
                "pair_rows": int(len(pair_table)),
                "unique_images_needed": int(
                    len(set(pair_table["query_image_evidence_id"].astype(str)) | set(pair_table["candidate_image_evidence_id"].astype(str)))
                ),
            },
        )
        return 2
    embedding_frame, vectors = load_embeddings(args.embeddings)
    coverage = coverage_audit(pair_table, set(vectors), args.embeddings)
    if not coverage["coverage_complete"]:
        write_blocked_audit(args, "incomplete_descriptor_embedding_coverage", coverage)
        return 2

    model_values = sorted(embedding_frame["embedding_model"].astype(str).unique())
    embedding_model = model_values[0] if len(model_values) == 1 else "mixed_models"
    table = add_conflict(pair_table, vectors, embedding_model)
    summary = summarize(table)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    audit = {
        "status": "complete",
        "inputs": {"pair_table": rel(args.pair_table), "embeddings": rel(args.embeddings)},
        "outputs": {"table": rel(args.output), "summary": rel(args.summary), "audit": rel(args.audit)},
        "row_count": int(len(table)),
        "column_count": int(len(table.columns)),
        "embedding_model": embedding_model,
        "coverage": coverage,
        "descriptor_conflict_band_counts": {
            str(k): int(v) for k, v in table["descriptor_conflict_band"].value_counts().sort_index().items()
        },
        "scientific_boundary": {
            "bobcat_identity_validation": "not_available_without_verified_individual_ids",
            "czechlynx_identity_validation": "available_for known positive/negative pair labels",
        },
    }
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
