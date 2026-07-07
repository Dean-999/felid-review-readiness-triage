# Phase19 4x3000 Dataset Source Scout

Date: 2026-07-06

Purpose: scout feasible sources for a 2 x 2 supplemental dataset:

```text
CzechLynx / Lynx-wild
CzechLynx / Lynx-urban-captive-heterogeneous
Bobcat-wild
Bobcat-urban-heterogeneous
```

## Local And API Counts

### Existing Frozen Modeling Data

- `outputs/frozen_modeling_datasets/phase17_strict3000_freeze_20260701/manifests/frozen_modeling_manifest.csv`
- Contains frozen Bobcat and CzechLynx modeling images.
- Existing CzechLynx strict 3000 is the strongest wild known-ID cell.
- Existing Bobcat final 3000 is human-clear but not verified-ID.

### iNaturalist API Counts

Queried via `https://api.inaturalist.org/v1/observations`.

- Bobcat / `Lynx rufus` / taxon_id `41976`
  - photos total: 50,982
  - captive=false: 50,258
  - captive=true: 724
  - research_grade: 43,453
  - organism_alive annotation query: 6,115
- Eurasian lynx / `Lynx lynx` / taxon_id `41979`
  - photos total: 1,717
  - captive=false: 1,266
  - captive=true: 451
  - research_grade: 965
  - organism_alive annotation query: 312

Interpretation: iNaturalist can support Bobcat-urban/heterogeneous at scale, but
cannot alone support a 3,000-image Eurasian lynx heterogeneous cell.

### GBIF Occurrence API Counts

Queried via `https://api.gbif.org/v1/species/match` and
`https://api.gbif.org/v1/occurrence/search?media_type=StillImage`.

- `Lynx lynx`: GBIF usageKey `2435240`, StillImage occurrence count `1,484`.
- `Lynx rufus`: GBIF usageKey `2435246`, StillImage occurrence count `33,816`.

Interpretation: GBIF supports Bobcat media at scale; Eurasian lynx media remains
below 3,000 unless additional non-GBIF sources are used.

## LILA / Camera-Trap Sources

### Felidae Conservation Fund 2020-2025

Official LILA page: `https://lila.science/datasets/felidae-conservation-fund`

Key page facts:

- 357k+ images across 216 camera traps in the San Francisco Bay Area and
  surroundings.
- Collected for Bay Area Puma Project and Bay Area Bobcat Project.
- Bobcat is one of the common labels; LILA page reports 11,764 bobcat images.
- Released under Community Data License Agreement, permissive variant.

Local project prefilter:

- `outputs/phase14/phase14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_all_passed.csv`
- Rows: 6,412 high-evidence Bobcat candidates.
- Summary JSON reports 31,278 Bobcat manifest rows and 6,412 high-evidence
  passed rows.

Recommended use: primary Bobcat-wild / wildland-edge camera-trap source.

### Caltech Camera Traps

Official LILA page: `https://lila.science/datasets/caltech-camera-traps/`

Parsed local metadata:

- 243,100 images.
- 8,098 bobcat annotations.

Recommended use: strong Bobcat-wild camera-trap supplement or replacement source
if FCF source-context is considered too urban-wildland-edge.

### WSU Lynx

Official LILA page: `https://lila.science/datasets/wsu-lynx/`

Key page facts:

- 1,205,453 images from 637 Washington locations.
- Camera traps on public lands, roads and hiking trails, unbaited, roughly 60 cm
  height, June-Oct 2016-2017.
- Released under Community Data License Agreement, permissive variant.

Parsed local metadata:

- `lynx rufus`: 5,629 annotations.
- `lynx canadensis`: 555 annotations.

Recommended use: useful North American wild-felid transfer stress source, but
not a CzechLynx / Eurasian lynx replacement.

### Seattle(ish) Camera Traps

Official LILA page: `https://lila.science/datasets/seattleish-camera-traps/`

Key page facts:

- About 20k images and 4.5k videos from a yard in the Seattle area.
- Specifically intended to fill consumer-grade / human-near camera-trap gaps.
- Released under Community Data License Agreement, permissive variant.

Parsed local metadata:

- Bobcat annotations: 36.

Recommended use: urban/consumer-grade stress examples only; not enough for a
3,000-image Bobcat-urban cell.

### NACTI

Official LILA page: `https://lila.science/datasets/nacti/`

Key page facts:

- 3.7M camera-trap images from five U.S. locations.
- Labels for 28 animal categories.
- Released under Community Data License Agreement, permissive variant.

Recommended use: possible wild camera-trap source after species-count parsing.

## Feasibility Decision

Recommended practical 4-cell naming:

```text
lynx_wild_known_id_core
lynx_heterogeneous_external_supplement
bobcat_wild_camera_trap
bobcat_urban_heterogeneous
```

Do not call the second cell `CzechLynx-urban` unless the images are actually
from the CzechLynx dataset or from the Czech urban/captive context. Most feasible
external images are better described as `Lynx lynx heterogeneous/captive/external`.

Current feasibility:

- `lynx_wild_known_id_core`: feasible now from existing CzechLynx strict 3000.
- `bobcat_wild_camera_trap`: feasible now from FCF and/or Caltech.
- `bobcat_urban_heterogeneous`: feasible from iNaturalist/GBIF plus urban-proxy
  classification and strict manual clarity gate.
- `lynx_heterogeneous_external_supplement`: not feasible at 3,000 from iNat/GBIF
  alone; requires broader source search, partner datasets, zoo/captive sources,
  or a lower target count with explicit imbalance.

