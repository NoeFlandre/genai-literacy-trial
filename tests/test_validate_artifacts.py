from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from genai_literacy_trial import validate_artifacts


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
