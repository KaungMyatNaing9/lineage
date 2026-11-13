from __future__ import annotations

import os
import subprocess
from pathlib import Path

from lineage.compare import compare_paths

_BODY = '''
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
'''


def _git(repo: Path, *args: str, when: str) -> None:
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = when
    env["GIT_COMMITTER_DATE"] = when
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=lineage@example.com", "-c", "user.name=Lineage", *args],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )


def _repo(path: Path, when: str, body: str) -> None:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)
    (path / "mod.py").write_text(body, encoding="utf-8")
    _git(path, "add", "mod.py", when=when)
    _git(path, "commit", "-q", "-m", "add mod", when=when)


def test_fully_formed_file_shortly_after_scores_high(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    _repo(original, "2020-01-01T00:00:00", _BODY)
    _repo(rewrite, "2020-01-11T00:00:00", _BODY)
    report = compare_paths(original, rewrite)
    timing = report.signal("git_timing")
    assert timing.score is not None and timing.score >= 0.99
    assert timing.evidence


def test_file_that_predates_the_original_is_not_aligned(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    _repo(original, "2020-06-01T00:00:00", _BODY)
    _repo(rewrite, "2019-01-01T00:00:00", _BODY)
    report = compare_paths(original, rewrite)
    timing = report.signal("git_timing")
    assert timing.score == 0.0
    assert timing.band == "low"


def test_directory_without_git_is_unavailable(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    original.mkdir()
    rewrite.mkdir()
    (original / "mod.py").write_text(_BODY, encoding="utf-8")
    (rewrite / "mod.py").write_text(_BODY, encoding="utf-8")
    report = compare_paths(original, rewrite)
    assert report.signal("git_timing").band == "unavailable"
    assert report.signal("git_timing").score is None
