#!/usr/bin/env python3
"""Sync the v2 assisted working CSV back to the primary working CSV."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_NAME = "phase6_unique_500_v2_balanced"
WORKSPACE = PROJECT_ROOT / f"outputs/czechlynx/phase6/annotation_review_packages/{WORKFLOW_NAME}/assisted_annotation_workspace"
ASSISTED = WORKSPACE / "assisted_working" / f"czechlynx_{WORKFLOW_NAME}_assisted_working.csv"
PRIMARY = PROJECT_ROOT / f"data/labels/czechlynx/czechlynx_{WORKFLOW_NAME}_image_annotation_working.csv"


def main() -> None:
    backup = PRIMARY.with_name(f"{PRIMARY.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy2(PRIMARY, backup)
    shutil.copy2(ASSISTED, PRIMARY)
    print(f"synced {ASSISTED} to {PRIMARY}")
    print(f"backup: {backup}")


if __name__ == "__main__":
    main()
