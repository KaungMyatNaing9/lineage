"""Report records and the fixed score bands for this version."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "BAND_HIGH",
    "BAND_LOW",
    "BAND_MODEST",
    "BAND_SUBSTANTIAL",
    "DISCLAIMER",
    "HOW_TO_READ",
    "Evidence",
    "Report",
    "Settings",
    "SideInfo",
    "SignalResult",
    "band_for",
]

# Fixed before any evaluation run. Descriptive labels, not a decision threshold.
BAND_LOW = 0.10
BAND_MODEST = 0.30
BAND_SUBSTANTIAL = 0.60
BAND_HIGH = 0.60

DISCLAIMER = (
    "Lineage measures textual and structural similarity between two codebases "
    "and shows the evidence behind each score. Similarity can come from a shared "
    "specification, a standard algorithm, common idioms, generated code, a "
    "vendored library, or two independent implementations of the same idea. "
    "This report does not determine authorship, does not reach a legal conclusion, "
    "and is not legal advice."
)

HOW_TO_READ = (
    f"Each signal has its own score from 0 to 1 (weighted Dice unless a signal "
    f"says otherwise). 0 means that signal did not overlap. 1 means the two sides "
    f"look the same under that signal. Rewrite containment near 1 means most of "
    f"the rewrite's signal is also present in the original, which happens when "
    f"the rewrite is a subset. Bands for this version: low below {BAND_LOW:.2f}, "
    f"modest below {BAND_MODEST:.2f}, substantial below {BAND_SUBSTANTIAL:.2f}, "
    f"high at or above {BAND_HIGH:.2f}. A missing score means the signal did not "
    f"have enough material, or did not apply. Bands are labels for reading this "
    f"report, not a decision threshold."
)


def band_for(score: float | None) -> str:
    """Map a score to a fixed band. None means the signal could not be scored."""
    if score is None:
        return "insufficient"
    if score < BAND_LOW:
        return "low"
    if score < BAND_MODEST:
        return "modest"
    if score < BAND_SUBSTANTIAL:
        return "substantial"
    return "high"


@dataclass
class Settings:
    """Knobs that change fingerprints. Recorded in every report."""

    token_k: int = 15
    token_window: int = 5
    struct_k: int = 6
    struct_window: int = 4
    include_vendored: bool = False
    timing: bool = True
    timing_window_days: int = 180
    max_file_bytes: int = 1_000_000
    max_files: int = 800
    evidence_limit: int = 24

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_k": self.token_k,
            "token_window": self.token_window,
            "struct_k": self.struct_k,
            "struct_window": self.struct_window,
            "include_vendored": self.include_vendored,
            "timing": self.timing,
            "timing_window_days": self.timing_window_days,
            "max_file_bytes": self.max_file_bytes,
            "max_files": self.max_files,
            "evidence_limit": self.evidence_limit,
            "band_low": BAND_LOW,
            "band_modest": BAND_MODEST,
            "band_substantial": BAND_SUBSTANTIAL,
        }


@dataclass
class Evidence:
    original_path: str
    original_start: int
    original_end: int
    rewrite_path: str
    rewrite_start: int
    rewrite_end: int
    score: float
    detail: str
    original_excerpt: str = ""
    rewrite_excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": _span(self.original_path, self.original_start, self.original_end),
            "rewrite": _span(self.rewrite_path, self.rewrite_start, self.rewrite_end),
            "original_path": self.original_path,
            "original_start": self.original_start,
            "original_end": self.original_end,
            "rewrite_path": self.rewrite_path,
            "rewrite_start": self.rewrite_start,
            "rewrite_end": self.rewrite_end,
            "score": round(self.score, 4),
            "detail": self.detail,
            "original_excerpt": self.original_excerpt,
            "rewrite_excerpt": self.rewrite_excerpt,
        }


def _span(path: str, start: int, end: int) -> str:
    if start <= 0:
        return path
    if end <= start:
        return f"{path}:{start}"
    return f"{path}:{start}-{end}"


@dataclass
class SignalResult:
    id: str
    name: str
    score: float | None
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    band: str = ""

    def __post_init__(self) -> None:
        if not self.band:
            self.band = band_for(self.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "score": None if self.score is None else round(float(self.score), 4),
            "band": self.band,
            "summary": self.summary,
            "metrics": _round_obj(self.metrics),
            "notes": list(self.notes),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass
class SideInfo:
    label: str
    path: str
    revision: str | None
    files_compared: int
    files_skipped: int
    non_source_ignored: int
    loc: int
    test_loc: int
    languages: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": self.path,
            "revision": self.revision,
            "files_compared": self.files_compared,
            "files_skipped": self.files_skipped,
            "non_source_ignored": self.non_source_ignored,
            "loc": self.loc,
            "test_loc": self.test_loc,
            "languages": self.languages,
        }


@dataclass
class Report:
    original: SideInfo
    rewrite: SideInfo
    signals: list[SignalResult]
    narrative: str
    parameters: dict[str, Any]
    skipped: list[dict[str, str]] = field(default_factory=list)
    generated_at: str = ""

    def signal(self, signal_id: str) -> SignalResult:
        for item in self.signals:
            if item.id == signal_id:
                return item
        raise KeyError(signal_id)


def _round_obj(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {str(key): _round_obj(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_round_obj(inner) for inner in value]
    return value
