# Lineage

Lineage compares an original codebase with another codebase and writes a similarity report. Each signal is scored and explained on its own. The report shows file and line spans on both sides.

It does not decide authorship, and it does not give legal advice.

> Lineage measures textual and structural similarity between two codebases and shows the evidence behind each score. Similarity can come from a shared specification, a standard algorithm, common idioms, generated code, a vendored library, or two independent implementations of the same idea. This report does not determine authorship, does not reach a legal conclusion, and is not legal advice.

## Install

Python 3.10 or newer.

```bash
pip install -e ".[dev]"
```

The only runtime dependency is Pygments.

## Compare

```bash
lineage compare ORIGINAL REWRITE -o report
```

`ORIGINAL` and `REWRITE` are local paths or git URLs. Optional `--rev-a` and `--rev-b` check out those revisions into a temporary clone. `-o report` writes `report.md`, `report.json`, and `report.html`.

```bash
lineage compare examples/original examples/renamed -o /tmp/lineage-renamed
lineage compare ./eval/projects/slug ./eval/projects/stats -o /tmp/lineage-different
lineage compare https://example.com/a.git https://example.com/b.git --rev-a v1.2.0 --rev-b main -o report
```

Other flags: `--no-timing`, `--include-vendored`, `--k`, `--window`, `--max-files` (default 800), `--max-file-bytes` (default 1_000_000).

Files under `vendor/`, `third_party/`, and similar directories are left out unless you pass `--include-vendored` or point the command at that directory itself. Generated files, minified bundles, lockfiles, and license files are left out. A leading license header is ignored for signals, and line numbers in the report still refer to the original files.

## How a score works

There is no single verdict. Each signal reports weighted Dice from 0 to 1, plus rewrite containment and original coverage when it has them.

- Dice near 0: that signal did not overlap.
- Dice near 1: the two sides look the same under that signal.
- Containment near 1: most of the rewrite's signal is also present in the original. A subset can have high containment and a lower Dice.

Bands are fixed labels for this version, not a decision threshold: low below 0.10, modest below 0.30, substantial below 0.60, high at or above 0.60. A missing score means the signal did not apply or did not have enough material.

### Token fingerprints

Winnowing over normalized tokens (Schleimer, Wilkerson, and Aiken, 2003). Default k is 15 and the window is 5. Inside each function, user-defined names become `ID0`, `ID1`, … in order of first appearance. Keywords and builtins stay as written. Whitespace and comments are dropped. String contents become `STR`. K-grams that are almost only literals and punctuation are dropped. Test files are not included. Reordering whole functions does not change the set. Reordering statements inside a function does.

### Structural similarity

Control shape: functions, branches, loops, assignments, calls. When both sides are mostly Python, the headline uses Python's grammar. Otherwise it uses a lexer approximation (indent depth in Python, brace depth elsewhere). That approximation is not a translation. It misses an algorithm rebuilt with different control flow, and short idiomatic shapes can still overlap; those are down-weighted. Cross-language scores are weaker than same-language scores. Tree-sitter is not used.

### Rare artifacts

Identifiers, string literals, comments, numbers, and a fixed list of known misspellings. Ordinary programming vocabulary, short numbers, and license text weigh little or nothing. Items that occur in many files are down-weighted again. Renamed identifiers do not overlap here; the token signal covers that.

### Test-case overlap

Distinctive literals inside test functions, and the set of those literals when a function has several. Ordinary fixtures (`{}`, `utf-8`, `0`, `1`, and similar) are ignored. Test files are excluded from the other signals so a shared test suite is not counted four times.

### Git history timing

Not a text-similarity score. Among file pairs that already have strong token alignment (containment at least 0.50 and at least 5 shared fingerprints), it asks how many rewrite files were introduced in one commit, with that commit adding at least 75% of the file, during a 180-day window after the original file's author date. No git history, or no strong alignment, means the signal was not computed. It is not reported as low similarity just because history is missing.

## Reports

- Markdown: summary table, metrics, and side-by-side excerpts.
- JSON (`schema_version` 1): the same content for other tools.
- HTML: a self-contained page. Open it in a browser. It does not load remote assets. Regions are shown in two panes with the original line numbers.

## Evaluation

`eval/RESULTS.md` and `eval/results.json` are the measured numbers for the v1 eval set. Labels were assigned from how each pair was built, before scores were read. AUC is only a description of this set: the chance a labeled-positive score beats a labeled-independent score.

On that set (21 full positives, 12 independent pairs for tokens):

| Signal | Full AUC | Full min / median / max | Independent min / median / max |
| --- | ---: | --- | --- |
| Token fingerprints | 1.000 | 0.135 / 1.000 / 1.000 | 0.000 / 0.000 / 0.014 |
| Structural | 1.000 | 0.751 / 1.000 / 1.000 | 0.000 / 0.013 / 0.116 |
| Rare artifacts | 1.000 | 0.677 / 1.000 / 1.000 | 0.000 / 0.007 / 0.050 |
| Test cases | 1.000 | 0.698 / 1.000 / 1.000 | 0.000 / 0.000 / 0.028 |

The token minimum of 0.135 is `tomli` 2.0.1 versus the `graingert/tomli` fork. That fork is an ancestor of 2.0.1, not a near-duplicate of it. Its structural score is 0.751 and its artifact score is 0.732. The vendored pair, CPython 3.11.9 `Lib/tomllib` against tomli 2.0.1, scores 0.994 (tokens), 1.000 (structural), and 0.991 (artifacts). Tomli 2.0.1 against 2.0.2 scores 0.978 on tokens.

Synthetic rename, reformat, and reorder of the slug, JSON, and argv fixtures score 1.000 on tokens. Keeping 70%, 40%, and 20% of slug's functions scores token Dice 0.685, 0.391, and 0.164, with rewrite containment 1.000 in each case. A hand port from Python to JavaScript scores tokens 0.000, structural 0.244, artifacts 0.584, and tests 0.762.

No independent pair reached 0.30 on tokens, structure, or artifacts. The highest structural score among independent pairs is 0.116 (a ring buffer against a linked queue). Two MIT TOML libraries, tomli and uiri/toml, score 0.000 on tokens.

Regenerate with:

```bash
python eval/run_eval.py --fetch
```

`--fetch` clones small MIT repositories listed in `eval/RESULTS.md` and downloads CPython's vendored `tomllib` files. Those third-party trees are cached under `eval/cache/` and are not committed. The synthetic half does not need a network connection. `tests/test_eval_synthetic.py` checks that the synthetic separation still holds.

## Tests

```bash
pytest
ruff check src tests eval/run_eval.py
mypy src
```

Covered: tokenization, winnowing, structural hashes, rarity weights, the boilerplate filter, report rendering, the CLI (including a local `--rev-a` / `--rev-b` checkout), an end-to-end fixture, and the synthetic eval lock.

## Limits

- Token fingerprints are same-language. A translation will not score high on that signal.
- Structural comparison across languages is a shared vocabulary of control events, not a semantic translation. One hand port is in the eval. It scored 0.244.
- Python grammar shapes are used only when the file parses. Other languages use the lexer approximation.
- Statement reordering inside a function changes token fingerprints. Whole-function reordering does not.
- Renames of keywords, builtins, or dunder names are not normalized away. Renames of user-defined names are.
- The known-misspelling list is a fixed set, not a general spellchecker.
- Repositories larger than 800 source files are truncated, and the report says so.
- Timing was measured on two synthetic histories. The real repositories in the eval were shallow clones or downloaded files, so timing was not part of those pairs.
- Bands were chosen before looking at any particular dispute. They are labels for reading a report.

## License

MIT. Copyright (c) 2026 Kaung (https://github.com/KaungMyatNaing9). See `LICENSE`.
