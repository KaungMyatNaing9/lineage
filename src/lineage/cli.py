"""Command line for Lineage."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from lineage import __version__
from lineage.compare import compare_paths
from lineage.gitio import LineageError, resolve_tree
from lineage.models import DISCLAIMER, Settings
from lineage.report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lineage",
        description=(
            "Compare an original codebase with another codebase and write a "
            "similarity report. The report does not reach a legal conclusion."
        ),
    )
    parser.add_argument("--version", action="version", version=f"lineage {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare", help="compare two local paths or git URLs")
    compare.add_argument("original", help="local path or git URL of the original")
    compare.add_argument("rewrite", help="local path or git URL of the other codebase")
    compare.add_argument("--rev-a", default=None, help="revision to check out for the original")
    compare.add_argument("--rev-b", default=None, help="revision to check out for the other codebase")
    compare.add_argument(
        "-o",
        "--output",
        default="lineage-report",
        help="output prefix (writes PREFIX.md, PREFIX.json, and PREFIX.html)",
    )
    compare.add_argument("--no-timing", action="store_true", help="do not read git history")
    compare.add_argument(
        "--include-vendored",
        action="store_true",
        help="score files under vendor/ and third_party/ instead of leaving them out",
    )
    compare.add_argument("--k", type=int, default=15, help="token k-gram length (default 15)")
    compare.add_argument("--window", type=int, default=5, help="winnowing window (default 5)")
    compare.add_argument("--max-files", type=int, default=800)
    compare.add_argument("--max-file-bytes", type=int, default=1_000_000)

    args = parser.parse_args(argv)
    if args.command == "compare":
        return _compare(args)
    parser.error(f"unknown command {args.command}")
    return 2


def _compare(args: argparse.Namespace) -> int:
    if args.k < 1 or args.window < 1:
        print("k and window must be at least 1", file=sys.stderr)
        return 2
    settings = Settings(
        token_k=args.k,
        token_window=args.window,
        include_vendored=args.include_vendored,
        timing=not args.no_timing,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
    )
    try:
        with tempfile.TemporaryDirectory(prefix="lineage-") as tmp:
            work = Path(tmp)
            original, rev_a = resolve_tree(args.original, args.rev_a, work, "original")
            rewrite, rev_b = resolve_tree(args.rewrite, args.rev_b, work, "rewrite")
            report = compare_paths(
                original,
                rewrite,
                settings=settings,
                original_label=args.original,
                rewrite_label=args.rewrite,
                original_revision=rev_a,
                rewrite_revision=rev_b,
            )
            # Excerpts are already on the report, so the temporary clone can disappear.
            written = write_report(report, Path(args.output))
    except LineageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for signal in report.signals:
        score = "n/a" if signal.score is None else f"{signal.score:.2f}"
        print(f"{signal.name}: {signal.band} ({score})")
    print(DISCLAIMER)
    print("Wrote " + ", ".join(str(path) for path in written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
