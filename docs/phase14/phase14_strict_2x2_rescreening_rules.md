# Phase 14 Strict 2x2 Rescreening Rules

Date: 2026-06-19

## Purpose

The first 400-image manual audit showed that the original AI-assisted 2x2 labels are not clean enough for final experiments. The next dataset must be rebuilt with stricter evidence-admission rules.

Target:

```text
>=90% expected correctness for the selected high-confidence and low-evidence stress sets,
pending validation by a second manual audit.
```

This is a precision target, not a claim already proven.

## Global Rules

All four final sets must satisfy:

- image file is readable;
- no duplicate `evidence_image_path`;
- no overlap between high-confidence and low-evidence stress sets within the same dataset;
- selected rows preserve their source path and source pool;
- excluded or middle-review rows are retained in the candidate pool, not silently deleted.

Do not use the old `human_review_bucket` alone as final truth. It is a weak label.

## High-Confidence Re-ID Evidence Rule

A sample is eligible for strict high-confidence evidence only if it satisfies all of:

```text
body_visibility == 76_100
pattern_visibility in {high, medium}
blur_level in {none, mild}
occlusion_level in {none, partial}
auto_prefeature_status == ok
```

Additional priority ordering:

```text
pattern high before medium
blur none before mild
occlusion none before partial
review_ready before review_limited
higher auto_evidence_score before lower
higher auto_quality_score before lower
```

This rule is intentionally stricter than the previous high-confidence selection because the audit showed that `review_ready + high confidence` over-admitted Bobcat images with small, distant, edge-cropped, frontal/rear, or weak-flank evidence.

## Low-Evidence Stress Rule

A sample is eligible for strict low-evidence stress if it is readable and satisfies at least one strong low-evidence condition:

```text
body_visibility in {0_25, 26_50}
or pattern_visibility in {none, low}
or blur_level in {moderate, severe}
or occlusion_level == major
or review_bucket in {species_level_only, uncertain}
```

Priority ordering:

```text
species_level_only / uncertain before review_limited
pattern none / low before medium
body 0_25 / 26_50 before 51_75
blur severe / moderate before mild
occlusion major before partial
lower auto_evidence_score before higher
```

The stress set is not a trash bin. It should contain scientifically useful low-evidence examples that test risk-control behavior.

## Bobcat High-Confidence Rule

Bobcat high-confidence selection uses the global strict high-confidence rule.

Extra caution:

- do not admit small/distant animals only because species is visible;
- do not admit frontal/rear-only images if flank evidence is absent;
- do not admit edge-cropped partial body images as core high evidence;
- prefer side-body visibility, but because side labels are incomplete, body + pattern + blur + occlusion are the primary filter.

Expected from current pool:

```text
current strict candidates are sufficient for 3,000.
```

## Bobcat Low-Evidence Stress Rule

Bobcat low-evidence stress uses the global strict low-evidence rule.

Extra caution:

- remove clear full side-profile images from stress;
- keep species-level-only and review-limited weak-evidence images;
- do not use unreadable/corrupt images as stress evidence.

Expected from current pool:

```text
current strict candidates are sufficient for 3,000.
```

## CzechLynx High-Confidence Rule

CzechLynx high-confidence uses the global strict high-confidence rule and must preserve identity utility:

```text
minimum 2 selected images per included identity where possible
identity-balanced round-robin selection
no singleton identity in final high-confidence set
```

The current 9,000-image CzechLynx candidate pool is not enough for a strict 3,000-image high-confidence set. The pool must be expanded from unused CzechLynx raw images without reusing any current `evidence_image_path`.

## CzechLynx Low-Evidence Stress Rule

CzechLynx low-evidence stress uses the global strict low-evidence rule, but should avoid over-penalizing usable side/body/flank images. If an image has:

```text
body_visibility == 76_100
pattern_visibility in {high, medium}
blur_level in {none, mild}
occlusion_level in {none, partial}
```

then it must not enter the stress set even if the old label was `species_level_only` or low confidence.

Identity utility:

```text
minimum 2 selected images per included identity where possible
identity-balanced round-robin selection
```

Expected from current pool:

```text
current strict candidates are sufficient for 3,000.
```

## Validation Requirement

After rebuilding the four strict 3,000 sets, generate a second manual audit package:

```text
50 images per quadrant, 200 total
```

Only after this second audit should we claim the rebuilt sets approach or exceed 90% correctness.

## Status

These rules supersede the original 2x2 weak-label selection for final experiments.
