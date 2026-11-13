"""Winnowing fingerprints (Schleimer, Wilkerson, Aiken 2003).

In every window of `w` k-gram hashes, the minimum hash is kept. Ties keep the
rightmost minimum. Any shared run of about w + k - 1 normalized tokens produces
at least one shared fingerprint.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Fingerprint:
    digest: str
    file: str
    start: int
    end: int
    weight: float


def select_window_minima(hashes: Sequence[Any], window: int) -> list[int]:
    """Return indices of winnowed minima. Values must be totally ordered."""
    count = len(hashes)
    if count == 0:
        return []
    if window < 1:
        raise ValueError("window must be at least 1")
    width = min(window, count)
    selected: list[int] = []
    previous = -1
    minimum_at = -1
    for index in range(count):
        window_start = index - width + 1
        if window_start < 0:
            continue
        if minimum_at < window_start:
            minimum_at = window_start
            for cursor in range(window_start, index + 1):
                if hashes[cursor] <= hashes[minimum_at]:
                    minimum_at = cursor
        elif hashes[index] <= hashes[minimum_at]:
            minimum_at = index
        if minimum_at != previous:
            selected.append(minimum_at)
            previous = minimum_at
    return selected


def digest_gram(parts: Sequence[str]) -> str:
    payload = "\x1f".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha1(payload).hexdigest()[:16]


def fingerprint_stream(
    texts: Sequence[str],
    lines: Sequence[int],
    *,
    file: str,
    k: int,
    window: int,
    weight_of: Callable[[tuple[str, ...]], float],
) -> list[Fingerprint]:
    """Build fingerprints from parallel text and line sequences.

    `weight_of` returns 0 when a k-gram should be ignored (boilerplate literals).
    """
    count = len(texts)
    if k < 1 or count < k or len(lines) != count:
        return []
    grams: list[tuple[str, float, int, int]] = []
    for start in range(count - k + 1):
        gram = tuple(texts[index] for index in range(start, start + k))
        weight = float(weight_of(gram))
        if weight <= 0:
            grams.append(("", 0.0, 0, 0))
            continue
        digest = digest_gram(gram)
        first = int(lines[start])
        last = int(lines[start + k - 1])
        grams.append((digest, weight, first, last))
    comparable = [item[0] if item[0] else "\uffff" for item in grams]
    # Empty digests are placeholders for dropped grams. Give them a sentinel that
    # loses every minimum comparison so they are not selected unless a window is
    # entirely dropped. Windows of only dropped grams are ignored below.
    chosen = select_window_minima(comparable, window)
    output: list[Fingerprint] = []
    seen: set[tuple[str, int]] = set()
    for index in chosen:
        digest, weight, first, last = grams[index]
        if not digest or weight <= 0:
            continue
        key = (digest, first)
        if key in seen:
            continue
        seen.add(key)
        output.append(Fingerprint(digest, file, first, last, weight))
    return output
