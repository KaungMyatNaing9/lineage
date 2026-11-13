from __future__ import annotations

from pathlib import Path

from lineage.compare import compare_paths
from lineage.transforms import (
    combine_rename_reformat_reorder,
    reformat_loose,
    rename_user_identifiers,
    reorder_toplevel,
)

_ORIGINAL = '''
def accumulate_readings(readings, scale, floor):
    total = 0
    skipped = 0
    for reading in readings:
        if reading is None:
            skipped += 1
            continue
        if reading > floor:
            total += reading * scale
        else:
            total += reading
    return total, skipped


def clamp_span(start, end, limit):
    if start > end:
        start, end = end, start
    width = end - start
    if width > limit:
        end = start + limit
    return start, end


def describe_budget(amount, limit):
    if amount > limit:
        return "over the flange budget"
    if amount == limit:
        return "at the flange budget"
    return "under the flange budget"
'''

_INDEPENDENT = '''
def ring_push(buffer, head, value, capacity):
    buffer[head] = value
    return (head + 1) % capacity


def ring_pop(buffer, tail, capacity):
    value = buffer[tail]
    buffer[tail] = None
    return value, (tail + 1) % capacity
'''


def _plant(root: Path, source: str, tests: str | None = None) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "mod.py").write_text(source, encoding="utf-8")
    if tests is not None:
        (root / "tests").mkdir()
        (root / "tests" / "test_mod.py").write_text(tests, encoding="utf-8")


def test_rename_reformat_and_reorder_stay_high(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    _plant(original, _ORIGINAL)
    _plant(rewrite, combine_rename_reformat_reorder(_ORIGINAL))
    report = compare_paths(original, rewrite)
    token = report.signal("token_fingerprint")
    structural = report.signal("structural")
    assert token.score is not None and token.score >= 0.9
    assert token.metrics["rewrite_containment"] >= 0.9
    assert structural.score is not None and structural.score >= 0.9
    assert token.evidence
    assert ":" in token.evidence[0].to_dict()["original"]


def test_each_edit_alone_preserves_token_overlap(tmp_path: Path) -> None:
    original = tmp_path / "original"
    _plant(original, _ORIGINAL)
    for transform in (rename_user_identifiers, reformat_loose, reorder_toplevel):
        rewrite = tmp_path / transform.__name__
        _plant(rewrite, transform(_ORIGINAL))
        report = compare_paths(original, rewrite)
        score = report.signal("token_fingerprint").score
        assert score is not None and score >= 0.9, transform.__name__


def test_independent_code_stays_low(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    _plant(original, _ORIGINAL)
    _plant(rewrite, _INDEPENDENT)
    report = compare_paths(original, rewrite)
    for signal_id in ("token_fingerprint", "structural", "rare_artifacts"):
        score = report.signal(signal_id).score
        assert score is None or score < 0.15, signal_id


def test_shared_license_header_does_not_create_a_high_score(tmp_path: Path) -> None:
    header = "# Copyright 2026 Example Author\n# SPDX-License-Identifier: MIT\n\n"
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    _plant(original, header + _ORIGINAL)
    _plant(rewrite, header + _INDEPENDENT)
    report = compare_paths(original, rewrite)
    score = report.signal("token_fingerprint").score
    assert score is None or score < 0.15


def test_identical_body_with_different_headers_stays_high(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    _plant(original, "# Copyright 2024 Left\n# SPDX-License-Identifier: MIT\n\n" + _ORIGINAL)
    _plant(rewrite, "# Copyright 2026 Right\n# SPDX-License-Identifier: Apache-2.0\n\n" + _ORIGINAL)
    report = compare_paths(original, rewrite)
    score = report.signal("token_fingerprint").score
    assert score is not None and score >= 0.9
