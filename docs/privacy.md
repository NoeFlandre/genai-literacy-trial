# Privacy and Scope

## What is public

The repository publishes:

- source code and tests;
- tiny synthetic survey, grade, and prompt fixtures;
- TOML templates for public configuration and synthetic inventory;
- aggregate-only CSV, figure, and report artifacts;
- the study overview figure and reproducibility documentation.

## What is not public

Do not add participant-level survey rows, individual grades, rosters, prompt transcripts, names, email addresses, institutional identifiers, notebooks, spreadsheets, exported submissions, or private drafts to tracked files.

The full-study input records and author-side cleaning artifacts are unavailable from a clean public clone. A successful synthetic run is not evidence that the study statistics can be reproduced without those inputs.

## Release checks

Scan a public output directory before sharing it:

```bash
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

For a repository release, run the default scan from the repository root:

```bash
uv run genai-literacy-trial audit-privacy
```

The scanner checks common personal-data text patterns, local patterns from the ignored `privacy_patterns.local.yml`, and denied document suffixes. It skips explicitly private/cache directories listed in `src/genai_literacy_trial/privacy.py`.

Generated public quantitative outputs are scanned by `run_quant_analysis()` before the command returns. The separate CLI scan is still required for the final tree or selected publication directory.

## Aggregate suppression

`config/quant_config.template.toml` sets `privacy.min_public_cell_count = 5`. Small categorical cells are suppressed in public aggregate tables. This is a project contract, not a substitute for reviewing generated files and local data paths.
