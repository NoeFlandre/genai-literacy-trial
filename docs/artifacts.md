# Artifacts

## Public smoke outputs

The quantitative public output directory contains the following contract.

### Tables

```text
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
```

### Figures and report

Each figure stem is written as both `.png` and `.pdf`:

```text
fig_prompt_quality_trajectory
fig_prompt_quality_learning_outcome
fig_calibration_forest
```

The generated report is `quantitative_report.md`. The names come from `quant_schema.py`, `quant_figures.py`, and `quant_report.py` and are tested as public contracts.

## Legacy aggregate outputs

The older `analysis.py` path writes these top-level CSVs:

```text
sample_summary.csv
prompt_training_means.csv
prompt_grade_correlations.csv
paper_statistics.csv
validation_report.csv
```

The repository includes aggregate-only examples under `paper_outputs/` and `paper_outputs/quantitative/`. Treat them as checked-in manuscript-facing artifacts; do not overwrite them casually.

## Local and private paths

```text
repro_outputs/                 ignored generated smoke outputs
private_outputs/               ignored local diagnostics
data/private/                  ignored participant-level inputs
archive/                       ignored source/archive materials
clean_private_data/            ignored cleaning workspace
```

The current quantitative pipeline creates the requested `--output-dir` for local diagnostics but writes the documented public tables, figures, and report to `--public-output-dir`. Do not infer that a private output directory is a complete reproducible snapshot.

## Validation and freshness

```bash
uv run python scripts/validate_artifacts.py \
  --mode small \
  --public-output-dir repro_outputs/small/public
```

Validation checks source existence and non-emptiness, required output existence and non-emptiness, CSV readability, and mtime-based staleness. It does not hash file contents or prove statistical validity. The pipeline itself performs input, inventory, and generated-public-output privacy checks.
