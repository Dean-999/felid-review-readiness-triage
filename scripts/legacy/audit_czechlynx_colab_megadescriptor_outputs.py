#!/usr/bin/env python3
"""Audit CzechLynx Colab MegaDescriptor-S-224 baseline outputs."""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_CSV = PROJECT_ROOT / "data" / "interim" / "czechlynx" / "czechlynx_pilot_pairs.csv"
COLAB_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "colab_megadescriptor"
    / "czechlynx_wildlife_baseline_outputs"
)
EMBEDDINGS_PARQUET = COLAB_DIR / "czechlynx_pilot_embeddings_megadescriptor_s224.parquet"
SIMILARITIES_CSV = COLAB_DIR / "czechlynx_pair_similarities_megadescriptor_s224.csv"
BASELINE_COMPARISON_CSV = COLAB_DIR / "phase2_baseline_comparison.csv"
READINESS_GROUP_COMPARISON_CSV = COLAB_DIR / "phase2_baseline_readiness_group_comparison.csv"
BASELINE_REPORT_TXT = COLAB_DIR / "phase2_baseline_comparison_report.txt"
AUDIT_REPORT_TXT = (
    PROJECT_ROOT / "outputs" / "czechlynx" / "qc" / "megadescriptor_colab_output_audit.txt"
)

REQUIRED_FILES = [
    (EMBEDDINGS_PARQUET, "embeddings parquet"),
    (SIMILARITIES_CSV, "pair similarities CSV"),
    (BASELINE_COMPARISON_CSV, "baseline comparison CSV"),
    (READINESS_GROUP_COMPARISON_CSV, "readiness group comparison CSV"),
    (BASELINE_REPORT_TXT, "baseline comparison report"),
]

EXPECTED_EMBEDDINGS = 200
EXPECTED_SIMILARITIES = 400
EXPECTED_SAME_PAIRS = 100
EXPECTED_DIFFERENT_PAIRS = 300

VALID_READINESS_GROUPS = {
    "limited_limited",
    "limited_unidentifiable",
    "ready_limited",
    "ready_ready",
    "ready_unidentifiable",
    "unidentifiable_unidentifiable",
}
MEGADESCRIPTOR_MODEL_MARKERS = ("MegaDescriptor", "S-224")

BASELINE_REQUIRED_COLUMNS = [
    "baseline",
    "total_pairs",
    "same_pairs",
    "different_pairs",
    "same_mean",
    "different_mean",
    "same_minus_different_gap",
    "roc_auc",
]
EXPECTED_BASELINES = {
    "ResNet50_ImageNet1K_V2": {
        "total_pairs": 400,
        "same_pairs": 100,
        "different_pairs": 300,
        "same_mean": 0.579955,
        "different_mean": 0.493990,
        "same_minus_different_gap": 0.085966,
        "roc_auc": 0.618667,
    },
    "MegaDescriptor_S_224": {
        "total_pairs": 400,
        "same_pairs": 100,
        "different_pairs": 300,
        "same_mean": 0.235992,
        "different_mean": 0.118512,
        "same_minus_different_gap": 0.117479,
        "roc_auc": 0.690400,
    },
}
METRIC_TOLERANCE = 1e-3


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def add_count_check(
    passes: list[str],
    failures: list[str],
    label: str,
    actual: int,
    expected: int,
) -> None:
    if actual == expected:
        passes.append(f"{label} is exactly {expected}.")
    else:
        failures.append(f"{label} is {actual}; expected {expected}.")


def count_same_individual(series: pd.Series) -> tuple[int, int]:
    normalized = series.map(clean_cell).str.lower()
    same_count = int((normalized == "true").sum())
    different_count = int((normalized == "false").sum())
    return same_count, different_count


def is_megadescriptor_model(value: object) -> bool:
    text = clean_cell(value)
    return all(marker in text for marker in MEGADESCRIPTOR_MODEL_MARKERS)


def audit_baseline_comparison(
    passes: list[str],
    failures: list[str],
    baseline_df: pd.DataFrame,
) -> None:
    missing_columns = sorted(set(BASELINE_REQUIRED_COLUMNS) - set(baseline_df.columns))
    if missing_columns:
        failures.append(
            "Baseline comparison missing required column(s): " + ", ".join(missing_columns)
        )
        return
    passes.append("Baseline comparison CSV has required columns.")

    baselines_present = set(baseline_df["baseline"].map(clean_cell))
    for baseline_name in EXPECTED_BASELINES:
        if baseline_name not in baselines_present:
            failures.append(f"Baseline comparison missing row for {baseline_name}.")
        else:
            passes.append(f"Baseline comparison contains {baseline_name}.")

    for baseline_name, expected_values in EXPECTED_BASELINES.items():
        if baseline_name not in baselines_present:
            continue
        row = baseline_df[baseline_df["baseline"].map(clean_cell) == baseline_name].iloc[0]
        for column, expected in expected_values.items():
            actual = float(row[column])
            if abs(actual - expected) > METRIC_TOLERANCE:
                failures.append(
                    f"{baseline_name} {column} is {actual:.6f}; expected {expected:.6f}."
                )
            else:
                passes.append(f"{baseline_name} {column} matches expected value.")


def run_audit() -> tuple[list[str], list[str]]:
    failures: list[str] = []
    passes: list[str] = []

    for path, label in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"Required file not found ({label}): {path}")
        else:
            passes.append(f"Required file exists: {path.name}")

    if failures:
        return passes, failures

    if not PAIR_CSV.exists():
        failures.append(f"Pair file not found: {PAIR_CSV}")
        return passes, failures
    passes.append(f"Pair file exists: {PAIR_CSV.name}")

    pairs = read_csv_clean(PAIR_CSV)
    similarities = read_csv_clean(SIMILARITIES_CSV)
    embeddings = pd.read_parquet(EMBEDDINGS_PARQUET)
    baseline_df = pd.read_csv(BASELINE_COMPARISON_CSV)

    add_count_check(
        passes,
        failures,
        "Pair similarity row count",
        len(similarities),
        EXPECTED_SIMILARITIES,
    )

    same_count, different_count = count_same_individual(similarities["same_individual"])
    add_count_check(passes, failures, "Same-individual pair count", same_count, EXPECTED_SAME_PAIRS)
    add_count_check(
        passes,
        failures,
        "Different-individual pair count",
        different_count,
        EXPECTED_DIFFERENT_PAIRS,
    )

    missing_cosine = int((similarities["cosine_similarity"] == "").sum())
    numeric_cosine = pd.to_numeric(similarities["cosine_similarity"], errors="coerce")
    nan_cosine = int(numeric_cosine.isna().sum())
    if missing_cosine or nan_cosine:
        failures.append(
            f"cosine_similarity has {missing_cosine} blank and {nan_cosine} nonnumeric value(s)."
        )
    else:
        passes.append("No missing cosine_similarity values.")

    pair_ids = set(pairs["pair_id"])
    similarity_pair_ids = set(similarities["pair_id"])
    missing_pair_ids = sorted(pair_ids - similarity_pair_ids)
    extra_pair_ids = sorted(similarity_pair_ids - pair_ids)
    if missing_pair_ids:
        failures.append(f"{len(missing_pair_ids)} pair ID(s) missing from similarities.")
        for pair_id in missing_pair_ids[:10]:
            failures.append(f"  missing pair_id: {pair_id}")
    else:
        passes.append("All pair IDs from pair file are present in similarities.")
    if extra_pair_ids:
        failures.append(f"{len(extra_pair_ids)} extra pair ID(s) found in similarities.")
        for pair_id in extra_pair_ids[:10]:
            failures.append(f"  extra pair_id: {pair_id}")
    else:
        passes.append("No extra pair IDs found in similarities.")

    pair_flags = pairs.set_index("pair_id")["same_individual"]
    similarity_flags = similarities.set_index("pair_id")["same_individual"]
    common_pair_ids = sorted(pair_ids & similarity_pair_ids)
    mismatched_flags = [
        pair_id
        for pair_id in common_pair_ids
        if pair_flags.loc[pair_id] != similarity_flags.loc[pair_id]
    ]
    if mismatched_flags:
        failures.append(
            f"{len(mismatched_flags)} same_individual value(s) do not match pair file."
        )
        for pair_id in mismatched_flags[:10]:
            failures.append(f"  mismatched pair_id: {pair_id}")
    else:
        passes.append("same_individual values match the pair file.")

    if "pair_readiness_group" not in similarities.columns:
        failures.append("pair_readiness_group column is missing from similarities.")
    else:
        passes.append("pair_readiness_group column is present.")
        readiness_values = set(similarities["pair_readiness_group"].map(clean_cell))
        unexpected_groups = sorted(readiness_values - VALID_READINESS_GROUPS)
        if unexpected_groups:
            failures.append(
                "Unexpected pair_readiness_group value(s): " + ", ".join(unexpected_groups)
            )
        else:
            passes.append("All pair_readiness_group values are valid.")

    if "embedding_model" in similarities.columns:
        model_values = similarities["embedding_model"].map(clean_cell).unique()
        if len(model_values) != 1 or not is_megadescriptor_model(model_values[0]):
            failures.append(
                "embedding_model is not consistent with MegaDescriptor-S-224 in similarities."
            )
        else:
            passes.append(
                f"embedding_model is consistent with MegaDescriptor-S-224: {model_values[0]}"
            )

    audit_baseline_comparison(passes, failures, baseline_df)

    missing_embedding_columns = sorted(
        {"pilot_image_id", "embedding_model", "embedding_dim", "embedding_vector"}
        - set(embeddings.columns)
    )
    if missing_embedding_columns:
        failures.append(
            "Embeddings missing required column(s): " + ", ".join(missing_embedding_columns)
        )
    else:
        passes.append("Embeddings parquet has required columns.")

    add_count_check(
        passes,
        failures,
        "Embedding row count",
        len(embeddings),
        EXPECTED_EMBEDDINGS,
    )
    unique_embedding_ids = embeddings["pilot_image_id"].astype(str).nunique()
    add_count_check(
        passes,
        failures,
        "Unique embedding pilot_image_id count",
        unique_embedding_ids,
        EXPECTED_EMBEDDINGS,
    )

    if "embedding_model" in embeddings.columns:
        model_values = embeddings["embedding_model"].astype(str).unique()
        if len(model_values) != 1 or not is_megadescriptor_model(model_values[0]):
            failures.append(
                "embedding_model is not consistent with MegaDescriptor-S-224 in embeddings."
            )
        else:
            passes.append(
                f"Embeddings embedding_model is consistent: {model_values[0]}"
            )

    return passes, failures


def format_audit_output(passes: list[str], failures: list[str]) -> str:
    lines = [
        "CzechLynx Colab MegaDescriptor-S-224 Output Audit",
        "",
        f"Colab output directory: {COLAB_DIR}",
        f"Pair file: {PAIR_CSV}",
        "",
    ]
    if passes:
        lines.append("PASS checks:")
        for item in passes:
            lines.append(f"  [PASS] {item}")
        lines.append("")
    if failures:
        lines.append("FAIL checks:")
        for item in failures:
            lines.append(f"  [FAIL] {item}")
        lines.append("")
    lines.append("RESULT: PASS" if not failures else "RESULT: FAIL")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        print("CzechLynx Colab MegaDescriptor-S-224 output audit")
        print(f"Colab directory: {COLAB_DIR}")
        print(f"Pair file: {PAIR_CSV}")
        print()

        passes, failures = run_audit()

        if passes:
            print("PASS checks:")
            for item in passes:
                print(f"  [PASS] {item}")
            print()

        if failures:
            print("FAIL checks:")
            for item in failures:
                print(f"  [FAIL] {item}")
            print()

        result = "PASS" if not failures else "FAIL"
        print(f"RESULT: {result}")

    output = buffer.getvalue()
    print(output, end="")

    AUDIT_REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
    report_body = format_audit_output(passes, failures)
    AUDIT_REPORT_TXT.write_text(report_body, encoding="utf-8")
    print(f"Wrote: {AUDIT_REPORT_TXT}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
