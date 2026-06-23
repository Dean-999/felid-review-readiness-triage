# Phase 8 Re-ID Tool and Dataset Search Summary

Date: 2026-06-14

Purpose: targeted source summary for Phase 8 planning. This is not a full systematic review.

## Re-ID Tools and Methods

- WildlifeDatasets paper: https://arxiv.org/abs/2311.09118 and WACV open-access PDF. Reports WildlifeDatasets as an open-source toolkit for animal Re-ID, with dataset preprocessing, performance analysis, model fine-tuning, and MegaDescriptor.
- WildlifeDatasets repository/docs: https://github.com/WildlifeDatasets/wildlife-datasets and https://wildlifedatasets.github.io/wildlife-datasets/
- wildlife-tools repository/docs: https://github.com/WildlifeDatasets/wildlife-tools and https://wildlifedatasets.github.io/wildlife-tools/. Covers feature extraction, similarity calculation, image retrieval, classification, and examples for MegaDescriptor and WildFusion.
- MegaDescriptor-S-224 Hugging Face model card: https://huggingface.co/BVRA/MegaDescriptor-S-224. Describes a Swin-S image feature model pretrained on animal Re-ID datasets.
- WildFusion: https://arxiv.org/html/2408.12934v1. Proposes calibrated similarity fusion of global deep scores and local matching scores for individual animal identification.
- ATRW Amur tiger benchmark: https://arxiv.org/abs/1906.05586, https://lila.science/datasets/atrw/, and https://cvwc2019.github.io/challenge.html. Uses rank-1 and mAP in challenge context.
- WildlifeReID-10k: CVPRW 2025 open-access PDF at https://openaccess.thecvf.com/content/CVPR2025W/FGVC/papers/Adam_WildlifeReID-10k_Wildlife_re-identification_dataset_with_10k_individual_animals_CVPRW_2025_paper.pdf and Kaggle listing https://www.kaggle.com/datasets/wildlifedatasets/wildlifereid-10k.

## Candidate External Felid Dataset Signals

- ATRW Amur tiger: public benchmark signal; >8,000 clips / 92 tigers in paper; LILA notes around 9,500 boxes and around 3,600 identity-linked boxes.
- Jaguar Re-ID: Kaggle competition https://www.kaggle.com/competitions/jaguar-re-id reports a test set of 371 images and 31 jaguars. Hugging Face dataset page https://huggingface.co/datasets/jaguaridentification/jaguars describes Porto Jofre jaguar individual-ID dataset.
- WildlifeReID-10k: broad multi-species benchmark; source summary reports >10k identities, >140k images, around 33 species / 37 datasets, including leopard and Amur tiger categories.
- African leopard: identified in recent model-combination study as provided by African Carnivore Wildbook, but public direct access was not confirmed in this quick search.
- Clouded leopard: camera-trap studies and recent Sunda clouded leopard individual monitoring reports exist, but no public individual Re-ID benchmark dataset was confirmed in this quick search.
- Snow leopard: algorithm-comparison literature exists, but no clearly public benchmark with downloadable individual labels was confirmed in this quick search.
- Lynx beyond CzechLynx: LILA lists WSU Lynx as a camera-trap dataset, but individual-ID Re-ID suitability was not confirmed in this quick search.

## Phase 8 Use

Immediate implementation should use CzechLynx local descriptor and identity-label resources. Broader patterned-felid claims require external dataset download/access checks and a separate leakage/license audit before analysis.
