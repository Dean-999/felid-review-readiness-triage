# Phase 6 Unique-500 v2 Balanced Selection Plan

## Purpose

Select a new balanced 500-image CzechLynx set for image-level visual-factor annotation.

This is a data-selection and packaging workflow. It does not train models, add descriptors, change PF-ERI scores, or run factor sensitivity analysis.

## Selection Philosophy

The v2 set is neither purely random nor purely hard-case enriched. It is stratified to support PF-ERI factor-to-risk modeling.

Target composition:

- high evidence: 125 to 175 images;
- medium evidence: 150 to 200 images;
- low but annotatable: 100 to 125 images;
- extreme hard: 50 to 75 images maximum.

The hard cap is operationally important: no batch may contain more than 10 extreme-hard or near-black images.

## Candidate Pool

The selector uses the CzechLynx real-image manifest and excludes images already in the frozen Phase 4 expanded set where possible.

To avoid near-duplicate domination, the scoring pool is identity and encounter capped before quality balancing.

## Quality Proxies

The script computes lightweight image-quality proxies:

- mean luminance;
- darkness fraction;
- bright-pixel fraction;
- contrast;
- edge-density proxy;
- image size;
- near-black flag;
- eye-shine-only flag;
- almost-empty flag.

These are sampling proxies only. They are not final PF-ERI labels.

## Quality Buckets

The script assigns each candidate to:

- `high_evidence_proxy`;
- `medium_evidence_proxy`;
- `low_but_annotatable_proxy`;
- `extreme_hard_proxy`.

The selected target counts are:

- 150 high;
- 175 medium;
- 110 low but annotatable;
- 65 extreme hard.

## Batch Construction

The selected 500 images are split into 10 batches of 50.

Batches 1 to 5 contain:

- 15 high;
- 18 medium;
- 11 low;
- 6 extreme hard.

Batches 6 to 10 contain:

- 15 high;
- 17 medium;
- 11 low;
- 7 extreme hard.

This prevents the first batch from being dominated by black or near-empty images.
