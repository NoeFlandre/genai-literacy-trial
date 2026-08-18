# Configuration

## Public quantitative template

`config/quant_config.template.toml` is the public starting point for `analyze-quant`. Its sections are:

| Section | Purpose |
| --- | --- |
| `[columns]` | Source column names for IDs, phases, groups, assignments, scores, grades, prior use, gender, and major. |
| `[labels]` | Pre/post labels, configured groups, and assignment numbers. |
| `[privacy]` | Public small-cell threshold. The template uses `min_public_cell_count = 5`. |
| `[survey_dimensions]` | Survey composite names and item columns. |
| `[reverse_coded_items]` | Items reversed before composite/reliability calculations. |
| `[likert_mapping]` | Text responses mapped to numeric values. |
| `[grade_mapping]` | Letter grades mapped to grade points. |

The loader rejects unknown sections or fixed-section keys, wrong TOML value types, identical pre/post labels, duplicate groups or assignments, empty groups or assignments, and a suppression threshold below 1. Group and assignment settings must be arrays; mapping values must be numeric where required.

## Expected inventory

`config/expected_inventory.template.toml` contains synthetic counts for pre/post responses, retained participants and survey rows, prompt rows, scored observations, missing scores, and group counts. Pass it to fail fast when a fixture changes unexpectedly:

```bash
--expected-inventory config/expected_inventory.template.toml
```

The file is optional only when `--expected-inventory` is omitted from `analyze-quant`. If the option is supplied, the path must exist and contain valid TOML; observed counts must match the contract. A missing explicit path fails before modeling instead of silently disabling inventory validation. The file is always part of the public smoke path.

Inventory files may contain a partial set of known keys. Unknown keys and values that are not non-negative integers fail before modeling.

## Input names and columns

The quantitative loader searches the input directory for:

```text
survey.csv or survey.xlsx
grades.csv or grades.xlsx
prompts.csv or prompts.xlsx
```

Provide exactly one primary file for each dataset. If both supported formats are present for the same dataset, the loader fails fast instead of choosing one implicitly.

It also accepts `public_cli_input_survey.csv`, `public_cli_input_grades.csv`, and `public_cli_input_prompts.csv` for compatibility with the private cleaning workflow. Required columns are determined by `[columns]`; the public template requires an ID and phase in survey data, an ID/group/midterm/final grade in grade data, and an ID/assignment/prompt score in prompt data.

The legacy aggregate path is less configurable and expects CSV files named `survey.csv`, `grades.csv`, and `prompts.csv` with its older column names.

## Environment variables

No environment variable is required by the public workflow. The figure module selects matplotlib's `Agg` backend in code. The Dockerfile sets `UV_SYSTEM_PYTHON=1` inside the container. `UV_CACHE_DIR` may be set to a writable local cache directory when the default uv cache is unavailable; this is an environment workaround, not a project input.

## Private configuration

These paths are ignored and must remain local:

```text
config/private_quant_config.toml
config/private_expected_inventory.toml
privacy_patterns.local.yml
```

Use private configs only for local author-side data mappings and inventory expectations. Do not copy their contents into tracked docs, tests, or public artifacts.

## Output paths

The public smoke wrapper defaults to ignored `repro_outputs/small/public` and `repro_outputs/small/private`. The direct `analyze-quant` command defaults to `paper_outputs/quantitative` for public artifacts and `private_outputs/quantitative` for local diagnostics; use explicit ignored paths for experiments unless checked-in artifact regeneration is intended.
