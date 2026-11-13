# Lineage v1 evaluation

Labels were assigned from how each pair was built, before scores were read.
Scores are weighted Dice unless a signal had nothing to score (`n/a`).
Bands elsewhere in the tool are low < 0.10, modest < 0.30, substantial < 0.60, high ≥ 0.60.
AUC is the pairwise probability that a labeled-positive score exceeds a labeled-independent score
(ties count as 0.5). It describes this eval set only.

## Separation

| Signal | Full AUC | With partials AUC | Full min / median / max (n) | Independent min / median / max (n) |
| --- | ---: | ---: | --- | --- |
| token_fingerprint | 1.000 | 1.000 | 0.135 / 1.000 / 1.000 (21) | 0.000 / 0.000 / 0.014 (12) |
| structural | 1.000 | 0.996 | 0.751 / 1.000 / 1.000 (21) | 0.000 / 0.013 / 0.116 (10) |
| rare_artifacts | 1.000 | 1.000 | 0.677 / 1.000 / 1.000 (14) | 0.000 / 0.007 / 0.050 (12) |
| test_cases | 1.000 | n/a | 0.698 / 1.000 / 1.000 (23) | 0.000 / 0.000 / 0.028 (7) |

## False-positive notes

An independent pair at or above 0.30 is listed. Full positives below 0.60 are listed too, so a weak full positive is not hidden by the AUC.

- **token_fingerprint** independent ≥ 0.30: none.
- **token_fingerprint** full-positive < 0.60: ['tomli_2.0.1_vs_graingert_fork'].
- **structural** independent ≥ 0.30: none.
- **structural** full-positive < 0.60: none.
- **rare_artifacts** independent ≥ 0.30: none.
- **rare_artifacts** full-positive < 0.60: none.
- **test_cases** independent ≥ 0.30: none.
- **test_cases** full-positive < 0.60: none.

## How to read the low scores

Full-positive AUC can stay at 1.0 while the minimum full-positive score is modest. That minimum is named above. On this run it is the graingert/tomli fork: git history shows it is an ancestor of tomli 2.0.1 (behind, and not ahead), so it was labeled same-lineage before scoring. Token Dice is much lower than the vendored CPython pair because the older snapshot has drifted. Structural and artifact scores for that fork stay well above the independent pairs. A same-lineage label is not a promise of a near-duplicate.

Partial edits of slug keep rewrite containment at 1.0 while Dice falls as fewer functions remain. A 20% slice is a modest Dice, not a high one. Containment is the column that says the remaining code is aligned with the original.

The Python-to-JavaScript port scores token 0.000, structural 0.244, artifacts 0.584, tests 0.762. Token fingerprints do not cross languages. The lexer control-flow score is only modest on this port, because the JavaScript version adds loops the Python version does not have. Shared strings and test literals carry more of that comparison.

## Every pair

| Pair | Group | Kind | Token | Containment | Structural | Artifacts | Tests |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| slug__exact | synthetic | exact | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| slug__rename | synthetic | rename | 1.000 | 1.000 | 1.000 | 0.520 | 1.000 |
| slug__reformat | synthetic | reformat | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| slug__reorder | synthetic | reorder | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| slug__combo | synthetic | combo | 1.000 | 1.000 | 1.000 | 0.520 | 1.000 |
| slug__paraphrase | synthetic | paraphrase | 0.819 | 0.832 | 1.000 | 0.800 | 1.000 |
| json_a__exact | synthetic | exact | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| json_a__rename | synthetic | rename | 1.000 | 1.000 | 1.000 | 0.698 | 1.000 |
| json_a__reformat | synthetic | reformat | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| json_a__reorder | synthetic | reorder | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| json_a__combo | synthetic | combo | 1.000 | 1.000 | 1.000 | 0.698 | 1.000 |
| json_a__paraphrase | synthetic | paraphrase | 0.821 | 0.814 | 1.000 | 0.376 | 1.000 |
| argv_a__exact | synthetic | exact | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| argv_a__rename | synthetic | rename | 1.000 | 1.000 | 1.000 | 0.754 | 1.000 |
| argv_a__reformat | synthetic | reformat | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| argv_a__reorder | synthetic | reorder | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| argv_a__combo | synthetic | combo | 1.000 | 1.000 | 1.000 | 0.754 | 1.000 |
| argv_a__paraphrase | synthetic | paraphrase | 1.000 | 1.000 | 1.000 | 0.312 | 1.000 |
| slug__partial_70 | synthetic | partial_70 | 0.685 | 1.000 | 0.657 | 0.861 | 1.000 |
| slug__partial_40 | synthetic | partial_40 | 0.391 | 1.000 | 0.321 | 0.677 | 1.000 |
| slug__partial_20 | synthetic | partial_20 | 0.164 | 1.000 | 0.111 | 0.486 | 1.000 |
| slug__diluted | synthetic | diluted | 0.426 | 0.477 | 0.448 | 0.735 | 1.000 |
| json_a_vs_json_b | synthetic | independent | 0.014 | 0.014 | 0.079 | 0.023 | 0.000 |
| argv_a_vs_argv_b | synthetic | independent | 0.000 | 0.000 | 0.039 | 0.041 | 0.000 |
| ring_vs_queue | synthetic | independent | 0.000 | 0.000 | 0.116 | 0.000 | n/a |
| stats_vs_units | synthetic | independent | 0.000 | 0.000 | n/a | 0.000 | n/a |
| slug_vs_stats | synthetic | independent | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| json_a_vs_argv_a | synthetic | independent | 0.000 | 0.000 | 0.025 | 0.031 | 0.000 |
| ring_vs_slug | synthetic | independent | 0.000 | 0.000 | 0.000 | 0.000 | n/a |
| units_vs_json_b | synthetic | independent | 0.000 | 0.000 | n/a | 0.000 | n/a |
| slug_vs_slug_js | synthetic | cross_language | 0.000 | 0.000 | 0.244 | 0.584 | 0.762 |
| timing_fully_formed_later | synthetic | timing_later | n/a | n/a | n/a | n/a | n/a |
| timing_predates | synthetic | timing_earlier | n/a | n/a | n/a | n/a | n/a |
| tomli_2.0.1_vs_cpython_3.11.9_tomllib | real | vendored_copy | 0.994 | 0.995 | 1.000 | 0.991 | n/a |
| tomli_2.0.1_vs_tomli_2.0.2 | real | adjacent_release | 0.978 | 0.972 | 0.984 | 0.981 | n/a |
| tomli_2.0.1_vs_graingert_fork | real | same_lineage | 0.135 | 0.142 | 0.751 | 0.732 | 0.698 |
| tomli_vs_uiri_toml | real | independent | 0.000 | 0.000 | 0.008 | 0.013 | 0.028 |
| tomli_vs_tomlkit | real | independent | 0.000 | 0.000 | 0.017 | 0.013 | 0.017 |
| tomli_vs_tomli_w | real | independent | 0.002 | 0.003 | 0.000 | 0.050 | n/a |
| iniconfig_vs_six | real | independent | 0.000 | 0.000 | 0.000 | 0.002 | 0.000 |

## Timing pairs

- `timing_fully_formed_later` (Rewrite file added in one commit 19 days later.): score 1.000, band high.
- `timing_predates` (Rewrite file added months before the original file.): score 0.000, band low.

## Real sources

Cloned locally for measurement. Not redistributed in this repository.

- `tomli-2.0.1` https://github.com/hukkin/tomli @ `2.0.1` commit `36ef51d6a5a55e0eca077b58695390d041061bd4` license: MIT.
- `tomli-2.0.2` https://github.com/hukkin/tomli @ `2.0.2` commit `3ec6775b118f2ae030d5b12c90939c7f65668e7e` license: MIT.
- `cpython-3.11.9-tomllib` https://github.com/python/cpython @ `v3.11.9` commit `de54cf5be371a6f5e2e9f208c38def5f81d3ef02` license: MIT SPDX on the vendored tomllib files (PSF contributor notice also present).
- `graingert-tomli` https://github.com/graingert/tomli @ `master` commit `c5cfe115fb8cc608416f1741f8b42cb5e1e0ab5a` license: MIT (fork of hukkin/tomli).
- `uiri-toml-0.10.2` https://github.com/uiri/toml @ `0.10.2` commit `3f637dba5f68db63d4b30967fedda51c82459471` license: MIT.
- `tomlkit-0.15.0` https://github.com/sdispater/tomlkit @ `0.15.0` commit `8694e4d3323df68eb325bf3d5ab7caa66f8c206a` license: MIT.
- `tomli-w-1.0.0` https://github.com/hukkin/tomli-w @ `1.0.0` commit `19099125f32e7c491603e393263754262b356956` license: MIT.
- `iniconfig-2.0.0` https://github.com/pytest-dev/iniconfig @ `v2.0.0` commit `93f5930e668c0d1ddf4597e38dd0dea4e2665e7a` license: MIT.
- `six-1.16.0` https://github.com/benjaminp/six @ `1.16.0` commit `65486e4383f9f411da95937451205d3c7b61b9e1` license: MIT.

## What a partial edit does

A rewrite that keeps only some functions can have rewrite containment near 1 and a lower Dice,
because Dice also penalizes original material that the rewrite does not contain.
Read both columns.

## Cross-language

`slug_vs_slug_js` is a hand port. Token fingerprints are same-language. Structural comparison
uses the lexer control-flow path. Artifact and test scores depend on shared strings and literals.
