# Repository Map For Agents

Use this as a navigation aid before editing.

## Top-Level Files

`README.md`
: Research/developer entry point with setup, smoke workflow, tests, and doc links.

`AGENTS.md`
: Concise agent instructions and invariants.

`pyproject.toml`
: Python package metadata, dependencies, `genai-literacy-trial` entry point, pytest config. Package manager is `uv`.

`uv.lock`
: Locked dependency graph.

`Dockerfile`
: Container setup for running `uv run pytest`. Inspected but not part of CI.

`.github/workflows/ci.yml`
: CI installs uv/Python 3.12, checks the lockfile, syncs locked dependencies, runs Ruff, `ty`, pytest, smoke/artifact validation, repository hygiene, and privacy audits.

## Source Package

`src/genai_literacy_trial/cli.py`
: Typer commands: `build-aggregates`, `validate-paper`, `reproduce-paper`, `audit-privacy`, and `analyze-quant`.

`src/genai_literacy_trial/paths.py`
: Shared repository-root paths for public fixtures, template configs, and smoke output defaults.

`src/genai_literacy_trial/reproduce_small.py`
: Package implementation for the public synthetic smoke runner. Also exposed as `genai-literacy-reproduce-small`.

`src/genai_literacy_trial/validate_artifacts.py`
: Package implementation for the small artifact validator. Also exposed as `genai-literacy-validate-artifacts`.

`src/genai_literacy_trial/repo_hygiene.py`
: Package implementation for tracked-file size checks. Also exposed as `genai-literacy-check-repo-hygiene`.

`src/genai_literacy_trial/analysis.py`
: Legacy aggregate-paper workflow and manuscript target validation.

`src/genai_literacy_trial/quant_pipeline.py`
: Main quantitative orchestration. This is the first file to inspect for workflow changes.

`src/genai_literacy_trial/quant_preprocess.py`
: Participant hashing, retained pre/post filtering, grade/prompt joins, composite scoring, prior-use mapping, inventory validation, and small-cell suppression.

`src/genai_literacy_trial/quant_config.py`
: TOML config dataclasses/loaders and expected inventory shape.

`src/genai_literacy_trial/quant_models.py`
: Model/table generation for trajectory, training effects, learning outcomes, calibration, pre/post change, diagnostics, and sensitivity.

`src/genai_literacy_trial/quant_stats.py`
: Statistical helper functions and deterministic seeds.

`src/genai_literacy_trial/quant_schema.py`
: Public table names and result TypedDicts. Update this with care.

`src/genai_literacy_trial/quant_figures.py`
: Figure names/formats and matplotlib rendering.

`src/genai_literacy_trial/quant_report.py`
: Markdown report writer and generated report filename.

`src/genai_literacy_trial/privacy.py`
: Privacy scanner rules, skipped directories, denied suffixes, and local pattern loading.

`src/genai_literacy_trial/scales.py`
: Shared grade and Likert mappings.

## Scripts

`scripts/reproduce_small.py`
: Compatibility wrapper for `genai_literacy_trial.reproduce_small`. Uses `data/synthetic/`, writes to ignored `repro_outputs/small/`, suppresses tiny-model warnings by default, and validates outputs.

`scripts/validate_artifacts.py`
: Compatibility wrapper for `genai_literacy_trial.validate_artifacts`.

`scripts/check_repo_hygiene.py`
: Compatibility wrapper for `genai_literacy_trial.repo_hygiene`.

## Data And Config

`data/synthetic/survey.csv`
`data/synthetic/grades.csv`
`data/synthetic/prompts.csv`
: Tiny non-identifying fixtures. Keep them small.

`config/quant_config.template.toml`
: Public column, label, privacy, survey dimension, reverse-coding, Likert, and grade mapping config.

`config/expected_inventory.template.toml`
: Expected counts for synthetic inputs.

## Outputs And Artifacts

`paper_outputs/`
: Checked-in aggregate-only legacy outputs and validation report.

`paper_outputs/quantitative/`
: Checked-in quantitative tables, figures, and markdown report.

`repro_outputs/`
: Ignored local output root for smoke runs.

`private_outputs/`
: Ignored local/private output root.

## Tests

`tests/quant_fixtures.py`
: Synthetic DataFrame fixture builder.

`tests/test_quant_preprocess.py`
: Filters, joins, composites, inventory validation, prior-use mapping, small-cell suppression.

`tests/test_quant_models.py`
: Model/table behavior, deterministic contrasts, diagnostics, sensitivity, prediction tables.

`tests/test_quant_stats.py`
: Statistical helper edge cases and deterministic outputs.

`tests/test_quant_cli.py`
: `analyze-quant` CLI generation, cleanup, and inventory failure behavior.

`tests/test_reproducibility_scripts.py`
: Public smoke runner and artifact validator.

`tests/test_privacy.py`
: Privacy scanner behavior.

Other test files cover legacy aggregate analysis, schema constants, report generation, figures, scales, and basic CLI behavior.

## Docs

`docs/architecture.md`
: Module responsibilities and extension rules.

`docs/data_flow.md`
: Quantitative and legacy pipeline flow.

`docs/diagrams.md`
: Concise Mermaid diagrams for architecture, data flow, artifacts, CLI/module mapping, and agent workflow.

`docs/cli.md`
: Commands and scripts.

`docs/artifacts.md`
: Public inputs, outputs, artifact names, and validation.

`docs/configuration.md`
: TOML config and environment notes.

`docs/reproducibility.md`
: Clean-clone setup and reproducibility paths.

`docs/troubleshooting.md`
: Failure modes and fixes.

`docs/common_failure_modes.md`
: Agent-focused failure-mode checklist.
