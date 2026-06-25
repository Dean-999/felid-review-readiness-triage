import pandas as pd

from scripts.build_phase16_dataset_foundation_audit import (
    high_evidence_proxy_pass,
    issue_flags,
    low_evidence_proxy_pass,
)


def test_high_evidence_proxy_pass_requires_review_ready_high_label():
    row = pd.Series(
        {
            "image_exists": "yes",
            "md_detected": "yes",
            "md_best_confidence": 0.91,
            "md_area_fraction": 0.12,
            "md_width_fraction": 0.30,
            "md_height_fraction": 0.30,
            "md_edge_touch": "no",
            "image_evidence_utility_score": 0.82,
            "human_review_bucket": "review_ready",
            "human_review_confidence": "high",
        }
    )
    assert high_evidence_proxy_pass(row)


def test_high_evidence_proxy_fails_small_edge_touch():
    row = pd.Series(
        {
            "image_exists": "yes",
            "md_detected": "yes",
            "md_best_confidence": 0.91,
            "md_area_fraction": 0.04,
            "md_width_fraction": 0.10,
            "md_height_fraction": 0.40,
            "md_edge_touch": "yes",
            "image_evidence_utility_score": 0.82,
            "human_review_bucket": "review_ready",
            "human_review_confidence": "high",
            "evidence_axis": "high_confidence",
        }
    )
    assert not high_evidence_proxy_pass(row)
    flags = issue_flags(row)
    assert "animal_small_for_high_evidence" in flags
    assert "edge_touch_or_crop_risk" in flags
    assert "high_confidence_proxy_fail" in flags


def test_low_evidence_proxy_rejects_high_like_stress_case():
    row = pd.Series(
        {
            "image_exists": "yes",
            "md_detected": "yes",
            "md_best_confidence": 0.94,
            "md_area_fraction": 0.18,
            "md_width_fraction": 0.30,
            "md_height_fraction": 0.30,
            "md_edge_touch": "no",
            "image_evidence_utility_score": 0.80,
            "human_review_bucket": "review_ready",
            "human_review_confidence": "high",
        }
    )
    assert not low_evidence_proxy_pass(row)


def test_low_evidence_proxy_accepts_small_or_species_level_case():
    row = pd.Series(
        {
            "image_exists": "yes",
            "md_detected": "yes",
            "md_best_confidence": 0.75,
            "md_area_fraction": 0.02,
            "md_width_fraction": 0.08,
            "md_height_fraction": 0.20,
            "md_edge_touch": "no",
            "image_evidence_utility_score": 0.32,
            "human_review_bucket": "species_level_only",
            "human_review_confidence": "low",
        }
    )
    assert low_evidence_proxy_pass(row)
