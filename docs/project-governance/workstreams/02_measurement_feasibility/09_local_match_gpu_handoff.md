# Local-Match GPU Handoff

The local-match feasibility input is an opaque, outcome-free package containing
160 pair executions and 305 byte-verified images. It must be paired with the
separate Kaggle execution package
`v2_local_match_kaggle_package.zip`. The execution package contains code only;
the input ZIP contains `pair_execution_manifest.csv` and an `images/`
directory; no restricted linkage file is included.

## Required Kaggle sequence

1. Upload the execution ZIP and the opaque input ZIP as two separate Kaggle
   Datasets. Enable Internet and a GPU.
2. Open `PF_ERI_v2_local_matcher_kaggle.ipynb` from the execution package.
3. Run the installation cell, then run `freeze` exactly once. Confirm that
   `matcher_freeze_record.json` exists before the input ZIP is opened. It
   records the code, environment and downloaded model-weight SHA256 values.
4. Run the `run` cell exactly once. It writes exactly 320 directional records
   (A→B and B→A for each of the 160 opaque pair IDs) and 160 canonical records.
5. Download `local_match_run_output.zip` unchanged. Do not inspect pairs to
   tune parameters, edit any CSV, replace weights, retry failures under altered
   settings, or manually rescue a value.

The canonical coverage is the fixed minimum of two valid directional coverage
values. A directional failure is non-numeric and distinct from zero.

For every `pair_execution_id`, run the frozen local matcher twice: left asset
to right asset and right asset to left asset. Preserve both raw directional
measurements, runtime, extractor version, model-weight checksum, preprocessing,
environment, failures, and the canonical symmetric coverage result. Do not
inspect or use a descriptor score, rank, identity, route, review outcome, or
manual correction.

The subsequent audit will require at least 80% valid output, ten distinct valid
coverage values, zero endpoint-order disagreements, zero manual rescues, and a
95th-percentile runtime no greater than 60 seconds per pair. A missing or
failed match is a recorded failure, never a zero coverage value.
