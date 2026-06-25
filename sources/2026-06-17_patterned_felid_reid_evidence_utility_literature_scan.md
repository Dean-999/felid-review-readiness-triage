# Patterned-Felid Re-ID Evidence Utility Literature Scan

Date: 2026-06-17

Purpose: support project-positioning discussion for PF-ERI as an evidence-utility and metric-learning enhancement layer for patterned-felid Re-ID.

## Search Focus

- animal / wildlife individual re-identification
- patterned felid photo-ID and camera-trap Re-ID
- image quality, view comparability, occlusion, blur, side visibility
- confidence, uncertainty, selective prediction, reject option, risk-coverage
- descriptor support, calibrated similarity fusion, pair-level reliability

## Key External Sources Found

1. WildlifeDatasets / MegaDescriptor
   - Source: https://arxiv.org/abs/2311.09118
   - Also: https://openaccess.thecvf.com/content/WACV2024/papers/Cermak_WildlifeDatasets_An_Open-Source_Toolkit_for_Animal_Re-Identification_WACV_2024_paper.pdf
   - Main relevance: open-source toolkit and broad benchmark/model infrastructure for animal Re-ID; introduces MegaDescriptor as a general animal Re-ID feature model.

2. WildFusion
   - Source: https://arxiv.org/abs/2408.12934
   - Main relevance: fuses deep global descriptors and local matching similarity with calibration for individual animal identification. This is close to descriptor/calibration fusion, but it is not an explicit ecological evidence admissibility or pair-comparability scoring system.

3. Multispecies animal Re-ID / community-curated dataset
   - Source: https://arxiv.org/abs/2412.05602
   - Main relevance: large multi-species animal Re-ID training and evaluation. Emphasis is model/dataset scale and generalization, not interpretable evidence utility or review-risk control.

4. WildlifeReID-10k
   - Source: https://openaccess.thecvf.com/content/CVPR2025W/FGVC/papers/Adam_WildlifeReID-10k_Wildlife_re-identification_dataset_with_10k_individual_animals_CVPRW_2025_paper.pdf
   - Main relevance: large benchmark with many individuals and species, including leakage-aware split motivation. Useful benchmark context for evaluation discipline.

5. Individual Identification of Large Felids in Field Studies
   - Source: https://www.frontiersin.org/journals/ecology-and-evolution/articles/10.3389/fevo.2022.866403/full
   - Main relevance: reviews photo-ID practice for large patterned felids and field-study constraints. Supports the domain premise that coat pattern, view, and camera-trap conditions determine evidence quality.

6. Automatic Individual Identification of Patterned Solitary Species Based on Unlabeled Video Data
   - Source: https://www.semanticscholar.org/paper/d1105ade2abe71d58e696a75de020baf2a0334c2
   - Main relevance: automated pipeline for patterned solitary species such as leopards. Shows that automation exists for patterned species, but focuses on identification pipeline rather than explicit evidence utility/risk-control scoring.

7. Machine learning with reject option / selective prediction
   - Sources:
     - https://arxiv.org/html/2107.11277v3
     - https://proceedings.mlr.press/v97/geifman19a.html
     - https://jmlr.org/papers/volume24/21-0048/21-0048.pdf
   - Main relevance: supplies general risk-coverage and abstention theory. PF-ERI can borrow this logic, but the novelty must come from adapting it to pair-level patterned-felid Re-ID evidence, not from claiming selective prediction itself is new.

8. Camera-trap quality and condition visibility
   - Source: https://pubmed.ncbi.nlm.nih.gov/41747477/
   - Main relevance: confirms that camera-trap image quality and capture conditions affect visual detectability of body-level evidence. Adjacent to PF-ERI, but focused on health/body-condition annotation rather than individual Re-ID pair comparability.

## Working Novelty Boundary

Existing work covers:

- animal Re-ID datasets, feature extractors, training recipes, and toolkits;
- model-level global/local score fusion and score calibration;
- large-scale multi-species Re-ID;
- patterned felid photo-ID and automated leopard-style pipelines;
- general selective prediction, reject option, and risk-coverage theory;
- camera-trap image quality effects in ecological annotation.

What appears less directly covered:

- a domain-specific evidence-utility layer for patterned-felid Re-ID that separates generic image clarity from individual-identification evidence;
- interpretable image-level factors mapped to pair-level comparability;
- pair-level reliability scores combining visual admissibility, flank/view comparability, pattern visibility, descriptor support, reciprocal/margin confidence, and disagreement penalties;
- using pair reliability to weight metric-learning losses and control unreliable hard negatives;
- validating against random matched and quality-proxy matched controls with held-out identity/query splits and false-candidate burden safeguards.
