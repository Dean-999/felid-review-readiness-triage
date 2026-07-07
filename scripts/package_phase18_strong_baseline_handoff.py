#!/usr/bin/env python3
"""Package Phase18 strong-baseline handoff metadata for external GPU runs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from scripts.phase18_pipeline_utils import PHASE18G_DIR, PROJECT_ROOT, now_utc, project_relative, read_csv, write_csv, write_json
except ImportError:  # pragma: no cover - direct script execution
    from phase18_pipeline_utils import PHASE18G_DIR, PROJECT_ROOT, now_utc, project_relative, read_csv, write_csv, write_json


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase18/phase18_strong_baseline_handoff_package"


def package_phase18_strong_baseline_handoff(
    handoff_manifest: Path,
    requirements_json: Path,
    output_dir: Path,
) -> dict[str, Any]:
    rows = read_csv(handoff_manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_manifest = output_dir / "phase18_strong_baseline_handoff_manifest.csv"
    write_csv(output_manifest, rows, list(rows[0].keys()))
    requirements_copy = output_dir / "phase18g_strong_baseline_requirements.json"
    requirements_copy.write_text(requirements_json.read_text(encoding="utf-8"), encoding="utf-8")
    readme = output_dir / "README.md"
    readme.write_text(
        "# Phase18 Strong Baseline Handoff Package\n\n"
        "Use this package to run external strong descriptor extraction on GPU/Colab.\n\n"
        "Required return artifacts:\n\n"
        "- `embedding_manifest.csv` keyed by `phase18_image_id`.\n"
        "- `embeddings.npy` with rows matching `embedding_row`.\n"
        "- `pair_scores.csv` for CzechLynx known-ID retrieval pairs only.\n\n"
        "Bobcat rows are unlabeled transfer/readiness rows. Do not create Bobcat "
        "identity labels or same/different labels.\n",
        encoding="utf-8",
    )
    audit = {
        "built_at_utc": now_utc(),
        "input_handoff_manifest": project_relative(handoff_manifest),
        "input_requirements_json": project_relative(requirements_json),
        "output_manifest": project_relative(output_manifest),
        "output_requirements_json": project_relative(requirements_copy),
        "row_count": len(rows),
        "status": "PASS",
        "claim_boundary": "Handoff package only; no descriptor output or scientific claim is produced here.",
    }
    write_json(output_dir / "phase18_strong_baseline_handoff_package_audit.json", audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--handoff-manifest",
        type=Path,
        default=PHASE18G_DIR / "phase18g_strong_baseline_handoff_manifest.csv",
    )
    parser.add_argument(
        "--requirements-json",
        type=Path,
        default=PHASE18G_DIR / "phase18g_strong_baseline_requirements.json",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = package_phase18_strong_baseline_handoff(args.handoff_manifest, args.requirements_json, args.output_dir)
    print("PASS phase18 strong baseline handoff package")
    print(f"row_count={audit['row_count']}")
    print(f"WROTE {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
