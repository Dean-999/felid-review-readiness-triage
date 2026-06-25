# Current Project Map

Date: 2026-06-23

This file is the current navigation layer for the repository. It separates the
active PF-ERI modeling line from historical experiments, superseded plans, and
data-construction work.

## Active Core

The current project is:

```text
PF-ERI for Same-Genus Wild-to-Urban Lynx Re-ID Evidence Reliability
```

The active modeling chain is:

```text
strong descriptor retrieval
-> PF-ERI pair-level evidence utility
-> descriptor-evidence conflict
-> calibrated review routing
-> risk-controlled evaluation
-> wild-to-urban transfer stress
```

PF-ERI is not a new descriptor and not automatic identity assignment. It is a
pair-level evidence reliability and review-routing layer around strong existing
Re-ID systems.

## Phase Layers

### Layer 0: Historical Foundation

Purpose: preserve why the project moved away from generic review-readiness and
simple metric-learning claims.

- `docs/phase6/`: PF-ERI Control history, validation digests, annotation
  workflow, and claim boundaries.
- `docs/phase8/`: retrieval-control evidence and boundary interpretation.
- `docs/phase9/`: no-training PF-ERI reranking results.
- `docs/phase11/`: pair-reliability math and early pair-level learning
  implementation.
- `docs/phase12/`: RQ1-RQ4 pairwise evidence foundation and confidence maps.
- `docs/phase13/`: learned utility and metric-learning failure diagnostics.

Status: historical evidence. Use for citations, rationale, and cautionary
lessons. Do not treat these as the current main roadmap.

### Layer 1: Data Construction and Evidence Design

Purpose: construct the 2x2 wild/urban x high/low evidence dataset and detector-
first evidence gates.

- `docs/phase14/`: same-genus wild-to-urban reliability design, 2x2 evidence
  sets, MegaDetector screening, manual audit logic, and output structure.
- `scripts/*phase14*`: manifests, detector-first selection, evidence tables,
  descriptor packages, pair comparability, and conflict tables.
- `colab/phase14_megadetector_selection/`: cloud MegaDetector helper.

Status: active data foundation. Keep these available because Phase 15 and Phase
16 depend on their outputs.

### Layer 2: Current Modeling Results

Purpose: validate PF-ERI as an evidence-routed review/risk layer on known-ID
CzechLynx and transfer the policy to bobcat as a stress test.

- `docs/phase15/`: query benchmark, calibrated ranker results, repeated
  validation, review policy, wild-to-urban stress analysis, and bobcat pair
  audit package.
- `scripts/build_phase15*.py`: current modeling and review-routing scripts.
- `colab/phase15_calibrated_ranker_colab.py`: optional cloud ranker training.

Status: current evidence base. Phase 15C repeated validation and Phase 15D/E/F
are the main empirical story right now.

### Layer 3: Next Strategy

Purpose: protect the current model against weak-baseline, data-bias, and
overclaiming criticism without changing the main contribution.

- `PROJECT_RULES.md`: current scientific rules and claim boundaries.
- `docs/superpowers/plans/2026-06-23-phase16-balanced-pf-eri-strategy.md`:
  executable next-step plan.
- `docs/phase16/`: Phase 16 entry point and implementation notes.

Status: active next direction. The seven advisor-suggested points are data
governance, benchmark, and robustness safeguards around PF-ERI, not the core
modeling contribution.

## Archived Material

- `docs/archive/superseded_plans/`: older executable plans replaced by the
  Phase 16 strategy.
- `docs/archive/superseded_specs/`: older design specs whose conclusions were
  merged into Phase 14/15/16.
- `colab/archive_metric_learning/`: metric-learning cloud scripts from earlier
  diagnostic phases. They are preserved because they explain why metric learning
  is not the current main path.
- `scripts/legacy/`: historical scripts needed only for reproducing older
  analyses.

## What Counts As Core Now

Core:

- pair-level PF-ERI evidence utility;
- descriptor-evidence conflict;
- calibrated review routing;
- risk-coverage and review-burden evaluation;
- CzechLynx known-ID validation;
- bobcat wild-to-urban review-readiness stress testing.

Not core, but still useful safeguards:

- laterality-aware sampling and pair audit;
- background/site leakage-pressure diagnostics;
- strong-model benchmark packaging;
- generative or augmentation robustness;
- captive imagery as a future calibration ceiling;
- ecological/spatiotemporal plausibility priors.

## Do Not Revive As Main Claims

- PF-ERI as a new descriptor.
- automatic identity assignment.
- bobcat identity accuracy without verified labels.
- urbanization causality.
- metric-learning improvement without strong held-out controls.
- generic image-quality filtering as the main contribution.
