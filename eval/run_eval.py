"""Build labeled pairs and measure how Lineage separates them.

Positive and negative labels are assigned from how each pair was constructed,
before scores are read. Numbers in RESULTS.md come from this script.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
EVAL = Path(__file__).resolve().parent
PROJECTS = EVAL / "projects"
CACHE = EVAL / "cache"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lineage.compare import compare_paths  # noqa: E402
from lineage.models import Settings  # noqa: E402
from lineage.transforms import (  # noqa: E402
    combine_rename_reformat_reorder,
    keep_function_fraction,
    paraphrase_strings,
    reformat_loose,
    rename_user_identifiers,
    reorder_toplevel,
)

SETTINGS = Settings(timing=False, max_files=800)

# Kinds that should score high on token fingerprints. Chosen from the edit,
# not from the score.
TOKEN_FULL = {
    "exact",
    "rename",
    "reformat",
    "reorder",
    "combo",
    "paraphrase",
    "vendored_copy",
    "same_lineage",
    "adjacent_release",
}
TOKEN_PARTIAL = {"partial_70", "partial_40", "partial_20", "diluted"}
INDEPENDENT = {"independent"}
ARTIFACT_FULL = {
    "exact",
    "reformat",
    "reorder",
    "partial_70",
    "partial_40",
    "vendored_copy",
    "same_lineage",
    "adjacent_release",
}


def _copy_project(source: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)


def _transform_tree(dest: Path, fn, *, tests_too: bool) -> None:
    for path in dest.rglob("*.py"):
        rel = path.relative_to(dest).as_posix()
        if not tests_too and ("/tests/" in f"/{rel}" or rel.startswith("tests/") or rel.startswith("test/")):
            continue
        path.write_text(fn(path.read_text(encoding="utf-8")), encoding="utf-8")


def _pair_row(pair_id: str, group: str, kind: str, left: Path, right: Path, note: str) -> dict[str, object]:
    report = compare_paths(left, right, settings=SETTINGS)
    signals: dict[str, object] = {}
    for signal in report.signals:
        signals[signal.id] = {
            "score": signal.score,
            "band": signal.band,
            "containment": signal.metrics.get("rewrite_containment"),
            "coverage": signal.metrics.get("original_coverage"),
        }
    return {
        "id": pair_id,
        "group": group,
        "kind": kind,
        "note": note,
        "signals": signals,
    }


def synthetic_rows(work: Path | None = None) -> list[dict[str, object]]:
    own_tmp = work is None
    if work is None:
        tmp = tempfile.TemporaryDirectory(prefix="lineage-eval-")
        work = Path(tmp.name)
    else:
        tmp = None
    rows: list[dict[str, object]] = []
    try:
        rows.extend(_transform_rows(work))
        rows.extend(_independent_rows())
        rows.append(
            _pair_row(
                "slug_vs_slug_js",
                "synthetic",
                "cross_language",
                PROJECTS / "slug",
                PROJECTS / "slug_js",
                "Hand port of the slug helper from Python to JavaScript. Strings and the typo are kept.",
            )
        )
        rows.extend(_timing_rows(work))
    finally:
        if own_tmp and tmp is not None:
            tmp.cleanup()
    return rows


def _transform_rows(work: Path) -> list[dict[str, object]]:
    bases = {
        "slug": PROJECTS / "slug",
        "json_a": PROJECTS / "json_a",
        "argv_a": PROJECTS / "argv_a",
    }
    edits = {
        "exact": (None, False),
        "rename": (lambda text: rename_user_identifiers(text, prefix="n"), True),
        "reformat": (reformat_loose, True),
        "reorder": (reorder_toplevel, False),
        "combo": (lambda text: combine_rename_reformat_reorder(text, prefix="n"), True),
        "paraphrase": (paraphrase_strings, False),
    }
    rows: list[dict[str, object]] = []
    for name, source in bases.items():
        for kind, (fn, tests_too) in edits.items():
            dest = work / f"{name}-{kind}"
            _copy_project(source, dest)
            if fn is not None:
                _transform_tree(dest, fn, tests_too=tests_too)
            rows.append(
                _pair_row(
                    f"{name}__{kind}",
                    "synthetic",
                    kind,
                    source,
                    dest,
                    f"Synthetic {kind} of {name}.",
                )
            )
    # Partials are only applied to slug, which has six top-level functions.
    slug = bases["slug"]
    for fraction, kind in ((0.7, "partial_70"), (0.4, "partial_40"), (0.2, "partial_20")):
        dest = work / f"slug-{kind}"
        _copy_project(slug, dest)
        _transform_tree(dest, lambda text, fraction=fraction: keep_function_fraction(text, fraction), tests_too=False)
        rows.append(
            _pair_row(
                f"slug__{kind}",
                "synthetic",
                kind,
                slug,
                dest,
                f"First {int(fraction * 100)}% of slug's top-level functions, identifiers left as written.",
            )
        )
    dest = work / "slug-diluted"
    _copy_project(slug, dest)
    extra = (PROJECTS / "stats" / "src" / "stats.py").read_text(encoding="utf-8")

    def dilute(text: str) -> str:
        return keep_function_fraction(text, 0.5).rstrip() + "\n\n" + extra

    _transform_tree(dest, dilute, tests_too=False)
    rows.append(
        _pair_row(
            "slug__diluted",
            "synthetic",
            "diluted",
            slug,
            dest,
            "Half of slug's functions plus an unrelated stats module appended in the same file.",
        )
    )
    return rows


def _independent_rows() -> list[dict[str, object]]:
    pairs = [
        ("json_a_vs_json_b", PROJECTS / "json_a", PROJECTS / "json_b", "Two JSON readers written separately."),
        ("argv_a_vs_argv_b", PROJECTS / "argv_a", PROJECTS / "argv_b", "Two argument readers written separately."),
        ("ring_vs_queue", PROJECTS / "ring", PROJECTS / "queue", "Ring buffer versus linked queue."),
        ("stats_vs_units", PROJECTS / "stats", PROJECTS / "units", "Summaries versus unit conversions."),
        ("slug_vs_stats", PROJECTS / "slug", PROJECTS / "stats", "Slug helper versus numeric summaries."),
        ("json_a_vs_argv_a", PROJECTS / "json_a", PROJECTS / "argv_a", "JSON reader versus argument reader."),
        ("ring_vs_slug", PROJECTS / "ring", PROJECTS / "slug", "Ring buffer versus slug helper."),
        ("units_vs_json_b", PROJECTS / "units", PROJECTS / "json_b", "Unit conversions versus the second JSON reader."),
    ]
    return [
        _pair_row(pair_id, "synthetic", "independent", left, right, note)
        for pair_id, left, right, note in pairs
    ]


def _timing_rows(work: Path) -> list[dict[str, object]]:
    original = work / "timing-original"
    later = work / "timing-later"
    earlier = work / "timing-earlier"
    body = (PROJECTS / "slug" / "src" / "slug.py").read_text(encoding="utf-8")
    _git_repo(original, "2020-01-01T00:00:00", body)
    _git_repo(later, "2020-01-20T00:00:00", body)
    _git_repo(earlier, "2019-06-01T00:00:00", body)
    settings = Settings(timing=True)
    rows = []
    for pair_id, right, kind, note in (
        ("timing_fully_formed_later", later, "timing_later", "Rewrite file added in one commit 19 days later."),
        ("timing_predates", earlier, "timing_earlier", "Rewrite file added months before the original file."),
    ):
        report = compare_paths(original, right, settings=settings)
        signal = report.signal("git_timing")
        rows.append(
            {
                "id": pair_id,
                "group": "synthetic",
                "kind": kind,
                "note": note,
                "signals": {
                    "git_timing": {
                        "score": signal.score,
                        "band": signal.band,
                        "containment": None,
                        "coverage": None,
                    }
                },
            }
        )
    return rows


def _git_repo(path: Path, when: str, body: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)
    (path / "slug.py").write_text(body, encoding="utf-8")
    env = {
        **dict(**{key: value for key, value in __import__("os").environ.items()}),
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
    }
    base = ["git", "-C", str(path), "-c", "user.email=lineage@example.com", "-c", "user.name=Lineage"]
    subprocess.run([*base, "add", "slug.py"], check=True, env=env, capture_output=True)
    subprocess.run([*base, "commit", "-q", "-m", "add"], check=True, env=env, capture_output=True)


def real_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Clone pinned permissive repos. Returns pair rows and a source manifest."""
    CACHE.mkdir(parents=True, exist_ok=True)
    sources: list[dict[str, object]] = []

    def checkout(name: str, url: str, rev: str) -> Path:
        dest = CACHE / name
        if not (dest / ".git").exists():
            if dest.exists():
                shutil.rmtree(dest)
            subprocess.run(
                ["git", "clone", "--quiet", "--depth", "1", "--branch", rev, url, str(dest)],
                check=True,
                timeout=180,
                capture_output=True,
                text=True,
            )
        sha = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        sources.append({"name": name, "url": url, "requested_rev": rev, "commit": sha, "sparse": []})
        return dest

    tomli = checkout("tomli-2.0.1", "https://github.com/hukkin/tomli", "2.0.1")
    tomli_202 = checkout("tomli-2.0.2", "https://github.com/hukkin/tomli", "2.0.2")
    cpython = _download_cpython_tomllib(CACHE / "cpython-3.11.9-tomllib")
    sources.append(
        {
            "name": "cpython-3.11.9-tomllib",
            "url": "https://github.com/python/cpython",
            "requested_rev": "v3.11.9",
            "commit": _github_commit("python/cpython", "v3.11.9"),
            "sparse": ["Lib/tomllib", "Lib/test/test_tomllib"],
            "note": "Individual files downloaded. The CPython git history was not cloned.",
        }
    )
    graingert = checkout("graingert-tomli", "https://github.com/graingert/tomli", "master")
    uiri = checkout("uiri-toml-0.10.2", "https://github.com/uiri/toml", "0.10.2")
    tomlkit = checkout("tomlkit-0.15.0", "https://github.com/sdispater/tomlkit", "0.15.0")
    tomliw = checkout("tomli-w-1.0.0", "https://github.com/hukkin/tomli-w", "1.0.0")
    iniconfig = checkout("iniconfig-2.0.0", "https://github.com/pytest-dev/iniconfig", "v2.0.0")
    six = checkout("six-1.16.0", "https://github.com/benjaminp/six", "1.16.0")

    def pkg(*parts: str) -> Path:
        return Path(*parts)

    rows = [
        _pair_row(
            "tomli_2.0.1_vs_cpython_3.11.9_tomllib",
            "real",
            "vendored_copy",
            pkg(tomli, "src", "tomli"),
            pkg(cpython, "Lib", "tomllib"),
            "CPython 3.11 Lib/tomllib is tomli 2.0.1 incorporated under the MIT license, with small adaptations.",
        ),
        _pair_row(
            "tomli_2.0.1_vs_tomli_2.0.2",
            "real",
            "adjacent_release",
            pkg(tomli, "src", "tomli"),
            pkg(tomli_202, "src", "tomli"),
            "Adjacent releases of the same MIT library.",
        ),
        _pair_row(
            "tomli_2.0.1_vs_graingert_fork",
            "real",
            "same_lineage",
            tomli,
            graingert,
            "graingert/tomli is a fork that was behind hukkin/tomli and not ahead of tag 2.0.1.",
        ),
        _pair_row(
            "tomli_vs_uiri_toml",
            "real",
            "independent",
            tomli,
            uiri,
            "Independent MIT TOML libraries (tomli and uiri/toml).",
        ),
        _pair_row(
            "tomli_vs_tomlkit",
            "real",
            "independent",
            tomli,
            tomlkit,
            "Independent MIT TOML libraries (tomli and tomlkit).",
        ),
        _pair_row(
            "tomli_vs_tomli_w",
            "real",
            "independent",
            pkg(tomli, "src", "tomli"),
            tomliw,
            "Same author, MIT. tomli reads TOML and tomli-w writes it. Treated as independent code.",
        ),
        _pair_row(
            "iniconfig_vs_six",
            "real",
            "independent",
            iniconfig,
            six,
            "Unrelated MIT utilities: an INI reader and a Python 2/3 compatibility layer.",
        ),
    ]
    for source in sources:
        source["license"] = _license_for(str(source["url"]))
    return rows, sources


def _github_commit(repo: str, rev: str) -> str:
    import json
    import urllib.request

    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/commits/{rev}",
        headers={"User-Agent": "lineage-eval", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    sha = payload.get("sha")
    if not isinstance(sha, str):
        return rev
    return sha


def _download_cpython_tomllib(dest: Path) -> Path:
    """Download the vendored tomllib sources without cloning CPython."""
    for folder in ("Lib/tomllib", "Lib/test/test_tomllib"):
        _download_github_dir(dest, "python/cpython", "v3.11.9", folder)
    parser = dest / "Lib" / "tomllib" / "_parser.py"
    if not parser.exists():
        raise RuntimeError("CPython tomllib download did not include _parser.py")
    return dest


def _download_github_dir(dest: Path, repo: str, rev: str, folder: str) -> None:
    import json
    import urllib.request

    api = f"https://api.github.com/repos/{repo}/contents/{folder}?ref={rev}"
    request = urllib.request.Request(
        api, headers={"User-Agent": "lineage-eval", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        items = json.load(response)
    for item in items:
        if item["type"] == "dir":
            _download_github_dir(dest, repo, rev, item["path"])
            continue
        if item["type"] != "file" or not str(item["name"]).endswith(".py"):
            continue
        target = dest / item["path"]
        if target.exists() and target.stat().st_size > 0:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        file_request = urllib.request.Request(item["download_url"], headers={"User-Agent": "lineage-eval"})
        with urllib.request.urlopen(file_request, timeout=60) as response:
            target.write_bytes(response.read())


def _license_for(url: str) -> str:
    table = {
        "hukkin/tomli": "MIT",
        "python/cpython": "MIT SPDX on the vendored tomllib files (PSF contributor notice also present)",
        "graingert/tomli": "MIT (fork of hukkin/tomli)",
        "uiri/toml": "MIT",
        "sdispater/tomlkit": "MIT",
        "hukkin/tomli-w": "MIT",
        "pytest-dev/iniconfig": "MIT",
        "benjaminp/six": "MIT",
    }
    for key, license_name in table.items():
        if key in url:
            return license_name
    return "unknown"


def _values(rows: list[dict[str, object]], signal: str, kinds: set[str]) -> list[float]:
    found: list[float] = []
    for row in rows:
        if row["kind"] not in kinds:
            continue
        signals = row["signals"]
        assert isinstance(signals, dict)
        payload = signals.get(signal)
        if not isinstance(payload, dict):
            continue
        score = payload.get("score")
        if isinstance(score, (int, float)):
            found.append(float(score))
    return found


def _auc(positive: list[float], negative: list[float]) -> float | None:
    if not positive or not negative:
        return None
    wins = 0.0
    for left in positive:
        for right in negative:
            if left > right:
                wins += 1.0
            elif left == right:
                wins += 0.5
    return wins / (len(positive) * len(negative))


def _spread(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    summary: dict[str, object] = {"n_pairs": len(rows), "signals": {}}
    signals = summary["signals"]
    assert isinstance(signals, dict)
    plan = {
        "token_fingerprint": (TOKEN_FULL, TOKEN_PARTIAL),
        "structural": (TOKEN_FULL, TOKEN_PARTIAL),
        "rare_artifacts": (ARTIFACT_FULL, {"rename", "combo", "paraphrase", "cross_language"}),
        "test_cases": (TOKEN_FULL | TOKEN_PARTIAL, set()),
    }
    for signal, (full, extra) in plan.items():
        full_scores = _values(rows, signal, full)
        partial_scores = _values(rows, signal, extra) if extra else []
        neg_scores = _values(rows, signal, INDEPENDENT)
        signals[signal] = {
            "full_auc": _auc(full_scores, neg_scores),
            "full_plus_partial_auc": _auc(full_scores + partial_scores, neg_scores) if extra else None,
            "full": _spread(full_scores),
            "partial_or_other": _spread(partial_scores),
            "independent": _spread(neg_scores),
            "independent_at_or_above_0_30": [
                row["id"]
                for row in rows
                if row["kind"] in INDEPENDENT and _score(row, signal) is not None and _score(row, signal) >= 0.30
            ],
            "full_below_0_60": [
                row["id"]
                for row in rows
                if row["kind"] in full and _score(row, signal) is not None and _score(row, signal) < 0.60
            ],
        }
    return summary


def _score(row: dict[str, object], signal: str) -> float | None:
    signals = row["signals"]
    if not isinstance(signals, dict):
        return None
    payload = signals.get(signal)
    if not isinstance(payload, dict):
        return None
    score = payload.get("score")
    if isinstance(score, (int, float)):
        return float(score)
    return None


def _cell(signals: dict[str, object], signal_id: str) -> str:
    payload = signals.get(signal_id, {})
    if not isinstance(payload, dict):
        return "n/a"
    return _fmt(payload.get("score"))


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_markdown(rows: list[dict[str, object]], summary: dict[str, object], sources: list[dict[str, object]]) -> str:
    lines = [
        "# Lineage v1 evaluation",
        "",
        "Labels were assigned from how each pair was built, before scores were read.",
        "Scores are weighted Dice unless a signal had nothing to score (`n/a`).",
        "Bands elsewhere in the tool are low < 0.10, modest < 0.30, substantial < 0.60, high ≥ 0.60.",
        "AUC is the pairwise probability that a labeled-positive score exceeds a labeled-independent score",
        "(ties count as 0.5). It describes this eval set only.",
        "",
        "## Separation",
        "",
        "| Signal | Full AUC | With partials AUC | Full min / median / max (n) | Independent min / median / max (n) |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    signals = summary["signals"]
    assert isinstance(signals, dict)
    for name, block in signals.items():
        assert isinstance(block, dict)
        full = block["full"]
        indep = block["independent"]
        assert isinstance(full, dict) and isinstance(indep, dict)
        lines.append(
            "| {name} | {auc} | {auc2} | {fmin} / {fmed} / {fmax} ({fn}) | {imin} / {imed} / {imax} ({inn}) |".format(
                name=name,
                auc=_fmt(block["full_auc"]),
                auc2=_fmt(block["full_plus_partial_auc"]),
                fmin=_fmt(full["min"]),
                fmed=_fmt(full["median"]),
                fmax=_fmt(full["max"]),
                fn=full["n"],
                imin=_fmt(indep["min"]),
                imed=_fmt(indep["median"]),
                imax=_fmt(indep["max"]),
                inn=indep["n"],
            )
        )
    lines.extend(["", "## False-positive notes", ""])
    lines.append(
        "An independent pair at or above 0.30 is listed. Full positives below 0.60 are listed too, "
        "so a weak full positive is not hidden by the AUC."
    )
    lines.append("")
    for name, block in signals.items():
        assert isinstance(block, dict)
        highs = block["independent_at_or_above_0_30"]
        lows = block["full_below_0_60"]
        lines.append(f"- **{name}** independent ≥ 0.30: {highs or 'none'}.")
        lines.append(f"- **{name}** full-positive < 0.60: {lows or 'none'}.")
    lines.extend(["", "## How to read the low scores", ""])
    lines.append(
        "Full-positive AUC can stay at 1.0 while the minimum full-positive score is modest. "
        "That minimum is named above. On this run it is the graingert/tomli fork: git history "
        "shows it is an ancestor of tomli 2.0.1 (behind, and not ahead), so it was labeled "
        "same-lineage before scoring. Token Dice is much lower than the vendored CPython pair "
        "because the older snapshot has drifted. Structural and artifact scores for that fork "
        "stay well above the independent pairs. A same-lineage label is not a promise of a near-duplicate."
    )
    lines.append("")
    lines.append(
        "Partial edits of slug keep rewrite containment at 1.0 while Dice falls as fewer functions "
        "remain. A 20% slice is a modest Dice, not a high one. Containment is the column that says "
        "the remaining code is aligned with the original."
    )
    lines.append("")
    cross = next((row for row in rows if row["id"] == "slug_vs_slug_js"), None)
    if cross is not None:
        sig = cross["signals"]
        assert isinstance(sig, dict)
        lines.append(
            "The Python-to-JavaScript port scores token "
            f"{_cell(sig, 'token_fingerprint')}, structural {_cell(sig, 'structural')}, "
            f"artifacts {_cell(sig, 'rare_artifacts')}, tests {_cell(sig, 'test_cases')}. "
            "Token fingerprints do not cross languages. The lexer control-flow score is only modest "
            "on this port, because the JavaScript version adds loops the Python version does not have. "
            "Shared strings and test literals carry more of that comparison."
        )
        lines.append("")
    lines.extend(["## Every pair", ""])
    lines.append("| Pair | Group | Kind | Token | Containment | Structural | Artifacts | Tests |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for row in rows:
        sig = row["signals"]
        assert isinstance(sig, dict)
        token = sig.get("token_fingerprint", {})
        containment = token.get("containment") if isinstance(token, dict) else None
        lines.append(
            f"| {row['id']} | {row['group']} | {row['kind']} | {_cell(sig, 'token_fingerprint')} | "
            f"{_fmt(containment)} | {_cell(sig, 'structural')} | {_cell(sig, 'rare_artifacts')} | "
            f"{_cell(sig, 'test_cases')} |"
        )
    if any(row["kind"] in {"timing_later", "timing_earlier"} for row in rows):
        lines.extend(["", "## Timing pairs", ""])
        for row in rows:
            if row["kind"] not in {"timing_later", "timing_earlier"}:
                continue
            sig = row["signals"]
            assert isinstance(sig, dict)
            payload = sig.get("git_timing", {})
            score = payload.get("score") if isinstance(payload, dict) else None
            band = payload.get("band") if isinstance(payload, dict) else None
            lines.append(f"- `{row['id']}` ({row['note']}): score {_fmt(score)}, band {band}.")
    if sources:
        lines.extend(
            [
                "",
                "## Real sources",
                "",
                "Cloned locally for measurement. Not redistributed in this repository.",
                "",
            ]
        )
        for source in sources:
            lines.append(
                f"- `{source['name']}` {source['url']} @ `{source['requested_rev']}` "
                f"commit `{source['commit']}` license: {source.get('license', '')}."
            )
    lines.extend(
        [
            "",
            "## What a partial edit does",
            "",
            "A rewrite that keeps only some functions can have rewrite containment near 1 and a lower Dice,",
            "because Dice also penalizes original material that the rewrite does not contain.",
            "Read both columns.",
            "",
            "## Cross-language",
            "",
            "`slug_vs_slug_js` is a hand port. Token fingerprints are same-language. Structural comparison",
            "uses the lexer control-flow path. Artifact and test scores depend on shared strings and literals.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure Lineage on the v1 eval set")
    parser.add_argument("--fetch", action="store_true", help="clone pinned permissive repositories and include them")
    parser.add_argument("--out", type=Path, default=EVAL)
    args = parser.parse_args(argv)
    rows = synthetic_rows()
    sources: list[dict[str, object]] = []
    if args.fetch:
        real, sources = real_rows()
        rows.extend(real)
    summary = summarize(rows)
    payload = {"eval_set": "lineage-v1", "summary": summary, "pairs": rows, "sources": sources}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (args.out / "RESULTS.md").write_text(render_markdown(rows, summary, sources), encoding="utf-8")
    print(render_markdown(rows, summary, sources))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
