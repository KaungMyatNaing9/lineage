"""Tiny numeric summaries."""


def mean(values):
    if not values:
        raise ValueError("no values")
    return sum(values) / len(values)


def median(values):
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def variance(values):
    if len(values) < 2:
        raise ValueError("need two values")
    center = mean(values)
    total = 0
    for value in values:
        delta = value - center
        total += delta * delta
    return total / (len(values) - 1)
