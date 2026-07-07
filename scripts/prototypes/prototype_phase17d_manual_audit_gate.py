#!/usr/bin/env python3
"""PROTOTYPE - throwaway Phase17D manual-audit decision explorer.

Question: do the final-freeze states feel right before we rely on them?

One command:
python3 scripts/prototypes/prototype_phase17d_manual_audit_gate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_phase17d_bobcat_manual_audit_gate import (
    decide_freeze_state,
    enrich_audit_sheet,
)


def rows(clean_allowed: int, clean_blocked: int, transfer_allowed: int, transfer_blocked: int) -> pd.DataFrame:
    data = []
    idx = 0
    for role, allowed, blocked in [
        ("clean_backbone", clean_allowed, clean_blocked),
        ("transfer_sentinel", transfer_allowed, transfer_blocked),
    ]:
        for _ in range(allowed):
            idx += 1
            data.append(row(idx, role, "yes"))
        for _ in range(blocked):
            idx += 1
            data.append(row(idx, role, "no"))
    return pd.DataFrame(data)


def blank_rows() -> pd.DataFrame:
    data = []
    for idx, role in enumerate(["clean_backbone"] * 20 + ["transfer_sentinel"] * 20, start=1):
        data.append(
            {
                "candidate_id": f"blank_{idx:04d}",
                "phase17c_selection_role": role,
                "phase17c_manual_audit_reason": f"selected_{role}",
                "source_tier": "1" if role == "clean_backbone" else "2",
                "phase17b_route": "high_confidence_review" if role == "clean_backbone" else "topup_stress_review",
                "is_bobcat_visible": "",
                "is_individual_review_usable": "",
                "selection_role_agreement": "",
                "algorithm_entry_allowed": "",
            }
        )
    return pd.DataFrame(data)


def row(idx: int, role: str, allowed: str) -> dict[str, object]:
    return {
        "candidate_id": f"demo_{idx:04d}",
        "phase17c_selection_role": role,
        "phase17c_manual_audit_reason": f"selected_{role}",
        "source_tier": "1" if role == "clean_backbone" else "2",
        "phase17b_route": "high_confidence_review" if role == "clean_backbone" else "topup_stress_review",
        "is_bobcat_visible": "yes",
        "is_individual_review_usable": allowed,
        "selection_role_agreement": allowed,
        "algorithm_entry_allowed": allowed,
    }


def show(name: str, frame: pd.DataFrame) -> None:
    enriched = enrich_audit_sheet(frame)
    decision, audit = decide_freeze_state(enriched, min_completed_per_role=20)
    print("=" * 72)
    print(name)
    print(
        {
            "decision": audit["freeze_decision"],
            "recommendation": audit["recommendation"],
            "clean": audit["clean_backbone"],
            "transfer": audit["transfer_sentinel"],
        }
    )
    print(decision[["role", "completed_rows", "algorithm_entry_allowed_rate", "freeze_decision"]].to_string(index=False))


def main() -> None:
    print("PROTOTYPE - Phase17D manual-audit gate state explorer")
    show("blocked: audit rows exist but fields are blank", blank_rows())
    show("pass: clean and transfer pass gates", rows(38, 2, 32, 8))
    show("pass_with_split: clean passes, transfer fails", rows(38, 2, 20, 20))
    show("revise: clean fails", rows(30, 10, 32, 8))


if __name__ == "__main__":
    main()
