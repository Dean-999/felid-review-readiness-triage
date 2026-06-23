# FCF Bobcat Human Review Rubric

Date: 2026-06-18

## Purpose

This rubric is for auditing the Phase 14 FCF/LILA bobcat 400-image review batch.

The labels are image-level evidence-readiness labels, not individual-ID labels. They estimate whether an image contains usable bobcat identity evidence for later PF-ERI stress testing.

## Core Rule

Do not ask whether the image is a good wildlife photo.

Ask:

```text
Does this image contain enough visible bobcat identity evidence to support individual-level Re-ID review or pairwise comparison?
```

## Columns and Allowed Values

### `human_pattern_visibility`

Allowed values:

```text
high
medium
low
none
uncertain
```

Use:

- `high`: flank/body markings or coat texture are clearly visible.
- `medium`: some markings or texture visible, but limited by distance, lighting, angle, or partial body.
- `low`: bobcat visible but identity-relevant markings are weak.
- `none`: no useful coat-pattern evidence.
- `uncertain`: reviewer cannot decide.

### `human_side_flank_visibility`

Allowed values:

```text
left
right
both
frontal
rear
unknown
```

Use:

- `left`, `right`, `both`: side/flank view supports pair comparison.
- `frontal` or `rear`: weaker for patterned-felid Re-ID unless other evidence is strong.
- `unknown`: body orientation cannot be judged.

### `human_body_visibility`

Allowed values:

```text
76_100
51_75
26_50
0_25
unknown
```

Use approximate visible body fraction. If only head, tail, or a small partial body is visible, use `0_25` or `26_50`.

### `human_blur_level`

Allowed values:

```text
none
mild
moderate
severe
unknown
```

Use:

- `none`: fine details are sharp.
- `mild`: animal is usable but detail is softened.
- `moderate`: identity evidence is meaningfully degraded.
- `severe`: markings/body evidence cannot be trusted.

### `human_occlusion_level`

Allowed values:

```text
none
partial
major
unknown
```

Use:

- `none`: animal is not blocked.
- `partial`: vegetation/object blocks some body but comparison may remain possible.
- `major`: key identity regions are blocked.

### `human_background_complexity`

Allowed values:

```text
low
medium
high
unknown
```

Use:

- `low`: clean background, animal easy to separate.
- `medium`: some vegetation/shadow/texture.
- `high`: cluttered background, hard separation, many edges or occluders.

### `human_modified_background`

Allowed values:

```text
yes
no
uncertain
```

Use `yes` for visible roads, fences, buildings, artificial lights, human structures, vehicles, pavement, or other built-environment cues.

### `human_review_bucket`

Allowed values:

```text
review_ready
review_limited
species_level_only
non_comparable
uncertain
```

Use:

- `review_ready`: clear enough for individual-level review or candidate pair comparison.
- `review_limited`: contains some identity evidence but should be reviewed cautiously.
- `species_level_only`: adequate for species presence, not individual Re-ID.
- `non_comparable`: cannot support pair comparison because of view, visibility, or image failure.
- `uncertain`: reviewer cannot decide without another image or expert review.

### `human_review_confidence`

Allowed values:

```text
high
medium
low
```

Use:

- `high`: label is straightforward.
- `medium`: label is probably correct but one limitation matters.
- `low`: difficult or ambiguous; should be manually checked.

### `human_notes`

Free text. Keep short. Use it for visible uncertainty such as:

```text
night_ir; weak_center_signal; likely_partial_body; cluttered_background; possible_exposure_issue; side_unclear
```

## Review Priority

The most important rows for manual checking are:

1. machine label says `likely_review_ready` but pattern or side evidence appears weak;
2. machine label says `likely_species_level_only` but the bobcat is actually clear;
3. night/IR images;
4. strong background clutter or vegetation occlusion;
5. any image with `human_review_confidence = low`.

## Claim Boundary

These labels can support:

```text
urban/peri-urban bobcat evidence-readiness and PF-ERI stress testing
```

They cannot support:

```text
individual bobcat identity validation
population estimation
urbanization causality
```
