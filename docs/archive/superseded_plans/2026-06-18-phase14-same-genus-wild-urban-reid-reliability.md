# Phase 14 Same-Genus Wild-Urban Re-ID Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 14 implementation layer that tests PF-ERI as a same-genus wild-to-urban Lynx evidence reliability model, organized as image-level evidence shift, pair-level comparability shift, and retrieval/review contamination.

**Architecture:** Keep CzechLynx as the known-ID validation carrier and add UWIN/FCF bobcat as urban or peri-urban same-genus stress contexts. The pipeline should first audit available bobcat inputs, then build a shared image-level evidence schema, quantify evidence-risk distribution shift, build pair-level comparability and descriptor-evidence conflict tables, create a small audited pair protocol if feasible, and transfer a conservative accept/review/defer/species-level-only policy.

**Core chain:**

```text
image-level evidence shift -> pair-level comparability shift -> retrieval/review contamination
```

**Claim boundary:** CzechLynx known-ID pairs can validate false-candidate risk and positive retention. Urban bobcat pairs without verified IDs can support comparability, conflict, review-readiness, and contamination-pressure claims only.

**Tech Stack:** Python scripts, pandas-compatible CSV tables, deterministic sampling, existing PF-ERI outputs under `data/` and `outputs/`, Markdown documentation, PASS/FAIL audit summaries.

---

## File Structure

- Create: `scripts/audit_phase14_uwin_bobcat_inventory.py`
  - Reads local UWIN bobcat metadata paths once confirmed.
  - Reports counts, available fields, privacy-sensitive fields, and whether individual labels or pair-audit labels exist.
- Create: `scripts/build_phase14_cross_context_evidence_table.py`
  - Builds a shared feature table with CzechLynx and UWIN bobcat rows using only fields that are comparable or explicitly marked context-specific.
- Create: `scripts/analyze_phase14_cross_context_shift.py`
  - Computes standardized mean differences, distribution distances, domain-classifier separability, and bootstrap intervals.
- Create: `scripts/build_phase14_pair_comparability_shift_table.py`
  - Builds wild known-ID and urban stress-test pair tables with pair PF-ERI, weakest-image evidence, descriptor similarity, and descriptor-evidence conflict fields.
- Create: `scripts/analyze_phase14_pair_comparability_shift.py`
  - Compares pair-level comparability and high-similarity low-admissibility conflict structure across wild and urban contexts without claiming urban false-match accuracy unless identity labels exist.
- Create: `scripts/prepare_phase14_uwin_pair_audit_manifest.py`
  - Samples a small UWIN bobcat pair-audit manifest across descriptor/PF-ERI conflict strata.
- Create: `scripts/analyze_phase14_uwin_pair_audit.py`
  - Evaluates PF-ERI, descriptor similarity, and quality-only signals against human labels once available.
- Create: `scripts/apply_phase14_review_readiness_policy.py`
  - Applies CzechLynx-calibrated PF-ERI thresholds to UWIN bobcat images/pairs and estimates accept/review/defer/species-level-only proportions.
- Create: `docs/phase14/phase14_implementation_status.md`
  - Tracks what has been implemented, what data are missing, and which claims are currently allowed.
- Modify: `docs/README.md`
  - Keep Phase 14 as active roadmap and point to the implementation status file after scripts exist.
- Modify: `README.md`
  - Update current pending status after each Phase 14 module completes.
- Modify: `PROJECT_RULES.md`
  - Only update if a new hard scientific rule or safety boundary is discovered.

## Task 1: UWIN Bobcat Data Inventory

**Files:**
- Create: `scripts/audit_phase14_uwin_bobcat_inventory.py`
- Create: `docs/phase14/phase14_implementation_status.md`

- [ ] **Step 1: Locate candidate UWIN bobcat inputs**

Run a non-destructive file inventory over `data/` and `sources/`.

Expected result:

```text
List candidate CSV/metadata/image-manifest files.
Do not open or copy raw images.
Do not expose sensitive site/trap coordinates in public docs.
```

- [ ] **Step 2: Write the inventory audit script**

The script should:

```python
import argparse
from pathlib import Path
import pandas as pd

SENSITIVE_HINTS = {
    "lat", "latitude", "lon", "longitude", "site", "trap", "camera",
    "cell", "location", "coordinate", "utm"
}

def summarize_csv(path: Path) -> dict:
    df = pd.read_csv(path, nrows=5000)
    columns = list(df.columns)
    lower_columns = [c.lower() for c in columns]
    sensitive = [
        c for c, lc in zip(columns, lower_columns)
        if any(token in lc for token in SENSITIVE_HINTS)
    ]
    identity_like = [
        c for c, lc in zip(columns, lower_columns)
        if "individual" in lc or lc in {"id", "animal_id", "identity"}
    ]
    bobcat_like = [
        c for c, lc in zip(columns, lower_columns)
        if "bobcat" in lc or "lynx rufus" in lc
    ]
    return {
        "path": str(path),
        "rows_sampled": len(df),
        "columns": columns,
        "sensitive_columns": sensitive,
        "identity_like_columns": identity_like,
        "bobcat_like_columns": bobcat_like,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="data")
    parser.add_argument("--output", default="outputs/phase14/uwin_bobcat_inventory.csv")
    args = parser.parse_args()

    rows = []
    for path in Path(args.root).rglob("*.csv"):
        if "bobcat" in path.name.lower() or "uwin" in str(path).lower():
            try:
                summary = summarize_csv(path)
                rows.append({
                    "path": summary["path"],
                    "rows_sampled": summary["rows_sampled"],
                    "n_columns": len(summary["columns"]),
                    "sensitive_columns": "|".join(summary["sensitive_columns"]),
                    "identity_like_columns": "|".join(summary["identity_like_columns"]),
                    "bobcat_like_columns": "|".join(summary["bobcat_like_columns"]),
                })
            except Exception as exc:
                rows.append({"path": str(path), "error": repr(exc)})

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"PASS phase14 UWIN inventory rows={len(rows)} output={out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the inventory audit**

Run:

```bash
python scripts/audit_phase14_uwin_bobcat_inventory.py --root data
```

Expected:

```text
PASS phase14 UWIN inventory rows=<n> output=outputs/phase14/uwin_bobcat_inventory.csv
```

- [ ] **Step 4: Record claim boundary**

Update `docs/phase14/phase14_implementation_status.md` with:

```markdown
# Phase 14 Implementation Status

Date: 2026-06-18

## Current Claim Boundary

Phase 14 can only claim UWIN bobcat field-readiness or review-readiness until individual labels or human-audited pair labels are verified.

## Inventory Status

- UWIN bobcat metadata files found: <count>
- Verified individual labels: yes/no/unknown
- Human pair-audit labels: yes/no/unknown
- Sensitive fields present: yes/no
- Public reporting rule: never expose exact site, trap, coordinate, or internal path fields.
```

## Task 2: Shared Cross-Context Evidence Table

**Files:**
- Create: `scripts/build_phase14_cross_context_evidence_table.py`
- Modify: `docs/phase14/phase14_implementation_status.md`

- [ ] **Step 1: Define the shared schema**

Required columns:

```text
row_id
context
species
source_dataset
image_key_blinded
has_identity_label
identity_label_available_for_validation
pf_eri_image_score
pattern_visibility
side_flank_visibility
body_visibility
blur_level
occlusion_level
night_ir
background_complexity
human_modified_background
descriptor_confidence
descriptor_evidence_conflict
feature_available_flags
```

- [ ] **Step 2: Build the table script**

The script must:

```text
accept CzechLynx PF-ERI image-level table path
accept optional UWIN bobcat metadata/annotation path
emit one harmonized CSV
mark missing fields as unavailable, not zero
avoid sensitive path/location fields
```

- [ ] **Step 3: Run table build**

Run:

```bash
python scripts/build_phase14_cross_context_evidence_table.py
```

Expected:

```text
PASS phase14 cross-context evidence table rows=<n> contexts=<CzechLynx,UWIN_bobcat>
```

- [ ] **Step 4: Audit table safety**

Confirm:

```text
No raw image path.
No exact trap/site/coordinate.
No original CzechLynx unique_name.
Context labels are present.
Missing UWIN features are explicitly flagged.
```

## Task 3: Evidence-Risk Distribution Shift Analysis

**Files:**
- Create: `scripts/analyze_phase14_cross_context_shift.py`
- Modify: `docs/phase14/phase14_implementation_status.md`

- [ ] **Step 1: Implement shift metrics**

Compute for every numeric shared feature:

```text
mean by context
standardized mean difference
Kolmogorov-Smirnov statistic
Wasserstein distance
bootstrap confidence interval for mean difference
```

- [ ] **Step 2: Add domain-classifier separability**

Use a simple regularized classifier only as a diagnostic:

```text
input: shared evidence features
target: CzechLynx vs UWIN_bobcat
output: cross-validated AUC
interpretation: how separable the evidence context is, not causality
```

- [ ] **Step 3: Run shift analysis**

Run:

```bash
python scripts/analyze_phase14_cross_context_shift.py
```

Expected:

```text
PASS phase14 cross-context shift features=<n> domain_auc=<value>
```

- [ ] **Step 4: Report allowed interpretation**

Write in `docs/phase14/phase14_implementation_status.md`:

```markdown
## Cross-Context Shift Status

The shift analysis tests whether UWIN bobcat has a different evidence-risk distribution from CzechLynx. It does not prove urbanization causes Re-ID failure.
```

## Task 4: Small UWIN Bobcat Pair-Audit Manifest

**Files:**
- Create: `scripts/prepare_phase14_uwin_pair_audit_manifest.py`
- Modify: `docs/phase14/phase14_implementation_status.md`

- [ ] **Step 1: Define pair strata**

Sample from:

```text
high descriptor / high PF-ERI
high descriptor / low PF-ERI
low descriptor / high PF-ERI
low descriptor / low PF-ERI
random matched controls
non-comparable candidates
```

- [ ] **Step 2: Define label schema**

Human labels:

```text
same
different
uncertain
non_comparable
```

Secondary fields:

```text
side_comparable
pattern_comparable
major_occlusion
major_blur
review_confidence
review_notes
```

- [ ] **Step 3: Build blinded manifest**

The manifest must include blinded image keys and audit fields only. It must not include:

```text
raw paths
site/trap/coordinate fields
descriptor similarity
PF-ERI score
predicted policy label
```

- [ ] **Step 4: Run manifest audit**

Expected:

```text
PASS phase14 UWIN pair audit manifest pairs=<n> strata=<k>
```

## Task 5: UWIN Pair-Audit Evaluation

**Files:**
- Create: `scripts/analyze_phase14_uwin_pair_audit.py`
- Modify: `docs/phase14/phase14_implementation_status.md`

- [ ] **Step 1: Wait for audited labels**

Do not run this task until a human-audited label CSV exists.

- [ ] **Step 2: Implement evaluation**

Compare:

```text
PF-ERI score
descriptor similarity
quality-only score
descriptor-evidence conflict score
```

Outcomes:

```text
confident comparable = same or different with sufficient confidence
uncertain_or_non_comparable = uncertain or non_comparable
```

- [ ] **Step 3: Report statistics**

Required outputs:

```text
AUC or average precision for uncertain/non-comparable prediction
conflict enrichment among uncertain/non-comparable pairs
bootstrap confidence intervals
confusion table by policy bucket
```

- [ ] **Step 4: Enforce claim boundary**

If labels are pair-comparability labels only, report review-readiness validation only. Do not claim full UWIN individual Re-ID validation.

## Task 6: Review-Readiness Policy Transfer

**Files:**
- Create: `scripts/apply_phase14_review_readiness_policy.py`
- Modify: `docs/phase14/phase14_implementation_status.md`

- [ ] **Step 1: Define conservative policy buckets**

Policy output:

```text
accept
review
defer
species_level_only
non_comparable
```

- [ ] **Step 2: Calibrate on CzechLynx only**

Thresholds or model weights must be chosen using CzechLynx calibration data only.

- [ ] **Step 3: Apply to UWIN bobcat**

Report:

```text
policy proportions
bootstrap intervals
dominant failure reasons
review-load estimate
```

- [ ] **Step 4: Compare against controls**

Controls:

```text
quality-only policy
descriptor-only policy
random same-coverage policy
```

Expected interpretation:

```text
PF-ERI is useful if it gives a clearer risk/review allocation than descriptor-only or quality-only policies, especially for high-similarity low-admissibility conflicts.
```

## Task 7: Documentation and Cleanup

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_RULES.md` only if needed
- Modify: `docs/README.md`
- Modify: `docs/phase14/phase14_implementation_status.md`

- [ ] **Step 1: Update read order**

Make sure `docs/README.md` points to:

```text
phase14 plan
phase14 implementation status
phase13 failure diagnosis as diagnostic background
phase12 roadmap as superseded foundation
```

- [ ] **Step 2: Remove misleading active-language**

Search for:

```text
active roadmap
current metric-learning
current main contribution
Metric Learning Enhancement
```

Expected:

```text
Only historical or diagnostic references remain.
```

- [ ] **Step 3: Summarize completed outputs**

Update `README.md` with the latest Phase 14 status after tasks finish.

- [ ] **Step 4: Verify repository safety**

Confirm no new raw data, raw images, contact sheets, or local outputs are staged for commit.

## Self-Review Checklist

- [ ] Phase 14 is the first active implementation direction.
- [ ] Phase 13D/RQ4 metric learning is marked diagnostic/optional.
- [ ] UWIN bobcat is not described as verified identity validation unless labels exist.
- [ ] Urban context is treated as a stress context, not a causal urbanization claim.
- [ ] CzechLynx remains the known-ID validation carrier.
- [ ] Every output has descriptor-only, quality-only, and random/matched controls where applicable.
- [ ] No sensitive UWIN or CzechLynx path/location fields are exposed in public docs.
