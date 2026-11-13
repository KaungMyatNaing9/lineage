"""Overlap of literals that sit together inside a test function.

Test files are left out of the token, structural, and artifact signals so a
shared test suite is reported here instead of being counted three more times.
Common fixtures (``{}``, ``[]``, ``"utf-8"``, ``0``, ``1``) have no weight.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lineage.artifacts import canonical_number, number_weight, string_weight
from lineage.discover import Corpus, SourceFile
from lineage.scoring import idf, weighted_containment, weighted_dice
from lineage.tokenize import chunk_ranges, lex, slice_lines


@dataclass
class CaseIndex:
    weight: dict[str, float] = field(default_factory=dict)
    files: dict[str, set[str]] = field(default_factory=dict)
    line: dict[str, int] = field(default_factory=dict)
    path: dict[str, str] = field(default_factory=dict)
    display: dict[str, str] = field(default_factory=dict)

    def observe(self, key: str, weight: float, file: str, line: int, display: str) -> None:
        if weight <= 0:
            return
        self.files.setdefault(key, set()).add(file)
        if weight >= self.weight.get(key, 0.0):
            self.weight[key] = weight
            self.line[key] = line
            self.path[key] = file
            self.display[key] = display


def index_tests(corpus: Corpus) -> CaseIndex:
    index = CaseIndex()
    for source in corpus.tests():
        for key, weight, line, display in cases_in(source):
            index.observe(key, weight, source.rel_path, line, display)
    return index


def cases_in(source: SourceFile) -> list[tuple[str, float, int, str]]:
    ranges = chunk_ranges(source.text, source.language)
    raw = lex(source.text, source.rel_path, source.language)
    output: list[tuple[str, float, int, str]] = []
    if not ranges:
        ranges = [(1, max(1, source.text.count("\n") + 1))]
    for start, end in ranges:
        literals: list[tuple[str, float]] = []
        for token in raw:
            if token.line < start or token.line > end or token.line <= source.license_skip_lines:
                continue
            if token.kind == "string":
                text = " ".join(token.value.split()).strip().casefold()
                weight = string_weight(text)
                if weight > 0:
                    literals.append((f"s:{text}", weight))
            elif token.kind == "number":
                canonical = canonical_number(token.value)
                if canonical is None:
                    continue
                weight = number_weight(canonical)
                if weight > 0:
                    literals.append((f"n:{canonical}", weight))
        if not literals:
            continue
        # Cap so one enormous test does not build a unique key from noise.
        literals.sort(key=lambda item: (-item[1], item[0]))
        chosen: list[str] = []
        seen: set[str] = set()
        best = 0.0
        for key, weight in literals:
            if key in seen:
                continue
            seen.add(key)
            chosen.append(key)
            best = max(best, weight)
            # Individual literals still count when the surrounding test harness differs.
            output.append((key, weight, start, key.split(":", 1)[-1][:80]))
            if len(chosen) >= 12:
                break
        if len(chosen) >= 2:
            signature = "case:" + "|".join(sorted(chosen))
            preview = slice_lines(source.text, start, min(end, start + 2)).strip().splitlines()
            display = preview[0][:80] if preview else signature[:80]
            output.append((signature, best, start, display))
    return output


def case_weights(left: CaseIndex, right: CaseIndex) -> tuple[dict[str, float], dict[str, float]]:
    left_w: dict[str, float] = {}
    right_w: dict[str, float] = {}
    for key, base in left.weight.items():
        df = len(left.files.get(key, ())) + len(right.files.get(key, ()))
        left_w[key] = base * idf(df)
    for key, base in right.weight.items():
        df = len(left.files.get(key, ())) + len(right.files.get(key, ()))
        right_w[key] = base * idf(df)
    return left_w, right_w


def case_scores(
    left_w: dict[str, float], right_w: dict[str, float]
) -> tuple[float | None, float | None, float | None, int]:
    if not left_w or not right_w:
        return None, None, None, 0
    return (
        weighted_dice(left_w, right_w),
        weighted_containment(right_w, left_w),
        weighted_containment(left_w, right_w),
        len(set(left_w) & set(right_w)),
    )
