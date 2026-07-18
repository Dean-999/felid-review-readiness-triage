from scripts.build_phase16_laterality_aware_pair_audit import (
    normalize_laterality,
    pair_side_relation,
)


def test_normalize_laterality_accepts_known_values():
    assert normalize_laterality("left") == "left"
    assert normalize_laterality("right") == "right"
    assert normalize_laterality("both") == "both"
    assert normalize_laterality("frontal") == "frontal"
    assert normalize_laterality("rear") == "rear"


def test_normalize_laterality_maps_missing_to_unknown():
    assert normalize_laterality("") == "unknown"
    assert normalize_laterality(None) == "unknown"
    assert normalize_laterality(float("nan")) == "unknown"
    assert normalize_laterality("side") == "unknown"


def test_pair_side_relation_same_side():
    assert pair_side_relation("left", "left") == "same_side"
    assert pair_side_relation("right", "right") == "same_side"
    assert pair_side_relation("both", "left") == "same_side_or_both"
    assert pair_side_relation("right", "both") == "same_side_or_both"


def test_pair_side_relation_opposite_and_unknown():
    assert pair_side_relation("left", "right") == "opposite_side"
    assert pair_side_relation("unknown", "right") == "one_or_both_unknown"
    assert pair_side_relation("left", "unknown") == "one_or_both_unknown"


def test_pair_side_relation_non_lateral():
    assert pair_side_relation("frontal", "left") == "non_lateral"
    assert pair_side_relation("rear", "right") == "non_lateral"
    assert pair_side_relation("frontal", "rear") == "non_lateral"
