# Pair Construction

Status: `PASS`

This module builds the first pair-level tables for the PF-ERI Selective
Evidence Sufficiency Model from the final modeling image index.

## Outputs

- CzechLynx known-ID pairs: `outputs/modeling-validation/pair-construction/czechlynx_known_id_pairs.csv`
- Bobcat unlabeled transfer-stress pairs: `outputs/modeling-validation/pair-construction/bobcat_transfer_stress_pairs.csv`
- Unified pair index: `outputs/modeling-validation/pair-construction/pair_construction_index.csv`

## Counts

- Total pair rows: 71695
- CzechLynx pair rows: 17695
- Bobcat pair rows: 54000
- CzechLynx same-ID pairs: 8695
- CzechLynx different-ID pairs: 9000

## Boundary

CzechLynx pairs carry known same/different labels. Bobcat pairs are unlabeled transfer-stress/comparability pairs only and cannot support identity-accuracy claims.
