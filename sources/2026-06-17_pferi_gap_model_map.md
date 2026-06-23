# PF-ERI Gap Model Map

Date: 2026-06-17

Purpose: map the patterned-felid Re-ID evidence utility idea against adjacent literatures and identify defensible mathematical-modeling gaps.

## Literature Blocks Checked

1. Animal Re-ID datasets and models
   - WildlifeDatasets / MegaDescriptor: https://openaccess.thecvf.com/content/WACV2024/papers/Cermak_WildlifeDatasets_An_Open-Source_Toolkit_for_Animal_Re-Identification_WACV_2024_paper.pdf
   - WildlifeReID-10k: https://openaccess.thecvf.com/content/CVPR2025W/FGVC/papers/Adam_WildlifeReID-10k_Wildlife_re-identification_dataset_with_10k_individual_animals_CVPRW_2025_paper.pdf
   - AnimalCLEF 2025 open-set Re-ID overview: https://ceur-ws.org/Vol-4038/paper_231.pdf
   - Multispecies Animal Re-ID: https://arxiv.org/html/2412.05602v1
   - OpenAnimals: https://openaccess.thecvf.com/content/ICCV2025/papers/Hou_OpenAnimals_Revisiting_Person_Re-Identification_for_Animals_Towards_Better_Generalization_ICCV_2025_paper.pdf

2. Patterned species and felid/photo-ID context
   - Large felid individual identification review: https://www.frontiersin.org/journals/ecology-and-evolution/articles/10.3389/fevo.2022.866403/full
   - Automatic individual identification of patterned solitary species: https://arxiv.org/abs/2304.09657
   - Landmark-guided animal Re-ID: https://openaccess.thecvf.com/content_WACVW_2020/papers/w2/Moskvyak_Learning_Landmark_Guided_Embeddings_for_Animal_Re-identification_WACVW_2020_paper.pdf

3. Biometric image quality / utility
   - Face Image Quality Assessment survey: https://dl.acm.org/doi/10.1145/3507901
   - Biometric quality review: https://link.springer.com/article/10.1186/1687-5281-2014-34
   - NIST biometric quality report: https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7544.pdf
   - Utility-based performance evaluation of biometric quality: https://link.springer.com/article/10.1186/s13640-024-00644-1

4. Pairwise visibility / occlusion in Re-ID
   - Quality-aware Part Models for occluded person Re-ID: https://arxiv.org/abs/2201.00107
   - Visibility-aware occluded person Re-ID: https://openaccess.thecvf.com/content/ICCV2021/papers/Yang_Learning_To_Know_Where_To_See_A_Visibility-Aware_Approach_for_ICCV_2021_paper.pdf
   - High-quality face images matching poorly / relational quality: https://www.cs.colostate.edu/~draper/papers/beveridge_fg11.pdf

5. Selective prediction, reject option, and risk control
   - Machine learning with a reject option survey: https://arxiv.org/html/2107.11277v3
   - Optimal Strategies for Reject Option Classifiers: https://jmlr.org/papers/volume24/21-0048/21-0048.pdf
   - Selective classification for deep neural networks: https://arxiv.org/pdf/1705.08500
   - Calibrated selective classification: https://arxiv.org/html/2208.12084v2

6. Camera-trap AI review burden and ecological inference
   - Robust ecological analysis of ML-labelled camera-trap data: https://besjournals.onlinelibrary.wiley.com/doi/10.1111/2041-210X.13576
   - Camera-trap image analysis design patterns: https://pmc.ncbi.nlm.nih.gov/articles/PMC6953665/
   - Human supervision in AI-assisted wildlife camera-trap workflows: https://theoryandpractice.citizenscienceassociation.org/articles/10.5334/cstp.752

## Preliminary Gap

The broad components are not new: animal Re-ID, biometric quality, selective prediction, occlusion-aware Re-ID, and ecological AI review workflows all exist.

The likely gap is narrower:

> a pair-level, evidence-admissibility model for patterned-felid Re-ID that explicitly models whether two images are comparable as individual-identity evidence before using descriptor similarity for retrieval, rejection, reranking, or loss weighting.

This gap is strongest if formalized mathematically as a constrained decision problem rather than as a heuristic quality filter.
