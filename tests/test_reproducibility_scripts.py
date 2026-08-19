from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from genai_literacy_trial import reproduce_small
from genai_literacy_trial.quant_figures import FIGURE_FORMATS, FIGURE_STEMS
from genai_literacy_trial.quant_report import QUANTITATIVE_REPORT_FILENAME
from genai_literacy_trial.quant_schema import QUANT_TABLE_OUTPUT_FORMAT, REQUIRED_QUANT_TABLES


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SMALL_OUTPUTS = (
    QUANTITATIVE_REPORT_FILENAME,
    *(f"{name}.{QUANT_TABLE_OUTPUT_FORMAT}" for name in REQUIRED_QUANT_TABLES),
    *(f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in FIGURE_FORMATS),
)


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def run_module(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _run_small_with_manifest(tmp_path: Path) -> tuple[Path, Path, Path, subprocess.CompletedProcess[str]]:
    input_dir = tmp_path / "input"
    public_output_dir = tmp_path / "public"
    private_output_dir = tmp_path / "private"
    manifest = tmp_path / "manifest.json"
    input_dir.mkdir()
    for name in ("survey.csv", "grades.csv", "prompts.csv"):
        shutil.copy2(REPO_ROOT / "data" / "synthetic" / name, input_dir / name)

    result = run_script(
        "scripts/reproduce_small.py",
        "--input-dir",
        str(input_dir),
        "--public-output-dir",
        str(public_output_dir),
        "--output-dir",
        str(private_output_dir),
        "--manifest",
        str(manifest),
    )
    return input_dir, public_output_dir, manifest, result


def test_validate_artifacts_reports_missing_small_outputs(tmp_path: Path) -> None:
    result = run_script(
        "scripts/validate_artifacts.py",
        "--mode",
        "small",
        "--public-output-dir",
        str(tmp_path / "missing-public"),
    )

    assert result.returncode == 1
    assert "missing" in result.stdout
    assert "table_data_verification.csv" in result.stdout


def test_validate_artifacts_reports_stale_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    public_output_dir = tmp_path / "public"
    config = tmp_path / "quant_config.toml"
    expected_inventory = tmp_path / "expected_inventory.toml"
    input_dir.mkdir()
    public_output_dir.mkdir()
    for name in ("survey.csv", "grades.csv", "prompts.csv"):
        (input_dir / name).write_text("col\nvalue\n", encoding="utf-8")
    config.write_text("[columns]\n", encoding="utf-8")
    expected_inventory.write_text("pre_responses = 1\n", encoding="utf-8")

    for name in REQUIRED_SMALL_OUTPUTS:
        path = public_output_dir / name
        if path.suffix == ".csv":
            path.write_text("col\nvalue\n", encoding="utf-8")
        else:
            path.write_bytes(b"artifact")
        os.utime(path, (1_700_000_000, 1_700_000_000))
    for path in [*(input_dir / name for name in ("survey.csv", "grades.csv", "prompts.csv")), config, expected_inventory]:
        os.utime(path, (1_700_000_100, 1_700_000_100))

    result = run_script(
        "scripts/validate_artifacts.py",
        "--mode",
        "small",
        "--input-dir",
        str(input_dir),
        "--config",
        str(config),
        "--expected-inventory",
        str(expected_inventory),
        "--public-output-dir",
        str(public_output_dir),
    )

    assert result.returncode == 1
    assert "stale" in result.stdout
    assert "quantitative_report.md" in result.stdout


def test_validate_artifacts_reports_invalid_quant_table_schema(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    public_output_dir = tmp_path / "public"
    config = tmp_path / "quant_config.toml"
    expected_inventory = tmp_path / "expected_inventory.toml"
    input_dir.mkdir()
    public_output_dir.mkdir()
    for name in ("survey.csv", "grades.csv", "prompts.csv"):
        (input_dir / name).write_text("col\nvalue\n", encoding="utf-8")
    config.write_text("[columns]\n", encoding="utf-8")
    expected_inventory.write_text("pre_responses = 1\n", encoding="utf-8")

    for name in REQUIRED_SMALL_OUTPUTS:
        path = public_output_dir / name
        if path.suffix == ".csv":
            path.write_text("col\nvalue\n", encoding="utf-8")
        else:
            path.write_bytes(b"artifact")

    result = run_script(
        "scripts/validate_artifacts.py",
        "--mode",
        "small",
        "--input-dir",
        str(input_dir),
        "--config",
        str(config),
        "--expected-inventory",
        str(expected_inventory),
        "--public-output-dir",
        str(public_output_dir),
        "--allow-stale",
    )

    assert result.returncode == 1
    assert "invalid_schema" in result.stdout
    assert "table_data_verification.csv" in result.stdout


def test_reproduce_small_generates_and_validates_quant_outputs(tmp_path: Path) -> None:
    public_output_dir = tmp_path / "public"
    private_output_dir = tmp_path / "private"

    result = run_script(
        "scripts/reproduce_small.py",
        "--public-output-dir",
        str(public_output_dir),
        "--output-dir",
        str(private_output_dir),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Small reproducibility run complete" in result.stdout
    assert "RuntimeWarning" not in result.stderr
    assert "ConvergenceWarning" not in result.stderr
    assert (public_output_dir / "quantitative_report.md").exists()
    assert (public_output_dir / "table_data_verification.csv").exists()
    assert private_output_dir.exists()


def test_reproduce_small_module_entry_point_matches_script_behavior(tmp_path: Path) -> None:
    public_output_dir = tmp_path / "public"
    private_output_dir = tmp_path / "private"

    result = run_module(
        "genai_literacy_trial.reproduce_small",
        "--public-output-dir",
        str(public_output_dir),
        "--output-dir",
        str(private_output_dir),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Small reproducibility run complete" in result.stdout
    assert (public_output_dir / "quantitative_report.md").exists()


def test_reproduce_small_outputs_are_byte_deterministic(tmp_path: Path) -> None:
    first_public = tmp_path / "first" / "public"
    second_public = tmp_path / "second" / "public"

    for root in (tmp_path / "first", tmp_path / "second"):
        result = run_script(
            "scripts/reproduce_small.py",
            "--public-output-dir",
            str(root / "public"),
            "--output-dir",
            str(root / "private"),
        )
        assert result.returncode == 0, result.stdout + result.stderr

    for relative_path in REQUIRED_SMALL_OUTPUTS:
        assert (first_public / relative_path).read_bytes() == (second_public / relative_path).read_bytes(), relative_path


def test_reproduce_small_writes_optional_manifest(tmp_path: Path) -> None:
    _, public_output_dir, manifest, result = _run_small_with_manifest(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert any(path.endswith("survey.csv") for path in payload["sources"])
    assert any(path.endswith("table_data_verification.csv") for path in payload["outputs"])
    assert (public_output_dir / "table_data_verification.csv").exists()


def test_validate_artifacts_reports_manifest_source_change_with_preserved_mtime(tmp_path: Path) -> None:
    input_dir, _, manifest, result = _run_small_with_manifest(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr

    source = input_dir / "survey.csv"
    original = source.stat()
    source.write_bytes(source.read_bytes() + b"\n")
    os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))

    result = run_script(
        "scripts/validate_artifacts.py",
        "--mode",
        "small",
        "--input-dir",
        str(input_dir),
        "--config",
        str(REPO_ROOT / "config" / "quant_config.template.toml"),
        "--expected-inventory",
        str(REPO_ROOT / "config" / "expected_inventory.template.toml"),
        "--public-output-dir",
        str(tmp_path / "public"),
        "--manifest",
        str(manifest),
    )

    assert result.returncode == 1
    assert "content_changed" in result.stdout
    assert "survey.csv" in result.stdout


def test_validate_artifacts_reports_manifest_output_change_with_preserved_mtime(tmp_path: Path) -> None:
    _, public_output_dir, manifest, result = _run_small_with_manifest(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr

    output = public_output_dir / "table_data_verification.csv"
    original = output.stat()
    output.write_bytes(output.read_bytes() + b"\n")
    os.utime(output, ns=(original.st_atime_ns, original.st_mtime_ns))

    result = run_script(
        "scripts/validate_artifacts.py",
        "--mode",
        "small",
        "--public-output-dir",
        str(public_output_dir),
        "--manifest",
        str(manifest),
    )

    assert result.returncode == 1
    assert "content_changed" in result.stdout
    assert "table_data_verification.csv" in result.stdout


def test_validate_artifacts_module_entry_point_reports_missing_outputs(tmp_path: Path) -> None:
    result = run_module(
        "genai_literacy_trial.validate_artifacts",
        "--mode",
        "small",
        "--public-output-dir",
        str(tmp_path / "missing-public"),
    )

    assert result.returncode == 1
    assert "missing" in result.stdout


def test_reproduce_small_main_covers_clean_manifest_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    public_output_dir = tmp_path / "public"
    private_output_dir = tmp_path / "private"
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(
        reproduce_small,
        "run_quant_analysis",
        lambda *_args: {"public_output_dir": public_output_dir, "private_output_dir": private_output_dir},
    )
    monkeypatch.setattr(reproduce_small, "validate_artifacts", lambda **_kwargs: [])
    monkeypatch.setattr(reproduce_small, "print_validation_report", lambda _issues: None)
    monkeypatch.setattr(reproduce_small, "write_manifest", lambda **_kwargs: None)

    result = reproduce_small.main(
        [
            "--output-dir",
            str(private_output_dir),
            "--public-output-dir",
            str(public_output_dir),
            "--manifest",
            str(manifest),
            "--show-model-warnings",
        ]
    )

    assert result == 0


def test_reproduce_small_main_returns_one_for_validation_issues(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        reproduce_small,
        "run_quant_analysis",
        lambda *_args: {"public_output_dir": tmp_path / "public", "private_output_dir": tmp_path / "private"},
    )
    monkeypatch.setattr(reproduce_small, "validate_artifacts", lambda **_kwargs: [object()])
    monkeypatch.setattr(reproduce_small, "print_validation_report", lambda _issues: None)

    assert reproduce_small.main(["--output-dir", str(tmp_path / "private"), "--public-output-dir", str(tmp_path / "public")]) == 1
