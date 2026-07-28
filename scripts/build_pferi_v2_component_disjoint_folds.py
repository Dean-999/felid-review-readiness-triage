#!/usr/bin/env python3
"""Build deterministic endpoint-component-disjoint nested folds for PF-ERI v2."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTCOME_TOKENS = ("label", "outcome", "adjudicat", "review_ready", "not_ready")
REQUIRED_MASTER_COLUMNS = {
    "canonical_pair_id",
    "pair_execution_id",
    "analytical_role",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "development_sampling_cell_id",
    "descriptor_support_category",
    "development_evidence_state",
    "best_rank_band",
    "local_match_measurement_failure",
    "endpoint_quality_measurement_failure",
}
REQUIRED_FORMAL_COLUMNS = {
    "formal_sampling_stage",
    "canonical_pair_id",
    "pair_execution_id",
    "source_analytical_role",
    "first_order_inclusion_probability",
}


@dataclass(frozen=True)
class NestedAssignments:
    outer: pd.DataFrame
    nested: pd.DataFrame
    components: pd.DataFrame
    balance: pd.DataFrame


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, value: str) -> str:
        if value not in self.parent:
            self.parent[value] = value
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: str, right: str) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left == root_right:
            return
        if root_left < root_right:
            self.parent[root_right] = root_left
        else:
            self.parent[root_left] = root_right


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_hash(*parts: object) -> str:
    return hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()


def validate_registry(registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if registry.get("registry_version") != "pferi_v2_component_disjoint_fold_design_v1":
        issues.append("unexpected registry version")
    if registry.get("outcome_policy") != "PROHIBITED":
        issues.append("outcomes must be prohibited during fold construction")
    if int(registry.get("outer_fold_count", 0)) < 2:
        issues.append("outer fold count must be at least two")
    if int(registry.get("inner_fold_count", 0)) < 2:
        issues.append("inner fold count must be at least two")
    balance = registry.get("balance_columns", [])
    if not isinstance(balance, list) or not balance:
        issues.append("balance_columns must be a non-empty list")
    if not set(balance) <= REQUIRED_MASTER_COLUMNS:
        issues.append("balance_columns contain unregistered fields")
    acceptance = registry.get("acceptance", {})
    if acceptance.get("zero_endpoint_leakage") is not True:
        issues.append("zero endpoint leakage must be mandatory")
    if acceptance.get("exact_pair_coverage") is not True:
        issues.append("exact pair coverage must be mandatory")
    minimum = float(acceptance.get("minimum_fold_pair_count_ratio_to_ideal", 0))
    maximum = float(acceptance.get("maximum_fold_pair_count_ratio_to_ideal", 0))
    if not 0 < minimum <= 1 <= maximum:
        issues.append("invalid fold-size acceptance ratios")
    weights = registry.get("objective_weights", {})
    if any(float(weights.get(name, 0)) <= 0 for name in [
        "pair_count", "component_count", "each_balance_column_total",
        "inclusion_probability_bin_total",
    ]):
        issues.append("all objective weights must be positive")
    return issues


def _outcome_like(columns: Sequence[str]) -> list[str]:
    return sorted(
        column for column in columns
        if any(token in column.lower() for token in OUTCOME_TOKENS)
    )


def load_outcome_free_development(master_path: Path, formal_path: Path) -> pd.DataFrame:
    master_header = pd.read_csv(master_path, nrows=0).columns.tolist()
    formal_header = pd.read_csv(formal_path, nrows=0).columns.tolist()
    contaminated = _outcome_like(master_header) + _outcome_like(formal_header)
    if contaminated:
        raise ValueError(f"outcome-like columns found in fold inputs: {sorted(set(contaminated))}")
    missing_master = sorted(REQUIRED_MASTER_COLUMNS - set(master_header))
    missing_formal = sorted(REQUIRED_FORMAL_COLUMNS - set(formal_header))
    if missing_master or missing_formal:
        raise ValueError(f"missing fold input columns: master={missing_master} formal={missing_formal}")

    master = pd.read_csv(master_path, usecols=sorted(REQUIRED_MASTER_COLUMNS))
    formal = pd.read_csv(formal_path, usecols=sorted(REQUIRED_FORMAL_COLUMNS))
    master = master.loc[master["analytical_role"].astype(str) == "development"].copy()
    formal = formal.loc[
        (formal["formal_sampling_stage"].astype(str) == "development")
        & (formal["source_analytical_role"].astype(str) == "development")
    ].copy()
    if master["canonical_pair_id"].duplicated().any():
        raise ValueError("duplicate pair IDs in development master frame")
    if formal["canonical_pair_id"].duplicated().any():
        raise ValueError("duplicate pair IDs in formal development sample")
    frame = formal[["canonical_pair_id", "first_order_inclusion_probability"]].merge(
        master,
        on="canonical_pair_id",
        how="left",
        validate="one_to_one",
        sort=False,
    )
    if frame["pair_execution_id"].isna().any():
        raise ValueError("formal development pair is missing from outcome-free master frame")
    probability = pd.to_numeric(frame["first_order_inclusion_probability"], errors="coerce")
    if probability.isna().any() or (probability <= 0).any() or (probability > 1).any():
        raise ValueError("invalid first-order inclusion probability")
    frame["first_order_inclusion_probability"] = probability
    for endpoint in ["endpoint_a_image_id", "endpoint_b_image_id"]:
        if frame[endpoint].isna().any() or (frame[endpoint].astype(str).str.len() == 0).any():
            raise ValueError(f"missing endpoint ID in {endpoint}")
    if (frame["endpoint_a_image_id"].astype(str) == frame["endpoint_b_image_id"].astype(str)).any():
        raise ValueError("self-pair found in formal development sample")
    return frame.reset_index(drop=True)


def connected_components(frame: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    union_find = UnionFind()
    for left, right in zip(frame["endpoint_a_image_id"], frame["endpoint_b_image_id"]):
        union_find.union(str(left), str(right))
    roots: dict[str, list[str]] = {}
    for endpoint in sorted(union_find.parent):
        roots.setdefault(union_find.find(endpoint), []).append(endpoint)
    component_by_endpoint: dict[str, str] = {}
    endpoint_sets: dict[str, set[str]] = {}
    for endpoints in roots.values():
        component_id = "cmp_" + _stable_hash(*sorted(endpoints))[:16]
        endpoint_sets[component_id] = set(endpoints)
        component_by_endpoint.update({endpoint: component_id for endpoint in endpoints})
    membership = frame["endpoint_a_image_id"].astype(str).map(component_by_endpoint)

    degree: dict[str, int] = {}
    for endpoint in pd.concat(
        [frame["endpoint_a_image_id"].astype(str), frame["endpoint_b_image_id"].astype(str)]
    ):
        degree[endpoint] = degree.get(endpoint, 0) + 1
    inventory_rows: list[dict[str, Any]] = []
    for component_id in sorted(endpoint_sets):
        mask = membership == component_id
        endpoints = endpoint_sets[component_id]
        inventory_rows.append(
            {
                "component_id": component_id,
                "endpoint_count": len(endpoints),
                "pair_count": int(mask.sum()),
                "maximum_endpoint_degree": max(degree[endpoint] for endpoint in endpoints),
                "local_match_failure_pair_count": int(
                    frame.loc[mask, "local_match_measurement_failure"].astype(str).str.lower().isin(
                        {"true", "1", "yes"}
                    ).sum()
                ) if "local_match_measurement_failure" in frame else 0,
                "quality_failure_pair_count": int(
                    frame.loc[mask, "endpoint_quality_measurement_failure"].astype(str).str.lower().isin(
                        {"true", "1", "yes"}
                    ).sum()
                ) if "endpoint_quality_measurement_failure" in frame else 0,
            }
        )
    return membership, pd.DataFrame(inventory_rows)


def _with_probability_bins(frame: pd.DataFrame, bin_count: int) -> pd.DataFrame:
    result = frame.copy()
    ranks = result["first_order_inclusion_probability"].rank(method="first")
    actual_bins = min(max(1, int(bin_count)), len(result))
    result["__inclusion_probability_bin"] = pd.qcut(
        ranks, q=actual_bins, labels=False, duplicates="drop"
    ).astype(str)
    return result


def _component_vectors(
    frame: pd.DataFrame,
    registry: dict[str, Any],
) -> tuple[list[str], np.ndarray, np.ndarray, list[str]]:
    dimensions: list[str] = ["__pair_count", "__component_count"]
    columns = list(registry["balance_columns"]) + ["__inclusion_probability_bin"]
    levels: dict[str, list[str]] = {}
    for column in columns:
        levels[column] = sorted(frame[column].fillna("__MISSING__").astype(str).unique())
        dimensions.extend(f"{column}={level}" for level in levels[column])
    component_ids = sorted(frame["component_id"].astype(str).unique())
    vectors = np.zeros((len(component_ids), len(dimensions)), dtype=float)
    weights = np.zeros(len(dimensions), dtype=float)
    objective = registry["objective_weights"]
    weights[0] = float(objective["pair_count"])
    weights[1] = float(objective["component_count"])
    offset = 2
    for column in columns:
        total = (
            float(objective["inclusion_probability_bin_total"])
            if column == "__inclusion_probability_bin"
            else float(objective["each_balance_column_total"])
        )
        weights[offset:offset + len(levels[column])] = total / len(levels[column])
        offset += len(levels[column])
    for row_index, component_id in enumerate(component_ids):
        subset = frame.loc[frame["component_id"].astype(str) == component_id]
        vectors[row_index, 0] = len(subset)
        vectors[row_index, 1] = 1
        offset = 2
        for column in columns:
            counts = subset[column].fillna("__MISSING__").astype(str).value_counts()
            for level_index, level in enumerate(levels[column]):
                vectors[row_index, offset + level_index] = int(counts.get(level, 0))
            offset += len(levels[column])
    return component_ids, vectors, weights, dimensions


def _allocation_objective(counts: np.ndarray, target: np.ndarray, weights: np.ndarray) -> float:
    scale = np.maximum(target, 1.0)
    return float(np.sum(weights[None, :] * ((counts - target[None, :]) / scale[None, :]) ** 2))


def assign_components(
    frame: pd.DataFrame,
    fold_count: int,
    registry: dict[str, Any],
    context: str,
) -> dict[str, int]:
    component_ids, vectors, weights, _ = _component_vectors(frame, registry)
    if len(component_ids) < fold_count:
        raise ValueError(f"{context} has fewer endpoint components than folds")
    target = vectors.sum(axis=0) / fold_count
    counts = np.zeros((fold_count, vectors.shape[1]), dtype=float)
    assignment: dict[str, int] = {}
    index_by_component = {component: index for index, component in enumerate(component_ids)}
    ordered = sorted(
        component_ids,
        key=lambda component: (
            -vectors[index_by_component[component], 0],
            _stable_hash(registry["allocation_seed"], context, component),
        ),
    )
    for component in ordered:
        vector = vectors[index_by_component[component]]
        candidates: list[tuple[float, str, int]] = []
        for fold in range(fold_count):
            proposed = counts.copy()
            proposed[fold] += vector
            candidates.append(
                (
                    _allocation_objective(proposed, target, weights),
                    _stable_hash(registry["allocation_seed"], context, component, fold),
                    fold,
                )
            )
        _, _, chosen = min(candidates)
        assignment[component] = chosen
        counts[chosen] += vector

    # Deterministic single-component moves can improve balance without ever
    # splitting a graph component. Stop at the first full pass with no change.
    for _ in range(50):
        improved = False
        current_objective = _allocation_objective(counts, target, weights)
        for component in sorted(
            component_ids,
            key=lambda value: _stable_hash(registry["allocation_seed"], context, "move", value),
        ):
            source = assignment[component]
            if sum(value == source for value in assignment.values()) <= 1:
                continue
            vector = vectors[index_by_component[component]]
            best = (current_objective, source)
            for destination in range(fold_count):
                if destination == source:
                    continue
                proposed = counts.copy()
                proposed[source] -= vector
                proposed[destination] += vector
                score = _allocation_objective(proposed, target, weights)
                if score < best[0] - 1e-12:
                    best = (score, destination)
            if best[1] != source:
                counts[source] -= vector
                counts[best[1]] += vector
                assignment[component] = best[1]
                current_objective = best[0]
                improved = True
        if not improved:
            break
    return assignment


def _balance_rows(
    frame: pd.DataFrame,
    fold_column: str,
    stage: str,
    outer_context: int | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fold, subset in frame.groupby(fold_column, sort=True):
        endpoints = set(subset["endpoint_a_image_id"].astype(str)) | set(
            subset["endpoint_b_image_id"].astype(str)
        )
        rows.append(
            {
                "stage": stage,
                "outer_fold_context": outer_context,
                "validation_fold": int(fold),
                "pair_count": len(subset),
                "component_count": subset["component_id"].nunique(),
                "endpoint_count": len(endpoints),
                "mean_first_order_inclusion_probability": float(
                    subset["first_order_inclusion_probability"].mean()
                ),
                "sampling_cell_level_count": subset["development_sampling_cell_id"].nunique(),
                "descriptor_support_level_count": subset["descriptor_support_category"].nunique(),
                "local_match_failure_pair_count": int(
                    subset["local_match_measurement_failure"].astype(str).str.lower().isin(
                        {"true", "1", "yes"}
                    ).sum()
                ),
                "quality_failure_pair_count": int(
                    subset["endpoint_quality_measurement_failure"].astype(str).str.lower().isin(
                        {"true", "1", "yes"}
                    ).sum()
                ),
            }
        )
    return rows


def build_nested_assignments(frame: pd.DataFrame, registry: dict[str, Any]) -> NestedAssignments:
    working = _with_probability_bins(frame, int(registry["inclusion_probability_bins"]))
    membership, inventory = connected_components(working)
    working["component_id"] = membership
    outer_map = assign_components(
        working, int(registry["outer_fold_count"]), registry, "outer"
    )
    working["outer_fold"] = working["component_id"].map(outer_map).astype(int)
    output_columns = [
        "canonical_pair_id", "pair_execution_id", "endpoint_a_image_id",
        "endpoint_b_image_id", "component_id", "outer_fold",
        "first_order_inclusion_probability",
    ] + list(registry["balance_columns"])
    outer = working[output_columns].sort_values("canonical_pair_id").reset_index(drop=True)
    balance_rows = _balance_rows(working, "outer_fold", "outer", None)

    nested_pieces: list[pd.DataFrame] = []
    for outer_fold in range(int(registry["outer_fold_count"])):
        training = working.loc[working["outer_fold"] != outer_fold].copy()
        inner_map = assign_components(
            training,
            int(registry["inner_fold_count"]),
            registry,
            f"inner_outer_{outer_fold}",
        )
        training["inner_fold"] = training["component_id"].map(inner_map).astype(int)
        training["outer_fold_context"] = outer_fold
        nested_pieces.append(
            training[
                [
                    "outer_fold_context", "canonical_pair_id", "pair_execution_id",
                    "endpoint_a_image_id", "endpoint_b_image_id", "component_id",
                    "inner_fold", "first_order_inclusion_probability",
                ] + list(registry["balance_columns"])
            ]
        )
        balance_rows.extend(
            _balance_rows(training, "inner_fold", "inner", outer_fold)
        )
    nested = pd.concat(nested_pieces, ignore_index=True).sort_values(
        ["outer_fold_context", "canonical_pair_id"]
    ).reset_index(drop=True)
    balance = pd.DataFrame(balance_rows).sort_values(
        ["stage", "outer_fold_context", "validation_fold"], na_position="first"
    ).reset_index(drop=True)
    return NestedAssignments(outer=outer, nested=nested, components=inventory, balance=balance)


def _endpoint_leakage(train: pd.DataFrame, validation: pd.DataFrame) -> set[str]:
    train_endpoints = set(train["endpoint_a_image_id"].astype(str)) | set(
        train["endpoint_b_image_id"].astype(str)
    )
    validation_endpoints = set(validation["endpoint_a_image_id"].astype(str)) | set(
        validation["endpoint_b_image_id"].astype(str)
    )
    return train_endpoints & validation_endpoints


def validate_assignments(
    frame: pd.DataFrame,
    assignments: NestedAssignments,
    registry: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    outer = assignments.outer
    nested = assignments.nested
    pair_ids = set(frame["canonical_pair_id"].astype(str))
    if len(outer) != len(frame) or outer["canonical_pair_id"].duplicated().any():
        issues.append("outer assignment does not contain each development pair exactly once")
    if set(outer["canonical_pair_id"].astype(str)) != pair_ids:
        issues.append("outer assignment pair coverage mismatch")
    outer_fold_count = int(registry["outer_fold_count"])
    inner_fold_count = int(registry["inner_fold_count"])
    if set(outer["outer_fold"].astype(int)) != set(range(outer_fold_count)):
        issues.append("outer fold IDs are incomplete")

    leakage_count = 0
    for fold in range(outer_fold_count):
        validation = outer.loc[outer["outer_fold"] == fold]
        training = outer.loc[outer["outer_fold"] != fold]
        leakage_count += len(_endpoint_leakage(training, validation))
    component_fold_counts = outer.groupby("component_id")["outer_fold"].nunique()
    if (component_fold_counts != 1).any():
        issues.append("an endpoint component was split across outer folds")

    expected_nested_rows = len(frame) * (outer_fold_count - 1)
    if len(nested) != expected_nested_rows:
        issues.append("nested assignment row count mismatch")
    for outer_context in range(outer_fold_count):
        subset = nested.loc[nested["outer_fold_context"] == outer_context]
        expected_ids = set(
            outer.loc[outer["outer_fold"] != outer_context, "canonical_pair_id"].astype(str)
        )
        if set(subset["canonical_pair_id"].astype(str)) != expected_ids:
            issues.append(f"inner assignment coverage mismatch for outer fold {outer_context}")
        if subset["canonical_pair_id"].duplicated().any():
            issues.append(f"duplicate inner assignment for outer fold {outer_context}")
        if set(subset["inner_fold"].astype(int)) != set(range(inner_fold_count)):
            issues.append(f"inner fold IDs incomplete for outer fold {outer_context}")
        if (subset.groupby("component_id")["inner_fold"].nunique() != 1).any():
            issues.append(f"endpoint component split in inner folds for outer fold {outer_context}")
        for inner_fold in range(inner_fold_count):
            validation = subset.loc[subset["inner_fold"] == inner_fold]
            training = subset.loc[subset["inner_fold"] != inner_fold]
            leakage_count += len(_endpoint_leakage(training, validation))
    if leakage_count:
        issues.append(f"endpoint leakage detected: {leakage_count}")

    acceptance = registry["acceptance"]
    outer_counts = outer["outer_fold"].value_counts().sort_index()
    outer_ideal = len(frame) / outer_fold_count
    minimum_ratio = float(acceptance["minimum_fold_pair_count_ratio_to_ideal"])
    maximum_ratio = float(acceptance["maximum_fold_pair_count_ratio_to_ideal"])
    if float(outer_counts.min() / outer_ideal) < minimum_ratio:
        issues.append("outer fold is below the minimum pair-count ratio")
    if float(outer_counts.max() / outer_ideal) > maximum_ratio:
        issues.append("outer fold exceeds the maximum pair-count ratio")
    inner_ratios: list[float] = []
    for outer_context, subset in nested.groupby("outer_fold_context"):
        ideal = len(subset) / inner_fold_count
        inner_ratios.extend((subset["inner_fold"].value_counts() / ideal).tolist())
    if min(inner_ratios) < minimum_ratio:
        issues.append("inner fold is below the minimum pair-count ratio")
    if max(inner_ratios) > maximum_ratio:
        issues.append("inner fold exceeds the maximum pair-count ratio")

    if acceptance.get("all_descriptor_support_levels_in_each_outer_validation_fold"):
        required_levels = set(frame["descriptor_support_category"].astype(str))
        for fold, subset in outer.groupby("outer_fold"):
            if set(subset["descriptor_support_category"].astype(str)) != required_levels:
                issues.append(f"outer fold {fold} lacks a descriptor-support level")

    diagnostics = {
        "endpoint_leakage_count": leakage_count,
        "outer_fold_pair_count_min": int(outer_counts.min()),
        "outer_fold_pair_count_max": int(outer_counts.max()),
        "outer_fold_pair_count_ideal": outer_ideal,
        "inner_fold_pair_count_ratio_min": float(min(inner_ratios)),
        "inner_fold_pair_count_ratio_max": float(max(inner_ratios)),
    }
    return issues, diagnostics


def _structural_warnings(frame: pd.DataFrame, registry: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    fold_count = int(registry["outer_fold_count"])
    for column in registry["balance_columns"]:
        counts = frame[column].fillna("__MISSING__").astype(str).value_counts()
        for level, count in counts.items():
            if int(count) < fold_count:
                warnings.append(
                    f"{column}={level} has only {int(count)} pair(s), fewer than {fold_count} outer folds"
                )
    return warnings


def _write_report(path: Path, audit: dict[str, Any]) -> None:
    warning_text = (
        " Structural warnings were retained rather than breaking endpoint isolation: "
        + "; ".join(audit["structural_warnings"])
        if audit["structural_warnings"] else " No structurally sparse balance level was detected."
    )
    path.write_text(
        "\n".join(
            [
                "# PF-ERI v2 Component-Disjoint Nested-Fold Audit",
                "",
                f"Status: **{audit['status']}**",
                "",
                "The 445 formal development pairs were grouped by transitive endpoint-image connectivity. "
                f"The graph contained {audit['component_count']} components; the largest contained "
                f"{audit['largest_component_pair_count']} pairs. Complete components were assigned to five "
                "outer validation folds, then the components remaining in each outer-training set were "
                "reassigned to four inner validation folds.",
                "",
                f"Endpoint leakage count was {audit['endpoint_leakage_count']}. The deterministic rerun hash "
                f"check was {audit['deterministic_reproduction_pass']}.{warning_text}",
                "",
                "A PASS establishes only the resampling geometry. It estimates no performance, reads no outcome, "
                "and does not authorize calibration or confirmation access.",
            ]
        ) + "\n",
        encoding="utf-8",
    )


def run(
    master_path: Path,
    formal_path: Path,
    registry_path: Path,
    output_dir: Path,
    *,
    expected_rows: int = 445,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to replace existing fold directory: {output_dir}")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_issues = validate_registry(registry)
    if registry_issues:
        raise ValueError("fold registry validation failed: " + "; ".join(registry_issues))
    frame = load_outcome_free_development(master_path, formal_path)
    if len(frame) != expected_rows:
        raise ValueError(f"development pair count mismatch: {len(frame)} != {expected_rows}")
    first = build_nested_assignments(frame, registry)
    second = build_nested_assignments(frame, registry)
    deterministic = (
        _frame_hash(first.outer) == _frame_hash(second.outer)
        and _frame_hash(first.nested) == _frame_hash(second.nested)
    )
    issues, diagnostics = validate_assignments(frame, first, registry)
    if not deterministic:
        issues.append("deterministic reproduction failed")
    status = "PASS" if not issues else "FAIL"

    output_dir.mkdir(parents=True)
    frozen_registry = output_dir / "fold_design_registry_frozen.json"
    component_path = output_dir / "endpoint_component_inventory.csv"
    outer_path = output_dir / "outer_fold_assignments.csv"
    nested_path = output_dir / "nested_fold_assignments.csv"
    balance_path = output_dir / "fold_balance_summary.csv"
    audit_path = output_dir / "fold_validation_audit.json"
    report_path = output_dir / "FOLD_DESIGN_REPORT.md"
    runner_snapshot = output_dir / "fold_builder_snapshot.py"
    frozen_registry.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    first.components.to_csv(component_path, index=False)
    first.outer.to_csv(outer_path, index=False)
    first.nested.to_csv(nested_path, index=False)
    first.balance.to_csv(balance_path, index=False)
    runner_snapshot.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    audit = {
        "audit_version": "pferi_v2_component_disjoint_fold_audit_v1",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "development_pair_count": len(frame),
        "component_count": len(first.components),
        "endpoint_count": len(
            set(frame["endpoint_a_image_id"].astype(str))
            | set(frame["endpoint_b_image_id"].astype(str))
        ),
        "largest_component_pair_count": int(first.components["pair_count"].max()),
        "largest_component_endpoint_count": int(first.components["endpoint_count"].max()),
        "outer_fold_count": int(registry["outer_fold_count"]),
        "inner_fold_count": int(registry["inner_fold_count"]),
        "outer_assignment_row_count": len(first.outer),
        "nested_assignment_row_count": len(first.nested),
        "deterministic_reproduction_pass": deterministic,
        "outer_assignment_sha256": _frame_hash(first.outer),
        "nested_assignment_sha256": _frame_hash(first.nested),
        "endpoint_leakage_count": diagnostics["endpoint_leakage_count"],
        "outer_fold_pair_count_min": diagnostics["outer_fold_pair_count_min"],
        "outer_fold_pair_count_max": diagnostics["outer_fold_pair_count_max"],
        "outer_fold_pair_count_ideal": diagnostics["outer_fold_pair_count_ideal"],
        "inner_fold_pair_count_ratio_min": diagnostics["inner_fold_pair_count_ratio_min"],
        "inner_fold_pair_count_ratio_max": diagnostics["inner_fold_pair_count_ratio_max"],
        "structural_warnings": _structural_warnings(frame, registry),
        "validation_issues": issues,
        "real_outcomes_used": False,
        "outcome_columns_read": 0,
        "calibration_or_confirmation_input_read": False,
        "master_input_sha256": sha256_file(master_path),
        "formal_manifest_sha256": sha256_file(formal_path),
        "fold_registry_source_sha256": sha256_file(registry_path),
        "fold_registry_frozen_sha256": sha256_file(frozen_registry),
        "fold_builder_sha256": sha256_file(Path(__file__)),
        "fold_builder_snapshot_sha256": sha256_file(runner_snapshot),
        "claim_boundary": registry["claim_boundary"],
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(report_path, audit)
    checksum_paths = [
        frozen_registry, component_path, outer_path, nested_path, balance_path,
        audit_path, report_path, runner_snapshot,
    ]
    (output_dir / "CHECKSUMS.sha256").write_text(
        "\n".join(f"{sha256_file(path)}  {path.name}" for path in checksum_paths) + "\n",
        encoding="utf-8",
    )
    if status != "PASS":
        raise RuntimeError("fold validation failed: " + "; ".join(issues))
    return audit


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--master-frame",
        type=Path,
        default=ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1"
        / "restricted_outcome_free_master_derivation_frame.csv",
    )
    parser.add_argument(
        "--formal-manifest",
        type=Path,
        default=ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1"
        / "restricted_formal_pair_sampling_manifest.csv",
    )
    parser.add_argument(
        "--fold-registry",
        type=Path,
        default=ROOT / "schemas/pferi_v2/component_disjoint_fold_design_v1.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, default=445)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    audit = run(
        args.master_frame.resolve(),
        args.formal_manifest.resolve(),
        args.fold_registry.resolve(),
        args.output_dir.resolve(),
        expected_rows=args.expected_rows,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
