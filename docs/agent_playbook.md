# Agent Playbook

This guide is for future coding-agent sessions. It assumes the agent starts from a potentially dirty worktree and needs to make safe, small changes.

## First Five Minutes

1. Check worktree state:

   ```bash
   git status --short
   ```

2. Read the short instructions:

   ```text
   AGENTS.md
   README.md
   ```

3. For code changes, inspect the relevant module and nearby tests before editing.

4. Prefer existing tiny fixtures:

   ```text
   data/synthetic/
   tests/quant_fixtures.py
   ```

5. Choose the smallest verification command that covers your change, then run the full check if the change touches workflow behavior, privacy, artifacts, or public docs.

## Safe Change Pattern

For preprocessing, stats, model, CLI, or artifact-contract changes:

1. Add or update a focused test in the closest existing test file.
2. Use a tiny DataFrame fixture or `tests/quant_fixtures.py`.
3. Implement the smallest code/doc change needed.
4. Run the touched test file.
5. Run broader checks when the change can affect generated outputs or privacy.

Good focused targets in this repo:

- Config alias handling.
- Retained participant filters.
- Joins between survey, grades, and prompts.
- Expected inventory mismatches.
- Prompt transcript column removal.
- Public artifact names and generated suffix cleanup.
- Metric formulas and deterministic bootstrap behavior.
- Privacy scanner findings.

## Commands

Install dependencies:

```bash
uv sync --dev
```

Run the CI-equivalent dependency setup:

```bash
uv lock --check
uv sync --locked --dev
```

Run Ruff lint:

```bash
uv run ruff check .
uv run ty check .
```

Build the public documentation:

```bash
uv run mkdocs build --strict --site-dir /tmp/genai-literacy-trial-site
```

Run tests:

```bash
uv run pytest
```

Run a targeted test file:

```bash
uv run pytest tests/test_quant_preprocess.py -q
```

Run privacy audit:

```bash
uv run genai-literacy-trial audit-privacy
```

Run repository hygiene checks:

```bash
uv run python scripts/check_repo_hygiene.py
```

Run public smoke workflow:

```bash
uv run python scripts/reproduce_small.py
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

The `scripts/` commands are wrappers around package modules. When changing smoke or hygiene behavior, edit `src/genai_literacy_trial/` and keep `python -m genai_literacy_trial.reproduce_small`, `python -m genai_literacy_trial.validate_artifacts`, and `python -m genai_literacy_trial.repo_hygiene` working.

Ruff lint, `ty` type checking, and the strict MkDocs build are configured. Keep all three checks passing when changing typed interfaces, pandas transformations, public docs, or navigation.

## Working With Artifacts

Use `repro_outputs/` for local generated outputs. It is ignored by git.

Avoid changing checked-in `paper_outputs/` unless the task explicitly asks to update public manuscript-facing artifacts. If you must regenerate checked-in outputs, state the command, expected paths, and privacy implications.

`analyze-quant` cleans top-level generated-style files in the public output directory before writing. Generated suffixes are `.csv`, `.pdf`, `.png`, and `.md`. Nested files and other suffixes are preserved.

`scripts/validate_artifacts.py` checks required small-run outputs and mtime staleness. With `--manifest`, it also validates SHA-256 hashes for configured sources and generated public outputs.

## Working With Private Data Assumptions

The public clone cannot fully reproduce the private study outputs. Private paths are ignored and should remain local:

```text
archive/
clean_private_data/
data/private/
private_outputs/
config/private_quant_config.toml
config/private_expected_inventory.toml
privacy_patterns.local.yml
```

Do not infer real participant values from private-path names, ignored files, or local-only patterns. Do not paste private names or examples into tracked docs/tests.

## Documentation Changes

Keep documentation concrete:

- Prefer actual paths, commands, module names, and artifact names.
- Mark inspected-but-unrun commands explicitly.
- Keep `AGENTS.md` concise; put explanations here or in `docs/repo_map.md`.
- After doc changes, run the privacy audit because docs are scanned text files.

## Reporting

Final reports should distinguish:

- commands actually run,
- behavior documented from code inspection,
- commands not run because they would overwrite tracked artifacts or require private data,
- remaining uncertainty or repo ambiguity.
