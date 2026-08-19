from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from genai_literacy_trial import validate_artifacts


def _write_valid_manifest_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source.csv"
    output = tmp_path / "output.csv"
    manifest = tmp_path / "manifest.json"
    source.write_text("participant_id\n1\n", encoding="utf-8")
    output.write_text("result\n1\n", encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    manifest.write_text(
        json.dumps(
            {
                "version": validate_artifacts.MANIFEST_VERSION,
                "sources": {str(source): digest(source)},
                "outputs": {str(output): digest(output)},
            }
        ),
        encoding="utf-8",
    )
    return manifest, source, output


def _write_validation_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    input_dir = tmp_path / "input"
    public_output_dir = tmp_path / "public"
    input_dir.mkdir()
    public_output_dir.mkdir()
    for name in validate_artifacts.SMALL_INPUT_FILES:
        (input_dir / name).write_text("value\n1\n", encoding="utf-8")
    config = tmp_path / "quant_config.toml"
    expected_inventory = tmp_path / "expected_inventory.toml"
    config.write_text("[columns]\n", encoding="utf-8")
    expected_inventory.write_text("pre_responses = 1\n", encoding="utf-8")
    return input_dir, config, expected_inventory, public_output_dir, public_output_dir / "report.md"


def test_validate_artifacts_accepts_valid_public_outputs_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir, config, expected_inventory, public_output_dir, output = _write_validation_fixture(tmp_path)
    output.write_text("# report\n", encoding="utf-8")
    monkeypatch.setattr(validate_artifacts, "_required_outputs", lambda _mode: ("report.md",))
    manifest = tmp_path / "manifest.json"
    validate_artifacts.write_manifest(
        path=manifest,
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
    )

    issues = validate_artifacts.validate_artifacts(
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
        manifest_path=manifest,
    )

    assert issues == []


def test_validate_artifacts_reports_stale_public_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir, config, expected_inventory, public_output_dir, output = _write_validation_fixture(tmp_path)
    output.write_text("# old report\n", encoding="utf-8")
    os.utime(output, ns=(1, 1))
    monkeypatch.setattr(validate_artifacts, "_required_outputs", lambda _mode: ("report.md",))

    issues = validate_artifacts.validate_artifacts(
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
    )

    assert [(issue.status, issue.path) for issue in issues] == [("stale", output)]


@pytest.mark.parametrize(
    ("state", "expected_status"),
    [("missing", "missing"), ("directory", "not_file"), ("empty", "empty")],
)
def test_validate_artifacts_reports_missing_nonfile_and_empty_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    expected_status: str,
) -> None:
    input_dir, config, expected_inventory, public_output_dir, output = _write_validation_fixture(tmp_path)
    if state == "directory":
        output.mkdir()
    elif state == "empty":
        output.write_text("", encoding="utf-8")
    monkeypatch.setattr(validate_artifacts, "_required_outputs", lambda _mode: ("report.md",))

    issues = validate_artifacts.validate_artifacts(
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
    )

    assert [(issue.status, issue.path) for issue in issues] == [(expected_status, output)]
    expected_detail = {
        "missing": "required output artifact is missing",
        "not_file": "required output path is not a file",
        "empty": "required output artifact is empty",
    }[expected_status]
    assert issues[0].detail == expected_detail


def test_validate_artifacts_reports_invalid_csv_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir, config, expected_inventory, public_output_dir, _ = _write_validation_fixture(tmp_path)
    table_stem = next(iter(validate_artifacts.REQUIRED_QUANT_TABLE_COLUMNS))
    output = public_output_dir / f"{table_stem}.csv"
    output.write_text("wrong_column\n1\n", encoding="utf-8")
    monkeypatch.setattr(validate_artifacts, "_required_outputs", lambda _mode: (output.name,))

    issues = validate_artifacts.validate_artifacts(
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
    )

    assert len(issues) == 1
    assert issues[0].status == "invalid_schema"
    assert issues[0].path == output


def test_write_manifest_preserves_existing_file_when_publish_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "input"
    public_output_dir = tmp_path / "public"
    input_dir.mkdir()
    public_output_dir.mkdir()
    for name in validate_artifacts.SMALL_INPUT_FILES:
        (input_dir / name).write_text("value\n1\n", encoding="utf-8")
    config = tmp_path / "quant_config.toml"
    expected_inventory = tmp_path / "expected_inventory.toml"
    config.write_text("[columns]\n", encoding="utf-8")
    expected_inventory.write_text("pre_responses = 1\n", encoding="utf-8")
    for name in validate_artifacts.SMALL_REQUIRED_OUTPUTS:
        (public_output_dir / name).write_bytes(b"artifact")

    manifest = tmp_path / "manifest.json"
    previous_contents = '{"version": 1, "previous": true}\n'
    manifest.write_text(previous_contents, encoding="utf-8")

    def fail_replace(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated manifest publish failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated manifest publish failure"):
        validate_artifacts.write_manifest(
            path=manifest,
            mode="small",
            input_dir=input_dir,
            config=config,
            expected_inventory=expected_inventory,
            public_output_dir=public_output_dir,
        )

    assert manifest.read_text(encoding="utf-8") == previous_contents


def test_small_sources_omits_optional_inventory() -> None:
    input_dir = Path("synthetic")
    config = Path("config.toml")

    assert validate_artifacts._small_sources(input_dir, config, None) == (
        input_dir / "survey.csv",
        input_dir / "grades.csv",
        input_dir / "prompts.csv",
        config,
    )


def test_validate_source_files_does_not_treat_one_byte_file_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "one-byte.csv"
    path.write_bytes(b"x")

    assert validate_artifacts._validate_source_files((path,)) == []


def test_read_csv_header_does_not_parse_rows_after_header(tmp_path: Path) -> None:
    path = tmp_path / "header-only.csv"
    path.write_text("first,second\n1,2\n\"unterminated\n", encoding="utf-8")

    columns = validate_artifacts._read_csv_header(path)

    assert isinstance(columns, pd.Index)
    assert columns.tolist() == ["first", "second"]


def test_missing_csv_columns_lists_all_missing_names(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"

    issue = validate_artifacts._missing_csv_columns(path, pd.Index(["present"]), ("first", "second"))

    assert issue is not None
    assert issue.status == "invalid_schema"
    assert issue.detail == "CSV is missing required columns: first, second"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0" * 64, True),
        ("a" * 64, True),
        ("A" * 64, False),
        ("g" * 64, False),
        ("0" * 63, False),
        ("0" * 65, False),
        (None, False),
        (0, False),
    ],
)
def test_is_sha256_accepts_only_lowercase_64_character_strings(value: object, expected: bool) -> None:
    assert validate_artifacts._is_sha256(value) is expected


def test_write_manifest_serializes_stable_sorted_indented_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir, config, expected_inventory, public_output_dir, output = _write_validation_fixture(tmp_path)
    output.write_text("# report\n", encoding="utf-8")
    monkeypatch.setattr(validate_artifacts, "_required_outputs", lambda _mode: ("report.md",))
    manifest = tmp_path / "nested" / "deeper" / "manifest.json"

    validate_artifacts.write_manifest(
        path=manifest,
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
    )

    sources = validate_artifacts._small_sources(input_dir, config, expected_inventory)
    expected = json.dumps(
        {
            "version": validate_artifacts.MANIFEST_VERSION,
            "sources": validate_artifacts._manifest_entries(sources),
            "outputs": validate_artifacts._manifest_entries((output,)),
        },
        indent=2,
        sort_keys=True,
    ) + "\n"
    assert manifest.read_text(encoding="utf-8") == expected


def test_write_manifest_file_uses_same_directory_and_non_deleting_utf8_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "manifest.json"
    calls: list[dict[str, object]] = []
    original = cast(Any, tempfile.NamedTemporaryFile)

    def recording_tempfile(**kwargs: object):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(validate_artifacts.tempfile, "NamedTemporaryFile", recording_tempfile)

    validate_artifacts._write_manifest_file(target, "{}\n")

    assert target.read_text(encoding="utf-8") == "{}\n"
    assert calls == [
        {
            "mode": "w",
            "encoding": "utf-8",
            "dir": target.parent,
            "prefix": ".manifest.json.",
            "suffix": ".tmp",
            "delete": False,
        }
    ]


def test_write_manifest_file_preserves_temporary_file_creation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_tempfile(**_kwargs: object):
        raise OSError("simulated temporary-file failure")

    monkeypatch.setattr(validate_artifacts.tempfile, "NamedTemporaryFile", fail_tempfile)

    with pytest.raises(OSError, match="simulated temporary-file failure"):
        validate_artifacts._write_manifest_file(tmp_path / "manifest.json", "{}\n")


def test_stale_output_requires_strictly_older_mtime(tmp_path: Path) -> None:
    path = tmp_path / "report.md"
    path.write_text("report\n", encoding="utf-8")
    mtime = path.stat().st_mtime

    assert validate_artifacts._stale_output_issue(path, mtime, allow_stale=False) is None
    assert validate_artifacts._stale_output_issue(path, mtime, allow_stale=True) is None


def test_stale_output_reports_exact_failure_detail(tmp_path: Path) -> None:
    path = tmp_path / "report.md"
    path.write_text("report\n", encoding="utf-8")

    issue = validate_artifacts._stale_output_issue(path, path.stat().st_mtime + 1, allow_stale=False)

    assert issue is not None
    assert issue.status == "stale"
    assert issue.detail == "output is older than at least one input/config file"


def test_validate_outputs_reports_all_output_issues() -> None:
    paths = (Path("missing-a.csv"), Path("missing-b.csv"))

    issues = validate_artifacts._validate_outputs(paths, newest_source_mtime=None, allow_stale=False)

    assert [(issue.status, issue.path) for issue in issues] == [
        ("missing", paths[0]),
        ("missing", paths[1]),
    ]


def test_validate_outputs_honors_allow_stale(tmp_path: Path) -> None:
    path = tmp_path / "report.md"
    path.write_text("report\n", encoding="utf-8")
    os.utime(path, ns=(1, 1))

    assert validate_artifacts._validate_outputs((path,), newest_source_mtime=2, allow_stale=True) == []


def test_newest_source_mtime_ignores_missing_paths_and_directories(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    directory = tmp_path / "directory"
    directory.mkdir()
    source = tmp_path / "source.csv"
    source.write_text("source\n", encoding="utf-8")
    newest = source.stat().st_mtime + 10
    os.utime(directory, ns=(int(newest * 1_000_000_000), int(newest * 1_000_000_000)))

    assert validate_artifacts._newest_source_mtime(()) is None
    assert validate_artifacts._newest_source_mtime((missing, directory, source)) == source.stat().st_mtime


def test_validate_artifacts_forwards_staleness_and_manifest_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir, config, expected_inventory, public_output_dir, output = _write_validation_fixture(tmp_path)
    output.write_text("# report\n", encoding="utf-8")
    monkeypatch.setattr(validate_artifacts, "_required_outputs", lambda _mode: ("report.md",))
    manifest = tmp_path / "manifest.json"
    validate_artifacts.write_manifest(
        path=manifest,
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
    )
    output.write_text("# changed report\n", encoding="utf-8")
    os.utime(output, ns=(1, 1))

    issues = validate_artifacts.validate_artifacts(
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
        allow_stale=True,
        manifest_path=manifest,
    )

    assert [(issue.status, issue.path) for issue in issues] == [("content_changed", output)]


def test_validate_artifacts_passes_mode_to_output_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir, config, expected_inventory, public_output_dir, _ = _write_validation_fixture(tmp_path)
    seen_modes: list[str] = []

    def required_outputs(mode: str) -> tuple[str, ...]:
        seen_modes.append(mode)
        return ()

    monkeypatch.setattr(validate_artifacts, "_required_outputs", required_outputs)

    assert validate_artifacts.validate_artifacts(
        mode="small",
        input_dir=input_dir,
        config=config,
        expected_inventory=expected_inventory,
        public_output_dir=public_output_dir,
    ) == []
    assert seen_modes == ["small"]


def test_write_manifest_rejects_missing_required_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir, config, expected_inventory, public_output_dir, _ = _write_validation_fixture(tmp_path)
    monkeypatch.setattr(validate_artifacts, "_required_outputs", lambda _mode: ("missing.md",))

    with pytest.raises(FileNotFoundError, match="Cannot write manifest; required files are missing"):
        validate_artifacts.write_manifest(
            path=tmp_path / "manifest.json",
            mode="small",
            input_dir=input_dir,
            config=config,
            expected_inventory=expected_inventory,
            public_output_dir=public_output_dir,
        )


def test_validate_manifest_rejects_unexpected_top_level_fields(tmp_path: Path) -> None:
    manifest, source, output = _write_valid_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["extra"] = "unexpected"
    payload["extra_two"] = "unexpected"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    issues = validate_artifacts._validate_manifest(manifest, (source,), (output,))

    assert len(issues) == 1
    assert issues[0].status == "invalid_manifest"
    assert issues[0].path == manifest
    assert issues[0].detail == "manifest has unexpected top-level entries: extra, extra_two"


def test_validate_manifest_rejects_malformed_json(tmp_path: Path) -> None:
    manifest, source, output = _write_valid_manifest_fixture(tmp_path)
    manifest.write_text("{", encoding="utf-8")

    issues = validate_artifacts._validate_manifest(manifest, (source,), (output,))

    assert len(issues) == 1
    assert issues[0].status == "invalid_manifest"
    assert issues[0].path == manifest
    assert "manifest could not be read" in issues[0].detail


def test_validate_manifest_rejects_unknown_version(tmp_path: Path) -> None:
    manifest, source, output = _write_valid_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["version"] = validate_artifacts.MANIFEST_VERSION + 1
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    issues = validate_artifacts._validate_manifest(manifest, (source,), (output,))

    assert len(issues) == 1
    assert issues[0].status == "invalid_manifest"
    assert issues[0].path == manifest
    assert f"version must be {validate_artifacts.MANIFEST_VERSION}" in issues[0].detail


def test_validate_manifest_rejects_missing_and_extra_entries(tmp_path: Path) -> None:
    manifest, source, output = _write_valid_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    missing_a = tmp_path / "missing-a.csv"
    missing_b = tmp_path / "missing-b.csv"
    payload["sources"] = {"unexpected-source-a.csv": "0" * 64, "unexpected-source-b.csv": "0" * 64}
    payload["outputs"] = {"unexpected-output-a.csv": "0" * 64, "unexpected-output-b.csv": "0" * 64}
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    issues = validate_artifacts._validate_manifest(manifest, (source, missing_a, missing_b), (output,))

    assert len(issues) == 2
    assert all(issue.status == "invalid_manifest" for issue in issues)
    assert all(issue.path == manifest for issue in issues)
    source_issue = next(issue for issue in issues if "sources" in issue.detail)
    output_issue = next(issue for issue in issues if "outputs" in issue.detail)
    assert source_issue.detail == (
        f"manifest sources contract mismatch (missing entries: {missing_a}, {missing_b}, {source}; "
        "unexpected entries: unexpected-source-a.csv, unexpected-source-b.csv)"
    )
    assert output_issue.detail == (
        "manifest outputs contract mismatch (missing entries: "
        f"{output}; unexpected entries: unexpected-output-a.csv, unexpected-output-b.csv)"
    )


def test_validate_manifest_rejects_extra_entry_when_expected_entry_is_present(tmp_path: Path) -> None:
    manifest, source, output = _write_valid_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["outputs"]["unexpected-output.csv"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    issues = validate_artifacts._validate_manifest(manifest, (source,), (output,))

    assert len(issues) == 1
    assert issues[0].path == manifest
    assert issues[0].detail == "manifest outputs contract mismatch (unexpected entries: unexpected-output.csv)"


def test_validate_manifest_rejects_invalid_hash(tmp_path: Path) -> None:
    manifest, source, output = _write_valid_manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["outputs"][str(output)] = "not-a-sha256"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    issues = validate_artifacts._validate_manifest(manifest, (source,), (output,))

    assert len(issues) == 1
    assert issues[0].status == "invalid_manifest"
    assert issues[0].path == manifest
    assert "not a SHA-256 digest" in issues[0].detail


def test_validate_source_files_rejects_existing_directory_as_source(tmp_path: Path) -> None:
    path = tmp_path / "survey.csv"
    path.mkdir()

    issues = validate_artifacts._validate_source_files((path,))

    assert len(issues) == 1
    assert issues[0].status == "not_file"
    assert issues[0].path == path
    assert issues[0].detail == "required source path is not a file"


def test_validate_csv_reports_parser_errors_as_invalid_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "input.csv"
    path.write_text("participant_id\n1\n", encoding="utf-8")

    def raise_parser_error(*_args: object, **_kwargs: object) -> None:
        raise pd.errors.ParserError("malformed CSV")

    monkeypatch.setattr(validate_artifacts.pd, "read_csv", raise_parser_error)

    issue = validate_artifacts._validate_csv(path, ("participant_id",))

    assert issue is not None
    assert issue.status == "invalid_csv"
    assert issue.path == path
    assert "malformed CSV" in issue.detail


def test_validate_csv_does_not_hide_unexpected_read_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "input.csv"
    path.write_text("participant_id\n1\n", encoding="utf-8")

    def raise_unexpected_error(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("unexpected parser bug")

    monkeypatch.setattr(validate_artifacts.pd, "read_csv", raise_unexpected_error)

    with pytest.raises(RuntimeError, match="unexpected parser bug"):
        validate_artifacts._validate_csv(path, ("participant_id",))


def test_validate_manifest_detects_changed_output_even_when_mtime_is_preserved(tmp_path: Path) -> None:
    manifest, source, output = _write_valid_manifest_fixture(tmp_path)
    original = output.stat()
    output.write_text("result\n2\n", encoding="utf-8")
    os.utime(output, ns=(original.st_atime_ns, original.st_mtime_ns))

    issues = validate_artifacts._validate_manifest(manifest, (source,), (output,))

    assert [(issue.status, issue.path) for issue in issues] == [("content_changed", output)]
    assert issues[0].detail == "file content differs from manifest"


def test_print_validation_report_handles_success_and_issues(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    validate_artifacts.print_validation_report([])
    assert capsys.readouterr().out == "Artifact validation passed.\n"

    issue = validate_artifacts.ValidationIssue("missing", tmp_path / "output.csv", "required output artifact is missing")
    validate_artifacts.print_validation_report([issue])
    output = capsys.readouterr().out
    assert output == (
        "Artifact validation failed:\n"
        f"missing: {tmp_path / 'output.csv'} - required output artifact is missing\n"
    )


def test_parse_args_exposes_stable_defaults_and_help(capsys: pytest.CaptureFixture[str]) -> None:
    defaults = validate_artifacts.parse_args([])

    assert defaults.mode == "small"
    assert defaults.input_dir == validate_artifacts.DATA_SYNTHETIC_DIR
    assert defaults.config == validate_artifacts.QUANT_CONFIG_TEMPLATE
    assert defaults.expected_inventory == validate_artifacts.EXPECTED_INVENTORY_TEMPLATE
    assert defaults.public_output_dir == validate_artifacts.REPRO_SMALL_PUBLIC_DIR
    assert defaults.allow_stale is False
    assert defaults.manifest is None
    assert isinstance(defaults.input_dir, Path)
    assert isinstance(defaults.config, Path)
    assert isinstance(defaults.expected_inventory, Path)
    assert isinstance(defaults.public_output_dir, Path)

    with pytest.raises(SystemExit) as help_exit:
        validate_artifacts.parse_args(["--help"])

    assert help_exit.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "Validate reproducibility artifacts for the public workflow." in help_text
    assert "--mode {small}" in help_text
    assert "--input-dir" in help_text
    assert "Directory containing synthetic survey, grades, and prompts CSV files." in help_text
    assert "Artifact contract to validate." in help_text
    assert "Quantitative TOML configuration used to generate outputs." in help_text
    assert "Expected inventory TOML used by the synthetic smoke run." in help_text
    assert "Directory containing generated public quantitative artifacts." in help_text
    assert "Report success even when outputs are older than inputs/config." in help_text
    assert "--manifest" in help_text
    assert "Optional SHA-256 manifest to validate alongside artifacts." in help_text
    assert "XX" not in help_text


def test_main_forwards_all_cli_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    reported: list[object] = []

    def fake_validate(**kwargs: object) -> list[validate_artifacts.ValidationIssue]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(validate_artifacts, "validate_artifacts", fake_validate)
    monkeypatch.setattr(validate_artifacts, "print_validation_report", reported.append)

    input_dir = tmp_path / "input"
    config = tmp_path / "config.toml"
    expected_inventory = tmp_path / "expected.toml"
    output_dir = tmp_path / "output"
    manifest = tmp_path / "manifest.json"
    assert validate_artifacts.main(
        [
            "--mode",
            "small",
            "--input-dir",
            str(input_dir),
            "--config",
            str(config),
            "--expected-inventory",
            str(expected_inventory),
            "--public-output-dir",
            str(output_dir),
            "--allow-stale",
            "--manifest",
            str(manifest),
        ]
    ) == 0

    assert captured == {
        "mode": "small",
        "input_dir": input_dir,
        "config": config,
        "expected_inventory": expected_inventory,
        "public_output_dir": output_dir,
        "allow_stale": True,
        "manifest_path": manifest,
    }
    assert reported == [[]]


def test_validate_artifacts_main_returns_status_from_validator(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(validate_artifacts, "validate_artifacts", lambda **_kwargs: [])
    monkeypatch.setattr(validate_artifacts, "print_validation_report", lambda _issues: None)
    assert validate_artifacts.main(["--public-output-dir", str(tmp_path)]) == 0

    issue = validate_artifacts.ValidationIssue("missing", tmp_path / "output.csv", "missing")
    monkeypatch.setattr(validate_artifacts, "validate_artifacts", lambda **_kwargs: [issue])
    assert validate_artifacts.main(["--public-output-dir", str(tmp_path)]) == 1
