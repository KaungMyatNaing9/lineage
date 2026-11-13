"""Turn fingerprint bags into Dice, containment, file alignments, and line regions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from lineage.discover import Corpus
from lineage.models import Evidence
from lineage.scoring import idf, weighted_containment, weighted_dice


@dataclass(frozen=True)
class Hit:
    file: str
    start: int
    end: int
    weight: float


@dataclass
class Bag:
    hits: dict[str, list[Hit]] = field(default_factory=dict)
    files: dict[str, set[str]] = field(default_factory=dict)

    def add(self, digest: str, file: str, start: int, end: int, weight: float = 1.0) -> None:
        if weight <= 0 or not digest:
            return
        self.files.setdefault(digest, set()).add(file)
        bucket = self.hits.setdefault(digest, [])
        already = sum(1 for hit in bucket if hit.file == file)
        if already < 4:
            bucket.append(Hit(file, start, end, weight))

    def __len__(self) -> int:
        return len(self.hits)


class FileMatch(TypedDict):
    rewrite_path: str
    original_path: str
    containment: float
    shared_fingerprints: int
    rewrite_fingerprints: int


@dataclass
class Overlap:
    dice: float | None
    containment: float | None
    coverage: float | None
    shared: int
    count_a: int
    count_b: int
    weights: dict[str, float]
    reason: str


def measure(left: Bag, right: Bag, baseline: set[str]) -> Overlap:
    """Score `right` against `left`. Containment is how much of `right` sits inside `left`."""
    keep_a = {digest for digest in left.hits if digest not in baseline}
    keep_b = {digest for digest in right.hits if digest not in baseline}
    if not keep_a or not keep_b:
        return Overlap(
            None,
            None,
            None,
            0,
            len(keep_a),
            len(keep_b),
            {},
            "not enough distinctive fingerprints after common idioms were filtered",
        )
    weights: dict[str, float] = {}
    for digest in keep_a | keep_b:
        df = len(left.files.get(digest, ())) + len(right.files.get(digest, ()))
        base = _max_weight(left, digest)
        other = _max_weight(right, digest)
        weights[digest] = max(base, other, 0.0) * idf(df)
    left_w = {digest: weights[digest] for digest in keep_a if weights[digest] > 0}
    right_w = {digest: weights[digest] for digest in keep_b if weights[digest] > 0}
    dice = weighted_dice(left_w, right_w)
    containment = weighted_containment(right_w, left_w)
    coverage = weighted_containment(left_w, right_w)
    shared = len(set(left_w) & set(right_w))
    return Overlap(dice, containment, coverage, shared, len(left_w), len(right_w), weights, "")


def file_rows(original: Bag, rewrite: Bag, weights: dict[str, float], limit: int = 15) -> list[FileMatch]:
    """Best original file for each rewrite file, by shared fingerprint weight."""
    by_rewrite: dict[str, dict[str, float]] = {}
    mass: dict[str, float] = {}
    shared_counts: dict[str, int] = {}
    best_shared_count: dict[tuple[str, str], int] = {}
    for digest, hits in rewrite.hits.items():
        weight = weights.get(digest, 0.0)
        if weight <= 0:
            continue
        rewrite_files = {hit.file for hit in hits}
        original_files = original.files.get(digest, set())
        for rewrite_file in rewrite_files:
            mass[rewrite_file] = mass.get(rewrite_file, 0.0) + weight
            if not original_files:
                continue
            shared_counts[rewrite_file] = shared_counts.get(rewrite_file, 0) + 1
            for original_file in original_files:
                pair = (rewrite_file, original_file)
                best_shared_count[pair] = best_shared_count.get(pair, 0) + 1
                bucket = by_rewrite.setdefault(rewrite_file, {})
                bucket[original_file] = bucket.get(original_file, 0.0) + weight
    rows: list[FileMatch] = []
    for rewrite_file, total in mass.items():
        partners = by_rewrite.get(rewrite_file, {})
        if not partners or total <= 0:
            continue
        original_file, shared_weight = max(partners.items(), key=lambda item: item[1])
        rows.append(
            {
                "rewrite_path": rewrite_file,
                "original_path": original_file,
                "containment": shared_weight / total,
                "shared_fingerprints": best_shared_count.get((rewrite_file, original_file), 0),
                "rewrite_fingerprints": shared_counts.get(rewrite_file, 0),
            }
        )
    rows.sort(key=lambda row: (-row["containment"], -row["shared_fingerprints"], row["rewrite_path"]))
    return rows[:limit]


def regions_for(
    original: Bag,
    rewrite: Bag,
    weights: dict[str, float],
    original_corpus: Corpus,
    rewrite_corpus: Corpus,
    *,
    limit: int,
    gap: int = 3,
) -> list[Evidence]:
    """Merge nearby shared fingerprints into side-by-side regions."""
    rows = file_rows(original, rewrite, weights, limit=40)
    texts_a = original_corpus.by_path()
    texts_b = rewrite_corpus.by_path()
    found: list[Evidence] = []
    for row in rows:
        if row["containment"] < 0.15 and row["shared_fingerprints"] < 2:
            continue
        rewrite_file = str(row["rewrite_path"])
        original_file = str(row["original_path"])
        marks = _marks_for_pair(original, rewrite, weights, original_file, rewrite_file)
        for region in _merge(marks, gap=gap):
            left = texts_a.get(original_file)
            right = texts_b.get(rewrite_file)
            found.append(
                Evidence(
                    original_path=original_file,
                    original_start=region.start_a,
                    original_end=region.end_a,
                    rewrite_path=rewrite_file,
                    rewrite_start=region.start_b,
                    rewrite_end=region.end_b,
                    score=region.weight,
                    detail=(
                        f"{region.count} shared fingerprints "
                        f"(combined weight {region.weight:.2f})"
                    ),
                    original_excerpt=_excerpt(left.text if left else "", region.start_a, region.end_a),
                    rewrite_excerpt=_excerpt(right.text if right else "", region.start_b, region.end_b),
                )
            )
    found.sort(key=lambda item: (-item.score, item.rewrite_path, item.rewrite_start))
    return found[:limit]


@dataclass
class _Mark:
    start_a: int
    end_a: int
    start_b: int
    end_b: int
    weight: float


@dataclass
class _Region:
    start_a: int
    end_a: int
    start_b: int
    end_b: int
    weight: float
    count: int


def _marks_for_pair(
    original: Bag,
    rewrite: Bag,
    weights: dict[str, float],
    original_file: str,
    rewrite_file: str,
) -> list[_Mark]:
    marks: list[_Mark] = []
    for digest, weight in weights.items():
        if weight <= 0 or digest not in original.hits or digest not in rewrite.hits:
            continue
        left = [hit for hit in original.hits[digest] if hit.file == original_file]
        right = [hit for hit in rewrite.hits[digest] if hit.file == rewrite_file]
        for hit_b, hit_a in zip(right, left, strict=False):
            marks.append(_Mark(hit_a.start, hit_a.end, hit_b.start, hit_b.end, weight))
    return marks


def _merge(marks: list[_Mark], gap: int) -> list[_Region]:
    if not marks:
        return []
    ordered = sorted(marks, key=lambda mark: (mark.start_b, mark.start_a))
    regions: list[_Region] = []
    for mark in ordered:
        if not regions:
            regions.append(_Region(mark.start_a, mark.end_a, mark.start_b, mark.end_b, mark.weight, 1))
            continue
        current = regions[-1]
        close_b = mark.start_b <= current.end_b + gap
        close_a = mark.start_a <= current.end_a + gap and mark.end_a >= current.start_a - gap
        if close_b and close_a:
            current.start_a = min(current.start_a, mark.start_a)
            current.end_a = max(current.end_a, mark.end_a)
            current.start_b = min(current.start_b, mark.start_b)
            current.end_b = max(current.end_b, mark.end_b)
            current.weight += mark.weight
            current.count += 1
        else:
            regions.append(_Region(mark.start_a, mark.end_a, mark.start_b, mark.end_b, mark.weight, 1))
    return regions


def _max_weight(bag: Bag, digest: str) -> float:
    hits = bag.hits.get(digest, [])
    if not hits:
        return 0.0
    return max(hit.weight for hit in hits)


def _excerpt(text: str, start: int, end: int, limit: int = 26) -> str:
    if not text or start <= 0:
        return ""
    lines = text.splitlines()
    start = max(1, start)
    end = min(len(lines), max(start, end))
    chunk = lines[start - 1 : end]
    clipped = []
    for line in chunk[:limit]:
        clipped.append(line if len(line) <= 180 else line[:180] + "…")
    if len(chunk) > limit:
        clipped.append("…")
    return "\n".join(clipped)
