# PF-ERI v2 literature verification and novelty boundary

Date: 2026-07-28
Purpose: support the PF-ERI v2 Introduction and Discussion without overstating novelty.

## Search and verification record

The planned Parallel academic searches could not run because `parallel-cli` required device authorization. The fallback used the repository's existing OpenAlex and Crossref caches plus fresh, unauthenticated OpenAlex queries. Raw query responses are stored in `sources/research_20260728_*.json` and `sources/literature_verification/`. Each reference used below had a matching OpenAlex record for title, authors, year, and DOI or an official proceedings page. One initially queried ICCV DOI resolved to an unrelated paper; it was rejected, and the correct visibility-aware Re-ID paper was identified by title search as DOI `10.1109/ICCV48922.2021.01167`.

## Evidence map

| Literature block | Verified representative sources | What is established | PF-ERI boundary |
| --- | --- | --- | --- |
| Animal Re-ID workflows and benchmarks | Schneider et al.; Vidal et al.; Cermak et al.; Adam et al. | Individual-animal identification, representation learning, retrieval benchmarks, toolkits, and cross-species evaluation are established. | PF-ERI is not presented as a new identity descriptor or benchmark. |
| Wildlife conservation AI | Tuia et al.; Whytock et al.; Villon et al. | Ecological AI requires error characterization, validation, and attention to downstream inference. | PF-ERI addresses candidate-pair evidence admission, not ecological abundance inference or species classification. |
| Similarity fusion and representation | Oquab et al.; Cermak et al. (WildFusion) | Strong self-supervised descriptors and calibrated fusion of multiple similarity sources are established. | Descriptor confidence or calibrated similarity is not assumed to be the same as human visual reviewability. |
| Biometric sample quality | Schlett et al. | Sample utility and recognition-oriented image-quality assessment are mature concepts. | PF-ERI extends the question from a single sample's utility to the relation between two non-canonical wildlife images. |
| Visibility-aware Re-ID | Yang et al. | Shared visible regions and occlusion-aware representations are established in person Re-ID. | PF-ERI uses pair comparability as an admission endpoint rather than claiming a new occlusion representation. |
| Selective prediction and rejection | Geifman and El-Yaniv; Hendrickx et al.; Angelopoulos et al. | Abstention, risk-coverage analysis, and calibrated risk control are established. | PF-ERI gives deferral a domain-specific evidential meaning but does not establish a distribution-free risk guarantee. |
| Felid field identification | Pereira et al. | Individual identification of large felids has methodological and conservation consequences. | PF-ERI evaluates reviewability, not field identity accuracy or demographic validity. |

## Novelty conclusion

The searches did not identify a direct equivalent that used responsible human reviewability of a descriptor-retrieved wildlife image pair as the principal endpoint while explicitly separating descriptor support, pair reviewability, and identity truth. Search recall is imperfect, so the manuscript should not use an absolute first-in-field claim. The defensible contribution is narrower: PF-ERI formalizes a post-retrieval pair-evidence admission task, evaluates a strict pair-evidence extension against a nested descriptor-plus-quality control, preserves endpoint-image dependence in development and confirmation, and reports development qualification separately from calibration, execution validation, and independent outcome confirmation.

## Interpretation constraints for the Discussion

The independent failure can be discussed in relation to prevalence transport, support restriction, calibration transport, and construct reliability, but none of these mechanisms was isolated experimentally. The development agreement result is evidence of endpoint uncertainty and must not be described as reviewer failure. The 637 unsupported pairs failed the frozen dual-descriptor relation; they were not rejected by humans. Operational closure concerned execution validation only. The paper must not claim identity-accuracy improvement, deployment readiness, Bobcat transfer, automatic identity assignment, or conformal risk control.
