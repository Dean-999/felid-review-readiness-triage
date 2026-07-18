# Task 04: Feature-Retention Decision After Outcome-Free Measurement Pilot

Status: frozen field-level decision; Workstream 02 remains in progress pending reviewer-interface audit.

## Decision scope

This decision applies only to whether a field has demonstrated outcome-free measurement feasibility on the fixed CzechLynx pilot. It does not select a predictive model, fit a coefficient, choose an operating threshold, or establish that a field improves re-identification. The field set remains unavailable for outcome modelling until the separate reviewer-interface gate has passed and the subsequent modelling protocol is frozen.

## Retained automatic candidates

`local_match_coverage_fraction` is retained as an automatic pair-level candidate. The frozen SuperPoint–LightGlue–RANSAC execution produced valid canonical coverage for all 160 pilot pairs, observed 154 distinct canonical values, respected the exact canonical-minimum aggregation rule for every pair, used no manual rescue, and had a 1.659-second 95th-percentile pair runtime. Its source archive and gate audit are at `outputs/pferi_v2/measurement_feasibility_pilot/local_match_runs/2026-07-14_gpu_t4_protocol_v2/`. This decision establishes only the feasibility of producing a local-correspondence coverage measure, not identity discrimination or threshold performance.

`native_pixel_count`, `sharpness_measure`, and `exposure_clipping_fraction` are retained as automatic image-quality candidates. Each was valid for all 305 images, had more than ten distinct values, used no manual rescue, and had a 0.163-second 95th-percentile native-metrics runtime. The clipping field must be described operationally as a channel-extreme fraction because its current definition marks a pixel if any RGB channel is near an extreme. Pixel count and sharpness are also image-acquisition proxies and may reflect camera, crop, resolution, infrared conditions, or sensor noise. These construct caveats are retained with the variables; later outcome-separated analysis must test their incremental value and possible redundancy rather than assume they are independent biological evidence.

## Excluded automatic field

`animal_coverage_fraction`, measured by the generic COCO cat-mask proxy, is excluded from the primary automatic feature set. It was valid for 113 of 305 decoded images, or 37.0%, which fails the pre-specified 90% valid-output gate. The other conditions, including runtime and variation among the detected images, do not override that failure. The 192 `subject_not_detected` records are missing measurements rather than zero coverage and must not be imputed, converted to zero, or manually rescued. The archive and gate audit are at `outputs/pferi_v2/measurement_feasibility_pilot/automatic_quality_runs/2026-07-14_gpu_cuda_protocol_v1/`.

## Oracle-only fields

Visible-pattern area, occlusion, shared-body region, and viewpoint compatibility remain oracle-only measurement-evaluation fields. Their two-annotator reliability gate passed on the 160-pair packet, including ICC lower bounds above the fixed threshold and a weighted-kappa lower bound above the fixed threshold. They remain excluded from the primary automatic model because they rely on human annotation and were not designated as automatically inferable evidence.

## Guardrails and next gate

No retained candidate may be described as a validated Re-ID feature, a causal driver of identity correctness, or a cross-felid result. The current decision does not reopen the rejected COCO proxy. A future species-adapted visible-body-region measurement would require a new versioned definition, a fresh outcome-free pilot, and an independent validation target before it could be considered. The remaining Workstream 02 hard gate is an independent reviewer-interface audit; no real v2 outcome collection may begin before that audit passes.
