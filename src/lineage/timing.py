"""When similar files showed up in git history.

This is not a similarity score. It asks a narrower question: among file pairs
that already share a strong token alignment, how many of the rewrite files
were introduced in one commit, fully formed, during a window after the
original file. No strong alignment, or no git history, means the signal does
not apply. It is never treated as low similarity just because history is absent.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from lineage.evidence import FileMatch
from lineage.models import Evidence


@dataclass
class TimingRow:
    original_path: str
    rewrite_path: str
    original_timestamp: int
    rewrite_timestamp: int
    delta_days: float
    fully_formed: bool | None
    aligned: bool
    original_commit: str
    rewrite_commit: str


def git_available(root: Path) -> bool:
    if not root.exists():
        return False
    probe = _git(root, "rev-parse", "--is-inside-work-tree")
    return probe.returncode == 0 and probe.stdout.strip() == "true"


def revision_label(root: Path) -> str | None:
    """HEAD sha, with a note when the working tree is dirty."""
    if not git_available(root if root.is_dir() else root.parent):
        return None
    base = root if root.is_dir() else root.parent
    head = _git(base, "rev-parse", "HEAD")
    if head.returncode != 0:
        return None
    sha = head.stdout.strip()
    status = _git(base, "status", "--porcelain")
    if status.returncode == 0 and status.stdout.strip():
        return f"{sha} (working tree differs from HEAD)"
    return sha


def time_alignments(
    original_root: Path,
    rewrite_root: Path,
    pairs: list[FileMatch],
    *,
    window_days: int,
    min_containment: float = 0.5,
    min_shared: int = 5,
) -> tuple[list[TimingRow], int]:
    """Return timing rows and how many strong pairs lacked a git introduction.

    `pairs` are token file-alignment rows.
    """
    rows: list[TimingRow] = []
    missing = 0
    for pair in pairs:
        if pair["containment"] < min_containment or pair["shared_fingerprints"] < min_shared:
            continue
        original_path = pair["original_path"]
        rewrite_path = pair["rewrite_path"]
        left = _birth(original_root, original_path)
        right = _birth(rewrite_root, rewrite_path)
        if left is None or right is None:
            missing += 1
            continue
        delta_days = (right[0] - left[0]) / 86400.0
        formed = _fully_formed(rewrite_root, right[1], rewrite_path)
        aligned = formed is True and 0 <= delta_days <= window_days
        rows.append(
            TimingRow(
                original_path=original_path,
                rewrite_path=rewrite_path,
                original_timestamp=left[0],
                rewrite_timestamp=right[0],
                delta_days=delta_days,
                fully_formed=formed,
                aligned=aligned,
                original_commit=left[1],
                rewrite_commit=right[1],
            )
        )
    return rows, missing


def timing_evidence(rows: list[TimingRow], limit: int) -> list[Evidence]:
    evidence: list[Evidence] = []
    ordered = sorted(rows, key=lambda row: (not row.aligned, abs(row.delta_days)))
    for row in ordered[:limit]:
        state = "within the window and fully formed" if row.aligned else "not both fully formed and inside the window"
        evidence.append(
            Evidence(
                original_path=row.original_path,
                original_start=1,
                original_end=1,
                rewrite_path=row.rewrite_path,
                rewrite_start=1,
                rewrite_end=1,
                score=1.0 if row.aligned else 0.0,
                detail=(
                    f"rewrite file author-date is {row.delta_days:.1f} days after the original "
                    f"file ({state}). original commit {row.original_commit[:10]}, "
                    f"rewrite commit {row.rewrite_commit[:10]}"
                ),
            )
        )
    return evidence


def _birth(root: Path, rel: str) -> tuple[int, str] | None:
    if not git_available(root):
        return None
    log = _git(root, "log", "--diff-filter=A", "--follow", "--format=%at %H", "--", rel)
    lines = [line.strip() for line in log.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    parts = lines[-1].split()
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), parts[1]
    except ValueError:
        return None


def _fully_formed(root: Path, commit: str, rel: str) -> bool | None:
    """True when the adding commit introduced at least 75% of the file's lines."""
    shown = _git(root, "show", f"{commit}:{rel}")
    if shown.returncode != 0:
        return None
    file_lines = max(1, shown.stdout.count("\n"))
    if file_lines < 15:
        return False
    numstat = _git(root, "show", "--numstat", "--format=", commit, "--", rel)
    insertions = 0
    found = False
    for line in numstat.stdout.splitlines():
        columns = line.split("\t")
        if len(columns) >= 2 and columns[0].isdigit():
            insertions += int(columns[0])
            found = True
    if not found:
        return None
    return insertions >= 0.75 * file_lines


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
