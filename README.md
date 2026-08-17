# GenAI Literacy Trial

Public, privacy-preserving analysis code for a three-arm prompt-engineering training trial in an engineering algorithms course.

The repository contains the Python package, synthetic fixtures, TOML templates, aggregate-only outputs, tests, reproducibility scripts, and privacy checks. Participant-level survey responses, grades, rosters, prompt transcripts, and private cleaning files are not distributed.

## Quick start

Install the locked development environment with [uv](https://docs.astral.sh/uv/):

```bash
uv sync --locked --dev
```

Run the public smoke workflow:

```bash
uv run python scripts/reproduce_small.py
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

Build the documentation locally:

```bash
uv run mkdocs serve
```

## Repository map

```text
src/genai_literacy_trial/  package, CLI, preprocessing, models, reports, privacy checks
data/synthetic/            tiny public survey, grade, and prompt fixtures
config/                    public quantitative config and expected inventory templates
paper_outputs/             checked-in aggregate-only manuscript-facing outputs
scripts/                   compatibility wrappers for the public smoke and validation commands
tests/                     focused unit, CLI, artifact, privacy, and documentation tests
docs/                      MkDocs source and internal agent guidance
```

## Main commands

```bash
uv run genai-literacy-trial --help
uv run genai-literacy-trial analyze-quant
uv run genai-literacy-trial reproduce-paper
uv run genai-literacy-trial audit-privacy
```

The `analyze-quant` command is the primary quantitative workflow. `reproduce-paper`, `build-aggregates`, and `validate-paper` are legacy aggregate-table commands retained for compatibility.

## Checks

```bash
uv lock --check
uv sync --locked --dev
uv run ruff check .
uv run ty check .
uv run mkdocs build --strict --site-dir /tmp/genai-literacy-trial-site
uv run pytest
uv run python scripts/check_repo_hygiene.py
uv run genai-literacy-trial audit-privacy
```

## Documentation

Start with the [documentation source](docs/index.md), [reproducibility guide](docs/reproducibility.md), and [architecture](docs/architecture.md). The site configuration is `mkdocs.yml`; CI builds it with strict link and navigation checks.

## Data policy

Only synthetic inputs and aggregate outputs belong in the public tree. Do not commit participant-level rows, personal identifiers, raw exports, notebooks, spreadsheets, or private drafts. See [Privacy and Scope](docs/privacy.md).
