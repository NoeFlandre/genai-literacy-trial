from __future__ import annotations

import pandas as pd

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
    _read_input,
    _merge_pre_composites,
)
from genai_literacy_trial.quant_figures import FIGURE_FORMATS
from genai_literacy_trial.quant_report import QUANTITATIVE_REPORT_FILENAME
from genai_literacy_trial.quant_preprocess import compute_survey_composites, participant_key
from genai_literacy_trial.quant_schema import PARTICIPANT_KEY_COLUMN, QUANT_TABLE_OUTPUT_FORMAT


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
