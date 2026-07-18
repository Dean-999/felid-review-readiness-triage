# Task 01: Power-and-Cost Input Audit and Simulation Contract

Status: complete — the input boundary is auditable; numerical simulation is deliberately blocked pending pre-outcome decisions.  
Workstream: 04 — Dual-Sample Confirmatory Design.

## Question

Before choosing an official v2 target, can PF-ERI honestly state the inputs that a power-and-cost simulation needs? This task is not a disguised sample-size calculation. It identifies which facts are already known outcome-free, which historical quantities may be used only as sensitivity context, and which choices must be made before anyone sees a v2 reviewability outcome.

## What is known without v2 outcomes

The frozen candidate reservoir contains 85,182 eligible canonical unordered pairs across 3,000 images. Its image-pair graph has one connected component and substantial shared-image dependence; the previously measured image degree range is 24–183. This supports a graph-aware simulation and rules out treating 1,200 pairs as independent rows.

The outcome-free measurement pilot supports operational feasibility for the retained automatic features. Local-match coverage was valid for all 160 pilot pairs with pair-runtime p95 1.659 seconds. Native pixels, sharpness, and channel-extreme clipping were complete on the 305 pilot images; the failed animal-coverage proxy is excluded from the primary automatic set. These facts do **not** establish the missingness or reviewer-completion rate of future outcome collection.

Historical v1 broad reviewer summaries report majority `review_ready` rates around 0.69–0.70, while targeted v1 packets were around 0.85–0.88. Their different selection mechanisms make them useful only as a range for outcome-free sensitivity scenarios. They are not a v2 prevalence estimate, expected model effect, calibration target, or source of a Brier-score threshold.

## Frozen boundary for the next calculation

`schemas/pferi_v2/power_cost_simulation_input_contract_v1.json` fixes the direction of the primary estimand as:

```text
Brier(active control) − Brier(full automatic-evidence model)
```

Thus a positive increment favors the full model. The contract does **not** freeze the minimum practical increment or claim that the v1 pooled Brier difference is an expected v2 effect. It also requires graph-aware uncertainty and prohibits treating descriptor directions or shared images as independent observations.

The contract and audit intentionally leave the following unresolved until a pre-outcome project decision is documented:

- practical Brier increment and superiority/noninferiority rule;
- deployment-prevalence sensitivity scenarios and rationale;
- graph-dependence simulation and final resampling rule;
- outcome nonresponse, invalid response, technical-failure, and adjudication reserve;
- independent first-pass and adjudication roles, pair-level conflict restrictions, and fields for reporting actual elapsed time after execution; no expected review duration or collection window is required by the current experimental design;
- one principal transparent budget/cost region and relative action losses.

Reviewer time is not a pre-outcome design input. The protocol neither assumes zero time nor invents an expected duration, total-hour budget, or collection window. Instead, immutable operational logs will record actual elapsed time, disagreement, and adjudication during execution, and those observed quantities will be reported descriptively after collection. They cannot be used as model inputs or to weaken the planned review standard.

## Artifact and interpretation

Run:

```bash
/Users/dshen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/audit_ws04_power_cost_inputs.py
```

The archived output is `outputs/pferi_v2/dual_sample_confirmation/2026-07-14_power_cost_input_audit_v1/power_cost_input_audit.json`. Its status is deliberately `BLOCKED_PENDING_PRE_OUTCOME_DECISIONS`, not PASS or FAIL. This is the correct result: it confirms provenance and shows exactly why selecting a target or seed now would be scientifically arbitrary.

After the required input decisions are accepted, the next task may run a dated, versioned sensitivity simulation. Only that later artifact may recommend retaining, increasing, or reducing the default 400 mechanism plus 800 deployment-pair target. It must still not generate reviewer packets or allow outcome collection until all later Workstream 04 artifacts are frozen.
