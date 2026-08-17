# Reproducibility Guide

This repository has two reproducibility paths:

- **Small public smoke path:** reruns the quantitative workflow on `data/synthetic/` and needs no private data.
- **Full study path:** reruns the same public aggregate workflow on analysis-ready participant data. The required participant-level inputs are not distributed, so this path is documented but not runnable from a public clone.

The smallest meaningful reproducible workflow is the synthetic quantitative pipeline. It exercises input loading, configuration parsing, retained-participant preprocessing, model/table generation, figure generation, report generation, and the privacy audit for generated public outputs.

## Setup From A Clean Clone

Install `uv`, then clone and install the project dependencies:

```bash
git clone https://github.com/NoeFlandre/genai-literacy-trial.git
cd genai-literacy-trial
uv sync --dev
```

The project requires Python 3.11 or newer. The CI workflow currently installs Python 3.12 and runs lockfile, Ruff, `ty`, pytest, smoke, artifact validation, repository hygiene, and privacy checks.

## Required Data Inputs

For the small public path, the required inputs are tracked in the repository:

```text
data/synthetic/survey.csv
data/synthetic/grades.csv
data/synthetic/prompts.csv
config/quant_config.template.toml
config/expected_inventory.template.toml
```

For the full study path, equivalent analysis-ready survey, grades, and prompts files are required. Those participant-level records are intentionally excluded from the public repository. Full-run configuration may also require ignored private files such as `config/private_quant_config.toml` and `config/private_expected_inventory.toml`.

## Optional Data Inputs

The quantitative input loader accepts `survey`, `grades`, and `prompts` files as `.csv` or `.xlsx`. The public smoke path uses `.csv`.

The older aggregate-only CLI path, `genai-literacy-trial reproduce-paper`, expects `survey.csv`, `grades.csv`, and `prompts.csv` and writes top-level aggregate CSVs to `paper_outputs/`.

## Tiny Smoke Test

Run the public synthetic workflow:

```bash
uv run python scripts/reproduce_small.py
```

By default this writes generated artifacts to ignored local directories:

```text
repro_outputs/small/public/
repro_outputs/small/private/
```

To write somewhere else:

```bash
uv run python scripts/reproduce_small.py \
  --public-output-dir /tmp/genai-literacy-public \
  --output-dir /tmp/genai-literacy-private
```

## Full Pipeline

The public synthetic equivalent of the full quantitative command is:

```bash
uv run genai-literacy-trial analyze-quant \
  --input-dir data/synthetic \
  --config config/quant_config.template.toml \
  --expected-inventory config/expected_inventory.template.toml \
  --output-dir repro_outputs/small/private \
  --public-output-dir repro_outputs/small/public
```

With unavailable full study data, use the same command shape and replace `--input-dir`, `--config`, `--expected-inventory`, `--output-dir`, and `--public-output-dir` with local private paths. Do not write participant-level outputs into tracked public directories.

## Validate Outputs

Validate the generated small-run artifacts:

```bash
uv run python scripts/validate_artifacts.py \
  --mode small \
  --public-output-dir repro_outputs/small/public
```

Run the privacy audit:

```bash
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

Run the test suite:

```bash
uv run pytest
```

The artifact validator checks that required public outputs exist, are non-empty, that CSV outputs are readable, and that outputs are not older than the newest relevant input/config file.

## Stale Cached Outputs

Generated outputs are considered stale when an output file is older than any source input or configuration file used for the run. Check this with:

```bash
uv run python scripts/validate_artifacts.py \
  --mode small \
  --public-output-dir repro_outputs/small/public
```

If stale artifacts are reported, rerun `scripts/reproduce_small.py` or rerun `genai-literacy-trial analyze-quant` with the same inputs and output directories. Use `--allow-stale` only when intentionally inspecting archived outputs.

The repository does not currently store artifact hashes or a run manifest, so staleness is based on filesystem modification times.

## Expected Outputs

The smoke run should produce the quantitative report, required public CSV tables, and PNG/PDF figures in the selected public output directory. See [artifacts.md](artifacts.md) for the current artifact inventory.

The synthetic outputs are not expected to match manuscript target statistics. The synthetic data are fixtures for exercising the public workflow, not the participant-level study dataset.

## Hardware And Runtime

The public smoke path uses six synthetic participants and runs local Python, pandas, scipy, statsmodels, and matplotlib code. The repository does not include benchmarked runtime or memory requirements. On ordinary researcher laptops it is expected to be a small job; if it takes several minutes, check that the command is using `data/synthetic/` and not a large private input directory.

The full study path is expected to be modest because the public metadata describes a classroom-scale study, but exact runtime and hardware needs cannot be confirmed from the public repository alone.

## Known Non-Reproducible Components

- Participant-level survey rows, grade records, prompt records, rosters, and private cleaning artifacts are not distributed.
- Private configuration files are ignored and may be required to reproduce author-side full-study outputs exactly.
- Manuscript target validation in `paper_outputs/validation_report.csv` depends on aggregate targets from the private study data. Synthetic smoke outputs may report mismatches or missing manuscript target metrics.
- The ignored `clean_private_data/`, `archive/`, and `private_outputs/` directories are not part of the public reproducibility package.

## Troubleshooting

If `uv` is missing, install it first and rerun `uv sync --dev`.

If imports fail when running Python scripts directly, run commands through `uv run` from the repository root.

If `validate_artifacts.py` reports missing outputs, rerun `uv run python scripts/reproduce_small.py` and confirm the same `--public-output-dir` is passed to the validator.

If you need to inspect model warnings from the tiny synthetic dataset, rerun the smoke command with `--show-model-warnings`. The default smoke wrapper hides expected statsmodels/numpy warnings so validation output stays readable.

If the privacy audit fails, inspect the reported file and remove participant-level or private identifiers from the public output path. Do not silence privacy findings for public release artifacts.

If inventory validation fails on private data, update the ignored private expected-inventory file only after confirming that the data extraction and retention criteria are correct.
