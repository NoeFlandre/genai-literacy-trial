# GenAI Literacy Trial

This repository is the public, privacy-preserving analysis package for a three-arm prompt-engineering training trial in an engineering algorithms course.

![Study overview](figures/study_overview.png)

The public checkout contains the analysis code, tiny synthetic fixtures, configuration templates, aggregate-only outputs, tests, and release checks. Participant-level survey responses, grades, rosters, prompt transcripts, and private cleaning files are intentionally excluded.

## Start here

Run the complete public smoke path from the repository root:

```bash
uv sync --locked --dev
uv run python scripts/reproduce_small.py
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

The run uses `data/synthetic/` and writes ignored outputs under `repro_outputs/small/`. It exercises preprocessing, inventory checks, statistical models, figures, the generated report, artifact validation, and the public-output privacy scan.

## Read next

- [Reproducibility](reproducibility.md) explains the public smoke path and the unavailable full-study boundary.
- [Architecture](architecture.md) maps the package modules and workflow boundaries.
- [Data flow](data_flow.md) describes inputs, retention, analysis tables, and outputs.
- [CLI reference](cli.md) lists the installed commands and compatibility scripts.
- [Artifacts](artifacts.md) records the public output contract.
- [Configuration](configuration.md) documents TOML sections and accepted inputs.
- [Development](development.md) lists the local checks used by CI.
- [Privacy and scope](privacy.md) defines what may be published.
- [Troubleshooting](troubleshooting.md) covers common failures.

## Research boundary

The synthetic workflow proves that the public code path runs. It does not reproduce study statistics: the participant-level source data and private configuration required for the full study are not in this repository.
