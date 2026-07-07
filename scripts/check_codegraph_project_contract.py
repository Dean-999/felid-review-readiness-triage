#!/usr/bin/env python3
"""Check that CodeGraph is usable only as a code-navigation helper."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/project_structure/codegraph_contract"
AUDIT_JSON = OUTPUT_DIR / "codegraph_project_contract_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

REQUIRED_EXACT_PATHS = [
    "PROJECT_RULES.md",
    "AGENTS.md",
    "docs/structure/current_pipeline_manifest.md",
    "docs/structure/2026-07-01_phase18_gap_research_and_plan.md",
    "scripts/freeze_phase17_modeling_dataset.py",
]


def run_codegraph_status() -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["codegraph", "status"],
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        return 127, "codegraph executable not found"
    return completed.returncode, completed.stdout


def build_audit() -> dict[str, Any]:
    status_code, status_output = run_codegraph_status()
    exact_path_checks = {
        path: (PROJECT_ROOT / path).exists()
        for path in REQUIRED_EXACT_PATHS
    }
    return {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "codegraph_dir_exists": (PROJECT_ROOT / ".codegraph").exists(),
        "codegraph_status_exit_code": status_code,
        "codegraph_status_output": status_output,
        "required_exact_path_checks": exact_path_checks,
        "contract": {
            "allowed": [
                "locate scripts",
                "understand functions",
                "trace implementation call paths",
                "inspect blast radius before edits",
            ],
            "forbidden_as_source_of_truth": [
                "CSV row counts",
                "photo validity",
                "image quality",
                "phase completion",
                "scientific claim boundaries",
                "human review decisions",
            ],
            "binding_rule": (
                "CodeGraph can answer where the code is; concrete manifests, "
                "audits, reports, and direct counts answer which data are valid."
            ),
            "fallback_when_broad_query_misses": (
                "Use exact paths from docs/structure/current_pipeline_manifest.md "
                "or inspect concrete CSV/JSON artifacts directly."
            ),
        },
    }


def write_report(audit: dict[str, Any]) -> None:
    path_checks = audit["required_exact_path_checks"]
    lines = [
        "# CodeGraph Project Contract",
        "",
        "Purpose: keep CodeGraph useful for code navigation without letting broad",
        "semantic retrieval override frozen data artifacts or project rules.",
        "",
        "## Status",
        "",
        f"- `.codegraph/` exists: {audit['codegraph_dir_exists']}",
        f"- `codegraph status` exit code: {audit['codegraph_status_exit_code']}",
        "",
        "## Required Exact Paths",
        "",
    ]
    for path, exists in path_checks.items():
        lines.append(f"- `{path}`: {'present' if exists else 'missing'}")
    lines.extend(
        [
            "",
            "## Binding Use",
            "",
            "Use CodeGraph first for code structure. Use exact paths whenever the",
            "current pipeline manifest already names the file. Treat broad results",
            "that point to legacy/prototype code as retrieval misses, not scientific",
            "state.",
            "",
            "Data decisions must be verified from CSV/JSON manifests, reports, and",
            "direct counts.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(audit)
    failed_paths = [
        path for path, exists in audit["required_exact_path_checks"].items() if not exists
    ]
    if failed_paths or not audit["codegraph_dir_exists"] or audit["codegraph_status_exit_code"] != 0:
        print("FAIL codegraph project contract")
        print(json.dumps({"failed_paths": failed_paths}, indent=2))
        return 1
    print("PASS codegraph project contract")
    print(f"WROTE {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
