#!/usr/bin/env python3
"""Organize assistant-returned range files into the v2 assisted workspace."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_NAME = "phase6_unique_500_v2_balanced"
WORKSPACE = PROJECT_ROOT / f"outputs/czechlynx/phase6/annotation_review_packages/{WORKFLOW_NAME}/assisted_annotation_workspace"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--range-id", required=True)
    parser.add_argument("--downloads-dir", default=str(Path.home() / "Downloads"))
    args = parser.parse_args()
    downloads = Path(args.downloads_dir).expanduser()
    target = WORKSPACE / "incoming_from_downloads" / args.range_id
    target.mkdir(parents=True, exist_ok=True)
    matched = []
    for path in downloads.iterdir():
        if args.range_id in path.name:
            dst = target / path.name
            if path.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(path, dst)
            else:
                shutil.copy2(path, dst)
            matched.append(dst)
    if not matched:
        raise SystemExit(f"No files containing {args.range_id} found in {downloads}")
    print(f"organized {len(matched)} files/directories into {target}")


if __name__ == "__main__":
    main()
