# Artifacts

This repository separates public aggregate artifacts from private/local research materials.

## Public Inputs

Tracked public inputs for the small workflow:

```text
data/synthetic/survey.csv
data/synthetic/grades.csv
data/synthetic/prompts.csv
config/quant_config.template.toml
config/expected_inventory.template.toml
```

The synthetic data are tiny fixtures for exercising the workflow. They are not de-identified participant records and are not expected to reproduce manuscript statistics.

## Main Quantitative Outputs

`run_quant_analysis()` writes the public quantitative artifact set to the selected public output directory. For `scripts/reproduce_small.py`, that directory defaults to:

```text
repro_outputs/small/public/
```

For `genai-literacy-trial analyze-quant`, the CLI default is:

```text
paper_outputs/quantitative/
```

Required public quantitative artifacts are:

```text
quantitative_report.md
table_data_verification.csv
table_missingness_prompt_by_group_assignment.csv
table_baseline_balance.csv
table_prompt_trajectory_model.csv
table_prompt_trajectory_estimated_means.csv
table_participant_training_contrasts.csv
table_participant_training_tests.csv
table_learning_outcome_models.csv
table_prompt_grade_correlations.csv
table_calibration_models.csv
table_survey_reliability.csv
table_prepost_survey_change.csv
table_small_sample_sensitivity.csv
table_perceived_usefulness_models.csv
table_complete_case_diagnostics.csv
table_prior_use_mapping.csv
table_scored_assignment_distribution_by_group.csv
table_prompt_sensitivity_min3_assignments.csv
table_prompt_sensitivity_all4_assignments.csv
fig_prompt_quality_trajectory.pdf
fig_prompt_quality_trajectory.png
fig_prompt_quality_learning_outcome.pdf
fig_prompt_quality_learning_outcome.png
fig_calibration_forest.pdf
fig_calibration_forest.png
```

The authoritative table names live in `src/genai_literacy_trial/quant_schema.py`. Figure stems and formats live in `src/genai_literacy_trial/quant_figures.py`. The report filename lives in `src/genai_literacy_trial/quant_report.py`.

## Legacy Aggregate Outputs

The legacy aggregate-paper workflow writes top-level CSVs under `paper_outputs/` by default:

```text
sample_summary.csv
prompt_training_means.csv
prompt_grade_correlations.csv
paper_statistics.csv
validation_report.csv
```

`validation_report.csv` compares observed aggregate metrics with `PAPER_TARGETS` in `analysis.py`.

## Checked-In Public Outputs

Checked-in public artifacts currently include:

```text
paper_outputs/
paper_outputs/quantitative/
docs/figures/study_overview.png
docs/figures/study_overview.pdf
docs/figures/study_overview.tex
```

These must remain aggregate-only or static documentation assets.

## Ignored Or Private Artifacts

The following paths are intentionally local-only or ignored:

```text
archive/
clean_private_data/
clean_private_data/analysis_ready/
data/private/
private_outputs/
repro_outputs/
config/private_quant_config.toml
config/private_expected_inventory.toml
privacy_patterns.local.yml
```

Do not move private inputs, raw exports, notebooks, spreadsheets, rosters, or participant-level diagnostics into tracked paths.

## Artifact Validation

Run:

```bash
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
```

The validator reports:

- `missing_source` or `empty_source` for unavailable inputs/configuration.
- `missing`, `not_file`, or `empty` for missing or invalid output artifacts.
- `invalid_csv` for CSV artifacts that pandas cannot read.
- `stale` when an output is older than the newest source input or configuration file.

The validator does not compare artifact contents against a golden hash. It checks the public artifact contract and modification times.
