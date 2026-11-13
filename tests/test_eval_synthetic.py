"""Lock the synthetic separation so a later edit cannot quietly collapse it."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from run_eval import summarize, synthetic_rows  # noqa: E402


def test_synthetic_pairs_separate() -> None:
    rows = synthetic_rows()
    summary = summarize(rows)
    signals = summary["signals"]
    assert isinstance(signals, dict)
    token = signals["token_fingerprint"]
    structural = signals["structural"]
    artifacts = signals["rare_artifacts"]
    assert isinstance(token, dict) and isinstance(structural, dict) and isinstance(artifacts, dict)
    assert token["full_auc"] == 1.0
    full = token["full"]
    independent = token["independent"]
    assert isinstance(full, dict) and isinstance(independent, dict)
    assert float(full["min"]) >= 0.8
    assert float(independent["max"]) < 0.05
    assert structural["full_auc"] is not None and float(structural["full_auc"]) >= 0.95
    assert not token["independent_at_or_above_0_30"]
    assert not structural["independent_at_or_above_0_30"]
    assert not artifacts["independent_at_or_above_0_30"]
    cross = next(row for row in rows if row["id"] == "slug_vs_slug_js")
    signals_row = cross["signals"]
    assert isinstance(signals_row, dict)
    token = signals_row["token_fingerprint"]
    rare = signals_row["rare_artifacts"]
    tests = signals_row["test_cases"]
    assert isinstance(token, dict) and isinstance(rare, dict) and isinstance(tests, dict)
    assert float(token["score"]) < 0.05
    assert float(rare["score"]) > float(token["score"])
    assert float(tests["score"]) > 0.5
