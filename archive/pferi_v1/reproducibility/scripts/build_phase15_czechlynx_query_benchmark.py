#!/usr/bin/env python3
"""Build Phase 15 CzechLynx query-level descriptor benchmark.

This is the first Evidence-Routed Review Layer input. It evaluates fixed
MegaDescriptor retrieval at query level before adding PF-ERI/quality routing.
No model is trained here.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE14_DIR = PROJECT_ROOT / "outputs/phase14"
PHASE15_DIR = PROJECT_ROOT / "outputs/phase15"
IMAGE_EVIDENCE = PHASE14_DIR / "phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv"
EMBEDDINGS = PHASE14_DIR / "phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv"
WORKING_LABELS = [
    PHASE14_DIR
    / "phase14_final_2x2_working_labels/phase14_czechlynx_high_confidence_3000_working_final_labels.csv",
    PHASE14_DIR
    / "phase14_final_2x2_working_labels/phase14_czechlynx_low_evidence_stress_3000_working_final_labels.csv",
]
OUT_DIR = PHASE15_DIR / "query_level_benchmark"
TOPK_TABLE = OUT_DIR / "phase15_czechlynx_query_topk_candidates.csv"
QUERY_SUMMARY = OUT_DIR / "phase15_czechlynx_query_level_summary.csv"
METRICS_TABLE = OUT_DIR / "phase15_czechlynx_descriptor_topk_metrics.csv"
AUDIT_JSON = OUT_DIR / "phase15_czechlynx_query_benchmark_audit.json"
REPORT_MD = OUT_DIR / "phase15_czechlynx_query_benchmark_report.md"

TOP_K = 50
SUMMARY_K = [1, 5, 10, 20, 50]
BLOCK_SIZE = 256

REQUIRED_IMAGE_COLUMNS = {
    "phase14_image_evidence_id",
    "species_axis",
    "evidence_axis",
    "source_quadrant",
    "image_path",
    "image_evidence_utility_score",
    "md_best_confidence",
    "md_area_fraction",
    "detector_geometry_score",
}
REQUIRED_EMBEDDING_COLUMNS = {
    "phase14_image_evidence_id",
    "embedding_model",
    "embedding_dim",
    "embedding_vector",
}
REQUIRED_LABEL_COLUMNS = {
    "identity_label",
    "candidate_source_path",
    "phase14_2x2_quadrant",
}
OPTIONAL_LABEL_COLUMNS = [
    "human_review_bucket",
    "human_review_confidence",
    "md_detected",
    "md_best_confidence",
    "md_area_fraction",
    "md_edge_touch",
    "md_selection_score",
    "md_low_stress_score",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def normalize_path(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    if text.startswith("/"):
        return str(Path(text))
    if text.startswith("data/"):
        return str((PROJECT_ROOT / text).resolve())
    return text


def parse_vector(value: object) -> np.ndarray:
    text = str(value).strip()
    try:
        vector = np.asarray(json.loads(text), dtype=np.float32)
    except Exception:
        vector = np.asarray(ast.literal_eval(text), dtype=np.float32)
    if vector.ndim != 1 or vector.size == 0 or not np.isfinite(vector).all():
        raise ValueError("Malformed embedding vector")
    norm = float(np.linalg.norm(vector))
    if norm <= 0 or not np.isfinite(norm):
        raise ValueError("Zero or invalid embedding vector")
    return (vector / norm).astype(np.float32)


def require_columns(frame: pd.DataFrame, required: set[str], source: Path) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{rel(source)} missing required columns: {missing}")


def load_czechlynx_metadata() -> pd.DataFrame:
    image = pd.read_csv(IMAGE_EVIDENCE, low_memory=False)
    require_columns(image, REQUIRED_IMAGE_COLUMNS, IMAGE_EVIDENCE)
    image = image[image["species_axis"].eq("czechlynx")].copy()
    image["normalized_image_path"] = image["image_path"].map(normalize_path)

    labels = []
    for path in WORKING_LABELS:
        frame = pd.read_csv(path, low_memory=False)
        require_columns(frame, REQUIRED_LABEL_COLUMNS, path)
        frame = frame.copy()
        frame["normalized_image_path"] = frame["candidate_source_path"].map(normalize_path)
        for column in OPTIONAL_LABEL_COLUMNS:
            if column not in frame.columns:
                frame[column] = np.nan
        labels.append(
            frame[
                [
                    "normalized_image_path",
                    "identity_label",
                    "phase14_2x2_quadrant",
                ]
                + OPTIONAL_LABEL_COLUMNS
            ]
        )
    label = pd.concat(labels, ignore_index=True)
    if label["normalized_image_path"].duplicated().any():
        dupes = label.loc[label["normalized_image_path"].duplicated(), "normalized_image_path"].head(10).tolist()
        raise ValueError(f"Duplicate CzechLynx working-final paths: {dupes}")

    out = image.merge(label, on="normalized_image_path", how="left", suffixes=("", "_working"))
    missing_identity = out["identity_label"].isna()
    if missing_identity.any():
        examples = out.loc[missing_identity, "image_path"].head(20).tolist()
        raise ValueError(f"Missing identity labels for {int(missing_identity.sum())} CzechLynx images: {examples}")
    if out["phase14_image_evidence_id"].duplicated().any():
        raise ValueError("Duplicate phase14_image_evidence_id in CzechLynx image evidence table")
    return out


def load_embedding_matrix(ids: list[str]) -> tuple[np.ndarray, str, dict[str, int]]:
    embedding = pd.read_csv(EMBEDDINGS, low_memory=False)
    require_columns(embedding, REQUIRED_EMBEDDING_COLUMNS, EMBEDDINGS)
    if embedding["phase14_image_evidence_id"].duplicated().any():
        raise ValueError("Duplicate phase14_image_evidence_id in embedding table")
    embedding = embedding.set_index("phase14_image_evidence_id")
    missing = [image_id for image_id in ids if image_id not in embedding.index]
    if missing:
        raise ValueError(f"Missing embeddings for {len(missing)} CzechLynx images: {missing[:20]}")

    vectors = [parse_vector(embedding.loc[image_id, "embedding_vector"]) for image_id in ids]
    dims = {int(v.size) for v in vectors}
    if len(dims) != 1:
        raise ValueError(f"Mixed embedding dimensions detected: {sorted(dims)}")
    model_values = embedding.loc[ids, "embedding_model"].dropna().astype(str).unique().tolist()
    model = model_values[0] if model_values else "unknown"
    matrix = np.vstack(vectors).astype(np.float32)
    id_to_index = {image_id: idx for idx, image_id in enumerate(ids)}
    return matrix, model, id_to_index


def rank_candidates(matrix: np.ndarray, metadata: pd.DataFrame) -> pd.DataFrame:
    ids = metadata["phase14_image_evidence_id"].astype(str).tolist()
    identities = metadata["identity_label"].astype(str).to_numpy()
    evidence_axis = metadata["evidence_axis"].astype(str).to_numpy()
    utility = pd.to_numeric(metadata["image_evidence_utility_score"], errors="coerce").to_numpy()
    md_conf = pd.to_numeric(metadata["md_best_confidence"], errors="coerce").to_numpy()
    md_area = pd.to_numeric(metadata["md_area_fraction"], errors="coerce").to_numpy()
    detector_geometry = pd.to_numeric(metadata["detector_geometry_score"], errors="coerce").to_numpy()
    source_quadrant = metadata["source_quadrant"].astype(str).to_numpy()

    rows: list[dict[str, Any]] = []
    n = matrix.shape[0]
    rank_limit = min(TOP_K, max(n - 1, 0))

    for start in range(0, n, BLOCK_SIZE):
        stop = min(start + BLOCK_SIZE, n)
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            sim = matrix[start:stop] @ matrix.T
        if not np.isfinite(sim).all():
            raise ValueError(f"Non-finite descriptor similarities detected for query block {start}:{stop}")
        for local_idx, query_idx in enumerate(range(start, stop)):
            scores = sim[local_idx].copy()
            scores[query_idx] = -np.inf
            if rank_limit == 0:
                continue
            candidate_idx = np.argpartition(-scores, rank_limit - 1)[:rank_limit]
            candidate_idx = candidate_idx[np.argsort(-scores[candidate_idx])]
            q_identity = identities[query_idx]
            q_axis = evidence_axis[query_idx]
            q_utility = float(utility[query_idx]) if np.isfinite(utility[query_idx]) else np.nan
            for rank, cand_idx in enumerate(candidate_idx, start=1):
                c_identity = identities[cand_idx]
                c_axis = evidence_axis[cand_idx]
                c_utility = float(utility[cand_idx]) if np.isfinite(utility[cand_idx]) else np.nan
                weakest = np.nanmin([q_utility, c_utility])
                rows.append(
                    {
                        "query_image_evidence_id": ids[query_idx],
                        "candidate_image_evidence_id": ids[cand_idx],
                        "rank": rank,
                        "descriptor_similarity": float(scores[cand_idx]),
                        "same_identity": "yes" if q_identity == c_identity else "no",
                        "query_identity_label": q_identity,
                        "candidate_identity_label": c_identity,
                        "query_evidence_axis": q_axis,
                        "candidate_evidence_axis": c_axis,
                        "pair_evidence_axis_relation": "same_axis" if q_axis == c_axis else "mixed_axis",
                        "query_source_quadrant": source_quadrant[query_idx],
                        "candidate_source_quadrant": source_quadrant[cand_idx],
                        "query_image_utility_score": q_utility,
                        "candidate_image_utility_score": c_utility,
                        "weakest_image_utility_score": float(weakest) if np.isfinite(weakest) else np.nan,
                        "query_md_confidence": float(md_conf[query_idx]) if np.isfinite(md_conf[query_idx]) else np.nan,
                        "candidate_md_confidence": float(md_conf[cand_idx]) if np.isfinite(md_conf[cand_idx]) else np.nan,
                        "query_md_area_fraction": float(md_area[query_idx]) if np.isfinite(md_area[query_idx]) else np.nan,
                        "candidate_md_area_fraction": float(md_area[cand_idx]) if np.isfinite(md_area[cand_idx]) else np.nan,
                        "query_detector_geometry_score": float(detector_geometry[query_idx])
                        if np.isfinite(detector_geometry[query_idx])
                        else np.nan,
                        "candidate_detector_geometry_score": float(detector_geometry[cand_idx])
                        if np.isfinite(detector_geometry[cand_idx])
                        else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def summarize_queries(topk: pd.DataFrame, metadata: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    identity_counts = metadata["identity_label"].astype(str).value_counts()
    query_meta = metadata[
        [
            "phase14_image_evidence_id",
            "identity_label",
            "evidence_axis",
            "source_quadrant",
            "image_evidence_utility_score",
        ]
    ].copy()
    query_meta["available_positive_gallery_images"] = (
        query_meta["identity_label"].astype(str).map(identity_counts).astype(int) - 1
    )

    summary_rows = []
    for query_id, frame in topk.groupby("query_image_evidence_id", sort=False):
        frame = frame.sort_values("rank")
        positives = frame["same_identity"].eq("yes")
        first_positive_rank = int(frame.loc[positives, "rank"].min()) if positives.any() else 0
        row: dict[str, Any] = {
            "phase14_image_evidence_id": query_id,
            "topk_returned": int(len(frame)),
            "first_positive_rank_top50": first_positive_rank,
            "positive_count_top50": int(positives.sum()),
            "false_candidate_count_top50": int((~positives).sum()),
            "false_before_first_positive_top50": int(first_positive_rank - 1) if first_positive_rank else int(len(frame)),
            "mean_descriptor_similarity_top50": float(frame["descriptor_similarity"].mean()),
            "mean_weakest_image_utility_top50": float(frame["weakest_image_utility_score"].mean()),
        }
        for k in SUMMARY_K:
            sub = frame[frame["rank"] <= k]
            sub_positive = sub["same_identity"].eq("yes")
            row[f"hit_at_{k}"] = bool(sub_positive.any())
            row[f"positive_count_at_{k}"] = int(sub_positive.sum())
            row[f"false_candidate_count_at_{k}"] = int((~sub_positive).sum())
            row[f"false_candidate_rate_at_{k}"] = float((~sub_positive).mean()) if len(sub) else np.nan
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    summary = query_meta.merge(summary, on="phase14_image_evidence_id", how="left")
    summary["query_has_positive_available"] = summary["available_positive_gallery_images"] > 0

    metric_rows = []
    for axis_name, frame in [("all_czechlynx", summary)] + [
        (f"query_{axis}", part) for axis, part in summary.groupby("evidence_axis", sort=True)
    ]:
        eligible = frame[frame["query_has_positive_available"]].copy()
        for k in SUMMARY_K:
            hit_col = f"hit_at_{k}"
            false_col = f"false_candidate_count_at_{k}"
            metric_rows.append(
                {
                    "query_group": axis_name,
                    "k": k,
                    "eligible_queries": int(len(eligible)),
                    "queries_with_hit": int(eligible[hit_col].fillna(False).sum()),
                    "hit_rate": float(eligible[hit_col].fillna(False).mean()) if len(eligible) else np.nan,
                    "mean_false_candidate_count": float(eligible[false_col].mean()) if len(eligible) else np.nan,
                    "median_false_candidate_count": float(eligible[false_col].median()) if len(eligible) else np.nan,
                    "mean_positive_count": float(eligible[f"positive_count_at_{k}"].mean()) if len(eligible) else np.nan,
                    "mean_false_candidate_rate": float(eligible[f"false_candidate_rate_at_{k}"].mean())
                    if len(eligible)
                    else np.nan,
                }
            )
    return summary, pd.DataFrame(metric_rows)


def write_report(metrics: pd.DataFrame, audit: dict[str, Any]) -> None:
    def val(group: str, k: int, col: str) -> str:
        row = metrics[(metrics["query_group"].eq(group)) & (metrics["k"].eq(k))]
        if row.empty:
            return "NA"
        value = row.iloc[0][col]
        if pd.isna(value):
            return "NA"
        return f"{float(value):.3f}"

    lines = [
        "# Phase 15 CzechLynx Query-Level Descriptor Benchmark",
        "",
        "This benchmark uses fixed MegaDescriptor embeddings only. It is the raw descriptor reference before PF-ERI/quality evidence routing. No model is trained.",
        "",
        "## Audit",
        "",
        f"- CzechLynx images: {audit['czechlynx_images']}",
        f"- Unique identities: {audit['unique_identities']}",
        f"- Queries with at least one positive gallery image: {audit['queries_with_positive_gallery']}",
        f"- Embedding model: `{audit['embedding_model']}`",
        "",
        "## Descriptor Baseline",
        "",
        "| Query group | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mean false@10 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for group in ["all_czechlynx", "query_high_confidence", "query_low_evidence_stress"]:
        lines.append(
            f"| {group} | {val(group, 1, 'hit_rate')} | {val(group, 5, 'hit_rate')} | "
            f"{val(group, 10, 'hit_rate')} | {val(group, 20, 'hit_rate')} | "
            f"{val(group, 50, 'hit_rate')} | {val(group, 10, 'mean_false_candidate_count')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This is a CzechLynx known-ID descriptor benchmark. It can validate query-level positive retrieval and false-candidate burden for CzechLynx only. It does not validate urban bobcat identity accuracy.",
            "",
            "The next step is to add PF-ERI pair comparability, weakest-image utility, quality controls, and descriptor-evidence conflict to these query candidates, then compare descriptor-only, quality-only, PF-ERI-only, and hybrid routing policies.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = load_czechlynx_metadata()
    ids = metadata["phase14_image_evidence_id"].astype(str).tolist()
    matrix, embedding_model, _ = load_embedding_matrix(ids)
    topk = rank_candidates(matrix, metadata)
    query_summary, metrics = summarize_queries(topk, metadata)

    topk.to_csv(TOPK_TABLE, index=False)
    query_summary.to_csv(QUERY_SUMMARY, index=False)
    metrics.to_csv(METRICS_TABLE, index=False)

    identity_counts = metadata["identity_label"].astype(str).value_counts()
    audit = {
        "status": "pass",
        "script": rel(Path(__file__)),
        "image_evidence_table": rel(IMAGE_EVIDENCE),
        "embeddings": rel(EMBEDDINGS),
        "working_label_tables": [rel(path) for path in WORKING_LABELS],
        "output_topk_table": rel(TOPK_TABLE),
        "output_query_summary": rel(QUERY_SUMMARY),
        "output_metrics_table": rel(METRICS_TABLE),
        "czechlynx_images": int(len(metadata)),
        "topk_candidates": int(len(topk)),
        "unique_identities": int(metadata["identity_label"].nunique()),
        "identities_with_at_least_two_images": int((identity_counts >= 2).sum()),
        "queries_with_positive_gallery": int(metadata["identity_label"].astype(str).map(identity_counts).gt(1).sum()),
        "embedding_model": embedding_model,
        "embedding_dim": int(matrix.shape[1]),
        "top_k": TOP_K,
        "claim_boundary": "CzechLynx known-ID query benchmark only; no bobcat identity validation; no model training.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    write_report(metrics, audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
