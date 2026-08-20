from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import genai_literacy_trial.quant_pipeline as quant_pipeline
from genai_literacy_trial.quant_config import QuantConfig
from genai_literacy_trial.quant_pipeline import (
    COMPATIBILITY_INPUT_PREFIX,
    EMPTY_CALIBRATION_FOREST_ROW,
    EMPTY_CALIBRATION_FOREST_COLUMNS,
    GENERATED_PUBLIC_SUFFIXES,
    INPUT_DATASETS,
    INPUT_FILE_FORMATS,
    INPUT_READERS,
    _calibration_forest_source,
    _numeric_input_issues,
    _read_primary_input,
    _read_input,
    _sample_bad_values,
    _score_reliability_items,
    _merge_pre_composites,
    run_quant_analysis,
)
from genai_literacy_trial.quant_figures import FIGURE_FORMATS
from genai_literacy_trial.quant_report import QUANTITATIVE_REPORT_FILENAME
from genai_literacy_trial.quant_preprocess import compute_survey_composites, participant_key
from genai_literacy_trial.quant_schema import PARTICIPANT_KEY_COLUMN, QUANT_TABLE_OUTPUT_FORMAT
from tests.quant_fixtures import write_synthetic_quant_input


def test_merge_pre_composites_uses_normalized_pre_phase_from_composites() -> None:
    config = QuantConfig.default()
    config = QuantConfig(
        columns=config.columns,
        pre_label="baseline",
        post_label="followup",
        survey_dimensions={"locus_of_control": ["control_1"]},
        reverse_coded_items={},
    )
    retained = pd.DataFrame(
        {
            "participant_id": ["p1", "p1"],
            "phase": ["baseline", "followup"],
            "group": ["A", "A"],
            "control_1": [2.0, 5.0],
        }
    )
    participant = pd.DataFrame({PARTICIPANT_KEY_COLUMN: [participant_key("p1")], "group": ["A"]})
    composites = compute_survey_composites(retained, config)

    merged = _merge_pre_composites(participant, composites)

    assert merged.loc[0, "locus_of_control"] == 2.0


def test_quant_pipeline_input_dataset_contract_is_explicit() -> None:
    assert INPUT_DATASETS == ("survey", "grades", "prompts")


def test_quant_pipeline_input_file_formats_are_explicit() -> None:
    assert INPUT_FILE_FORMATS == ("csv", "xlsx")


def test_each_declared_input_format_has_reader() -> None:
    assert set(INPUT_FILE_FORMATS) <= set(INPUT_READERS)


def test_read_input_honors_configured_file_formats(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("genai_literacy_trial.quant_pipeline.INPUT_FILE_FORMATS", ("xlsx",))
    expected = pd.DataFrame({"value": [1, 2]})
    expected.to_excel(tmp_path / "survey.xlsx", index=False)

    observed = _read_input(tmp_path, "survey")

    pd.testing.assert_frame_equal(observed, expected)


def test_read_input_rejects_multiple_primary_formats(tmp_path) -> None:
    frame = pd.DataFrame({"value": [1, 2]})
    frame.to_csv(tmp_path / "survey.csv", index=False)
    frame.to_excel(tmp_path / "survey.xlsx", index=False)

    with pytest.raises(ValueError, match="Multiple input files found for survey"):
        _read_input(tmp_path, "survey")


def test_read_primary_input_preserves_dataset_name(monkeypatch, tmp_path) -> None:
    def reader(_path: Path) -> pd.DataFrame:
        return pd.DataFrame({"value": [1]})
    calls: list[tuple[Path, str, object]] = []

    def fake_read_dataset(path: Path, name: str, callback: object) -> pd.DataFrame:
        calls.append((path, name, callback))
        return pd.DataFrame({"value": [1]})

    monkeypatch.setattr(quant_pipeline, "_read_dataset", fake_read_dataset)
    path = tmp_path / "survey.csv"

    result = _read_primary_input([(path, reader)], "survey")

    assert result is not None
    assert calls == [(path, "survey", reader)]


def test_sample_bad_values_keeps_three_value_error_limit() -> None:
    values = pd.Series(["bad1", "bad2", "bad3", "bad4"])

    assert _sample_bad_values(values, pd.Series([True] * 4)) == "bad1, bad2, bad3"


def test_numeric_input_issues_does_not_reject_fractional_noninteger_scores_by_default() -> None:
    assert _numeric_input_issues(pd.Series([1.5]), "prompt_score") == []


def test_quant_pipeline_compatibility_input_prefix_is_explicit() -> None:
    assert COMPATIBILITY_INPUT_PREFIX == "public_cli_input_"


def test_generated_public_suffixes_derive_from_output_contracts() -> None:
    expected = {f".{QUANT_TABLE_OUTPUT_FORMAT}", *(f".{suffix}" for suffix in FIGURE_FORMATS), ".md"}
    assert GENERATED_PUBLIC_SUFFIXES == expected
    assert f".{QUANTITATIVE_REPORT_FILENAME.rsplit('.', maxsplit=1)[-1]}" in GENERATED_PUBLIC_SUFFIXES


def test_calibration_forest_source_preserves_empty_table_fallback_schema() -> None:
    observed = _calibration_forest_source(pd.DataFrame())

    assert list(observed.columns) == list(EMPTY_CALIBRATION_FOREST_COLUMNS)
    assert observed.to_dict("records") == [EMPTY_CALIBRATION_FOREST_ROW]


def test_run_quant_analysis_fails_fast_on_missing_required_input_columns(tmp_path) -> None:
    input_dir = tmp_path / "input"
    write_synthetic_quant_input(input_dir)
    survey = pd.read_csv(input_dir / "survey.csv").drop(columns=["phase"])
    survey.to_csv(input_dir / "survey.csv", index=False)

    with pytest.raises(ValueError, match="survey.*missing required columns.*phase"):
        run_quant_analysis(
            input_dir,
            Path("config/quant_config.template.toml"),
            Path("config/expected_inventory.template.toml"),
            tmp_path / "private",
            tmp_path / "public",
        )


def test_run_quant_analysis_fails_fast_on_empty_input_tables(tmp_path) -> None:
    input_dir = tmp_path / "input"
    write_synthetic_quant_input(input_dir)
    pd.read_csv(input_dir / "grades.csv").iloc[0:0].to_csv(input_dir / "grades.csv", index=False)

    with pytest.raises(ValueError, match="grades.*empty"):
        run_quant_analysis(
            input_dir,
            Path("config/quant_config.template.toml"),
            Path("config/expected_inventory.template.toml"),
            tmp_path / "private",
            tmp_path / "public",
        )


def test_run_quant_analysis_reports_malformed_prompt_rows_before_modeling(tmp_path) -> None:
    input_dir = tmp_path / "input"
    write_synthetic_quant_input(input_dir)
    prompts = pd.read_csv(input_dir / "prompts.csv")
    prompts["assignment"] = prompts["assignment"].astype(object)
    prompts["prompt_score"] = prompts["prompt_score"].astype(object)
    prompts.loc[0, "assignment"] = "first"
    prompts.loc[1, "prompt_score"] = "not numeric"
    prompts.to_csv(input_dir / "prompts.csv", index=False)

    with pytest.raises(ValueError, match="prompts.*assignment.*first.*prompt_score.*not numeric"):
        run_quant_analysis(
            input_dir,
            Path("config/quant_config.template.toml"),
            Path("config/expected_inventory.template.toml"),
            tmp_path / "private",
            tmp_path / "public",
        )


def test_score_reliability_items_uses_the_five_point_reverse_code() -> None:
    config = QuantConfig.default()
    pre = pd.DataFrame(
        {
            "control_1": [1, 2, 3, 4],
            "control_reverse": [5, 4, 3, 2],
        }
    )

    existing, scored = _score_reliability_items(pre, "locus_of_control", ["control_1", "control_reverse"], config)

    assert existing == ["control_1", "control_reverse"]
    assert scored["control_reverse"].tolist() == [1.0, 2.0, 3.0, 4.0]


def test_run_quant_analysis_preserves_previous_public_outputs_when_publication_fails(tmp_path, monkeypatch) -> None:
    input_dir = tmp_path / "input"
    public_dir = tmp_path / "public"
    write_synthetic_quant_input(input_dir)
    public_dir.mkdir()
    previous_table = public_dir / "table_data_verification.csv"
    previous_report = public_dir / "quantitative_report.md"
    previous_table.write_text("previous table\n", encoding="utf-8")
    previous_report.write_text("previous report\n", encoding="utf-8")

    def fail_report(*args, **kwargs):
        raise RuntimeError("report publication failed")

    monkeypatch.setattr("genai_literacy_trial.quant_pipeline.write_quantitative_report", fail_report)

    with pytest.raises(RuntimeError, match="report publication failed"):
        run_quant_analysis(
            input_dir,
            Path("config/quant_config.template.toml"),
            Path("config/expected_inventory.template.toml"),
            tmp_path / "private",
            public_dir,
        )

    assert previous_table.read_text(encoding="utf-8") == "previous table\n"
    assert previous_report.read_text(encoding="utf-8") == "previous report\n"
