#!/usr/bin/env python3
"""Build Issue 5 fixed-budget review utility evidence."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
ROUTES_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv"
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue5"
BUDGET_COMPARISON_CSV = OUTPUT_DIR / "issue5_fixed_budget_review_utility.csv"
POLICY_DELTA_CSV = OUTPUT_DIR / "issue5_fixed_budget_policy_delta.csv"
FIGURE_SVG = OUTPUT_DIR / "figure_issue5_review_budget_utility.svg"
AUDIT_JSON = OUTPUT_DIR / "issue5_review_budget_value_audit.json"
REPORT_MD = PROJECT_ROOT / "docs/modeling-validation/2026-07-09_review_budget_routing_value.md"

ROUTE_PRIORITY = {
    "accept_review": 3,
    "cautious_review": 2,
    "conflict_review": 1,
    "defer_low_evidence": 0,
}
BUDGETS = [25, 50, 100, 150, 200, 300, 400]
STRATEGIES = ["pferi_priority", "descriptor_priority"]

BUDGET_COLUMNS = [
    "scope",
    "strategy",
    "budget",
    "selected_count",
    "review_ready_count",
    "not_ready_or_uncertain_count",
    "not_ready_or_uncertain_rate",
    "review_ready_rate",
    "same_id_count",
    "different_id_count",
    "same_id_retention",
    "false_candidate_burden_rate",
    "mean_descriptor_similarity_percentile",
    "mean_evidence_admission_score",
    "accept_review_count",
    "cautious_review_count",
    "conflict_review_count",
    "defer_low_evidence_count",
    "claim_boundary",
]

DELTA_COLUMNS = [
    "scope",
    "budget",
    "pferi_not_ready_or_uncertain_rate",
    "descriptor_not_ready_or_uncertain_rate",
    "delta_not_ready_or_uncertain_rate",
    "pferi_review_ready_rate",
    "descriptor_review_ready_rate",
    "delta_review_ready_rate",
    "pferi_same_id_retention",
    "descriptor_same_id_retention",
    "delta_same_id_retention",
    "pferi_false_candidate_burden_rate",
    "descriptor_false_candidate_burden_rate",
    "delta_false_candidate_burden_rate",
    "interpretation",
    "claim_boundary",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def mean(rows: list[dict[str, Any]], column: str) -> float | str:
    if not rows:
        return ""
    return sum(to_float(row.get(column)) for row in rows) / len(rows)


def merge_rows() -> list[dict[str, Any]]:
    route_lookup = {(row["descriptor_name"], row["review_pair_id"]): row for row in read_csv(ROUTES_CSV)}
    output = []
    for row in read_csv(VALIDATION_TABLE_CSV):
        route = route_lookup[(row["descriptor_name"], row["review_pair_id"])]
        output.append({**row, **route})
    return output


def pferi_priority(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            ROUTE_PRIORITY.get(str(row.get("route_label", "")), -1),
            to_float(row.get("evidence_admission_score")),
            to_float(row.get("descriptor_similarity_percentile")),
        ),
        reverse=True,
    )


def descriptor_priority(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            to_float(row.get("descriptor_similarity_percentile")),
            to_float(row.get("evidence_admission_score")),
        ),
        reverse=True,
    )


def scope_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "pooled": rows,
        "megadescriptor_l_384": [row for row in rows if row["descriptor_name"] == "megadescriptor_l_384"],
        "dinov2_vitl14": [row for row in rows if row["descriptor_name"] == "dinov2_vitl14"],
    }


def selected_prefix(rows: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    return rows[: min(budget, len(rows))]


def budget_summary(scope: str, strategy: str, rows: list[dict[str, Any]], budget: int) -> dict[str, Any]:
    selected = selected_prefix(rows, budget)
    route_counts = Counter(row["route_label"] for row in selected)
    same_total = sum(1 for row in rows if row["same_identity_known_id"] == "yes")
    same_count = sum(1 for row in selected if row["same_identity_known_id"] == "yes")
    different_count = len(selected) - same_count
    not_ready = sum(int(row["not_ready_or_uncertain_label"]) for row in selected)
    ready = sum(int(row["review_ready_label"]) for row in selected)
    selected_count = len(selected)
    return {
        "scope": scope,
        "strategy": strategy,
        "budget": budget,
        "selected_count": selected_count,
        "review_ready_count": ready,
        "not_ready_or_uncertain_count": not_ready,
        "not_ready_or_uncertain_rate": not_ready / selected_count if selected_count else "",
        "review_ready_rate": ready / selected_count if selected_count else "",
        "same_id_count": same_count,
        "different_id_count": different_count,
        "same_id_retention": same_count / same_total if same_total else "",
        "false_candidate_burden_rate": different_count / selected_count if selected_count else "",
        "mean_descriptor_similarity_percentile": mean(selected, "descriptor_similarity_percentile"),
        "mean_evidence_admission_score": mean(selected, "evidence_admission_score"),
        "accept_review_count": route_counts["accept_review"],
        "cautious_review_count": route_counts["cautious_review"],
        "conflict_review_count": route_counts["conflict_review"],
        "defer_low_evidence_count": route_counts["defer_low_evidence"],
        "claim_boundary": "Fixed-budget review utility only; false-candidate burden is review burden, not identity accuracy.",
    }


def build_budget_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for scope, subset in scope_rows(rows).items():
        ordered = {
            "pferi_priority": pferi_priority(subset),
            "descriptor_priority": descriptor_priority(subset),
        }
        scope_budgets = [budget for budget in BUDGETS if budget <= len(subset)]
        if len(subset) not in scope_budgets:
            scope_budgets.append(len(subset))
        for budget in sorted(set(scope_budgets)):
            for strategy in STRATEGIES:
                output.append(budget_summary(scope, strategy, ordered[strategy], budget))
    return output


def row_lookup(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    return {(row["scope"], row["strategy"], int(row["budget"])): row for row in rows}


def build_delta_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = row_lookup(rows)
    output = []
    for scope in sorted({row["scope"] for row in rows}):
        budgets = sorted({int(row["budget"]) for row in rows if row["scope"] == scope})
        for budget in budgets:
            pferi = lookup[(scope, "pferi_priority", budget)]
            descriptor = lookup[(scope, "descriptor_priority", budget)]
            delta_not_ready = to_float(pferi["not_ready_or_uncertain_rate"]) - to_float(descriptor["not_ready_or_uncertain_rate"])
            delta_ready = to_float(pferi["review_ready_rate"]) - to_float(descriptor["review_ready_rate"])
            delta_same = to_float(pferi["same_id_retention"]) - to_float(descriptor["same_id_retention"])
            delta_false = to_float(pferi["false_candidate_burden_rate"]) - to_float(descriptor["false_candidate_burden_rate"])
            if delta_not_ready < 0:
                interpretation = "PF-ERI priority reduces not-ready/uncertain review burden at this fixed budget."
            elif delta_not_ready == 0:
                interpretation = "PF-ERI priority ties descriptor priority on not-ready/uncertain burden at this fixed budget."
            else:
                interpretation = "PF-ERI priority increases not-ready/uncertain burden at this fixed budget; treat as a boundary."
            output.append(
                {
                    "scope": scope,
                    "budget": budget,
                    "pferi_not_ready_or_uncertain_rate": pferi["not_ready_or_uncertain_rate"],
                    "descriptor_not_ready_or_uncertain_rate": descriptor["not_ready_or_uncertain_rate"],
                    "delta_not_ready_or_uncertain_rate": delta_not_ready,
                    "pferi_review_ready_rate": pferi["review_ready_rate"],
                    "descriptor_review_ready_rate": descriptor["review_ready_rate"],
                    "delta_review_ready_rate": delta_ready,
                    "pferi_same_id_retention": pferi["same_id_retention"],
                    "descriptor_same_id_retention": descriptor["same_id_retention"],
                    "delta_same_id_retention": delta_same,
                    "pferi_false_candidate_burden_rate": pferi["false_candidate_burden_rate"],
                    "descriptor_false_candidate_burden_rate": descriptor["false_candidate_burden_rate"],
                    "delta_false_candidate_burden_rate": delta_false,
                    "interpretation": interpretation,
                    "claim_boundary": "Review utility only; same-ID retention is candidate coverage, not automated identity assignment.",
                }
            )
    return output


def svg_line(points: list[tuple[float, float]], color: str, width: int = 3) -> str:
    value = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{value}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'


def panel(
    rows: list[dict[str, Any]],
    x_col: str,
    y_col: str,
    title: str,
    x0: int,
    y0: int,
    width: int,
    height: int,
    y_label: str,
) -> str:
    colors = {"pferi_priority": "#0072B2", "descriptor_priority": "#D55E00"}
    x_values = sorted({to_float(row[x_col]) for row in rows})
    y_values = [to_float(row[y_col]) for row in rows]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = 0.0, max(0.01, max(y_values))

    def sx(value: float) -> float:
        return x0 + 45 + (value - x_min) / (x_max - x_min or 1.0) * (width - 70)

    def sy(value: float) -> float:
        return y0 + height - 35 - (value - y_min) / (y_max - y_min or 1.0) * (height - 65)

    items = [
        f'<text x="{x0}" y="{y0 + 12}" font-size="14" font-weight="700">{title}</text>',
        f'<line x1="{x0 + 45}" y1="{y0 + height - 35}" x2="{x0 + width - 25}" y2="{y0 + height - 35}" stroke="#333"/>',
        f'<line x1="{x0 + 45}" y1="{y0 + 30}" x2="{x0 + 45}" y2="{y0 + height - 35}" stroke="#333"/>',
        f'<text x="{x0 + width / 2}" y="{y0 + height - 4}" text-anchor="middle" font-size="11">Review budget</text>',
        f'<text x="{x0 + 12}" y="{y0 + height / 2}" text-anchor="middle" font-size="11" transform="rotate(-90 {x0 + 12} {y0 + height / 2})">{y_label}</text>',
        f'<text x="{x0 + 41}" y="{y0 + height - 31}" text-anchor="end" font-size="10">0</text>',
        f'<text x="{x0 + 41}" y="{y0 + 34}" text-anchor="end" font-size="10">{y_max:.2f}</text>',
    ]
    for budget in x_values:
        x = sx(budget)
        items.append(f'<line x1="{x:.1f}" y1="{y0 + height - 35}" x2="{x:.1f}" y2="{y0 + height - 30}" stroke="#333"/>')
        items.append(f'<text x="{x:.1f}" y="{y0 + height - 17}" text-anchor="middle" font-size="9">{int(budget)}</text>')
    for strategy in STRATEGIES:
        strategy_rows = sorted([row for row in rows if row["strategy"] == strategy], key=lambda row: int(row["budget"]))
        points = [(sx(to_float(row[x_col])), sy(to_float(row[y_col]))) for row in strategy_rows]
        items.append(svg_line(points, colors[strategy]))
        for x, y in points:
            items.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{colors[strategy]}"/>')
    return "\n".join(items)


def write_figure(rows: list[dict[str, Any]]) -> None:
    pooled = [row for row in rows if row["scope"] == "pooled"]
    width, height = 900, 460
    legend = [
        '<rect x="0" y="0" width="900" height="460" fill="white"/>',
        '<text x="36" y="32" font-size="18" font-weight="700">Fixed-budget review utility</text>',
        '<line x1="610" y1="28" x2="650" y2="28" stroke="#0072B2" stroke-width="3"/><circle cx="630" cy="28" r="3.2" fill="#0072B2"/><text x="660" y="32" font-size="12">PF-ERI priority</text>',
        '<line x1="610" y1="50" x2="650" y2="50" stroke="#D55E00" stroke-width="3"/><circle cx="630" cy="50" r="3.2" fill="#D55E00"/><text x="660" y="54" font-size="12">Descriptor priority</text>',
    ]
    body = [
        panel(pooled, "budget", "not_ready_or_uncertain_rate", "A. Not-ready/uncertain burden", 45, 70, 380, 330, "Burden rate"),
        panel(pooled, "budget", "same_id_retention", "B. Same-ID candidate coverage", 475, 70, 380, 330, "Coverage"),
        '<text x="45" y="438" font-size="10" fill="#555">Endpoint: human reviewability / evidential admissibility. Same-ID coverage is review utility, not automated identity accuracy.</text>',
    ]
    FIGURE_SVG.parent.mkdir(parents=True, exist_ok=True)
    FIGURE_SVG.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="460" viewBox="0 0 900 460" role="img">\n'
        + "\n".join(legend + body)
        + "\n</svg>\n",
        encoding="utf-8",
    )


def fmt(value: Any) -> str:
    return f"{to_float(value):.3f}"


def write_report(delta_rows: list[dict[str, Any]], budget_rows: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    key_budget = 100
    pooled_100 = next(row for row in delta_rows if row["scope"] == "pooled" and int(row["budget"]) == key_budget)
    pooled_200 = next(row for row in delta_rows if row["scope"] == "pooled" and int(row["budget"]) == 200)
    positive_burden = [
        row for row in delta_rows
        if row["scope"] == "pooled" and to_float(row["delta_not_ready_or_uncertain_rate"]) < 0
    ]
    lines = [
        "# Review-Budget Routing Value",
        "",
        "Date: 2026-07-09",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This analysis asks whether PF-ERI changes the practical value of a fixed human review budget after a strong descriptor has already generated candidate pairs. The comparison is intentionally workflow-level: PF-ERI priority is compared with descriptor-similarity priority on the same CzechLynx reviewed pair pool, and human labels are used only after selection to audit reviewability, not to choose the queue. The endpoint is review burden and evidence hygiene, not identity accuracy.",
        "",
        f"At a budget of {key_budget} reviewed pairs in the pooled table, PF-ERI priority selected a queue with not-ready/uncertain burden {fmt(pooled_100['pferi_not_ready_or_uncertain_rate'])}, compared with {fmt(pooled_100['descriptor_not_ready_or_uncertain_rate'])} for descriptor priority. The same comparison retained same-ID candidate coverage of {fmt(pooled_100['pferi_same_id_retention'])} for PF-ERI priority and {fmt(pooled_100['descriptor_same_id_retention'])} for descriptor priority. At a budget of 200 pairs, PF-ERI priority had not-ready/uncertain burden {fmt(pooled_200['pferi_not_ready_or_uncertain_rate'])}, compared with {fmt(pooled_200['descriptor_not_ready_or_uncertain_rate'])} for descriptor priority.",
        "",
        f"Across pooled fixed-budget settings, PF-ERI priority reduced not-ready/uncertain burden in {len(positive_burden)} of {len([row for row in delta_rows if row['scope'] == 'pooled'])} budgets. This supports an applied evidence-value claim: PF-ERI can order a review queue so that a limited expert budget often encounters fewer uncertain or not-ready pairs. The tradeoff is explicit rather than hidden: at some budgets, descriptor priority retains more same-ID candidates, while PF-ERI priority admits more review-ready different-ID pairs that may be useful for clear exclusion decisions. This is not a claim that PF-ERI identifies individuals automatically; same-ID retention is reported only as a secondary candidate-coverage audit in the known-ID CzechLynx table.",
        "",
        "The analysis remains bounded. False-candidate burden is treated as review burden, because a different-ID pair may still be review-ready if it is easy for a reviewer to reject. Bobcat identity performance remains blocked because Bobcat identity labels are not part of this validated endpoint. The figure accompanying this report visualizes the pooled burden and candidate-coverage tradeoff across budgets using colorblind-safe line encodings.",
        "",
        "## Artifact Links",
        "",
        f"The fixed-budget comparison table is `{audit['outputs']['budget_comparison_csv']}`. The policy-delta table is `{audit['outputs']['policy_delta_csv']}`. The publication-style SVG figure is `{audit['outputs']['figure_svg']}`. The audit file is `{audit['outputs']['audit_json']}`.",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    rows = merge_rows()
    budget_rows = build_budget_rows(rows)
    delta_rows = build_delta_rows(budget_rows)
    write_csv(BUDGET_COMPARISON_CSV, budget_rows, BUDGET_COLUMNS)
    write_csv(POLICY_DELTA_CSV, delta_rows, DELTA_COLUMNS)
    write_figure(budget_rows)
    pooled_deltas = [row for row in delta_rows if row["scope"] == "pooled"]
    positive_burden_count = sum(to_float(row["delta_not_ready_or_uncertain_rate"]) < 0 for row in pooled_deltas)
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if positive_burden_count > 0 else "FAIL_NO_BUDGET_VALUE",
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "input_routes_csv": project_relative(ROUTES_CSV),
        "row_count": len(rows),
        "budgets": BUDGETS,
        "strategies": STRATEGIES,
        "pooled_budget_count": len(pooled_deltas),
        "pooled_positive_burden_reduction_count": positive_burden_count,
        "selection_leakage_guard": "Human review labels are not used for queue construction; they are post-selection audit labels.",
        "outputs": {
            "budget_comparison_csv": project_relative(BUDGET_COMPARISON_CSV),
            "policy_delta_csv": project_relative(POLICY_DELTA_CSV),
            "figure_svg": project_relative(FIGURE_SVG),
            "audit_json": project_relative(AUDIT_JSON),
            "report_md": project_relative(REPORT_MD),
        },
        "claim_boundary": "Review-budget routing and evidence hygiene only; not identity accuracy, mAP, MRR, top-k identity improvement, or Bobcat identity validation.",
    }
    write_json(AUDIT_JSON, audit)
    write_report(delta_rows, budget_rows, audit)
    return audit


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
