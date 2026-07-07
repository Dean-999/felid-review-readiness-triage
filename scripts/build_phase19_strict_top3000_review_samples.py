#!/usr/bin/env python3
"""Build Phase19 strict top-3000 candidates and 100-image review samples.

The top-3000 files are still candidate sets. They become freeze-ready only
after the corresponding 100-image validation sample has a high human CLEAR
rate under the strict visual standard.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREFILTER_DIR = PROJECT_ROOT / "outputs/phase19/phase19_strict_photo_prefilter"
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_strict_top3000_validation"

POOLS = [
    "bobcat_wild_camera_trap",
    "bobcat_urban_heterogeneous",
    "lynx_external_heterogeneous_supplement",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = -999.0) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def row_passes_hard_gate(row: dict[str, str]) -> bool:
    if row.get("phase19_prefilter_decision") != "review":
        return False
    if row.get("technical_quality_rule") != "technical_strict_pass":
        return False
    if row.get("phase19_manual_review_priority") not in {"high", "cautious"}:
        return False
    if row.get("subject_area_rule") in {"reject_area_lt_0_20", "cautious_edge_touch"}:
        return False
    reject_reasons = row.get("phase19_prefilter_reject_reasons", "")
    hard_reject_tokens = [
        "bad_text_track_scat_dead_sign",
        "subject_area_lt_0_20",
        "min_dimension_lt_700",
        "megapixels_lt_0_65",
        "small_file_lt_75kb",
        "min_dimension_lt_850_ultra",
        "megapixels_lt_0_90_ultra",
        "small_file_lt_140kb_ultra",
        "low_sharpness_proxy",
        "low_sharpness_proxy_ultra",
        "weak_edges",
        "weak_edges_ultra",
        "low_contrast",
        "low_contrast_ultra",
        "low_entropy_ultra",
        "heavy_shadow_highlight_clipping_ultra",
        "too_dark_or_night_ultra",
        "too_bright_washed_ultra",
        "low_color_or_ir_night_ultra",
    ]
    return not any(token in reject_reasons for token in hard_reject_tokens)


def strict_sort_key(row: dict[str, str]) -> tuple[int, float, float, float, float, str]:
    area_rule_rank = {
        "pass_area_ge_0_30": 0,
        "cautious_area_0_20_to_0_30": 1,
        "manual_area_required": 2,
    }.get(row.get("subject_area_rule", ""), 9)
    return (
        area_rule_rank,
        -safe_float(row.get("phase19_strict_photo_score")),
        -safe_float(row.get("laplacian_var")),
        -safe_float(row.get("gradient_p90")),
        -safe_float(row.get("image_megapixels")),
        row.get("phase19_review_id", ""),
    )


def validation_sample(top_rows: list[dict[str, str]], sample_size: int) -> list[dict[str, str]]:
    """Sample across the accepted candidate range, not just the prettiest top rows."""
    if len(top_rows) <= sample_size:
        return [dict(row, phase19_validation_sample_role="all_available") for row in top_rows]
    plan = [
        ("top_strict", 40, 0.00, 0.20),
        ("middle_strict", 30, 0.40, 0.60),
        ("boundary_strict", 30, 0.80, 1.00),
    ]
    picked: list[dict[str, str]] = []
    seen: set[str] = set()
    n = len(top_rows)
    for role, count, start_frac, end_frac in plan:
        start = int(n * start_frac)
        end = max(start + 1, int(n * end_frac))
        segment = top_rows[start:end]
        if not segment:
            continue
        if len(segment) <= count:
            indexes = list(range(len(segment)))
        else:
            indexes = sorted({round(i * (len(segment) - 1) / (count - 1)) for i in range(count)})
        for index in indexes:
            row = segment[index]
            row_id = row.get("phase19_review_id", "")
            if row_id and row_id not in seen:
                out = dict(row)
                out["phase19_validation_sample_role"] = role
                picked.append(out)
                seen.add(row_id)
    if len(picked) < sample_size:
        for row in top_rows:
            row_id = row.get("phase19_review_id", "")
            if row_id not in seen:
                out = dict(row)
                out["phase19_validation_sample_role"] = "fill"
                picked.append(out)
                seen.add(row_id)
            if len(picked) >= sample_size:
                break
    return picked[:sample_size]


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit: dict[str, Any] = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "logic": (
            "For each Phase19 pool, first build a strict top-3000 candidate set, "
            "then export a 100-image validation sample spanning top/middle/boundary. "
            "The top-3000 set is not freeze-ready until the sample review supports it."
        ),
        "hard_gate": {
            "technical_quality_rule": "technical_strict_pass only",
            "prefilter_decision": "review only",
            "area": "reject detector <20%; prioritize detector >=30%; allow manual_area_required only as candidate pending sample validation",
            "excluded_proxy_reasons": [
                "bad_text_track_scat_dead_sign",
                "subject_area_lt_0_20",
                "min_dimension_lt_700",
                "megapixels_lt_0_65",
                "small_file_lt_75kb",
                "min_dimension_lt_850_ultra",
                "megapixels_lt_0_90_ultra",
                "small_file_lt_140kb_ultra",
                "low_sharpness_proxy",
                "low_sharpness_proxy_ultra",
                "weak_edges",
                "weak_edges_ultra",
                "low_contrast",
                "low_contrast_ultra",
                "low_entropy_ultra",
                "heavy_shadow_highlight_clipping_ultra",
                "too_dark_or_night_ultra",
                "too_bright_washed_ultra",
                "low_color_or_ir_night_ultra",
            ],
        },
        "pools": {},
    }
    combined_samples: list[dict[str, Any]] = []
    fieldnames: list[str] | None = None
    for pool in args.pools:
        source = PREFILTER_DIR / f"{pool}_strict_photo_prefilter.csv"
        rows = read_csv(source)
        if fieldnames is None:
            fieldnames = list(rows[0].keys()) + ["phase19_top3000_rank", "phase19_validation_sample_role"]
        gated = [row for row in rows if row_passes_hard_gate(row)]
        gated.sort(key=strict_sort_key)
        top_rows = []
        for rank, row in enumerate(gated[: args.target_per_pool], start=1):
            out = dict(row)
            out["phase19_top3000_rank"] = rank
            out["phase19_validation_sample_role"] = ""
            top_rows.append(out)
        sample = validation_sample(top_rows, args.sample_per_pool)
        combined_samples.extend(sample)
        write_csv(OUT_DIR / f"{pool}_strict_top3000_candidates.csv", top_rows, fieldnames)
        write_csv(OUT_DIR / f"{pool}_strict_top3000_validation_sample100.csv", sample, fieldnames)
        audit["pools"][pool] = {
            "prefilter_rows": len(rows),
            "strict_gated_rows": len(gated),
            "top_candidate_rows": len(top_rows),
            "validation_sample_rows": len(sample),
            "candidate_shortfall": max(0, args.target_per_pool - len(top_rows)),
            "area_rule_counts_top": dict(Counter(row.get("subject_area_rule", "") for row in top_rows)),
            "sample_role_counts": dict(Counter(row.get("phase19_validation_sample_role", "") for row in sample)),
            "outputs": {
                "top3000": str((OUT_DIR / f"{pool}_strict_top3000_candidates.csv").relative_to(PROJECT_ROOT)),
                "sample100": str((OUT_DIR / f"{pool}_strict_top3000_validation_sample100.csv").relative_to(PROJECT_ROOT)),
            },
        }
    if fieldnames is None:
        raise RuntimeError("no input rows found")
    write_csv(OUT_DIR / "phase19_strict_top3000_validation_sample300_combined.csv", combined_samples, fieldnames)
    audit["combined_sample_rows"] = len(combined_samples)
    audit["combined_sample_csv"] = str(
        (OUT_DIR / "phase19_strict_top3000_validation_sample300_combined.csv").relative_to(PROJECT_ROOT)
    )
    (OUT_DIR / "phase19_strict_top3000_validation_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Phase19 strict top-3000 validation outputs to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pools", nargs="+", choices=POOLS, default=POOLS)
    parser.add_argument("--target-per-pool", type=int, default=3000)
    parser.add_argument("--sample-per-pool", type=int, default=100)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
