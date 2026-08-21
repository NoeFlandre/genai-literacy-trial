# Development

## Environment

The project uses `uv`, requires Python 3.11 or newer, and runs CI on Python 3.12. Install the locked development environment from the repository root:

```bash
uv lock --check
uv sync --locked --dev
```

The development group includes pytest, coverage, Ruff, `ty`, MkDocs Material, mutmut, and Radon.

## Quality gates

Run the deterministic completion gate used by CI from the repository root:

```bash
uv lock --check
uv sync --locked --dev
uv run --locked --no-sync python scripts/qa_gauntlet.py
```

The runner is fail-fast and executes these stages in this exact order:

1. Baseline: locked dependency resolution and installation.
2. Ruff lint.
3. `ty` type checking.
4. Full tests with fresh coverage data.
5. Focused acceptance tests for high-risk contracts, reproducibility, and artifacts.
6. Architecture checks for package boundaries, CLI imports, docs wiring, and a strict MkDocs build.
7. CRAP calculation over `src/` and `scripts/`.
8. Mutation tests through `scripts/run_mutation_gate.py`.
9. Synthetic smoke reproduction, artifact validation, public privacy scan, and repository hygiene.
10. Diff review with `git diff --check HEAD`, diff summary, and worktree status.

The runner writes only temporary coverage, Radon, and documentation files under `/tmp`; smoke outputs remain under ignored `repro_outputs/`. It does not run the repository-wide privacy audit because that audit is a separate release check and may include local/private paths.

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

The default gate must report zero surviving, untested, or timed-out mutants. Equivalent mutations are excluded explicitly in `[tool.mutmut]`; those exclusions are limited to ordering flags, runtime-only casts, temporary-directory naming/location defaults, and explicit numeric casts.

The CRAP gate is strict: every measured function in `src/` and `scripts/` must score **below 6**. The command fails at exactly 6.0, not only above it:

```bash
uv run python -m coverage run --source=src,scripts -m pytest
uv run python -m coverage json -o /tmp/genai-literacy-trial-coverage.json
uv run radon cc src scripts -j > /tmp/genai-literacy-trial-cc.json
uv run python scripts/check_crap.py --coverage-json /tmp/genai-literacy-trial-coverage.json --radon-json /tmp/genai-literacy-trial-cc.json
```

CRAP is calculated per function as `complexity² × (1 - coverage)³ + complexity`. Keep the maximum below 6; add focused tests or split a complex function when the gate fails.

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
