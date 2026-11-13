"""Run every signal and assemble a report. The library does not print."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from lineage import __version__
from lineage.artifacts import (
    artifact_evidence,
    index_corpus,
    overlap_scores,
    weighted_maps,
)
from lineage.baseline import structural_baseline, token_baseline
from lineage.discover import Corpus, SourceFile, load_corpus
from lineage.evidence import Bag, FileMatch, file_rows, measure, regions_for
from lineage.models import (
    DISCLAIMER,
    HOW_TO_READ,
    Evidence,
    Report,
    Settings,
    SideInfo,
    SignalResult,
)
from lineage.structural import (
    STRUCTURAL_LIMITS,
    fill_control_bag,
    fill_python_ast_bag,
    python_fraction,
)
from lineage.testsig import case_scores, case_weights, index_tests
from lineage.timing import git_available, time_alignments, timing_evidence
from lineage.tokenize import gram_weight, normalized_chunks
from lineage.winnow import fingerprint_stream

TOKEN_NOTES = (
    "User-defined names are numbered in order of first appearance inside each "
    "function, so a rename or a reformat does not move this signal. Keywords and "
    "builtins stay as written. Comments are ignored here. K-grams made almost "
    "entirely of string literals and punctuation are dropped; those literals are "
    "scored as artifacts instead. Test files are omitted. Reordering whole "
    "functions is stable because each function is fingerprinted on its own. "
    "Reordering the statements inside a function does change the token stream."
)


def compare_paths(
    original: Path,
    rewrite: Path,
    *,
    settings: Settings | None = None,
    original_label: str | None = None,
    rewrite_label: str | None = None,
    original_revision: str | None = None,
    rewrite_revision: str | None = None,
) -> Report:
    settings = settings or Settings()
    left = load_corpus(
        original,
        include_vendored=settings.include_vendored,
        max_file_bytes=settings.max_file_bytes,
        max_files=settings.max_files,
    )
    right = load_corpus(
        rewrite,
        include_vendored=settings.include_vendored,
        max_file_bytes=settings.max_file_bytes,
        max_files=settings.max_files,
    )
    token = _token_signal(left, right, settings)
    structural = _structural_signal(left, right, settings)
    artifacts = _artifact_signal(left, right, settings)
    tests = _test_signal(left, right, settings)
    timing = _timing_signal(original, rewrite, token, settings)
    signals = [token, structural, artifacts, tests, timing]
    skipped = [
        {"side": "original", "path": path, "reason": reason} for path, reason in left.skipped
    ] + [{"side": "rewrite", "path": path, "reason": reason} for path, reason in right.skipped]
    return Report(
        original=_side("original", original_label or str(original), original_revision, left),
        rewrite=_side("rewrite", rewrite_label or str(rewrite), rewrite_revision, right),
        signals=signals,
        narrative=_narrate(signals),
        parameters={"tool_version": __version__, **settings.to_dict(), "how_to_read": HOW_TO_READ},
        skipped=skipped[:80],
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )


def _side(label: str, path: str, revision: str | None, corpus: Corpus) -> SideInfo:
    return SideInfo(
        label=label,
        path=path,
        revision=revision,
        files_compared=len(corpus.files),
        files_skipped=len(corpus.skipped),
        non_source_ignored=corpus.ignored_non_source,
        loc=corpus.loc,
        test_loc=corpus.test_loc,
        languages=corpus.languages(),
    )


def _narrate(signals: list[SignalResult]) -> str:
    bits: list[str] = []
    for signal in signals:
        if signal.score is None:
            bits.append(f"{signal.name}: {signal.band}")
        else:
            bits.append(f"{signal.name}: {signal.band} ({signal.score:.2f})")
    return (
        "Similarity by signal — "
        + "; ".join(bits)
        + ". Read containment and coverage next to each score. "
        + DISCLAIMER
    )


def _token_signal(left: Corpus, right: Corpus, settings: Settings) -> SignalResult:
    bag_a, bag_b = Bag(), Bag()
    _fill_tokens(left, bag_a, settings)
    _fill_tokens(right, bag_b, settings)
    overlap = measure(bag_a, bag_b, token_baseline(settings.token_k, settings.token_window))
    rows = file_rows(bag_a, bag_b, overlap.weights, limit=15)
    evidence = regions_for(
        bag_a,
        bag_b,
        overlap.weights,
        left,
        right,
        limit=settings.evidence_limit,
    )
    summary = _dice_summary(
        "Token fingerprints",
        overlap.dice,
        overlap.containment,
        overlap.coverage,
        overlap.shared,
        overlap.count_a,
        overlap.count_b,
        len(evidence),
        overlap.reason,
    )
    return SignalResult(
        id="token_fingerprint",
        name="Token fingerprints",
        score=overlap.dice,
        summary=summary,
        metrics={
            "dice": overlap.dice,
            "rewrite_containment": overlap.containment,
            "original_coverage": overlap.coverage,
            "shared_fingerprints": overlap.shared,
            "fingerprints_original": overlap.count_a,
            "fingerprints_rewrite": overlap.count_b,
            "k": settings.token_k,
            "window": settings.token_window,
            "file_matches": rows,
        },
        evidence=evidence,
        notes=[TOKEN_NOTES],
    )


def _fill_tokens(corpus: Corpus, bag: Bag, settings: Settings) -> None:
    for source in corpus.non_tests():
        chunks = normalized_chunks(
            source.text,
            source.rel_path,
            source.language,
            skip_lines=source.license_skip_lines,
        )
        for chunk in chunks:
            texts = [token.text for token in chunk]
            lines = [token.line for token in chunk]
            for fingerprint in fingerprint_stream(
                texts,
                lines,
                file=source.rel_path,
                k=settings.token_k,
                window=settings.token_window,
                weight_of=gram_weight,
            ):
                bag.add(
                    fingerprint.digest,
                    fingerprint.file,
                    fingerprint.start,
                    fingerprint.end,
                    fingerprint.weight,
                )


def _structural_signal(left: Corpus, right: Corpus, settings: Settings) -> SignalResult:
    control_a, control_b = Bag(), Bag()
    ast_a, ast_b = Bag(), Bag()
    fill_control_bag(left, control_a, k=settings.struct_k, window=settings.struct_window)
    fill_control_bag(right, control_b, k=settings.struct_k, window=settings.struct_window)
    fill_python_ast_bag(left, ast_a, k=settings.struct_k, window=settings.struct_window)
    fill_python_ast_bag(right, ast_b, k=settings.struct_k, window=settings.struct_window)
    baseline = structural_baseline(settings.struct_k, settings.struct_window)
    control = measure(control_a, control_b, baseline)
    ast_overlap = measure(ast_a, ast_b, baseline)
    mostly_python = python_fraction(left.non_tests()) >= 0.6 and python_fraction(right.non_tests()) >= 0.6
    if mostly_python and ast_overlap.dice is not None:
        chosen = ast_overlap
        chosen_bag = (ast_a, ast_b)
        used = "python_ast"
    else:
        chosen = control
        chosen_bag = (control_a, control_b)
        used = "control_flow"
    evidence = regions_for(
        chosen_bag[0],
        chosen_bag[1],
        chosen.weights,
        left,
        right,
        limit=settings.evidence_limit,
    )
    if chosen.dice is None:
        summary = chosen.reason or "Not enough structural fingerprints to score."
    else:
        summary = (
            f"Headline uses {used.replace('_', ' ')}. Weighted Dice is {chosen.dice:.2f} "
            f"({chosen.shared} shared shapes; rewrite containment "
            f"{_fmt(chosen.containment)}; original coverage {_fmt(chosen.coverage)}). "
            f"Control-flow Dice is {_fmt(control.dice)}; Python grammar Dice is {_fmt(ast_overlap.dice)}."
        )
    return SignalResult(
        id="structural",
        name="Structural similarity",
        score=chosen.dice,
        summary=summary,
        metrics={
            "dice": chosen.dice,
            "headline": used,
            "rewrite_containment": chosen.containment,
            "original_coverage": chosen.coverage,
            "shared_fingerprints": chosen.shared,
            "control_flow_dice": control.dice,
            "python_ast_dice": ast_overlap.dice,
            "k": settings.struct_k,
            "window": settings.struct_window,
            "file_matches": file_rows(chosen_bag[0], chosen_bag[1], chosen.weights),
        },
        evidence=evidence,
        notes=[STRUCTURAL_LIMITS],
    )


def _artifact_signal(left: Corpus, right: Corpus, settings: Settings) -> SignalResult:
    index_a = index_corpus(left)
    index_b = index_corpus(right)
    left_w, right_w = weighted_maps(index_a, index_b)
    dice, containment, coverage, shared = overlap_scores(left_w, right_w)
    # Evidence weights are the rewrite-side weights of shared keys.
    evidence = artifact_evidence(index_a, index_b, right_w, limit=settings.evidence_limit)
    _attach_line_excerpts(evidence, left, right)
    if dice is None:
        summary = "Not enough rare artifacts on both sides to score."
    else:
        preview = ", ".join(item.detail for item in evidence[:3])
        summary = (
            f"Weighted Dice is {dice:.2f} ({shared} shared artifacts; "
            f"rewrite containment {_fmt(containment)}; original coverage {_fmt(coverage)}). "
            + (f"Strongest: {preview}." if preview else "No shared artifact cleared the rarity filter.")
        )
    return SignalResult(
        id="rare_artifacts",
        name="Rare artifacts",
        score=dice,
        summary=summary,
        metrics={
            "dice": dice,
            "rewrite_containment": containment,
            "original_coverage": coverage,
            "shared_artifacts": shared,
            "artifacts_original": len(left_w),
            "artifacts_rewrite": len(right_w),
        },
        evidence=evidence,
        notes=[
            "Identifiers, string literals, comments, numbers, and known misspellings "
            "are weighted by how unusual they are. Names that are ordinary English or "
            "ordinary programming vocabulary, short numbers, and license text contribute "
            "little or nothing. An identifier that was renamed will not overlap here."
        ],
    )


def _test_signal(left: Corpus, right: Corpus, settings: Settings) -> SignalResult:
    if not left.tests() or not right.tests():
        missing = []
        if not left.tests():
            missing.append("original")
        if not right.tests():
            missing.append("rewrite")
        who = " and ".join(missing)
        return SignalResult(
            id="test_cases",
            name="Test-case overlap",
            score=None,
            band="unavailable",
            summary=f"No test files were found on the {who} side, so this signal was not computed.",
            notes=["Test paths are detected by directory name and by filename conventions."],
        )
    index_a = index_tests(left)
    index_b = index_tests(right)
    left_w, right_w = case_weights(index_a, index_b)
    dice, containment, coverage, shared = case_scores(left_w, right_w)
    evidence: list[Evidence] = []
    if dice is not None:
        shared_keys = set(left_w) & set(right_w)
        ranked = sorted(shared_keys, key=lambda key: (-min(left_w[key], right_w[key]), key))
        for key in ranked[: settings.evidence_limit]:
            evidence.append(
                Evidence(
                    original_path=index_a.path.get(key, ""),
                    original_start=index_a.line.get(key, 1),
                    original_end=index_a.line.get(key, 1),
                    rewrite_path=index_b.path.get(key, ""),
                    rewrite_start=index_b.line.get(key, 1),
                    rewrite_end=index_b.line.get(key, 1),
                    score=min(left_w[key], right_w[key]),
                    detail=f"shared test literals {index_a.display.get(key, '')}",
                )
            )
        _attach_line_excerpts(evidence, left, right)
    if dice is None:
        summary = (
            "Test files are present, but they did not contain distinctive literals "
            "(unusual strings or numbers) to compare."
        )
        band = "insufficient"
    else:
        summary = (
            f"Weighted Dice of per-test literal sets is {dice:.2f} "
            f"({shared} shared test signatures; rewrite containment {_fmt(containment)}; "
            f"original coverage {_fmt(coverage)})."
        )
        band = ""
    return SignalResult(
        id="test_cases",
        name="Test-case overlap",
        score=dice,
        band=band,
        summary=summary,
        metrics={
            "dice": dice,
            "rewrite_containment": containment,
            "original_coverage": coverage,
            "shared_cases": shared,
            "cases_original": len(left_w),
            "cases_rewrite": len(right_w),
            "test_files_original": len(left.tests()),
            "test_files_rewrite": len(right.tests()),
        },
        evidence=evidence,
        notes=[
            "Each test function contributes the set of distinctive literals inside it. "
            "Ordinary fixtures such as empty collections, utf-8, 0, and 1 are ignored. "
            "Token, structural, and artifact signals do not see test files."
        ],
    )


def _timing_signal(
    original: Path,
    rewrite: Path,
    token: SignalResult,
    settings: Settings,
) -> SignalResult:
    notes = [
        "Timing uses author dates of the commits that introduced strongly aligned "
        f"files (token containment at least 0.50 and at least 5 shared fingerprints). "
        f"A file counts as fully formed when that commit added at least 75% of its "
        f"lines. The window is {settings.timing_window_days} days after the original "
        "file. This does not measure similarity of the text."
    ]
    if not settings.timing:
        return SignalResult(
            id="git_timing",
            name="Git history timing",
            score=None,
            band="unavailable",
            summary="Timing was turned off.",
            notes=notes,
        )
    original_root = original if original.is_dir() else original.parent
    rewrite_root = rewrite if rewrite.is_dir() else rewrite.parent
    if not git_available(original_root) or not git_available(rewrite_root):
        return SignalResult(
            id="git_timing",
            name="Git history timing",
            score=None,
            band="unavailable",
            summary="One or both paths are not inside a git repository, so timing was not computed.",
            notes=notes,
        )
    raw_pairs = token.metrics.get("file_matches") or []
    pairs = cast(list[FileMatch], [row for row in raw_pairs if isinstance(row, dict)])
    rows, missing = time_alignments(
        original_root,
        rewrite_root,
        pairs,
        window_days=settings.timing_window_days,
    )
    if not rows:
        why = "No file pair was both strongly aligned and present in both histories."
        if missing:
            why = f"{why} {missing} aligned path(s) had no introducing commit."
        return SignalResult(
            id="git_timing",
            name="Git history timing",
            score=None,
            band="unavailable",
            summary=why,
            metrics={"strong_pairs": 0, "untracked_pairs": missing},
            notes=notes,
        )
    aligned = sum(1 for row in rows if row.aligned)
    score = aligned / len(rows)
    return SignalResult(
        id="git_timing",
        name="Git history timing",
        score=score,
        summary=(
            f"{aligned} of {len(rows)} strongly aligned file pairs were introduced "
            f"fully formed within {settings.timing_window_days} days after the "
            f"matching original file. {missing} other aligned path(s) had no introducing commit."
        ),
        metrics={
            "aligned_pairs": aligned,
            "timed_pairs": len(rows),
            "untracked_pairs": missing,
            "window_days": settings.timing_window_days,
            "median_delta_days": _median([row.delta_days for row in rows]),
        },
        evidence=timing_evidence(rows, settings.evidence_limit),
        notes=notes,
    )


def _attach_line_excerpts(evidence: list[Evidence], left: Corpus, right: Corpus) -> None:
    left_files = left.by_path()
    right_files = right.by_path()
    for item in evidence:
        if not item.original_excerpt:
            item.original_excerpt = _one_line(left_files.get(item.original_path), item.original_start)
        if not item.rewrite_excerpt:
            item.rewrite_excerpt = _one_line(right_files.get(item.rewrite_path), item.rewrite_start)


def _one_line(source: SourceFile | None, line: int) -> str:
    if source is None or line <= 0:
        return ""
    rows = source.text.splitlines()
    if line > len(rows):
        return ""
    text = rows[line - 1]
    return text if len(text) <= 180 else text[:180] + "…"


def _dice_summary(
    name: str,
    dice: float | None,
    containment: float | None,
    coverage: float | None,
    shared: int,
    count_a: int,
    count_b: int,
    regions: int,
    reason: str,
) -> str:
    del name
    if dice is None:
        return reason or "Not enough fingerprints to score."
    return (
        f"Weighted Dice is {dice:.2f} ({shared} shared fingerprints of "
        f"{count_a} on the original and {count_b} on the rewrite; "
        f"rewrite containment {_fmt(containment)}; original coverage {_fmt(coverage)}). "
        f"{regions} aligned regions are listed with file:line spans."
    )


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
