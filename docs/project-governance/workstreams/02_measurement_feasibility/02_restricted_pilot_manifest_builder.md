# Task 02: Restricted Pilot-Manifest Builder

Status: complete; actual restricted pilot manifest generated and audited.

## Purpose

This task creates the reproducible path from a future frozen v2 candidate reservoir to the 160-pair outcome-free feasibility pilot. It is intentionally unable to consume the existing `czechlynx_known_id_pairs.csv` file. That file is a historical pair-construction output with identity fields, so treating it as a v2 reservoir would violate the separation established in Workstreams 00 and 01.

## Builder Contract

The builder accepts three inputs only: the v2 canonical unordered-pair manifest, the v2 directed candidate-membership manifest, and an image-context manifest containing image identifier, decode status, illumination metadata, and source-camera context. It refuses outcome-like, identity-like, feature-like, route-like, and v1-like fields in the pair source. From eligible, available, decodable pairs it deterministically selects the requested count using the locked seed and round-robin coverage across descriptor membership, retrieval-rank band, and day/infrared context. It writes only a restricted pilot identifier, canonical pair identifier, seed, selection stratum, availability, inclusion status, and exclusion reason.

The output is not reviewer-facing and is not a confirmation manifest. Its pair identifiers must be reserved so later confirmation selection excludes every pilot pair. The builder records candidate exclusions and stratum counts, and it fails rather than silently returning fewer than the requested number of pairs.

## Completed Selection and Boundary

The fresh, dual-descriptor v2 reservoir contains 85,182 canonical pairs. With seed `pferi-v2-pilot-seed-001`, the builder selected 160 eligible unique canonical pairs, recorded at `work/pferi_v2/gpu/measurement_feasibility/restricted_pilot_manifest.csv`, with a PASS audit beside it. The selected pairs are stratified across descriptor membership and retrieval-rank bands; all available context was `day_or_unknown`, so no artificial infrared stratum was created. No pilot measurement or outcome label has been accessed. The historical identity-bearing pair table remains prohibited and was not used.

## Validation

`scripts/build_v2_measurement_feasibility_pilot_manifest.py` has unit coverage for deterministic selection, duplicate prevention, insufficient-pool failure, and rejection of identity-bearing source headers. Once the new v2 inputs exist, run:

```bash
python3 scripts/build_v2_measurement_feasibility_pilot_manifest.py \
  --canonical-pairs path/to/v2_canonical_pairs.csv \
  --candidate-memberships path/to/v2_candidate_memberships.csv \
  --image-context path/to/v2_image_context.csv \
  --seed pferi-v2-pilot-seed-001 \
  --output-csv path/to/restricted_pilot_manifest.csv \
  --audit-json path/to/restricted_pilot_manifest_audit.json
```
