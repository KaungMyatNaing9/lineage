from __future__ import annotations

import math

from lineage.scoring import idf, weighted_containment, weighted_dice


def test_identical_sets_score_one() -> None:
    weights = {"a": 1.0, "b": 2.0}
    assert weighted_dice(weights, dict(weights)) == 1.0
    assert weighted_containment(weights, weights) == 1.0


def test_partial_overlap() -> None:
    left = {"h1": 1.0, "h2": 1.0}
    right = {"h1": 1.0, "h3": 1.0}
    assert weighted_dice(left, right) == 0.5
    assert weighted_containment(right, left) == 0.5


def test_disjoint_is_zero_and_empty_is_none() -> None:
    assert weighted_dice({"a": 1.0}, {"b": 1.0}) == 0.0
    assert weighted_dice({}, {"b": 1.0}) is None
    assert weighted_containment({}, {"b": 1.0}) is None


def test_idf_decreases() -> None:
    assert idf(1) == 1.0
    assert idf(2) == 1.0 / (1.0 + math.log(2))
    assert idf(20) < idf(2)
