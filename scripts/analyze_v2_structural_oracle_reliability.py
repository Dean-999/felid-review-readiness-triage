#!/usr/bin/env python3
"""Audit the current v2 structural-oracle reliability data without outcomes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pingouin as pg
from sklearn.metrics import cohen_kappa_score

PACKET_COLUMNS = {"annotation_packet_id"}
CONTINUOUS = {
    "visible_pattern_area_fraction": ["left_visible_pattern_area_fraction", "right_visible_pattern_area_fraction"],
    "occlusion_fraction": ["left_occlusion_fraction", "right_occlusion_fraction"],
    "shared_body_region_fraction": ["shared_body_region_fraction"],
}
VIEWPOINTS = {"compatible", "partial", "incompatible", "unknown"}


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")
    if not PACKET_COLUMNS.issubset(frame.columns) or frame.annotation_packet_id.duplicated().any():
        raise ValueError(f"invalid response file: {path}")
    return frame


def check_grid(frame: pd.DataFrame) -> None:
    for field_list in CONTINUOUS.values():
        for field in field_list:
            values = frame[field].astype(float)
            if not ((values.ge(0) & values.le(1)) & ((values * 20).round() == values * 20)).all():
                raise ValueError(f"invalid 0.05-grid values in {field}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotator-a", type=Path, required=True)
    parser.add_argument("--annotator-b", type=Path, required=True)
    parser.add_argument("--expected-packets", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args()
    a, b = load(args.annotator_a), load(args.annotator_b)
    expected = pd.read_csv(args.expected_packets, dtype=str, keep_default_na=False).fillna("")
    expected_ids = set(expected.annotation_packet_id)
    if set(a.annotation_packet_id) != expected_ids or set(b.annotation_packet_id) != expected_ids:
        raise ValueError("response packet coverage does not exactly equal the frozen packet manifest")
    if set(a.technical_problem_flag) != {"no"} or set(b.technical_problem_flag) != {"no"}:
        raise ValueError("technical-problem responses require a separate missingness disposition")
    check_grid(a); check_grid(b)
    merged = a.merge(b, on="annotation_packet_id", suffixes=("_a", "_b"), validate="one_to_one")
    reliability: dict[str, object] = {}
    for family, fields in CONTINUOUS.items():
        long = []
        for field in fields:
            for _, row in merged.iterrows():
                target = f"{row.annotation_packet_id}:{field}"
                long.extend([
                    {"target": target, "rater": "annotator_a", "score": float(row[f"{field}_a"])},
                    {"target": target, "rater": "annotator_b", "score": float(row[f"{field}_b"])},
                ])
        icc = pg.intraclass_corr(data=pd.DataFrame(long), targets="target", raters="rater", ratings="score")
        result = icc[icc.Type == "ICC(A,1)"].iloc[0]
        reliability[family] = {
            "method": "two_way_random_absolute_agreement_single_measure_icc",
            "icc": float(result.ICC), "ci95_lower": float(result.CI95[0]), "ci95_upper": float(result.CI95[1]),
            "target_count": len(long) // 2, "gate_lower_bound": 0.60,
            "gate_status": "PASS" if float(result.CI95[0]) >= 0.60 else "FAIL",
        }
    viewpoints_a, viewpoints_b = merged.viewpoint_compatibility_class_a, merged.viewpoint_compatibility_class_b
    if not set(viewpoints_a).issubset(VIEWPOINTS) or not set(viewpoints_b).issubset(VIEWPOINTS):
        raise ValueError("invalid viewpoint class")
    viewpoint_valid = merged[(merged.viewpoint_compatibility_class_a != "unknown") & (merged.viewpoint_compatibility_class_b != "unknown")].copy()
    order = {"incompatible": 0, "partial": 1, "compatible": 2}
    viewpoint_a = viewpoint_valid.viewpoint_compatibility_class_a.map(order)
    viewpoint_b = viewpoint_valid.viewpoint_compatibility_class_b.map(order)
    weighted_kappa = float(cohen_kappa_score(viewpoint_a, viewpoint_b, weights="linear"))
    rng = np.random.default_rng(20260713)
    bootstrap = [
        cohen_kappa_score(viewpoint_a.iloc[index], viewpoint_b.iloc[index], weights="linear")
        for index in (rng.integers(0, len(viewpoint_valid), len(viewpoint_valid)) for _ in range(10_000))
    ]
    weighted_ci = np.quantile(bootstrap, [0.025, 0.975])
    weighted_pass = float(weighted_ci[0]) >= 0.50
    continuous_all_pass = all(item["gate_status"] == "PASS" for item in reliability.values())
    status = "PASS" if continuous_all_pass and weighted_pass else "FAIL"
    decision = (
        "All continuous structural fields and the fixed weighted-kappa viewpoint gate pass. "
        "The structural-oracle measurement gate is passed for this frozen pilot batch."
        if continuous_all_pass and weighted_pass else
        "At least one continuous structural field fails the pre-registered ICC lower-bound gate. "
        "Do not use failed oracle annotations as measurement truth, training data, or primary automatic-model inputs."
    )
    audit = {
        "analysis_version": "pferi_v2_structural_oracle_reliability_audit_v2",
        "status": status,
        "packet_count": len(expected), "annotator_a_rows": len(a), "annotator_b_rows": len(b), "paired_rows": len(merged),
        "technical_problem_counts": {"annotator_a": int((a.technical_problem_flag == "yes").sum()), "annotator_b": int((b.technical_problem_flag == "yes").sum())},
        "continuous_reliability": reliability,
        "viewpoint_exact_agreement": float((viewpoints_a == viewpoints_b).mean()),
        "viewpoint_unweighted_kappa": float(cohen_kappa_score(viewpoints_a, viewpoints_b)),
        "viewpoint_weighted_kappa": weighted_kappa,
        "viewpoint_weighted_kappa_ci95_lower": float(weighted_ci[0]),
        "viewpoint_weighted_kappa_ci95_upper": float(weighted_ci[1]),
        "viewpoint_evaluable_pair_count": len(viewpoint_valid),
        "viewpoint_unknown_excluded_pair_count": len(merged) - len(viewpoint_valid),
        "weighted_kappa_gate_status": "PASS" if weighted_pass else "FAIL",
        "weighted_kappa_method": "linear weights; ordinal order incompatible < partial < compatible; pair-level bootstrap 10,000 resamples, seed 20260713",
        "decision": decision,
        "claim_boundary": "Outcome-free reliability analysis only; no identity, reviewability, descriptor, score, rank, route, or outcome field was read.",
    }
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
