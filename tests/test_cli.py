from __future__ import annotations

from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from genai_literacy_trial.cli import app


def test_reproduce_paper_writes_safe_outputs_from_synthetic_inputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "paper_outputs"
    input_dir.mkdir()

    pd.DataFrame(
        {
            "Email": ["p01", "p02", "p03"],
            "Phase": ["After", "After", "After"],
        }
    ).to_csv(input_dir / "survey.csv", index=False)
    pd.DataFrame(
        {
            "Email": ["p01", "p02", "p03"],
            "Group": ["A", "B", "C"],
            "Midterm Grade": ["B", "B+", "A-"],
            "Final Grade": ["B+", "A-", "A"],
        }
    ).to_csv(input_dir / "grades.csv", index=False)
    pd.DataFrame(
        {
            "Email": ["p01", "p02", "p03"],
            "Student prompting quality score (1 bad - 5 best)": [2.0, 3.0, 4.0],
        }
    ).to_csv(input_dir / "prompts.csv", index=False)

    result = CliRunner().invoke(
        app,
        [
            "reproduce-paper",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (output_dir / "sample_summary.csv").exists()
    assert (output_dir / "prompt_training_means.csv").exists()
    assert (output_dir / "prompt_grade_correlations.csv").exists()
    assert (output_dir / "validation_report.csv").exists()


def test_audit_privacy_fails_on_public_personal_data(tmp_path: Path) -> None:
    unsafe_address = "student" + "@" + "academic-domain" + "." + "edu"
    (tmp_path / "README.md").write_text(unsafe_address, encoding="utf-8")

    result = CliRunner().invoke(app, ["audit-privacy", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "email" in result.output


def test_validate_paper_reads_paper_statistics_and_writes_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "paper_outputs"
    output_dir.mkdir()
    pd.DataFrame({"metric": ["retained_students"], "observed": [45.0]}).to_csv(output_dir / "paper_statistics.csv", index=False)

    result = CliRunner().invoke(app, ["validate-paper", "--output-dir", str(output_dir)])

    assert result.exit_code == 0, result.output
    report = pd.read_csv(output_dir / "validation_report.csv")
    assert set(report.columns) == {"metric", "expected", "observed", "delta", "status"}
    assert report.loc[report["metric"] == "retained_students", "status"].item() == "ok"


def test_validate_paper_falls_back_to_sample_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / "paper_outputs"
    output_dir.mkdir()
    pd.DataFrame({"retained_students": [45.0]}).to_csv(output_dir / "sample_summary.csv", index=False)

    result = CliRunner().invoke(app, ["validate-paper", "--output-dir", str(output_dir)])

    assert result.exit_code == 0, result.output
    assert (output_dir / "validation_report.csv").exists()
