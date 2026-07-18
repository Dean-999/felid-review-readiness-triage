# Adversarial Review of the Sampling-Strata Proposal

Status: critical review complete; the reviewed design was accepted by the project owner pre-outcome on 16 July 2026.  
Prepared: 15 July 2026 before an official seed or v2 outcome packet.

## Overall assessment

The proposed sampling design addresses the largest remaining pre-outcome validity threat in Workstream 04: the possibility that a favourable result would be produced by a non-representative or outcome-responsive pair sample. Its strongest feature is the separation of analytical roles. Development is allowed to favor feature-range coverage, calibration preserves the queue distribution, deployment estimates performance on a probability-linked held-out frame, and mechanism confirmation deliberately enriches failure conditions without being allowed to make prevalence claims. Selecting deployment before mechanism prevents a subtle but serious bias in which difficult mechanism pairs are removed first and the remaining deployment queue becomes artificially easy.

This is one of the most important remaining design decisions, but it is not sufficient by itself. A perfect sampling rule cannot repair an outcome leak, unreliable labels, an unfrozen model, invalid calibration, or post-outcome threshold changes. Conversely, a strong model cannot repair a biased confirmation frame. Sampling is therefore a necessary structural condition for the later claim, not the single source of scientific validity.

## Critical threats that must remain gated

The first critical threat is target-population ambiguity. The primary finite population must be stated as the deduplicated canonical confirmation frame created by the randomized image partition. Calling the result representative of arbitrary CzechLynx pairs, all camera-trap images, or other retrieval depths would exceed the design. Generalisation back to the full frozen candidate graph depends on the outcome-free image allocation and balance audit; cross-species generalisation requires a new local validation cycle.

The second critical threat is unavailable full-frame automatic evidence. At present, retained image-quality and local-match measurements have passed an outcome-free pilot, but they have not been generated for every image and within-role pair required by this design. Mechanism and development evidence strata therefore cannot yet be instantiated. The design correctly treats this as a stop condition. Using pilot quantiles, imputing detector-based fields that failed feasibility, or constructing mechanism cells from reviewer impressions would invalidate the freeze.

The third critical threat is information leakage through seemingly harmless stratification variables. Identity truth, filenames, camera or site metadata inferred from paths, human oracle annotations, and fitted PF-ERI predictions could all make the sample easier or align it with later outcomes. The proposal prohibits them from primary sampling. Any later addition of camera, site, illumination, or authorized identity information must occur through a versioned amendment before the official seed and cannot be justified by inspecting labels.

## Important interpretive limitations

The six mechanism challenge classes are hierarchical bookkeeping categories, not experimentally isolated causes. A quality-stressed pair may also have weak local correspondence and descriptor disagreement, but the precedence rule assigns it to one cell to keep quotas auditable. Treating class coefficients as causal mechanism effects would therefore be confounded. The later analysis must use the underlying continuous measurements, report overlap among flags, and describe the mechanism sample as conditional stress evidence.

The quintile boundaries and rank bands are design choices rather than natural biological thresholds. Their value is reproducibility and tail coverage, not a claim that the twentieth percentile separates usable from unusable evidence. Continuous predictors remain continuous in the primary model unless the modelling specification independently justifies a transformation. Sensitivity analyses may describe adjacent quantile definitions, but the sample cannot be redrawn to favor one of them.

The image graph is connected and sampled pairs may share endpoints. Blocking image allocation by degree improves role balance but does not create independent pair observations. The proposal correctly leaves shared-image pairs in the queue and requires the accepted dyadic cluster-robust interval. An ordinary row-level interval would remain anti-conservative even if all nine retrieval cells were perfectly balanced.

## Evidence-quality conclusion

Before execution, the design has strong protection against selection bias, outcome switching, descriptor-scale misuse, and mechanism/deployment conflation. Its evidence quality remains conditional on four observable gates: complete outcome-free automatic measurements, sufficient post-partition cell capacity, exact inclusion-probability accounting, and zero information-role crossing. If all four pass before the seed is applied, the design is suitable for a confirmatory held-out evaluation of the frozen CzechLynx candidate queue. If any gate fails, the correct disposition is design repair before outcome collection, not a weaker claim after the fact.
