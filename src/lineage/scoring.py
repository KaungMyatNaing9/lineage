"""Weighted overlap used by every signal.

Dice is symmetric. Containment answers a different question: how much of the
rewrite's weight also appears on the original side. A subset can have
containment near 1 and a lower Dice, so reports show both.
"""

from __future__ import annotations

import math


def idf(document_frequency: int) -> float:
    """Down-weight items that show up in many files. df of 1 keeps full weight."""
    df = max(int(document_frequency), 1)
    return 1.0 / (1.0 + math.log(df))


def weighted_dice(left: dict[str, float], right: dict[str, float]) -> float | None:
    """Dice coefficient over positive weights. Identical key sets score 1."""
    if not left or not right:
        return None
    shared = set(left) & set(right)
    intersection = sum(min(left[key], right[key]) for key in shared)
    total = sum(left.values()) + sum(right.values())
    if total <= 0:
        return None
    return (2.0 * intersection) / total


def weighted_containment(part: dict[str, float], whole: dict[str, float]) -> float | None:
    """Fraction of `part`'s weight that is covered by `whole`."""
    if not part:
        return None
    covered = 0.0
    for key, weight in part.items():
        if weight <= 0:
            continue
        other = whole.get(key, 0.0)
        if other > 0:
            covered += min(weight, other)
    denominator = sum(weight for weight in part.values() if weight > 0)
    if denominator <= 0:
        return None
    return covered / denominator
