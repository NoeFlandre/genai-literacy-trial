from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

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
    assert "Artifact validation passed." in capsys.readouterr().out

    issue = validate_artifacts.ValidationIssue("missing", tmp_path / "output.csv", "required output artifact is missing")
    validate_artifacts.print_validation_report([issue])
    output = capsys.readouterr().out
    assert "Artifact validation failed:" in output
    assert "missing" in output


def test_validate_artifacts_main_returns_status_from_validator(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(validate_artifacts, "validate_artifacts", lambda **_kwargs: [])
    monkeypatch.setattr(validate_artifacts, "print_validation_report", lambda _issues: None)
    assert validate_artifacts.main(["--public-output-dir", str(tmp_path)]) == 0

    issue = validate_artifacts.ValidationIssue("missing", tmp_path / "output.csv", "missing")
    monkeypatch.setattr(validate_artifacts, "validate_artifacts", lambda **_kwargs: [issue])
    assert validate_artifacts.main(["--public-output-dir", str(tmp_path)]) == 1
