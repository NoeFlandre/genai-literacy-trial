from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from genai_literacy_trial import validate_artifacts


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
