"""Fingerprints of ordinary idioms, excluded from token and structural scores.

The snippets are intentionally generic. A project that shares only these shapes
does not receive a high score from them. Distinctive project code is unaffected
because its grams are different.
"""

from __future__ import annotations

from lineage.structural import control_events, python_ast_streams
from lineage.tokenize import gram_weight, normalized_chunks
from lineage.winnow import fingerprint_stream

_CACHE: dict[tuple[str, int, int], set[str]] = {}

SNIPPETS: tuple[tuple[str, str, str], ...] = (
    (
        "python",
        "read.py",
        '''
def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()

def write_text(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
''',
    ),
    (
        "python",
        "main.py",
        '''
def main(argv):
    if not argv:
        return 0
    for arg in argv:
        if arg.startswith("-"):
            continue
        handle(arg)
    return 0

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
''',
    ),
    (
        "python",
        "init.py",
        '''
class Box:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value
''',
    ),
    (
        "javascript",
        "read.js",
        '''
function readText(path) {
  const handle = open(path, "utf-8");
  try {
    return handle.read();
  } finally {
    handle.close();
  }
}
''',
    ),
)


def token_baseline(k: int, window: int) -> set[str]:
    key = ("token", k, window)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    found: set[str] = set()
    for language, name, source in SNIPPETS:
        for chunk in normalized_chunks(source, name, language):
            texts = [token.text for token in chunk]
            lines = [token.line for token in chunk]
            for fingerprint in fingerprint_stream(
                texts, lines, file=name, k=k, window=window, weight_of=gram_weight
            ):
                found.add(fingerprint.digest)
    _CACHE[key] = found
    return found


def structural_baseline(k: int, window: int) -> set[str]:
    key = ("struct", k, window)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    found: set[str] = set()
    for language, name, source in SNIPPETS:
        for texts, lines in _control_chunks(source, name, language):
            for fingerprint in fingerprint_stream(
                texts, lines, file=name, k=k, window=window, weight_of=lambda _gram: 1.0
            ):
                found.add("c:" + fingerprint.digest)
        if language == "python":
            for texts, lines in python_ast_streams(source, 0):
                for fingerprint in fingerprint_stream(
                    texts, lines, file=name, k=k, window=window, weight_of=lambda _gram: 1.0
                ):
                    found.add("a:" + fingerprint.digest)
    _CACHE[key] = found
    return found


def _control_chunks(source: str, filename: str, language: str) -> list[tuple[list[str], list[int]]]:
    events = control_events(source, filename, language, 0)
    if not events:
        return []
    texts = [label for label, _line in events]
    lines = [line for _label, line in events]
    return [(texts, lines)]
