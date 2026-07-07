# Phase18 Pair-Level Evidence Reliability Modeling

Date: 2026-07-01

Phase18 starts from the frozen local modeling package:

```text
outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701/
```

The phase keeps the project direction fixed:

```text
strong descriptor / matching platform
-> candidate queue
-> PF-ERI pair-level evidence admissibility
-> descriptor-evidence conflict and risk estimate
-> evidence-routed review action
```

## Current Slices

1. Phase18A builds an image-level feature manifest from the frozen package.
2. Phase18B extracts descriptor embeddings from Phase18A rows.
3. Phase18C creates CzechLynx known-ID candidate pairs and split manifests.
4. Phase18D adds PF-ERI 2.0 pair features.
5. Phase18E trains/calibrates conservative review routers.
6. Phase18F applies transfer-stress/readiness scoring to Bobcat without identity
   accuracy claims.
7. Phase18G packages strong-baseline handoff inputs and blocks final claims
   until credible strong descriptor artifacts are returned.

## Automated Local-Control Pipeline

The current automated pipeline is:

```text
scripts/run_phase18_all.py
```

It runs:

```text
Phase18A -> Phase18B -> Phase18C -> Phase18D -> Phase18E -> Phase18F -> Phase18G
```

Current outputs:

- `outputs/phase18/phase18a_frozen_feature_manifest/`
- `outputs/phase18/phase18b_local_descriptor_control/`
- `outputs/phase18/phase18c_czechlynx_pair_contract/`
- `outputs/phase18/phase18d_pf_eri_pair_features/`
- `outputs/phase18/phase18e_review_router/`
- `outputs/phase18/phase18f_bobcat_transfer_readiness/`
- `outputs/phase18/phase18g_strong_baseline_claim_gate/`
- `outputs/phase18/phase18_all_pipeline/`

Current run summary:

- Phase18B rows: 6,000.
- Phase18B embedding shape: 6,000 x 822.
- Strong-model runtime status: not ready in the current local Python runtime
  because `torch` and `timm` are unavailable.
- Phase18C CzechLynx known-ID rows: 3,000 images, 235 identities, 60,000 top-k
  candidate pairs.
- Phase18D PF-ERI feature rows: 60,000.
- Phase18E router policies: 5 deterministic local-control policies.
- Phase18F Bobcat transfer-readiness rows: 30,000 pair rows over 3,000 unlabeled
  Bobcat images.
- Phase18G status: `BLOCKED_STRONG_BASELINE_NOT_RUN` until strong descriptor
  embeddings or pair scores are supplied.

## Baseline Boundary

Phase18B is currently a local descriptor-control baseline, not a strong
MegaDescriptor/WildFusion/foundation-model baseline. This lets the full
algorithm chain run automatically and exposes schema/modeling bugs early. It
does not support final scientific claims against descriptor-only or strong Re-ID
systems.

The next scientific upgrade is to replace or add to Phase18B with:

```text
MegaDescriptor / WildlifeTools
DINOv2 or another strong foundation descriptor
optional WildFusion/local matching scores
```

Phase18G is the guardrail for this boundary. If strong descriptor artifacts are
absent, Phase18G still writes a handoff manifest but keeps the scientific claim
gate blocked.

## Claim Boundary

PF-ERI is not a descriptor replacement and Phase18 must not claim Bobcat
identity accuracy without verified Bobcat identity labels or audited
same/different pair labels. The primary endpoint is review utility:
admissibility, comparability, conflict, risk coverage, abstention, and review
burden.
