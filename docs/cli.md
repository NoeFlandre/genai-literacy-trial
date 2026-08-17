# CLI And Scripts

The installed command is:

```bash
uv run genai-literacy-trial
```

It is a Typer app defined in `src/genai_literacy_trial/cli.py`.

Additional console entry points expose the public smoke and hygiene helpers:

```bash
uv run genai-literacy-reproduce-small
uv run genai-literacy-validate-artifacts
uv run genai-literacy-check-repo-hygiene
```

The `scripts/` files documented below are compatibility wrappers around package modules in `src/genai_literacy_trial/`.

## Public Smoke Scripts

### `scripts/reproduce_small.py`

Verified smoke command:

```bash
uv run python scripts/reproduce_small.py
```

Equivalent module and console forms:

```bash
uv run python -m genai_literacy_trial.reproduce_small
uv run genai-literacy-reproduce-small
```

Defaults:

```text
--input-dir data/synthetic
--config config/quant_config.template.toml
--expected-inventory config/expected_inventory.template.toml
--output-dir repro_outputs/small/private
--public-output-dir repro_outputs/small/public
```

Useful options:

```bash
uv run python scripts/reproduce_small.py \
  --public-output-dir /tmp/genai-literacy-public \
  --output-dir /tmp/genai-literacy-private
```

Use `--show-model-warnings` to show statsmodels/numpy warnings from the tiny synthetic dataset. The default wrapper hides those warnings so smoke output is readable.

### `scripts/validate_artifacts.py`

Verified validator command:

```bash
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
```

Equivalent module and console forms:

```bash
uv run python -m genai_literacy_trial.validate_artifacts --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-validate-artifacts --mode small --public-output-dir repro_outputs/small/public
```

Defaults:

```text
--mode small
--input-dir data/synthetic
--config config/quant_config.template.toml
--expected-inventory config/expected_inventory.template.toml
--public-output-dir repro_outputs/small/public
```

The validator checks source files, required output files, non-empty files, CSV readability, and mtime-based staleness. Use `--allow-stale` only for intentional inspection of archived outputs.

### `scripts/check_repo_hygiene.py`

Tracked-file size check:

```bash
uv run python scripts/check_repo_hygiene.py
```

Equivalent module and console forms:

```bash
uv run python -m genai_literacy_trial.repo_hygiene
uv run genai-literacy-check-repo-hygiene
```

Default threshold:

```text
--max-mib 5.0
```

The script uses `git ls-files`, so it checks committed/tracked files rather than ignored local outputs.

## `genai-literacy-trial analyze-quant`

Main quantitative pipeline:

```bash
uv run genai-literacy-trial analyze-quant \
  --input-dir data/synthetic \
  --config config/quant_config.template.toml \
  --expected-inventory config/expected_inventory.template.toml \
  --output-dir repro_outputs/small/private \
  --public-output-dir repro_outputs/small/public
```

Defaults from the CLI:

```text
--input-dir data/synthetic
--config config/quant_config.template.toml
--expected-inventory None
--output-dir private_outputs/quantitative
--public-output-dir paper_outputs/quantitative
```

The command prints the public output directory and runs a privacy audit on generated public outputs before returning.

## `genai-literacy-trial reproduce-paper`

Legacy aggregate-paper pipeline:

```bash
uv run genai-literacy-trial reproduce-paper
```

Defaults:

```text
--input-dir data/synthetic
--output-dir paper_outputs
```

This combines `build-aggregates` and `validate-paper`: it writes aggregate CSVs and `validation_report.csv`.

## `genai-literacy-trial build-aggregates`

Legacy aggregate table generation:

```bash
uv run genai-literacy-trial build-aggregates --input-dir data/synthetic --output-dir paper_outputs
```

Reads `survey.csv`, `grades.csv`, and `prompts.csv`. Writes aggregate CSV tables.

## `genai-literacy-trial validate-paper`

Legacy target validation:

```bash
uv run genai-literacy-trial validate-paper --output-dir paper_outputs
```

Reads `paper_statistics.csv` when present, otherwise falls back to `sample_summary.csv`, and writes `validation_report.csv`.

## `genai-literacy-trial audit-privacy`

Privacy scanner:

```bash
uv run genai-literacy-trial audit-privacy
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

Options:

```text
--root .
--local-patterns None
```

When `--local-patterns` is omitted, the scanner looks for `privacy_patterns.local.yml` under the selected root. That file is ignored by git.

## Docker

The `Dockerfile` installs `uv`, copies `pyproject.toml`, `uv.lock`, `README.md`, `src/`, `tests/`, and `data/`, runs `uv sync --dev`, and defaults to:

```bash
uv run pytest
```

The Docker workflow was inspected in this docs update but not run locally.
