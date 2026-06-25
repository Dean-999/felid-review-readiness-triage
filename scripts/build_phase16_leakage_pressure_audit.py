#!/usr/bin/env python3
"""Diagnose path/site proxy leakage pressure in Phase 15 candidate pairs.

This is not a causal background-leakage proof. It estimates whether high
descriptor-similarity pairs are concentrated within available path/site/date
proxies so that later review and validation can treat them as higher-risk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CZECH_INPUT = PROJECT_ROOT / "outputs/phase15/evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv"
BOBCAT_INPUT = PROJECT_ROOT / "outputs/phase15/wild_urban_transfer_stress/phase15e_bobcat_evidence_routed_review_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/leakage_pressure"
OUTPUT_TABLE = OUTPUT_DIR / "phase16_leakage_pressure_pair_audit.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "phase16_leakage_pressure_summary.csv"
OUTPUT_AUDIT = OUTPUT_DIR / "phase16_leakage_pressure_audit.json"

BASE_COLUMNS = [
    "query_image_evidence_id",
    "candidate_image_evidence_id",
    "descriptor_similarity",
    "same_identity",
    "query_image_path",
    "candidate_image_path",
    "primary_failure_reason",
]


def path_site_proxy(path: object) -> str:
    """Return a coarse, non-sensitive path-derived site/date proxy."""
    if path is None:
        return "unknown"
    text = str(path).strip()
    if not text:
        return "unknown"
    parts = Path(text).parts
    if "felidae_conservation_fund" in parts:
        try:
            idx = parts.index("images")
            site = parts[idx + 2]
            date = parts[idx + 3]
            return f"fcf:{site}:{date}"
        except (ValueError, IndexError):
            return "fcf:unknown"
    if "CzechLynx" in parts:
        try:
            idx = parts.index("CzechLynx")
            collection = parts[idx + 1]
            return f"czechlynx:{collection}"
        except (ValueError, IndexError):
            return "czechlynx:unknown"
    return "unknown"


def same_proxy_group(query_proxy: str, candidate_proxy: str) -> bool:
    """Unknown proxies never count as same-site evidence."""
    if query_proxy == "unknown" or candidate_proxy == "unknown":
        return False
    return query_proxy == candidate_proxy


def _read_needed_columns(path: Path) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0)
    columns = [column for column in BASE_COLUMNS if column in header.columns]
    for optional in ["phase15d_review_action", "phase15e_review_action"]:
        if optional in header.columns:
            columns.append(optional)
    missing = {"query_image_path", "candidate_image_path", "descriptor_similarity"} - set(columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")
    return pd.read_csv(path, usecols=columns, low_memory=False)


def load_pairs(path: Path, dataset: str) -> pd.DataFrame:
    df = _read_needed_columns(path).copy()
    df["phase16_dataset"] = dataset
    df["phase16_query_site_proxy"] = df["query_image_path"].map(path_site_proxy)
    df["phase16_candidate_site_proxy"] = df["candidate_image_path"].map(path_site_proxy)
    df["phase16_same_site_proxy"] = [
        same_proxy_group(query, candidate)
        for query, candidate in zip(
            df["phase16_query_site_proxy"],
            df["phase16_candidate_site_proxy"],
        )
    ]
    descriptor_similarity = pd.to_numeric(df["descriptor_similarity"], errors="coerce")
    threshold = float(descriptor_similarity.quantile(0.90))
    df["phase16_high_similarity_threshold"] = threshold
    df["phase16_high_similarity"] = descriptor_similarity >= threshold
    df["phase16_site_leakage_pressure"] = (
        df["phase16_same_site_proxy"] & df["phase16_high_similarity"]
    )
    return df


def summarize(combined: pd.DataFrame) -> pd.DataFrame:
    return (
        combined.groupby("phase16_dataset", dropna=False)
        .agg(
            pair_count=("query_image_evidence_id", "count"),
            same_site_proxy_rate=("phase16_same_site_proxy", "mean"),
            high_similarity_rate=("phase16_high_similarity", "mean"),
            site_leakage_pressure_rate=("phase16_site_leakage_pressure", "mean"),
            high_similarity_threshold=("phase16_high_similarity_threshold", "first"),
        )
        .reset_index()
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    czech = load_pairs(CZECH_INPUT, "czechlynx_known_id")
    bobcat = load_pairs(BOBCAT_INPUT, "bobcat_transfer_stress")
    combined = pd.concat([czech, bobcat], ignore_index=True, sort=False)
    summary = summarize(combined)
    combined.to_csv(OUTPUT_TABLE, index=False)
    summary.to_csv(OUTPUT_SUMMARY, index=False)
    audit = {
        "czech_input": str(CZECH_INPUT),
        "bobcat_input": str(BOBCAT_INPUT),
        "output_table": str(OUTPUT_TABLE),
        "output_summary": str(OUTPUT_SUMMARY),
        "rows": int(len(combined)),
        "datasets": summary.to_dict(orient="records"),
        "claim_boundary": (
            "path-derived site proxies estimate leakage pressure only; "
            "this is not causal proof or exact protected location metadata"
        ),
    }
    OUTPUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS phase16 leakage pressure audit rows={len(combined)}")
    print(f"WROTE {OUTPUT_TABLE}")


if __name__ == "__main__":
    main()
