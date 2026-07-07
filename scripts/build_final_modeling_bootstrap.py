#!/usr/bin/env python3
"""Build the final modeling bootstrap contract from the physical photo freeze."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_FREEZE_ROOT = PROJECT_ROOT / "outputs/final_freeze"
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/final-modeling-bootstrap"
INDEX_CSV = OUTPUT_DIR / "final_modeling_freeze_index.csv"
IMAGE_INDEX_CSV = OUTPUT_DIR / "final_modeling_image_index.csv"
AUDIT_JSON = OUTPUT_DIR / "final_modeling_bootstrap_audit.json"
CONTRACT_MD = OUTPUT_DIR / "final_modeling_contract.md"
CLAIM_GATES_JSON = OUTPUT_DIR / "final_modeling_claim_gates.json"


CORE_SCOPES: dict[str, dict[str, Any]] = {
    "lynx-wild": {
        "min_rows": 3000,
        "max_rows": 3000,
        "identity_validation_allowed": True,
        "identity_column": "source_identity_label",
        "species": "czechlynx",
        "domain_label": "wild",
        "modeling_role": "known-ID CzechLynx validation core",
        "permitted_endpoint": "same/different pair validation, reviewability, risk routing",
        "claim_boundary": "Known-ID CzechLynx image core; supports same/different pair validation after pair construction.",
    },
    "bobcat-wild": {
        "min_rows": 3000,
        "max_rows": 3000,
        "identity_validation_allowed": False,
        "identity_column": "",
        "species": "bobcat",
        "domain_label": "wild",
        "modeling_role": "wild Bobcat transfer/evidence stress core",
        "permitted_endpoint": "review-readiness, comparability, evidence-risk transfer",
        "claim_boundary": "Bobcat clear-photo core; identity labels unavailable, so identity accuracy claims are blocked.",
    },
    "bobcat-urban": {
        "min_rows": 3000,
        "max_rows": None,
        "identity_validation_allowed": False,
        "identity_column": "",
        "species": "bobcat",
        "domain_label": "urban_periurban",
        "modeling_role": "urban/peri-urban Bobcat stress and pair contamination core",
        "permitted_endpoint": "review-readiness, comparability, domain-shift pressure",
        "claim_boundary": "Bobcat urban/peri-urban stress core; supports evidence shift diagnostics only.",
    },
}

OPTIONAL_SCOPES: dict[str, dict[str, Any]] = {
    "lynx-urban": {
        "identity_validation_allowed": False,
        "modeling_role": "small auxiliary heterogeneity note only",
        "permitted_endpoint": "qualitative/exploratory context; not a 3000-image core",
    }
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_project_path(value: str) -> Path:
    path = Path(str(value).strip())
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def nonempty_count(rows: list[dict[str, str]], column: str) -> int:
    return sum(1 for row in rows if str(row.get(column, "")).strip())


def missing_image_count(rows: list[dict[str, str]], column: str = "final_freeze_image_path") -> int:
    missing = 0
    for row in rows:
        value = str(row.get(column, "")).strip()
        if not value or not resolve_project_path(value).exists():
            missing += 1
    return missing


def stable_image_id(scope: str, row_number: int) -> str:
    return f"pferi_{scope.replace('-', '_')}_{row_number:05d}"


def first_value(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def source_image_key(row: dict[str, str]) -> str:
    return first_value(
        row,
        [
            "source_candidate_id",
            "candidate_id",
            "phase14_image_evidence_id",
            "canonical_image_key",
            "image_key",
            "source_image_uri",
            "image_uri",
        ],
    )


def build_image_index_rows(scope: str, spec: dict[str, Any], manifest: Path) -> list[dict[str, Any]]:
    rows = read_rows(manifest)
    identity_column = str(spec.get("identity_column", "")).strip()
    identity_allowed = bool(spec.get("identity_validation_allowed", False))
    index_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=1):
        image_path_value = str(row.get("final_freeze_image_path", "")).strip()
        resolved_image_path = resolve_project_path(image_path_value) if image_path_value else Path("")
        identity_label = str(row.get(identity_column, "")).strip() if identity_allowed and identity_column else ""
        index_rows.append(
            {
                "image_id": stable_image_id(scope, row_number),
                "scope": scope,
                "species": spec.get("species", ""),
                "domain_label": spec.get("domain_label", ""),
                "source_row_number": row_number,
                "source_manifest_path": display_path(manifest),
                "source_image_key": source_image_key(row),
                "source_candidate_id": first_value(
                    row,
                    [
                        "source_candidate_id",
                        "candidate_id",
                        "phase14_image_evidence_id",
                        "canonical_photo_id",
                        "photo_id",
                    ],
                ),
                "local_image_path": display_path(resolved_image_path) if image_path_value else "",
                "local_image_exists": bool(image_path_value and resolved_image_path.exists()),
                "identity_validation_allowed": identity_allowed,
                "identity_label": identity_label,
                "identity_label_status": "present" if identity_label else ("not_applicable" if not identity_allowed else "missing"),
                "modeling_role": spec["modeling_role"],
                "permitted_endpoint": spec["permitted_endpoint"],
                "claim_boundary": spec.get("claim_boundary", ""),
                "sha256": first_value(row, ["final_freeze_sha256", "sha256", "phase19_augmented_sha256"]),
                "bytes": first_value(row, ["final_freeze_bytes", "bytes"]),
                "image_width": first_value(row, ["image_width", "phase19_augmented_width"]),
                "image_height": first_value(row, ["image_height", "phase19_augmented_height"]),
            }
        )
    return index_rows


def audit_scope(scope: str, spec: dict[str, Any], required: bool) -> dict[str, Any]:
    manifest = FINAL_FREEZE_ROOT / scope / "manifest.csv"
    out: dict[str, Any] = {
        "scope": scope,
        "required": required,
        "manifest_path": display_path(manifest),
        "modeling_role": spec["modeling_role"],
        "permitted_endpoint": spec["permitted_endpoint"],
        "identity_validation_allowed": bool(spec.get("identity_validation_allowed", False)),
        "status": "PASS",
        "row_count": 0,
        "final_freeze_image_path_nonempty": 0,
        "missing_image_files": 0,
        "identity_column": spec.get("identity_column", ""),
        "identity_nonempty": "",
        "identity_unique_count": "",
        "required_columns_missing": "",
        "notes": "",
    }
    if not manifest.exists():
        out["status"] = "FAIL" if required else "OPTIONAL_MISSING"
        out["notes"] = "manifest.csv is absent"
        return out

    rows = read_rows(manifest)
    columns = set(rows[0].keys()) if rows else set()
    out["row_count"] = len(rows)
    out["final_freeze_image_path_nonempty"] = nonempty_count(rows, "final_freeze_image_path")
    out["missing_image_files"] = missing_image_count(rows)

    failures: list[str] = []
    required_columns = ["final_freeze_image_path"]
    identity_column = str(spec.get("identity_column", "")).strip()
    if spec.get("identity_validation_allowed") and identity_column:
        required_columns.append(identity_column)
    missing_columns = [column for column in required_columns if column not in columns]
    out["required_columns_missing"] = ";".join(missing_columns)
    if missing_columns:
        failures.append("required_columns_missing")

    min_rows = spec.get("min_rows")
    max_rows = spec.get("max_rows")
    if min_rows is not None and len(rows) < int(min_rows):
        failures.append(f"row_count_lt_{min_rows}")
    if max_rows is not None and len(rows) > int(max_rows):
        failures.append(f"row_count_gt_{max_rows}")
    if out["final_freeze_image_path_nonempty"] != len(rows):
        failures.append("missing_final_freeze_image_path_values")
    if out["missing_image_files"]:
        failures.append("copied_image_files_missing")

    if spec.get("identity_validation_allowed"):
        if not identity_column or identity_column not in columns:
            failures.append("required_identity_column_missing")
        else:
            out["identity_nonempty"] = nonempty_count(rows, identity_column)
            out["identity_unique_count"] = len(
                {str(row.get(identity_column, "")).strip() for row in rows if str(row.get(identity_column, "")).strip()}
            )
            if out["identity_nonempty"] != len(rows):
                failures.append("identity_labels_incomplete")

    if failures:
        out["status"] = "FAIL"
        out["notes"] = ";".join(failures)
    return out


def build_claim_gates() -> dict[str, Any]:
    blocked_claims = [
        {
            "claim": "Bobcat identity accuracy",
            "status": "blocked",
            "reason": "Bobcat wild and urban final-freeze rows do not provide verified individual identity labels.",
        },
        {
            "claim": "Bobcat false-match accuracy",
            "status": "blocked",
            "reason": "No audited Bobcat same/different pair labels are present in the modeling contract.",
        },
        {
            "claim": "Bobcat mAP/MRR/top-k identity retrieval performance",
            "status": "blocked",
            "reason": "Bobcat data are transfer/evidence-stress inputs only under the current freeze.",
        },
        {
            "claim": "PF-ERI is a new visual descriptor",
            "status": "blocked",
            "reason": "PF-ERI is defined as a post-retrieval pair-level evidence governance layer after strong descriptors.",
        },
        {
            "claim": "PF-ERI automatically identifies individuals",
            "status": "blocked",
            "reason": "The model may route evidence-admissible pairs; it does not assign final identity by itself.",
        },
    ]
    allowed_claims = [
        {
            "claim": "CzechLynx known-ID same/different pair validation",
            "status": "allowed_after_pair_construction",
            "scope": "lynx-wild",
        },
        {
            "claim": "Bobcat wild/urban evidence-risk transfer stress",
            "status": "allowed",
            "scope": "bobcat-wild,bobcat-urban",
        },
        {
            "claim": "Pair-level evidence sufficiency and review-readiness routing",
            "status": "allowed_after_calibration",
            "scope": "all core scopes",
        },
    ]
    return {
        "built_at_utc": utc_now(),
        "modeling_program": "PF-ERI Selective Evidence Sufficiency Model",
        "blocked_claims": blocked_claims,
        "allowed_claims": allowed_claims,
    }


def build_contract(rows: list[dict[str, Any]], overall_status: str) -> str:
    table = "\n".join(
        "| {scope} | {status} | {row_count} | {missing_image_files} | {identity_validation_allowed} | {permitted_endpoint} |".format(
            **row
        )
        for row in rows
    )
    return f"""# Final Modeling Bootstrap Contract

Date: 2026-07-07

Status: `{overall_status}`

This is the modeling entry contract after the project slimming. Final modeling
must start from `outputs/final_freeze/<scope>/manifest.csv` and copied images
under `outputs/final_freeze/<scope>/images/`.

| Scope | Status | Rows | Missing copied images | Identity validation allowed | Permitted endpoint |
| --- | --- | ---: | ---: | --- | --- |
{table}

## Binding Modeling Scope

- PF-ERI is a post-retrieval pair-level selective evidence governance layer.
- The first formal model is the PF-ERI Selective Evidence Sufficiency Model:
  a risk-calibrated selective inference layer for wildlife Re-ID candidate
  pairs.
- The model should estimate pair-level evidence sufficiency and calibrated
  evidence risk after strong descriptor candidate retrieval.
- CzechLynx wild known-ID rows may support same/different pair validation.
- Bobcat wild and Bobcat urban rows may support transfer stress, pair
  comparability, review-readiness, and evidence-risk pressure only.
- Bobcat identity accuracy, Bobcat false-match accuracy, and descriptor-training
  improvement claims remain blocked unless verified Bobcat identity labels or
  audited same/different Bobcat pair labels are added later.
- The machine-readable image entry point is
  `outputs/modeling-validation/final-modeling-bootstrap/final_modeling_image_index.csv`.
- The machine-readable blocked/allowed claim gate is
  `outputs/modeling-validation/final-modeling-bootstrap/final_modeling_claim_gates.json`.
- `lynx-urban` is not a required 3000-image modeling cell; it is an optional
  auxiliary heterogeneity note only.

## Selective Evidence Sufficiency Modeling Plan

Active work must be named by module purpose, not by new phase numbers.

```text
modeling-contract:
  build the final pair-level input contract from outputs/final_freeze

evidence-feature-extraction:
  compute image evidence, pair comparability, descriptor conflict, and
  domain/source stress features

known-id-evidence-sufficiency-validation:
  train and validate the evidence sufficiency model on known-ID CzechLynx pairs

risk-calibrated-evidence-admission:
  calibrate selective-risk thresholds and report risk-coverage behavior

evidence-risk-decomposition:
  explain not-ready risk by observable evidence components and reason labels

bobcat-wild-urban-transfer-stress:
  evaluate evidence-risk shift and review burden under Bobcat wild/urban data
  without identity-accuracy claims

review-budget-routing:
  select pair subsets under fixed review budget and target evidence-risk levels

robustness-and-claim-gates:
  run group-aware splits, descriptor-family stratification, ablations,
  calibration checks, and blocked-claim audits
```

Mathematical target:

```text
maximize accepted-pair coverage
subject to calibrated selective evidence risk <= alpha
```
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [audit_scope(scope, spec, required=True) for scope, spec in CORE_SCOPES.items()]
    rows.extend(audit_scope(scope, spec, required=False) for scope, spec in OPTIONAL_SCOPES.items())
    image_index_rows: list[dict[str, Any]] = []
    for scope, spec in CORE_SCOPES.items():
        manifest = FINAL_FREEZE_ROOT / scope / "manifest.csv"
        if manifest.exists():
            image_index_rows.extend(build_image_index_rows(scope, spec, manifest))

    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    duplicate_image_ids = len(image_index_rows) - len({row["image_id"] for row in image_index_rows})
    image_index_missing_files = sum(not row["local_image_exists"] for row in image_index_rows)
    if duplicate_image_ids or image_index_missing_files:
        fail_count += 1
    overall_status = "PASS_READY_FOR_FINAL_MODELING_BOOTSTRAP" if fail_count == 0 else "FAIL_NOT_READY"

    write_csv(INDEX_CSV, rows)
    write_csv(IMAGE_INDEX_CSV, image_index_rows)
    claim_gates = build_claim_gates()
    CLAIM_GATES_JSON.write_text(json.dumps(claim_gates, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit = {
        "built_at_utc": utc_now(),
        "status": overall_status,
        "final_freeze_root": display_path(FINAL_FREEZE_ROOT),
        "index_csv": display_path(INDEX_CSV),
        "image_index_csv": display_path(IMAGE_INDEX_CSV),
        "claim_gates_json": display_path(CLAIM_GATES_JSON),
        "contract_md": display_path(CONTRACT_MD),
        "core_scopes": sorted(CORE_SCOPES),
        "optional_scopes": sorted(OPTIONAL_SCOPES),
        "fail_count": fail_count,
        "image_index_rows": len(image_index_rows),
        "duplicate_image_ids": duplicate_image_ids,
        "image_index_missing_files": image_index_missing_files,
        "image_index_scope_counts": {
            scope: sum(row["scope"] == scope for row in image_index_rows)
            for scope in sorted(CORE_SCOPES)
        },
        "blocked_claim_count": len(claim_gates["blocked_claims"]),
        "claim_boundary": (
            "Readiness for PF-ERI pair-level evidence-governance modeling only; "
            "not descriptor training and not Bobcat identity accuracy."
        ),
        "rows": rows,
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CONTRACT_MD.write_text(build_contract(rows, overall_status), encoding="utf-8")

    print(overall_status)
    print(f"WROTE {display_path(INDEX_CSV)}")
    print(f"WROTE {display_path(IMAGE_INDEX_CSV)}")
    print(f"WROTE {display_path(CLAIM_GATES_JSON)}")
    print(f"WROTE {display_path(AUDIT_JSON)}")
    print(f"WROTE {display_path(CONTRACT_MD)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
