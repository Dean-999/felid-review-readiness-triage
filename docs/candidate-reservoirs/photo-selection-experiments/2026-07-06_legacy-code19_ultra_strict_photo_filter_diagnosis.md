# legacy-code19 Ultra-Strict Photo Filter Diagnosis

Date: 2026-07-06

## Trigger

Human spot review found that the previous strict sample still contained too many
motion-blurred and night/low-visibility images. The filter was therefore
upgraded from `strict` to `ultra-strict`.

## Added Hard Exclusions

The updated filter now rejects or demotes images with:

- low minimum dimension below 850 px;
- low megapixels below 0.90 MP;
- file size below 140 KB;
- contrast below the ultra threshold;
- weak edge strength;
- low Laplacian sharpness proxy;
- low entropy;
- heavy shadow/highlight clipping;
- too-dark/night-like exposure;
- washed-out over-bright exposure;
- low-color / likely IR-night appearance.

These exclusions are meant to remove images where the scene may be visible but
the animal itself is not evidence-comparable.

## New Strict-Gated Counts

After the ultra-strict gate:

- `bobcat_wild_camera_trap`: 1,831 strict candidates; shortfall to 3,000 = 1,169.
- `bobcat_urban_heterogeneous`: 198 strict candidates; shortfall to 3,000 = 2,802.
- `lynx_external_heterogeneous_supplement`: 255 strict candidates; shortfall to 3,000 = 2,745.

Therefore, the current downloaded candidate pools cannot honestly produce three
ultra-strict 3,000-image sets. Lowering the filter would reintroduce the exact
motion blur/night-visibility problem found by human review.

## Current Validation App

The regenerated 300-image validation sample is served at:

`http://127.0.0.1:8503`

Working file:

`outputs/legacy-code19/legacy-code19_ultra_strict_top3000_validation_review/legacy-code19_strict_photo_review_working.csv`

## Decision Rule

If the ultra-strict sample is acceptable, then:

- freeze only the available ultra-strict candidates for now;
- do not claim 3,000 per cell for these three cells;
- collect additional high-quality sources or targeted daytime/high-resolution
  candidates before attempting a 3,000-per-cell freeze.

If the ultra-strict sample is still poor, the next fix must be object-aware
filtering or manual pre-selection, not further threshold-only tuning.
