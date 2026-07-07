#!/usr/bin/env python3
"""Build the Phase17K Bobcat clarity-first review gate.

Phase17K replaces metadata-first 3000 selection with a strict visual clarity
gate. The output is a review pool, not a frozen algorithm manifest: only rows
manually marked clear may enter the final Bobcat 3000.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase17/phase17e_external_source_probe/"
    / "prototype_phase17e_inat_research_grade_bobcat_organism_candidates.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17k_bobcat_clarity_gate"
POOL_CSV = OUTPUT_DIR / "phase17k_bobcat_clarity_gate_pool.csv"
PRIOR_AUDITS = [
    PROJECT_ROOT / "outputs/phase17/phase17e_inat_yesno_audit/phase17e_inat_bobcat_yesno_working.csv",
    PROJECT_ROOT / "outputs/phase17/phase17f_inat_organism_yesno_audit/phase17e_inat_bobcat_yesno_working.csv",
    PROJECT_ROOT / "outputs/phase17/phase17g_inat_alive_yesno_audit/phase17e_inat_bobcat_yesno_working.csv",
    PROJECT_ROOT
    / "outputs/phase17/phase17h_inat_auto_selected_3000_spot_audit/phase17e_inat_bobcat_yesno_working.csv",
    PROJECT_ROOT
    / "outputs/phase17/phase17j_inat_human_calibrated_3000_spot_audit/phase17e_inat_bobcat_yesno_working.csv",
]

CLARITY_COLUMNS = [
    "phase17k_clarity_gate_decision",
    "phase17k_clarity_reject_reason",
    "phase17k_clarity_notes",
    "phase17k_clarity_audited_at_utc",
    "phase17k_prior_human_quality_label",
    "phase17k_prior_human_source",
    "phase17k_auto_reject_reason",
    "phase17k_auto_keep",
    "phase17k_algorithm_entry_rule",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def collect_prior_labels() -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for audit_path in PRIOR_AUDITS:
        if not audit_path.exists():
            continue
        for row in read_rows(audit_path):
            decision = row.get("human_quality_yes_no", "")
            if decision not in {"yes", "no"}:
                continue
            candidate_id = row.get("candidate_id", "")
            if not candidate_id:
                continue
            labels.setdefault(candidate_id, {"yes": "0", "no": "0", "source": ""})
            labels[candidate_id][decision] = str(int(labels[candidate_id][decision]) + 1)
            labels[candidate_id]["source"] = audit_path.name
    return labels


def auto_reject_reason(row: dict[str, str], prior: dict[str, str] | None) -> str:
    if row.get("evidence_organism") == "no":
        return "not_organism_annotation"
    if row.get("alive_dead") == "dead":
        return "dead_observation"
    if row.get("evidence_scat") == "yes":
        return "scat_annotation"
    if row.get("evidence_track") == "yes":
        return "track_annotation"
    if row.get("captive") == "true":
        return "captive_observation"
    if prior and int(prior.get("no", "0")) > 0 and int(prior.get("yes", "0")) == 0:
        return "prior_human_not_usable"
    return ""


def place_specificity(row: dict[str, str]) -> int:
    place = row.get("place_guess", "")
    return place.count(",")


def build_pool() -> dict[str, object]:
    source_rows = read_rows(SOURCE_CSV)
    prior_labels = collect_prior_labels()
    output_rows: list[dict[str, str]] = []
    reject_counts: Counter[str] = Counter()
    seen_observations: set[str] = set()

    for row in source_rows:
        candidate_id = row.get("candidate_id", "")
        prior = prior_labels.get(candidate_id)
        reject_reason = auto_reject_reason(row, prior)
        if reject_reason:
            reject_counts[reject_reason] += 1
            continue
        observation_id = row.get("observation_id", "")
        if observation_id in seen_observations:
            reject_counts["duplicate_observation_extra_photo"] += 1
            continue
        seen_observations.add(observation_id)

        prior_yes = bool(prior and int(prior.get("yes", "0")) > 0 and int(prior.get("no", "0")) == 0)
        row = dict(row)
        row["phase17k_clarity_gate_decision"] = "clear" if prior_yes else ""
        row["phase17k_clarity_reject_reason"] = ""
        row["phase17k_clarity_notes"] = "seeded from prior human YES" if prior_yes else ""
        row["phase17k_clarity_audited_at_utc"] = (
            datetime.now(timezone.utc).isoformat(timespec="seconds") if prior_yes else ""
        )
        row["phase17k_prior_human_quality_label"] = "yes" if prior_yes else ""
        row["phase17k_prior_human_source"] = prior.get("source", "") if prior else ""
        row["phase17k_auto_reject_reason"] = ""
        row["phase17k_auto_keep"] = "yes"
        row["phase17k_algorithm_entry_rule"] = (
            "ONLY phase17k_clarity_gate_decision=clear may enter Bobcat algorithm-entry 3000"
        )
        output_rows.append(row)

    output_rows.sort(
        key=lambda row: (
            row["phase17k_clarity_gate_decision"] != "clear",
            -place_specificity(row),
            row.get("observed_on", ""),
            row.get("candidate_id", ""),
        )
    )

    fieldnames = list(source_rows[0].keys()) + [column for column in CLARITY_COLUMNS if column not in source_rows[0]]
    write_rows(POOL_CSV, output_rows, fieldnames)

    clear_count = sum(1 for row in output_rows if row["phase17k_clarity_gate_decision"] == "clear")
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_csv": str(SOURCE_CSV),
        "output_pool_csv": str(POOL_CSV),
        "input_photo_rows": len(source_rows),
        "pool_rows": len(output_rows),
        "seeded_prior_clear_rows": clear_count,
        "pending_clarity_rows": len(output_rows) - clear_count,
        "auto_reject_counts": dict(reject_counts),
        "final_3000_freeze_rule": "Do not freeze final Bobcat 3000 until at least 3000 rows are manually clear.",
        "clarity_standard": {
            "clear": "bobcat visibly sharp enough for individual-review comparison; not tiny/far, not severe blur, not severe occlusion, not sign/dead-only",
            "not_clear": "any uncertainty about visual comparability rejects the row from algorithm-entry 3000",
        },
    }
    (OUTPUT_DIR / "phase17k_bobcat_clarity_gate_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = [
        "# Phase17K Bobcat Clarity Gate",
        "",
        "Phase17K is a clarity-first replacement for the failed metadata-first Bobcat 3000 selection.",
        "",
        "## Hard Rule",
        "",
        "Only rows with `phase17k_clarity_gate_decision=clear` may enter the final Bobcat algorithm-entry 3000.",
        "",
        "A row is NOT CLEAR if the bobcat is tiny/far, blurred, motion-smeared, severely occluded, dead/sign-only, or otherwise not visually comparable.",
        "",
        "## Counts",
        "",
        f"- Input photo rows: {len(source_rows)}",
        f"- Review pool rows: {len(output_rows)}",
        f"- Seeded prior clear rows: {clear_count}",
        f"- Pending clarity rows: {len(output_rows) - clear_count}",
        "",
        "## Auto Reject Counts",
        "",
    ]
    for key, value in sorted(reject_counts.items()):
        report.append(f"- {key}: {value}")
    report.extend(
        [
            "",
            "## Decision",
            "",
            "The earlier Phase17H/Phase17J pools are not valid final Bobcat 3000 manifests because metadata filters did not enforce visual clarity.",
            "Phase17K is the required gate before algorithm design.",
        ]
    )
    (OUTPUT_DIR / "phase17k_bobcat_clarity_gate_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(SOURCE_CSV)
    audit = build_pool()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
