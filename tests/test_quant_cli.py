from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from genai_literacy_trial.cli import app
from tests.quant_fixtures import write_synthetic_quant_input


def test_analyze_quant_cli_generates_tables_figures_and_report(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "private"
    public_dir = tmp_path / "public"
    write_synthetic_quant_input(input_dir)

    result = CliRunner().invoke(
        app,
        [
            "analyze-quant",
            "--input-dir",
            str(input_dir),
            "--config",
            "config/quant_config.template.toml",
            "--expected-inventory",
            "config/expected_inventory.template.toml",
            "--output-dir",
            str(output_dir),
            "--public-output-dir",
            str(public_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    required = [
        "quantitative_report.md",
        "table_data_verification.csv",
        "table_complete_case_diagnostics.csv",
        "table_learning_outcome_models.csv",
        "table_participant_training_tests.csv",
        "table_perceived_usefulness_models.csv",
        "table_prior_use_mapping.csv",
        "table_scored_assignment_distribution_by_group.csv",
        "table_prompt_sensitivity_min3_assignments.csv",
        "table_prompt_sensitivity_all4_assignments.csv",
        "fig_prompt_quality_trajectory.pdf",
        "fig_prompt_quality_trajectory.png",
        "fig_prompt_quality_learning_outcome.pdf",
        "fig_prompt_quality_learning_outcome.png",
        "fig_calibration_forest.pdf",
        "fig_calibration_forest.png",
    ]
    for name in required:
        assert (public_dir / name).exists(), name
    assert "Privacy audit passed" in result.output


def test_analyze_quant_cli_cleans_stale_public_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "private"
    public_dir = tmp_path / "public"
    write_synthetic_quant_input(input_dir)

    stale_artifacts = [
        public_dir / "stale.csv",
        public_dir / "fig_old.png",
        public_dir / "old_report.md",
        public_dir / "legacy_report.pdf",
    ]
    public_dir.mkdir(parents=True, exist_ok=True)
    for stale in stale_artifacts:
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale generated artifact", encoding="utf-8")
    (public_dir / "nested").mkdir()
    nested_stale = public_dir / "nested" / "old_fig.png"
    nested_stale.write_text("nested stale figure", encoding="utf-8")
    preserved = public_dir / "notes.txt"
    preserved.write_text("should remain", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "analyze-quant",
            "--input-dir",
            str(input_dir),
            "--config",
            "config/quant_config.template.toml",
            "--expected-inventory",
            "config/expected_inventory.template.toml",
            "--output-dir",
            str(output_dir),
            "--public-output-dir",
            str(public_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    required = [
        "quantitative_report.md",
        "table_data_verification.csv",
        "table_complete_case_diagnostics.csv",
        "table_learning_outcome_models.csv",
        "table_participant_training_tests.csv",
        "table_perceived_usefulness_models.csv",
        "table_prior_use_mapping.csv",
        "table_scored_assignment_distribution_by_group.csv",
        "table_prompt_sensitivity_min3_assignments.csv",
        "table_prompt_sensitivity_all4_assignments.csv",
        "fig_prompt_quality_trajectory.pdf",
        "fig_prompt_quality_trajectory.png",
        "fig_prompt_quality_learning_outcome.pdf",
        "fig_prompt_quality_learning_outcome.png",
        "fig_calibration_forest.pdf",
        "fig_calibration_forest.png",
    ]
    for stale in stale_artifacts:
        assert not stale.exists(), stale.name
    for name in required:
        assert (public_dir / name).exists(), name
    assert nested_stale.exists()
    assert preserved.exists()
