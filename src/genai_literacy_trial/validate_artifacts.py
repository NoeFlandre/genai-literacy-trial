from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, cast

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
from genai_literacy_trial.quant_schema import (
    QUANT_TABLE_OUTPUT_FORMAT,
    REQUIRED_QUANT_TABLE_COLUMNS,
    REQUIRED_QUANT_TABLES,
)


SMALL_INPUT_FILES = ("survey.csv", "grades.csv", "prompts.csv")
SMALL_REQUIRED_OUTPUTS = (
    QUANTITATIVE_REPORT_FILENAME,
    *(f"{name}.{QUANT_TABLE_OUTPUT_FORMAT}" for name in REQUIRED_QUANT_TABLES),
    *(f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in FIGURE_FORMATS),
)
MANIFEST_VERSION = 1


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
        elif not path.is_file():
            issues.append(ValidationIssue("not_file", path, "required source path is not a file"))
        elif path.stat().st_size == 0:
            issues.append(ValidationIssue("empty_source", path, "required source file is empty"))
    return issues


def _validate_csv(path: Path, required_columns: Sequence[str]) -> ValidationIssue | None:
    try:
        table = pd.read_csv(path, nrows=1)
    except pd.errors.EmptyDataError:
        return ValidationIssue("empty", path, "CSV has no header row")
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        return ValidationIssue("invalid_csv", path, f"CSV could not be read: {exc}")
    if len(table.columns) == 0:
        return ValidationIssue("invalid_csv", path, "CSV has no columns")
    missing_columns = [column for column in required_columns if column not in table.columns]
    if missing_columns:
        return ValidationIssue("invalid_schema", path, f"CSV is missing required columns: {', '.join(missing_columns)}")
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_entries(paths: Sequence[Path]) -> dict[str, str]:
    return {_display_path(path): _sha256(path) for path in paths}


def write_manifest(
    *,
    path: Path,
    mode: str,
    input_dir: Path,
    config: Path,
    expected_inventory: Path | None,
    public_output_dir: Path,
) -> None:
    sources = _small_sources(input_dir, config, expected_inventory)
    outputs = [public_output_dir / name for name in _required_outputs(mode)]
    missing = [candidate for candidate in [*sources, *outputs] if not candidate.is_file()]
    if missing:
        names = ", ".join(_display_path(candidate) for candidate in missing)
        raise FileNotFoundError(f"Cannot write manifest; required files are missing: {names}")
    payload = {
        "version": MANIFEST_VERSION,
        "sources": _manifest_entries(sources),
        "outputs": _manifest_entries(outputs),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _validate_manifest(path: Path, sources: Sequence[Path], outputs: Sequence[Path]) -> list[ValidationIssue]:
    if not path.exists():
        return [ValidationIssue("manifest_missing", path, "manifest file is missing")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [ValidationIssue("invalid_manifest", path, f"manifest could not be read: {exc}")]
    if not isinstance(payload, dict) or payload.get("version") != MANIFEST_VERSION:
        return [ValidationIssue("invalid_manifest", path, f"manifest version must be {MANIFEST_VERSION}")]

    issues: list[ValidationIssue] = []
    for section, current_paths in (("sources", sources), ("outputs", outputs)):
        recorded_value = payload.get(section)
        if not isinstance(recorded_value, dict):
            issues.append(ValidationIssue("invalid_manifest", path, f"manifest {section} must be an object"))
            continue
        recorded = cast(dict[str, object], recorded_value)
        expected_keys = {_display_path(candidate) for candidate in current_paths}
        missing_keys = sorted(expected_keys - set(recorded))
        extra_keys = sorted(set(recorded) - expected_keys)
        if missing_keys or extra_keys:
            details = []
            if missing_keys:
                details.append(f"missing entries: {', '.join(missing_keys)}")
            if extra_keys:
                details.append(f"unexpected entries: {', '.join(extra_keys)}")
            issues.append(ValidationIssue("invalid_manifest", path, f"manifest {section} contract mismatch ({'; '.join(details)})"))
            continue
        for current_path in current_paths:
            if not current_path.is_file():
                continue
            key = _display_path(current_path)
            expected_hash = recorded[key]
            if not _is_sha256(expected_hash):
                issues.append(ValidationIssue("invalid_manifest", path, f"manifest hash for {key} is not a SHA-256 digest"))
            elif _sha256(current_path) != expected_hash:
                issues.append(ValidationIssue("content_changed", current_path, "file content differs from manifest"))
    return issues


def validate_artifacts(
    *,
    mode: str,
    input_dir: Path,
    config: Path,
    expected_inventory: Path | None,
    public_output_dir: Path,
    allow_stale: bool = False,
    manifest_path: Path | None = None,
) -> list[ValidationIssue]:
    sources = _small_sources(input_dir, config, expected_inventory)
    issues = _validate_source_files(sources)
    source_files = [path for path in sources if path.exists() and path.is_file()]
    newest_source_mtime = max((path.stat().st_mtime for path in source_files), default=None)

    output_paths = [public_output_dir / relative_name for relative_name in _required_outputs(mode)]
    for path in output_paths:
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
            csv_issue = _validate_csv(path, REQUIRED_QUANT_TABLE_COLUMNS[path.stem])
            if csv_issue is not None:
                issues.append(csv_issue)
                continue
        if newest_source_mtime is not None and path.stat().st_mtime < newest_source_mtime and not allow_stale:
            issues.append(ValidationIssue("stale", path, "output is older than at least one input/config file"))
    if manifest_path is not None:
        issues.extend(_validate_manifest(manifest_path, sources, output_paths))
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
    parser.add_argument("--manifest", type=Path, default=None, help="Optional SHA-256 manifest to validate alongside artifacts.")
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
        manifest_path=args.manifest,
    )
    print_validation_report(issues)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
