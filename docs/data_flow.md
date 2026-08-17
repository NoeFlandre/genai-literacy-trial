# Data Flow

The repository has two analysis paths: the main quantitative pipeline and an older aggregate-paper pipeline.

For concise visual summaries, see `docs/diagrams.md`.

## Main Quantitative Pipeline

Entry points:

```bash
uv run python scripts/reproduce_small.py
uv run genai-literacy-trial analyze-quant ...
```

Code path:

```text
CLI/script
  -> quant_pipeline.run_quant_analysis()
  -> quant_config.load_quant_config()
  -> quant_config.load_expected_inventory()
  -> quant_pipeline._read_input()
  -> quant_preprocess.prepare_retained_survey()
  -> quant_preprocess.build_participant_table()
  -> quant_preprocess.compute_survey_composites()
  -> quant_pipeline._merge_pre_composites()
  -> quant_preprocess.build_assignment_prompt_table()
  -> quant_preprocess.prior_use_mapping_table()
  -> quant_preprocess.validate_analysis_inventory()
  -> quant_models and quant_stats
  -> quant_figures
  -> quant_report.write_quantitative_report()
  -> privacy.scan_public_tree(public_output_dir)
```

## Inputs

The quantitative loader reads these dataset basenames from `--input-dir`:

```text
survey.csv or survey.xlsx
grades.csv or grades.xlsx
prompts.csv or prompts.xlsx
```

It also accepts compatibility names:

```text
public_cli_input_survey.csv
public_cli_input_grades.csv
public_cli_input_prompts.csv
```

The public smoke workflow uses:

```text
data/synthetic/survey.csv
data/synthetic/grades.csv
data/synthetic/prompts.csv
```

## Identifiers And Retention

`quant_preprocess.participant_key()` hashes source IDs with SHA-256 and truncates to 12 hex characters. Public intermediate tables use `participant_key`, not the original ID.

`prepare_retained_survey()` keeps participants present in both configured pre and post survey phases. It reports `pre_responses`, `post_responses`, `dropouts`, `retained_participants`, and `retained_survey_rows`.

`build_participant_table()`:

- filters grades to retained participants,
- rejects conflicting duplicate grade rows,
- maps letter grades to numeric grade points,
- merges pre-survey optional fields such as prior use, gender, and major,
- computes mean prompt score and scored-assignment count from prompts.

`build_assignment_prompt_table()`:

- drops raw transcript-like columns matching `User...` or `GPT...`,
- hashes participant IDs,
- merges group labels from retained participants,
- returns assignment-level `participant_key`, `group`, `assignment`, and `prompt_score`.

## Survey Composites

`compute_survey_composites()` uses `config/quant_config.template.toml` survey dimensions and reverse-coded items. It normalizes configured phase labels to:

```text
pre
post
```

Composite scores require at least half of available items for that dimension, with a minimum of one item.

## Inventory Validation

`validate_analysis_inventory()` checks:

- one pre and one post row per retained participant,
- unique participant-level rows,
- groups inside configured labels,
- assignments inside configured labels,
- prompt scores between 1 and 5,
- no transcript columns after prompt preprocessing,
- optional expected inventory counts.

When an expected-inventory TOML is supplied, mismatches raise `ValueError`.

## Outputs

The main pipeline writes:

```text
<public-output-dir>/table_*.csv
<public-output-dir>/fig_*.pdf
<public-output-dir>/fig_*.png
<public-output-dir>/quantitative_report.md
```

It creates the private/local diagnostics directory passed as `--output-dir`, but the current pipeline does not write substantive diagnostic files there.

## Cache And Cleanup Behavior

There is no content-addressed cache and no run manifest.

Before a quantitative run writes public outputs, `_clean_public_output_dir()` deletes only top-level files in `--public-output-dir` whose suffix is one of:

```text
.csv
.pdf
.png
.md
```

It preserves nested directories and files with other suffixes, such as `notes.txt`.

`scripts/validate_artifacts.py` treats an output as stale if it is older than any input/config source file used for the small run. This is mtime-based only.

## Legacy Aggregate-Paper Pipeline

Entry points:

```bash
uv run genai-literacy-trial build-aggregates
uv run genai-literacy-trial validate-paper
uv run genai-literacy-trial reproduce-paper
```

This path reads `survey.csv`, `grades.csv`, and `prompts.csv`; it does not use the TOML quantitative config. It writes top-level aggregate CSVs such as:

```text
sample_summary.csv
prompt_training_means.csv
prompt_grade_correlations.csv
paper_statistics.csv
validation_report.csv
```

By default those files go to `paper_outputs/`.
