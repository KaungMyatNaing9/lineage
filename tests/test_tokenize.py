from __future__ import annotations

from lineage.tokenize import chunk_ranges, gram_weight, normalize_source
from lineage.transforms import reformat_loose, rename_user_identifiers


def _texts(source: str) -> list[str]:
    return [token.text for token in normalize_source(source, "mod.py", "python")]


def test_rename_and_whitespace_do_not_change_normalized_tokens() -> None:
    source = (
        "def accumulate(readings, scale):\n"
        "    total = 0\n"
        "    for reading in readings:\n"
        "        if reading > scale:\n"
        "            total += reading * scale\n"
        "    return total\n"
    )
    renamed = rename_user_identifiers(source, prefix="v")
    assert "accumulate" not in renamed
    assert _texts(source) == _texts(renamed)
    assert _texts(source) == _texts(reformat_loose(source))


def test_comments_and_string_contents_are_normalized_away() -> None:
    left = 'def run(value):\n    # note\n    label = "alpha"\n    return label\n'
    right = "def run(value):\n    label = 'beta'\n    return label\n"
    assert _texts(left) == _texts(right)
    assert "STR" in _texts(left)
    assert "alpha" not in _texts(left)


def test_imports_are_not_fingerprinted_as_tokens() -> None:
    source = "import os\nfrom pathlib import Path\n\ndef run(value):\n    return value\n"
    texts = _texts(source)
    assert "import" not in texts
    assert "os" not in texts
    assert "return" in texts


def test_builtins_stay_and_user_names_become_ids() -> None:
    texts = _texts("def run(values):\n    return len(values)\n")
    assert "len" in texts
    assert "run" not in texts
    assert any(token.startswith("ID") for token in texts)


def test_small_numbers_stay_and_large_numbers_collapse() -> None:
    texts = _texts("def run():\n    return (1, 48271)\n")
    assert "1" in texts
    assert "NUM" in texts
    assert "48271" not in texts


def test_string_table_grams_are_dropped() -> None:
    gram = ("STR", ":", "STR", ",", "STR", ":", "STR", ",", "STR")
    assert gram_weight(gram) == 0.0
    informative = ("def", "ID0", "(", "ID1", ")", ":", "return", "ID1", "+", "1")
    assert gram_weight(informative) == 1.0


def test_python_functions_are_separate_chunks() -> None:
    source = "import os\n\ndef alpha():\n    return 1\n\ndef beta():\n    return 2\n"
    ranges = chunk_ranges(source, "python")
    assert ranges == [(3, 4), (6, 7)]
