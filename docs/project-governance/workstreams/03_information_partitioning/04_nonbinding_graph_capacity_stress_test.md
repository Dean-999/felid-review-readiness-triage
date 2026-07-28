# Task 04: Nonbinding Graph-Capacity Stress Test

Status: complete — outcome-free graph-capacity feasibility PASS.
Workstream: 03 — Development, Calibration, and Confirmation Partitioning.

## Purpose

The candidate graph is a single connected component, so a whole-component split is impossible. This task asks a narrower question: if images are placed into disjoint temporary roles, does the induced within-role graph retain enough canonical pairs to make a later development, calibration, and confirmation design possible? The task is deliberately a feasibility stress test rather than a split generator. It does not identify the best allocation, select a formal sample size, create a packet, inspect identity truth, or read an outcome.

## Design

Each simulation assigned all 3,000 candidate images to one temporary role and retained a canonical pair only when both endpoints shared that role. Cross-role pairs were counted as exclusions, because they could not enter a valid future split without violating the zero-image-crossing rule. Three explicitly nonbinding image-share scenarios were evaluated across 32 deterministic stress seeds each: equal thirds, a development-weighted configuration with a 20% calibration pool, and a confirmation-weighted configuration with a 20% calibration pool. The configuration file states that these seeds and shares are not the official seed or allocation rule.

The stress benchmark required every active role in every run to retain at least 1,200 unique canonical pairs and at least 400 canonical pairs with membership in each primary descriptor family. These values are deliberately conservative capacity checks, not a power calculation, outcome budget, or commitment that each eventual analytical role will receive 1,200 reviewed pairs. Descriptor coverage was counted once for each canonical pair and descriptor family; directed memberships were never treated as independent pairs.

## Results

All 96 simulations met both nonbinding capacity benchmarks. In the equal-thirds scenario, the median retained within-role pool was 28,387.5 pairs, or 33.33% of the 85,182-pair candidate universe, while the median cross-role exclusion count was 56,794.5. The smallest active-role pool across its 32 seeds still contained 9,119 canonical pairs. In the development-weighted scenario, the smallest calibration pool contained 3,247 pairs, despite using only 600 images. In the confirmation-weighted scenario, the smallest development pool contained 5,060 pairs, while the smallest observed descriptor-covered active-role pool across all scenarios and seeds contained 1,657 pairs. All of these values exceed the 1,200-pair and 400-descriptor-pair capacity benchmarks.

The result quantifies the unavoidable cost of image-level isolation. Approximately 59% to 67% of candidate edges became cross-role exclusions under the tested allocations. That loss is not a defect in the validator or an indication that the frozen reservoir is unusable. It is the price of preventing an image from informing more than one analytical role. The remaining within-role pools are nevertheless much larger than the nonbinding stress benchmark.

## Interpretation and limitations

The correct conclusion is that image-disjoint partitioning is graph-capacity feasible for the tested stress configurations. The result does not show that any scenario is statistically optimal, that it is balanced over laterality, quality, illumination, camera/site, or known identity, or that an identity-disjoint sensitivity set exists. It also cannot establish that 1,200 is the final review target, because that decision belongs to the pre-outcome power-and-cost analysis in Workstream 04. Random image assignment is intentionally not the eventual allocation algorithm; it is a falsification-oriented test of whether isolation alone would exhaust the candidate queue.

The next allocation step must use the Workstream 04 numerical decision to select an official target, reserve, stratification rule, and seed. It must then create real image and pair manifests, quantify each planned stratum, validate them with the Workstream 03 zero-crossing contract, and apply the authorized identity-disjoint sensitivity audit. Until those steps are complete, no text may call a partition locked or generate a real outcome-review packet.

## Reproducibility

The scenario configuration is `schemas/pferi_v2/nonbinding_image_partition_feasibility_scenarios_v1.json`. The executable simulation is `scripts/simulate_ws03_image_partition_feasibility.py`, and the archived audit, per-seed counts, summary table, and generated report are stored at `archive/pferi_v2/task_runs/information_partitioning/2026-07-14_nonbinding_partition_feasibility_v1/`. The simulation reads only the frozen canonical-pair and descriptor-membership manifests.
