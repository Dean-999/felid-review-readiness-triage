# Phase 14 Algorithm Logic Source Notes

Date: 2026-06-21

This note records sources consulted while planning the Phase 14 2x2 algorithmic pipeline. `parallel-cli` was unavailable locally, so the search was performed through available web lookup and saved here for reproducibility.

## Camera-trap detection and prefiltering

- Microsoft MegaDetector / Biodiversity repository: https://github.com/microsoft/CameraTraps/blob/main/megadetector.md
  - Relevance: use MegaDetector as a mature animal/person/vehicle detector and crop/geometry provider, not as a research contribution.
- LILA MegaDetector results for camera-trap datasets: https://lila.science/megadetector-results-for-camera-trap-datasets/
  - Relevance: LILA provides precomputed MegaDetector outputs, including RDE versions; useful for detector-first candidate selection without downloading all images.

## Wildlife Re-ID feature extraction

- WildlifeDatasets: An open-source toolkit for animal re-identification: https://arxiv.org/abs/2311.09118
  - Relevance: establishes WildlifeDatasets and MegaDescriptor as strong reusable baselines for animal Re-ID.
- WildlifeTools repository: https://github.com/WildlifeDatasets/wildlife-tools
  - Relevance: practical tooling for animal Re-ID feature extraction and similarity analysis.
- MegaDescriptor model card: https://huggingface.co/BVRA/MegaDescriptor-L-384
  - Relevance: fixed descriptor source for retrieval signals; our project should not claim to invent the descriptor.
- WildlifeReID-10k: https://arxiv.org/abs/2406.09211
  - Relevance: important baseline dataset and warning that random splits can be inadequate in wildlife Re-ID.
- OpenAnimals: https://arxiv.org/abs/2410.00204
  - Relevance: animal Re-ID differs from person Re-ID because species, pose, environment, and body structure vary.
- Multispecies Animal Re-ID Using a Large Community-Curated Dataset: https://arxiv.org/abs/2412.05602
  - Relevance: strong multispecies model direction; useful as a future stronger descriptor comparison, not the present PF-ERI contribution.

## Risk control and abstention

- Selective Classification for Deep Neural Networks: https://arxiv.org/abs/1705.08500
  - Relevance: risk-coverage / reject-option framing; directly maps to accept-review-defer decisions.
- Conformal Risk Control: https://arxiv.org/abs/2208.02814
  - Relevance: distribution-free risk control for monotone losses; possible later upgrade for calibrated thresholds.
- A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification: https://arxiv.org/abs/2107.07511
  - Relevance: explains model-agnostic uncertainty/risk calibration; useful for conservative paper framing.
