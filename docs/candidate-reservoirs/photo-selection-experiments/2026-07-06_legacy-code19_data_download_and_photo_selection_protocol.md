# legacy-code19 Data Download And Photo Selection Protocol

Date: 2026-07-06

## Purpose

This document records the first operational step for legacy-code19:

```text
download or stage raw candidate image pools
-> score and filter them with strict evidence criteria
-> manually review the highest-quality queue
-> freeze only the final visually admissible images
```

The target legacy-code19 data design is:

```text
core_1: lynx_wild_known_id_core, 3000 images
core_2: bobcat_wild_camera_trap, 3000 images
core_3: bobcat_urban_heterogeneous, 3000 images
auxiliary: lynx_external_heterogeneous_supplement, 500-1500 high-quality images if available
```

Do not force a symmetric `CzechLynx-urban 3000` cell. External Lynx images are
auxiliary sensitivity unless a true audited CzechLynx urban/captive source
exists.

## Download Sources

### 1. CzechLynx Wild Known-ID Core

Status: already available locally.

Use:

```text
outputs/frozen_modeling_datasets/legacy-code17_strict3000_freeze_20260701/manifests/czechlynx_frozen_manifest.csv
outputs/czechlynx/legacy-code17_strict3000_supplement/augmented/legacy-code17_czechlynx_strict3000_augmented_manifest.csv
```

Role:

```text
primary known-ID wild lynx validation core
```

Do not replace this with external Lynx images. Its value is that it is strict,
wild, known-ID, and already human-reviewed.

### 2. Bobcat Wild Camera-Trap Core

Primary source:

- LILA Felidae Conservation Fund 2020-2025:
  `https://lila.science/datasets/felidae-conservation-fund/`

Direct metadata and image roots:

```text
metadata:
https://storage.googleapis.com/public-datasets-lila/felidae-conservation-fund/felidae_conservation_fund_2020_2025.zip

image base:
https://storage.googleapis.com/public-datasets-lila/felidae-conservation-fund

MegaDetector/RDE filtered detections:
https://lila.science/public/lila-md-results/wildepod-2026-02-16-v5a.0.1_detections.filtered.json.zip
```

Local existing prefilter:

```text
outputs/legacy-code14/legacy-code14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_all_passed.csv
```

Current count evidence:

```text
local FCF high-evidence Bobcat candidates: 6412
LILA page reported Bobcat images: 11764
```

Secondary source:

- LILA Caltech Camera Traps:
  `https://lila.science/datasets/caltech-camera-traps/`

Direct metadata and image roots:

```text
metadata:
https://storage.googleapis.com/public-datasets-lila/caltechcameratraps/labels/caltech_camera_traps.json.zip

image base:
https://storage.googleapis.com/public-datasets-lila/caltech-unzipped/cct_images

MegaDetector/RDE filtered detections:
https://lila.science/public/lila-md-results/caltech-camera-traps_mdv5a.0.0_results.filtered_rde_0.150_0.850_10_0.300.json.zip
```

Current count evidence:

```text
parsed Bobcat annotations: 8098
```

Use Caltech if the Felidae Conservation Fund queue does not provide 3000 strict
clear images after manual review, or if a second independent wild camera-trap
source is needed.

### 3. Bobcat Urban/Heterogeneous Core

Primary source:

- iNaturalist Bobcat taxon page:
  `https://www.inaturalist.org/taxa/41976-Lynx-rufus`
- iNaturalist API documentation:
  `https://api.inaturalist.org/v1/docs/`

Useful API starting points:

```text
all Bobcat observations with photos:
https://api.inaturalist.org/v1/observations?taxon_id=41976&photos=true

research-grade Bobcat observations with photos:
https://api.inaturalist.org/v1/observations?taxon_id=41976&photos=true&quality_grade=research

wild/not-captive Bobcat observations with photos:
https://api.inaturalist.org/v1/observations?taxon_id=41976&photos=true&captive=false
```

Current count evidence:

```text
iNaturalist Bobcat photos: 50982
iNaturalist Bobcat research-grade photos: 43453
iNaturalist Bobcat captive/cultivated photos: 724
```

Secondary source:

- GBIF `Lynx rufus` species page:
  `https://www.gbif.org/species/2435246`
- GBIF occurrence API:
  `https://techdocs.gbif.org/en/openapi/v1/occurrence`

Useful API starting point:

```text
https://api.gbif.org/v1/occurrence/search?taxon_key=2435246&media_type=StillImage
```

Current count evidence:

```text
GBIF Lynx rufus StillImage occurrences: 33816
GBIF Lynx rufus human-observation StillImage occurrences: 31620
```

Important boundary:

```text
Urban/heterogeneous is not a native iNaturalist or GBIF truth label.
It must be derived from source platform, place metadata, coordinate context,
human-near visual context, and manual audit.
```

### 4. Auxiliary External Lynx Heterogeneity Panel

This panel is optional sensitivity, not a main core cell.

Primary exploratory sources:

- iNaturalist Eurasian lynx taxon page:
  `https://www.inaturalist.org/taxa/41979-Lynx-lynx`
- GBIF `Lynx lynx` species page:
  `https://www.gbif.org/species/2435240`
- GBIF `Lynx lynx` StillImage API:
  `https://api.gbif.org/v1/occurrence/search?taxon_key=2435240&media_type=StillImage`
- Wikimedia Commons `Lynx lynx in zoos`:
  `https://commons.wikimedia.org/wiki/Category:Lynx_lynx_in_zoos`

Current count evidence:

```text
iNaturalist Lynx lynx photos: 1717
iNaturalist Lynx lynx research-grade photos: 965
iNaturalist Lynx lynx captive/cultivated photos: 451
GBIF Lynx lynx StillImage occurrences: 1484
Wikimedia Commons Lynx lynx in zoos direct files: 146
```

Boundary:

```text
Do not call this CzechLynx-urban.
Call it lynx_external_heterogeneous_supplement.
Use it only as auxiliary sensitivity unless a true audited CzechLynx
urban/captive source becomes available.
```

## Photo Selection Standard

The final selected images must be visually useful for individual-level evidence
review. The rule is stricter than species presence.

### Accept

Accept only if all of these are true:

```text
the target animal is alive and visible
the image is decodable and not corrupted
the animal itself is sharp enough for pattern/body comparison
the visible body/pattern evidence is sufficient for individual review
the animal is not only a track, scat, sign, skeleton, dead animal, or drawing
the image is not dominated by severe motion blur, severe low light, or mosaic artifacts
the body is not so partial that pairwise comparison would be unfair
the animal is not tiny/far unless the crop/augmentation still preserves clear pattern evidence
```

### Reject

Reject if any of these are true:

```text
track, scat, sign-only, skeleton, dead animal, toy, drawing, or non-photo
wrong species or uncertain species
severe blur on the animal even if background is sharp
night image where the animal is smeared or pattern is unreadable
subject too small to compare markings
severe occlusion or only a small body fragment
head-only image unless the study explicitly needs face/head evidence
edge-truncated body where important identity evidence is missing
duplicate or near-duplicate that does not add evidence diversity
license/provenance not usable
```

### Subject Size Rule

Preferred:

```text
animal occupies at least 30-40% of the image area or crop area
```

Allowed with caution:

```text
20-30% area if the animal is genuinely sharp, mostly complete, and visible
pattern/body evidence remains clear after mild readability augmentation
```

Reject:

```text
below 20% area unless a high-quality crop has clear identity evidence
```

The final decision is based on visible evidence, not only measured area.

### Partial Body Rule

Partial body is allowed only if the remaining visible body includes enough
pattern/shape evidence for pairwise comparison.

Reject partial-body images when:

```text
only legs, tail, rear point, head, or small torso fragment is visible
the flank/pattern region is mostly missing
edge contact removes the main comparable region
occlusion prevents fair pair comparison
```

### Night / Motion Rule

Night images are not automatically rejected. They are accepted only if the animal
itself is sharp and comparable.

Reject when:

```text
the animal is motion-smeared
the body pattern is washed out by IR or glare
the image has strong noise/mosaic artifacts
the background is clear but the animal is blurred
```

### Augmentation Rule

Readability augmentation is allowed only after the original is already
scientifically usable.

Allowed:

```text
mild full-frame or crop readability enhancement
contrast/sharpness adjustment
unsharp mask
JPEG quality preservation
```

Forbidden:

```text
hallucinating missing pattern
AI restoration that invents markings
using augmented image as source of truth
converting an unusable original into an apparently usable image
```

The original image remains the evidence source of truth.

## Selection Workflow

### Step 1: Build Raw Candidate Pool

For each source, download or stage metadata first, not all images blindly.

Required raw fields:

```text
source_dataset
source_platform
source_observation_id
source_photo_id
image_uri
license
attribution
species/taxon label
capture datetime if available
location or place proxy if available
source context: camera_trap / iNaturalist / GBIF / zoo / unknown
```

### Step 2: Automated Source Filter

Keep only rows satisfying:

```text
species/taxon is target species
photo exists
license/provenance is usable or auditable
not known track/scat/sign/dead-only evidence
not captive if building a wild camera-trap cell
source context matches intended cell
```

### Step 3: Automated Visual Pre-Score

Score but do not blindly trust:

```text
decode_status
image_width / image_height
detector confidence
subject area fraction
subject width/height fraction
edge contact count
blur/sharpness proxy
contrast proxy
night/low-light proxy
partial body risk
duplicate/near-duplicate key
```

The goal is to rank a review queue, not to replace human judgment.

### Step 4: Strict Human Gate

Use a Streamlit yes/no review interface with these decisions:

```text
clear_accept
reject_blur_or_motion
reject_too_small
reject_partial_or_occluded
reject_wrong_or_uncertain_species
reject_dead_track_scat_sign
reject_duplicate
reject_license_or_provenance
uncertain_review_later
```

Human review standard:

```text
When uncertain, reject from the clean 3000.
Uncertain images can be saved for stress tests, not clean algorithm entry.
```

### Step 5: Build Final 3000

Rank accepted rows by:

```text
human clear decision
animal clarity
visible pattern/body evidence
subject area and completeness
source diversity
location/observation diversity
license/provenance confidence
duplicate removal
```

Freeze only after:

```text
3000 accepted rows exist
all files download or copy successfully
all images decode successfully
checksums are written
manifest row count is verified
audit JSON reports PASS
```

### Step 6: Record Non-Selected Images

Rejected images are still scientifically useful.

Use them for:

```text
low-evidence stress tests
source-diagnosis
transfer-risk analysis
review burden analysis
failure examples
```

Do not silently mix them into the clean 3000.

## Cell-Specific Download Priorities

### Bobcat Wild Camera-Trap

Priority:

```text
1. Felidae Conservation Fund high-evidence local prefilter
2. Caltech Camera Traps Bobcat annotations
3. WSU Lynx `lynx rufus` annotations if extra wild diversity is needed
```

Target raw pool:

```text
at least 5000-8000 candidates before manual gate
```

Expected final:

```text
3000 strict clear images feasible
```

### Bobcat Urban/Heterogeneous

Priority:

```text
1. iNaturalist research-grade Bobcat photos
2. iNaturalist non-research but high-quality photo rows if needed
3. GBIF StillImage human observations as supplement
```

Target raw pool:

```text
at least 8000-12000 candidates before manual gate
```

Extra metadata needed:

```text
place_guess
latitude/longitude if available
observed_on
license
attribution
captive flag
urban/periurban proxy
```

Expected final:

```text
3000 strict clear images feasible, but urban label must be audited as a proxy
```

### Lynx External Heterogeneity Auxiliary

Priority:

```text
1. iNaturalist Lynx lynx photos
2. GBIF Lynx lynx StillImage occurrences
3. Wikimedia Commons zoo/captive Lynx lynx images
```

Target:

```text
500-1500 strict clear images, not forced to 3000
```

Expected final:

```text
auxiliary sensitivity panel only
```

## Reporting Language

Allowed:

```text
The final selected images are strict visual-evidence candidates for PF-ERI
evidence-risk modeling and review-readiness analysis.
```

Forbidden:

```text
These images prove Bobcat identity accuracy.
These images create a balanced CzechLynx urban cell.
External Lynx images are equivalent to CzechLynx.
Downloaded research-grade/camera-trap labels alone guarantee individual-review usability.
```

## Source Links

- LILA datasets: `https://lila.science/datasets/`
- LILA Felidae Conservation Fund: `https://lila.science/datasets/felidae-conservation-fund/`
- LILA Caltech Camera Traps: `https://lila.science/datasets/caltech-camera-traps/`
- LILA WSU Lynx: `https://lila.science/datasets/wsu-lynx/`
- iNaturalist API docs: `https://api.inaturalist.org/v1/docs/`
- iNaturalist Bobcat: `https://www.inaturalist.org/taxa/41976-Lynx-rufus`
- iNaturalist Eurasian lynx: `https://www.inaturalist.org/taxa/41979-Lynx-lynx`
- GBIF Occurrence API: `https://techdocs.gbif.org/en/openapi/v1/occurrence`
- GBIF Bobcat / Lynx rufus: `https://www.gbif.org/species/2435246`
- GBIF Eurasian lynx / Lynx lynx: `https://www.gbif.org/species/2435240`
- Wikimedia Commons Lynx lynx in zoos:
  `https://commons.wikimedia.org/wiki/Category:Lynx_lynx_in_zoos`

