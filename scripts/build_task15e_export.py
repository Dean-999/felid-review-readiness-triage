#!/usr/bin/env python3
"""Validate and build the single downloadable PF-ERI Task 15E result ZIP."""
from __future__ import annotations
import argparse, json
from pathlib import Path
try:
    from run_task15e import build_export
except ImportError:
    from task15e_modelscope_runner import build_export

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--results-dir", required=True, type=Path)
parser.add_argument("--zip", default="PF_ERI_TASK15E_FINAL_EXPORT.zip", type=Path)
args = parser.parse_args()
try:
    audit = build_export(args.results_dir.resolve(), args.zip.resolve())
except Exception as error:
    print(json.dumps({"status": "FAIL", "error": str(error)}, indent=2)); raise SystemExit(1)
print(json.dumps(audit, indent=2, sort_keys=True))
