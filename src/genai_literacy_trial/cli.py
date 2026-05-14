from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer

from genai_literacy_trial.analysis import (
    build_paper_aggregates,
    load_csv_inputs,
    observed_metrics_from_outputs,
    validate_against_targets,
    write_aggregate_outputs,
)
from genai_literacy_trial.privacy import scan_public_tree
from genai_literacy_trial.quant_pipeline import run_quant_analysis
from genai_literacy_trial.quant_schema import PUBLIC_OUTPUT_DIR_KEY

app = typer.Typer(no_args_is_help=True)


@app.command("build-aggregates")
def build_aggregates(
    input_dir: Path = typer.Option(Path("data/synthetic"), help="Directory containing survey.csv, grades.csv, and prompts.csv."),
    output_dir: Path = typer.Option(Path("paper_outputs"), help="Directory for aggregate-only outputs."),
) -> None:
    survey, grades, prompts = load_csv_inputs(input_dir)
    outputs = build_paper_aggregates(survey=survey, grades=grades, prompts=prompts)
    write_aggregate_outputs(outputs, output_dir)
    typer.echo(f"Wrote aggregate-only outputs to {output_dir}")


@app.command("validate-paper")
def validate_paper(
    output_dir: Path = typer.Option(Path("paper_outputs"), help="Directory containing aggregate outputs."),
) -> None:
    observed = {}
    statistics_path = output_dir / "paper_statistics.csv"
    if statistics_path.exists():
        statistics = pd.read_csv(statistics_path)
        observed.update(observed_metrics_from_outputs({"paper_statistics": statistics}))
    sample_path = output_dir / "sample_summary.csv"
    if not observed and sample_path.exists():
        sample = pd.read_csv(sample_path)
        observed.update(observed_metrics_from_outputs({"sample_summary": sample}))
    report = validate_against_targets(observed)
    output_dir.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_dir / "validation_report.csv", index=False)
    mismatches = report[report["status"] == "mismatch"]
    typer.echo(f"Wrote validation report to {output_dir / 'validation_report.csv'}")
    if not mismatches.empty:
        typer.echo("Manuscript target mismatches were flagged for author review.")


@app.command("reproduce-paper")
def reproduce_paper(
    input_dir: Path = typer.Option(Path("data/synthetic"), help="Directory containing public synthetic CSV fixtures."),
    output_dir: Path = typer.Option(Path("paper_outputs"), help="Directory for aggregate-only paper outputs."),
) -> None:
    survey, grades, prompts = load_csv_inputs(input_dir)
    outputs = build_paper_aggregates(survey=survey, grades=grades, prompts=prompts)
    write_aggregate_outputs(outputs, output_dir)
    observed = observed_metrics_from_outputs(outputs)
    validate_against_targets(observed).to_csv(output_dir / "validation_report.csv", index=False)
    typer.echo(f"Reproduced aggregate outputs and validation report in {output_dir}")


@app.command("audit-privacy")
def audit_privacy(
    root: Path = typer.Option(Path("."), help="Repository root to scan."),
    local_patterns: Path | None = typer.Option(None, help="Optional ignored YAML file with additional private patterns."),
) -> None:
    findings = scan_public_tree(root, local_pattern_file=local_patterns)
    if not findings:
        typer.echo("Privacy audit passed: no public personal-data patterns found.")
        return
    for finding in findings:
        typer.echo(f"{finding.path}: {finding.rule}: {finding.evidence}")
    raise typer.Exit(1)


@app.command("analyze-quant")
def analyze_quant(
    input_dir: Path = typer.Option(Path("data/synthetic"), help="Directory containing survey, grades, and prompts input files."),
    config: Path = typer.Option(Path("config/quant_config.template.toml"), help="TOML configuration mapping column names."),
    expected_inventory: Path | None = typer.Option(None, help="Optional TOML file with expected inventory counts."),
    output_dir: Path = typer.Option(Path("private_outputs/quantitative"), help="Ignored private output directory for diagnostics."),
    public_output_dir: Path = typer.Option(Path("paper_outputs/quantitative"), help="Aggregate-only public output directory."),
) -> None:
    paths = run_quant_analysis(input_dir, config, expected_inventory, output_dir, public_output_dir)
    typer.echo(f"Quantitative analysis complete. Public outputs: {paths[PUBLIC_OUTPUT_DIR_KEY]}")
    typer.echo("Privacy audit passed for generated public outputs.")


if __name__ == "__main__":
    app()
