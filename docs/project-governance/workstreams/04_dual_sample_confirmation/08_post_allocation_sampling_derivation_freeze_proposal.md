# Accepted post-allocation sampling derivation freeze

Status: accepted pre-outcome by the project owner on 20 July 2026. This acceptance authorizes only the outcome-free derivation frame and capacity audit. It does not authorize formal pair selection, reviewer-packet construction, or outcome collection.

Status: proposed before pair sampling and before any v2 outcome access; owner acceptance is required before implementation may create a formal sample.

## Purpose and decision boundary

The accepted four-stage sampling design fixes the scientific roles, sample sizes, broad strata, selection order, and official seed. The completed full-frame execution now supplies automatic local-correspondence measurements for the entire 28,295-pair within-role frame. Two implementation details nevertheless remain underspecified: equal numeric values could be assigned different percentile categories under different ranking conventions, and different software could turn the same official seed into different within-cell random orders. Leaving either choice to the sampling script would create an avoidable researcher degree of freedom immediately before the formal sample is drawn.

This proposal closes those operational gaps without changing the accepted scientific design. It does not alter the 445 development, 445 calibration, 889 deployment-confirmation, or 445 mechanism-confirmation collection totals. It does not change the frozen image allocation, matcher output, failure taxonomy, analytical endpoints, or identity boundary. It authorizes neither pair selection nor outcome collection. Its machine-readable companion is `schemas/pferi_v2/post_allocation_sampling_derivation_contract_v1.json`.

## Immutable source binding

The derivation must bind to the hashes recorded in the machine-readable contract. The authoritative sources are the accepted four-stage sampling contract, official seed record, official 1,000/1,000/1,000 image-role allocation, 28,295-row within-role pair frame, restricted execution-to-canonical linkage, descriptor-membership table, 3,000-image automatic-quality table, frozen image-strata preflight, and the checksum-protected final full-frame execution export. The canonical local-match input is the 28,295-row merged canonical measurement table inside that export. A changed hash is a new input state and must stop execution rather than be silently accepted.

A read-only preflight found exact cardinality agreement. The pair frame, restricted linkage, and canonical measurement table each contain 28,295 unique keys with zero set difference. Every frame pair has retained descriptor membership. All 3,000 endpoint images occur in both the automatic-quality table and the official allocation, and no endpoint is missing. This establishes technical feasibility for the derivation but is not the post-allocation capacity result.

## Percentiles and ties

Every numeric percentile introduced at this stage will use a midrank empirical percentile. For a value x in a nonempty reference frame of size N, its percentile is the number of values strictly below x plus half the number equal to x, divided by N. Equal measurements therefore receive equal percentiles and are never split by an opaque identifier. A bottom-quintile flag means a percentile no greater than 0.20, and a top-quintile flag means a percentile no less than 0.80. The realized flagged fraction may differ slightly from exactly one fifth when a boundary contains ties; preserving measurement equivalence is preferable to manufacturing a distinction between equal observations.

The rule is consequential for local correspondence. A finite canonical coverage of zero with `failure_code = none` remains a valid observed zero. It is ranked with all other valid coverage values in the same image-allocation role and is not relabelled as missing. By contrast, a non-`none` canonical failure code, absent coverage, or nonfinite coverage is a measurement failure and is excluded only from the valid-value percentile denominator, not from the eligible pair frame. The eleven frozen scientific failures consequently remain available to the development measurement-failure state and the mechanism automatic-measurement-failure challenge class.

Descriptor similarities will first be canonicalized separately by descriptor, taking the maximum similarity across retained directions for a pair. Each canonical descriptor score will then be ranked only against pairs carrying the same descriptor in the same image-allocation role. Raw MegaDescriptor and DINOv2 scores will never be compared directly. Dual-descriptor disagreement is the absolute difference between the two resulting percentiles.

The three retained image-quality measurements will be ranked across the frozen 3,000-image set with their scientific directions made explicit. More native pixels and greater sharpness are better; less channel-extreme clipping is better, so the clipping value is sign-reversed before ranking. A pair's endpoint-quality summary is the worse, or minimum, of its two endpoint percentiles. These definitions retain the previously recorded construct limitation that the clipping fraction is an operational channel-extreme measure rather than a validated photographic-exposure scale.

## Evidence and mechanism state assignment

Development evidence state follows a fixed precedence. A pair is first assigned `measurement_failure` if a required endpoint-quality or canonical local-correspondence measurement is invalid. Among the remaining pairs, `evidence_stress` applies when any worse-endpoint quality percentile or the within-development local-correspondence percentile is in its bottom quintile, or when a dual-descriptor pair has top-quintile descriptor-percentile disagreement. Every other valid pair is `ordinary`. Crossing these states with the nine frozen retrieval strata yields at most twenty-seven development cells.

The confirmation mechanism hierarchy remains unchanged. After the deployment sample has been made immutable, each remaining confirmation pair is assigned in order to automatic measurement failure, frozen endpoint image-quality stress, bottom-quintile confirmation local correspondence, descriptor exclusivity, top-quintile dual-descriptor disagreement, or ordinary reference. The hierarchy is sampling bookkeeping, not a causal decomposition. Region-source category and directional local-match asymmetry remain available technical measurements but are not added as sampling strata because doing so now would expand the accepted design after seeing their distributions.

## Deterministic seed use

The official 64-character hexadecimal seed is decoded to 32 key bytes and used with HMAC-SHA256. Each ordering message is a compact UTF-8 JSON array containing, in order, the derivation-contract version, analytical role, sampling stage, cell identifier, and ordering-unit identifier. The ordering-unit identifier is the canonical pair identifier for within-cell pair ordering and the empty string for cell-level integer-allocation tie-breaking. Within a cell, pairs are ordered by ascending HMAC digest, with canonical pair identifier used only as a theoretical digest-collision tie-break. The first allocated number of pairs in that order forms the selection. This cryptographic hash ordering implements a deterministic seeded random permutation without dependence on a language-specific pseudorandom-number generator or library version.

Separate sampling-stage namespaces prevent the same pair ordering from being reused accidentally across development, calibration, deployment, mechanism, or integer-allocation tie-breaking. The official seed cannot be rerolled. A sample-degree audit may describe shared-image dependence but cannot trigger a favorable reroll or post-selection degree optimization; the accepted dyadic cluster-robust analysis is the remedy for shared endpoints.

## Alternatives rejected

Splitting equal numeric values by opaque pair ID was rejected because it would assign scientifically identical measurements to different evidence states solely to force exact quintile counts. Python's built-in `random` interface was rejected because reproducibility would depend on runtime and implementation details not recorded in the scientific contract. Treating zero coverage as missing was rejected because it would erase an observed conservative measurement. Excluding the eleven scientific failures was rejected because failure is an applicability state required by the accepted design. Adding region source, retry level, directional asymmetry, identity, or any reviewer-derived field as a new sampling stratum was rejected because it would expand the design after inspecting the full-frame distribution.

## Acceptance and next gate

Owner acceptance freezes only the operational derivation rules. The next implementation must produce a restricted master derivation frame, checksum manifest, join audit, percentile-and-tie audit, role-by-cell capacity table, and planned quota table. It must stop with `INSUFFICIENT_FRAME_CAPACITY` if the accepted totals cannot be filled without changing cells. Formal pair selection remains prohibited until that audit reports PASS. Reviewer-packet construction and outcome collection remain prohibited after capacity PASS until the separate formal sample and leakage audits also pass.
