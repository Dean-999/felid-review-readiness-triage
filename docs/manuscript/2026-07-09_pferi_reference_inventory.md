# PF-ERI Manuscript Reference Inventory

Date searched and checked: 2026-07-09

This inventory records the references used or reserved for the manuscript draft. It is not a full systematic review. It is a manuscript citation inventory that maps each source to its job in the argument.

## Core Sources Used In The Draft

Schneider, S., Taylor, G. W., Linquist, S., and Kremer, S. C. (2019). Past, present and future approaches using computer vision for animal re-identification from camera trap data. *Methods in Ecology and Evolution*. https://doi.org/10.1111/2041-210X.13133

Use: animal re-identification and computer-vision context.

Vidal, M., Wolf, N., Rosenberg, B., Harris, B. P., Mathis, A., and others. (2021). Perspectives on individual animal identification from biology and computer vision. *Integrative and Comparative Biology*. https://doi.org/10.1093/icb/icab107

Use: bridge between biological individual identification and computer vision.

Cermak, V., Picek, L., Adam, L., and Papafitsoros, K. (2024a). WildlifeDatasets: An open-source toolkit for animal re-identification. *IEEE/CVF Winter Conference on Applications of Computer Vision*. https://doi.org/10.1109/WACV57701.2024.00585

Use: WildlifeDatasets and MegaDescriptor context; strong descriptor control framing.

Cermak, V., Picek, L., Adam, L., Neumann, L., and Matas, J. (2024b). WildFusion: Individual animal identification with calibrated similarity fusion. arXiv:2408.12934. https://arxiv.org/abs/2408.12934

Use: modern animal Re-ID fusion context. Used to clarify that PF-ERI is not a descriptor-fusion or identity-ranking method.

Picek, L., Straka, J., Jirik, M., Belotti, E., Dula, M., Krausova, J., Bojda, M., Cermak, V., and others. (2026). CzechLynx: A Dataset for Individual Identification and Pose Estimation of the Eurasian Lynx. *Scientific Data*, 13, 511. https://doi.org/10.1038/s41597-026-06853-9

Use: CzechLynx known-ID Eurasian lynx dataset context and benchmark source. The Nature page reports 39,760 camera-trap images, identity labels, segmentation masks, pose skeletons, 319 individuals, and long-term monitoring across two regions.

Choo, Y. R., Kudavidanage, E. P., Amarasinghe, T. R., Nimalrathna, T., Chua, M. A. H., and Webb, E. L. (2020). Best practices for reporting individual identification using camera trap photographs. *Global Ecology and Conservation*, 24, e01294. https://doi.org/10.1016/j.gecco.2020.e01294

Use: field need for rigorous handling of unclassifiable photographs, inter-observer discrepancies, and misidentification risk.

Pereira, K. S., Gibson, L., Biggs, D., Samarasinghe, D., and others. (2022). Individual identification of large felids in field studies: Common methods, challenges, and implications for conservation science. *Frontiers in Ecology and Evolution*. https://doi.org/10.3389/fevo.2022.866403

Use: patterned large-felid photo-identification challenges.

Blount, D., Gero, S., Van Oast, J., Parham, J., and others. (2022). Flukebook: an open-source AI platform for cetacean photo identification. *Mammalian Biology*. https://doi.org/10.1007/s42991-021-00221-3

Use: human-in-the-loop photo-identification platform context.

Wildbook. Matching process documentation. https://wildbook.docs.wildme.org/data/matching-process.html

Use: operational matching-platform context. Accessed 2026-07-09.

Wildbook. Image analysis pipeline documentation. https://wildbook.docs.wildme.org/introduction/image-analysis-pipeline.html

Use: operational pipeline context. Accessed 2026-07-09.

Tuia, D., Kellenberger, B., Beery, S., Costelloe, B. R., and others. (2022). Perspectives in machine learning for wildlife conservation. *Nature Communications*. https://doi.org/10.1038/s41467-022-27980-y

Use: broader machine-learning-for-conservation framing.

Whytock, R. C., Swiezewski, J., Zwerts, J. A., Bara-Slupski, T., and others. (2021). Robust ecological analysis of camera trap data labelled by a machine learning model. *Methods in Ecology and Evolution*. https://doi.org/10.1111/2041-210X.13576

Use: downstream ecological analysis needs validation and error-aware handling of machine-generated labels.

Villon, S., Mouillot, D., Chaumont, M., Subsol, G., and others. (2020). A new method to control error rates in automated species identification with deep learning algorithms. *Scientific Reports*. https://doi.org/10.1038/s41598-020-67573-7

Use: error-rate control in ecological image classification, used as adjacent motivation rather than an individual-ReID claim.

Oquab, M., Darcet, T., Moutakanni, T., Vo, H., Szafraniec, M., and others. (2023). DINOv2: Learning robust visual features without supervision. arXiv:2304.07193. https://arxiv.org/abs/2304.07193

Use: strong visual descriptor context for DINOv2.

Hendrickx, K., Perini, L., Van der Plas, D., Meert, W., and others. (2024). Machine learning with a reject option: a survey. *Machine Learning*. https://doi.org/10.1007/s10994-024-06534-x

Use: reject-option and abstention background. This is a related-work source, not the novelty claim.

Geifman, Y., and El-Yaniv, R. (2017). Selective classification for deep neural networks. *Advances in Neural Information Processing Systems*. https://arxiv.org/abs/1705.08500

Use: selective classification background.

Geifman, Y., and El-Yaniv, R. (2019). SelectiveNet: A deep neural network with an integrated reject option. *Proceedings of Machine Learning Research*. https://proceedings.mlr.press/v97/geifman19a.html

Use: selective prediction background.

Angelopoulos, A. N., Bates, S., Fisch, A., Lei, L., and Schuster, T. (2024). Conformal risk control. *International Conference on Learning Representations*. https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf

Use: risk-control background. The manuscript should avoid claiming distribution-free cross-domain risk control.

## Reserved Or Context Sources

Adam, L., Cermak, V., Papafitsoros, K., and Picek, L. (2025). WildlifeReID-10k: Wildlife re-identification dataset with 10k individual animals. *IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops*. https://openaccess.thecvf.com/content/CVPR2025W/FGVC/papers/Adam_WildlifeReID-10k_Wildlife_re-identification_dataset_with_10k_individual_animals_CVPRW_2025_paper.pdf

Use: benchmark-scale reference for animal Re-ID datasets. Used to clarify that PF-ERI is not claiming benchmark-scale identity-ranking performance.

## Sources Excluded From Formal Draft Citation

Some local Crossref search outputs returned irrelevant high-citation papers because of broad search terms. These include unrelated results in `sources/papers_atrw_crossref.json`, `sources/papers_panda_reid_crossref.json`, and `sources/papers_wildlifereid10k_crossref.json`. They should not be cited without manual verification.

The DOI `10.1016/j.biocon.2020.108902` was checked and did not match the intended "Best practices for reporting individual identification using camera trap photographs" source. The correct DOI for that source is `10.1016/j.gecco.2020.e01294`.
