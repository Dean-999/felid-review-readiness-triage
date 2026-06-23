#!/usr/bin/env python3
"""Validate CzechLynx Phase 5 ERI-ReID score bands."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORES_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "phase5"
    / "czechlynx_phase5_pair_eri_scores_internal.csv"
)
TABLE_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "phase5" / "tables"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "phase5" / "figures"
BAND_VALIDATION_CSV = TABLE_DIR / "czechlynx_phase5_eri_band_validation.csv"

SCORE_COLUMNS = [
    ("visual_only_eri", "visual_only_eri_band"),
    ("model_support_score", None),
    ("hybrid_eri", "hybrid_eri_band"),
    ("hybrid_eri_visual_heavy", None),
    ("hybrid_eri_balanced", None),
    ("hybrid_eri_model_heavy", None),
    ("hybrid_eri_agreement_heavy", None),
]
SIMILARITY_COLUMNS = ["megadescriptor_similarity", "resnet50_similarity"]


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def score_band(score: float) -> str:
    if score >= 75.0:
        return "high"
    if score >= 50.0:
        return "medium"
    if score >= 25.0:
        return "low"
    return "unusable"


def auc_from_scores(labels: pd.Series, scores: pd.Series) -> float | None:
    positives = labels == "same"
    n_pos = int(positives.sum())
    n_neg = int((~positives).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = scores.rank(method="average")
    pos_rank_sum = float(ranks[positives].sum())
    auc = (pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def metric_row(
    df: pd.DataFrame,
    score_name: str,
    band_name: str,
    band_label: str,
    similarity_col: str,
) -> dict[str, object]:
    same = df[df["pair_type"] == "same"]
    different = df[df["pair_type"] == "different"]
    same_mean = float(same[similarity_col].mean()) if len(same) else math.nan
    different_mean = float(different[similarity_col].mean()) if len(different) else math.nan
    auc = auc_from_scores(df["pair_type"], df[similarity_col])
    n_same = int(len(same))
    n_different = int(len(different))
    sparse = n_same < 20 or n_different < 20
    return {
        "score_name": score_name,
        "band_variable": band_name,
        "band": band_label,
        "similarity_model": similarity_col.replace("_similarity", ""),
        "pair_count": int(len(df)),
        "n_same": n_same,
        "n_different": n_different,
        "same_mean_similarity": same_mean,
        "different_mean_similarity": different_mean,
        "separation_gap": same_mean - different_mean,
        "roc_auc": auc,
        "sparse_band_caveat": "yes" if sparse else "no",
    }


def build_validation(scores: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for score_col, explicit_band_col in SCORE_COLUMNS:
        if explicit_band_col is None:
            band_col = f"{score_col}_band_for_validation"
            scores[band_col] = scores[score_col].astype(float).map(score_band)
        else:
            band_col = explicit_band_col

        for similarity_col in SIMILARITY_COLUMNS:
            rows.append(metric_row(scores, score_col, band_col, "all", similarity_col))
            for band in ["high", "medium", "low", "unusable"]:
                subset = scores[scores[band_col] == band].copy()
                if subset.empty:
                    continue
                rows.append(metric_row(subset, score_col, band_col, band, similarity_col))
    return pd.DataFrame(rows)


def write_figures(validation: pd.DataFrame) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: matplotlib unavailable; skipping figures: {exc}")
        return

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for model in ["megadescriptor", "resnet50"]:
        subset = validation[
            (validation["band"] != "all")
            & (validation["similarity_model"] == model)
            & (validation["score_name"].isin(["visual_only_eri", "hybrid_eri"]))
        ].copy()
        if subset.empty:
            continue
        subset["band"] = pd.Categorical(
            subset["band"], categories=["high", "medium", "low", "unusable"], ordered=True
        )
        pivot = subset.pivot(index="band", columns="score_name", values="roc_auc").sort_index()
        ax = pivot.plot(kind="bar", figsize=(8, 5), ylim=(0.0, 1.0))
        ax.set_title(f"Phase 5 ERI band ROC-AUC ({model})")
        ax.set_xlabel("ERI band")
        ax.set_ylabel("ROC-AUC")
        ax.axhline(0.5, color="black", linewidth=0.8)
        plt.tight_layout()
        out = FIGURE_DIR / f"phase5_eri_band_auc_{model}.png"
        plt.savefig(out, dpi=200)
        plt.close()


def main() -> int:
    if not SCORES_CSV.exists():
        return fail(f"ERI score file not found: {SCORES_CSV}")

    scores = pd.read_csv(SCORES_CSV)
    required = {"pair_type", *SIMILARITY_COLUMNS}
    for score_col, band_col in SCORE_COLUMNS:
        required.add(score_col)
        if band_col:
            required.add(band_col)
    missing = sorted(required - set(scores.columns))
    if missing:
        return fail("score file missing required column(s): " + ", ".join(missing))

    for col in [score for score, _ in SCORE_COLUMNS] + SIMILARITY_COLUMNS:
        scores[col] = pd.to_numeric(scores[col], errors="raise")

    validation = build_validation(scores)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    validation.to_csv(BAND_VALIDATION_CSV, index=False)
    write_figures(validation)

    print("CzechLynx Phase 5 ERI-ReID band validation")
    print(f"Input rows: {len(scores)}")
    print(f"Output CSV: {BAND_VALIDATION_CSV}")
    print(f"Rows written: {len(validation)}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
