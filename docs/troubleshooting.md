# Troubleshooting

## uv or import failures

Run from the repository root:

```bash
uv sync --locked --dev
uv run python scripts/reproduce_small.py
```

If the default uv cache is not writable, set a temporary cache location:

```bash
UV_CACHE_DIR=/tmp/genai-literacy-uv-cache uv sync --locked --dev
```

## Missing or empty inputs

Check `--input-dir` and the expected names in [Configuration](configuration.md). The quantitative path fails if survey, grades, or prompts are empty or missing required configured columns.

## Malformed values or duplicate rows

The quantitative path fails before modeling for nonnumeric/nonfinite assignment or prompt-score values, noninteger assignments, conflicting duplicate grade rows, duplicate participant/assignment prompt rows, invalid groups or assignments, and unmapped prior-use categories. Fix the source or TOML mapping; do not silently drop the rows.

## Inventory mismatch

When `--expected-inventory` is supplied, observed counts must match the TOML contract. Confirm the retention criteria and source extraction before changing the expected file. Private expected inventories must remain ignored.

If the command reports `Expected inventory file not found`, check the path passed to `--expected-inventory`. Omit the option only when inventory validation is intentionally not required.

## Stale artifacts

Run:

```bash
uv run python scripts/validate_artifacts.py --mode small --public-output-dir repro_outputs/small/public
```

Rerun the pipeline when `stale` is reported. Freshness uses modification times, not content hashes.

## Privacy failures

Scan the exact tree being published:

```bash
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

Inspect every finding. Do not bypass the scanner or commit the ignored local pattern file. The scanner rejects common personal-data patterns and denied suffixes such as `.xlsx`, `.docx`, `.ipynb`, and `.pptx` in public trees.

## Small-data model warnings

The six-participant fixture can produce statsmodels and NumPy convergence or divide-by-zero warnings. The smoke wrapper hides them by default; show them for diagnosis:

```bash
uv run python scripts/reproduce_small.py --show-model-warnings
```

Warnings do not make synthetic output equivalent to study results.

## Checked-in output changes

The direct quantitative command defaults to `paper_outputs/quantitative`; the smoke wrapper defaults to ignored `repro_outputs/small/`. Use explicit ignored output paths during development. If checked-in outputs change intentionally, review the diff, run privacy/hygiene checks, and update the artifact documentation.

## Documentation build failures

Build with strict mode to see the exact broken link or navigation item:

```bash
uv run mkdocs build --strict --site-dir /tmp/genai-literacy-trial-site
```

The public site excludes the internal agent pages. Keep public navigation in `mkdocs.yml` and internal guidance in `AGENTS.md` or the excluded docs.
