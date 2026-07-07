# Current Project Map

Date: 2026-07-07

This is the current navigation layer after the repository slimming. The active
project is no longer organized around the old Phase16/17/18 directory names.
Those folders remain provenance, diagnostics, or legacy reproduction material.

## Core Claim

```text
PF-ERI is a post-retrieval, pair-level evidence governance layer for patterned
felid Re-ID candidate review.
```

PF-ERI is not a new descriptor, not automatic individual recognition, and not a
primary top-k/mAP improvement claim. The active question is whether a candidate
pair returned by a strong descriptor queue is evidence-admissible,
review-ready, should be deferred, or carries evidence risk.

## Current Data Entry Point

Use this folder for final modeling inputs:

```text
outputs/final_freeze/
```

Current frozen scopes:

| Scope | Status | Rows | Role |
| --- | --- | ---: | --- |
| `lynx-wild` | frozen | 3,000 | known-ID CzechLynx validation core |
| `bobcat-wild` | frozen | 3,000 | wild Bobcat transfer/evidence stress core |
| `bobcat-urban` | frozen | 6,000 | urban/peri-urban Bobcat stress and pair-contamination core |
| `lynx-urban` | auxiliary only | no 3000-image manifest | small heterogeneity note; not a forced core cell |

Rules:

- final modeling must read `outputs/final_freeze/<scope>/manifest.csv`;
- final modeling must use copied files in `outputs/final_freeze/<scope>/images/`;
- candidate reservoirs and historical phase outputs are provenance, not the
  modeling entry point;
- Bobcat rows do not provide verified individual identity labels;
- Bobcat identity accuracy and Bobcat false-match accuracy remain blocked unless
  verified individual labels or audited same/different Bobcat pair labels are
  created later;
- do not force a symmetric CzechLynx urban 3000 cell.

## Current Evidence Status

Phase18L and Phase18M establish the current pair-level mechanism.

Phase18L descriptor-controlled result:

```text
PASS
```

Phase18M identity-balanced result:

```text
BLIND_CONFIRMED_IDENTITY_BALANCED_PASS
```

Interpretation:

```text
Low PF-ERI admissibility remains enriched for human uncertain/not-ready
reviewability labels after descriptor family, descriptor similarity, and known
same/different identity stratum are controlled.
```

This supports PF-ERI as a pair-level reviewability and evidence-admissibility
signal. It does not support a claim that PF-ERI is an identity classifier.

## Active Modeling Direction

The next active layer is:

```text
PF-ERI Selective Evidence Sufficiency Model
```

The formal modeling chain is:

```text
strong descriptor retrieval
-> candidate pair queue
-> pair-level evidence sufficiency scoring
-> calibrated selective evidence admission
-> risk-coverage and review-budget routing
-> Bobcat wild/urban transfer-stress evaluation
```

Scientific subtitle:

```text
A risk-calibrated selective inference layer for wildlife Re-ID candidate pairs
```

The first modeling bootstrap is:

```text
scripts/build_final_modeling_bootstrap.py
outputs/modeling-validation/final-modeling-bootstrap/
```

Run this before final algorithm work. It verifies that the physical freeze is
usable and writes the modeling contract that downstream scripts should consume.

Active work after this point must be named by module purpose, not by new phase
numbers. Examples: `modeling-contract`, `evidence-feature-extraction`,
`known-id-evidence-sufficiency-validation`,
`risk-calibrated-evidence-admission`, `bobcat-wild-urban-transfer-stress`,
and `review-budget-routing`.

## Current Folder Roles

Active:

- `outputs/final_freeze/`: current physical photo freeze and manifest entry.
- `outputs/modeling-validation/final-modeling-bootstrap/`: generated readiness
  contract for final modeling.
- `outputs/modeling-validation/pair-level-validation/`: completed pair-level
  validation evidence, strong descriptor controls, and reviewability analyses.
- `docs/modeling-validation/pair-level-validation/`: scientific interpretation
  and claim boundaries for completed validation and the transition into
  selective evidence sufficiency modeling.
- `docs/photo-freeze/`: photo-freeze rules and provenance map.
- `docs/project-governance/`: structure maps, logs, project rules, and
  executable plans.
- `PROJECT_RULES.md`: binding scientific claim boundaries.
- `AGENTS.md`: CodeGraph and project-specific tool guardrails.

Legacy/provenance:

- old `outputs/phase16`, `outputs/phase17`, and `outputs/phase18` paths;
- old `docs/phase*` paths;
- archived metric-learning and candidate-selection scripts;
- candidate source pools under `data/` or historical output folders.

Legacy material can explain how a dataset was constructed, but it must not
override `outputs/final_freeze` or current claim rules.

## What Counts As Core Now

Core:

- pair-level PF-ERI evidence utility;
- descriptor-evidence conflict;
- review-readiness and evidence-admissibility routing;
- calibrated selective evidence admission;
- risk coverage, positive retention, and review burden;
- review-budget routing;
- CzechLynx known-ID validation;
- Bobcat wild/urban transfer and evidence-risk stress testing;
- strong-descriptor-controlled comparison.

Not core:

- training a new descriptor as the main contribution;
- claiming automatic Bobcat individual recognition;
- claiming Bobcat identity accuracy without verified Bobcat identities;
- forcing a 4x3000 design when the fourth cell is scientifically weak;
- using old candidate-selection folders as final modeling inputs.
