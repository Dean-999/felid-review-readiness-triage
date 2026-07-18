#!/usr/bin/env python3
"""Build Phase17D Bobcat manual-audit gate and final-freeze decision."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_SHEET = (
    PROJECT_ROOT
    / "outputs/phase17/phase17c_bobcat_provisional_3000/phase17c_bobcat_manual_audit_expansion_sheet.csv"
)
DEFAULT_PROVISIONAL_MANIFEST = (
    PROJECT_ROOT
    / "outputs/phase17/phase17c_bobcat_provisional_3000/phase17c_bobcat_provisional_3000_manifest.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17d_bobcat_manual_audit_gate"

SUMMARY_CSV = "phase17d_bobcat_manual_audit_summary.csv"
ROUTE_AGREEMENT_CSV = "phase17d_bobcat_route_agreement.csv"
DECISION_CSV = "phase17d_bobcat_algorithm_entry_decision.csv"
ENRICHED_AUDIT_CSV = "phase17d_bobcat_manual_audit_enriched.csv"
AUDIT_JSON = "phase17d_bobcat_manual_audit_gate_audit.json"
REPORT_MD = "phase17d_bobcat_final_freeze_recommendation.md"

REQUIRED_AUDIT_COLUMNS = [
    "candidate_id",
    "phase17c_selection_role",
    "phase17c_manual_audit_reason",
    "is_bobcat_visible",
    "is_individual_review_usable",
    "selection_role_agreement",
    "algorithm_entry_allowed",
]

KEY_ROLES = ["clean_backbone", "transfer_sentinel"]
TRUE_VALUES = {"true", "1", "yes", "y", "allow", "allowed", "pass", "usable"}
FALSE_VALUES = {"false", "0", "no", "n", "block", "blocked", "fail", "not_usable"}

DEFAULT_CLEAN_ALLOWED_GATE = 0.90
DEFAULT_TRANSFER_ALLOWED_GATE = 0.70
DEFAULT_MIN_COMPLETED_PER_ROLE = 20


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def normalize_bool(value: object) -> bool | None:
    text = normalize_text(value)
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    if text == "":
        return None
    return None


def bool_from_column(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].map(normalize_bool)


def load_audit_sheet(audit_sheet: Path) -> pd.DataFrame:
    frame = pd.read_csv(audit_sheet, low_memory=False)
    missing = [column for column in REQUIRED_AUDIT_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError("Phase17D audit sheet missing required columns: " + ", ".join(missing))
    if frame["candidate_id"].duplicated().any():
        duplicate_count = int(frame["candidate_id"].duplicated().sum())
        raise ValueError(f"Phase17D audit sheet candidate_id duplicate_count={duplicate_count}")
    return frame


def enrich_audit_sheet(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["phase17d_is_bobcat_visible_bool"] = bool_from_column(out, "is_bobcat_visible")
    out["phase17d_is_individual_review_usable_bool"] = bool_from_column(out, "is_individual_review_usable")
    out["phase17d_selection_role_agreement_bool"] = bool_from_column(out, "selection_role_agreement")
    out["phase17d_algorithm_entry_allowed_bool"] = bool_from_column(out, "algorithm_entry_allowed")
    required_bool_cols = [
        "phase17d_is_bobcat_visible_bool",
        "phase17d_is_individual_review_usable_bool",
        "phase17d_selection_role_agreement_bool",
        "phase17d_algorithm_entry_allowed_bool",
    ]
    out["phase17d_required_fields_complete"] = out[required_bool_cols].notna().all(axis=1)
    out["phase17d_audit_scope"] = "supporting_or_rejected_audit"
    out.loc[out["phase17c_selection_role"].isin(KEY_ROLES), "phase17d_audit_scope"] = "selected_role_gate"
    out["phase17d_failure_reason"] = ""
    out.loc[
        out["phase17d_required_fields_complete"] & ~out["phase17d_is_bobcat_visible_bool"].astype(bool),
        "phase17d_failure_reason",
    ] = "not_bobcat_visible"
    out.loc[
        out["phase17d_required_fields_complete"]
        & out["phase17d_is_bobcat_visible_bool"].astype(bool)
        & ~out["phase17d_is_individual_review_usable_bool"].astype(bool),
        "phase17d_failure_reason",
    ] = "not_individual_review_usable"
    out.loc[
        out["phase17d_required_fields_complete"]
        & out["phase17d_is_bobcat_visible_bool"].astype(bool)
        & out["phase17d_is_individual_review_usable_bool"].astype(bool)
        & ~out["phase17d_algorithm_entry_allowed_bool"].astype(bool),
        "phase17d_failure_reason",
    ] = "algorithm_entry_not_allowed"
    out.loc[
        out["phase17d_required_fields_complete"]
        & out["phase17d_algorithm_entry_allowed_bool"].astype(bool)
        & ~out["phase17d_selection_role_agreement_bool"].astype(bool),
        "phase17d_failure_reason",
    ] = "selection_role_disagreement"
    return out


def summarize_manual_audit(enriched: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groupers = {
        "all": pd.Series("all", index=enriched.index),
        "selection_role": enriched["phase17c_selection_role"].fillna(""),
        "audit_reason": enriched["phase17c_manual_audit_reason"].fillna(""),
        "source_tier": enriched["source_tier"].astype(str) if "source_tier" in enriched else pd.Series("", index=enriched.index),
    }
    for grouping, labels in groupers.items():
        for value, group in enriched.groupby(labels, dropna=False):
            complete = group["phase17d_required_fields_complete"]
            completed = group[complete].copy()
            rows.append(
                {
                    "grouping": grouping,
                    "value": str(value),
                    "rows": int(len(group)),
                    "completed_rows": int(len(completed)),
                    "completion_rate": float(complete.mean()) if len(group) else 0.0,
                    "bobcat_visible_rate": rate(completed, "phase17d_is_bobcat_visible_bool"),
                    "individual_review_usable_rate": rate(completed, "phase17d_is_individual_review_usable_bool"),
                    "selection_role_agreement_rate": rate(completed, "phase17d_selection_role_agreement_bool"),
                    "algorithm_entry_allowed_rate": rate(completed, "phase17d_algorithm_entry_allowed_bool"),
                    "failure_rows": int((completed["phase17d_algorithm_entry_allowed_bool"] == False).sum())
                    if len(completed)
                    else 0,
                }
            )
    return pd.DataFrame(rows)


def rate(frame: pd.DataFrame, column: str) -> float:
    if frame.empty:
        return float("nan")
    values = frame[column].dropna()
    if values.empty:
        return float("nan")
    return float(values.astype(bool).mean())


def build_route_agreement(enriched: pd.DataFrame) -> pd.DataFrame:
    if "phase17b_route" not in enriched.columns:
        return pd.DataFrame()
    completed = enriched[enriched["phase17d_required_fields_complete"]].copy()
    if completed.empty:
        return pd.DataFrame(
            columns=[
                "phase17b_route",
                "completed_rows",
                "algorithm_entry_allowed_rate",
                "selection_role_agreement_rate",
                "individual_review_usable_rate",
            ]
        )
    return (
        completed.groupby("phase17b_route", dropna=False)
        .agg(
            completed_rows=("candidate_id", "count"),
            algorithm_entry_allowed_rate=("phase17d_algorithm_entry_allowed_bool", lambda s: float(s.astype(bool).mean())),
            selection_role_agreement_rate=("phase17d_selection_role_agreement_bool", lambda s: float(s.astype(bool).mean())),
            individual_review_usable_rate=("phase17d_is_individual_review_usable_bool", lambda s: float(s.astype(bool).mean())),
        )
        .reset_index()
        .sort_values("completed_rows", ascending=False)
    )


def role_stats(enriched: pd.DataFrame, role: str) -> dict[str, object]:
    role_rows = enriched[enriched["phase17c_selection_role"].eq(role)].copy()
    completed = role_rows[role_rows["phase17d_required_fields_complete"]].copy()
    return {
        "role": role,
        "rows": int(len(role_rows)),
        "completed_rows": int(len(completed)),
        "completion_rate": float(len(completed) / len(role_rows)) if len(role_rows) else 0.0,
        "algorithm_entry_allowed_rate": rate(completed, "phase17d_algorithm_entry_allowed_bool"),
        "selection_role_agreement_rate": rate(completed, "phase17d_selection_role_agreement_bool"),
        "individual_review_usable_rate": rate(completed, "phase17d_is_individual_review_usable_bool"),
    }


def decide_freeze_state(
    enriched: pd.DataFrame,
    clean_allowed_gate: float = DEFAULT_CLEAN_ALLOWED_GATE,
    transfer_allowed_gate: float = DEFAULT_TRANSFER_ALLOWED_GATE,
    min_completed_per_role: int = DEFAULT_MIN_COMPLETED_PER_ROLE,
) -> tuple[pd.DataFrame, dict[str, object]]:
    clean = role_stats(enriched, "clean_backbone")
    transfer = role_stats(enriched, "transfer_sentinel")
    clean_completed = int(clean["completed_rows"])
    transfer_completed = int(transfer["completed_rows"])
    clean_rate = float(clean["algorithm_entry_allowed_rate"]) if pd.notna(clean["algorithm_entry_allowed_rate"]) else float("nan")
    transfer_rate = (
        float(transfer["algorithm_entry_allowed_rate"])
        if pd.notna(transfer["algorithm_entry_allowed_rate"])
        else float("nan")
    )

    if clean_completed < min_completed_per_role or transfer_completed < min_completed_per_role:
        decision = "BLOCKED_PENDING_AUDIT"
        recommendation = "Complete manual audit fields for enough clean-backbone and transfer-sentinel rows."
    elif clean_rate < clean_allowed_gate:
        decision = "REVISE"
        recommendation = "Revise Bobcat provisional 3000 selection before algorithm entry; clean-backbone audit gate failed."
    elif transfer_rate < transfer_allowed_gate:
        decision = "PASS_WITH_SPLIT"
        recommendation = (
            "Allow clean backbone into main algorithm-entry manifest, but keep transfer sentinels as a separate "
            "stress-test split until revised or further audited."
        )
    else:
        decision = "PASS"
        recommendation = "Allow provisional 2700 clean-backbone plus 300 transfer-sentinel manifest to proceed."

    rows = [clean, transfer]
    decision_frame = pd.DataFrame(rows)
    decision_frame["clean_allowed_gate"] = clean_allowed_gate
    decision_frame["transfer_allowed_gate"] = transfer_allowed_gate
    decision_frame["min_completed_per_role"] = min_completed_per_role
    decision_frame["freeze_decision"] = decision
    decision_frame["recommendation"] = recommendation

    audit = {
        "created_at": utc_now(),
        "status": "PASS" if decision in {"PASS", "PASS_WITH_SPLIT"} else decision,
        "freeze_decision": decision,
        "recommendation": recommendation,
        "clean_backbone": clean,
        "transfer_sentinel": transfer,
        "clean_allowed_gate": clean_allowed_gate,
        "transfer_allowed_gate": transfer_allowed_gate,
        "min_completed_per_role": min_completed_per_role,
        "claim_status": "MANUAL_AUDIT_GATE_ONLY",
        "claim_boundary": (
            "Phase17D evaluates manual review-readiness for Bobcat algorithm entry. "
            "It does not evaluate Bobcat identity accuracy."
        ),
    }
    return decision_frame, audit


def write_report(output_dir: Path, audit: dict[str, object], summary: pd.DataFrame) -> None:
    clean = audit["clean_backbone"]
    transfer = audit["transfer_sentinel"]
    lines = [
        "# Phase17D Bobcat Manual-Audit Gate",
        "",
        "This report turns Phase17C manual-audit outcomes into a conservative final-freeze recommendation.",
        "It does not evaluate Bobcat identity accuracy.",
        "",
        "## Decision",
        "",
        f"- Freeze decision: `{audit['freeze_decision']}`.",
        f"- Recommendation: {audit['recommendation']}",
        f"- Claim status: `{audit['claim_status']}`.",
        "",
        "## Role Gates",
        "",
        "| role | rows | completed | allowed rate | agreement rate | usable rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        role_line(clean),
        role_line(transfer),
        "",
        "## Gate Thresholds",
        "",
        f"- Clean-backbone allowed gate: {audit['clean_allowed_gate']:.2f}.",
        f"- Transfer-sentinel allowed gate: {audit['transfer_allowed_gate']:.2f}.",
        f"- Minimum completed rows per role: {audit['min_completed_per_role']}.",
        "",
        "## Boundary",
        "",
        str(audit["claim_boundary"]),
        "",
        "## Files",
        "",
        f"- `{SUMMARY_CSV}`",
        f"- `{ROUTE_AGREEMENT_CSV}`",
        f"- `{DECISION_CSV}`",
        f"- `{ENRICHED_AUDIT_CSV}`",
        f"- `{AUDIT_JSON}`",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def role_line(stats: dict[str, object]) -> str:
    return (
        f"| `{stats['role']}` | {int(stats['rows'])} | {int(stats['completed_rows'])} | "
        f"{format_rate(stats['algorithm_entry_allowed_rate'])} | "
        f"{format_rate(stats['selection_role_agreement_rate'])} | "
        f"{format_rate(stats['individual_review_usable_rate'])} |"
    )


def format_rate(value: object) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "nan"
    if pd.isna(numeric):
        return "nan"
    return f"{numeric:.4f}"


def run_phase17d_bobcat_manual_audit_gate(
    audit_sheet: Path = DEFAULT_AUDIT_SHEET,
    provisional_manifest: Path = DEFAULT_PROVISIONAL_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    clean_allowed_gate: float = DEFAULT_CLEAN_ALLOWED_GATE,
    transfer_allowed_gate: float = DEFAULT_TRANSFER_ALLOWED_GATE,
    min_completed_per_role: int = DEFAULT_MIN_COMPLETED_PER_ROLE,
) -> dict[str, object]:
    raw = load_audit_sheet(audit_sheet)
    enriched = enrich_audit_sheet(raw)
    summary = summarize_manual_audit(enriched)
    route = build_route_agreement(enriched)
    decision, audit = decide_freeze_state(
        enriched,
        clean_allowed_gate=clean_allowed_gate,
        transfer_allowed_gate=transfer_allowed_gate,
        min_completed_per_role=min_completed_per_role,
    )
    audit["audit_sheet"] = str(audit_sheet)
    audit["provisional_manifest"] = str(provisional_manifest)
    audit["output_dir"] = str(output_dir)
    audit["manual_audit_rows"] = int(len(raw))
    audit["provisional_manifest_exists"] = provisional_manifest.exists()

    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / SUMMARY_CSV, index=False)
    route.to_csv(output_dir / ROUTE_AGREEMENT_CSV, index=False)
    decision.to_csv(output_dir / DECISION_CSV, index=False)
    enriched.to_csv(output_dir / ENRICHED_AUDIT_CSV, index=False)
    (output_dir / AUDIT_JSON).write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(output_dir, audit, summary)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-sheet", type=Path, default=DEFAULT_AUDIT_SHEET)
    parser.add_argument("--provisional-manifest", type=Path, default=DEFAULT_PROVISIONAL_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--clean-allowed-gate", type=float, default=DEFAULT_CLEAN_ALLOWED_GATE)
    parser.add_argument("--transfer-allowed-gate", type=float, default=DEFAULT_TRANSFER_ALLOWED_GATE)
    parser.add_argument("--min-completed-per-role", type=int, default=DEFAULT_MIN_COMPLETED_PER_ROLE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = run_phase17d_bobcat_manual_audit_gate(
        audit_sheet=args.audit_sheet,
        provisional_manifest=args.provisional_manifest,
        output_dir=args.output_dir,
        clean_allowed_gate=args.clean_allowed_gate,
        transfer_allowed_gate=args.transfer_allowed_gate,
        min_completed_per_role=args.min_completed_per_role,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
