"""Language-aware tokenization and rename-stable normalization.

User-defined names become ID0, ID1, … in order of first appearance inside each
chunk (a function, or a module-level statement). Keywords, builtins, and
dunder names stay as written. Whitespace, comments, and license-header lines
are dropped. String contents become STR so wording changes do not move the
fingerprint; the artifact signal keeps the actual strings.
"""

from __future__ import annotations

import ast
import bisect
import re
from dataclasses import dataclass
from typing import Any

from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.token import Comment, Name, Number, Operator, Punctuation, String, Text, Whitespace
from pygments.util import ClassNotFound

from lineage.lexicon import PRESERVED_NAMES

_LOW_INFO = frozenset(
    {
        "STR",
        "NUM",
        ",",
        ";",
        ":",
        ".",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
        "...",
        "@",
    }
)

_IMPORT_LINE = re.compile(
    r"""^\s*(
        from\s+\S+\s+import\b
        |import\b
        |\#\s*include\b
        |include\b
        |using\s+\w
        |require\s*\(
        |use\s+\w
    )""",
    re.VERBOSE,
)

_FUNC_LINE = re.compile(
    r"""^\s*
        (?:export\s+(?:default\s+)?)?
        (?:pub(?:\([^)]*\))?\s+)?
        (?:(?:public|private|protected|static|final|async|unsafe|extern|crate)\s+)*
        (?:function\b|func\b|fn\b|fun\b|sub\b|def\b)
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class RawTok:
    kind: str
    value: str
    line: int


@dataclass(frozen=True)
class NormTok:
    text: str
    line: int


def chunk_ranges(source: str, language: str) -> list[tuple[int, int]]:
    """1-indexed inclusive line ranges. One range per function, plus module-level code."""
    if language == "python":
        ranges = _python_ranges(source)
    else:
        ranges = _brace_ranges(source)
    if not ranges:
        last = max(1, source.count("\n") + (0 if source.endswith("\n") else 1))
        return [(1, last)]
    return ranges


def normalized_chunks(
    source: str,
    filename: str,
    language: str,
    *,
    skip_lines: int = 0,
) -> list[list[NormTok]]:
    """Normalize each function (and module-level chunk) with its own ID map.

    Line numbers stay aligned with `source`. Splitting after lexing is what
    makes reordering whole functions leave fingerprints unchanged.
    """
    raw = lex(source, filename, language)
    ranges = chunk_ranges(source, language)
    chunks: list[list[NormTok]] = []
    for start, end in ranges:
        names: dict[str, str] = {}
        chunk = _normalize_raw(raw, names, skip_lines=skip_lines, start=start, end=end)
        if chunk:
            chunks.append(chunk)
    return chunks


def normalize_source(source: str, filename: str, language: str, *, skip_lines: int = 0) -> list[NormTok]:
    """Normalize a whole snippet as one chunk. Used by unit tests."""
    raw = lex(source, filename, language)
    return _normalize_raw(raw, {}, skip_lines=skip_lines, start=1, end=10**9)


def _normalize_raw(
    raw: list[RawTok],
    names: dict[str, str],
    *,
    skip_lines: int,
    start: int,
    end: int,
) -> list[NormTok]:
    output: list[NormTok] = []
    for token in raw:
        if token.line < start or token.line > end or token.line <= skip_lines:
            continue
        if token.kind in {"comment", "whitespace", "skip"}:
            continue
        if token.kind == "string":
            output.append(NormTok("STR", token.line))
        elif token.kind == "number":
            output.append(NormTok(_norm_number(token.value), token.line))
        elif token.kind == "name":
            output.append(NormTok(_norm_name(token.value, names), token.line))
        elif token.kind in {"keyword", "preserved", "op", "punct"}:
            output.append(NormTok(token.value, token.line))
    return output


def gram_weight(tokens: tuple[str, ...]) -> float:
    """Drop k-grams that are almost only literals and punctuation.

    Those grams are shared by unrelated tables of strings. Real string overlap
    is scored by the artifact signal instead.
    """
    if not tokens:
        return 0.0
    informative = sum(1 for token in tokens if token not in _LOW_INFO)
    if informative / len(tokens) < 0.40:
        return 0.0
    return 1.0


def slice_lines(source: str, start: int, end: int) -> str:
    lines = source.splitlines()
    start = max(1, start)
    end = max(start, end)
    return "\n".join(lines[start - 1 : end])


def lex(source: str, filename: str, language: str) -> list[RawTok]:
    lexer = _lexer(filename, source, language)
    import_lines = {
        index + 1
        for index, line in enumerate(source.splitlines())
        if _IMPORT_LINE.match(line)
    }
    # Pygments drops a leading newline, so line numbers come from the character
    # offset rather than from counting newlines in the tokens it yields.
    line_starts = [0]
    for index, char in enumerate(source):
        if char == "\n":
            line_starts.append(index + 1)
    raw: list[RawTok] = []
    for index, ttype, value in lexer.get_tokens_unprocessed(source):
        if not value or value.strip() == "":
            continue
        start_line = bisect.bisect_right(line_starts, index)
        if start_line in import_lines:
            continue
        if ttype in Comment:
            raw.append(RawTok("comment", value, start_line))
            continue
        if ttype in String:
            if _string_payload(ttype, value) is None:
                continue
            raw.append(RawTok("string", _string_payload(ttype, value) or "", start_line))
            continue
        if ttype in Number:
            raw.append(RawTok("number", value, start_line))
            continue
        if ttype in Name:
            raw.append(RawTok(_name_kind(ttype), value, start_line))
            continue
        if ttype in Operator or ttype in Punctuation:
            raw.append(RawTok("op" if ttype in Operator else "punct", value, start_line))
            continue
        # Keywords are not always under Operator/Name. Pygments uses Token.Keyword.
        type_name = str(ttype)
        if "Keyword" in type_name:
            raw.append(RawTok("keyword", value.lower(), start_line))
            continue
        if ttype in Text or ttype in Whitespace:
            continue
        if value.isidentifier():
            raw.append(RawTok("name", value, start_line))
    return raw


def _name_kind(ttype: object) -> str:
    # Order matters: Magic and Builtin are subclasses of Name.
    # "preserved" keeps the spelling. "name" is renamed to an ID token.
    if ttype in Name.Builtin or ttype in Name.Builtin.Pseudo or ttype in Name.Exception:
        return "preserved"
    if ttype in Name.Function.Magic:
        return "preserved"
    return "name"


def _string_payload(ttype: object, value: str) -> str | None:
    if ttype in String.Interpol or ttype in String.Affix:
        return None
    stripped = value.strip()
    if stripped in {'"', "'", '"""', "'''", "`"}:
        return None
    if stripped and set(stripped) <= set("\"'`"):
        return None
    return _unwrap_string(value)


def _unwrap_string(value: str) -> str:
    """Drop one layer of quotes so Python (split quotes) and JS (quotes included) agree."""
    text = value.strip()
    for quote in ('"""', "'''", "`", '"', "'"):
        if text.startswith(quote) and text.endswith(quote) and len(text) >= len(quote) * 2:
            return text[len(quote) : -len(quote)]
    return value


def _norm_name(value: str, names: dict[str, str]) -> str:
    if value in PRESERVED_NAMES:
        return value
    if value not in names:
        names[value] = f"ID{len(names)}"
    return names[value]


def _norm_number(raw: str) -> str:
    text = raw.lower().replace("_", "").rstrip("l")
    try:
        if text.startswith(("0x", "0b", "0o")) or "." not in text and "e" not in text:
            base = 10
            if text.startswith("0x"):
                base = 16
            elif text.startswith("0b"):
                base = 2
            elif text.startswith("0o"):
                base = 8
            value = int(text, base)
            if -1 <= value <= 10:
                return str(value)
            return "NUM"
        value_f = float(text)
        if value_f == int(value_f) and -1 <= int(value_f) <= 10:
            return str(int(value_f))
    except ValueError:
        return "NUM"
    return "NUM"


def _lexer(filename: str, source: str, language: str) -> Any:
    try:
        if language:
            return get_lexer_by_name(language)
    except ClassNotFound:
        pass
    try:
        return get_lexer_for_filename(filename, source)
    except ClassNotFound:
        return get_lexer_by_name("text")


def _python_ranges(source: str) -> list[tuple[int, int]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    spans: list[tuple[int, int]] = []

    def take_function(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            if node.decorator_list:
                start = min(start, min(item.lineno for item in node.decorator_list))
            end = node.end_lineno if isinstance(node.end_lineno, int) else start
            spans.append((start, end))
            return
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    take_function(child)
                else:
                    start_line = getattr(child, "lineno", None)
                    if not isinstance(start_line, int):
                        continue
                    end_line = getattr(child, "end_lineno", None)
                    spans.append((start_line, end_line if isinstance(end_line, int) else start_line))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            take_function(node)
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        start = getattr(node, "lineno", None)
        if start is None:
            continue
        spans.append((start, getattr(node, "end_lineno", None) or start))
    return spans


def _brace_ranges(source: str) -> list[tuple[int, int]]:
    lines = source.splitlines()
    spans: list[tuple[int, int]] = []
    covered: set[int] = set()
    index = 0
    while index < len(lines):
        if not _FUNC_LINE.match(lines[index]):
            index += 1
            continue
        depth = 0
        seen_brace = False
        end = index
        for cursor in range(index, len(lines)):
            end = cursor
            for char in lines[cursor]:
                if char == "{":
                    depth += 1
                    seen_brace = True
                elif char == "}":
                    depth -= 1
            if seen_brace and depth <= 0:
                break
        spans.append((index + 1, end + 1))
        covered.update(range(index, end + 1))
        index = end + 1
    # Module-level runs that are not inside a function.
    run_start: int | None = None
    for index, _line in enumerate(lines):
        if index in covered or not lines[index].strip() or _IMPORT_LINE.match(lines[index]):
            if run_start is not None and index - run_start >= 4:
                spans.append((run_start + 1, index))
            run_start = None
            continue
        if run_start is None:
            run_start = index
    if run_start is not None and len(lines) - run_start >= 4:
        spans.append((run_start + 1, len(lines)))
    return spans
