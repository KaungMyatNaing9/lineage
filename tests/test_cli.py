from __future__ import annotations

import json
from pathlib import Path

from lineage.cli import main


def test_compare_writes_three_files(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    original.mkdir()
    rewrite.mkdir()
    body = (
        "def accumulate(readings, scale):\n"
        "    total = 0\n"
        "    for reading in readings:\n"
        "        if reading > scale:\n"
        "            total += reading * scale\n"
        "        else:\n"
        "            total += reading\n"
        "    return total\n"
    )
    (original / "mod.py").write_text(body, encoding="utf-8")
    (rewrite / "mod.py").write_text(body, encoding="utf-8")
    prefix = tmp_path / "report"
    code = main(["compare", str(original), str(rewrite), "-o", str(prefix), "--no-timing"])
    assert code == 0
    payload = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    assert payload["signals"][0]["id"] == "token_fingerprint"
    assert prefix.with_suffix(".html").exists()
    assert prefix.with_suffix(".md").exists()


def test_missing_path_is_an_error(tmp_path: Path) -> None:
    code = main(["compare", str(tmp_path / "missing"), str(tmp_path), "-o", str(tmp_path / "out")])
    assert code == 2


def test_compare_at_two_revisions(tmp_path: Path) -> None:
    import os
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, capture_output=True)
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = "2020-01-01T00:00:00"
    env["GIT_COMMITTER_DATE"] = "2020-01-01T00:00:00"
    git = ["git", "-C", str(repo), "-c", "user.email=lineage@example.com", "-c", "user.name=Lineage"]
    first = (
        "def accumulate(readings, scale):\n"
        "    total = 0\n"
        "    for reading in readings:\n"
        "        if reading > scale:\n"
        "            total += reading * scale\n"
        "        else:\n"
        "            total += reading\n"
        "    return total\n"
    )
    second = (
        "def ring_push(buffer, head, value, capacity):\n"
        "    buffer[head] = value\n"
        "    return (head + 1) % capacity\n"
    )
    (repo / "mod.py").write_text(first, encoding="utf-8")
    subprocess.run([*git, "add", "mod.py"], check=True, env=env, capture_output=True)
    subprocess.run([*git, "commit", "-q", "-m", "first"], check=True, env=env, capture_output=True)
    older = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    (repo / "mod.py").write_text(second, encoding="utf-8")
    subprocess.run([*git, "add", "mod.py"], check=True, env=env, capture_output=True)
    subprocess.run([*git, "commit", "-q", "-m", "second"], check=True, env=env, capture_output=True)
    newer = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    prefix = tmp_path / "rev-report"
    code = main(
        [
            "compare",
            str(repo),
            str(repo),
            "--rev-a",
            older,
            "--rev-b",
            newer,
            "-o",
            str(prefix),
            "--no-timing",
        ]
    )
    assert code == 0
    payload = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    token = next(item for item in payload["signals"] if item["id"] == "token_fingerprint")
    assert token["score"] is None or token["score"] < 0.2


def test_help_exits_zero() -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
