# CLI Reference

Install the project first:

```bash
uv sync --locked --dev
```

Use `--help` for the complete Typer-generated option list:

```bash
uv run genai-literacy-trial --help
```

## Primary quantitative command

```bash
uv run genai-literacy-trial analyze-quant \
  --input-dir data/synthetic \
  --config config/quant_config.template.toml \
  --expected-inventory config/expected_inventory.template.toml \
  --output-dir repro_outputs/small/private \
  --public-output-dir repro_outputs/small/public
```

Defaults are `data/synthetic`, the public template config, no expected-inventory file, `private_outputs/quantitative`, and `paper_outputs/quantitative`, respectively. The command accepts CSV, XLSX, and compatibility-prefixed CSV input names; see [Configuration](configuration.md).

It writes aggregate tables, figures, and `quantitative_report.md`, then scans the selected public output directory. The `--output-dir` is a local diagnostics path and must not be a tracked public directory.

## Public smoke wrapper

```bash
uv run python scripts/reproduce_small.py
```

Equivalent forms:

```bash
uv run python -m genai_literacy_trial.reproduce_small
uv run genai-literacy-reproduce-small
```

Useful options are `--input-dir`, `--config`, `--expected-inventory`, `--output-dir`, `--public-output-dir`, `--allow-stale`, `--manifest`, and `--show-model-warnings`. `--manifest` writes an optional local SHA-256 record after a successful run.

## Artifact validator

```bash
uv run python scripts/validate_artifacts.py \
  --mode small \
  --public-output-dir repro_outputs/small/public
```

Equivalent forms are `python -m genai_literacy_trial.validate_artifacts` and `genai-literacy-validate-artifacts`. The validator supports `--input-dir`, `--config`, `--expected-inventory`, `--public-output-dir`, `--allow-stale`, and optional `--manifest` SHA-256 validation.

## Privacy and hygiene

```bash
uv run genai-literacy-trial audit-privacy
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
uv run python scripts/check_repo_hygiene.py
```

`audit-privacy` accepts `--root` and optional `--local-patterns`. The hygiene wrapper checks tracked file sizes; its default threshold is 5 MiB.

## Legacy aggregate commands

```bash
uv run genai-literacy-trial build-aggregates
uv run genai-literacy-trial validate-paper
uv run genai-literacy-trial reproduce-paper
```

These commands default to `data/synthetic` and `paper_outputs`. They use the older aggregate implementation in `analysis.py` and should not be confused with the newer quantitative artifact contract.
