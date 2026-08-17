from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from genai_literacy_trial.paths import (
    DATA_SYNTHETIC_DIR,
    EXPECTED_INVENTORY_TEMPLATE,
    QUANT_CONFIG_TEMPLATE,
    REPO_ROOT,
    REPRO_SMALL_PUBLIC_DIR,
)
from genai_literacy_trial.quant_figures import FIGURE_FORMATS, FIGURE_STEMS
from genai_literacy_trial.quant_report import QUANTITATIVE_REPORT_FILENAME
from genai_literacy_trial.quant_schema import QUANT_TABLE_OUTPUT_FORMAT, REQUIRED_QUANT_TABLES


SMALL_INPUT_FILES = ("survey.csv", "grades.csv", "prompts.csv")
SMALL_REQUIRED_OUTPUTS = (
    QUANTITATIVE_REPORT_FILENAME,
    *(f"{name}.{QUANT_TABLE_OUTPUT_FORMAT}" for name in REQUIRED_QUANT_TABLES),
    *(f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in FIGURE_FORMATS),
)


@dataclass(frozen=True)
class ValidationIssue:
    status: str
    path: Path
    detail: str


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _small_sources(input_dir: Path, config: Path, expected_inventory: Path | None) -> tuple[Path, ...]:
    sources = [input_dir / name for name in SMALL_INPUT_FILES]
    sources.append(config)
    if expected_inventory is not None:
        sources.append(expected_inventory)
    return tuple(sources)


def _required_outputs(mode: str) -> tuple[str, ...]:
    if mode != "small":
        raise ValueError(f"Unsupported validation mode: {mode}")
    return SMALL_REQUIRED_OUTPUTS


def _validate_source_files(paths: Sequence[Path]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for path in paths:
        if not path.exists():
            issues.append(ValidationIssue("missing_source", path, "required source file is missing"))
        elif path.is_file() and path.stat().st_size == 0:
            issues.append(ValidationIssue("empty_source", path, "required source file is empty"))
    return issues


def _validate_csv(path: Path) -> ValidationIssue | None:
    try:
        table = pd.read_csv(path, nrows=1)
    except pd.errors.EmptyDataError:
        return ValidationIssue("empty", path, "CSV has no header row")
    except Exception as exc:
        return ValidationIssue("invalid_csv", path, f"CSV could not be read: {exc}")
    if len(table.columns) == 0:
        return ValidationIssue("invalid_csv", path, "CSV has no columns")
    return None


def validate_artifacts(
    *,
    mode: str,
    input_dir: Path,
    config: Path,
    expected_inventory: Path | None,
    public_output_dir: Path,
    allow_stale: bool = False,
) -> list[ValidationIssue]:
    sources = _small_sources(input_dir, config, expected_inventory)
    issues = _validate_source_files(sources)
    source_files = [path for path in sources if path.exists() and path.is_file()]
    newest_source_mtime = max((path.stat().st_mtime for path in source_files), default=None)

    for relative_name in _required_outputs(mode):
        path = public_output_dir / relative_name
        if not path.exists():
            issues.append(ValidationIssue("missing", path, "required output artifact is missing"))
            continue
        if not path.is_file():
            issues.append(ValidationIssue("not_file", path, "required output path is not a file"))
            continue
        if path.stat().st_size == 0:
            issues.append(ValidationIssue("empty", path, "required output artifact is empty"))
            continue
        if path.suffix.lower() == ".csv":
            csv_issue = _validate_csv(path)
            if csv_issue is not None:
                issues.append(csv_issue)
                continue
        if newest_source_mtime is not None and path.stat().st_mtime < newest_source_mtime and not allow_stale:
            issues.append(ValidationIssue("stale", path, "output is older than at least one input/config file"))
    return issues


def print_validation_report(issues: Sequence[ValidationIssue]) -> None:
    if not issues:
        print("Artifact validation passed.")
        return
    print("Artifact validation failed:")
    for issue in issues:
        print(f"{issue.status}: {_display_path(issue.path)} - {issue.detail}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate reproducibility artifacts for the public workflow.")
    parser.add_argument("--mode", choices=("small",), default="small", help="Artifact contract to validate.")
    parser.add_argument("--input-dir", type=Path, default=DATA_SYNTHETIC_DIR, help="Directory containing synthetic survey, grades, and prompts CSV files.")
    parser.add_argument("--config", type=Path, default=QUANT_CONFIG_TEMPLATE, help="Quantitative TOML configuration used to generate outputs.")
    parser.add_argument("--expected-inventory", type=Path, default=EXPECTED_INVENTORY_TEMPLATE, help="Expected inventory TOML used by the synthetic smoke run.")
    parser.add_argument("--public-output-dir", type=Path, default=REPRO_SMALL_PUBLIC_DIR, help="Directory containing generated public quantitative artifacts.")
    parser.add_argument("--allow-stale", action="store_true", help="Report success even when outputs are older than inputs/config.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    issues = validate_artifacts(
        mode=args.mode,
        input_dir=args.input_dir,
        config=args.config,
        expected_inventory=args.expected_inventory,
        public_output_dir=args.public_output_dir,
        allow_stale=args.allow_stale,
    )
    print_validation_report(issues)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
