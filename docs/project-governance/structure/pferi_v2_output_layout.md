# PF-ERI v2 result layout

`outputs/pferi_v2/` is the compact authoritative-result surface. Names use
scientific function rather than a date or `_vN` suffix. Every new output must
be placed under the existing measurement, partition, review, or model function
that it serves.

`work/pferi_v2/` holds reconstructable execution material. GPU and ModelScope
packages, descriptor runs, local smoke runs, and temporary execution outputs
belong under `work/pferi_v2/gpu/`.

`artifacts/transfers/pferi_v2/` holds reviewer, browser-audit, and external
handoff packages. Delivery ZIPs are not scientific result directories.

`archive/pferi_v2/` holds historical task runs and superseded evidence. It
preserves dated and versioned names for provenance, including the superseded
Task15M external-confirmation analysis.
