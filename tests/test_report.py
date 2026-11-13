from __future__ import annotations

import json
import re
from pathlib import Path

from lineage.compare import compare_paths
from lineage.models import DISCLAIMER
from lineage.report import render_html, render_json, render_markdown, write_report

_BANNED = re.compile(r"plagiar|copied|stolen|infring|theft", re.IGNORECASE)


def _project(root: Path, name: str, body: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_reports_include_disclaimer_and_avoid_accusatory_words(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    body = (
        "def accumulate(readings, scale):\n"
        "    total = 0\n"
        "    for reading in readings:\n"
        "        if reading > scale:\n"
        '            label = "flange torque table"\n'
        "            total += reading * scale\n"
        "        else:\n"
        "            total += reading\n"
        "    return total\n"
    )
    hostile = 'def run():\n    return "<script>alert(1)</script>"\n'
    _project(original, "mod.py", body + hostile)
    _project(rewrite, "mod.py", body + hostile)
    report = compare_paths(original, rewrite)
    blob = render_markdown(report) + render_html(report) + report.narrative
    for signal in report.signals:
        blob += signal.summary + " ".join(signal.notes)
    assert DISCLAIMER in render_markdown(report)
    assert DISCLAIMER in render_html(report)
    assert _BANNED.search(blob) is None
    page = render_html(report)
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page
    payload = json.loads(render_json(report))
    assert payload["schema_version"] == 1
    assert payload["disclaimer"] == DISCLAIMER
    assert {item["id"] for item in payload["signals"]} == {
        "token_fingerprint",
        "structural",
        "rare_artifacts",
        "test_cases",
        "git_timing",
    }


def test_write_report_prefixes(tmp_path: Path) -> None:
    original = tmp_path / "original"
    rewrite = tmp_path / "rewrite"
    _project(original, "mod.py", "def run(value):\n    return value + 1\n")
    _project(rewrite, "mod.py", "def run(value):\n    return value + 1\n")
    report = compare_paths(original, rewrite)
    paths = write_report(report, tmp_path / "out" / "demo")
    assert [path.suffix for path in paths] == [".md", ".json", ".html"]
    assert all(path.exists() for path in paths)
