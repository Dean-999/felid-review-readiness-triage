# Phase 6 Unique-500 v2 Balanced Reset Decision

## Decision

The previous Phase 6 unique-500 image annotation workflow is no longer the active workflow.

It was archived because it over-selected almost-black and extremely low-information images. That made the set too hard-case dominated for PF-ERI factor-to-risk modeling.

## Why Reset Was Necessary

PF-ERI Control needs a balanced evidence-quality distribution:

- clear images for normal evidence behavior;
- medium images for gradual degradation;
- low but annotatable images for degraded evidence;
- a capped number of extreme hard images for defer/exclude modeling.

The previous set was biased toward extreme hard cases. That would make it difficult to estimate how visual evidence quality changes risk across the full useful range of camera-trap evidence.

## Archive

The flawed workflow was archived at:

```text
outputs/czechlynx/phase6/archive/flawed_unique_500_selection_20260613/
```

Raw data and earlier frozen Phase 4 labels were not modified.

## New Active Workflow

The active workflow is now:

```text
phase6_unique_500_v2_balanced
```

Duplicate-reliability work is separate and postponed until this balanced v2 set is stable.
