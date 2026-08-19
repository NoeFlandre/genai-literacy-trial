# Development

## Environment

The project uses `uv`, requires Python 3.11 or newer, and runs CI on Python 3.12. Install the locked development environment from the repository root:

```bash
uv lock --check
uv sync --locked --dev
```

The development group includes pytest, coverage, Ruff, `ty`, MkDocs Material, mutmut, and Radon.

## Quality gates

Run the same checks used by the main CI job:

```bash
uv run ruff check .
uv run ty check .
uv run python -m coverage run --source=src -m pytest
uv run python -m coverage json -o /tmp/genai-literacy-trial-coverage.json
uv run radon cc src/genai_literacy_trial -j > /tmp/genai-literacy-trial-cc.json
uv run python scripts/check_crap.py --coverage-json /tmp/genai-literacy-trial-coverage.json --radon-json /tmp/genai-literacy-trial-cc.json
uv run mkdocs build --strict --site-dir /tmp/genai-literacy-trial-site
uv run python scripts/reproduce_small.py
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
uv run python scripts/check_repo_hygiene.py
```

The repository-wide privacy command is part of the release gate:

```bash
uv run genai-literacy-trial audit-privacy
```

An ignored `privacy_patterns.local.yml` may add local release-review patterns. Do not commit that file or use it to suppress a finding.

## Tests

Tests are in `tests/`. The highest-risk coverage is concentrated in:

- `test_quant_preprocess.py`: retention, joins, duplicate rows, mappings, and input validation.
- `test_quant_models.py` and `test_quant_stats.py`: metrics, model tables, confidence intervals, and edge cases.
- `test_quant_cli.py` and `test_reproducibility_scripts.py`: command behavior and generated artifact contracts.
- `test_privacy.py`, `test_repo_hygiene.py`, and `test_docs.py`: release safety and documentation wiring.

Use a focused test while editing, then run the full suite before handoff:

```bash
uv run pytest tests/test_quant_preprocess.py -q
uv run pytest
```

## Mutation and CRAP checks

The focused mutation gate covers input resolution and validation, privacy cell suppression, Welch ANOVA edge handling, and artifact manifest validation. Run it from the repository root:

```bash
uv run python scripts/run_mutation_gate.py
```

The default gate must report zero surviving, untested, or timed-out mutants. Equivalent mutations are excluded explicitly in `[tool.mutmut]`; those exclusions are limited to ordering flags, runtime-only casts, and explicit numeric casts.

The CRAP gate is strict: every measured source function must score **below 6**. The command fails at exactly 6.0, not only above it:

```bash
uv run python -m coverage run --source=src -m pytest
uv run python -m coverage json -o /tmp/genai-literacy-trial-coverage.json
uv run radon cc src/genai_literacy_trial -j > /tmp/genai-literacy-trial-cc.json
uv run python scripts/check_crap.py --coverage-json /tmp/genai-literacy-trial-coverage.json --radon-json /tmp/genai-literacy-trial-cc.json
```

CRAP is calculated per function as `complexity² × (1 - coverage)³ + complexity`. The current full-source measurement has a maximum score of 5.27. Keep the maximum below 6; add focused tests or split a complex function when the gate fails.

## Safe changes

- Keep `data/synthetic/` small and non-identifying.
- Put generated local outputs in ignored `repro_outputs/`.
- Treat constants in `quant_schema.py`, `quant_figures.py`, and `quant_report.py` as public contracts.
- If preprocessing, joins, configurations, metrics, or artifact names change, add a tiny focused regression test and update the relevant docs.
- Do not overwrite checked-in `paper_outputs/` unless regeneration is explicitly intended and reviewed.

## Documentation

The public site is configured in `mkdocs.yml`. Build it strictly before changing the navigation or links:

```bash
uv run mkdocs build --strict --site-dir /tmp/genai-literacy-trial-site
```

Internal agent guidance remains in `AGENTS.md`, `docs/agent_playbook.md`, `docs/repo_map.md`, and `docs/common_failure_modes.md`; those pages are deliberately excluded from the public site navigation.
