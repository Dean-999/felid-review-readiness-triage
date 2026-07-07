# CodeGraph Project Structure Map

Date: 2026-07-07

This map uses CodeGraph for code-navigation structure and direct manifest
checks for data state. CodeGraph is used to answer where code lives and how
scripts relate. CSV/JSON manifests remain the source of truth for counts,
photo-selection state, freeze status, and scientific boundaries.

## Executive Map

```mermaid
flowchart TB
  Rules["PROJECT_RULES.md / AGENTS.md<br/>claim boundaries and CodeGraph contract"]
  Current["docs/structure/current_pipeline_manifest.md<br/>active read order and script list"]
  Freeze["outputs/final_freeze/<br/>current photo-selection freeze entry"]

  subgraph Data["Data and Source Inputs"]
    RawCzech["data/raw/czechlynx<br/>CzechLynx source"]
    FCF["data/external/felidae_conservation_fund<br/>Bobcat / FCF source"]
    Labels["data/labels + data/interim<br/>manual labels and internal manifests"]
    Sources["sources/<br/>literature and external evidence cache"]
  end

  subgraph legacy-code14["legacy-code14: 2x2 Image Evidence Foundation"]
    P14Sets["outputs/legacy-code14/legacy-code14_2x2_evidence_sets"]
    P14Inputs["outputs/legacy-code14/legacy-code14_algorithm_inputs<br/>12,000 image evidence rows"]
    P14Emb["outputs/legacy-code14/legacy-code14_descriptor_embeddings"]
  end

  subgraph legacy-code15["legacy-code15: Evidence-Routed Review"]
    P15Policy["outputs/legacy-code15/evidence_routed_review_policy"]
    P15Stress["outputs/legacy-code15/wild_urban_transfer_stress<br/>Bobcat 6,000 images / 300,000 pairs"]
  end

  subgraph legacy-code16["legacy-code16: Safeguards and Controls"]
    P16Audit["dataset foundation / leakage / laterality"]
    P16Score["candidate scoring and recalibration"]
    P16Pair["pair schema, CzechLynx pair table, calibrated router"]
  end

  subgraph legacy-code17["legacy-code17: Strict Photo Entry"]
    BobcatSeed["outputs/legacy-code17/legacy-code17n_bobcat_final3000_seed<br/>Bobcat clear 3,000 seed"]
    LynxStrict["outputs/czechlynx/legacy-code17_strict3000_supplement<br/>CzechLynx strict 3,000"]
    FrozenPkg["outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701<br/>6,000 frozen modeling rows"]
  end

  subgraph legacy-code18["legacy-code18: Pair-Level PF-ERI Modeling"]
    P18A["18A frozen feature manifest"]
    P18B["18B local descriptor control"]
    P18C["18C CzechLynx known-ID pair contract"]
    P18D["18D PF-ERI pair features"]
    P18E["18E review router"]
    P18F["18F Bobcat transfer readiness"]
    P18M["18M identity-balanced confirmation"]
  end

  subgraph legacy-code19["legacy-code19: Later Photo-Selection Experiments"]
    P19Pools["data/legacy-code19_candidate_pools<br/>raw reservoirs, not freeze"]
    P19Bobcat["scripts/build_legacy-code19_*<br/>Bobcat clean/area/augmentation experiments"]
  end

  Rules --> Current
  Current --> Freeze
  RawCzech --> P14Sets
  FCF --> P14Sets
  Labels --> P14Inputs
  P14Sets --> P14Inputs
  P14Inputs --> P15Policy
  P14Emb --> P15Policy
  P15Policy --> P15Stress
  P15Stress --> P16Audit
  P16Audit --> P16Score
  P16Score --> P16Pair
  P16Pair --> legacy-code17
  BobcatSeed --> FrozenPkg
  LynxStrict --> FrozenPkg
  FrozenPkg --> P18A --> P18B --> P18C --> P18D --> P18E --> P18F
  P18D --> P18M
  P18E --> P18M
  P19Pools -.candidate only.-> P19Bobcat
  P19Bobcat -.provenance / experiments.-> Freeze
  FrozenPkg --> Freeze
  P15Stress --> Freeze
```

## Current Final Freeze

Use `outputs/final_freeze/` as the current navigation layer.

```mermaid
flowchart LR
  FF["outputs/final_freeze"]

  BU["bobcat-urban/<br/>manifest.csv<br/>6,000 images"]
  BUPairs["legacy-code15 pair table<br/>300,000 pairs"]
  BW["bobcat-wild/<br/>Bobcat frozen manifest<br/>3,000 images"]
  LW["lynx-wild/<br/>CzechLynx frozen manifest<br/>3,000 images"]
  LU["lynx-urban/<br/>150 auxiliary<br/>manifest pending"]

  FF --> BU
  FF --> BW
  FF --> LW
  FF --> LU
  BU --> BUPairs
```

Validated freeze counts:

| Freeze scope | Rows | Source |
| --- | ---: | --- |
| `bobcat-urban` | 6,000 images | `outputs/final_freeze/bobcat-urban/manifest.csv` |
| `bobcat-urban-pairs` | 300,000 pairs | `outputs/legacy-code15/wild_urban_transfer_stress/legacy-code15e_bobcat_evidence_routed_review_table.csv` |
| `bobcat-wild` | 3,000 images | `outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/bobcat_frozen_manifest.csv` |
| `lynx-wild` | 3,000 images | `outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/czechlynx_frozen_manifest.csv` |
| `lynx-urban` | 150 images | plan-complete auxiliary, manifest pending archival |

## Phase Flow

```mermaid
flowchart TB
  P14["legacy-code14<br/>2x2 image evidence foundation"]
  P15["legacy-code15<br/>evidence-routed review + wild/urban stress"]
  P16["legacy-code16<br/>safeguards, scoring, pair contracts"]
  P17["legacy-code17<br/>strict photo-entry and final-3000 seeds"]
  FreezePkg["legacy-code17 freeze package<br/>6,000 rows"]
  P18["legacy-code18<br/>PF-ERI pair-level evidence governance"]
  Strong["Strong descriptors<br/>MegaDescriptor / DINOv2 returned artifacts"]
  Reviews["Blind reviewability analyses<br/>18I / 18J / 18L / 18M"]
  FinalFreeze["outputs/final_freeze<br/>current photo freeze"]

  P14 --> P15 --> P16 --> P17 --> FreezePkg --> P18
  Strong --> P18
  P18 --> Reviews
  P17 --> FinalFreeze
  P15 --> FinalFreeze
```

## CodeGraph Script Backbone

CodeGraph identified these as the active backbone or navigation/guardrail
scripts. Broad CodeGraph queries can retrieve legacy or experimental scripts,
so exact paths remain preferred once known.

```mermaid
flowchart TB
  Contract["scripts/check_codegraph_project_contract.py<br/>CodeGraph use boundary"]
  Consolidation["scripts/build_project_artifact_consolidation_index.py<br/>non-destructive artifact index"]
  Freeze17["scripts/freeze_legacy-code17_modeling_dataset.py<br/>legacy-code17 modeling package freeze"]
  Run18["scripts/run_legacy-code18_all.py<br/>legacy-code18a-G runner"]

  subgraph P18Scripts["legacy-code18 scripts"]
    A["build_legacy-code18a_frozen_feature_manifest.py"]
    B["build_legacy-code18b_local_descriptor_control.py"]
    C["build_legacy-code18c_czechlynx_pair_contract.py"]
    D["build_legacy-code18d_pf_eri_pair_features.py"]
    E["build_legacy-code18e_review_router.py"]
    F["build_legacy-code18f_bobcat_transfer_readiness.py"]
    G["build_legacy-code18g_strong_baseline_claim_gate.py"]
  end

  subgraph P19Scripts["legacy-code19 Bobcat photo-selection experiments"]
    Clean["build_legacy-code19_bobcat_inat_daylight_clean_queue.py"]
    Area["build_legacy-code19_bobcat_inat_area10_queue.py"]
    Final["build_legacy-code19_bobcat_final3000_with_area10_seed.py"]
    Aug["build_legacy-code19_bobcat_area10_augmented_final3000.py"]
  end

  Contract --> Consolidation
  Freeze17 --> Run18
  Run18 --> A --> B --> C --> D --> E --> F --> G
  Clean --> Area --> Final --> Aug
```

## Directory Roles

| Path | Role | Use now |
| --- | --- | --- |
| `outputs/final_freeze/` | Current freeze entry point | Yes, primary navigation |
| `outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/` | Stable 3,000 Bobcat + 3,000 CzechLynx modeling package | Yes, source of truth for frozen 6,000 package |
| `outputs/legacy-code14/legacy-code14_algorithm_inputs/` | 12,000-row 2x2 image evidence table and pair comparability | Yes, provenance and legacy-code15 input |
| `outputs/legacy-code15/wild_urban_transfer_stress/` | Bobcat urban/peri-urban transfer-stress pair outputs | Yes, pair-level stress source |
| `outputs/legacy-code16/` | Safeguards, scoring, pair contracts, calibrated controls | Yes, provenance/control layer |
| `outputs/legacy-code17/` | Bobcat final seed and strict review history | Yes, provenance; avoid treating all subdirs as current |
| `outputs/czechlynx/legacy-code17_strict3000_supplement/` | CzechLynx strict 3,000 rebuild and augmentation | Yes, provenance for lynx wild freeze |
| `outputs/legacy-code18/` | Pair-level modeling, strong descriptor controls, reviewability analyses | Yes, current algorithmic evidence layer |
| `outputs/legacy-code19/` | Later Bobcat photo-selection experiments | Conditional; not a stable freeze source unless manifest exists and is indexed |
| `data/legacy-code19_candidate_pools/` | Raw candidate reservoirs | No final claims; candidate only |
| `sources/` | Literature/source cache | Citation support, not model output |
| `colab/` | GPU/Colab training and strong-model packages | Runtime support/provenance |
| `scripts/prototypes/` | Throwaway or exploratory logic | Provenance only unless promoted and documented |

## Claim Boundaries

- PF-ERI is a post-retrieval pair-level evidence-governance and review-routing
  layer.
- It is not a descriptor replacement.
- It is not automatic identity recognition.
- Bobcat material is not verified individual identity evidence unless separate
  identity labels or audited same/different pair labels are added.
- `lynx-urban` is a 150-image auxiliary note, not a 3,000-image main cell.
- CodeGraph can locate and trace code; it cannot decide photo validity, CSV
  counts, phase completion, or final scientific claims.

## Practical Navigation

Start here:

1. `outputs/final_freeze/README.md` for current photo freeze.
2. `docs/structure/current_pipeline_manifest.md` for active scripts and read
   order.
3. `docs/legacy-code18/README.md` for current pair-level modeling status.
4. `outputs/legacy-code18/legacy-code18m_identity_balanced_analysis/` for the strongest
   current blind-confirmed reviewability result.
5. `outputs/project_structure/codegraph_contract/` and
   `outputs/project_structure/artifact_consolidation_index/` for structure
   guardrails.

