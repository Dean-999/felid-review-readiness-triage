# Colab / Kaggle Scripts

Date: 2026-06-23

Current cloud scripts are split into active utilities and archived diagnostic
metric-learning experiments.

## Active

- `phase14_megadetector_selection/`
  - Cloud MegaDetector support for detector-first evidence selection.
  - Used for Phase 14 data construction and top-up screening.
- `phase15_calibrated_ranker_colab.py`
  - Current optional cloud training script for calibrated candidate rankers.
  - Supports Phase 15 evidence-routed review validation.

## Archived

- `archive_metric_learning/phase9d_metric_learning/`
- `archive_metric_learning/phase10_lite_metric_learning/`
- `archive_metric_learning/phase11_metric_learning/`

These are preserved as diagnostic history. They should not be treated as the
active project path unless metric learning is explicitly reopened with stronger
controls.

## Phase 15 calibrated ranker

Use `phase15_calibrated_ranker_colab.py` only after the no-training Phase 15
benchmark and hybrid-routing tables have been generated locally.

Input file:

```text
outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv
```

Example Colab/Kaggle command:

```bash
python phase15_calibrated_ranker_colab.py \
  --input /content/phase15_czechlynx_candidate_routing_input.csv \
  --output-dir /content/phase15_colab_ranker_outputs
```

Boundary:

- CzechLynx known-ID held-out query split only.
- No bobcat identity-validation claim.
- Compare trained rankers against descriptor-only top-k before making any
  improvement claim.
