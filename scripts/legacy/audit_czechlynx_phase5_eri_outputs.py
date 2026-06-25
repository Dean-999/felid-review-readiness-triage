#!/usr/bin/env python3
"""Audit CzechLynx Phase 5 ERI-ReID outputs for completeness and leakage."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "phase5"
TABLE_DIR = PHASE5_DIR / "tables"
FIGURE_DIR = PHASE5_DIR / "figures"
QC_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "qc"

SCORES_CSV = PHASE5_DIR / "czechlynx_phase5_pair_eri_scores_internal.csv"
BAND_VALIDATION_CSV = TABLE_DIR / "czechlynx_phase5_eri_band_validation.csv"
POLICY_FRONTIER_CSV = TABLE_DIR / "czechlynx_phase5_policy_frontier.csv"
BASELINE_CSV = TABLE_DIR / "czechlynx_phase5_eri_vs_similarity_baselines.csv"
REPORT_TXT = QC_DIR / "phase5_eri_audit_report.txt"

EXPECTED_ROWS = 3000
EXPECTED_SAME = 750
EXPECTED_DIFFERENT = 2250

REQUIRED_SCORE_COLUMNS = {
    "pair_id",
    "pair_type",
    "image_a_expanded_id",
    "image_b_expanded_id",
    "visual_only_eri",
    "model_support_score",
    "cross_model_agreement",
    "hybrid_eri",
    "hybrid_eri_visual_heavy",
    "hybrid_eri_balanced",
    "hybrid_eri_model_heavy",
    "hybrid_eri_agreement_heavy",
    "visual_only_eri_band",
    "hybrid_eri_band",
    "visual_only_review_tier",
    "hybrid_review_tier",
    "resnet50_similarity",
    "megadescriptor_similarity",
}

REQUIRED_POLICIES = {
    "keep_all",
    "strict_high_quality_evidence",
    "remove_severe_blur",
    "remove_low_none_pattern",
    "remove_side_not_comparable",
    "visual_only_eri_high",
    "visual_only_eri_high_medium",
    "hybrid_eri_high",
    "hybrid_eri_high_medium",
}

REQUIRED_BASELINE_PARTS = {
    "raw_megadescriptor_ranking",
    "raw_resnet50_ranking",
}

SENSITIVE_COLUMN_PARTS = [
    "unique_name",
    "latitude",
    "longitude",
    "cell_code",
    "trap_id",
    "review_image_path",
    "location",
]
SENSITIVE_VALUE_PARTS = ["lynx_", "unique_name", "latitude", "longitude", "cell_code", "trap_id"]


def check(condition: bool, message: str, pass_lines: list[str], fail_lines: list[str]) -> None:
    if condition:
        pass_lines.append(f"[PASS] {message}")
    else:
        fail_lines.append(f"[FAIL] {message}")


def scan_sensitive_values(path: Path, df: pd.DataFrame) -> list[str]:
    findings: list[str] = []
    sensitive_cols = [
        col for col in df.columns if any(part in col.lower() for part in SENSITIVE_COLUMN_PARTS)
    ]
    for col in sensitive_cols:
        findings.append(f"{path.name}: sensitive-looking column `{col}`")
    object_df = df.select_dtypes(include=["object"])
    for col in object_df.columns:
        values = object_df[col].astype(str).str.lower()
        for part in SENSITIVE_VALUE_PARTS:
            if values.str.contains(part, regex=False).any():
                findings.append(f"{path.name}: restricted value pattern `{part}` in `{col}`")
    return findings


def main() -> int:
    pass_lines: list[str] = []
    fail_lines: list[str] = []

    paths = [SCORES_CSV, BAND_VALIDATION_CSV, POLICY_FRONTIER_CSV, BASELINE_CSV]
    for path in paths:
        check(path.exists(), f"Required output exists: {path}", pass_lines, fail_lines)
    check(FIGURE_DIR.exists(), f"Figure directory exists: {FIGURE_DIR}", pass_lines, fail_lines)

    dataframes: dict[Path, pd.DataFrame] = {}
    for path in paths:
        if path.exists():
            try:
                dataframes[path] = pd.read_csv(path)
                pass_lines.append(f"[PASS] Loaded CSV: {path}")
            except Exception as exc:  # noqa: BLE001
                fail_lines.append(f"[FAIL] Could not load {path}: {exc}")

    scores = dataframes.get(SCORES_CSV)
    if scores is not None:
        missing = sorted(REQUIRED_SCORE_COLUMNS - set(scores.columns))
        check(not missing, "Score file has required Phase 5 score columns.", pass_lines, fail_lines)
        if missing:
            fail_lines.append("       Missing: " + ", ".join(missing))
        check(len(scores) == EXPECTED_ROWS, "Score file has 3,000 pair rows.", pass_lines, fail_lines)
        check(
            int((scores["pair_type"] == "same").sum()) == EXPECTED_SAME,
            "Score file has 750 same pairs.",
            pass_lines,
            fail_lines,
        )
        check(
            int((scores["pair_type"] == "different").sum()) == EXPECTED_DIFFERENT,
            "Score file has 2,250 different pairs.",
            pass_lines,
            fail_lines,
        )
        for col in [
            "visual_only_eri",
            "model_support_score",
            "cross_model_agreement",
            "hybrid_eri",
            "hybrid_eri_visual_heavy",
            "hybrid_eri_balanced",
            "hybrid_eri_model_heavy",
            "hybrid_eri_agreement_heavy",
        ]:
            if col in scores.columns:
                numeric = pd.to_numeric(scores[col], errors="coerce")
                check(
                    numeric.notna().all() and numeric.between(0, 100).all(),
                    f"{col} is numeric and within [0, 100].",
                    pass_lines,
                    fail_lines,
                )
        for col in ["visual_only_eri_band", "hybrid_eri_band"]:
            if col in scores.columns:
                check(
                    set(scores[col].dropna()).issubset({"high", "medium", "low", "unusable"}),
                    f"{col} contains only expected band labels.",
                    pass_lines,
                    fail_lines,
                )

    validation = dataframes.get(BAND_VALIDATION_CSV)
    if validation is not None:
        check(
            {"visual_only_eri", "hybrid_eri"}.issubset(set(validation["score_name"])),
            "Band validation includes visual-only and hybrid ERI.",
            pass_lines,
            fail_lines,
        )
        check(
            {"megadescriptor", "resnet50"}.issubset(set(validation["similarity_model"])),
            "Band validation includes both similarity models.",
            pass_lines,
            fail_lines,
        )

    frontier = dataframes.get(POLICY_FRONTIER_CSV)
    if frontier is not None:
        policies = set(frontier["policy"])
        missing_policies = sorted(REQUIRED_POLICIES - policies)
        check(not missing_policies, "Policy frontier includes required ERI and visual policies.", pass_lines, fail_lines)
        if missing_policies:
            fail_lines.append("       Missing policies: " + ", ".join(missing_policies))

    baselines = dataframes.get(BASELINE_CSV)
    if baselines is not None:
        baseline_names = " ".join(sorted(set(baselines["policy"])))
        for part in REQUIRED_BASELINE_PARTS:
            check(
                part in baseline_names,
                f"Baseline comparison includes {part}.",
                pass_lines,
                fail_lines,
            )

    leakage_findings: list[str] = []
    for path, df in dataframes.items():
        leakage_findings.extend(scan_sensitive_values(path, df))
    check(not leakage_findings, "No restricted columns or value patterns found.", pass_lines, fail_lines)
    fail_lines.extend(f"[FAIL] {finding}" for finding in leakage_findings)

    figure_count = len(list(FIGURE_DIR.glob("*.png"))) if FIGURE_DIR.exists() else 0
    check(figure_count > 0, "At least one Phase 5 figure was generated.", pass_lines, fail_lines)

    QC_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "CzechLynx Phase 5 ERI-ReID output audit",
        "========================================",
        "",
        "PASS checks:",
        *[f"  {line}" for line in pass_lines],
        "",
        "FAIL checks:",
        *([f"  {line}" for line in fail_lines] if fail_lines else ["  none"]),
        "",
        "Result:",
        "RESULT: FAIL" if fail_lines else "RESULT: PASS",
    ]
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if fail_lines else 0


if __name__ == "__main__":
    sys.exit(main())
