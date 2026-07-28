#!/usr/bin/env python3
"""One-shot weighted, dyadic-robust Task15M external confirmation analysis."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import shutil
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EXPORT = Path('/Users/dshen/Downloads/PF_ERI_TASK15M_CONFIRMATION_FINAL_EXPORT.zip')
EXPORT_SHA = Path('/Users/dshen/Downloads/PF_ERI_TASK15M_CONFIRMATION_FINAL_EXPORT.sha256')
DESIGN = ROOT / 'archive/pferi_v2/task_runs/model_development/2026-07-27_task15m_independent_confirmation_design_freeze_v1'
OUTCOMES = ROOT / 'archive/pferi_v2/task_runs/review/adjudicated_outcomes'
COMMITMENTS = ROOT / 'archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1/sealed_outcome_commitments.json'
OUTPUT = ROOT / 'archive/pferi_v2/task_runs/models/confirmation'
PREFIX = 'PF_ERI_TASK15M_CONFIRMATION_FINAL_EXPORT/'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def archive_csv(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with archive.open(PREFIX + name) as handle:
        return list(csv.DictReader(io.TextIOWrapper(handle, encoding='utf-8', newline='')))


def commitment_digest(rows: list[dict[str, str]]) -> str:
    text = '\n'.join('|'.join(row[key] for key in ('canonical_pair_id', 'final_three_category_label', 'review_ready_label', 'not_ready_or_uncertain_label', 'final_label_source')) for row in sorted(rows, key=lambda item: item['canonical_pair_id']))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def checksums(directory: Path) -> None:
    files = sorted(path for path in directory.rglob('*') if path.is_file() and path.name != 'CHECKSUMS.sha256')
    (directory / 'CHECKSUMS.sha256').write_text(''.join(f'{sha256(path)}  {path.relative_to(directory)}\n' for path in files), encoding='utf-8')


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(f'refusing to overwrite immutable output: {OUTPUT}')
    expected_export_hash = EXPORT_SHA.read_text(encoding='utf-8').split()[0]
    if sha256(EXPORT) != expected_export_hash:
        raise RuntimeError('Task15M export SHA256 mismatch')
    with zipfile.ZipFile(EXPORT) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Task15M export ZIP CRC failure')
        run = json.loads(archive.read(PREFIX + 'run_audit.json'))
        validation = json.loads(archive.read(PREFIX + 'validation_audit.json'))
        if run.get('status') != 'PASS' or validation.get('status') != 'PASS' or validation.get('failures') != [] or run.get('confirmation_outcomes_accessed') is not False:
            raise RuntimeError('Task15M measurement export is not a passing outcome-free result')
        supported = archive_csv(archive, 'supported_pair_manifest.csv')
        predictions = archive_csv(archive, 'frozen_model_calibrated_predictions.csv')
    if len(supported) != 252 or len(predictions) != 504:
        raise RuntimeError('unexpected frozen Task15M scored inventory')
    linkage = read_csv(DESIGN / 'restricted/legacy_confirmation_linkage.csv')
    formal = read_csv(ROOT / 'archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1/restricted_formal_pair_sampling_manifest.csv')
    outcomes = read_csv(OUTCOMES / 'final_adjudicated_outcomes.csv')
    deployment = [row for row in outcomes if row['formal_sampling_stage'] == 'deployment_confirmation']
    commitment = json.loads(COMMITMENTS.read_text(encoding='utf-8'))['locked_stages']['deployment_confirmation']['outcome_commitment_sha256']
    if len(deployment) != 889 or commitment_digest(deployment) != commitment:
        raise RuntimeError('sealed deployment-confirmation outcome commitment mismatch')
    linkage_by_task = {row['task15m_confirmation_pair_id']: row['historical_canonical_pair_id'] for row in linkage}
    formal_by_id = {row['canonical_pair_id']: row for row in formal}
    outcome_by_id = {row['canonical_pair_id']: row for row in deployment}
    pred_by_pair: dict[str, dict[str, float]] = {}
    for row in predictions:
        pred_by_pair.setdefault(row['canonical_pair_id'], {})[row['model_id']] = float(row['calibrated_probability_not_ready_or_uncertain'])
    records = []
    for row in supported:
        task_id = row['canonical_pair_id']; historical_id = linkage_by_task.get(task_id)
        if historical_id is None or historical_id not in formal_by_id or historical_id not in outcome_by_id or set(pred_by_pair.get(task_id, {})) != {'P3', 'P5'}:
            raise RuntimeError(f'incomplete Task15M outcome join: {task_id}')
        sample, outcome = formal_by_id[historical_id], outcome_by_id[historical_id]
        if sample['formal_sampling_stage'] != 'deployment_confirmation' or outcome['not_ready_or_uncertain_label'] not in {'0', '1'}:
            raise RuntimeError(f'invalid joined deployment outcome: {task_id}')
        y = float(outcome['not_ready_or_uncertain_label']); p3 = pred_by_pair[task_id]['P3']; p5 = pred_by_pair[task_id]['P5']
        records.append({'task15m_confirmation_pair_id': task_id, 'historical_canonical_pair_id': historical_id, 'endpoint_a_image_id': row['endpoint_a_image_id'], 'endpoint_b_image_id': row['endpoint_b_image_id'], 'sampling_probability': float(sample['first_order_inclusion_probability']), 'outcome': y, 'p3_brier_loss': (y-p3)**2, 'p5_brier_loss': (y-p5)**2, 'delta_brier_p3_minus_p5': (y-p3)**2-(y-p5)**2})
    weights = np.asarray([1.0/r['sampling_probability'] for r in records], dtype=float)
    delta = np.asarray([r['delta_brier_p3_minus_p5'] for r in records], dtype=float)
    normalized = weights / weights.sum(); estimate = float(np.dot(normalized, delta))
    influence = normalized * (delta - estimate)
    endpoint_sums: dict[str, float] = {}
    for record, value in zip(records, influence):
        for endpoint in (record['endpoint_a_image_id'], record['endpoint_b_image_id']):
            endpoint_sums[endpoint] = endpoint_sums.get(endpoint, 0.0) + float(value)
    variance = float(sum(value * value for value in endpoint_sums.values()) - np.dot(influence, influence))
    if variance < -1e-15:
        raise RuntimeError('negative dyadic sandwich variance')
    variance = max(0.0, variance); se = math.sqrt(variance)
    lower, upper = estimate - 1.959963984540054 * se, estimate + 1.959963984540054 * se
    independent_se = float(math.sqrt(np.dot(influence, influence)))
    p3_brier = float(np.dot(normalized, np.asarray([r['p3_brier_loss'] for r in records])))
    p5_brier = float(np.dot(normalized, np.asarray([r['p5_brier_loss'] for r in records])))
    degree = Counter(endpoint for row in records for endpoint in (row['endpoint_a_image_id'], row['endpoint_b_image_id']))
    status = 'PASS_PRIMARY_CONFIRMATION' if lower > 0.005 else 'FAIL_PRIMARY_CONFIRMATION'
    report = {
        'status': status, 'analysis_version': 'pferi_v2_task15m_external_confirmation_analysis_v1',
        'completed_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'claim_boundary': 'This is an external confirmation analysis only for the 252 pairs supported by the frozen current dual-descriptor taxonomy. It does not establish identity accuracy, universal deployment utility, or project completion.',
        'protocol_deviation': 'During outcome-table schema inspection immediately before this analysis freeze, two CSV data rows were displayed. The predeclared estimand, support restriction, model predictions, calibration transform, weights, interval, and success threshold were not changed.',
        'bindings': {'export_sha256': expected_export_hash, 'export_contract_sha256': run['contract_sha256'], 'deployment_outcome_commitment_sha256': commitment},
        'sample': {'candidate_pair_count': 889, 'supported_pair_count': len(records), 'unsupported_pair_count': 637, 'unique_endpoint_count': len(degree), 'maximum_endpoint_degree': max(degree.values())},
        'estimand': {'definition': 'Hájek-normalized inverse-probability-weighted Brier(P3_calibrated)-Brier(P5_calibrated)', 'p3_weighted_brier': p3_brier, 'p5_weighted_brier': p5_brier, 'point_estimate': estimate, 'practical_increment_threshold': 0.005},
        'interval': {'method': 'two-sided 95% dyadic cluster-robust sandwich using physical image endpoints', 'standard_error': se, 'lower_95': lower, 'upper_95': upper, 'independent_row_se_diagnostic': independent_se, 'dyadic_to_independent_se_ratio': (se/independent_se if independent_se else None)},
        'decision_rule': 'PASS only when lower_95 > 0.005', 'outcome_joined_after_measurement_export_verified': True,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT.parent, prefix='.task15m_analysis.') as temporary:
        stage = Path(temporary) / OUTPUT.name; stage.mkdir(); (stage/'restricted').mkdir()
        write_json(stage/'task15m_external_confirmation_analysis.json', report)
        with (stage/'restricted/task15m_pair_level_brier_losses.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
        (stage/'TASK15M_EXTERNAL_CONFIRMATION_REPORT.md').write_text(f'# Task15M External Confirmation\n\nStatus: **{status}**\n\nThe frozen weighted P3-minus-P5 Brier increment is `{estimate:.9f}`. The dyadic cluster-robust 95% interval is `[{lower:.9f}, {upper:.9f}]`; the predeclared lower-bound threshold is `0.005`.\n', encoding='utf-8')
        checksums(stage); shutil.move(str(stage), str(OUTPUT))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
