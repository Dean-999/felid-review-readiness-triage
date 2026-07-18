# PF-ERI v2: Pair-Level Evidence Admission for Wildlife Re-ID Candidate Review

> Current status: `v2_design_locked`. Historical v1 results are exploratory and are neither confirmatory nor submission-ready.

PF-ERI v2 studies whether a wildlife image pair retrieved by a strong Re-ID descriptor contains enough comparable visual evidence for responsible human individual-level review. Its governing idea is **Similarity is not admissibility.** The project does not build a new descriptor or automatically assign animal identities. It creates an auditable evidence-admission layer that can route a candidate pair to `admit`, `expert_review`, or `defer` after retrieval.

The primary domain is known-identity CzechLynx. The accepted four-stage programme targets 2,000 analyzable unique unordered pairs: 400 development, 400 calibration, 400 mechanism confirmation, and 800 probability-sampled deployment confirmation. At the accepted 0.90 planning completion fraction it prepares 2,224 pairs. Two independent blinded reviewers assess every pair; a third blinded reviewer adjudicates specified disagreements. Feature measurement, outcome review, identity truth, model development, calibration, and final confirmation are deliberately separated. The primary model tests whether automatically available pair-evidence features improve reviewability prediction beyond descriptor similarity and independent image-quality measures.

The historical v1 400-row material remains in the repository for provenance, feature design, and error analysis. It cannot be used for a v2 model-selection, calibration, confirmation, reliability, deployment, or external-validation claim. Bobcat, Mainland Clouded Leopard, and Marbled Cat are future species-adapter studies, not v2 empirical domains.

`PROJECT_RULES.md` is the binding project contract. `docs/CURRENT_PROJECT_MAP.md` gives the current state and navigation. Workbook04 is the active work area; its design is locked, the official image allocation is frozen, and pair sampling/outcome packets remain blocked pending within-role automatic measurements and post-allocation gates. The operational protocol, pre-specified analysis plan, and reviewer instructions are in `paper/protocols/`. Superseded implementations are recorded in `docs/project-governance/SUPERSEDED_IMPLEMENTATIONS.md`.

## Execution environment

Use Python 3.11 or newer; current scripts use `datetime.UTC`, which is unavailable
in the macOS system Python 3.9. A local `.venv` is disposable and is not evidence
of a reproducible environment. The repository does not yet have a dependency
lockfile, so reproduce historical runs from the script, frozen inputs, output
audit/hash records, and the environment details recorded by each execution
package; do not treat an unrecorded local environment as authoritative.
