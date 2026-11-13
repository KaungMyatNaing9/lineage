"""Resolve a local path or git URL to a tree, optionally at a revision."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from lineage.timing import revision_label

_USERINFO = re.compile(r"://[^/\s@]+@")


class LineageError(Exception):
    """A user-facing failure: bad path, failed clone, unknown revision."""


class _Materialized:
    def __init__(self) -> None:
        self._tmp: tempfile.TemporaryDirectory[str] | None = None

    def open(self) -> Path:
        if self._tmp is None:
            self._tmp = tempfile.TemporaryDirectory(prefix="lineage-")
        return Path(self._tmp.name)

    def close(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None


def resolve_tree(spec: str, revision: str | None, work: Path, name: str) -> tuple[Path, str | None]:
    """Return a directory or file to read, plus a revision label when git knows one."""
    path = Path(spec)
    if path.exists():
        if revision:
            destination = work / name
            _clone(str(path.resolve()), destination)
            _checkout(destination, revision)
            return destination, revision_label(destination)
        label_root = path if path.is_dir() else path.parent
        return path.resolve(), revision_label(label_root)
    if _looks_like_git_url(spec):
        destination = work / name
        _clone(spec, destination)
        if revision:
            _checkout(destination, revision)
        return destination, revision_label(destination)
    raise LineageError(f"not a local path or a git URL: {spec}")


def _looks_like_git_url(spec: str) -> bool:
    return spec.startswith(("https://", "http://", "git@", "ssh://", "git://")) or spec.endswith(".git")


def _clone(url: str, destination: Path) -> None:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", "clone", "--quiet", url, str(destination)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    if result.returncode != 0:
        detail = _redact((result.stderr or result.stdout or "git clone failed").strip())
        raise LineageError(f"could not clone {_redact(url)}: {detail}")


def _checkout(destination: Path, revision: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(destination), "checkout", "--quiet", "--detach", revision],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = _redact((result.stderr or result.stdout or "checkout failed").strip())
        raise LineageError(f"could not check out {revision}: {detail}")


def _redact(text: str) -> str:
    return _USERINFO.sub("://", text)
