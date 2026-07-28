# Pair-level evidence admission after wildlife re-identification retrieval: staged development and independent evaluation of PF-ERI v2

Manuscript status: v2 working draft with Methods and Results completed
Evidence cutoff: frozen PF-ERI v2 evidence package through project closure
Reporting orientation: TRIPOD-style prediction-model reporting with STROBE-relevant sample-flow and provenance elements

![Graphical abstract](../figures/pferi_v2/graphical_abstract.png)

## Abstract

Modern wildlife re-identification systems retrieve visually similar candidates, but retrieval strength does not establish that a particular image pair contains comparable evidence for responsible human review. We developed Pairwise Felid Evidence Reviewability Index version 2 (PF-ERI v2), a staged post-retrieval framework that separates dual-descriptor pair support from human visual reviewability and identity truth. A descriptor-plus-image-quality control model (P3) and its strict local pair-evidence extension (P5) were evaluated on 1,600 reviewed pairs in 400 endpoint-disjoint components, frozen at a common ridge penalty, calibrated on 448 independent pairs, and executed without outcome access on 889 external candidates. P5 reduced weighted development Brier score from 0.194909 to 0.189046, an increment of 0.005863, with nonnegative increments in all five folds. External execution identified 252 descriptor-supported pairs and produced 504 frozen calibrated predictions; 637 pairs lacked the prespecified same-direction dual-descriptor top-20 relation. In the one-shot independent analysis of the 252 supported pairs, P3 achieved a weighted Brier score of 0.307246 and P5 achieved 0.509116. The P3-minus-P5 difference was -0.201870, with a dyadic 95% interval from -0.224671 to -0.179068, and the prespecified P5 success criterion failed. PF-ERI v2 therefore established a reproducible pair-level evidence-admission task and execution workflow, but the P5 development increment did not reproduce independently. The results do not establish P5 superiority, identity accuracy, deployment utility, or automatic identity assignment.

Keywords: animal re-identification; camera traps; evidence admission; image pairs; reviewability; selective prediction; wildlife monitoring

## Introduction

Camera traps and other field-imaging systems have expanded the scale at which individual animals can be monitored, but they also produce large collections of non-canonical photographs that vary in viewpoint, visible body region, occlusion, illumination, and technical quality. Individual-animal re-identification systems address part of this problem by retrieving candidate matches from visual representations. The field now includes multi-species datasets, open-source evaluation tools, general animal descriptors, and increasingly broad benchmarks (Schneider et al., 2019; Vidal et al., 2021; Cermak et al., 2024a; Adam et al., 2025). These developments improve candidate generation, yet a high-ranked candidate is not automatically suitable for evidential use. Human reviewers may still face pairs that are technically valid and visually similar but expose different body sides, show little common pattern, or otherwise lack a responsible basis for comparison.

This distinction matters because errors made at the image-pair level can propagate into field identification and subsequent ecological analysis. Reviews of large-felid identification emphasize the methodological consequences of imperfect individual assignment, while the broader conservation-AI literature cautions that model errors and unexamined data conditions can affect downstream inference (Tuia et al., 2022; Pereira et al., 2022). Camera-trap studies have therefore called for transparent validation, controlled error rates, and human oversight rather than assuming that classifier confidence alone is sufficient (Villon et al., 2020; Whytock et al., 2021). Most of that work concerns species labels, identity ranking, or downstream ecological estimates. A separate operational question arises after retrieval: does a particular candidate pair contain enough comparable visual evidence to be reviewed responsibly?

Several established research areas approach this question without fully defining the same endpoint. Biometric quality assessment estimates the utility of a sample for recognition, but it commonly treats quality as a property of one image or of a sample relative to a standardized recognition process (Schlett et al., 2022). Visibility-aware re-identification methods model occluded body regions and shared visible information, particularly in person Re-ID (Yang et al., 2021). Selective prediction and reject-option learning formalize when a model should abstain, and conformal risk-control methods provide stronger guarantees under specified calibration and loss conditions (Geifman and El-Yaniv, 2019; Hendrickx et al., 2024; Angelopoulos et al., 2024). In animal Re-ID, calibrated similarity fusion combines global descriptors and local evidence to improve identity ranking (Cermak et al., 2024b). These literatures establish the ingredients for quality-aware and selective workflows, but they do not make descriptor support, pair reviewability, and identity truth interchangeable.

We developed Pairwise Felid Evidence Reviewability Index version 2 (PF-ERI v2) as a post-retrieval evidence-admission framework. PF-ERI treats the unordered image pair as the scientific object and separates two gates. The first asks whether two frozen descriptor systems support the same candidate relation. The second asks whether human reviewers consider the visible evidence comparable enough for responsible review. The endpoint is therefore neither descriptor confidence nor identity correctness. A different-identity pair may be review-ready when the visible evidence supports a reliable rejection, whereas a same-identity pair may be unsuitable when the shared evidence is weak.

The study addressed three linked questions. First, did an automatic local pair-evidence block add a practically meaningful and directionally stable development-stage increment beyond a descriptor-plus-image-quality control? Second, could the resulting models be frozen, calibrated, and executed on an external candidate queue without changing the model or opening outcomes? Third, did the development-stage increment reproduce in a one-shot independent comparison that accounted for repeated physical image endpoints? We answered these questions in separate prospective stages so that development qualification, probability calibration, execution validation, and independent outcome confirmation could not be treated as equivalent forms of evidence.

## Methods

### Study design and scientific object

PF-ERI v2 was designed as a staged study of pair-level evidence admission after image retrieval. The scientific object was an unordered pair of wildlife photographs proposed for human comparison, rather than either photograph considered alone. The framework distinguished five adjacent constructs: single-image technical quality, directed descriptor similarity, pair-level descriptor-relation support, human visual reviewability, and identity truth. Technical quality indicated whether an image could be decoded and measured. Descriptor similarity represented the strength or rank of one image retrieving another. Descriptor-relation support indicated whether a candidate pair satisfied a frozen cross-descriptor relation. Visual reviewability indicated whether the two photographs contained sufficiently comparable evidence for responsible human review. Identity truth indicated whether the photographs depicted the same individual and was not the primary PF-ERI endpoint (Figure 1; Table 2).

The workflow contained two pair-level gates. Gate 1 required MegaDescriptor and DINOv2 to support the same pair direction within their frozen top-20 retrieval results. Pairs satisfying either the `both_reciprocal` or `both_agreement` category entered the supported measurement path. Pairs without this relation were assigned the exact reason `no_same_direction_dual_descriptor_top20_consensus`. Gate 2 was the human assessment of visual reviewability. These gates answered different questions: failure of descriptor support did not constitute a human judgment that a pair was not review-ready, and a review-ready pair did not imply that the two images depicted the same individual. A different-identity pair could be review-ready when the visible evidence supported a responsible rejection.

### Prospective stages and information boundaries

The study separated development, model freezing, calibration, external execution, independent outcome analysis, and operational closure (Figure 2; Table 1). The independent development stage permitted model fitting and comparison using newly collected development outcomes and endpoint-disjoint folds. The subsequent freeze fixed the model family, feature sets, preprocessing, coefficients, and regularization. The calibration stage permitted only model-specific intercept and slope estimation for the frozen raw probabilities. External execution permitted descriptor measurement, image-quality measurement, local-match measurement, frozen scoring, and application of the stored calibration transforms while confirmation outcomes remained sealed. The outcome analysis then opened the accepted outcomes once and compared the frozen models without refitting or recalibration.

Each stage produced a separate disposition. Development qualification authorized calibration but did not establish external performance. Calibration completion established a reproducible probability transform but did not establish superiority. External execution validation established coverage, artifact integrity, and successful scoring along the supported path but did not use outcomes. The independent outcome analysis supplied the only external P3-versus-P5 performance comparison. Operational `CONFIRMED/CLOSED` status was defined solely for the external execution-validation scope and was not treated as evidence of P5 superiority, identity accuracy, deployment utility, or automatic identity assignment.

### Human review endpoint and adjudication

Reviewers classified each pair as `review_ready`, `not_review_ready`, or `uncertain` using a structured instrument. The binary model target was the probability of `not_ready_or_uncertain`. Under the frozen development and calibration mapping, a pair was assigned outcome 0 only when the required review-ready rule was satisfied; all other eligible combinations were assigned outcome 1. The conservative mapping treated unresolved visual evidence as non-admission rather than as evidence of identity mismatch. Reason codes and confidence were retained as descriptive fields. The technical-problem flag was used for response eligibility, whereas submission timestamps were descriptive only and were excluded from eligibility and statistical analysis (Table S3).

The formal outcome workflow used two first-pass reviews per pair. Exact first-pass agreements were retained directly, and disagreements in the formal sample were resolved by fresh blinded adjudication. The frozen final outcomes contained both the first-pass records and the final three-category and binary labels. Agreement statistics were calculated separately for development, calibration, and formal confirmation. Three-category exact agreement was the proportion of pairs receiving the same categorical decision. Binary agreement and Cohen's kappa used the review-ready versus not-ready-or-uncertain mapping. Agreement metrics were descriptive and were not used to tune either model (Table S4).

The returned human outcomes were accepted under a retrospective human-authorship disposition with a major protocol deviation. Four reviewer attestations supported accepting the decisions, reason codes, and confidence values as independently authored human judgments. The raw response files were not modified. However, formal outcome collection began before the recorded release authorization was complete, the earlier browser audit did not correspond exactly to the final application version, and timestamp patterns were inconsistent with the supplied application writer. Timestamps were therefore excluded from all time, cost, eligibility, and statistical analyses. The accepted outcomes could be used for model analysis after adjudication, but the collection was not represented as a fully clean preregistered confirmation (Table S13).

### Predictor sets and frozen models

P3 was the active control and combined descriptor and independent endpoint-quality information. Its descriptor block included MegaDescriptor and DINOv2 within-role percentiles and the descriptor-support category. Its quality block included the minimum endpoint native-pixel, sharpness, and exposure percentiles, together with endpoint quality-failure and frozen quality-stress states. P5 was a strict extension of P3 and added only the pair-evidence block: local-match coverage and its explicit missing or failure states. Thus, differences between P3 and P5 were attributable to the prespecified incremental pair-evidence block rather than to different model families or regularization choices (Table 4; Tables S6 and S7).

Both models used ridge logistic regression with an unpenalized intercept and a fixed regularization value of 100. Continuous predictors underwent training-fold median imputation, centering, and scaling by the training-fold population standard deviation, with an explicit missing indicator. Categorical predictors used frozen one-hot encoding with explicit missing and unknown states. A failed local measurement was not encoded as zero pair evidence. Preprocessing was fitted within each training partition during development and was frozen with the final model bundle. The outcome orientation was 1 for not-ready-or-uncertain and 0 for review-ready.

### Independent development and qualification

The independent development sample contained 1,600 pairs arranged in 400 endpoint-image connected components. Components, rather than rows, were the dependency and partitioning unit. Five outer folds were constructed so that physical image endpoints did not cross training and validation partitions. Each fold contained 320 validation pairs from 80 components, and the endpoint-leakage count was zero in every fold. The fixed development design used normalized inverse-square-root first-order inclusion-probability weights (Table S5).

The development estimand was weighted Brier(P3) minus weighted Brier(P5), so positive values favored P5 because lower Brier scores indicated better probabilistic prediction. P5 qualification required a pooled increment of at least 0.005 and a nonnegative increment in at least four of five outer folds. Regularization was selected without using real outcomes in the independent sample and was not retuned within the outer folds. Passing the development rule authorized freezing and calibration; it did not authorize an external-performance claim.

### Probability calibration

Calibration used an independent sample of 448 double-reviewed pairs after the P3 and P5 coefficients, preprocessing, and regularization had been frozen. For each model, the permitted calibration model was

`logit Pr(y=1) = calibration intercept + calibration slope x logit(raw frozen probability)`.

Raw probabilities were clipped only to the numerical interval from 10^-12 to 1 minus 10^-12 before the logit transformation. The calibration stage estimated one intercept and one slope for each model. It did not refit the original logistic models, change features or preprocessing, change lambda, perform model selection, or create an action threshold. The analysis required both outcome classes, finite parameters, convergence, and calibrated probabilities within the unit interval. The stored workflow also completed 2,000 bootstrap replicates as a calibration-stage diagnostic (Table S8).

### Outcome-free external execution

The external queue contained 889 candidate pairs formed from 815 verified images. Current MegaDescriptor-L-384 and DINOv2-ViT-L/14 embeddings and directed top-20 scores were generated under the frozen execution contract. Gate 1 assigned each candidate to `both_reciprocal`, `both_agreement`, or unsupported. Only supported pairs were eligible for local-match measurement, P3/P5 score-input construction, frozen raw scoring, and application of the stored calibration transforms. This restriction was specified before confirmation outcomes were opened (Table S9).

Execution integrity was evaluated using manifest row counts, embedding shapes, L2-normalization checks, file hashes, quality- and local-match failure inventories, prediction counts, and a separate validation audit. A complete supported path required one descriptor-support record, the relevant endpoint-quality measurements, one local-match row, and one calibrated prediction from each model. The execution stage did not calculate Brier scores or inspect the confirmation labels (Table S10).

### Independent outcome analysis

The independent model comparison was restricted to the 252 Gate-1-supported external pairs. The primary estimand was the Hajek-normalized inverse-probability-weighted mean of Brier(P3 calibrated) minus Brier(P5 calibrated). Positive values favored P5. The models, score inputs, and calibration parameters were taken directly from the frozen artifacts; no coefficient, predictor, preprocessing value, regularization value, or calibration parameter was recomputed.

Uncertainty was estimated with a two-sided 95% dyadic cluster-robust sandwich interval using the original physical endpoint image identifiers as dyad members. This approach allowed a photograph to contribute to more than one pair without treating all pair rows as independent. The prespecified success criterion required the lower endpoint of the 95% interval to exceed the minimum practical increment of 0.005. The analysis was performed once after the frozen prediction file had been linked to the accepted outcomes. Independent-row uncertainty was retained only as a diagnostic and did not replace the dyadic interval (Table S12).

### Reproducibility and claim control

The manuscript evidence package bound each reported claim to frozen CSV or JSON artifacts using SHA-256 hashes, declared row counts, and semantic invariants. A deterministic display builder generated six main tables, sixteen supplementary tables, and the publication figures without fitting a model or recalculating calibration parameters. Tables were retained as editable CSV and Markdown files, and figures were exported as 450-dpi PNG, SVG, and PDF files. Automated tests checked the headline results, pair-support denominators, agreement calculations, and claim boundaries. Separate checksum manifests covered the table and figure packages (Tables S14 and S16).

## Results

### Pair flow and endpoint distributions

The independent development sample included 1,600 pairs in 400 endpoint-disjoint components. Under the frozen binary mapping, 448 pairs (28.0%) were review-ready and 1,152 (72.0%) were not-ready-or-uncertain. The calibration sample included 448 pairs, of which 86 (19.2%) were review-ready and 362 (80.8%) were not-ready-or-uncertain (Table 3; Figure 4).

The full external queue contained 889 candidate pairs and 815 unique images. The final human outcomes classified 712 pairs (80.1%) as review-ready and 177 (19.9%) as not-ready-or-uncertain. Among the 252 descriptor-supported pairs used in the independent model comparison, 218 (86.5%) were review-ready and 34 (13.5%) were not-ready-or-uncertain. The 637 descriptor-unsupported pairs contained 494 review-ready and 143 not-ready-or-uncertain human outcomes. Thus, descriptor support and human reviewability were not interchangeable: most descriptor-unsupported pairs were nevertheless classified as review-ready by the human endpoint. Endpoint prevalence also differed substantially across development, calibration, and external samples. These distributions were descriptive and did not identify the cause of performance transport (Table 3; Table S11; Figure 4).

### Reviewer agreement and human-outcome provenance

In development, the reviewers gave the same three-category decision for 661 of 1,600 pairs (41.3%). Binary agreement was 855 of 1,600 (53.4%), with Cohen's kappa of 0.0787. In calibration, three-category agreement was 341 of 448 (76.1%), binary agreement was 413 of 448 (92.2%), and binary kappa was 0.7802. In the formal external sample, three-category agreement was 805 of 889 (90.6%), binary agreement was 832 of 889 (93.6%), and binary kappa was 0.8049. Eighty-four exact three-category disagreements in that sample underwent adjudication. The low development agreement indicated substantial uncertainty in the development-stage measurement of the reviewability construct; it was not interpreted as reviewer failure (Table S4).

Human authorship of the retained decision fields was accepted retrospectively on the basis of four reviewer attestations, and the final outcome audit authorized model analysis after adjudication. The major protocol deviations remained part of the evidence record. In particular, release authorization and the application-version audit were not fully prospective for the returned labels, and timestamps were excluded. Consequently, the human outcomes were analyzed as accepted human judgments with a major protocol-deviation disclosure, not as a fully clean preregistered collection (Table S13).

### Development performance and model freeze

In the pooled component-disjoint development analysis, the weighted Brier score was 0.194909 for P3 and 0.189046 for P5. The P3-minus-P5 increment was 0.005863, exceeding the frozen point-estimate threshold of 0.005. The fold-specific increments were nonnegative in all five outer folds, exceeding the stability requirement of four folds (Table 5; Table S5; Figure 3). P5 therefore passed the development qualification screen.

Following qualification, the P3 active control and P5 full model were frozen with lambda 100. The frozen P5 design equaled the complete P3 transformed design followed by the five registered local pair-evidence columns. The freeze prohibited subsequent feature changes, coefficient changes, regularization changes, or model reselection. This disposition established development qualification and a reproducible model bundle; it did not establish calibrated or external performance (Table 4; Tables S6 and S7).

### Calibration

Both outcome classes were present among the 448 calibration pairs, with 86 outcome-0 and 362 outcome-1 pairs. The stored P3 calibration intercept was -4.10791542893 and its slope was 5.57298280202. The stored P5 intercept was -3.16449012869 and its slope was 4.38560914488. Both fits converged, all calibrated probabilities were finite and within the unit interval, and all 2,000 requested bootstrap replicates were completed. No original model was refitted, no feature or regularization value changed, and no action threshold was created. The calibration stage therefore passed its frozen validity checks but did not provide an independent P3-versus-P5 performance test (Table 5; Table S8).

### External execution and descriptor support

Of the 889 candidate pairs, 252 (28.3%) satisfied Gate 1. This supported set contained 109 `both_reciprocal` pairs (12.3% of all candidates) and 143 `both_agreement` pairs (16.1%). The remaining 637 pairs (71.7%) were assigned `no_same_direction_dual_descriptor_top20_consensus`. This designation recorded failure of the frozen descriptor relation and did not encode human rejection or lack of identity evidence (Table S9; Figure 4).

The execution verified all 815 candidate images and produced complete image-quality measurements without recorded failure. MegaDescriptor and DINOv2 embedding shapes, score counts, normalization checks, and hashes matched the frozen audits. All 252 supported pairs had local-match measurements without a recorded failure, and the package contained 504 calibrated predictions, one from each model for every supported pair. The execution and validation audits passed without accessing confirmation outcomes. Accordingly, the external execution received its bounded execution-validation PASS status (Table 5; Table S10).

### Independent P3-versus-P5 comparison

The one-shot independent analysis included the 252 supported pairs, representing 357 unique physical endpoint images. The maximum physical endpoint degree was seven. The Hajek-weighted Brier score was 0.307246 for P3 and 0.509116 for P5. The primary P3-minus-P5 estimate was -0.201870, so the direction favored P3. The two-sided dyadic 95% interval was -0.224671 to -0.179068. The interval did not approach the frozen success requirement that its lower endpoint exceed 0.005 (Table 5; Table S12; Figure 3).

The independent comparison therefore failed the primary confirmation criterion. The small, directionally stable P5 increment observed in development did not reproduce in the external supported subset. This negative independent result did not alter the factual development-stage qualification, calibration completion, or external execution-integrity results, but it precluded a claim that P5 was independently superior to P3.

### Bounded study disposition

The completed evidence chain supported four bounded statements. First, the candidate image pair was successfully operationalized as a distinct post-retrieval scientific object. Second, P5 passed the prespecified development screen as a strict pair-evidence extension of P3. Third, the frozen models, calibration transforms, and external scoring path were reproducibly executed and audited. Fourth, P5 superiority did not reproduce in the independent outcome comparison (Table 6).

The project was operationally recorded as `CONFIRMED/CLOSED` only within the external execution-validation scope. The independent outcome result was not the basis for that operational closure and remained negative. Neither disposition established identity accuracy, automatic identity assignment, universal deployment utility, guaranteed risk control, or transfer to Bobcat data.

## Discussion

PF-ERI v2 produced a mixed result with a clear inferential boundary. The framework successfully operationalized the candidate image pair as a post-retrieval evidence object, completed a strictly staged model-development and execution pathway, and identified a small but directionally stable P5 increment in independent development. That increment did not reproduce in the frozen external comparison. Instead, the independent point estimate and its dyadic interval strongly favored the simpler P3 control. The central empirical conclusion is therefore not that pair evidence is useless, nor that P5 was confirmed, but that this particular P5 implementation passed its development screen and then failed to demonstrate independent superiority.

The pair-level task remains distinct from the upstream animal Re-ID methods on which it depends. MegaDescriptor and related tools provide general representations and reproducible animal Re-ID evaluation, DINOv2 supplies a strong self-supervised visual representation, and WildlifeReID-10k expands the scale and diversity of benchmark evaluation (Oquab et al., 2023; Cermak et al., 2024a; Adam et al., 2025). WildFusion further shows that global and local similarity sources can be calibrated and combined for individual identification (Cermak et al., 2024b). PF-ERI does not replace these methods or claim a better identity descriptor. It asks whether a retrieved pair should enter a human evidence workflow at all. The finding that 494 of 637 descriptor-unsupported external pairs were nevertheless human review-ready illustrates why descriptor taxonomy and visual reviewability must be reported separately.

PF-ERI also differs from single-sample quality assessment. Biometric quality frameworks appropriately define quality through expected recognition utility, and visibility-aware Re-ID methods can emphasize common visible regions (Schlett et al., 2022; Yang et al., 2021). Wildlife pairs, however, may be asymmetric in side, pose, scale, and visible pattern. A technically strong image can form a weak comparison with another technically strong image. PF-ERI makes this relational property explicit and measures it through a human reviewability endpoint. The present results support that conceptual distinction, but they do not show that the selected local-match coverage feature is a stable or sufficient measurement of the construct.

The workflow role of PF-ERI is related to selective prediction: pairs with weak evidence may be admitted, referred for expert review, or deferred. Reject-option methods provide a mature vocabulary for abstention and risk-coverage trade-offs (Geifman and El-Yaniv, 2019; Hendrickx et al., 2024). PF-ERI gives deferral a domain-specific evidential interpretation, but the current study did not estimate a risk-coverage curve, choose a deployment threshold, or establish distribution-free control. Conformal risk control should therefore be regarded as a possible future extension rather than as a property of the present model (Angelopoulos et al., 2024).

Several observed differences could contribute to the failure of transport, although this study was not designed to identify a single cause. Review-ready prevalence increased from 28.0% in development and 19.2% in calibration to 86.5% in the supported external subset. Such a shift changes the loss landscape for calibrated probability predictions, but prevalence alone does not prove why P5 failed. The external comparison was also restricted to the 252 candidates satisfying the dual-descriptor relation, which may have changed the range and meaning of local-match evidence. The stored calibration transforms were estimated in a different sample, and the distributions of frozen probabilities differed between stages. Finally, the development endpoint had low inter-reviewer agreement. Each factor is a plausible transport hypothesis; none was isolated experimentally, and selecting one after observing the result would overstate the evidence.

The development agreement result deserves particular attention. Three-category agreement of 41.3%, binary agreement of 53.4%, and binary kappa of 0.0787 indicate that the development labels contained substantial construct uncertainty. The conservative binary rule encoded disagreement and uncertainty as non-admission, which was appropriate for the frozen workflow but may have caused P5 to learn properties of reviewer discordance as well as visual reviewability. Agreement was much higher in calibration and formal confirmation. This difference is a measurement limitation and a design signal for future studies, not evidence that reviewers performed inadequately. A stronger next study should refine examples and decision anchors before collection, model reviewer-specific variation where feasible, and prespecify how disagreement enters both the target and uncertainty analysis.

The study had several methodological strengths. P3 and P5 were strictly nested, used the same regularization, and differed only by the registered pair-evidence block. Endpoint-connected components prevented image leakage across development folds. Calibration was limited to stored intercept and slope transformations. External outcomes remained sealed during measurement and scoring, and the independent comparison was performed once without refitting. Dyadic uncertainty used the original image endpoints rather than assuming independent pair rows. Finally, hashes, row-count checks, deterministic display builders, and explicit claim boundaries made it possible to preserve a negative independent result without rewriting earlier evidence.

The limitations are equally important. Only 252 of 889 external candidates, or 28.3%, entered the supported scoring path. This limits the primary comparison to a selected subset and leaves the model without predictions for most of the queue. Human outcome provenance was accepted retrospectively with a major protocol deviation; the decision fields were retained, but the collection cannot be described as a fully clean preregistered confirmation. The reviewability endpoint did not measure identity accuracy, review time, field deployment utility, downstream encounter-history validity, or ecological decision quality. No causal transport analysis was performed, and the data do not establish transfer to Bobcat imagery. The large negative independent estimate also arose in a setting with substantial stage-to-stage outcome shift, so it should not be generalized to every wildlife Re-ID system or candidate distribution.

The next study should retain the scientific task while redesigning its measurement and confirmation strategy. Reviewability criteria should be refined using disagreement-focused pilot pairs, followed by a new development sample with explicit reviewer-effects analysis. Descriptor support should either be broadened prospectively or treated as a formal deferral action whose coverage is itself an outcome. Calibration and confirmation samples should reflect the anticipated deployment prevalence and support composition, and transport diagnostics should be specified before outcomes are opened. The automatic pair-evidence block should test multiple prespecified relational features rather than relying primarily on local-match coverage. Any identity-performance study should use separately audited same/different-individual labels and should remain distinct from the reviewability endpoint.

Transparent negative confirmation is itself useful in conservation machine learning. Wildlife AI can reduce review burden, but downstream use requires that model errors, data restrictions, and human oversight remain visible (Tuia et al., 2022; Villon et al., 2020; Whytock et al., 2021). PF-ERI v2 shows that a plausible and stable development gain can reverse after frozen calibration and external transport. The resulting contribution is therefore a task definition, an auditable staged workflow, and evidence about one failed implementation, rather than a claim of a deployment-ready superior model.

## Conclusion

PF-ERI v2 formalized pair-level visual evidence admission as a distinct step after wildlife image retrieval. A strict local pair-evidence extension produced a small, directionally stable development-stage improvement over the descriptor-plus-quality control, but that improvement did not reproduce in the independent supported-pair comparison. The models and external execution path were reproducibly frozen, calibrated, and audited, yet P5 superiority was not confirmed. These results support continued study of pair reviewability and stage-separated validation while rejecting identity-accuracy, deployment-utility, or automatic-assignment claims for the present implementation.

## Data and code availability

The repository contains hash-bound derived evidence manifests, frozen model and calibration records, deterministic table and figure builders, automated tests, editable display-source files, and reproducibility checksums. The manuscript-facing evidence map is provided under `paper/supplement/source_data/pferi_v2/`. The six main tables, sixteen supplementary tables, and source figures are provided under `paper/tables/pferi_v2/` and `paper/figures/pferi_v2/`. Raw restricted imagery, sensitive location information, and identity linkage are not included in the manuscript package and will be shared only when permitted by the originating licenses, conservation-sensitivity restrictions, and applicable data-use agreements. A journal-facing repository URL and controlled-access request procedure will be inserted before submission.

## Ethics statement

This study analyzed existing wildlife photographs, derived image-pair measurements, and human review responses; it did not involve capture, handling, intervention, or experimentation on live animals. Image access and any future redistribution remain subject to the originating dataset licenses and conservation-sensitivity restrictions. Human review decisions are reported only through pseudonymous reviewer codes and aggregate statistics. The applicable institutional determination for secondary image analysis and reviewer participation, including any exemption or approval identifier, will be verified and inserted before submission.

## Author contributions

The sole author was responsible for conceptualization, methodology, software, validation, formal analysis, investigation, resources, data curation, visualization, project administration, and writing of the original draft, as well as review and editing of the manuscript. The sole author approved the manuscript and accepts responsibility for the integrity of the work.

## Acknowledgements

The author thanks four independent reviewers who completed the blinded pair-level visual assessments used in this study. The reviewers contributed human review decisions but did not participate in study conception, model development, statistical analysis, interpretation, or manuscript authorship. Reviewer identities are not reported; their contributions are described through pseudonymous codes and aggregate statistics.

## Funding

This research received no external funding.

## Competing interests

The author declares no competing interests.

## References

Adam, L., Cermak, V., Papafitsoros, K., and Picek, L. (2025). WildlifeReID-10k: Wildlife re-identification dataset with 10k individual animals. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops*. https://doi.org/10.1109/CVPRW67362.2025.00197

Angelopoulos, A. N., Bates, S., Fisch, A., Lei, L., and Schuster, T. (2024). Conformal risk control. *International Conference on Learning Representations*. https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf

Cermak, V., Picek, L., Adam, L., and Papafitsoros, K. (2024a). WildlifeDatasets: An open-source toolkit for animal re-identification. *Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision*. https://doi.org/10.1109/WACV57701.2024.00585

Cermak, V., Picek, L., Adam, L., Neumann, L., and Matas, J. (2024b). WildFusion: Individual animal identification with calibrated similarity fusion. *arXiv*. https://doi.org/10.48550/arXiv.2408.12934

Geifman, Y., and El-Yaniv, R. (2019). SelectiveNet: A deep neural network with an integrated reject option. *Proceedings of Machine Learning Research, 97*, 2151-2159. https://proceedings.mlr.press/v97/geifman19a.html

Hendrickx, K., Perini, L., Van der Plas, D., Meert, W., and Davis, J. (2024). Machine learning with a reject option: A survey. *Machine Learning*. https://doi.org/10.1007/s10994-024-06534-x

Oquab, M., Darcet, T., Moutakanni, T., Vo, H., Szafraniec, M., and others. (2023). DINOv2: Learning robust visual features without supervision. *arXiv*. https://doi.org/10.48550/arXiv.2304.07193

Pereira, K. S., Gibson, L., Biggs, D., Samarasinghe, D., and Braczkowski, A. (2022). Individual identification of large felids in field studies: Common methods, challenges, and implications for conservation science. *Frontiers in Ecology and Evolution, 10*, 866403. https://doi.org/10.3389/fevo.2022.866403

Schlett, T., Rathgeb, C., Henniger, O., Galbally, J., Fierrez, J., and Busch, C. (2022). Face image quality assessment: A literature survey. *ACM Computing Surveys, 54*(10s). https://doi.org/10.1145/3507901

Schneider, S., Taylor, G. W., Linquist, S., and Kremer, S. C. (2019). Past, present and future approaches using computer vision for animal re-identification from camera trap data. *Methods in Ecology and Evolution, 10*(4), 461-470. https://doi.org/10.1111/2041-210X.13133

Tuia, D., Kellenberger, B., Beery, S., Costelloe, B. R., Zuffi, S., and others. (2022). Perspectives in machine learning for wildlife conservation. *Nature Communications, 13*, 792. https://doi.org/10.1038/s41467-022-27980-y

Vidal, M., Wolf, N., Rosenberg, B., Harris, B. P., and Mathis, A. (2021). Perspectives on individual animal identification from biology and computer vision. *Integrative and Comparative Biology, 61*(3), 900-916. https://doi.org/10.1093/icb/icab107

Villon, S., Mouillot, D., Chaumont, M., Subsol, G., Claverie, T., and Villeger, S. (2020). A new method to control error rates in automated species identification with deep learning algorithms. *Scientific Reports, 10*, 10972. https://doi.org/10.1038/s41598-020-67573-7

Whytock, R. C., Swiezewski, J., Zwerts, J. A., Bara-Slupski, T., Pambo, A. F. K., and others. (2021). Robust ecological analysis of camera trap data labelled by a machine learning model. *Methods in Ecology and Evolution, 12*(6), 1080-1092. https://doi.org/10.1111/2041-210X.13576

Yang, J., Zhang, J., Yu, F., Jiang, X., Zhang, M., Sun, X., Chen, Y.-C., and Zheng, W.-S. (2021). Learning to know where to see: A visibility-aware approach for occluded person re-identification. *Proceedings of the IEEE/CVF International Conference on Computer Vision*. https://doi.org/10.1109/ICCV48922.2021.01167
