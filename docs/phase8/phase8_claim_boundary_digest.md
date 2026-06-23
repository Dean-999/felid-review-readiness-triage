# Phase 8 Claim Boundary Digest

Date: 2026-06-17

Purpose: provide the current Phase 8 claim boundary in one place.

## Supported Claim

Use this claim:

```text
PF-ERI is a CzechLynx-tested evidence-control and review-prioritization framework for patterned-felid Re-ID review. It reduced false-candidate review burden under held-out query-level evaluation, but current evidence does not support robust fixed-descriptor Re-ID accuracy improvement beyond repeated random same-size controls.
```

## Unsupported Claims

Do not claim:

- PF-ERI robustly improves fixed-descriptor mAP;
- PF-ERI is a new Re-ID model;
- PF-ERI identifies true individuals;
- PF-ERI is validated across felids;
- PF-ERI is validated for Mainland Clouded Leopard or Marbled Cat;
- PF-ERI is ready for field deployment;
- PF-ERI supports population estimation.

## Policy Interpretation

`candidate_f`:

```text
main review-control reference that preserves coverage and positive retention.
```

`v4_0636`:

```text
operational refinement that lowers false-candidate burden with lower retention and coverage.
```

Strict PF-ERI references and expected-utility variants:

```text
sensitivity layers, not final identity policies.
```

## Link To Current Direction

Phase 8 should now be read as evidence that image-level hard selection is not enough. The next defensible algorithmic target is:

```text
pair-level admissibility + descriptor-evidence conflict + reliability-aware learning
```

This is the Phase 12 direction.
