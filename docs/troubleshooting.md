# Troubleshooting

## `uv` Or Import Errors

Run commands from the repository root through `uv run`:

```bash
uv sync --dev
uv run python scripts/reproduce_small.py
```

The scripts add `src/` to `sys.path` for direct execution, but `uv run` also ensures the declared dependencies are available.

## Missing Input Files

For the quantitative pipeline, `--input-dir` must contain:

```text
survey.csv or survey.xlsx
grades.csv or grades.xlsx
prompts.csv or prompts.xlsx
```

The legacy `reproduce-paper` command only reads CSV files named:

```text
survey.csv
grades.csv
prompts.csv
```

## Empty Or Malformed Input Tables

`analyze-quant` now validates the three quantitative input tables before preprocessing. It fails fast if:

- `survey`, `grades`, or `prompts` is empty,
- a required configured column is missing,
- prompt assignment values are nonnumeric, nonfinite, or noninteger,
- prompt scores are nonnumeric or nonfinite.

Fix the source table or the column aliases in the TOML config before rerunning. These checks run before model fitting so malformed rows do not become silent aggregate or metric errors.

## Duplicate Prompt Assignment Rows

Each participant can contribute at most one prompt row per assignment. Duplicate participant/assignment prompt rows fail before participant means are computed, because duplicates would silently bias `mean_prompt_score` and prompt-observation counts.

## Expected Inventory Mismatch

When `--expected-inventory` is supplied, the run fails if observed row counts differ from the TOML counts. For the public smoke workflow, compare against:

```text
config/expected_inventory.template.toml
```

For private full-study runs, update ignored private expected-inventory files only after confirming the data extraction and retention criteria.

## Unmapped Prior ChatGPT Use

`run_quant_analysis()` fails if `prior_use_mapping_table()` finds unmapped pre-survey prior-use categories. Add valid categories to `[likert_mapping]` in the relevant TOML config or correct the input data.

## Invalid Grades, Groups, Assignments, Or Prompt Scores

Preprocessing and inventory validation can fail on:

- unmapped letter grades,
- group labels outside configured groups,
- assignment values outside configured assignments,
- prompt scores outside 1 to 5,
- retained survey participants without exactly one pre and one post row,
- conflicting duplicate grade rows.

Check `config/quant_config.template.toml` or your private config before changing code.

## Invalid Quantitative Config Contracts

`load_quant_config()` rejects invalid scientific contracts such as identical pre/post labels, duplicate group labels, duplicate assignment labels, or `min_public_cell_count < 1`. Correct the TOML config rather than working around these errors in code.

## Stale Artifacts

Run:

```bash
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
```

If the validator reports `stale`, rerun:

```bash
uv run python scripts/reproduce_small.py
```

Staleness is based on file modification times, not content hashes.

## Privacy Audit Failures

Run the scanner on the path you plan to publish:

```bash
uv run genai-literacy-trial audit-privacy --root paper_outputs
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

The scanner rejects common private text patterns and denied suffixes such as `.xlsx`, `.docx`, `.ipynb`, and `.pptx` in public paths. It skips private/cache directories listed in `privacy.py`.

If the scanner reports a local pattern from `privacy_patterns.local.yml`, remove the matching public file or text. Do not commit `privacy_patterns.local.yml`.

## Model Warnings In Tiny Synthetic Runs

The tiny public fixture can produce statsmodels/numpy convergence or divide-by-zero warnings because the dataset is intentionally small. `scripts/reproduce_small.py` suppresses those warnings by default. Use:

```bash
uv run python scripts/reproduce_small.py --show-model-warnings
```

when diagnosing model behavior.

## Synthetic Outputs Do Not Match Manuscript Targets

The synthetic data exercise the workflow; they are not the private study dataset. Mismatches or missing manuscript target metrics in synthetic validation reports are expected unless the private source data are available.

## Public Output Directory Contains Old Files

`analyze-quant` removes only top-level files with generated suffixes `.csv`, `.pdf`, `.png`, and `.md` from the public output directory before writing new outputs. Nested files and other suffixes are preserved. Remove unrelated files manually if needed.

## Repository Hygiene Check Cannot Run

`scripts/check_repo_hygiene.py` and `genai-literacy-check-repo-hygiene` shell out to `git ls-files`. If they report that `git ls-files failed`, run the check from a Git checkout and confirm `git` is installed and available on `PATH`.
