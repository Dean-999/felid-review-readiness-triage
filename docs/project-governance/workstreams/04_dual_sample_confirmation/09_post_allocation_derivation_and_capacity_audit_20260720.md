# Outcome-free derivation and post-allocation capacity audit

Status: **PASS for frame derivation and capacity; formal selection remains unauthorized.**
Date: 20 July 2026
Outcome access: none
Formal pair selection performed: no

## Decision

The accepted post-allocation derivation rules were applied to the complete frozen within-role frame. All immutable file and ZIP-member hashes matched the accepted contract. The frame, execution linkage, and merged canonical measurements joined one-to-one to 28,295 canonical unordered pairs. The resulting restricted master contains 9,445 development, 9,433 calibration, and 9,417 confirmation pairs. No pair crossed its frozen image-allocation role, no endpoint was absent, and no reviewer, identity, outcome, packet, or selection field was introduced.

The accepted collection totals are feasible without merging, relabelling, or deleting cells. The exact preselection quotas sum to 445 development, 445 calibration, and 889 deployment-confirmation pairs. After any immutable 889-pair deployment draw, 8,528 confirmation pairs necessarily remain, which exceeds the 445-pair mechanism target. This is a capacity result, not a selected sample.

## Scientific derivation checks

All numeric percentiles use the accepted empirical midrank formula. Equal numeric values retain one percentile; IDs never break scientific ties. This matters for native pixel count, where 2,033 image rows occur in ties, and for local correspondence, where large zero-coverage ties occur. The output retains 1,266 finite zero local-coverage measurements as observed values: 416 development, 407 calibration, and 443 confirmation pairs. Their within-role percentile is positive because all equal zero values share their midrank. They are not treated as missing.

The eleven frozen scientific local-matcher failures are also retained rather than discarded: two occur in development and nine in confirmation. Calibration contains none. Development assigns the two failures to two nonempty `measurement_failure` cells, each with capacity one and planned quota one. This is the consequence of the accepted balanced water-filling rule; it is not evidence that the matcher is universally applicable or that those failures are representative of queue prevalence.

Descriptor scores were canonicalized as the maximum retained directional membership score for each descriptor. An additional hard validation proves that every `both`, `megadescriptor_only`, and `dinov2_only` frame declaration matches the descriptors actually present. Descriptor percentiles are computed separately by descriptor and frozen analytical role. Raw scores from different descriptor models are never directly compared.

The development rule produces 20 nonempty cells rather than the theoretical maximum of 27: 18 retrieval-stratum-by-valid-evidence cells and two observed measurement-failure cells. The development frame contains 7,031 evidence-stress, 2,412 ordinary, and two measurement-failure pairs. The large stress fraction is mechanically plausible under the frozen union rule because stress can be triggered by any endpoint quality metric, local correspondence, or dual-descriptor disagreement. It must not be interpreted as a biological prevalence estimate.

Calibration and deployment each retain all nine common retrieval strata. Their smallest cell capacities are 138 and 126, respectively, well above their assigned Hamilton quotas. No capacity-driven cell merge or quota truncation occurred.

## Sequential mechanism boundary

The exact mechanism challenge cells cannot be computed honestly at this stage. The accepted design defines them on the confirmation frame remaining **after** the 889 deployment pairs are immutable, and the dual-descriptor disagreement top quintile must be recalculated on that remainder. Computing exact mechanism cells now would either use the wrong denominator or covertly perform the deployment selection during a nominal capacity audit.

Accordingly, this audit freezes only the guaranteed post-deployment total capacity of 8,528 and the mechanism target of 445. The later formal sampler must first freeze the deployment draw, remove exactly those canonical pair IDs, recompute the mechanism hierarchy and its disagreement percentile on the remainder, perform the exact water-filled mechanism allocation, and then stop if any cell or overlap invariant fails.

## Artifacts

The builder is `scripts/build_v2_post_allocation_sampling_frame.py`; its regression tests are in `tests/test_build_v2_post_allocation_sampling_frame.py`. The restricted generated artifacts are stored under `archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1/`:

- `restricted_outcome_free_master_derivation_frame.csv`
- `immutable_input_hash_audit.json`
- `join_cardinality_audit.json`
- `percentile_and_tie_audit.json`
- `role_by_cell_capacity.csv`
- `planned_allocation_quotas.csv`
- `post_allocation_capacity_audit.json`
- `CHECKSUMS.sha256`

Nine focused tests pass for midrank ties, nonfinite rejection, capacity-safe Hamilton allocation, near-equal water filling, insufficient-capacity failure, descriptor-support consistency, failure precedence, prohibited schema fields, and deterministic namespaced HMAC derivation. A fresh real-frame rebuild also returned PASS with 28,295 rows.

## Authorization boundary and next gate

This PASS closes the outcome-free derivation and preselection capacity gate only. It does not validate identity accuracy, PF-ERI predictive utility, reviewer reliability, or biological generalization. It does not authorize a reviewer packet or outcome collection. The next proposed task is a separately tested, atomic formal sampling utility that applies the already frozen HMAC order exactly once, records inclusion probabilities and sample degrees, freezes deployment before deriving mechanism cells, proves zero pair overlap, and emits a restricted selection audit. It must remain unexecuted until the project owner explicitly authorizes the formal draw.
