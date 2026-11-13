"""Structural fingerprints.

Python files get a grammar-based shape from the stdlib AST. Every language also
gets a coarser control-flow shape from the lexer so a cross-language pair can
be compared. The two are not the same feature: the report says which one the
headline score used.

Limits, stated on every report: this is control shape, not behavior. The lexer
path is an approximation (indent depth in Python, brace depth elsewhere). It
misses an algorithm that was rewritten with different branches, and it can
overlap on short idiomatic control flow. Those common shapes are down-weighted
by inverse document frequency and by a small baseline.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable

from lineage.discover import Corpus, SourceFile
from lineage.evidence import Bag
from lineage.tokenize import chunk_ranges, lex
from lineage.winnow import fingerprint_stream

STRUCTURAL_LIMITS = (
    "Structural hashes describe control shape (functions, branches, loops, "
    "assignments, calls), not behavior. When both sides are mostly Python, the "
    "headline uses Python's grammar. Otherwise the headline uses a lexer "
    "approximation: indent depth for Python and brace depth for other languages. "
    "That approximation is not a translation. It misses algorithms rebuilt with "
    "different control flow, and short idiomatic shapes can overlap; those are "
    "down-weighted. Cross-language scores are weaker than same-language scores."
)

_CONTROL = {
    "if": "IF",
    "elif": "ELSE",
    "elsif": "ELSE",
    "elseif": "ELSE",
    "else": "ELSE",
    "for": "LOOP",
    "foreach": "LOOP",
    "while": "LOOP",
    "switch": "SWITCH",
    "match": "SWITCH",
    "case": "CASE",
    "return": "RET",
    "yield": "YIELD",
    "try": "TRY",
    "except": "EXCEPT",
    "catch": "EXCEPT",
    "rescue": "EXCEPT",
    "finally": "FINALLY",
    "with": "WITH",
    "raise": "RAISE",
    "throw": "RAISE",
    "assert": "ASSERT",
    "break": "BREAK",
    "continue": "CONTINUE",
    "class": "CLASS",
    "struct": "CLASS",
    "interface": "CLASS",
    "def": "FUNC",
    "function": "FUNC",
    "func": "FUNC",
    "fn": "FUNC",
    "fun": "FUNC",
    "lambda": "FUNC",
}

_ASSIGN = {"=", "+=", "-=", "*=", "/=", "//=", "%=", ":=", "&=", "|=", "^=", "<<=", ">>=", "**=", "=>"}

_COMPOUND = {"FUNC", "CLASS", "IF", "ELSE", "LOOP", "TRY", "EXCEPT", "WITH", "SWITCH", "CASE"}


def python_fraction(files: Iterable[SourceFile]) -> float:
    loc = sum(item.loc for item in files) or 1
    python_loc = sum(item.loc for item in files if item.language == "python")
    return python_loc / loc


def fill_control_bag(corpus: Corpus, bag: Bag, *, k: int, window: int) -> None:
    for source in corpus.non_tests():
        for texts, lines in control_streams(source.text, source.rel_path, source.language, source.license_skip_lines):
            for fingerprint in fingerprint_stream(
                texts,
                lines,
                file=source.rel_path,
                k=k,
                window=window,
                weight_of=lambda _gram: 1.0,
            ):
                bag.add(
                    "c:" + fingerprint.digest,
                    fingerprint.file,
                    fingerprint.start,
                    fingerprint.end,
                    fingerprint.weight,
                )


def fill_python_ast_bag(corpus: Corpus, bag: Bag, *, k: int, window: int) -> None:
    for source in corpus.non_tests():
        if source.language != "python":
            continue
        for texts, lines in python_ast_streams(source.text, source.license_skip_lines):
            for fingerprint in fingerprint_stream(
                texts,
                lines,
                file=source.rel_path,
                k=k,
                window=window,
                weight_of=lambda _gram: 1.0,
            ):
                bag.add(
                    "a:" + fingerprint.digest,
                    fingerprint.file,
                    fingerprint.start,
                    fingerprint.end,
                    fingerprint.weight,
                )


def control_streams(
    source: str,
    filename: str,
    language: str,
    skip_lines: int,
) -> list[tuple[list[str], list[int]]]:
    events = control_events(source, filename, language, skip_lines)
    ranges = chunk_ranges(source, language) or [(1, max(1, source.count("\n") + 1))]
    streams: list[tuple[list[str], list[int]]] = []
    for start, end in ranges:
        texts = [label for label, line in events if start <= line <= end and line > skip_lines]
        lines = [line for _label, line in events if start <= line <= end and line > skip_lines]
        if texts:
            streams.append((texts, lines))
    return streams


def control_events(source: str, filename: str, language: str, skip_lines: int = 0) -> list[tuple[str, int]]:
    """Coarse control-flow events as ``LABEL@depth`` plus the source line."""
    indents = _indents(source)
    use_indent = language == "python"
    depth = 0
    events: list[tuple[str, int]] = []
    prev_kind = ""
    skip_paren = False
    for token in lex(source, filename, language):
        if token.line <= skip_lines:
            continue
        if token.value == "{":
            if not use_indent:
                depth += 1
            prev_kind = "punct"
            continue
        if token.value == "}":
            if not use_indent:
                depth = max(0, depth - 1)
            prev_kind = "punct"
            continue
        here = indents[token.line - 1] if use_indent and token.line - 1 < len(indents) else depth
        label = _CONTROL.get(token.value.lower()) if token.kind == "keyword" else None
        if label:
            events.append((f"{label}@{here}", token.line))
            if label == "FUNC":
                skip_paren = True
            prev_kind = "keyword"
            continue
        if token.value in _ASSIGN:
            events.append((f"ASSIGN@{here}", token.line))
            prev_kind = "op"
            continue
        if token.value == "(":
            if skip_paren:
                skip_paren = False
            elif prev_kind in {"name", "preserved"}:
                events.append((f"CALL@{here}", token.line))
            prev_kind = "punct"
            continue
        if token.kind in {"name", "preserved"}:
            prev_kind = token.kind
        else:
            prev_kind = token.kind
    return events


def python_ast_streams(source: str, skip_lines: int) -> list[tuple[list[str], list[int]]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    streams: list[tuple[list[str], list[int]]] = []

    def take(node: ast.AST) -> None:
        texts, lines = _ast_events(node, skip_lines)
        if texts:
            streams.append((texts, lines))

    saw_function = False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            saw_function = True
            take(node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    saw_function = True
                    take(child)
    if not saw_function:
        texts, lines = _ast_events(tree, skip_lines)
        if texts:
            streams.append((texts, lines))
    return streams


def _ast_events(node: ast.AST, skip_lines: int) -> tuple[list[str], list[int]]:
    events: list[tuple[str, int]] = []

    def walk(current: ast.AST, depth: int) -> None:
        label = _ast_label(current)
        line = int(getattr(current, "lineno", 1) or 1)
        if label and line > skip_lines:
            events.append((f"{label}@{depth}", line))
        child_depth = depth + 1 if label in _COMPOUND else depth
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                continue
            walk(child, child_depth)

    walk(node, 0)
    return [label for label, _line in events], [line for _label, line in events]


def _ast_label(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return "FUNC"
    if isinstance(node, ast.ClassDef):
        return "CLASS"
    if isinstance(node, (ast.If, ast.IfExp)):
        return "IF"
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        return "LOOP"
    if isinstance(node, ast.Return):
        return "RET"
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return "ASSIGN"
    if isinstance(node, ast.Call):
        return "CALL"
    if isinstance(node, ast.Try):
        return "TRY"
    if isinstance(node, ast.ExceptHandler):
        return "EXCEPT"
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return "WITH"
    if isinstance(node, ast.Raise):
        return "RAISE"
    if isinstance(node, ast.Assert):
        return "ASSERT"
    if isinstance(node, (ast.Yield, ast.YieldFrom)):
        return "YIELD"
    if isinstance(node, ast.Break):
        return "BREAK"
    if isinstance(node, ast.Continue):
        return "CONTINUE"
    if isinstance(node, ast.Match):
        return "SWITCH"
    return None


def _indents(source: str) -> list[int]:
    lines = source.splitlines() or [""]
    depths: list[int] = []
    last = 0
    for line in lines:
        if not line.strip():
            depths.append(last)
            continue
        expanded = line.replace("\t", "    ")
        spaces = len(expanded) - len(expanded.lstrip(" "))
        last = spaces // 4
        depths.append(last)
    return depths
