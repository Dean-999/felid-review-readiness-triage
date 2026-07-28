#!/usr/bin/env python3
"""Outcome-invariant fold-train preprocessor for registered PF-ERI v2 models."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd


MISSING_TOKEN = "__MISSING__"
UNKNOWN_TOKEN = "__UNKNOWN__"


def canonical_category(value: Any) -> str:
    if value is None or pd.isna(value):
        return MISSING_TOKEN
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    text = str(value).strip()
    if not text:
        return MISSING_TOKEN
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered
    return text


def payload_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FittedFoldPreprocessor:
    contract_version: str
    block_names: tuple[str, ...]
    continuous: tuple[dict[str, Any], ...]
    categorical: tuple[dict[str, Any], ...]
    output_columns: tuple[str, ...]
    fitted_row_count: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "serialization_version": "pferi_v2_fitted_fold_preprocessor_v1",
            "contract_version": self.contract_version,
            "block_names": list(self.block_names),
            "continuous": list(self.continuous),
            "categorical": list(self.categorical),
            "output_columns": list(self.output_columns),
            "fitted_row_count": self.fitted_row_count,
        }

    @property
    def sha256(self) -> str:
        return payload_sha256(self.to_payload())

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "FittedFoldPreprocessor":
        if payload.get("serialization_version") != "pferi_v2_fitted_fold_preprocessor_v1":
            raise ValueError("unexpected fitted preprocessor serialization version")
        return cls(
            contract_version=str(payload["contract_version"]),
            block_names=tuple(map(str, payload["block_names"])),
            continuous=tuple(dict(row) for row in payload["continuous"]),
            categorical=tuple(dict(row) for row in payload["categorical"]),
            output_columns=tuple(map(str, payload["output_columns"])),
            fitted_row_count=int(payload["fitted_row_count"]),
        )

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        parts: dict[str, np.ndarray] = {}
        for spec in self.continuous:
            column = str(spec["column"])
            if column not in frame:
                raise ValueError(f"missing continuous feature: {column}")
            numeric = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
            numeric[~np.isfinite(numeric)] = np.nan
            missing = np.isnan(numeric)
            imputed = np.where(missing, float(spec["median"]), numeric)
            parts[f"{column}__z"] = (imputed - float(spec["mean"])) / float(spec["scale"])
            parts[f"{column}__missing"] = missing.astype(float)
        for spec in self.categorical:
            column = str(spec["column"])
            if column not in frame:
                raise ValueError(f"missing categorical feature: {column}")
            known = set(map(str, spec["observed_levels"])) | {MISSING_TOKEN}
            values = frame[column].map(canonical_category)
            values = values.where(values.isin(known), UNKNOWN_TOKEN)
            for level in spec["encoded_levels"]:
                parts[f"{column}=={level}"] = (values == level).to_numpy(dtype=float)
        output = pd.DataFrame(parts, index=frame.index)
        output = output.loc[:, list(self.output_columns)]
        if output.shape[1] != len(set(output.columns)):
            raise RuntimeError("duplicate transformed feature columns")
        if not np.isfinite(output.to_numpy(dtype=float)).all():
            raise RuntimeError("non-finite transformed feature value")
        return output


def _registered_features(
    contract: dict[str, Any], block_names: Sequence[str]
) -> tuple[list[str], list[str]]:
    blocks = contract.get("feature_blocks", {})
    continuous: list[str] = []
    categorical: list[str] = []
    for block in block_names:
        if block not in blocks:
            raise ValueError(f"unregistered feature block: {block}")
        continuous.extend(map(str, blocks[block].get("continuous", [])))
        categorical.extend(map(str, blocks[block].get("categorical", [])))
    if len(continuous) != len(set(continuous)) or len(categorical) != len(set(categorical)):
        raise ValueError("duplicate feature registered across selected blocks")
    if set(continuous) & set(categorical):
        raise ValueError("feature registered as both continuous and categorical")
    return continuous, categorical


def fit_fold_preprocessor(
    frame: pd.DataFrame,
    contract: dict[str, Any],
    block_names: Sequence[str],
) -> FittedFoldPreprocessor:
    if contract.get("contract_version") != "pferi_v2_feature_preprocessing_contract_v1":
        raise ValueError("unexpected feature preprocessing contract")
    if len(frame) == 0:
        raise ValueError("cannot fit preprocessing on an empty training fold")
    continuous_columns, categorical_columns = _registered_features(contract, block_names)
    missing = sorted((set(continuous_columns) | set(categorical_columns)) - set(frame.columns))
    if missing:
        raise ValueError(f"training fold lacks registered features: {missing}")

    continuous_specs: list[dict[str, Any]] = []
    categorical_specs: list[dict[str, Any]] = []
    for column in continuous_columns:
        numeric = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        numeric[~np.isfinite(numeric)] = np.nan
        if np.isnan(numeric).all():
            raise ValueError(f"continuous training feature is entirely missing: {column}")
        median = float(np.nanmedian(numeric))
        imputed = np.where(np.isnan(numeric), median, numeric)
        mean = float(np.mean(imputed))
        scale = float(np.std(imputed, ddof=0))
        if not np.isfinite(scale) or scale < 1e-12:
            scale = 1.0
        continuous_specs.append(
            {"column": column, "median": median, "mean": mean, "scale": scale}
        )

    for column in categorical_columns:
        values = frame[column].map(canonical_category)
        observed = sorted(set(values) - {MISSING_TOKEN, UNKNOWN_TOKEN})
        reference = observed[0] if observed else None
        encoded = [level for level in observed if level != reference]
        encoded.extend([MISSING_TOKEN, UNKNOWN_TOKEN])
        categorical_specs.append(
            {
                "column": column,
                "observed_levels": observed,
                "reference_level": reference,
                "encoded_levels": encoded,
            }
        )

    categorical_by_column = {str(spec["column"]): spec for spec in categorical_specs}
    output_columns: list[str] = []
    for block in block_names:
        block_spec = contract["feature_blocks"][block]
        for column in block_spec.get("continuous", []):
            output_columns.extend([f"{column}__z", f"{column}__missing"])
        for column in block_spec.get("categorical", []):
            output_columns.extend(
                f"{column}=={level}"
                for level in categorical_by_column[str(column)]["encoded_levels"]
            )

    fitted = FittedFoldPreprocessor(
        contract_version=str(contract["contract_version"]),
        block_names=tuple(map(str, block_names)),
        continuous=tuple(continuous_specs),
        categorical=tuple(categorical_specs),
        output_columns=tuple(output_columns),
        fitted_row_count=len(frame),
    )
    # Fit must immediately prove that its training transform is finite and schema-stable.
    fitted.transform(frame)
    return fitted


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
