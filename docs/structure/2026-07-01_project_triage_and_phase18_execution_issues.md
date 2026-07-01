# Project Triage And Phase18 Execution Issues

Date: 2026-07-01

## Triage Result

The repository has many Phase16/17 output directories because image-entry
selection was iterated through multiple strictness levels. That history should
remain available for provenance, but it should not be the algorithm entry point.

The active entry point is now:

```text
outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv
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

Historical Phase16/17 directories are consolidated through a non-destructive
index:

```text
scripts/build_project_artifact_consolidation_index.py
outputs/project_structure/artifact_consolidation_index/
```

This keeps provenance but tells Phase18 to use the freeze manifest.

## Phase18 Vertical Slices

1. **Phase18A frozen image feature manifest**
   - Blocked by: none.
   - User stories covered: as a model builder, I can start from one verified
     frozen image table with hashes, dimensions, roles, and identity boundary.

2. **Phase18B strong descriptor embedding extraction**
   - Blocked by: Phase18A.
   - User stories covered: as a model builder, I can run MegaDescriptor and at
     least one strong foundation baseline without changing the frozen image set.
   - Current implementation: local descriptor-control baseline in
     `scripts/build_phase18b_local_descriptor_control.py`, because the current
     runtime has no `torch`/`timm`.

3. **Phase18C CzechLynx known-ID pair contract**
   - Blocked by: Phase18A and Phase18B.
   - User stories covered: as an evaluator, I can form same/different candidate
     pairs with identity labels and leakage-aware split fields.
   - Current implementation: `scripts/build_phase18c_czechlynx_pair_contract.py`.

4. **Phase18D PF-ERI 2.0 pair feature table**
   - Blocked by: Phase18C.
   - User stories covered: as a reviewer, I can inspect whether each pair is
     admissible, comparable, conflicting, or risky, not merely descriptor-similar.
   - Current implementation: `scripts/build_phase18d_pf_eri_pair_features.py`.

5. **Phase18E calibrated review router**
   - Blocked by: Phase18D.
   - User stories covered: as a scientist, I can evaluate review utility under
     fixed retention, fixed review budget, abstention, and calibration metrics.
   - Current implementation: `scripts/build_phase18e_review_router.py`.

6. **Phase18F Bobcat transfer-stress/readiness application**
   - Blocked by: Phase18D and preferably Phase18E.
   - User stories covered: as a field user, I can route Bobcat candidate
     evidence by readiness without claiming unlabeled identity accuracy.
   - Current implementation: `scripts/build_phase18f_bobcat_transfer_readiness.py`.

7. **Phase18 all-step automation**
   - Blocked by: Phase18A-G scripts.
   - User stories covered: as a maintainer, I can run one command and regenerate
     the whole local-control Phase18 chain plus claim gate in dependency order.
   - Current implementation: `scripts/run_phase18_all.py`.

8. **Phase18G strong-baseline claim gate**
   - Blocked by: Phase18A and the current Phase18B local-control audit.
   - User stories covered: as a scientist, I cannot accidentally treat the local
     descriptor-control run as a final strong-baseline comparison.
   - Current implementation: `scripts/build_phase18g_strong_baseline_claim_gate.py`.

## Confidence Loop

The strategy is high-confidence only under these repairs:

- strong descriptors are treated as baselines, not straw men;
- Bobcat is not used for identity accuracy until labels or audited pairs exist;
- pair-level modeling is the main mechanism because Re-ID errors occur at the
  comparison/candidate-pair layer;
- every phase output has an audit file and a claim-boundary note.

## Current Automated Run

`scripts/run_phase18_all.py` has executed Phase18A-F with status
`PASS`.

Important counts:

- Phase18B: 6,000 rows, 822-dimensional local descriptor-control embeddings.
- Phase18C: 3,000 CzechLynx known-ID images, 235 identities, 60,000 pair rows.
- Phase18D: 60,000 PF-ERI pair-feature rows.
- Phase18E: 5 local-control router policies, 10 metric rows.
- Phase18F: 3,000 Bobcat unlabeled images, 30,000 transfer-readiness pair rows.
- Phase18G: strong-baseline handoff and claim gate; current gate is expected to
  be `BLOCKED_STRONG_BASELINE_NOT_RUN` until strong embeddings/scores are
  supplied.

Claim boundary:

- These outputs prove the Phase18 pipeline contract runs end-to-end.
- They do not prove PF-ERI beats MegaDescriptor, WildFusion, or any strong
  descriptor baseline.
