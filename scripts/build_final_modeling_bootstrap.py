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
AUDIT_JSON = OUTPUT_DIR / "final_modeling_bootstrap_audit.json"
CONTRACT_MD = OUTPUT_DIR / "final_modeling_contract.md"


CORE_SCOPES: dict[str, dict[str, Any]] = {
    "lynx-wild": {
        "min_rows": 3000,
        "max_rows": 3000,
        "identity_validation_allowed": True,
        "identity_column": "source_identity_label",
        "modeling_role": "known-ID CzechLynx validation core",
        "permitted_endpoint": "same/different pair validation, reviewability, risk routing",
    },
    "bobcat-wild": {
        "min_rows": 3000,
        "max_rows": 3000,
        "identity_validation_allowed": False,
        "identity_column": "",
        "modeling_role": "wild Bobcat transfer/evidence stress core",
        "permitted_endpoint": "review-readiness, comparability, evidence-risk transfer",
    },
    "bobcat-urban": {
        "min_rows": 3000,
        "max_rows": None,
        "identity_validation_allowed": False,
        "identity_column": "",
        "modeling_role": "urban/peri-urban Bobcat stress and pair contamination core",
        "permitted_endpoint": "review-readiness, comparability, domain-shift pressure",
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


def nonempty_count(rows: list[dict[str, str]], column: str) -> int:
    return sum(1 for row in rows if str(row.get(column, "")).strip())


def missing_image_count(rows: list[dict[str, str]], column: str = "final_freeze_image_path") -> int:
    missing = 0
    for row in rows:
        value = str(row.get(column, "")).strip()
        if not value or not Path(value).exists():
            missing += 1
    return missing


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
        "notes": "",
    }
    if not manifest.exists():
        out["status"] = "FAIL" if required else "OPTIONAL_MISSING"
        out["notes"] = "manifest.csv is absent"
        return out

    rows = read_rows(manifest)
    out["row_count"] = len(rows)
    out["final_freeze_image_path_nonempty"] = nonempty_count(rows, "final_freeze_image_path")
    out["missing_image_files"] = missing_image_count(rows)

    failures: list[str] = []
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

    identity_column = str(spec.get("identity_column", "")).strip()
    if spec.get("identity_validation_allowed"):
        if not identity_column or identity_column not in (rows[0].keys() if rows else []):
            failures.append("required_identity_column_missing")
        else:
            out["identity_nonempty"] = nonempty_count(rows, identity_column)
            if out["identity_nonempty"] != len(rows):
                failures.append("identity_labels_incomplete")

    if failures:
        out["status"] = "FAIL"
        out["notes"] = ";".join(failures)
    return out


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

    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    overall_status = "PASS_READY_FOR_FINAL_MODELING_BOOTSTRAP" if fail_count == 0 else "FAIL_NOT_READY"

    write_csv(INDEX_CSV, rows)
    audit = {
        "built_at_utc": utc_now(),
        "status": overall_status,
        "final_freeze_root": display_path(FINAL_FREEZE_ROOT),
        "index_csv": display_path(INDEX_CSV),
        "contract_md": display_path(CONTRACT_MD),
        "core_scopes": sorted(CORE_SCOPES),
        "optional_scopes": sorted(OPTIONAL_SCOPES),
        "fail_count": fail_count,
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
    print(f"WROTE {display_path(AUDIT_JSON)}")
    print(f"WROTE {display_path(CONTRACT_MD)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
