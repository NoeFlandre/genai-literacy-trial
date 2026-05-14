from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from genai_literacy_trial.cli import app
from genai_literacy_trial.quant_figures import FIGURE_FORMATS, FIGURE_STEMS
from genai_literacy_trial.quant_pipeline import TABLE_OUTPUT_FORMAT
from genai_literacy_trial.quant_report import QUANTITATIVE_REPORT_FILENAME
from genai_literacy_trial.quant_schema import REQUIRED_QUANT_TABLES
from tests.quant_fixtures import write_synthetic_quant_input


REQUIRED_ANALYZE_QUANT_OUTPUTS = [
    QUANTITATIVE_REPORT_FILENAME,
    *(f"{name}.{TABLE_OUTPUT_FORMAT}" for name in REQUIRED_QUANT_TABLES),
    *(f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in FIGURE_FORMATS),
]


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
    for name in REQUIRED_ANALYZE_QUANT_OUTPUTS:
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
    for stale in stale_artifacts:
        assert not stale.exists(), stale.name
    for name in REQUIRED_ANALYZE_QUANT_OUTPUTS:
        assert (public_dir / name).exists(), name
    assert nested_stale.exists()
    assert preserved.exists()
