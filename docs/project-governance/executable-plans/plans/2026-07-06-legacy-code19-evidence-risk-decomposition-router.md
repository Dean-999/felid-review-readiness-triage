# legacy-code19 Evidence Risk Decomposition Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build legacy-code19 as a conservative PF-ERI evidence-risk decomposition and selective review-router modeling phase using a 3x3000 core dataset plus an auxiliary Lynx heterogeneity panel.

**Architecture:** legacy-code19 is a staged, auditable pipeline. It freezes dataset provenance first, extracts prespecified image/pair/domain factors second, trains conservative CzechLynx reviewability models third, then evaluates Bobcat wild-vs-urban transfer pressure and selective review routing without making Bobcat identity-accuracy claims.

**Tech Stack:** Python standard library, pandas, numpy, scipy, scikit-learn, statsmodels if available, matplotlib/seaborn for figures, Streamlit only for optional human review packets, project-local CSV/JSON/Markdown audit artifacts.

---

## Locked Scientific Design

legacy-code19 must use this data design:

```text
core_1: lynx_wild_known_id_core, 3000 strict CzechLynx images
core_2: bobcat_wild_camera_trap, 3000 LILA camera-trap Bobcat images
core_3: bobcat_urban_heterogeneous, 3000 iNaturalist/GBIF-style Bobcat images
auxiliary: lynx_external_heterogeneous_supplement, 500-1500 high-quality external Lynx images if available
```

Do not force a symmetric `CzechLynx-urban 3000` cell. External Lynx images are auxiliary sensitivity unless a true audited CzechLynx urban/captive source exists.

legacy-code19 must model:

```text
image-level evidence
pair-level comparability
descriptor-evidence conflict
domain/source shift
selective review-routing risk
```

legacy-code19 must not model or claim:

```text
new descriptor training
automatic identity assignment
Bobcat identity accuracy
universal top-k/mAP improvement
WildFusion/MegaDescriptor replacement
```

## File Structure

Create:

- `docs/legacy-code19/README.md`: human-readable legacy-code19 entry point and claim boundary.
- `scripts/build_legacy-code19a_dataset_manifest.py`: builds the 3x3000 core plus auxiliary manifest from frozen/local/source artifacts.
- `scripts/build_legacy-code19b_factor_table.py`: extracts prespecified image-level, pair-level, descriptor-control, and source/domain factors.
- `scripts/build_legacy-code19c_reviewability_models.py`: trains conservative reviewability baselines and PF-ERI models on CzechLynx/legacy-code18 labels.
- `scripts/build_legacy-code19d_selective_router.py`: calibrates risk and produces risk-coverage/review-budget/defer curves.
- `scripts/build_legacy-code19e_transfer_risk_analysis.py`: compares Bobcat wild camera-trap vs Bobcat urban/heterogeneous evidence-risk profiles.
- `scripts/build_legacy-code19f_reason_enrichment_packet.py`: creates a compact review packet for not-ready reason labels.
- `scripts/build_legacy-code19g_claim_gate.py`: writes the final legacy-code19 claim gate and model card.
- `tests/test_legacy-code19_pipeline.py`: unit and smoke tests for all legacy-code19 builders.

Outputs:

- `outputs/legacy-code19/legacy-code19a_dataset_manifest/`
- `outputs/legacy-code19/legacy-code19b_factor_table/`
- `outputs/legacy-code19/legacy-code19c_reviewability_models/`
- `outputs/legacy-code19/legacy-code19d_selective_router/`
- `outputs/legacy-code19/legacy-code19e_transfer_risk_analysis/`
- `outputs/legacy-code19/legacy-code19f_reason_enrichment_packet/`
- `outputs/legacy-code19/legacy-code19g_claim_gate/`

Modify:

- `PROJECT_RULES.md`: already contains the legacy-code19 hard rule; future edits must preserve it.
- `docs/CURRENT_PROJECT_MAP.md`: already points to this plan.
- `docs/logs/daily_work_log.md`: record each legacy-code19 execution day.

## Task 1: legacy-code19a Dataset Manifest

**Files:**
- Create: `scripts/build_legacy-code19a_dataset_manifest.py`
- Create: `tests/test_legacy-code19_pipeline.py`
- Create: `docs/legacy-code19/README.md`
- Output: `outputs/legacy-code19/legacy-code19a_dataset_manifest/legacy-code19a_dataset_manifest.csv`
- Output: `outputs/legacy-code19/legacy-code19a_dataset_manifest/legacy-code19a_dataset_manifest_audit.json`

- [ ] **Step 1: Write manifest tests**

Add tests that assert the builder can produce the required cell schema and refuses to label external Lynx data as CzechLynx urban.

```python
import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class legacy-code19pipelinetests(unittest.TestCase):
    def test_legacy-code19a_manifest_builder_outputs_required_cells(self):
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19a_dataset_manifest.py"],
            cwd=REPO,
            check=True,
        )
        out_dir = REPO / "outputs/legacy-code19/legacy-code19a_dataset_manifest"
        manifest = out_dir / "legacy-code19a_dataset_manifest.csv"
        audit = out_dir / "legacy-code19a_dataset_manifest_audit.json"
        self.assertTrue(manifest.exists())
        self.assertTrue(audit.exists())
        rows = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))
        self.assertGreaterEqual(len(rows), 9000)
        cells = {row["legacy-code19_cell"] for row in rows}
        self.assertIn("lynx_wild_known_id_core", cells)
        self.assertIn("bobcat_wild_camera_trap", cells)
        self.assertIn("bobcat_urban_heterogeneous", cells)
        self.assertNotIn("czechlynx_urban", cells)
        data = json.load(audit.open(encoding="utf-8"))
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["dataset_design"], "3x3000_core_plus_auxiliary")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19a_manifest_builder_outputs_required_cells
```

Expected: FAIL because `scripts/build_legacy-code19a_dataset_manifest.py` does not exist.

- [ ] **Step 3: Implement the manifest builder**

Create `scripts/build_legacy-code19a_dataset_manifest.py` with a minimal deterministic builder that reads:

```text
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/czechlynx_frozen_manifest.csv
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/bobcat_frozen_manifest.csv
outputs/legacy-code14/legacy-code14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_all_passed.csv
sources/2026-07-06_legacy-code19_4x3000_dataset_source_scout.md
```

Required manifest columns:

```text
legacy-code19_image_id
legacy-code19_cell
species
domain_label
source_platform
source_dataset
source_candidate_id
source_image_uri
source_image_path
frozen_image_path
identity_label_available
identity_label
quality_gate
license
attribution
selection_rank
claim_boundary
```

Selection rules:

```text
lynx_wild_known_id_core: first 3000 czechlynx frozen rows
bobcat_urban_heterogeneous: first 3000 bobcat frozen rows
bobcat_wild_camera_trap: first 3000 FCF high-evidence rows
lynx_external_heterogeneous_supplement: zero rows until a verified source manifest is added
```

- [ ] **Step 4: Run manifest test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19a_manifest_builder_outputs_required_cells
```

Expected: PASS.

- [ ] **Step 5: Commit legacy-code19a**

```bash
git add scripts/build_legacy-code19a_dataset_manifest.py tests/test_legacy-code19_pipeline.py docs/legacy-code19/README.md outputs/legacy-code19/legacy-code19a_dataset_manifest
git commit -m "feat: add legacy-code19a dataset manifest"
```

## Task 2: legacy-code19b Factor Table

**Files:**
- Create: `scripts/build_legacy-code19b_factor_table.py`
- Modify: `tests/test_legacy-code19_pipeline.py`
- Output: `outputs/legacy-code19/legacy-code19b_factor_table/legacy-code19b_factor_table.csv`
- Output: `outputs/legacy-code19/legacy-code19b_factor_table/legacy-code19b_factor_table_audit.json`

- [ ] **Step 1: Add factor table tests**

Add a test requiring the six locked high-value factors and leakage-blocked columns.

```python
    def test_legacy-code19b_factor_table_has_locked_factor_schema(self):
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19a_dataset_manifest.py"],
            cwd=REPO,
            check=True,
        )
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19b_factor_table.py"],
            cwd=REPO,
            check=True,
        )
        table = REPO / "outputs/legacy-code19/legacy-code19b_factor_table/legacy-code19b_factor_table.csv"
        rows = list(csv.DictReader(table.open(newline="", encoding="utf-8")))
        self.assertGreaterEqual(len(rows), 9000)
        fields = set(rows[0])
        required = {
            "visible_pattern_area_score",
            "viewpoint_side_compatibility",
            "body_part_overlap_score",
            "night_or_motion_blur_risk",
            "cross_descriptor_agreement_score",
            "source_domain_shift_score",
        }
        self.assertTrue(required.issubset(fields))
        forbidden = {"same_identity_known_id", "identity_label_as_feature", "evidence_group"}
        self.assertTrue(forbidden.isdisjoint(fields))
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19b_factor_table_has_locked_factor_schema
```

Expected: FAIL because the factor builder does not exist.

- [ ] **Step 3: Implement conservative factor extraction**

Create `scripts/build_legacy-code19b_factor_table.py`. Use existing manifest columns and available image dimensions/metadata. If a factor cannot be measured from current metadata, write a documented neutral value plus a `factor_measurement_status` field instead of inventing evidence.

Required factor defaults:

```text
visible_pattern_area_score: subject area fraction when available, else 0.5 with status estimated_missing_detector_bbox
viewpoint_side_compatibility: 0.5 until side labels exist
body_part_overlap_score: 0.5 until body-part labels exist
night_or_motion_blur_risk: 0.5 until image-level blur/night extraction exists
cross_descriptor_agreement_score: 0.5 until both descriptor scores are joined
source_domain_shift_score: 0.0 for CzechLynx wild, 0.5 for Bobcat wild camera-trap, 1.0 for Bobcat urban heterogeneous, 0.75 for Lynx auxiliary
```

The audit must list which factors are measured, estimated, or pending enriched extraction.

- [ ] **Step 4: Run factor tests**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19b_factor_table_has_locked_factor_schema
```

Expected: PASS.

- [ ] **Step 5: Commit legacy-code19b**

```bash
git add scripts/build_legacy-code19b_factor_table.py tests/test_legacy-code19_pipeline.py outputs/legacy-code19/legacy-code19b_factor_table
git commit -m "feat: add legacy-code19b factor table"
```

## Task 3: legacy-code19c CzechLynx Reviewability Models

**Files:**
- Create: `scripts/build_legacy-code19c_reviewability_models.py`
- Modify: `tests/test_legacy-code19_pipeline.py`
- Output: `outputs/legacy-code19/legacy-code19c_reviewability_models/`

- [ ] **Step 1: Add reviewability model smoke test**

```python
    def test_legacy-code19c_reviewability_models_write_baseline_comparison(self):
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19c_reviewability_models.py"],
            cwd=REPO,
            check=True,
        )
        out_dir = REPO / "outputs/legacy-code19/legacy-code19c_reviewability_models"
        comparison = out_dir / "legacy-code19c_model_comparison.csv"
        gate = out_dir / "legacy-code19c_model_claim_gate.json"
        self.assertTrue(comparison.exists())
        self.assertTrue(gate.exists())
        rows = list(csv.DictReader(comparison.open(newline="", encoding="utf-8")))
        model_names = {row["model_name"] for row in rows}
        self.assertIn("descriptor_similarity_only", model_names)
        self.assertIn("image_quality_only", model_names)
        self.assertIn("pf_eri_evidence_only", model_names)
        self.assertIn("descriptor_quality_pf_eri", model_names)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19c_reviewability_models_write_baseline_comparison
```

Expected: FAIL because the model builder does not exist.

- [ ] **Step 3: Implement conservative model comparison**

Train only on legacy-code18 human review labels and legacy-code18d/legacy-code18m features. Required model families:

```text
descriptor_similarity_only
image_quality_only
descriptor_plus_quality
pf_eri_evidence_only
descriptor_quality_pf_eri
```

Metrics:

```text
auc_review_ready
brier_score
mean_score_ready
mean_score_not_ready_or_uncertain
query_cluster_bootstrap_ci_lower
query_cluster_bootstrap_ci_upper
```

The claim gate may pass only if PF-ERI evidence adds reviewability utility beyond image quality and is not reported as identity accuracy.

- [ ] **Step 4: Run model smoke test**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19c_reviewability_models_write_baseline_comparison
```

Expected: PASS.

- [ ] **Step 5: Commit legacy-code19c**

```bash
git add scripts/build_legacy-code19c_reviewability_models.py tests/test_legacy-code19_pipeline.py outputs/legacy-code19/legacy-code19c_reviewability_models
git commit -m "feat: add legacy-code19c reviewability model comparison"
```

## Task 4: legacy-code19d Selective Router

**Files:**
- Create: `scripts/build_legacy-code19d_selective_router.py`
- Modify: `tests/test_legacy-code19_pipeline.py`
- Output: `outputs/legacy-code19/legacy-code19d_selective_router/`

- [ ] **Step 1: Add selective-router test**

```python
    def test_legacy-code19d_selective_router_outputs_risk_coverage(self):
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19d_selective_router.py"],
            cwd=REPO,
            check=True,
        )
        out_dir = REPO / "outputs/legacy-code19/legacy-code19d_selective_router"
        curves = out_dir / "legacy-code19d_risk_coverage_curve.csv"
        policy = out_dir / "legacy-code19d_router_policy.csv"
        self.assertTrue(curves.exists())
        self.assertTrue(policy.exists())
        rows = list(csv.DictReader(policy.open(newline="", encoding="utf-8")))
        actions = {row["router_action"] for row in rows}
        self.assertEqual(actions, {"accept_review_ready", "cautious_review", "defer_low_evidence"})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19d_selective_router_outputs_risk_coverage
```

Expected: FAIL because the router builder does not exist.

- [ ] **Step 3: Implement calibrated selective routing**

Use legacy-code19c scores. Output:

```text
legacy-code19d_risk_coverage_curve.csv
legacy-code19d_review_budget_curve.csv
legacy-code19d_calibration_curve.csv
legacy-code19d_router_policy.csv
legacy-code19d_selective_router_audit.json
```

Router actions:

```text
accept_review_ready: calibrated risk <= 0.10
cautious_review: 0.10 < calibrated risk <= 0.35
defer_low_evidence: calibrated risk > 0.35
```

If calibration is not reliable, the audit status must be `CALIBRATION_WEAK_USE_RANKED_RISK_ONLY`.

- [ ] **Step 4: Run router test**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19d_selective_router_outputs_risk_coverage
```

Expected: PASS.

- [ ] **Step 5: Commit legacy-code19d**

```bash
git add scripts/build_legacy-code19d_selective_router.py tests/test_legacy-code19_pipeline.py outputs/legacy-code19/legacy-code19d_selective_router
git commit -m "feat: add legacy-code19d selective router"
```

## Task 5: legacy-code19e Bobcat Wild-vs-Urban Transfer Risk

**Files:**
- Create: `scripts/build_legacy-code19e_transfer_risk_analysis.py`
- Modify: `tests/test_legacy-code19_pipeline.py`
- Output: `outputs/legacy-code19/legacy-code19e_transfer_risk_analysis/`

- [ ] **Step 1: Add transfer-risk test**

```python
    def test_legacy-code19e_transfer_risk_keeps_bobcat_identity_claim_blocked(self):
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19e_transfer_risk_analysis.py"],
            cwd=REPO,
            check=True,
        )
        audit = REPO / "outputs/legacy-code19/legacy-code19e_transfer_risk_analysis/legacy-code19e_transfer_risk_audit.json"
        data = json.load(audit.open(encoding="utf-8"))
        self.assertEqual(data["bobcat_identity_accuracy_claim"], "BLOCKED_NO_VERIFIED_IDENTITY_LABELS")
        self.assertEqual(data["allowed_claim"], "bobcat_wild_vs_urban_evidence_risk_pressure")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19e_transfer_risk_keeps_bobcat_identity_claim_blocked
```

Expected: FAIL because the transfer-risk builder does not exist.

- [ ] **Step 3: Implement transfer-risk analysis**

Compare Bobcat wild camera-trap and Bobcat urban/heterogeneous cells on:

```text
visible_pattern_area_score
night_or_motion_blur_risk
source_domain_shift_score
predicted_not_ready_risk
router_action_fraction
defer_low_evidence_fraction
```

Output:

```text
legacy-code19e_group_risk_summary.csv
legacy-code19e_factor_shift_summary.csv
legacy-code19e_router_action_by_domain.csv
legacy-code19e_transfer_risk_audit.json
```

- [ ] **Step 4: Run transfer-risk test**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19e_transfer_risk_keeps_bobcat_identity_claim_blocked
```

Expected: PASS.

- [ ] **Step 5: Commit legacy-code19e**

```bash
git add scripts/build_legacy-code19e_transfer_risk_analysis.py tests/test_legacy-code19_pipeline.py outputs/legacy-code19/legacy-code19e_transfer_risk_analysis
git commit -m "feat: add legacy-code19e transfer risk analysis"
```

## Task 6: legacy-code19f Reason Enrichment Packet

**Files:**
- Create: `scripts/build_legacy-code19f_reason_enrichment_packet.py`
- Modify: `tests/test_legacy-code19_pipeline.py`
- Output: `outputs/legacy-code19/legacy-code19f_reason_enrichment_packet/`

- [ ] **Step 1: Add reason-packet test**

```python
    def test_legacy-code19f_reason_packet_has_required_reason_schema(self):
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19f_reason_enrichment_packet.py"],
            cwd=REPO,
            check=True,
        )
        packet = REPO / "outputs/legacy-code19/legacy-code19f_reason_enrichment_packet/legacy-code19f_reason_review_packet.csv"
        rows = list(csv.DictReader(packet.open(newline="", encoding="utf-8")))
        self.assertGreater(len(rows), 0)
        fields = set(rows[0])
        self.assertTrue({"reviewability_decision", "primary_not_ready_reason", "secondary_not_ready_reason"}.issubset(fields))
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19f_reason_packet_has_required_reason_schema
```

Expected: FAIL because the packet builder does not exist.

- [ ] **Step 3: Implement reason enrichment packet**

Create a compact packet of high-risk, uncertain, and disagreement examples. Required reason options:

```text
low_single_image_evidence
non_comparable_viewpoint_or_side
partial_body_or_occlusion
night_motion_or_blur
descriptor_visual_conflict
source_domain_shift_risk
identity_uncertain_but_reviewable
other
```

- [ ] **Step 4: Run reason-packet test**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19f_reason_packet_has_required_reason_schema
```

Expected: PASS.

- [ ] **Step 5: Commit legacy-code19f**

```bash
git add scripts/build_legacy-code19f_reason_enrichment_packet.py tests/test_legacy-code19_pipeline.py outputs/legacy-code19/legacy-code19f_reason_enrichment_packet
git commit -m "feat: add legacy-code19f reason enrichment packet"
```

## Task 7: legacy-code19g Claim Gate And Model Card

**Files:**
- Create: `scripts/build_legacy-code19g_claim_gate.py`
- Modify: `tests/test_legacy-code19_pipeline.py`
- Output: `outputs/legacy-code19/legacy-code19g_claim_gate/legacy-code19g_claim_gate.csv`
- Output: `outputs/legacy-code19/legacy-code19g_claim_gate/legacy-code19_model_card.md`

- [ ] **Step 1: Add claim-gate test**

```python
    def test_legacy-code19g_claim_gate_blocks_overclaims(self):
        subprocess.run(
            [sys.executable, "scripts/build_legacy-code19g_claim_gate.py"],
            cwd=REPO,
            check=True,
        )
        gate = REPO / "outputs/legacy-code19/legacy-code19g_claim_gate/legacy-code19g_claim_gate.csv"
        rows = list(csv.DictReader(gate.open(newline="", encoding="utf-8")))
        status_by_claim = {row["claim_name"]: row["status"] for row in rows}
        self.assertEqual(status_by_claim["pf_eri_new_descriptor"], "BLOCKED")
        self.assertEqual(status_by_claim["bobcat_identity_accuracy"], "BLOCKED")
        self.assertIn(status_by_claim["pair_level_evidence_governance"], {"PASS", "MIXED"})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19g_claim_gate_blocks_overclaims
```

Expected: FAIL because the claim-gate builder does not exist.

- [ ] **Step 3: Implement claim gate and model card**

Claim gate rows:

```text
pair_level_evidence_governance
reviewability_calibration
selective_router_risk_coverage
bobcat_wild_vs_urban_evidence_risk
auxiliary_lynx_heterogeneity_sensitivity
pf_eri_new_descriptor
automatic_identity_assignment
bobcat_identity_accuracy
universal_topk_map_improvement
```

The model card must include:

```text
intended use
not intended use
training/evaluation data
known limitations
factor measurement status
calibration status
domain transfer caution
allowed claims
blocked claims
```

- [ ] **Step 4: Run claim-gate test**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline.legacy-code19pipelinetests.test_legacy-code19g_claim_gate_blocks_overclaims
```

Expected: PASS.

- [ ] **Step 5: Commit legacy-code19g**

```bash
git add scripts/build_legacy-code19g_claim_gate.py tests/test_legacy-code19_pipeline.py outputs/legacy-code19/legacy-code19g_claim_gate
git commit -m "feat: add legacy-code19g claim gate and model card"
```

## Task 8: Full Pipeline Verification

**Files:**
- Modify: `docs/legacy-code19/README.md`
- Modify: `docs/logs/daily_work_log.md`

- [ ] **Step 1: Run the complete legacy-code19 smoke suite**

Run:

```bash
python3 -m unittest tests.test_legacy-code19_pipeline
```

Expected: PASS for every legacy-code19 test.

- [ ] **Step 2: Run all legacy-code19 builders in order**

Run:

```bash
python3 scripts/build_legacy-code19a_dataset_manifest.py
python3 scripts/build_legacy-code19b_factor_table.py
python3 scripts/build_legacy-code19c_reviewability_models.py
python3 scripts/build_legacy-code19d_selective_router.py
python3 scripts/build_legacy-code19e_transfer_risk_analysis.py
python3 scripts/build_legacy-code19f_reason_enrichment_packet.py
python3 scripts/build_legacy-code19g_claim_gate.py
```

Expected: each command exits 0 and writes its audit file.

- [ ] **Step 3: Verify overclaim blocks**

Run:

```bash
rg -n "Bobcat identity accuracy|new descriptor|automatic identity" outputs/legacy-code19/legacy-code19g_claim_gate docs/legacy-code19 PROJECT_RULES.md
```

Expected: every occurrence is either a blocked claim or a forbidden-use statement.

- [ ] **Step 4: Update legacy-code19 README and daily log**

Update `docs/legacy-code19/README.md` with the final artifact list, claim gate status, and next action. Update `docs/logs/daily_work_log.md` with commands run, files changed, scientific decision, and next action.

- [ ] **Step 5: Commit verification docs**

```bash
git add docs/legacy-code19/README.md docs/logs/daily_work_log.md outputs/legacy-code19
git commit -m "docs: record legacy-code19 pipeline verification"
```

## Self-Review

- Spec coverage: The plan covers the 3x3000 core plus auxiliary dataset design, the six locked high-value factors, CzechLynx reviewability modeling, calibration, selective routing, Bobcat wild-vs-urban transfer risk, reason-label enrichment, and final claim gates.
- Placeholder scan: The plan contains no unfinished placeholder markers or undefined future placeholders.
- Type consistency: The same cell names, output directories, and claim names are used across tasks.
- Scope check: The plan is a single legacy-code19 modeling pipeline with staged outputs. It is large but sequential and testable task-by-task.
