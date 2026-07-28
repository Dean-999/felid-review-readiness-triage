# Contributing

Use Python 3.11 or newer and initialize the managed environment with `uv sync --all-groups`.

Before committing, run `uv run pre-commit run --all-files` and the relevant tests. The CI workflow runs `python -m compileall` and `pytest` for every pull request.

Commit source code, tests, schemas, documentation, compact publication displays, manifests, hashes, and audit summaries. Do not commit raw photographs, reviewer responses, restricted identity/linkage mappings, model weights, embeddings, posterior draws, ZIP deliveries, or temporary execution outputs. Keep those materials in the local evidence boundary and record their provenance with manifests and checksums.

Each pull request should have one purpose. Use a new branch from current `main`, use a descriptive title, and update the nearest iteration-history README when an experiment changes.
