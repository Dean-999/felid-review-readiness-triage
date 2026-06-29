# Phase16G Real CzechLynx Pair Table Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run Phase16G on real CzechLynx data by bridging Phase16F selected images to Phase15 descriptor candidate pairs, then generating audited pair-level tables without training a model.

**Architecture:** Add a focused adapter that normalizes CzechLynx paths and converts the real Phase16F manifest plus Phase15 routing/top-k pairs into the generic inputs expected by the existing Phase16G prototype builder. Keep the existing schema builder, audit script, and prototype builder as the core execution layer; the new code only adapts real repository outputs and writes a run report.

**Tech Stack:** Python standard library, pandas, unittest, existing Phase16G scripts.

---

## Current Real Inputs

Use these repository outputs as defaults:

```text
outputs/phase16/phase16f_czechlynx_constrained_selection/phase16f_czechlynx_selected_3000_manifest.csv
outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv
outputs/phase16/leakage_pressure/phase16_leakage_pressure_pair_audit.csv
outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_table.csv
```

Why an adapter is needed:

```text
Phase16F selected image rows:
candidate_id, image_key, phase16f_selection_bucket, iqa_quality_proxy_score,
clip_side_view_score, clip_viewpoint_label, phase16f_balance_group

Phase15 descriptor pair rows:
query_image_evidence_id, candidate_image_evidence_id, query_image_path,
candidate_image_path, query_identity_label, candidate_identity_label,
descriptor_similarity, rank, descriptor_evidence_conflict_score
```

The join key is not a shared ID. The safest current bridge is a normalized CzechLynx path suffix:

```text
Phase16F image_key:
CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg

Phase15 query_image_path:
.../data/raw/czechlynx/CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg
```

## File Structure

- Create `scripts/run_phase16g_real_czechlynx_pair_table.py`: real-data adapter and orchestrator.
- Create `tests/test_phase16g_real_czechlynx_pair_table.py`: tests path normalization, selected-image conversion, descriptor-pair conversion, optional flag joins, and end-to-end fixture run.
- Modify `docs/phase16/README.md`: add the real CzechLynx Phase16G run command and output paths.
- Modify `scripts/README.md`: register the real-data runner.

## Output Contract

The runner must write:

```text
outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_pair_table.csv
outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_pair_audit.json
outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_control_summary.csv
outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_split_summary.csv
outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_run_summary.json
outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_run_report.md
```

## Scientific Boundary

This run is allowed to claim:

```text
Phase16G produced an audited CzechLynx known-ID pair-level evidence table for later Phase16H calibrated review-router modeling.
```

This run must not claim:

```text
final calibrated model
automatic identity assignment
Bobcat identity accuracy
new Re-ID descriptor
field deployment readiness
```

## Task 1: Add Real-Data Adapter Tests

**Files:**
- Create: `tests/test_phase16g_real_czechlynx_pair_table.py`

- [ ] **Step 1: Create failing tests**

Create `tests/test_phase16g_real_czechlynx_pair_table.py`:

```python
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_phase16g_real_czechlynx_pair_table import (
    build_descriptor_pairs_for_selected,
    build_selected_image_table,
    normalize_czechlynx_key,
    run_real_czechlynx_pair_table,
)


class Phase16GRealCzechLynxPairTableTest(unittest.TestCase):
    def test_normalize_czechlynx_key_handles_absolute_and_relative_paths(self):
        absolute = "/Users/example/project/data/raw/czechlynx/CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg"
        relative = "CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg"

        self.assertEqual(
            normalize_czechlynx_key(absolute),
            "CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg",
        )
        self.assertEqual(
            normalize_czechlynx_key(relative),
            "CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg",
        )

    def test_build_selected_image_table_maps_real_phase16f_columns(self):
        selected = pd.DataFrame(
            [
                {
                    "candidate_id": "p16e_1",
                    "image_key": "CzechLynx/site/lynx_001/a.jpg",
                    "phase16f_selection_bucket": "strict_core",
                    "phase16f_balance_group": "lynx_001",
                    "iqa_quality_proxy_score": 0.9,
                    "clip_side_view_score": 0.8,
                    "clip_viewpoint_label": "left_side",
                    "source_name": "czechlynx_real_all",
                    "phase16f_selection_rank": 1,
                }
            ]
        )

        out = build_selected_image_table(selected)

        self.assertEqual(out.loc[0, "image_id"], "CzechLynx/site/lynx_001/a.jpg")
        self.assertEqual(out.loc[0, "identity_id"], "lynx_001")
        self.assertEqual(out.loc[0, "phase16f_tier"], "strict_core")
        self.assertAlmostEqual(out.loc[0, "iqa_score"], 0.9)
        self.assertAlmostEqual(out.loc[0, "side_probability"], 0.8)

    def test_build_descriptor_pairs_keeps_only_selected_selected_pairs_and_flags_metadata(self):
        selected_images = pd.DataFrame(
            [
                {"image_id": "CzechLynx/site/lynx_001/a.jpg"},
                {"image_id": "CzechLynx/site/lynx_001/b.jpg"},
                {"image_id": "CzechLynx/site/lynx_002/c.jpg"},
            ]
        )
        routing = pd.DataFrame(
            [
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                    "rank": 1,
                    "descriptor_similarity": 0.95,
                    "descriptor_evidence_conflict_score": 0.2,
                    "query_identity_label": "lynx_001",
                    "candidate_identity_label": "lynx_001",
                    "evidence_route_decision": "review",
                },
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_999/z.jpg",
                    "rank": 2,
                    "descriptor_similarity": 0.40,
                    "descriptor_evidence_conflict_score": 0.1,
                    "query_identity_label": "lynx_001",
                    "candidate_identity_label": "lynx_999",
                    "evidence_route_decision": "review",
                },
            ]
        )
        leakage = pd.DataFrame(
            [
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                    "phase16_site_leakage_pressure": True,
                }
            ]
        )
        laterality = pd.DataFrame(
            [
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                    "phase16_pair_side_relation": "same_side",
                    "side_direction_compatibility": 1.0,
                }
            ]
        )

        out = build_descriptor_pairs_for_selected(
            routing,
            selected_images,
            leakage=leakage,
            laterality=laterality,
        )

        self.assertEqual(len(out), 1)
        row = out.iloc[0]
        self.assertEqual(row["query_image_id"], "CzechLynx/site/lynx_001/a.jpg")
        self.assertEqual(row["candidate_image_id"], "CzechLynx/site/lynx_001/b.jpg")
        self.assertTrue(bool(row["source_leakage_pressure_flag"]))
        self.assertEqual(row["laterality_relation"], "same_side")
        self.assertEqual(row["split_group"], "query::lynx_001")

    def test_run_real_czechlynx_pair_table_writes_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected_path = root / "selected.csv"
            routing_path = root / "routing.csv"
            output_dir = root / "out"

            pd.DataFrame(
                [
                    {
                        "candidate_id": "p16e_1",
                        "image_key": "CzechLynx/site/lynx_001/a.jpg",
                        "phase16f_selection_bucket": "strict_core",
                        "phase16f_balance_group": "lynx_001",
                        "iqa_quality_proxy_score": 0.9,
                        "clip_side_view_score": 0.8,
                        "clip_viewpoint_label": "left_side",
                    },
                    {
                        "candidate_id": "p16e_2",
                        "image_key": "CzechLynx/site/lynx_001/b.jpg",
                        "phase16f_selection_bucket": "strict_core",
                        "phase16f_balance_group": "lynx_001",
                        "iqa_quality_proxy_score": 0.85,
                        "clip_side_view_score": 0.7,
                        "clip_viewpoint_label": "left_side",
                    },
                ]
            ).to_csv(selected_path, index=False)
            pd.DataFrame(
                [
                    {
                        "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                        "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                        "rank": 1,
                        "descriptor_similarity": 0.95,
                        "descriptor_evidence_conflict_score": 0.2,
                        "query_identity_label": "lynx_001",
                        "candidate_identity_label": "lynx_001",
                        "evidence_route_decision": "review",
                    }
                ]
            ).to_csv(routing_path, index=False)

            summary = run_real_czechlynx_pair_table(
                selected_path=selected_path,
                routing_path=routing_path,
                output_dir=output_dir,
                leakage_path=None,
                laterality_path=None,
            )

            self.assertEqual(summary["audit_status"], "PASS")
            self.assertEqual(summary["pair_rows"], 1)
            self.assertTrue((output_dir / "phase16g_czechlynx_pair_table.csv").exists())
            self.assertTrue((output_dir / "phase16g_czechlynx_run_report.md").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PY=/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
PYTHONDONTWRITEBYTECODE=1 $PY -m unittest tests/test_phase16g_real_czechlynx_pair_table.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.run_phase16g_real_czechlynx_pair_table'
```

## Task 2: Implement The Real CzechLynx Runner

**Files:**
- Create: `scripts/run_phase16g_real_czechlynx_pair_table.py`
- Test: `tests/test_phase16g_real_czechlynx_pair_table.py`

- [ ] **Step 1: Create the runner**

Create `scripts/run_phase16g_real_czechlynx_pair_table.py`:

```python
#!/usr/bin/env python3
"""Run Phase16G CzechLynx pair-table construction on real repository outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from scripts.build_phase16g_czechlynx_pair_prototype import build_pair_rows, write_outputs
from scripts.build_phase16g_pair_feature_schema import write_schema


DEFAULT_SELECTED = Path("outputs/phase16/phase16f_czechlynx_constrained_selection/phase16f_czechlynx_selected_3000_manifest.csv")
DEFAULT_ROUTING = Path("outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv")
DEFAULT_LEAKAGE = Path("outputs/phase16/leakage_pressure/phase16_leakage_pressure_pair_audit.csv")
DEFAULT_LATERALITY = Path("outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_table.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/phase16/phase16g_czechlynx_real_pair_table")


def normalize_czechlynx_key(value: object) -> str:
    text = str(value).replace("\\", "/")
    marker = "CzechLynx/"
    if marker in text:
        return marker + text.split(marker, 1)[1]
    return text.lstrip("/")


def _numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _string(frame: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="object")
    return frame[column].fillna(default).astype(str)


def build_selected_image_table(selected: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=selected.index)
    out["image_id"] = _string(selected, "image_key").map(normalize_czechlynx_key)
    out["candidate_id"] = _string(selected, "candidate_id")
    out["identity_id"] = _string(selected, "phase16f_balance_group")
    out["phase16f_tier"] = _string(selected, "phase16f_selection_bucket")
    out["iqa_score"] = _numeric(selected, "iqa_quality_proxy_score")
    out["side_probability"] = _numeric(selected, "clip_side_view_score")
    out["pose_completeness"] = _numeric(selected, "pose_completeness")
    out["clip_viewpoint_label"] = _string(selected, "clip_viewpoint_label", "unknown")
    out["source_name"] = _string(selected, "source_name", "czechlynx")
    out["phase16f_selection_rank"] = _numeric(selected, "phase16f_selection_rank")

    if out["image_id"].duplicated().any():
        duplicate_count = int(out["image_id"].duplicated().sum())
        raise ValueError(f"Phase16F selected image_id must be unique; duplicate_count={duplicate_count}")
    if out["identity_id"].eq("").any():
        missing_count = int(out["identity_id"].eq("").sum())
        raise ValueError(f"Phase16F selected rows missing phase16f_balance_group; missing_count={missing_count}")
    return out


def _pair_key(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["query_image_id"].astype(str)
        + "||"
        + frame["candidate_image_id"].astype(str)
    )


def _optional_pair_flags(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["pair_join_key"])
    out = pd.DataFrame(index=frame.index)
    out["query_image_id"] = _string(frame, "query_image_path").map(normalize_czechlynx_key)
    out["candidate_image_id"] = _string(frame, "candidate_image_path").map(normalize_czechlynx_key)
    out["pair_join_key"] = _pair_key(out)
    for column in [
        "phase16_site_leakage_pressure",
        "phase16_pair_side_relation",
        "side_direction_compatibility",
    ]:
        if column in frame.columns:
            out[column] = frame[column]
    return out.drop_duplicates("pair_join_key")


def build_descriptor_pairs_for_selected(
    routing: pd.DataFrame,
    selected_images: pd.DataFrame,
    leakage: pd.DataFrame | None = None,
    laterality: pd.DataFrame | None = None,
) -> pd.DataFrame:
    selected_ids = set(selected_images["image_id"].astype(str))
    out = pd.DataFrame(index=routing.index)
    out["query_image_id"] = _string(routing, "query_image_path").map(normalize_czechlynx_key)
    out["candidate_image_id"] = _string(routing, "candidate_image_path").map(normalize_czechlynx_key)
    out["descriptor_similarity"] = _numeric(routing, "descriptor_similarity")
    out["descriptor_rank"] = _numeric(routing, "rank").astype(int)
    out["descriptor_margin"] = _numeric(routing, "descriptor_evidence_support_score")
    out["reciprocal_rank_flag"] = False
    out["duplicate_or_near_duplicate_flag"] = False
    out["source_leakage_pressure_flag"] = False
    out["laterality_relation"] = "unknown"
    out["side_compatibility"] = "unknown"
    out["split_group"] = "query::" + _string(routing, "query_identity_label", "unknown")

    if "descriptor_evidence_conflict_score" in routing.columns:
        out["descriptor_margin"] = pd.to_numeric(
            routing["descriptor_evidence_conflict_score"],
            errors="coerce",
        ).fillna(0.0)

    out = out[
        out["query_image_id"].isin(selected_ids)
        & out["candidate_image_id"].isin(selected_ids)
        & out["query_image_id"].ne(out["candidate_image_id"])
    ].copy()

    out["pair_join_key"] = _pair_key(out)

    leakage_flags = _optional_pair_flags(leakage)
    if not leakage_flags.empty and "phase16_site_leakage_pressure" in leakage_flags.columns:
        out = out.merge(
            leakage_flags[["pair_join_key", "phase16_site_leakage_pressure"]],
            on="pair_join_key",
            how="left",
        )
        out["source_leakage_pressure_flag"] = out["phase16_site_leakage_pressure"].fillna(False).astype(bool)
        out = out.drop(columns=["phase16_site_leakage_pressure"])

    laterality_flags = _optional_pair_flags(laterality)
    if not laterality_flags.empty:
        keep_columns = [
            column
            for column in ["pair_join_key", "phase16_pair_side_relation", "side_direction_compatibility"]
            if column in laterality_flags.columns
        ]
        out = out.merge(laterality_flags[keep_columns], on="pair_join_key", how="left")
        if "phase16_pair_side_relation" in out.columns:
            out["laterality_relation"] = out["phase16_pair_side_relation"].fillna("unknown").astype(str)
            out = out.drop(columns=["phase16_pair_side_relation"])
        if "side_direction_compatibility" in out.columns:
            out["side_compatibility"] = out["side_direction_compatibility"].fillna("unknown").astype(str)
            out = out.drop(columns=["side_direction_compatibility"])

    return out.drop(columns=["pair_join_key"]).reset_index(drop=True)


def write_run_report(summary: dict[str, object], output_dir: Path) -> None:
    lines = [
        "# Phase16G CzechLynx Real Pair Table Run",
        "",
        "This run bridges Phase16F CzechLynx selected images to Phase15 descriptor candidate pairs.",
        "It creates an audited pair-level evidence table for later Phase16H modeling.",
        "",
        "## Summary",
        "",
        f"- Selected image rows: {summary['selected_rows']:,}",
        f"- Descriptor candidate rows scanned: {summary['routing_rows']:,}",
        f"- Pair rows written: {summary['pair_rows']:,}",
        f"- Audit status: {summary['audit_status']}",
        "",
        "## Claim Boundary",
        "",
        "This output is not final model training, not automatic identity assignment, and not Bobcat identity validation.",
        "",
    ]
    (output_dir / "phase16g_czechlynx_run_report.md").write_text("\n".join(lines))


def run_real_czechlynx_pair_table(
    selected_path: Path,
    routing_path: Path,
    output_dir: Path,
    leakage_path: Path | None,
    laterality_path: Path | None,
) -> dict[str, object]:
    selected_raw = pd.read_csv(selected_path)
    routing = pd.read_csv(routing_path)
    leakage = pd.read_csv(leakage_path) if leakage_path and leakage_path.exists() else None
    laterality = pd.read_csv(laterality_path) if laterality_path and laterality_path.exists() else None

    selected_images = build_selected_image_table(selected_raw)
    descriptor_pairs = build_descriptor_pairs_for_selected(
        routing,
        selected_images,
        leakage=leakage,
        laterality=laterality,
    )
    pair_table = build_pair_rows(
        selected_images,
        descriptor_pairs,
        control_regime="phase16f_selected_real_czechlynx",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_schema(output_dir / "phase16g_pair_feature_schema.json")
    audit = write_outputs(pair_table, output_dir)
    summary = {
        "status": "PASS" if audit["status"] == "PASS" and len(pair_table) > 0 else "REVIEW",
        "audit_status": audit["status"],
        "selected_rows": int(len(selected_raw)),
        "selected_unique_images": int(selected_images["image_id"].nunique()),
        "routing_rows": int(len(routing)),
        "pair_rows": int(len(pair_table)),
        "positive_pair_rows": int(pair_table["same_identity_label"].fillna(False).astype(bool).sum()) if len(pair_table) else 0,
        "false_pair_rows": int((~pair_table["same_identity_label"].fillna(False).astype(bool)).sum()) if len(pair_table) else 0,
        "claim_boundary": "CzechLynx known-ID pair table only; no final model training and no Bobcat identity claim",
    }
    (output_dir / "phase16g_czechlynx_run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    write_run_report(summary, output_dir)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--routing", type=Path, default=DEFAULT_ROUTING)
    parser.add_argument("--leakage", type=Path, default=DEFAULT_LEAKAGE)
    parser.add_argument("--laterality", type=Path, default=DEFAULT_LATERALITY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = run_real_czechlynx_pair_table(
        selected_path=args.selected,
        routing_path=args.routing,
        output_dir=args.output_dir,
        leakage_path=args.leakage,
        laterality_path=args.laterality,
    )
    print(f"Status: {summary['status']}")
    print(f"Audit status: {summary['audit_status']}")
    print(f"Pair rows: {summary['pair_rows']}")
    print(f"Wrote {args.output_dir}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the new tests**

Run:

```bash
PY=/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
PYTHONDONTWRITEBYTECODE=1 $PY -m unittest tests/test_phase16g_real_czechlynx_pair_table.py -v
```

Expected:

```text
OK
```

## Task 3: Run Real CzechLynx Phase16G

**Files:**
- Uses: `scripts/run_phase16g_real_czechlynx_pair_table.py`
- Writes ignored outputs under: `outputs/phase16/phase16g_czechlynx_real_pair_table/`

- [ ] **Step 1: Generate the real pair table**

Run:

```bash
PY=/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
$PY scripts/run_phase16g_real_czechlynx_pair_table.py
```

Expected:

```text
Status: PASS
Audit status: PASS
Pair rows: <positive integer>
Wrote outputs/phase16/phase16g_czechlynx_real_pair_table
```

- [ ] **Step 2: Inspect summary**

Run:

```bash
cat outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_run_summary.json
```

Expected:

```text
"audit_status": "PASS"
"pair_rows": positive integer
"claim_boundary": "CzechLynx known-ID pair table only; no final model training and no Bobcat identity claim"
```

- [ ] **Step 3: Inspect output columns**

Run:

```bash
PY=/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
$PY - <<'PY'
import pandas as pd
path = "outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_pair_table.csv"
df = pd.read_csv(path)
print("rows", len(df))
print("columns", len(df.columns))
print(df[["pair_id", "descriptor_similarity", "same_identity_label", "source_leakage_pressure_flag", "laterality_relation"]].head().to_string(index=False))
assert len(df) > 0
assert df["pair_id"].is_unique
PY
```

Expected:

```text
rows <positive integer>
columns <positive integer>
```

## Task 4: Add Run Documentation

**Files:**
- Modify: `docs/phase16/README.md`
- Modify: `scripts/README.md`

- [ ] **Step 1: Update `docs/phase16/README.md`**

Add this section after the Phase16G planning boundary:

```markdown
## Phase16G Real CzechLynx Run

Run the real CzechLynx pair-table bridge after Phase16F selected images and
Phase15 descriptor candidate pairs are available:

```text
python3 scripts/run_phase16g_real_czechlynx_pair_table.py
outputs/phase16/phase16g_czechlynx_real_pair_table/
```

This output is an audited pair-level table for Phase16H planning. It is not
final calibrated model training and does not affect the Bobcat identity claim
boundary.
```

- [ ] **Step 2: Update `scripts/README.md`**

Add this bullet near other Phase16G scripts:

```markdown
- `run_phase16g_real_czechlynx_pair_table.py` - bridges the real Phase16F
  CzechLynx selected 3000 manifest to Phase15 descriptor candidate pairs,
  joins optional leakage/laterality flags, and writes the audited Phase16G
  CzechLynx real pair-table outputs.
```

- [ ] **Step 3: Verify docs**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
for path in [Path("docs/phase16/README.md"), Path("scripts/README.md")]:
    text = path.read_text()
    assert "run_phase16g_real_czechlynx_pair_table.py" in text
    assert "Phase16H" in text or "Phase 16H" in text
print("phase16g real-run docs PASS")
PY
```

Expected:

```text
phase16g real-run docs PASS
```

## Task 5: Full Verification

**Files:**
- Test: `tests/test_phase16g_real_czechlynx_pair_table.py`
- Test: all existing `tests/test*.py`

- [ ] **Step 1: Run focused Phase16G tests**

Run:

```bash
PY=/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
PYTHONDONTWRITEBYTECODE=1 $PY -m unittest \
  tests/test_phase16g_pair_feature_schema.py \
  tests/test_phase16g_pair_table_audit.py \
  tests/test_phase16g_czechlynx_pair_prototype.py \
  tests/test_phase16g_real_czechlynx_pair_table.py \
  -v
```

Expected:

```text
OK
```

- [ ] **Step 2: Run full suite**

Run:

```bash
PY=/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
PYTHONDONTWRITEBYTECODE=1 $PY -m unittest discover -s tests -p 'test*.py' -v
```

Expected:

```text
OK
```

- [ ] **Step 3: Review git diff**

Run:

```bash
git diff --stat
git status --short
```

Expected tracked/untracked changes include:

```text
scripts/run_phase16g_real_czechlynx_pair_table.py
tests/test_phase16g_real_czechlynx_pair_table.py
docs/phase16/README.md
scripts/README.md
```

## Self-Review

- Spec coverage: This plan bridges real Phase16F selected rows to Phase15 descriptor candidate pairs, preserves leakage/laterality flags when present, writes audited Phase16G outputs, and documents the run.
- Placeholder scan: No plan-for-later markers or unspecified test instructions remain.
- Type consistency: The adapter emits `image_id`, `identity_id`, `iqa_score`, `side_probability`, `query_image_id`, `candidate_image_id`, `descriptor_similarity`, `split_group`, `source_leakage_pressure_flag`, and `laterality_relation`, matching the existing Phase16G prototype builder.
- Scientific boundary: The plan does not train a model, does not alter final 3000 freeze rules, and does not create Bobcat identity claims.
