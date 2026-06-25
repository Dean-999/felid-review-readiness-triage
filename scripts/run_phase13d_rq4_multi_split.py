#!/usr/bin/env python3
"""Run Phase 13D across multiple splits and descriptors.

This is the confidence-building wrapper for the local fixed-embedding RQ4
sanity experiment. It repeatedly calls the Phase 13D builder, keeps each
split/descriptor result, and writes aggregate tables for paired policy
contrasts.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_fixed_embedding_training"
RUN_DIR = OUT_DIR / "multi_split_runs"

BUILD_SCRIPT = PROJECT_ROOT / "scripts/build_phase13d_rq4_fixed_embedding_training.py"
SUMMARY_SCRIPT = PROJECT_ROOT / "scripts/summarize_phase13d_rq4_fixed_embedding_training.py"

EXPOSURE = OUT_DIR / "phase13d_rq4_loss_exposure_summary.csv"
TRAINING = OUT_DIR / "phase13d_rq4_training_metrics.csv"
RETRIEVAL = OUT_DIR / "phase13d_rq4_retrieval_metrics.csv"

AGG_EXPOSURE = OUT_DIR / "phase13d_rq4_multi_split_loss_exposure_summary.csv"
AGG_TRAINING = OUT_DIR / "phase13d_rq4_multi_split_training_metrics.csv"
AGG_RETRIEVAL = OUT_DIR / "phase13d_rq4_multi_split_retrieval_metrics.csv"


def run_one(split_id: int, descriptor: str, args: argparse.Namespace) -> dict[str, Path]:
    cmd = [
        "python3",
        str(BUILD_SCRIPT),
        "--split-id",
        str(split_id),
        "--descriptor",
        descriptor,
        "--epochs",
        str(args.epochs),
        "--max-train-pairs",
        str(args.max_train_pairs),
        "--batch-size",
        str(args.batch_size),
        "--hidden-dim",
        str(args.hidden_dim),
        "--projection-dim",
        str(args.projection_dim),
        "--learning-rate",
        str(args.learning_rate),
        "--weight-decay",
        str(args.weight_decay),
        "--margin",
        str(args.margin),
    ]
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    run_prefix = RUN_DIR / f"split{split_id}_{descriptor}"
    paths = {
        "exposure": run_prefix.with_name(f"{run_prefix.name}_loss_exposure_summary.csv"),
        "training": run_prefix.with_name(f"{run_prefix.name}_training_metrics.csv"),
        "retrieval": run_prefix.with_name(f"{run_prefix.name}_retrieval_metrics.csv"),
    }
    shutil.copyfile(EXPOSURE, paths["exposure"])
    shutil.copyfile(TRAINING, paths["training"])
    shutil.copyfile(RETRIEVAL, paths["retrieval"])
    return paths


def add_run_columns(path: Path, split_id: int, descriptor: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["run_split_id"] = int(split_id)
    frame["run_descriptor"] = descriptor
    return frame


def parse_run_path(path: Path) -> tuple[int, str]:
    stem = path.stem
    # split1_megadescriptor_retrieval_metrics
    parts = stem.split("_")
    split_id = int(parts[0].removeprefix("split"))
    descriptor = parts[1]
    return split_id, descriptor


def aggregate(paths: list[Path], output: Path) -> None:
    frames = []
    for path in paths:
        split_id, descriptor = parse_run_path(path)
        frames.append(add_run_columns(path, split_id, descriptor))
    pd.concat(frames, ignore_index=True).to_csv(output, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits", nargs="*", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--descriptors", nargs="*", choices=["megadescriptor", "resnet50"], default=["megadescriptor", "resnet50"])
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--max-train-pairs", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--projection-dim", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--margin", type=float, default=0.35)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    exposure_paths: list[Path] = []
    training_paths: list[Path] = []
    retrieval_paths: list[Path] = []
    for split_id in args.splits:
        for descriptor in args.descriptors:
            paths = run_one(split_id, descriptor, args)
            exposure_paths.append(paths["exposure"])
            training_paths.append(paths["training"])
            retrieval_paths.append(paths["retrieval"])

    aggregate(exposure_paths, AGG_EXPOSURE)
    aggregate(training_paths, AGG_TRAINING)
    aggregate(retrieval_paths, AGG_RETRIEVAL)

    subprocess.run(
        ["python3", str(SUMMARY_SCRIPT), "--inputs", str(AGG_RETRIEVAL)],
        cwd=PROJECT_ROOT,
        check=True,
    )
    print(f"Wrote multi-split Phase 13D retrieval metrics to {AGG_RETRIEVAL.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
