#!/usr/bin/env python3
"""Run Phase18A-G in dependency order."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.phase18_pipeline_utils import PROJECT_ROOT, now_utc, write_json
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import PROJECT_ROOT, now_utc, write_json


OUTPUT_DIR = PROJECT_ROOT / "outputs/phase18/phase18_all_pipeline"
AUDIT_JSON = OUTPUT_DIR / "phase18_all_pipeline_audit.json"


STEPS = [
    ("phase18a", "scripts/build_phase18a_frozen_feature_manifest.py"),
    ("phase18b", "scripts/build_phase18b_local_descriptor_control.py"),
    ("phase18c", "scripts/build_phase18c_czechlynx_pair_contract.py"),
    ("phase18d", "scripts/build_phase18d_pf_eri_pair_features.py"),
    ("phase18e", "scripts/build_phase18e_review_router.py"),
    ("phase18f", "scripts/build_phase18f_bobcat_transfer_readiness.py"),
    ("phase18g", "scripts/build_phase18g_strong_baseline_claim_gate.py"),
]


def run_step(script: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3", script],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "script": script,
        "exit_code": completed.returncode,
        "output_tail": completed.stdout[-4000:],
    }


def run_pipeline(stop_on_failure: bool = True) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for step_id, script in STEPS:
        result = {"step_id": step_id, **run_step(script)}
        results.append(result)
        if stop_on_failure and result["exit_code"] != 0:
            break
    audit = {
        "built_at_utc": now_utc(),
        "step_count": len(STEPS),
        "executed_step_count": len(results),
        "results": results,
        "status": "PASS" if len(results) == len(STEPS) and all(row["exit_code"] == 0 for row in results) else "FAIL",
        "claim_boundary": (
            "Automated Phase18 local-control pipeline plus Phase18G strong-baseline "
            "claim gate. Final scientific claims remain blocked until strong "
            "descriptor artifacts are supplied."
        ),
    }
    write_json(AUDIT_JSON, audit)
    (OUTPUT_DIR / "README.md").write_text(
        "# Phase18 All Pipeline\n\nRuns Phase18A-G in dependency order and records "
        "each step exit code. Phase18G blocks final claims until strong descriptor "
        "artifacts are available.\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-going", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = run_pipeline(stop_on_failure=not args.keep_going)
    print(json.dumps({"status": audit["status"], "executed_step_count": audit["executed_step_count"]}, indent=2))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
