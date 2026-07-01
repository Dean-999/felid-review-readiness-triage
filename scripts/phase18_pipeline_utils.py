#!/usr/bin/env python3
"""Shared helpers for the Phase18 local automated pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = "/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

PHASE18A_DIR = PROJECT_ROOT / "outputs/phase18/phase18a_frozen_feature_manifest"
PHASE18A_MANIFEST = PHASE18A_DIR / "phase18a_frozen_image_feature_manifest.csv"
PHASE18B_DIR = PROJECT_ROOT / "outputs/phase18/phase18b_local_descriptor_control"
PHASE18B_MANIFEST = PHASE18B_DIR / "phase18b_local_descriptor_manifest.csv"
PHASE18B_EMBEDDINGS = PHASE18B_DIR / "phase18b_local_descriptor_embeddings.npy"
PHASE18C_DIR = PROJECT_ROOT / "outputs/phase18/phase18c_czechlynx_pair_contract"
PHASE18C_PAIRS = PHASE18C_DIR / "phase18c_czechlynx_known_id_pair_contract.csv"
PHASE18D_DIR = PROJECT_ROOT / "outputs/phase18/phase18d_pf_eri_pair_features"
PHASE18D_FEATURES = PHASE18D_DIR / "phase18d_pf_eri_pair_features.csv"
PHASE18E_DIR = PROJECT_ROOT / "outputs/phase18/phase18e_review_router"
PHASE18F_DIR = PROJECT_ROOT / "outputs/phase18/phase18f_bobcat_transfer_readiness"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_fold(value: str, fold_count: int = 5) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % fold_count


def calibration_role(value: str) -> str:
    return "evaluation" if stable_fold(value) == 4 else "calibration"


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return (matrix / norms).astype(np.float32)


def average_precision(relevance: list[bool]) -> float:
    hits = 0
    total = 0.0
    for idx, relevant in enumerate(relevance, start=1):
        if relevant:
            hits += 1
            total += hits / idx
    return total / hits if hits else 0.0


def percentile_ranks(values: list[float]) -> list[float]:
    if not values:
        return []
    order = np.argsort(np.asarray(values, dtype=np.float64))
    ranks = np.empty(len(values), dtype=np.float64)
    if len(values) == 1:
        ranks[order[0]] = 1.0
    else:
        ranks[order] = np.linspace(0.0, 1.0, len(values))
    return [float(v) for v in ranks]


def image_quality_from_row(row: dict[str, str]) -> float:
    min_dim = to_float(row.get("min_dimension", "0"))
    megapixels = to_float(row.get("megapixels", "0"))
    dim_score = clamp01(min_dim / 512.0)
    mp_score = clamp01(megapixels / 0.75)
    return round(0.55 * dim_score + 0.45 * mp_score, 6)


def aspect_compatibility(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    return round(clamp01(1.0 - abs(a - b) / max(a, b)), 6)


def size_compatibility(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    return round(clamp01(min(a, b) / max(a, b)), 6)
