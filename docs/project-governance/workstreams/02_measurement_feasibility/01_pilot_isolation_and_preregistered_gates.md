# Task 01: Pilot Isolation and Pre-registered Gates

Status: complete. Contract version: `pferi_v2_measurement_feasibility_pilot_contract_v1`.

## Purpose

The measurement-feasibility pilot is a stress test for the measurement system, not a small confirmation study. It must expose feature failures before scarce outcome-review capacity is used, while remaining unable to influence a v2 confirmation estimate through reused pairs or observed reviewability labels. This task freezes the pilot unit, selection boundary, and feature-retention rules before any pilot measurement is inspected.

## Pilot Design

The target is 160 unique canonical unordered CzechLynx pairs. This number is a practical measurement pilot target rather than a power calculation for a predictive effect. It is large enough to make gross variation, missingness, runtime, and annotation-reliability failures visible, but it cannot establish model utility. The pilot manifest uses a restricted canonical-pair link and a neutral pilot identifier. It records only the seed, selection stratum, availability, inclusion status, and exclusion reason. It contains no v1 identifier, identity truth, route, score, review decision, or v2 outcome label. Every selected pilot pair is permanently ineligible for either v2 confirmation sample.

Selection is made from a frozen CzechLynx candidate-pair reservoir using a fixed seed and prospective coverage of descriptor membership, retrieval-rank band, day/infrared metadata, image-decode availability, and source-camera context where it exists. These fields are selection metadata only; they are never reviewer-visible. The selection may not use a model score, a v1 outcome, a v2 outcome, or an observed pilot measurement to favor a field that looks successful.

## Fixed Retention Rules

The pilot has ten gates fixed before measurement. Each active-control quality field requires at least 90 percent valid automatic output among decodable eligible images, at least ten distinct valid values, zero manual rescues, and a 95th-percentile runtime no greater than 30 seconds per image on a documented reference environment. Local-match coverage requires at least 80 percent valid output among pairs with two decodable images, at least ten distinct values, exact endpoint-order invariance, zero manual rescues, and a 95th-percentile runtime no greater than 60 seconds per pair.

The three continuous oracle structural measurements require a lower 95 percent confidence bound of at least 0.60 for two-annotator ICC, and viewpoint compatibility requires a lower 95 percent confidence bound of at least 0.50 for weighted kappa. A failed gate has a pre-declared response: remove the field, redefine it or retain it only as an oracle, or declare measurement not ready. The thresholds are deliberately set before pilot results. They may be reconsidered only through a versioned amendment and a fresh pilot or an explicitly nonconfirmatory status.

## Boundary

This task does not select actual pairs, run an extractor, annotate an image, or fit an outcome model. Workstream 02 may now begin its outcome-free measurement pilot. The separate rendered-interface leakage audit remains a hard prerequisite for any real v2 outcome-review collection, but it does not block feature-only feasibility work.

## Validation

`scripts/validate_v2_measurement_feasibility_pilot_contract.py` validates the contract at `schemas/pferi_v2/measurement_feasibility_pilot_contract_v1.json`. It rejects directed sampling units, outcome-like manifest fields, confirmation overlap, incomplete difficulty coverage, adaptive retention rules, and missing gates.

```bash
python3 scripts/validate_v2_measurement_feasibility_pilot_contract.py \
  --contract schemas/pferi_v2/measurement_feasibility_pilot_contract_v1.json \
  --audit-json path/to/measurement_feasibility_pilot_contract_audit.json
```
