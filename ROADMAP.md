# Roadmap

Lineage 0.1 scores five signals and writes Markdown, JSON, and HTML. Later milestones stay inside the same rule: report similarity and show evidence. Do not add a verdict, a legal conclusion, or language that asserts authorship.

## Stronger structure

- Optional tree-sitter grammars for languages other than Python, with the same event vocabulary the lexer path uses now.
- Keep the lexer path as the fallback, and keep saying when a score used the fallback.
- Data-flow or type shapes for cases where control flow was rebuilt but the computation was not. Ship this only with an eval that shows the false-positive rate.

## Better cross-language comparison

- A larger set of hand ports, more than the one Python-to-JavaScript pair in v1.
- Identifier and literal alignment that survives quote style and obvious renames, without folding the token signal into the artifact signal.
- Report the language pair on every structural score so a modest cross-language number is not read as a same-language number.

## Baseline corpus

- Replace the small embedded idiom list with fingerprints from a reviewed permissive corpus.
- Publish the corpus list, the commit of each project, and the license.
- Keep common idioms out of the score, and keep showing when a region was down-weighted.

## Scale and review

- A file-to-file alignment pass before scoring, so a split or merged file is easier to read.
- Cache fingerprints by content hash.
- Raise or remove the 800-file cap once that cache exists, and re-measure runtime on a few medium repositories.
- Diff highlighting inside the HTML panes. The page should stay a single file with no remote assets.

## Calibration

- A held-out set that is not the v1 set in `eval/RESULTS.md`.
- Report AUC on the held-out set separately. Do not refit the 0.10 / 0.30 / 0.60 bands on the set you are quoting.
- More independent pairs that solve the same problem, including pairs that share a specification (two TOML readers is a start, not a finished study).

## History

- Timing on full (not shallow) histories, with a clear note when a file was renamed.
- Per-line introduction times only if they stay fast enough to run by default. File-level timing is the v1 behavior.

## Out of scope

- A single accusatory score.
- Words or UI that state code was copied, plagiarized, or used improperly.
- Running the tool against a live dispute as part of development.
- Publishing other people's source inside this repository. Record the URL, revision, and license instead.
