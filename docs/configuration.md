# Configuration Reference

The public quantitative workflow is configured by TOML files in `config/`.

## Public Template Config

`config/quant_config.template.toml` defines:

- `[columns]`: source column names for participant IDs, phase labels, group labels, assignments, prompt scores, grades, prior use, gender, and major.
- `[labels]`: pre/post phase labels, expected groups, and expected assignment numbers.
- `[privacy]`: public-output suppression settings such as `min_public_cell_count`.
- `[survey_dimensions]`: survey composite definitions.
- `[reverse_coded_items]`: reverse-scored survey items by dimension.
- `[likert_mapping]`: conversion from survey response text to numeric values.
- `[grade_mapping]`: conversion from letter grades to grade points.

Use the template as the starting point for public synthetic runs:

```bash
uv run genai-literacy-trial analyze-quant \
  --input-dir data/synthetic \
  --config config/quant_config.template.toml \
  --expected-inventory config/expected_inventory.template.toml \
  --output-dir repro_outputs/small/private \
  --public-output-dir repro_outputs/small/public
```

## Expected Inventory

`config/expected_inventory.template.toml` documents the expected synthetic fixture counts, including pre/post responses, retained participants, survey rows, prompt assignment rows, scored prompt observations, missing prompt scores, and group counts.

Pass an expected-inventory file when you want the pipeline to fail on unexpected row-count drift:

```bash
--expected-inventory config/expected_inventory.template.toml
```

For private full-study runs, use an ignored private inventory file after confirming the data extraction criteria.

## Input File Names

The quantitative pipeline expects these dataset names in the input directory:

```text
survey.csv or survey.xlsx
grades.csv or grades.xlsx
prompts.csv or prompts.xlsx
```

For compatibility with the private cleaning workflow, it also accepts:

```text
public_cli_input_survey.csv
public_cli_input_grades.csv
public_cli_input_prompts.csv
```

The older aggregate-only `reproduce-paper` command expects only:

```text
survey.csv
grades.csv
prompts.csv
```

## Environment Variables

No environment variables are required for the public smoke path.

The figure code sets matplotlib to the non-interactive `Agg` backend in code, so `MPLBACKEND` is not required for headless runs. Use standard Python or `uv` environment variables only if needed for your local development environment.

The `Dockerfile` sets `UV_SYSTEM_PYTHON=1` inside the container before running `uv sync --dev`.

## Private Configuration

The following private config paths are ignored by git:

```text
config/private_quant_config.toml
config/private_expected_inventory.toml
```

Use private config files for real study column mappings or inventory targets that cannot be published. Keep them out of public commits.

## Privacy Settings

`min_public_cell_count` controls small-cell suppression in public aggregate tables. The public template sets it to `5`.

The privacy audit can also read ignored local patterns from `privacy_patterns.local.yml`:

```bash
uv run genai-literacy-trial audit-privacy \
  --root paper_outputs \
  --local-patterns privacy_patterns.local.yml
```

Only use local patterns to add stricter checks. Do not use them to bypass public privacy findings.

## Cache And Output Configuration

`analyze-quant` writes public outputs to `--public-output-dir` and creates the directory passed to `--output-dir`. The public output directory is cleaned before each run only for top-level generated-style suffixes: `.csv`, `.pdf`, `.png`, and `.md`.

`scripts/reproduce_small.py` defaults to ignored `repro_outputs/small/` paths so local smoke runs do not modify checked-in `paper_outputs/`.
