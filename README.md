# GenAI Literacy Trial

![Study Overview](docs/figures/study_overview.png)

Public, privacy-preserving analysis package for a three-arm prompt-engineering training trial in an engineering algorithms course.

The repository contains Python analysis code, synthetic fixtures, aggregate-only public outputs, reproducibility scripts, and privacy checks. Participant-level research records are intentionally not distributed.

## Repository Layout

```text
src/genai_literacy_trial/  Python package for preprocessing, models, reports, CLI, and privacy checks
data/synthetic/           tiny public survey/grades/prompts fixtures
config/                   public TOML config and expected synthetic inventory
paper_outputs/            checked-in aggregate-only manuscript-facing outputs
paper_outputs/quantitative/ checked-in quantitative tables, figures, and report
scripts/                  public smoke reproduction and artifact validator scripts
tests/                    unit and CLI tests using synthetic fixtures
docs/                     developer/research documentation and static study figure
```

Ignored local/private paths include `archive/`, `clean_private_data/`, `data/private/`, `private_outputs/`, `repro_outputs/`, `config/private_quant_config.toml`, `config/private_expected_inventory.toml`, and `privacy_patterns.local.yml`.

## Setup

The project uses `uv` and requires Python 3.11 or newer. CI currently runs Python 3.12.

```bash
uv sync --dev
```

No environment variables are required for the public smoke workflow.

## Main Public Smoke Workflow

Run the no-private-data quantitative workflow:

```bash
uv run python scripts/reproduce_small.py
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

The `scripts/` files are thin compatibility wrappers. The same smoke helpers are also available as installed commands after `uv sync --dev`:

```bash
uv run genai-literacy-reproduce-small
uv run genai-literacy-validate-artifacts --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-check-repo-hygiene
```

This reads:

```text
data/synthetic/survey.csv
data/synthetic/grades.csv
data/synthetic/prompts.csv
config/quant_config.template.toml
config/expected_inventory.template.toml
```

and writes ignored local outputs under:

```text
repro_outputs/small/public/
repro_outputs/small/private/
```

## Other Workflows

Full quantitative pipeline command shape:

```bash
uv run genai-literacy-trial analyze-quant \
  --input-dir data/synthetic \
  --config config/quant_config.template.toml \
  --expected-inventory config/expected_inventory.template.toml \
  --output-dir repro_outputs/small/private \
  --public-output-dir repro_outputs/small/public
```

Legacy aggregate-paper workflow:

```bash
uv run genai-literacy-trial reproduce-paper
```

The full study workflow requires private participant-level survey, grade, and prompt inputs that are not present in this public repository.

## Tests And Checks

```bash
uv lock --check
uv sync --locked --dev
uv run ruff check .
uv run ty check .
uv run pytest
uv run python scripts/reproduce_small.py
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
uv run python scripts/check_repo_hygiene.py
uv run genai-literacy-trial audit-privacy
```

CI runs the same commands on Python 3.12, including the `ty` type check.

## Documentation

- [Architecture](docs/architecture.md)
- [Data flow](docs/data_flow.md)
- [Diagrams](docs/diagrams.md)
- [CLI and scripts](docs/cli.md)
- [Artifacts](docs/artifacts.md)
- [Configuration](docs/configuration.md)
- [Reproducibility](docs/reproducibility.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Agent playbook](docs/agent_playbook.md)
- [Agent repo map](docs/repo_map.md)
- [Common failure modes](docs/common_failure_modes.md)

## Privacy Policy

Do not commit row-level survey responses, individual grades, rosters, raw prompt transcripts, names, email addresses, institutional identifiers, notebooks, spreadsheets, exported submissions, or private draft documents.

Every public release should pass:

```bash
uv run genai-literacy-trial audit-privacy
```

The ignored `privacy_patterns.local.yml` file may add project-specific private patterns for local release review.
