#!/usr/bin/env python3
"""Colab runner for Phase 10-Lite matched metric-learning checks.

This script is a convenience entrypoint for Colab. It is not intended to be run
locally during package preparation.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

DEFAULT_CONFIGS = [
    "config_k2_random_matched.yaml",
    "config_k2_quality_matched.yaml",
    "config_k2_pf_eri_matched.yaml",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", nargs="*", default=DEFAULT_CONFIGS)
    parser.add_argument("--run-evaluation", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    for config_name in args.configs:
        config_path = root / config_name
        print(f"Running Phase 10-Lite training config: {config_path}")
        subprocess.run(
            ["python", str(root / "train_phase10_lite_metric_learning.py"), "--config", str(config_path)],
            check=True,
        )
        if args.run_evaluation:
            print(
                "Evaluation requires a checkpoint path. Run evaluate_phase10_lite_retrieval.py "
                "explicitly with --checkpoint after confirming the output directory."
            )


if __name__ == "__main__":
    main()
