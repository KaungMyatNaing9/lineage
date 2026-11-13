"""Rare shared identifiers, strings, comments, numbers, and misspellings.

An item that is common in ordinary code gets weight 0 or a small weight.
An item that appears in many files of the two projects is down-weighted again
(inverse document frequency). The score is weighted Dice over what remains.
Renamed identifiers do not overlap here; token fingerprints cover that case.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from lineage.discover import Corpus, SourceFile
from lineage.lexicon import (
    COMMON_IDENTIFIERS,
    COMMON_LITERALS,
    COMMON_NUMBERS,
    COMMON_WORDS,
    MISSPELLINGS,
)
from lineage.models import Evidence
from lineage.scoring import idf, weighted_containment, weighted_dice
from lineage.tokenize import lex

_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


@dataclass
class Found:
    key: str
    kind: str
    display: str
    weight: float
    line: int


@dataclass
class ArtifactIndex:
    weight: dict[str, float] = field(default_factory=dict)
    files: dict[str, set[str]] = field(default_factory=dict)
    line: dict[str, int] = field(default_factory=dict)
    path: dict[str, str] = field(default_factory=dict)
    kind: dict[str, str] = field(default_factory=dict)
    display: dict[str, str] = field(default_factory=dict)

    def observe(self, item: Found, file: str) -> None:
        if item.weight <= 0:
            return
        self.files.setdefault(item.key, set()).add(file)
        previous = self.weight.get(item.key, 0.0)
        if item.weight >= previous:
            self.weight[item.key] = item.weight
            self.line[item.key] = item.line
            self.path[item.key] = file
            self.kind[item.key] = item.kind
            self.display[item.key] = item.display


def index_corpus(corpus: Corpus) -> ArtifactIndex:
    index = ArtifactIndex()
    for source in corpus.non_tests():
        for item in extract_artifacts(source):
            index.observe(item, source.rel_path)
    return index


def extract_artifacts(source: SourceFile) -> list[Found]:
    found: list[Found] = []
    comment_parts: list[tuple[int, str]] = []
    string_line = 0
    string_buf: list[str] = []

    def flush_string() -> None:
        nonlocal string_line, string_buf
        if not string_buf:
            return
        text = "".join(string_buf)
        normalized = _norm_text(text)
        weight = string_weight(normalized)
        if weight > 0:
            found.append(Found("str:" + normalized, "string", _short(text.strip()), weight, string_line))
        found.extend(_typos(normalized, string_line))
        string_buf = []

    for token in lex(source.text, source.rel_path, source.language):
        if token.line <= source.license_skip_lines:
            continue
        if token.kind != "string":
            flush_string()
        if token.kind == "comment":
            comment_parts.append((token.line, token.value))
            continue
        if token.kind == "string":
            if string_buf and token.line != string_line:
                flush_string()
            if not string_buf:
                string_line = token.line
            string_buf.append(token.value)
            continue
        if token.kind == "number":
            canonical = canonical_number(token.value)
            if canonical is None:
                continue
            weight = number_weight(canonical)
            if weight > 0:
                found.append(Found(f"num:{canonical}", "number", canonical, weight, token.line))
            continue
        if token.kind == "name":
            weight = identifier_weight(token.value)
            if weight > 0:
                key = "id:" + token.value.casefold()
                found.append(Found(key, "identifier", token.value, weight, token.line))
    flush_string()
    for line, text in _comment_blocks(comment_parts):
        normalized = _norm_text(_strip_comment(text))
        if len(normalized) >= 24 and "license" not in normalized and "copyright" not in normalized:
            weight = 1.15 if not _all_common_words(normalized) else 0.15
            if "spdx" in normalized:
                weight = 0.05
            found.append(Found("comment:" + normalized, "comment", _short(normalized), weight, line))
            for shingle, shingle_line in _shingles(normalized, line):
                found.append(Found("shingle:" + shingle, "comment", _short(shingle), 0.7, shingle_line))
        found.extend(_typos(normalized, line))
    return found


def identifier_weight(name: str) -> float:
    raw = name.strip()
    if len(raw) < 5 or (raw.startswith("__") and raw.endswith("__")):
        return 0.0
    folded = raw.casefold()
    if folded in COMMON_IDENTIFIERS or folded in COMMON_WORDS:
        return 0.0
    pieces = [piece.casefold() for piece in _CAMEL.findall(raw)] or [folded]
    if pieces and all(piece in COMMON_IDENTIFIERS or piece in COMMON_WORDS for piece in pieces):
        return 0.15
    weight = 1.0
    if len(raw) >= 16:
        weight += 0.5
    if any(char.isdigit() for char in raw) and any(char.isalpha() for char in raw):
        weight += 0.25
    return min(weight, 4.0)


def string_weight(normalized: str) -> float:
    if len(normalized) < 8 or normalized in COMMON_LITERALS:
        return 0.0
    if not any(char.isalpha() for char in normalized):
        return 0.0
    if "license" in normalized or "copyright" in normalized or "spdx" in normalized:
        return 0.05
    words = re.findall(r"[a-z0-9']+", normalized)
    if words and all(word in COMMON_WORDS or word in COMMON_IDENTIFIERS for word in words) and len(normalized) < 28:
        return 0.2
    weight = 1.0 + min(len(normalized), 80) / 40.0
    if any(word in MISSPELLINGS for word in words):
        weight += 2.5
    return min(weight, 5.0)


def number_weight(canonical: str) -> float:
    if canonical in COMMON_NUMBERS:
        return 0.0
    digits = canonical.replace("-", "").replace(".", "")
    if len(digits) <= 2:
        return 0.0
    return min(1.0 + 0.25 * (len(digits) - 2), 4.0)


def canonical_number(raw: str) -> str | None:
    text = raw.strip().lower().replace("_", "")
    if text.endswith(("l", "u")):
        text = text[:-1]
    try:
        if any(char in text for char in ".e") and not text.startswith(("0x", "0b", "0o")):
            value = float(text)
            if not math.isfinite(value):
                return None
            if abs(value - round(value)) < 1e-9 and abs(value) < 1e15:
                return str(int(round(value)))
            return f"{value:.8g}"
        base = 10
        if text.startswith("0x"):
            base = 16
        elif text.startswith("0b"):
            base = 2
        elif text.startswith("0o"):
            base = 8
        return str(int(text, base))
    except ValueError:
        return None


def weighted_maps(left: ArtifactIndex, right: ArtifactIndex) -> tuple[dict[str, float], dict[str, float]]:
    left_w: dict[str, float] = {}
    right_w: dict[str, float] = {}
    for key, base in left.weight.items():
        df = len(left.files.get(key, ())) + len(right.files.get(key, ()))
        left_w[key] = base * idf(max(df, 1))
    for key, base in right.weight.items():
        df = len(left.files.get(key, ())) + len(right.files.get(key, ()))
        right_w[key] = base * idf(max(df, 1))
    return left_w, right_w


def artifact_evidence(
    left: ArtifactIndex,
    right: ArtifactIndex,
    weights: dict[str, float],
    *,
    limit: int,
) -> list[Evidence]:
    shared = set(left.weight) & set(right.weight)
    ranked = sorted(shared, key=lambda key: (-weights.get(key, 0.0), key))
    evidence: list[Evidence] = []
    for key in ranked[:limit]:
        if weights.get(key, 0.0) <= 0:
            continue
        kind = left.kind.get(key, "artifact")
        display = left.display.get(key, key)
        evidence.append(
            Evidence(
                original_path=left.path.get(key, ""),
                original_start=left.line.get(key, 1),
                original_end=left.line.get(key, 1),
                rewrite_path=right.path.get(key, ""),
                rewrite_start=right.line.get(key, 1),
                rewrite_end=right.line.get(key, 1),
                score=weights.get(key, 0.0),
                detail=f"shared {kind} {_short(display)!r} (weight {weights.get(key, 0.0):.2f})",
            )
        )
    return evidence


def overlap_scores(
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


def _typos(normalized: str, line: int) -> list[Found]:
    found: list[Found] = []
    for word in set(re.findall(r"[a-z']+", normalized)):
        if word in MISSPELLINGS:
            found.append(Found(f"typo:{word}", "typo", word, 4.0, line))
    return found


def _shingles(normalized: str, line: int) -> list[tuple[str, int]]:
    words = normalized.split()
    output: list[tuple[str, int]] = []
    if len(words) < 6:
        return output
    for index in range(len(words) - 5):
        window = words[index : index + 6]
        if all(word in COMMON_WORDS or word in COMMON_IDENTIFIERS for word in window):
            continue
        output.append((" ".join(window), line))
    return output[:8]


def _all_common_words(normalized: str) -> bool:
    words = re.findall(r"[a-z0-9']+", normalized)
    return bool(words) and all(word in COMMON_WORDS or word in COMMON_IDENTIFIERS for word in words)


def _comment_blocks(parts: list[tuple[int, str]]) -> list[tuple[int, str]]:
    if not parts:
        return []
    blocks: list[tuple[int, str]] = []
    start, buf, prev = parts[0][0], parts[0][1], parts[0][0]
    for line, text in parts[1:]:
        if line <= prev + 1:
            buf += " " + text
            prev = line
            continue
        blocks.append((start, buf))
        start, buf, prev = line, text, line
    blocks.append((start, buf))
    return blocks


def _strip_comment(text: str) -> str:
    text = re.sub(r"/\*|\*/", " ", text)
    text = re.sub(r"(?m)^\s*(#|//|\*)\s?", " ", text)
    return text


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _short(text: str, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
