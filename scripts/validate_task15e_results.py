#!/usr/bin/env python3
"""Validate a complete PF-ERI Task 15E result directory."""
from __future__ import annotations
import argparse, json
from pathlib import Path
try:
    from run_task15e import validate_results
except ImportError:
    from task15e_modelscope_runner import validate_results

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--results-dir", required=True, type=Path)
args = parser.parse_args()
audit = validate_results(args.results_dir.resolve())
print(json.dumps(audit, indent=2, sort_keys=True))
raise SystemExit(0 if audit["status"] == "PASS" else 1)
