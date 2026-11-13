"""Controlled edits used by the evaluation harness.

These functions build labeled pairs. They are not a claim about how any real
project was produced. Rename leaves language keywords, builtins, exceptions,
and dunder names alone, which is the same set the tokenizer keeps verbatim.
"""

from __future__ import annotations

import ast
import io
import tokenize

from lineage.lexicon import PRESERVED_NAMES


def rename_user_identifiers(source: str, prefix: str = "n") -> str:
    mapping: dict[str, str] = {}

    def fresh(name: str) -> str:
        if name in PRESERVED_NAMES:
            return name
        if name not in mapping:
            mapping[name] = f"{prefix}{len(mapping)}"
        return mapping[name]

    pieces: list[tuple[int, str]] = []
    reader = io.StringIO(source).readline
    for token in tokenize.generate_tokens(reader):
        if token.type == tokenize.NAME:
            pieces.append((tokenize.NAME, fresh(token.string)))
        else:
            pieces.append((token.type, token.string))
    return tokenize.untokenize(pieces)


def reformat_loose(source: str) -> str:
    """Change indentation and blank lines without changing tokens that matter."""
    output: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith(("def ", "class ", "async def ")) and output and output[-1].strip():
            output.append("")
        indent = len(line) - len(line.lstrip(" "))
        new_indent = (indent // 4) * 2
        output.append((" " * new_indent) + line.lstrip(" ").rstrip())
    return "\n".join(output).strip() + "\n"


def reorder_toplevel(source: str) -> str:
    """Reverse the order of top-level functions and classes. Imports stay put."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    lines = source.splitlines(keepends=True)
    spans: list[tuple[int, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            if getattr(node, "decorator_list", None):
                start = min(start, min(item.lineno for item in node.decorator_list))
            spans.append((start, node.end_lineno or start))
    if len(spans) < 2:
        return source
    first = min(start for start, _end in spans)
    header = "".join(lines[: first - 1])
    blocks = ["".join(lines[start - 1 : end]) for start, end in spans]
    body = "\n".join(block.rstrip() for block in reversed(blocks))
    return header + body + "\n"


def keep_function_fraction(source: str, fraction: float) -> str:
    """Keep the first `fraction` of top-level functions and classes."""
    if fraction >= 1:
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    if len(functions) < 2:
        return source
    keep_count = max(1, int(round(len(functions) * fraction)))
    keep_count = min(keep_count, len(functions) - 1) if fraction < 1 else len(functions)
    drop = functions[keep_count:]
    lines = source.splitlines(keepends=True)
    spans: list[tuple[int, int]] = []
    for node in drop:
        start = node.lineno
        if getattr(node, "decorator_list", None):
            start = min(start, min(item.lineno for item in node.decorator_list))
        spans.append((start, node.end_lineno or start))
    for start, end in sorted(spans, reverse=True):
        del lines[start - 1 : end]
    return "".join(lines)


def paraphrase_strings(source: str) -> str:
    """Replace string literals so artifact overlap falls and token shape stays."""
    count = 0
    pieces: list[tuple[int, str]] = []
    reader = io.StringIO(source).readline
    for token in tokenize.generate_tokens(reader):
        if token.type == tokenize.STRING:
            count += 1
            pieces.append((tokenize.STRING, f'"s{count}"'))
        else:
            pieces.append((token.type, token.string))
    return tokenize.untokenize(pieces)


def combine_rename_reformat_reorder(source: str, prefix: str = "n") -> str:
    return reorder_toplevel(reformat_loose(rename_user_identifiers(source, prefix=prefix)))
