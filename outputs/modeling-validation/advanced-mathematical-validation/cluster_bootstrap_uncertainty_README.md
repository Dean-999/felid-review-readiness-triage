# Cluster Bootstrap Uncertainty

Status: `PASS`

This module estimates uncertainty for PF-ERI validation metrics by
resampling clusters instead of individual rows.

## Cluster Units

- `query_image_cluster`: rows grouped by query PF-ERI image id.
- `component_group_cluster`: rows grouped by connected fold/component group.

## Identity Bootstrap

not_feasible_identity_relation_has_only_yes_no_not_resolved_identity_clusters

## Sparse Cluster Warning

Intervals with fewer than 10 clusters are reported as diagnostics, not
high-precision uncertainty estimates. Component-group calibration and
evaluation splits are especially sparse because they contain only a few
fold/component clusters.

## Outputs

- Metric intervals: `outputs/modeling-validation/advanced-mathematical-validation/cluster_bootstrap_metric_intervals.csv`
- Diagnostics: `outputs/modeling-validation/advanced-mathematical-validation/cluster_bootstrap_diagnostics.csv`

## Boundary

Cluster-aware uncertainty intervals for CzechLynx reviewability; Bobcat identity claims remain blocked.
