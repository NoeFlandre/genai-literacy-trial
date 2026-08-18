# Reproducibility

## Public path

The smallest meaningful workflow is the synthetic quantitative run. It uses six synthetic participants and exercises input loading, TOML configuration, retention and joins, inventory validation, statistical tables, figures, report generation, stale-output validation, and the generated-output privacy scan.

It does not reproduce study statistics. The participant-level source records and private configuration required for the full study are not in this repository.

## Clean setup

```bash
git clone https://github.com/NoeFlandre/genai-literacy-trial.git
cd genai-literacy-trial
uv sync --locked --dev
```

Python 3.11 or newer is required. CI uses Python 3.12. No environment variable is required for the public path.

## Required public inputs

```text
data/synthetic/survey.csv
data/synthetic/grades.csv
data/synthetic/prompts.csv
config/quant_config.template.toml
config/expected_inventory.template.toml
```

The quantitative loader also accepts `.xlsx` inputs and compatibility names such as `public_cli_input_survey.csv`; the public fixture uses the CSV names above. The legacy aggregate workflow accepts only `survey.csv`, `grades.csv`, and `prompts.csv`.

## Tiny smoke run

```bash
uv run python scripts/reproduce_small.py
```

The default output locations are ignored by git:

```text
repro_outputs/small/public/
repro_outputs/small/private/
```

To isolate outputs elsewhere:

```bash
uv run python scripts/reproduce_small.py \
  --public-output-dir /tmp/genai-literacy-public \
  --output-dir /tmp/genai-literacy-private
```

Use `--show-model-warnings` when diagnosing the expected small-sample statsmodels and NumPy warnings.

## Full quantitative command

The public equivalent is:

```bash
uv run genai-literacy-trial analyze-quant \
  --input-dir data/synthetic \
  --config config/quant_config.template.toml \
  --expected-inventory config/expected_inventory.template.toml \
  --output-dir repro_outputs/small/private \
  --public-output-dir repro_outputs/small/public
```

For an author-side full study run, replace the input and ignored private configuration paths with local analysis-ready files. Do not place those files or participant-level outputs in tracked directories.

## Validate outputs

```bash
uv run python scripts/validate_artifacts.py \
  --mode small \
  --public-output-dir repro_outputs/small/public
uv run genai-literacy-trial audit-privacy --root repro_outputs/small/public
```

The validator checks required sources, required outputs, non-empty files, CSV readability, and output modification times. The privacy command checks the selected publication tree.

## Stale outputs

Staleness is currently determined by file modification times: an output is stale when it is older than the newest relevant input or configuration file. There is no content hash or run manifest. The test suite checks byte-for-byte determinism for the generated CSV tables and Markdown report; PDF figure binaries may differ between runs because of renderer metadata. Rerun the smoke or quantitative command when `validate_artifacts.py` reports `stale`. `--allow-stale` is for inspection only.

## Legacy path

The retained aggregate-only path is:

```bash
uv run genai-literacy-trial reproduce-paper
```

It uses `src/genai_literacy_trial/analysis.py`, writes top-level aggregate CSVs to `paper_outputs/` by default, and produces a target validation report. It is not the primary quantitative workflow and should not be used as evidence of full-study reproduction.

## Runtime and limits

The synthetic workflow is designed to be a small local job. The repository has no benchmarked runtime or memory requirement. Full-study requirements cannot be estimated reliably from the public checkout because the source data and private cleaning steps are unavailable.

The synthetic data are fixtures, so target mismatches in manuscript validation are expected. Exact author-side reproduction remains conditional on unavailable participant-level inputs, private configuration, and private extraction criteria.
