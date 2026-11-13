from __future__ import annotations

from pathlib import Path

from lineage.artifacts import extract_artifacts, identifier_weight, string_weight
from lineage.compare import compare_paths
from lineage.discover import load_corpus


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_common_names_weigh_less_than_rare_names() -> None:
    assert identifier_weight("value") == 0.0
    assert identifier_weight("get_value") < identifier_weight("flange_torque")
    assert identifier_weight("xqz_flange_torque") > 1.0
    assert string_weight("error") == 0.0
    assert string_weight("flange torque exceeds budget") > 1.0


def test_shared_rare_string_and_typo_raise_the_artifact_score(tmp_path: Path) -> None:
    shared = (
        "def prepare(reading):\n"
        "    # the seperator is applied before truncating the flange label\n"
        '    if reading < 0:\n'
        '        raise ValueError("flange torque exceeds 48271 mN")\n'
        "    return reading\n"
    )
    other = (
        "def prepare(reading):\n"
        "    if reading < 0:\n"
        '        raise ValueError("negative")\n'
        "    return reading\n"
    )
    left = tmp_path / "left"
    right = tmp_path / "right"
    unrelated = tmp_path / "unrelated"
    _write(left, "mod.py", shared)
    _write(right, "mod.py", shared)
    _write(unrelated, "mod.py", other)
    same = compare_paths(left, right)
    different = compare_paths(left, unrelated)
    assert same.signal("rare_artifacts").score == 1.0
    assert (different.signal("rare_artifacts").score or 0) < 0.2
    details = " ".join(item.detail for item in same.signal("rare_artifacts").evidence)
    assert "48271" in details
    assert "seperator" in details


def test_a_common_word_shared_by_many_files_is_downweighted(tmp_path: Path) -> None:
    rare = 'MARKER = "xqz flange torque 48271"\n'
    common = 'NOTE = "invalid value"\n'
    left = tmp_path / "left"
    right = tmp_path / "right"
    for index in range(6):
        _write(left, f"f{index}.py", common + (rare if index == 0 else "x = 1\n"))
        _write(right, f"g{index}.py", common + (rare if index == 0 else "y = 2\n"))
    corpus = load_corpus(left)
    texts = " ".join(item.display for item in extract_artifacts(corpus.files[0]))
    assert "48271" in texts or "xqz" in texts
    report = compare_paths(left, right)
    details = " ".join(item.detail for item in report.signal("rare_artifacts").evidence)
    assert "48271" in details
    # The shared ordinary phrase is either absent or lighter than the rare marker.
    rare_score = max(item.score for item in report.signal("rare_artifacts").evidence)
    ordinary = [item for item in report.signal("rare_artifacts").evidence if "invalid value" in item.detail]
    if ordinary:
        assert ordinary[0].score < rare_score
