# Agent Instructions

## Purpose

This repo is a privacy-preserving reproducibility package for a GenAI literacy prompt-engineering trial. Public code must run on synthetic fixtures and aggregate-only outputs without exposing participant-level research data.

## Core Invariants

- Do not add participant-level survey rows, grades, rosters, prompt transcripts, names, email addresses, institutional identifiers, notebooks, spreadsheets, or private drafts to tracked files.
- Public outputs must remain aggregate-only.
- The small public workflow must not require private data.
- Keep `genai-literacy-trial audit-privacy` passing before release.
- Treat `src/genai_literacy_trial/quant_schema.py`, `quant_figures.py`, and `quant_report.py` constants as public artifact contracts.
- If changing preprocessing, joins, configs, metrics, or artifact contracts, add focused tests with tiny synthetic fixtures.

## Setup And Checks

```bash
uv lock --check
uv sync --locked --dev
uv run ruff check .
uv run ty check .
uv run pytest
uv run python scripts/check_repo_hygiene.py
uv run genai-literacy-trial audit-privacy
```

Main smoke path:

```bash
uv run python scripts/reproduce_small.py
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

The files under `scripts/` are compatibility wrappers around package modules. Prefer keeping reusable logic in `src/genai_literacy_trial/`; module forms such as `uv run python -m genai_literacy_trial.reproduce_small` should stay equivalent to the script wrappers.

Ruff lint and `ty` type checking are configured in `pyproject.toml` and CI.

## Edit Carefully

- Do not casually edit `paper_outputs/` or `paper_outputs/quantitative/`; those are checked-in manuscript-facing aggregate artifacts.
- Do not edit ignored/private paths: `archive/`, `clean_private_data/`, `data/private/`, `private_outputs/`, `config/private_quant_config.toml`, `config/private_expected_inventory.toml`, or `privacy_patterns.local.yml`.
- Prefer writing generated test/smoke outputs under ignored `repro_outputs/`.
- Do not run commands that overwrite checked-in outputs unless the task explicitly asks for regenerated artifacts.
- Keep `data/synthetic/` tiny and non-identifying.

## Style

- Follow existing Python style: typed functions where local code already uses types, pandas DataFrames for tables, deterministic seeds for resampling, and constants for public output names.
- Prefer existing helpers over duplicate parsing or ad hoc joins.
- Keep changes small and scoped. Avoid unrelated refactors.
- Use `uv run ...` commands from the repo root.

## Reporting Uncertainty

- State when a path is documented from code inspection rather than freshly executed.
- Do not claim full-study reproduction works from public clone; private participant-level inputs are unavailable.
- If a command writes into tracked artifacts, say so before running it.

## What Not To Do

- Do not fabricate expected outputs or manuscript statistics.
- Do not silence privacy findings for public artifacts.
- Do not store raw/private data in docs, tests, fixtures, or public outputs.
- Do not change artifact names without updating schema constants, generation code, tests, and docs together.
- Do not rely on line coverage as a reason to add broad tests; prioritize silent scientific/correctness failures.

Longer agent guidance: `docs/agent_playbook.md`, `docs/repo_map.md`, and `docs/common_failure_modes.md`.
