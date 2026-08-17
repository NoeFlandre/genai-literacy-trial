# Common Failure Modes

This page lists mistakes that future agents should actively avoid or test for.

## Privacy And Public Output Failures

Failure: committing participant-level rows, raw prompt transcript columns, names, emails, spreadsheets, notebooks, or private draft files.

Prevention:

- Keep private files in ignored/private paths.
- Run `uv run genai-literacy-trial audit-privacy`.
- Run targeted audits on generated public paths before reporting success.

## Accidentally Overwriting Checked-In Artifacts

Failure: running `analyze-quant` with default `--public-output-dir paper_outputs/quantitative` when the task only needs a smoke check.

Prevention:

- Use `scripts/reproduce_small.py` for smoke work.
- Use `--public-output-dir repro_outputs/small/public`.
- Inspect `git status --short` after commands.

## Stale Or Incomplete Reproducibility Outputs

Failure: reporting artifacts as valid when they are older than inputs/configs, missing files, or unreadable CSVs.

Prevention:

```bash
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
```

The validator checks mtime staleness, not content hashes.

## Broken Public Artifact Contract

Failure: adding/removing a table or figure in generation code without updating schema constants, tests, docs, or validation.

Prevention:

- Tables: update `REQUIRED_QUANT_TABLES` in `quant_schema.py`, generation in `quant_pipeline.py`, and tests/docs.
- Figures: update `FIGURE_STEMS` or `FIGURE_FORMATS` in `quant_figures.py`, generation in `quant_pipeline.py`, and tests/docs.
- Report name: update `QUANTITATIVE_REPORT_FILENAME` and dependent tests/docs.

## Silent Join Or Filter Errors

Failure: dropout participants leaking into participant or assignment tables, duplicate grade rows being silently collapsed when conflicting, or prompt transcript columns reaching public outputs.

Prevention:

- Add small DataFrame tests in `tests/test_quant_preprocess.py`.
- Check `participant_key` use instead of raw IDs.
- Run inventory validation tests and `analyze-quant` CLI tests.

## Malformed Input Tables

Failure: missing configured columns, empty input tables, nonnumeric prompt scores, or malformed assignment labels reaching preprocessing or model fitting.

Prevention:

- Keep `run_quant_analysis()` input validation fail-fast.
- Add tiny fixture tests for each new input shape.
- Do not coerce malformed scientific values to missing unless that policy is explicitly documented.

## Duplicate Prompt Assignment Rows

Failure: multiple prompt rows for one participant/assignment silently bias participant mean prompt quality and prompt-observation counts.

Prevention:

- Reject duplicate participant/assignment prompt rows before participant-level aggregation.
- Keep duplicate-row tests near preprocessing/join tests.

## Config Alias Drift

Failure: changing config names or defaults without proving aliased columns still drive preprocessing.

Prevention:

- Update `config/quant_config.template.toml` and `quant_config.py` together.
- Add tests that load a temporary TOML and run preprocessing with aliased columns.
- Reject config contracts that make the design ambiguous, such as duplicate labels or identical pre/post labels.

## Expected Inventory Drift

Failure: accepting row-count drift silently when a workflow expects fixed survey/prompt inventory.

Prevention:

- Pass `--expected-inventory` for smoke and private reproducibility runs.
- Test mismatch behavior through the CLI.

## Statistical Contract Drift

Failure: changing formulas, p-value adjustment order, bootstrap seeds, or complete-case behavior without a regression test.

Prevention:

- Prefer golden-output or deterministic regression tests for metric tables.
- Keep deterministic seeds in `quant_stats.py`.
- Test missing values and small-sample edge cases.

## Misreading Tiny Synthetic Warnings

Failure: treating statsmodels/numpy warnings from the tiny fixture as proof the smoke workflow failed.

Prevention:

- Use `scripts/reproduce_small.py` for normal smoke runs; it suppresses expected tiny-model warnings.
- Use `--show-model-warnings` only for diagnostics.

## Claiming Full Reproduction From Public Clone

Failure: saying the full study is reproducible without private participant-level inputs.

Prevention:

- State that the public clone supports the synthetic workflow and aggregate-output validation.
- Mark full-study reproduction as documented but not runnable from the public repository.

## Adding Broad, Fragile Tests

Failure: adding tests only for line coverage or broad mocks that hide scientific regressions.

Prevention:

- Prefer tiny fixtures and focused assertions.
- Prioritize parsers, schema conversions, filters, joins, config handling, artifact contracts, and metric computations.
