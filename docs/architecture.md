# Architecture

This repository is a small Python package plus reproducibility scripts. The package entry point is `genai-literacy-trial`, defined in `pyproject.toml` as `genai_literacy_trial.cli:app`.

For concise visual summaries, see `docs/diagrams.md`.

## Package Modules

`src/genai_literacy_trial/cli.py`
: Typer command definitions for aggregate generation, paper validation, privacy audit, and quantitative analysis.

`src/genai_literacy_trial/analysis.py`
: Legacy aggregate-paper workflow. It reads `survey.csv`, `grades.csv`, and `prompts.csv`, computes aggregate summary/correlation/statistic tables, and validates observed metrics against `PAPER_TARGETS`.

`src/genai_literacy_trial/quant_config.py`
: TOML config loader. Defines column names, phase/group/assignment labels, small-cell suppression threshold, survey dimensions, reverse-coded items, Likert mapping, grade mapping, and expected inventory shape.

`src/genai_literacy_trial/quant_preprocess.py`
: Participant-key hashing, retained pre/post survey filtering, participant table construction, assignment prompt table construction, survey composites, prior-use mapping, inventory validation, and small-cell suppression.

`src/genai_literacy_trial/quant_stats.py`
: Deterministic statistical helpers: bootstrap CIs, Welch/permutation ANOVA, Kruskal test, Hedges g, Pearson/Spearman correlations with CIs, Benjamini-Hochberg FDR, Cronbach alpha, standardization, and small-sample sensitivity.

`src/genai_literacy_trial/quant_models.py`
: Quantitative model tables. Covers prompt trajectory, participant-level training contrasts, learning-outcome models, complete-case diagnostics, perceived-usefulness models, calibration models, pre/post survey change models, prompt-missingness sensitivity, and model-based prediction table.

`src/genai_literacy_trial/quant_pipeline.py`
: Main quantitative orchestration. Loads inputs/config, runs preprocessing, model/table generation, figure generation, report generation, output cleanup, and privacy audit for generated public outputs.

`src/genai_literacy_trial/quant_schema.py`
: Public output contracts and TypedDict result shapes. `REQUIRED_QUANT_TABLES` is the authoritative public quantitative table list.

`src/genai_literacy_trial/quant_figures.py`
: Matplotlib figure generation. Uses the non-interactive `Agg` backend and writes each figure as both PDF and PNG.

`src/genai_literacy_trial/quant_report.py`
: Markdown quantitative report writer. `QUANTITATIVE_REPORT_FILENAME` is `quantitative_report.md`.

`src/genai_literacy_trial/privacy.py`
: Public-tree privacy scanner. Skips ignored private/cache directories, scans supported text files for private patterns, and rejects denied public file suffixes such as `.xlsx`, `.docx`, `.ipynb`, and `.pptx`.

`src/genai_literacy_trial/scales.py`
: Shared grade and Likert scale constants.

`src/genai_literacy_trial/paths.py`
: Shared repository-root path constants for public synthetic inputs, template configs, and smoke output defaults.

`src/genai_literacy_trial/reproduce_small.py`, `validate_artifacts.py`, `repo_hygiene.py`
: Package implementations for the public smoke, artifact validation, and tracked-file hygiene helpers. These are available through module commands, console scripts, and compatibility wrappers under `scripts/`.

## Scripts

`scripts/reproduce_small.py`
: Compatibility wrapper for `genai_literacy_trial.reproduce_small`. Runs `run_quant_analysis()` on `data/synthetic/`, writes ignored local outputs under `repro_outputs/small/`, suppresses expected tiny-fixture model warnings by default, and calls the artifact validator.

`scripts/validate_artifacts.py`
: Compatibility wrapper for `genai_literacy_trial.validate_artifacts`. Validates the small reproducibility artifact contract.

`scripts/check_repo_hygiene.py`
: Compatibility wrapper for `genai_literacy_trial.repo_hygiene`.

## Tests

Tests live in `tests/` and use synthetic fixtures only. Important coverage areas include:

- CLI workflows in `tests/test_cli.py`, `tests/test_quant_cli.py`, and `tests/test_reproducibility_scripts.py`.
- Quant preprocessing/data joins in `tests/test_quant_preprocess.py`.
- Model and metric outputs in `tests/test_quant_models.py` and `tests/test_quant_stats.py`.
- Public artifact/schema contracts in `tests/test_quant_schema.py`, `tests/test_quant_pipeline.py`, `tests/test_quant_report.py`, and `tests/test_quant_figures.py`.
- Privacy scanning in `tests/test_privacy.py`.

## Extension Rules

- Keep participant-level data out of tracked files.
- Add or update synthetic fixtures when changing public workflow behavior.
- When adding a public quantitative table, update `REQUIRED_QUANT_TABLES`, generate it in `quant_pipeline.py`, and update tests/docs.
- When adding a public figure, update `FIGURE_STEMS` or `FIGURE_FORMATS` in `quant_figures.py`, generate it in `quant_pipeline.py`, and update tests/docs.
- Preserve the public-output privacy audit at the end of `run_quant_analysis()`.
- Prefer focused tests for joins, filters, config mapping, inventory validation, metric formulas, and artifact contracts.
- Keep public outputs aggregate-only; diagnostics that might contain participant-level rows belong in ignored private/local directories.
