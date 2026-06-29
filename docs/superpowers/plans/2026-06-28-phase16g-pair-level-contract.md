# Phase16G Pair-Level Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase16G as a deterministic pair-level evidence contract and CzechLynx known-ID prototype without training the final review-router.

**Architecture:** Add a schema-first contract under `docs/phase16/`, then implement focused Python scripts that build and audit pair-level tables from Phase16F/Phase15 artifacts. The builder must keep image evidence, pair comparability, descriptor support, conflict features, labels, controls, and split fields separate so Phase16H can train a calibrated review-router later.

**Tech Stack:** Python standard library, pandas, unittest, existing repository script/test conventions.

---

## File Structure

- Create `docs/phase16/phase16g_pair_level_contract.md`: human-readable schema, phase boundary, allowed claims, and Phase16H gates.
- Create `scripts/build_phase16g_pair_feature_schema.py`: writes `phase16g_pair_feature_schema.json` and validates required column groups.
- Create `scripts/build_phase16g_czechlynx_pair_prototype.py`: builds CzechLynx pair rows from available Phase16F/Phase15 inputs, controls, labels, and split groups.
- Create `scripts/audit_phase16g_pair_table.py`: reusable audit for required columns, unique pair IDs, label boundaries, split leakage, and Bobcat claim boundaries.
- Create `tests/test_phase16g_pair_feature_schema.py`: unit tests for schema content and grouped columns.
- Create `tests/test_phase16g_czechlynx_pair_prototype.py`: fixture-level tests for CzechLynx prototype behavior.
- Create `tests/test_phase16g_pair_table_audit.py`: tests audit failures and PASS cases.
- Modify `docs/phase16/README.md`: add Phase16G as contract/prototype and Phase16H as future modeling.
- Modify `scripts/README.md`: add Phase16G entry points after Phase16F.

## Task 1: Document The Phase16G Contract

**Files:**
- Create: `docs/phase16/phase16g_pair_level_contract.md`
- Modify: `docs/phase16/README.md`

- [ ] **Step 1: Create the contract document**

Create `docs/phase16/phase16g_pair_level_contract.md` with this content:

````markdown
# Phase16G Pair-Level Evidence Contract

Date: 2026-06-28

Phase16G defines the pair-level evidence table used after Phase16F constrained selection and before Phase16H calibrated review-router modeling.

Phase16G is not final model training. It is not identity assignment. It does not report Bobcat identity accuracy without verified labels or audited same/different pair labels.

## Correct Phase Boundary

```text
Phase16E full scoring
-> result acceptance
-> Phase16F soft eligibility and constrained selection
-> manual audit calibration
-> final 3000 freeze
-> Phase16G pair-level contract and CzechLynx prototype
-> Phase16H calibrated review-router modeling
````

## Required Column Groups

```text
image_evidence_features
pair_comparability_features
descriptor_features
conflict_features
control_features
label_fields
audit_fields
split_fields
```

## Required Controls

```text
descriptor_only
quality_only
random_same_size
phase16f_selected
low_evidence_stress
```

## Claim Boundary

CzechLynx known-ID pairs may validate false-candidate burden, positive retention, risk coverage, and descriptor-evidence conflict.

Bobcat pairs remain transfer-stress and review-readiness evidence unless verified individual labels or audited same/different pair labels exist.
```

- [ ] **Step 2: Add README pointer**

Modify `docs/phase16/README.md` after the current "Next Step" section to add:

````markdown
## Phase16G Planning Boundary

Phase16G is planned as a pair-level evidence contract and CzechLynx known-ID prototype:

```text
docs/phase16/phase16g_pair_level_contract.md
docs/superpowers/specs/2026-06-28-phase16g-pair-level-contract-design.md
docs/superpowers/plans/2026-06-28-phase16g-pair-level-contract.md
````

Phase16G should not train the final review-router. Formal calibrated modeling belongs in Phase16H after Bobcat Phase16E/16F and manual audit calibration are available.
```

- [ ] **Step 3: Verify docs render cleanly**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
for path in [
    Path("docs/phase16/README.md"),
    Path("docs/phase16/phase16g_pair_level_contract.md"),
]:
    text = path.read_text()
    assert "Phase16G" in text
    assert "identity assignment" in text or "identity accuracy" in text
print("phase16g docs smoke check PASS")
PY
```

Expected:

```text
phase16g docs smoke check PASS
```

- [ ] **Step 4: Commit**

```bash
git add docs/phase16/README.md docs/phase16/phase16g_pair_level_contract.md
git commit -m "docs: define Phase16G pair-level contract"
```

## Task 2: Add The Pair Feature Schema Builder

**Files:**
- Create: `scripts/build_phase16g_pair_feature_schema.py`
- Create: `tests/test_phase16g_pair_feature_schema.py`

- [ ] **Step 1: Write the failing schema test**

Create `tests/test_phase16g_pair_feature_schema.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_phase16g_pair_feature_schema import build_schema, write_schema


class Phase16GPairFeatureSchemaTest(unittest.TestCase):
    def test_schema_contains_required_groups_and_columns(self):
        schema = build_schema()
        groups = {group["name"]: group for group in schema["column_groups"]}

        self.assertIn("image_evidence_features", groups)
        self.assertIn("pair_comparability_features", groups)
        self.assertIn("descriptor_features", groups)
        self.assertIn("conflict_features", groups)
        self.assertIn("label_fields", groups)
        self.assertIn("split_fields", groups)

        all_columns = {
            column
            for group in schema["column_groups"]
            for column in group["columns"]
        }
        for required in [
            "pair_id",
            "query_image_id",
            "candidate_image_id",
            "descriptor_similarity",
            "descriptor_evidence_conflict_flag",
            "same_identity_label",
            "label_allowed_for_modeling",
            "split_group",
        ]:
            self.assertIn(required, all_columns)

    def test_write_schema_outputs_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "schema.json"
            write_schema(output)
            loaded = json.loads(output.read_text())
            self.assertEqual(loaded["phase"], "Phase16G")
            self.assertEqual(loaded["schema_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_phase16g_pair_feature_schema.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.build_phase16g_pair_feature_schema'
```

- [ ] **Step 3: Implement the schema builder**

Create `scripts/build_phase16g_pair_feature_schema.py`:

```python
#!/usr/bin/env python3
"""Build the Phase16G pair-level feature schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_OUTPUT = Path("outputs/phase16/phase16g_pair_contract/phase16g_pair_feature_schema.json")


def build_schema() -> dict[str, object]:
    return {
        "phase": "Phase16G",
        "schema_version": "1.0",
        "claim_boundary": {
            "czechlynx": "known-id validation carrier",
            "bobcat": "transfer-stress unless verified labels or audited same/different pairs exist",
            "not_allowed": [
                "automatic identity assignment",
                "bobcat identity accuracy without verified labels",
                "new Re-ID descriptor claim",
            ],
        },
        "column_groups": [
            {"name": "identity_fields", "columns": ["pair_id", "dataset_role", "species_context", "query_image_id", "candidate_image_id"]},
            {"name": "image_evidence_features", "columns": ["query_load_success", "candidate_load_success", "query_iqa_score", "candidate_iqa_score", "weakest_iqa_score", "query_evidence_band", "candidate_evidence_band", "pair_evidence_band"]},
            {"name": "pair_comparability_features", "columns": ["query_side_probability", "candidate_side_probability", "side_compatibility", "laterality_relation", "query_pose_completeness", "candidate_pose_completeness", "weakest_pose_completeness"]},
            {"name": "descriptor_features", "columns": ["descriptor_similarity", "descriptor_rank", "descriptor_margin", "reciprocal_rank_flag", "descriptor_support_band"]},
            {"name": "conflict_features", "columns": ["visual_support_band", "descriptor_evidence_conflict_flag"]},
            {"name": "control_features", "columns": ["control_regime", "duplicate_or_near_duplicate_flag", "source_leakage_pressure_flag", "query_source_tier", "candidate_source_tier", "query_phase16f_tier", "candidate_phase16f_tier"]},
            {"name": "label_fields", "columns": ["same_identity_label", "review_action_label", "label_source", "label_allowed_for_modeling"]},
            {"name": "audit_fields", "columns": ["manual_audit_status"]},
            {"name": "split_fields", "columns": ["split_group"]},
        ],
    }


def write_schema(output_path: Path = DEFAULT_OUTPUT) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_schema(), indent=2, sort_keys=True) + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = write_schema(args.output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run schema test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_phase16g_pair_feature_schema.py -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Run schema builder**

Run:

```bash
python3 scripts/build_phase16g_pair_feature_schema.py
```

Expected:

```text
Wrote outputs/phase16/phase16g_pair_contract/phase16g_pair_feature_schema.json
```

- [ ] **Step 6: Commit**

```bash
git add scripts/build_phase16g_pair_feature_schema.py tests/test_phase16g_pair_feature_schema.py
git commit -m "feat: add Phase16G pair schema builder"
```

## Task 3: Add The Pair Table Audit

**Files:**
- Create: `scripts/audit_phase16g_pair_table.py`
- Create: `tests/test_phase16g_pair_table_audit.py`

- [ ] **Step 1: Write the failing audit tests**

Create `tests/test_phase16g_pair_table_audit.py`:

```python
import unittest

import pandas as pd

from scripts.audit_phase16g_pair_table import audit_pair_table


def valid_table(dataset_role="czechlynx_known_id"):
    return pd.DataFrame(
        [
            {
                "pair_id": "p1",
                "dataset_role": dataset_role,
                "species_context": "czechlynx" if dataset_role == "czechlynx_known_id" else "bobcat",
                "query_image_id": "q1",
                "candidate_image_id": "c1",
                "descriptor_similarity": 0.8,
                "descriptor_evidence_conflict_flag": False,
                "same_identity_label": True if dataset_role == "czechlynx_known_id" else pd.NA,
                "label_source": "czechlynx_known_id" if dataset_role == "czechlynx_known_id" else "none",
                "label_allowed_for_modeling": True if dataset_role == "czechlynx_known_id" else False,
                "split_group": "fold_0",
            }
        ]
    )


class Phase16GPairTableAuditTest(unittest.TestCase):
    def test_valid_czechlynx_table_passes(self):
        audit = audit_pair_table(valid_table())
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["errors"], [])

    def test_missing_required_column_fails(self):
        table = valid_table().drop(columns=["pair_id"])
        audit = audit_pair_table(table)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("missing_required_columns: pair_id", audit["errors"])

    def test_duplicate_pair_id_fails(self):
        table = pd.concat([valid_table(), valid_table()], ignore_index=True)
        audit = audit_pair_table(table)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("duplicate_pair_id_count: 1", audit["errors"])

    def test_bobcat_modeling_label_without_verified_source_fails(self):
        table = valid_table(dataset_role="bobcat_transfer_stress")
        table.loc[0, "label_allowed_for_modeling"] = True
        audit = audit_pair_table(table)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("bobcat_modeling_labels_require_verified_or_manual_pair_audit", audit["errors"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_phase16g_pair_table_audit.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.audit_phase16g_pair_table'
```

- [ ] **Step 3: Implement the audit script**

Create `scripts/audit_phase16g_pair_table.py`:

```python
#!/usr/bin/env python3
"""Audit Phase16G pair-level tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "pair_id",
    "dataset_role",
    "species_context",
    "query_image_id",
    "candidate_image_id",
    "descriptor_similarity",
    "descriptor_evidence_conflict_flag",
    "same_identity_label",
    "label_source",
    "label_allowed_for_modeling",
    "split_group",
]

BOBCAT_MODELING_LABEL_SOURCES = {"verified_bobcat_id", "manual_pair_audit"}


def audit_pair_table(table: pd.DataFrame) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    missing = [column for column in REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        errors.append("missing_required_columns: " + ", ".join(missing))
        return {"status": "FAIL", "row_count": int(len(table)), "errors": errors, "warnings": warnings}

    duplicate_count = int(table["pair_id"].duplicated().sum())
    if duplicate_count:
        errors.append(f"duplicate_pair_id_count: {duplicate_count}")

    if table["pair_id"].isna().any():
        errors.append("null_pair_id")

    same_image = table["query_image_id"].astype(str).eq(table["candidate_image_id"].astype(str))
    if same_image.any():
        errors.append(f"self_pair_count: {int(same_image.sum())}")

    bobcat = table["species_context"].astype(str).str.lower().eq("bobcat")
    modeling = table["label_allowed_for_modeling"].fillna(False).astype(bool)
    if (bobcat & modeling & ~table["label_source"].isin(BOBCAT_MODELING_LABEL_SOURCES)).any():
        errors.append("bobcat_modeling_labels_require_verified_or_manual_pair_audit")

    if table["split_group"].isna().any():
        warnings.append("split_group_has_missing_values")

    return {
        "status": "FAIL" if errors else "PASS",
        "row_count": int(len(table)),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    table = pd.read_csv(args.input)
    audit = audit_pair_table(table)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(f"Audit status: {audit['status']}")
    print(f"Wrote {args.output}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run audit tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_phase16g_pair_table_audit.py -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add scripts/audit_phase16g_pair_table.py tests/test_phase16g_pair_table_audit.py
git commit -m "feat: add Phase16G pair table audit"
```

## Task 4: Build The CzechLynx Pair Prototype

**Files:**
- Create: `scripts/build_phase16g_czechlynx_pair_prototype.py`
- Create: `tests/test_phase16g_czechlynx_pair_prototype.py`

- [ ] **Step 1: Write the failing CzechLynx prototype tests**

Create `tests/test_phase16g_czechlynx_pair_prototype.py`:

```python
import unittest

import pandas as pd

from scripts.build_phase16g_czechlynx_pair_prototype import build_pair_rows


class Phase16GCzechLynxPairPrototypeTest(unittest.TestCase):
    def test_build_pair_rows_creates_known_id_labels_and_controls(self):
        selected = pd.DataFrame(
            [
                {"image_id": "a", "identity_id": "id1", "phase16f_tier": "strict_core", "iqa_score": 0.9, "side_probability": 0.8},
                {"image_id": "b", "identity_id": "id1", "phase16f_tier": "strict_core", "iqa_score": 0.8, "side_probability": 0.7},
                {"image_id": "c", "identity_id": "id2", "phase16f_tier": "balanced_only", "iqa_score": 0.7, "side_probability": 0.6},
            ]
        )
        descriptor = pd.DataFrame(
            [
                {"query_image_id": "a", "candidate_image_id": "b", "descriptor_similarity": 0.95, "descriptor_rank": 1, "descriptor_margin": 0.1},
                {"query_image_id": "a", "candidate_image_id": "c", "descriptor_similarity": 0.50, "descriptor_rank": 2, "descriptor_margin": 0.05},
            ]
        )

        rows = build_pair_rows(selected, descriptor, control_regime="phase16f_selected")

        self.assertEqual(len(rows), 2)
        same = rows.loc[rows["candidate_image_id"].eq("b")].iloc[0]
        different = rows.loc[rows["candidate_image_id"].eq("c")].iloc[0]
        self.assertTrue(bool(same["same_identity_label"]))
        self.assertFalse(bool(different["same_identity_label"]))
        self.assertEqual(same["label_source"], "czechlynx_known_id")
        self.assertTrue(bool(same["label_allowed_for_modeling"]))
        self.assertEqual(same["control_regime"], "phase16f_selected")
        self.assertAlmostEqual(same["weakest_iqa_score"], 0.8)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_phase16g_czechlynx_pair_prototype.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.build_phase16g_czechlynx_pair_prototype'
```

- [ ] **Step 3: Implement the CzechLynx prototype builder**

Create `scripts/build_phase16g_czechlynx_pair_prototype.py`:

```python
#!/usr/bin/env python3
"""Build a Phase16G CzechLynx known-ID pair prototype table."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.audit_phase16g_pair_table import audit_pair_table


DEFAULT_OUTPUT_DIR = Path("outputs/phase16/phase16g_czechlynx_pair_prototype")


def _image_lookup(selected: pd.DataFrame) -> dict[str, dict[str, object]]:
    return selected.set_index("image_id").to_dict(orient="index")


def _evidence_band(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def build_pair_rows(selected: pd.DataFrame, descriptor_pairs: pd.DataFrame, control_regime: str) -> pd.DataFrame:
    lookup = _image_lookup(selected)
    rows: list[dict[str, object]] = []

    for row in descriptor_pairs.to_dict(orient="records"):
        query_id = str(row["query_image_id"])
        candidate_id = str(row["candidate_image_id"])
        if query_id not in lookup or candidate_id not in lookup:
            continue

        query = lookup[query_id]
        candidate = lookup[candidate_id]
        query_iqa = float(query.get("iqa_score", 0.0))
        candidate_iqa = float(candidate.get("iqa_score", 0.0))
        weakest_iqa = min(query_iqa, candidate_iqa)
        same_identity = query.get("identity_id") == candidate.get("identity_id")

        rows.append(
            {
                "pair_id": f"czechlynx::{query_id}::{candidate_id}",
                "dataset_role": "czechlynx_known_id",
                "species_context": "czechlynx",
                "query_image_id": query_id,
                "candidate_image_id": candidate_id,
                "query_source_tier": "czechlynx_known_id",
                "candidate_source_tier": "czechlynx_known_id",
                "query_phase16f_tier": query.get("phase16f_tier", ""),
                "candidate_phase16f_tier": candidate.get("phase16f_tier", ""),
                "query_evidence_band": _evidence_band(query_iqa),
                "candidate_evidence_band": _evidence_band(candidate_iqa),
                "pair_evidence_band": _evidence_band(weakest_iqa),
                "query_load_success": True,
                "candidate_load_success": True,
                "query_iqa_score": query_iqa,
                "candidate_iqa_score": candidate_iqa,
                "weakest_iqa_score": weakest_iqa,
                "query_side_probability": float(query.get("side_probability", 0.0)),
                "candidate_side_probability": float(candidate.get("side_probability", 0.0)),
                "side_compatibility": "unknown",
                "laterality_relation": "unknown",
                "query_pose_completeness": float(query.get("pose_completeness", 0.0)),
                "candidate_pose_completeness": float(candidate.get("pose_completeness", 0.0)),
                "weakest_pose_completeness": min(float(query.get("pose_completeness", 0.0)), float(candidate.get("pose_completeness", 0.0))),
                "descriptor_similarity": float(row.get("descriptor_similarity", 0.0)),
                "descriptor_rank": int(row.get("descriptor_rank", 0)),
                "descriptor_margin": float(row.get("descriptor_margin", 0.0)),
                "reciprocal_rank_flag": bool(row.get("reciprocal_rank_flag", False)),
                "descriptor_support_band": "high" if float(row.get("descriptor_similarity", 0.0)) >= 0.8 else "medium_or_low",
                "visual_support_band": _evidence_band(weakest_iqa),
                "descriptor_evidence_conflict_flag": bool(float(row.get("descriptor_similarity", 0.0)) >= 0.8 and weakest_iqa < 0.6),
                "control_regime": control_regime,
                "duplicate_or_near_duplicate_flag": bool(row.get("duplicate_or_near_duplicate_flag", False)),
                "source_leakage_pressure_flag": bool(row.get("source_leakage_pressure_flag", False)),
                "manual_audit_status": "not_audited",
                "review_action_label": "",
                "same_identity_label": bool(same_identity),
                "label_source": "czechlynx_known_id",
                "label_allowed_for_modeling": True,
                "split_group": str(row.get("split_group", "unassigned")),
            }
        )

    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--descriptor-pairs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--control-regime", default="phase16f_selected")
    args = parser.parse_args()

    selected = pd.read_csv(args.selected)
    descriptor_pairs = pd.read_csv(args.descriptor_pairs)
    pair_table = build_pair_rows(selected, descriptor_pairs, args.control_regime)
    audit = audit_pair_table(pair_table)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pair_table.to_csv(args.output_dir / "phase16g_czechlynx_pair_table.csv", index=False)
    pd.DataFrame([audit]).to_json(args.output_dir / "phase16g_czechlynx_pair_audit.json", orient="records", indent=2)
    pair_table.groupby("control_regime").size().rename("pair_count").reset_index().to_csv(args.output_dir / "phase16g_czechlynx_control_summary.csv", index=False)
    pair_table.groupby("split_group").size().rename("pair_count").reset_index().to_csv(args.output_dir / "phase16g_czechlynx_split_summary.csv", index=False)

    print(f"Audit status: {audit['status']}")
    print(f"Wrote {args.output_dir}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run prototype tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_phase16g_czechlynx_pair_prototype.py -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add scripts/build_phase16g_czechlynx_pair_prototype.py tests/test_phase16g_czechlynx_pair_prototype.py
git commit -m "feat: add Phase16G CzechLynx pair prototype"
```

## Task 5: Register Phase16G Entry Points

**Files:**
- Modify: `scripts/README.md`
- Modify: `docs/phase16/README.md`

- [ ] **Step 1: Update script README**

Add this section to `scripts/README.md` near the Phase16 entries:

````markdown
### Phase16G Pair-Level Contract

```bash
python3 scripts/build_phase16g_pair_feature_schema.py
python3 scripts/audit_phase16g_pair_table.py --input outputs/phase16/phase16g_czechlynx_pair_prototype/phase16g_czechlynx_pair_table.csv --output outputs/phase16/phase16g_czechlynx_pair_prototype/phase16g_czechlynx_pair_audit.json
````

Phase16G prepares pair-level tables and audits for later Phase16H review-router modeling. It does not train the final model.
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests/test_phase16g_pair_feature_schema.py \
  tests/test_phase16g_pair_table_audit.py \
  tests/test_phase16g_czechlynx_pair_prototype.py \
  -v
```

Expected:

```text
OK
```

- [ ] **Step 3: Run full test suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test*.py' -v
```

Expected:

```text
OK
```

- [ ] **Step 4: Commit**

```bash
git add docs/phase16/README.md scripts/README.md
git commit -m "docs: register Phase16G pair contract workflow"
```

## Self-Review

- Spec coverage: The plan implements the Phase16G-A schema contract, Phase16G-B CzechLynx known-ID prototype, reusable audit boundaries, docs, and Phase16H gates.
- Placeholder scan: No plan-for-later markers or unspecified test instructions remain.
- Type consistency: The schema, audit, and builder all use `pair_id`, `query_image_id`, `candidate_image_id`, `descriptor_evidence_conflict_flag`, `same_identity_label`, `label_source`, `label_allowed_for_modeling`, and `split_group` consistently.
- Claim boundary: Bobcat modeling labels are blocked unless `label_source` is `verified_bobcat_id` or `manual_pair_audit`.
