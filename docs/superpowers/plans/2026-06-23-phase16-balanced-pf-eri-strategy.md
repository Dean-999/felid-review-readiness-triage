# Phase 16 Balanced PF-ERI Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a competition-ready, paper-defensible, and tool-oriented PF-ERI 2.0 modeling workflow whose core is pair-level evidence utility, descriptor-evidence conflict detection, calibrated review routing, and risk-controlled evaluation. Laterality-aware sampling, background/site leakage-pressure audit, strong-model benchmarking, augmentation, ecological context, and captive imagery are data-governance or validation safeguards around the model, not replacements for the main line.

**Architecture:** Phase 16 keeps PF-ERI as the algorithmic center: strong Re-ID retrieval produces candidate pairs, PF-ERI estimates admissible pair evidence and descriptor-evidence conflict, then a calibrated policy routes each pair into accept/review/defer/species-level/non-comparable actions. The seven advisor-suggested dimensions are implemented as sampling, audit, benchmark, or robustness layers that protect this modeling claim. The implementation stays in focused scripts under `scripts/`, generated outputs under `outputs/phase16/`, and interpretation docs under `docs/phase16/`.

**Tech Stack:** Python 3, pandas, numpy, scikit-learn where needed, existing CSV/JSON artifacts under `outputs/phase14/` and `outputs/phase15/`, pytest for new unit tests, Markdown documentation.

---

## Strategic Confidence Audit

Before implementing this plan, run this reasoning loop and keep it visible in the Phase 16 report:

```text
Question: Do we have 100% strategic confidence that this direction balances competition, paper, and tool value?
Initial answer: No.
```

### Vulnerability 1: Bobcat lacks verified individual IDs

Risk: Urban-vs-wild could be misread as bobcat identity-accuracy validation.

Repair:
- Keep CzechLynx as the only quantitative known-ID validation carrier.
- Treat bobcat as transfer stress, review-readiness, ambiguity pressure, and human pair-audit target.
- Every bobcat table must include a claim-boundary field.

Confidence after repair: high.

### Vulnerability 2: Laterality is under-specified

Risk: Pair-level comparability can be biased if left/right/both/frontal/rear is unknown or imbalanced, but laterality is a data-selection and audit constraint, not the main contribution.

Repair:
- Add an explicit laterality schema.
- Build a manual laterality audit package.
- Recompute pair-level comparability with `same_side`, `opposite_side`, `one_unknown`, and `non_lateral` categories when labels exist.
- Report known-side and full-pool results separately.
- Keep laterality as a bias-control/sampling rule around PF-ERI, not as a standalone algorithmic claim.

Confidence after repair: high if enough laterality labels are audited; medium if laterality remains mostly unknown.

### Vulnerability 3: Background/site leakage could inflate similarity

Risk: High descriptor similarity may reflect camera/site/background instead of animal identity evidence.

Repair:
- Add site/date/path-derived leakage proxies where exact protected metadata cannot be exposed.
- Treat Phase 16A as leakage-pressure auditing only, not causal proof.
- In CzechLynx, test same-site hard negatives and different-site positives only when metadata supports it.
- In bobcat, report background/site pressure only, not false-match accuracy.

Confidence after repair: high for diagnostic leakage-pressure claims; causal claims are explicitly out of scope unless stronger evidence becomes available.

### Vulnerability 4: Weak-baseline criticism

Risk: Beating descriptor-only or quality-only may not convince a strong reviewer or tool user.

Repair:
- Keep MegaDescriptor as fixed baseline.
- Add a strong-model benchmark interface for WildFusion-style outputs or external local-matching scores.
- If WildFusion cannot be run immediately, produce a cloud package and a benchmark contract so the comparison is ready.

Confidence after repair: high if WildFusion or equivalent scores are obtained; medium if only packaged.

### Vulnerability 5: Project scope can sprawl

Risk: Adding generative AI, augmentation, captive data, ecological priors, and strong models all at once makes the project incoherent.

Repair:
- Phase 16A data-governance layer: laterality-aware sampling, background/site leakage-pressure audit, and strong-model benchmark hook.
- Phase 16B optional: ecological/spatiotemporal plausibility.
- Phase 16C optional: augmentation/generative robustness stress.
- Captive data remains future calibration ceiling, not current main axis.

Confidence after repair: high.

### Final Strategy Confidence

```text
Factually defensible confidence: high, not absolute.
Reason: the plan has explicit claim boundaries, known-ID validation, leakage-pressure diagnostics, and strong-baseline preparation.
Residual dependency: laterality labels and strong-model outputs must be generated or audited before final safeguard claims; the central PF-ERI modeling claims still depend on pair-level evidence/routing validation.
```

## Feasibility Gate Matrix

Use this matrix to prevent Phase 16 from becoming too hard or too diffuse. Items in this table are not automatically core contributions; they become core only if they directly improve PF-ERI evidence modeling, routing, or risk evaluation.

| Proposal | Current status | Why it matters | Feasible Phase 16A action | Claim allowed now | Claim not allowed now |
|---|---|---|---|---|---|
| Laterality-aware sampling | Partly available but under-labeled | Prevents biased pair selection and non-comparable side comparisons | Add schema, sample manual audit candidates, compute known/unknown side diagnostics | Laterality is a sampling and pair-audit constraint | Laterality is the core algorithmic contribution or full left/right performance proof before labels exist |
| Background/site leakage | Metadata may be incomplete or protected | High similarity may reflect context instead of animal evidence | Estimate leakage pressure from path/date/site proxies | High-similarity pairs show more or less leakage pressure | Model causally uses background |
| Strong-model benchmark | MegaDescriptor exists; WildFusion may require external/cloud run | Avoid weak-baseline criticism | Package stable image/pair contract for returned strong-model scores | PF-ERI can be evaluated around best available scores | PF-ERI beats WildFusion before scores return |
| Ecological/spatiotemporal plausibility | Depends on metadata availability | Activity range and location can guide review plausibility | Defer to Phase 16B; only inventory metadata now | Potential future risk prior | Identity evidence is proven by location/time |
| Generative/augmentation robustness | Technically possible but risky for patterns | Tests stability under blur/occlusion/domain shift | Defer to Phase 16C; do not train on generated identity evidence | Future robustness stress test | Generated images are real identity evidence |
| Captive imagery | New data source and domain | Could provide high-quality calibration ceiling | Future extension only | Possible calibration reference | Third main axis in current study |

Implementation rule:

```text
If a proposal cannot directly support PF-ERI pair-level evidence modeling, review routing, or risk-controlled evaluation with existing data or a small audit package, it remains a data safeguard or extension, not a core modeling task.
```

---

## File Structure

Create these files:

- `docs/phase16/README.md` — Phase 16 index and claim boundaries.
- `docs/phase16/phase16_balanced_strategy_cn.md` — Chinese strategy narrative for competition/paper/tool alignment.
- `docs/phase16/phase16_literature_gap_matrix.md` — Seven-dimension gap review mapped to project decisions.
- `scripts/build_phase16_laterality_audit_table.py` — Builds laterality audit candidates and schema.
- `scripts/build_phase16_laterality_aware_pair_audit.py` — Recomputes pair comparability with laterality-aware categories.
- `scripts/build_phase16_leakage_pressure_audit.py` — Diagnoses site/path/background leakage pressure using available proxies.
- `scripts/package_phase16_strong_model_benchmark.py` — Creates a cloud/external package for WildFusion or equivalent benchmark scoring.
- `scripts/build_phase16_integrated_strategy_report.py` — Combines Phase 16 outputs into summary tables and Markdown.
- `tests/test_phase16_laterality_logic.py` — Unit tests for laterality and pair-side relation logic.
- `tests/test_phase16_leakage_logic.py` — Unit tests for path/site leakage proxy logic.

Modify these files:

- `PROJECT_RULES.md` — Add Phase 16 strategy boundaries.
- `docs/phase15/README.md` — Point to Phase 16 as next reliability-control phase.

Generated outputs:

- `outputs/phase16/laterality_audit/phase16_laterality_audit_candidates.csv`
- `outputs/phase16/laterality_audit/phase16_laterality_schema.json`
- `outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_table.csv`
- `outputs/phase16/leakage_pressure/phase16_leakage_pressure_pair_audit.csv`
- `outputs/phase16/strong_model_benchmark/phase16_strong_model_benchmark_manifest.csv`
- `outputs/phase16/integrated_report/phase16_integrated_strategy_report.md`

---

## Task 1: Add Phase 16 Strategy Boundaries

**Files:**
- Create: `docs/phase16/README.md`
- Create: `docs/phase16/phase16_balanced_strategy_cn.md`
- Modify: `PROJECT_RULES.md`
- Modify: `docs/phase15/README.md`

- [ ] **Step 1: Create the Phase 16 README**

Write `docs/phase16/README.md` with this content:

```markdown
# Phase 16: Balanced PF-ERI 2.0 Strategy

Phase 16 upgrades PF-ERI from a five-action review-routing prototype into a competition-ready, paper-defensible, and tool-oriented evidence reliability workflow.

Core priority:

```text
competition clarity + paper rigor + practical review-routing utility
```

Phase 16 keeps the existing scientific boundary:

- CzechLynx is the known-ID validation carrier.
- Bobcat is an urban/peri-urban transfer stress and review-readiness context unless verified individual IDs or audited same/different pair labels are available.
- PF-ERI is not a new Re-ID descriptor and does not automatically assign identity.

Phase 16 adds three required data-governance and validation safeguards around the PF-ERI model:

1. Laterality-aware sampling and pair audit.
2. Background/site leakage pressure diagnostics.
3. Strong-model benchmark preparation against MegaDescriptor/WildFusion-style workflows.

Optional extensions:

- ecological/spatiotemporal plausibility;
- augmentation/generative robustness stress;
- captive imagery as future high-quality calibration ceiling.
```

- [ ] **Step 2: Create the Chinese strategy document**

Write `docs/phase16/phase16_balanced_strategy_cn.md` with this content:

```markdown
# Phase 16 平衡战略：竞赛、论文与工具价值

## 核心定位

Phase 16 不把项目改成单纯的 urban vs wild 对比，也不把 PF-ERI 说成新的 Re-ID 模型。

核心问题是：

```text
当强 Re-ID 模型给出相似候选后，这个 candidate pair 是否仍然具备可采纳的个体识别证据？
```

## 三目标权重

```text
竞赛/展示价值：40%
科研论文严谨性：35%
真实工具应用价值：25%
```

## 主线

```text
MegaDescriptor/WildFusion-style retrieval
-> PF-ERI pair-level admissibility
-> review action routing
-> wild-to-urban transfer stress
```

Data-governance safeguards around this chain:

```text
laterality-aware sampling/pair audit
background/site leakage-pressure audit
strong-model benchmark contract
```

## 不能越界的结论

- 不声称 bobcat identity accuracy。
- 不声称 urbanization causes Re-ID failure。
- 不声称 PF-ERI 是新 descriptor。
- 不声称生成式增强产生真实身份样本。
- 不把圈养数据变成当前主轴。

## 最强贡献表述

```text
PF-ERI 2.0 判断强 Re-ID 候选 pair 是否在左右侧、背景地点、图像退化和跨环境迁移约束下仍然是可采纳的个体识别证据，并输出可执行的 review action。
```
```

- [ ] **Step 3: Update `PROJECT_RULES.md`**

Append this section after the Phase 15 paragraph:

```markdown
## Phase 16 Balanced Strategy Rule

Phase 16 must balance three goals:

```text
competition-ready communication
paper-defensible validation
practical tool-oriented review routing
```

The active Phase 16 claim is:

```text
PF-ERI 2.0 models whether strong Re-ID candidate pairs contain admissible identity evidence and routes them into risk-controlled review actions under cross-context evidence shift.
```

Phase 16 required safeguards:

These are data-governance and validation safeguards around the PF-ERI model, not the core contribution.

1. Laterality-aware sampling and pair audit: left, right, both, frontal, rear, and unknown should be represented explicitly when labels are available.
2. Background/site leakage pressure diagnostics: candidate similarity must be audited against path/site/date proxies or protected metadata-derived indicators where available. This is a risk-pressure audit, not a causal proof unless stronger evidence is available.
3. Strong-model benchmark preparation: PF-ERI must be evaluated around best-available descriptor or local-matching systems, not only weak baselines.

Urban-vs-wild remains a transfer-stress design axis, not a standalone identity-accuracy claim. Bobcat outputs remain review-readiness and evidence-risk outputs unless verified individual labels or audited same/different pairs exist.
```

- [ ] **Step 4: Update `docs/phase15/README.md`**

Add this line under current interpretation:

```markdown
- Phase 16 is the next PF-ERI modeling phase, with data-governance safeguards for laterality-aware sampling/pair audit, background/site leakage-pressure diagnostics, and strong-model benchmark preparation.
```

- [ ] **Step 5: Verify docs exist**

Run:

```bash
ls docs/phase16 PROJECT_RULES.md docs/phase15/README.md
```

Expected: `docs/phase16/README.md` and `docs/phase16/phase16_balanced_strategy_cn.md` are listed.

- [ ] **Step 6: Commit**

```bash
git add PROJECT_RULES.md docs/phase15/README.md docs/phase16/README.md docs/phase16/phase16_balanced_strategy_cn.md
git commit -m "docs: add phase16 balanced PF-ERI strategy"
```

---

## Task 2: Add Laterality Logic Unit Tests

**Files:**
- Create: `tests/test_phase16_laterality_logic.py`

- [ ] **Step 1: Create unit tests**

Write `tests/test_phase16_laterality_logic.py`:

```python
from scripts.build_phase16_laterality_aware_pair_audit import normalize_laterality, pair_side_relation


def test_normalize_laterality_accepts_known_values():
    assert normalize_laterality("left") == "left"
    assert normalize_laterality("right") == "right"
    assert normalize_laterality("both") == "both"
    assert normalize_laterality("frontal") == "frontal"
    assert normalize_laterality("rear") == "rear"


def test_normalize_laterality_maps_missing_to_unknown():
    assert normalize_laterality("") == "unknown"
    assert normalize_laterality(None) == "unknown"
    assert normalize_laterality(float("nan")) == "unknown"
    assert normalize_laterality("side") == "unknown"


def test_pair_side_relation_same_side():
    assert pair_side_relation("left", "left") == "same_side"
    assert pair_side_relation("right", "right") == "same_side"
    assert pair_side_relation("both", "left") == "same_side_or_both"
    assert pair_side_relation("right", "both") == "same_side_or_both"


def test_pair_side_relation_opposite_and_unknown():
    assert pair_side_relation("left", "right") == "opposite_side"
    assert pair_side_relation("unknown", "right") == "one_or_both_unknown"
    assert pair_side_relation("left", "unknown") == "one_or_both_unknown"


def test_pair_side_relation_non_lateral():
    assert pair_side_relation("frontal", "left") == "non_lateral"
    assert pair_side_relation("rear", "right") == "non_lateral"
    assert pair_side_relation("frontal", "rear") == "non_lateral"
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```bash
pytest tests/test_phase16_laterality_logic.py -q
```

Expected: FAIL with `ModuleNotFoundError` because the implementation script does not exist yet.

- [ ] **Step 3: Commit test**

```bash
git add tests/test_phase16_laterality_logic.py
git commit -m "test: add phase16 laterality logic tests"
```

---

## Task 3: Implement Laterality-Aware Pair Audit

**Files:**
- Create: `scripts/build_phase16_laterality_aware_pair_audit.py`
- Uses: `outputs/phase14/phase14_algorithm_inputs/phase14_2x2_pair_comparability_table.csv`
- Outputs: `outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_table.csv`
- Outputs: `outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_summary.csv`
- Outputs: `outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_audit.json`

- [ ] **Step 1: Write implementation**

Create `scripts/build_phase16_laterality_aware_pair_audit.py`:

```python
#!/usr/bin/env python3
"""Build Phase 16 laterality-aware pair comparability outputs."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs/phase14_2x2_pair_comparability_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/laterality_aware_pair_audit"
OUTPUT_TABLE = OUTPUT_DIR / "phase16_laterality_aware_pair_table.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "phase16_laterality_aware_pair_summary.csv"
OUTPUT_AUDIT = OUTPUT_DIR / "phase16_laterality_aware_pair_audit.json"

KNOWN = {"left", "right", "both", "frontal", "rear", "unknown"}
NON_LATERAL = {"frontal", "rear"}


def normalize_laterality(value: object) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float) and math.isnan(value):
        return "unknown"
    text = str(value).strip().lower()
    if text in KNOWN:
        return text
    return "unknown"


def pair_side_relation(query_side: object, candidate_side: object) -> str:
    q = normalize_laterality(query_side)
    c = normalize_laterality(candidate_side)
    if q == "unknown" or c == "unknown":
        return "one_or_both_unknown"
    if q in NON_LATERAL or c in NON_LATERAL:
        return "non_lateral"
    if q == "both" or c == "both":
        return "same_side_or_both"
    if q == c:
        return "same_side"
    return "opposite_side"


def relation_penalty(relation: str) -> float:
    penalties = {
        "same_side": 0.00,
        "same_side_or_both": 0.03,
        "opposite_side": 0.18,
        "one_or_both_unknown": 0.08,
        "non_lateral": 0.22,
    }
    return penalties[relation]


def build(input_path: Path = DEFAULT_INPUT) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    pairs = pd.read_csv(input_path, low_memory=False)
    pairs["phase16_query_laterality"] = pairs.get("query_side_raw", "unknown").map(normalize_laterality)
    pairs["phase16_candidate_laterality"] = pairs.get("candidate_side_raw", "unknown").map(normalize_laterality)
    pairs["phase16_pair_side_relation"] = [
        pair_side_relation(q, c)
        for q, c in zip(pairs["phase16_query_laterality"], pairs["phase16_candidate_laterality"])
    ]
    pairs["phase16_laterality_penalty"] = pairs["phase16_pair_side_relation"].map(relation_penalty)
    base = pairs["pair_comparability_score"].astype(float)
    pairs["phase16_laterality_adjusted_pair_score"] = (base - pairs["phase16_laterality_penalty"]).clip(0.0, 1.0)
    pairs["phase16_laterality_known_pair"] = ~pairs["phase16_pair_side_relation"].isin(["one_or_both_unknown"])

    summary = (
        pairs.groupby(["environment_axis", "species_axis", "pair_block", "phase16_pair_side_relation"], dropna=False)
        .agg(
            pair_count=("phase14_pair_id", "count"),
            mean_original_pair_score=("pair_comparability_score", "mean"),
            mean_laterality_adjusted_pair_score=("phase16_laterality_adjusted_pair_score", "mean"),
            known_side_rate=("phase16_laterality_known_pair", "mean"),
        )
        .reset_index()
    )

    audit = {
        "input": str(input_path),
        "output_table": str(OUTPUT_TABLE),
        "rows": int(len(pairs)),
        "laterality_relation_counts": {
            str(k): int(v) for k, v in pairs["phase16_pair_side_relation"].value_counts(dropna=False).items()
        },
        "claim_boundary": "laterality adjustment is a reliability diagnostic until audited laterality labels are available",
    }
    return pairs, summary, audit


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs, summary, audit = build()
    pairs.to_csv(OUTPUT_TABLE, index=False)
    summary.to_csv(OUTPUT_SUMMARY, index=False)
    OUTPUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS phase16 laterality-aware pair audit rows={audit['rows']}")
    print(f"WROTE {OUTPUT_TABLE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run unit tests**

```bash
pytest tests/test_phase16_laterality_logic.py -q
```

Expected: PASS.

- [ ] **Step 3: Run builder**

```bash
python3 scripts/build_phase16_laterality_aware_pair_audit.py
```

Expected:

```text
PASS phase16 laterality-aware pair audit rows=120000
WROTE .../outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_table.csv
```

- [ ] **Step 4: Inspect summary**

```bash
python3 -c "import pandas as pd; p='outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_summary.csv'; print(pd.read_csv(p).head(20).to_string())"
```

Expected: summary includes `phase16_pair_side_relation` and counts for unknown/same/opposite/non-lateral categories.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_phase16_laterality_aware_pair_audit.py tests/test_phase16_laterality_logic.py
git commit -m "feat: add phase16 laterality-aware pair audit"
```

---

## Task 4: Build Laterality Audit Candidate Package

**Files:**
- Create: `scripts/build_phase16_laterality_audit_table.py`
- Uses: `outputs/phase14/phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv`
- Outputs: `outputs/phase16/laterality_audit/phase16_laterality_audit_candidates.csv`
- Outputs: `outputs/phase16/laterality_audit/phase16_laterality_schema.json`
- Outputs: `outputs/phase16/laterality_audit/phase16_laterality_audit_summary.json`

- [ ] **Step 1: Write builder**

Create `scripts/build_phase16_laterality_audit_table.py`:

```python
#!/usr/bin/env python3
"""Prepare a deterministic manual laterality audit table for Phase 16."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/laterality_audit"
OUTPUT_CSV = OUTPUT_DIR / "phase16_laterality_audit_candidates.csv"
OUTPUT_SCHEMA = OUTPUT_DIR / "phase16_laterality_schema.json"
OUTPUT_SUMMARY = OUTPUT_DIR / "phase16_laterality_audit_summary.json"
RANDOM_SEED = 1601
SAMPLES_PER_QUADRANT = 150


def select_candidates(df: pd.DataFrame) -> pd.DataFrame:
    eligible = df[df["image_exists"].astype(str).str.lower().eq("yes")].copy()
    groups = []
    for quadrant, group in eligible.groupby("source_quadrant", sort=True):
        n = min(SAMPLES_PER_QUADRANT, len(group))
        sampled = group.sample(n=n, random_state=RANDOM_SEED)
        groups.append(sampled)
    out = pd.concat(groups, ignore_index=True)
    out = out.sort_values(["source_quadrant", "phase14_image_evidence_id"]).reset_index(drop=True)
    out.insert(0, "phase16_laterality_audit_index", range(1, len(out) + 1))
    out["manual_laterality"] = ""
    out["manual_laterality_confidence"] = ""
    out["manual_laterality_notes"] = ""
    keep = [
        "phase16_laterality_audit_index",
        "phase14_image_evidence_id",
        "source_quadrant",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "image_key",
        "image_path",
        "md_area_fraction",
        "human_review_bucket",
        "evidence_admissibility_band",
        "manual_laterality",
        "manual_laterality_confidence",
        "manual_laterality_notes",
    ]
    return out[keep]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT, low_memory=False)
    audit = select_candidates(df)
    audit.to_csv(OUTPUT_CSV, index=False)
    schema = {
        "manual_laterality_allowed_values": ["left", "right", "both", "frontal", "rear", "unknown"],
        "manual_laterality_confidence_allowed_values": ["high", "medium", "low"],
        "rule": "Label visible animal body side, not image-facing direction. Use unknown when side cannot be determined.",
    }
    OUTPUT_SCHEMA.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    summary = {
        "input": str(INPUT),
        "output": str(OUTPUT_CSV),
        "rows": int(len(audit)),
        "samples_per_quadrant_target": SAMPLES_PER_QUADRANT,
        "quadrant_counts": {str(k): int(v) for k, v in audit["source_quadrant"].value_counts().sort_index().items()},
        "claim_boundary": "manual laterality audit package; blank labels are not model output",
    }
    OUTPUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"PASS phase16 laterality audit candidates rows={len(audit)}")
    print(f"WROTE {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run builder**

```bash
python3 scripts/build_phase16_laterality_audit_table.py
```

Expected:

```text
PASS phase16 laterality audit candidates rows=600
WROTE .../outputs/phase16/laterality_audit/phase16_laterality_audit_candidates.csv
```

- [ ] **Step 3: Verify balanced quadrants**

```bash
python3 -c "import json; print(json.load(open('outputs/phase16/laterality_audit/phase16_laterality_audit_summary.json'))['quadrant_counts'])"
```

Expected: four quadrants each have 150 unless a quadrant has fewer eligible images.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_phase16_laterality_audit_table.py
git commit -m "feat: package phase16 laterality audit candidates"
```

---

## Task 5: Add Background/Site Leakage Tests

**Files:**
- Create: `tests/test_phase16_leakage_logic.py`

- [ ] **Step 1: Create tests**

Write `tests/test_phase16_leakage_logic.py`:

```python
from scripts.build_phase16_leakage_pressure_audit import path_site_proxy, same_proxy_group


def test_path_site_proxy_extracts_fcf_prefix():
    path = "/project/data/external/felidae_conservation_fund/images/bobcat_3000/69/2023-03/image.jpg"
    assert path_site_proxy(path) == "fcf:69:2023-03"


def test_path_site_proxy_extracts_czechlynx_identity_parent_safely():
    path = "/project/data/raw/czechlynx/CzechLynx/foe_carpaths/lynx_248/14259_lynx_248.jpg"
    assert path_site_proxy(path) == "czechlynx:foe_carpaths"


def test_path_site_proxy_unknown_for_empty():
    assert path_site_proxy("") == "unknown"
    assert path_site_proxy(None) == "unknown"


def test_same_proxy_group():
    assert same_proxy_group("a", "a") is True
    assert same_proxy_group("a", "b") is False
    assert same_proxy_group("unknown", "unknown") is False
```

- [ ] **Step 2: Run test and confirm failure**

```bash
pytest tests/test_phase16_leakage_logic.py -q
```

Expected: FAIL with `ModuleNotFoundError` because the implementation script does not exist yet.

- [ ] **Step 3: Commit test**

```bash
git add tests/test_phase16_leakage_logic.py
git commit -m "test: add phase16 leakage proxy tests"
```

---

## Task 6: Implement Background/Site Leakage Pressure Audit

**Files:**
- Create: `scripts/build_phase16_leakage_pressure_audit.py`
- Uses: `outputs/phase15/evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv`
- Uses: `outputs/phase15/wild_urban_transfer_stress/phase15e_bobcat_evidence_routed_review_table.csv`
- Outputs: `outputs/phase16/leakage_pressure/phase16_leakage_pressure_pair_audit.csv`
- Outputs: `outputs/phase16/leakage_pressure/phase16_leakage_pressure_summary.csv`
- Outputs: `outputs/phase16/leakage_pressure/phase16_leakage_pressure_audit.json`

- [ ] **Step 1: Write implementation**

Create `scripts/build_phase16_leakage_pressure_audit.py`:

```python
#!/usr/bin/env python3
"""Diagnose path/site proxy leakage pressure in Phase 15 candidate pairs.

This is not a causal background-leakage proof. It estimates whether high
descriptor-similarity pairs are concentrated within available path/site/date
proxies so that later review and validation can treat them as higher-risk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CZECH_INPUT = PROJECT_ROOT / "outputs/phase15/evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv"
BOBCAT_INPUT = PROJECT_ROOT / "outputs/phase15/wild_urban_transfer_stress/phase15e_bobcat_evidence_routed_review_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/leakage_pressure"
OUTPUT_TABLE = OUTPUT_DIR / "phase16_leakage_pressure_pair_audit.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "phase16_leakage_pressure_summary.csv"
OUTPUT_AUDIT = OUTPUT_DIR / "phase16_leakage_pressure_audit.json"


def path_site_proxy(path: object) -> str:
    if path is None:
        return "unknown"
    text = str(path)
    if not text.strip():
        return "unknown"
    parts = Path(text).parts
    if "felidae_conservation_fund" in parts:
        try:
            idx = parts.index("images")
            site = parts[idx + 2]
            date = parts[idx + 3]
            return f"fcf:{site}:{date}"
        except (ValueError, IndexError):
            return "fcf:unknown"
    if "CzechLynx" in parts:
        try:
            idx = parts.index("CzechLynx")
            collection = parts[idx + 1]
            return f"czechlynx:{collection}"
        except (ValueError, IndexError):
            return "czechlynx:unknown"
    return "unknown"


def same_proxy_group(query_proxy: str, candidate_proxy: str) -> bool:
    if query_proxy == "unknown" or candidate_proxy == "unknown":
        return False
    return query_proxy == candidate_proxy


def load_pairs(path: Path, dataset: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df = df.copy()
    df["phase16_dataset"] = dataset
    df["phase16_query_site_proxy"] = df["query_image_path"].map(path_site_proxy)
    df["phase16_candidate_site_proxy"] = df["candidate_image_path"].map(path_site_proxy)
    df["phase16_same_site_proxy"] = [
        same_proxy_group(q, c)
        for q, c in zip(df["phase16_query_site_proxy"], df["phase16_candidate_site_proxy"])
    ]
    df["phase16_high_similarity"] = df["descriptor_similarity"].astype(float) >= df["descriptor_similarity"].astype(float).quantile(0.90)
    df["phase16_site_leakage_pressure"] = df["phase16_same_site_proxy"] & df["phase16_high_similarity"]
    return df


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    czech = load_pairs(CZECH_INPUT, "czechlynx_known_id")
    bobcat = load_pairs(BOBCAT_INPUT, "bobcat_transfer_stress")
    keep_cols = [
        "phase16_dataset",
        "query_image_evidence_id",
        "candidate_image_evidence_id",
        "descriptor_similarity",
        "same_identity",
        "phase16_query_site_proxy",
        "phase16_candidate_site_proxy",
        "phase16_same_site_proxy",
        "phase16_high_similarity",
        "phase16_site_leakage_pressure",
    ]
    for optional in ["phase15d_review_action", "phase15e_review_action", "primary_failure_reason"]:
        if optional in czech.columns or optional in bobcat.columns:
            if optional not in czech.columns:
                czech[optional] = ""
            if optional not in bobcat.columns:
                bobcat[optional] = ""
            keep_cols.append(optional)
    combined = pd.concat([czech[keep_cols], bobcat[keep_cols]], ignore_index=True)
    summary = (
        combined.groupby("phase16_dataset", dropna=False)
        .agg(
            pair_count=("query_image_evidence_id", "count"),
            same_site_proxy_rate=("phase16_same_site_proxy", "mean"),
            high_similarity_rate=("phase16_high_similarity", "mean"),
            site_leakage_pressure_rate=("phase16_site_leakage_pressure", "mean"),
        )
        .reset_index()
    )
    combined.to_csv(OUTPUT_TABLE, index=False)
    summary.to_csv(OUTPUT_SUMMARY, index=False)
    audit = {
        "czech_input": str(CZECH_INPUT),
        "bobcat_input": str(BOBCAT_INPUT),
        "output_table": str(OUTPUT_TABLE),
        "rows": int(len(combined)),
        "claim_boundary": "path-derived site proxies estimate leakage pressure only; this is not causal proof or exact protected location metadata",
    }
    OUTPUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS phase16 background leakage audit rows={len(combined)}")
    print(f"WROTE {OUTPUT_TABLE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_phase16_leakage_logic.py -q
```

Expected: PASS.

- [ ] **Step 3: Run builder**

```bash
python3 scripts/build_phase16_leakage_pressure_audit.py
```

Expected:

```text
PASS phase16 leakage pressure audit rows=600000
WROTE .../outputs/phase16/leakage_pressure/phase16_leakage_pressure_pair_audit.csv
```

- [ ] **Step 4: Inspect leakage summary**

```bash
python3 -c "import pandas as pd; print(pd.read_csv('outputs/phase16/leakage_pressure/phase16_leakage_pressure_summary.csv').to_string(index=False))"
```

Expected: two rows, one for CzechLynx and one for bobcat.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_phase16_leakage_pressure_audit.py tests/test_phase16_leakage_logic.py
git commit -m "feat: add phase16 leakage pressure audit"
```

---

## Task 7: Package Strong-Model Benchmark Inputs

**Files:**
- Create: `scripts/package_phase16_strong_model_benchmark.py`
- Uses: `outputs/phase14/phase14_descriptor_embedding_package/phase14_2x2_descriptor_embedding_manifest.csv`
- Uses: `outputs/phase15/evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv`
- Uses: `outputs/phase15/wild_urban_transfer_stress/phase15e_bobcat_evidence_routed_review_table.csv`
- Outputs: `outputs/phase16/strong_model_benchmark/phase16_strong_model_benchmark_manifest.csv`
- Outputs: `outputs/phase16/strong_model_benchmark/phase16_strong_model_pair_contract.csv`
- Outputs: `outputs/phase16/strong_model_benchmark/README.md`

- [ ] **Step 1: Write packaging script**

Create `scripts/package_phase16_strong_model_benchmark.py`:

```python
#!/usr/bin/env python3
"""Package image and pair manifests for external strong-model benchmarking."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_INPUT = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_package/phase14_2x2_descriptor_embedding_manifest.csv"
CZECH_PAIRS = PROJECT_ROOT / "outputs/phase15/evidence_routed_review_policy/phase15d_evidence_routed_review_table.csv"
BOBCAT_PAIRS = PROJECT_ROOT / "outputs/phase15/wild_urban_transfer_stress/phase15e_bobcat_evidence_routed_review_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/strong_model_benchmark"
IMAGE_OUTPUT = OUTPUT_DIR / "phase16_strong_model_benchmark_manifest.csv"
PAIR_OUTPUT = OUTPUT_DIR / "phase16_strong_model_pair_contract.csv"
README = OUTPUT_DIR / "README.md"
AUDIT = OUTPUT_DIR / "phase16_strong_model_benchmark_audit.json"
MAX_PAIRS_PER_DATASET = 50000


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    images = pd.read_csv(IMAGE_INPUT, low_memory=False)
    image_cols = [c for c in ["phase14_image_evidence_id", "image_path", "source_quadrant", "environment_axis", "species_axis", "evidence_axis"] if c in images.columns]
    images[image_cols].drop_duplicates().to_csv(IMAGE_OUTPUT, index=False)

    pair_frames = []
    for dataset, path in [("czechlynx_known_id", CZECH_PAIRS), ("bobcat_transfer_stress", BOBCAT_PAIRS)]:
        pairs = pd.read_csv(path, low_memory=False)
        pairs = pairs.sort_values("descriptor_similarity", ascending=False).head(MAX_PAIRS_PER_DATASET).copy()
        pairs["phase16_dataset"] = dataset
        keep = [
            "phase16_dataset",
            "query_image_evidence_id",
            "candidate_image_evidence_id",
            "query_image_path",
            "candidate_image_path",
            "descriptor_similarity",
            "same_identity",
            "primary_failure_reason",
        ]
        for col in keep:
            if col not in pairs.columns:
                pairs[col] = ""
        pair_frames.append(pairs[keep])
    pair_contract = pd.concat(pair_frames, ignore_index=True)
    pair_contract.to_csv(PAIR_OUTPUT, index=False)

    README.write_text(
        "# Phase 16 Strong-Model Benchmark Package\n\n"
        "Purpose: provide a stable image and pair contract for WildFusion, local feature matching, or another strong animal Re-ID benchmark.\n\n"
        "Required return columns for pair-level benchmark output:\n\n"
        "```text\n"
        "phase16_dataset\nquery_image_evidence_id\ncandidate_image_evidence_id\nstrong_model_name\nstrong_model_score\nstrong_model_rank\nstrong_model_notes\n"
        "```\n\n"
        "Claim boundary: this package prepares a benchmark interface. It does not itself validate identity.\n",
        encoding="utf-8",
    )
    audit = {
        "image_rows": int(len(images)),
        "pair_rows": int(len(pair_contract)),
        "image_output": str(IMAGE_OUTPUT),
        "pair_output": str(PAIR_OUTPUT),
        "claim_boundary": "strong-model package only; final claims require returned strong-model scores",
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS phase16 strong-model benchmark package image_rows={len(images)} pair_rows={len(pair_contract)}")
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run packaging script**

```bash
python3 scripts/package_phase16_strong_model_benchmark.py
```

Expected:

```text
PASS phase16 strong-model benchmark package image_rows=12000 pair_rows=100000
WROTE .../outputs/phase16/strong_model_benchmark
```

- [ ] **Step 3: Verify contract columns**

```bash
python3 -c "import pandas as pd; print(pd.read_csv('outputs/phase16/strong_model_benchmark/phase16_strong_model_pair_contract.csv', nrows=1).columns.tolist())"
```

Expected: includes `phase16_dataset`, `query_image_evidence_id`, `candidate_image_evidence_id`, and `descriptor_similarity`.

- [ ] **Step 4: Commit**

```bash
git add scripts/package_phase16_strong_model_benchmark.py
git commit -m "feat: package phase16 strong-model benchmark inputs"
```

---

## Task 8: Create Seven-Dimension Literature Gap Matrix

**Files:**
- Create: `docs/phase16/phase16_literature_gap_matrix.md`

- [ ] **Step 1: Write the matrix document**

Create `docs/phase16/phase16_literature_gap_matrix.md`:

```markdown
# Phase 16 Literature Gap Matrix

## Purpose

This document maps seven advisor-suggested dimensions to the PF-ERI project. Each dimension is classified as model core, data safeguard, benchmark safeguard, mechanism extension, robustness extension, or deferred.

## Decision Matrix

| Dimension | What others do | Remaining gap | Project role | Decision |
|---|---|---|---|---|
| Generative algorithms | Re-ID augmentation, style transfer, diffusion synthesis | Evidence-preservation risk is under-tested for animal patterns | Robustness stress only | Extension |
| Left/right balance | Photo-ID and spatial capture-recapture recognize side-specific identity evidence | Strong Re-ID outputs rarely expose side-admissibility actions | Sampling and pair-comparability audit | Data safeguard |
| Blur/data augmentation | Common accuracy and robustness enhancement | Enhancement may alter admissible pattern evidence | Evidence-preservation ablation | Extension |
| Captive dimension | High-quality controlled animal imagery exists | Captive-to-wild evidence transfer can be confounded by enclosure backgrounds | Calibration ceiling | Deferred |
| Same-site different individuals | Camera-trap models can use background/site context | Re-ID similarity can reflect background leakage | Leakage-pressure audit | Data diagnostic safeguard |
| Activity range and context | Ecological models use space/time/home range | CV Re-ID rarely separates visual evidence from ecological prior | Optional plausibility prior | Mechanism |
| Strong external models | MegaDescriptor, WildFusion, Wildbook/IBEIS retrieve strong candidates | They do not fully answer admissible-evidence review action | Benchmark substrate for PF-ERI | Benchmark safeguard |

## Main Gap Statement

Current animal Re-ID systems can retrieve visually similar candidates, but they rarely provide a calibrated answer to whether the candidate pair is admissible identity evidence and what risk-controlled review action should follow. Laterality mismatch, possible background/site leakage pressure, image degradation, cross-context transfer, and review-budget constraints are evaluation conditions around that core problem.

## Integration Rule

Phase 16 should not add all seven dimensions equally. The main line remains PF-ERI modeling: pair-level evidence utility, descriptor-evidence conflict, calibrated review routing, and risk-controlled evaluation. The first implementation layer should add three data-governance safeguards around that model: laterality-aware sampling/pair audit, background/site leakage-pressure audit, and strong-model benchmark preparation. Ecological plausibility becomes Phase 16B. Generative augmentation and captive imagery remain controlled extensions.
```

- [ ] **Step 2: Check no overclaim language**

Run:

```bash
rg -n "bobcat.*accuracy|urbanization causes|new descriptor|automatic identity" docs/phase16/phase16_literature_gap_matrix.md
```

Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add docs/phase16/phase16_literature_gap_matrix.md
git commit -m "docs: map phase16 literature gaps to PF-ERI"
```

---

## Task 9: Build Integrated Phase 16 Strategy Report

**Files:**
- Create: `scripts/build_phase16_integrated_strategy_report.py`
- Uses: outputs from Tasks 3, 6, 7
- Outputs: `outputs/phase16/integrated_report/phase16_integrated_strategy_report.md`
- Outputs: `outputs/phase16/integrated_report/phase16_integrated_strategy_summary.json`

- [ ] **Step 1: Write report builder**

Create `scripts/build_phase16_integrated_strategy_report.py`:

```python
#!/usr/bin/env python3
"""Build an integrated Phase 16 strategy report from generated outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAT_SUMMARY = PROJECT_ROOT / "outputs/phase16/laterality_aware_pair_audit/phase16_laterality_aware_pair_summary.csv"
LEAK_SUMMARY = PROJECT_ROOT / "outputs/phase16/leakage_pressure/phase16_leakage_pressure_summary.csv"
STRONG_AUDIT = PROJECT_ROOT / "outputs/phase16/strong_model_benchmark/phase16_strong_model_benchmark_audit.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/integrated_report"
OUTPUT_MD = OUTPUT_DIR / "phase16_integrated_strategy_report.md"
OUTPUT_JSON = OUTPUT_DIR / "phase16_integrated_strategy_summary.json"


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "No rows."
    return df.head(max_rows).to_markdown(index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    laterality = pd.read_csv(LAT_SUMMARY)
    leakage = pd.read_csv(LEAK_SUMMARY)
    strong = json.loads(STRONG_AUDIT.read_text(encoding="utf-8"))

    report = f"""# Phase 16 Integrated Strategy Report

## Executive Summary

Phase 16 upgrades PF-ERI into a balanced competition/paper/tool strategy by keeping the model as the center and adding three safeguards around it:

1. laterality-aware sampling and pair audit;
2. background/site leakage pressure diagnostics;
3. strong-model benchmark preparation.

## Claim Boundary

CzechLynx remains the known-ID validation carrier. Bobcat remains an urban/peri-urban transfer-stress and review-readiness context unless verified individual IDs or audited same/different pair labels are available.

## Laterality Summary

{markdown_table(laterality)}

## Background/Site Leakage Summary

{markdown_table(leakage)}

## Strong-Model Benchmark Package

```json
{json.dumps(strong, indent=2)}
```

## Strategic Interpretation

The project should keep urban-vs-wild as the transfer-stress design axis, not as a standalone identity-accuracy claim. The central scientific contribution is pair-level admissible-evidence routing after strong Re-ID retrieval.

## Next Decision Gate

Do not make final Phase 16 scientific claims until either manual laterality audit labels or a documented laterality classifier are available for enough samples to separate known-side and unknown-side results.
"""
    OUTPUT_MD.write_text(report, encoding="utf-8")
    summary = {
        "laterality_summary_rows": int(len(laterality)),
        "leakage_summary_rows": int(len(leakage)),
        "strong_model_pair_rows": int(strong["pair_rows"]),
        "claim_boundary": "integrated strategy report; not final paper claims",
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"PASS phase16 integrated strategy report wrote={OUTPUT_MD}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run report builder**

```bash
python3 scripts/build_phase16_integrated_strategy_report.py
```

Expected:

```text
PASS phase16 integrated strategy report wrote=.../outputs/phase16/integrated_report/phase16_integrated_strategy_report.md
```

- [ ] **Step 3: Inspect first 80 lines**

```bash
sed -n '1,80p' outputs/phase16/integrated_report/phase16_integrated_strategy_report.md
```

Expected: contains executive summary, claim boundary, laterality summary, leakage summary, and strong-model audit JSON.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_phase16_integrated_strategy_report.py
git commit -m "feat: build phase16 integrated strategy report"
```

---

## Task 10: Final Verification Gate

**Files:**
- Uses all Phase 16 scripts and docs.

- [ ] **Step 1: Run all Phase 16 unit tests**

```bash
pytest tests/test_phase16_laterality_logic.py tests/test_phase16_leakage_logic.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run all Phase 16 builders**

```bash
python3 scripts/build_phase16_laterality_audit_table.py
python3 scripts/build_phase16_laterality_aware_pair_audit.py
python3 scripts/build_phase16_leakage_pressure_audit.py
python3 scripts/package_phase16_strong_model_benchmark.py
python3 scripts/build_phase16_integrated_strategy_report.py
```

Expected: each script prints `PASS`.

- [ ] **Step 3: Run claim-risk scan**

```bash
rg -n "bobcat.*accuracy|urbanization causes|new descriptor|automatic identity|population estimation" PROJECT_RULES.md docs/phase16 scripts/build_phase16_*.py scripts/package_phase16_strong_model_benchmark.py
```

Expected: any matches are negative claim-boundary statements only.

- [ ] **Step 4: Confirm generated outputs exist**

```bash
ls outputs/phase16/laterality_audit outputs/phase16/laterality_aware_pair_audit outputs/phase16/leakage_pressure outputs/phase16/strong_model_benchmark outputs/phase16/integrated_report
```

Expected: all five output directories exist and contain CSV/JSON/Markdown outputs.

- [ ] **Step 5: Review git status**

```bash
git status --short
```

Expected: only intended docs, scripts, and tests are tracked or staged. `outputs/` remains untracked/ignored and should not be committed.

- [ ] **Step 6: Final commit if needed**

```bash
git add PROJECT_RULES.md docs/phase15/README.md docs/phase16 scripts/build_phase16_laterality_audit_table.py scripts/build_phase16_laterality_aware_pair_audit.py scripts/build_phase16_leakage_pressure_audit.py scripts/package_phase16_strong_model_benchmark.py scripts/build_phase16_integrated_strategy_report.py tests/test_phase16_laterality_logic.py tests/test_phase16_leakage_logic.py
git commit -m "feat: add phase16 balanced PF-ERI strategy workflow"
```

Expected: commit succeeds. If earlier task commits were already made, this final commit may report nothing to commit.

---

## Execution Order

Implement in this order:

1. Task 1: Strategy boundaries.
2. Task 2: Laterality tests.
3. Task 3: Laterality pair table.
4. Task 4: Laterality manual audit package.
5. Task 5: Leakage tests.
6. Task 6: Background/site leakage audit.
7. Task 7: Strong-model benchmark package.
8. Task 8: Literature gap matrix.
9. Task 9: Integrated report.
10. Task 10: Final verification gate.

Do not start optional generative augmentation, captive data, or ecological prior modeling until the Phase 16A data-governance gates pass.

---

## Self-Review

Spec coverage:

- Competition-ready narrative: Task 1 and Task 8.
- Paper-defensible safeguards: Tasks 2, 3, 5, 6, and 10.
- Tool-oriented benchmark interface: Task 7.
- Integrated reporting: Task 9.
- Claim-boundary protection: Tasks 1, 8, 9, and 10.

Placeholder scan:

- No placeholder markers or undefined file paths remain.
- Optional future work is explicitly excluded from Phase 16A rather than left incomplete.

Type consistency:

- Laterality values are consistently `left`, `right`, `both`, `frontal`, `rear`, `unknown`.
- Pair-side relation values are consistently `same_side`, `same_side_or_both`, `opposite_side`, `one_or_both_unknown`, `non_lateral`.
- Leakage proxy fields consistently use the `phase16_` prefix.
