# Project Triage And legacy-code18 Execution Issues

Date: 2026-07-01

## Triage Result

The repository has many legacy-code16/17 output directories because image-entry
selection was iterated through multiple strictness levels. That history should
remain available for provenance, but it should not be the algorithm entry point.

The active entry point is now:

```text
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv
```

## CodeGraph Repair

CodeGraph is kept as a code-structure tool. The project now has a contract
check script:

```text
scripts/check_codegraph_project_contract.py
```

It verifies `.codegraph/`, `codegraph status`, and the exact-path docs/scripts
that define the current project. Broad CodeGraph retrieval misses must not
override CSV/JSON audits or project rules.

## Structure Repair

Historical legacy-code16/17 directories are consolidated through a non-destructive
index:

```text
scripts/build_project_artifact_consolidation_index.py
outputs/project_structure/artifact_consolidation_index/
```

This keeps provenance but tells legacy-code18 to use the freeze manifest.

## legacy-code18 Vertical Slices

1. **legacy-code18a frozen image feature manifest**
   - Blocked by: none.
   - User stories covered: as a model builder, I can start from one verified
     frozen image table with hashes, dimensions, roles, and identity boundary.

2. **legacy-code18b strong descriptor embedding extraction**
   - Blocked by: legacy-code18a.
   - User stories covered: as a model builder, I can run MegaDescriptor and at
     least one strong foundation baseline without changing the frozen image set.
   - Current implementation: local descriptor-control baseline in
     `scripts/build_legacy-code18b_local_descriptor_control.py`, because the current
     runtime has no `torch`/`timm`.

3. **legacy-code18c CzechLynx known-ID pair contract**
   - Blocked by: legacy-code18a and legacy-code18b.
   - User stories covered: as an evaluator, I can form same/different candidate
     pairs with identity labels and leakage-aware split fields.
   - Current implementation: `scripts/build_legacy-code18c_czechlynx_pair_contract.py`.

4. **legacy-code18d PF-ERI 2.0 pair feature table**
   - Blocked by: legacy-code18c.
   - User stories covered: as a reviewer, I can inspect whether each pair is
     admissible, comparable, conflicting, or risky, not merely descriptor-similar.
   - Current implementation: `scripts/build_legacy-code18d_pf_eri_pair_features.py`.

5. **legacy-code18e calibrated review router**
   - Blocked by: legacy-code18d.
   - User stories covered: as a scientist, I can evaluate review utility under
     fixed retention, fixed review budget, abstention, and calibration metrics.
   - Current implementation: `scripts/build_legacy-code18e_review_router.py`.

6. **legacy-code18f Bobcat transfer-stress/readiness application**
   - Blocked by: legacy-code18d and preferably legacy-code18e.
   - User stories covered: as a field user, I can route Bobcat candidate
     evidence by readiness without claiming unlabeled identity accuracy.
   - Current implementation: `scripts/build_legacy-code18f_bobcat_transfer_readiness.py`.

7. **legacy-code18 all-step automation**
   - Blocked by: legacy-code18a-G scripts.
   - User stories covered: as a maintainer, I can run one command and regenerate
     the whole local-control legacy-code18 chain plus claim gate in dependency order.
   - Current implementation: `scripts/run_legacy-code18_all.py`.

8. **legacy-code18g strong-baseline claim gate**
   - Blocked by: legacy-code18a and the current legacy-code18b local-control audit.
   - User stories covered: as a scientist, I cannot accidentally treat the local
     descriptor-control run as a final strong-baseline comparison.
   - Current implementation: `scripts/build_legacy-code18g_strong_baseline_claim_gate.py`.

## Confidence Loop

The strategy is high-confidence only under these repairs:

- strong descriptors are treated as baselines, not straw men;
- Bobcat is not used for identity accuracy until labels or audited pairs exist;
- pair-level modeling is the main mechanism because Re-ID errors occur at the
  comparison/candidate-pair layer;
- every phase output has an audit file and a claim-boundary note.

## Current Automated Run

`scripts/run_legacy-code18_all.py` has executed legacy-code18a-F with status
`PASS`.

Important counts:

- legacy-code18b: 6,000 rows, 822-dimensional local descriptor-control embeddings.
- legacy-code18c: 3,000 CzechLynx known-ID images, 235 identities, 60,000 pair rows.
- legacy-code18d: 60,000 PF-ERI pair-feature rows.
- legacy-code18e: 5 local-control router policies, 10 metric rows.
- legacy-code18f: 3,000 Bobcat unlabeled images, 30,000 transfer-readiness pair rows.
- legacy-code18g: strong-baseline handoff and claim gate; current gate is expected to
  be `BLOCKED_STRONG_BASELINE_NOT_RUN` until strong embeddings/scores are
  supplied.

Claim boundary:

- These outputs prove the legacy-code18 pipeline contract runs end-to-end.
- They do not prove PF-ERI beats MegaDescriptor, WildFusion, or any strong
  descriptor baseline.
