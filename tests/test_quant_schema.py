from __future__ import annotations

from pathlib import Path
from typing import get_type_hints

from genai_literacy_trial.quant_schema import (
    NORMALIZED_POST_LABEL,
    NORMALIZED_PRE_LABEL,
    PARTICIPANT_KEY_COLUMN,
    PRIVATE_OUTPUT_DIR_KEY,
    PUBLIC_OUTPUT_DIR_KEY,
    QUANT_TABLE_OUTPUT_FORMAT,
    REQUIRED_QUANT_TABLES,
    BootstrapSummary,
    LearningOutcomeTables,
    PromptSensitivityTables,
    QuantPathMap,
    QuantTableMap,
    StatisticalTestResult,
    TrainingEffectTables,
)


def test_internal_quant_schema_constants_are_explicit() -> None:
    assert PARTICIPANT_KEY_COLUMN == "participant_key"
    assert NORMALIZED_PRE_LABEL == "pre"
    assert NORMALIZED_POST_LABEL == "post"


def test_quant_output_path_keys_are_explicit() -> None:
    assert PUBLIC_OUTPUT_DIR_KEY == "public_output_dir"
    assert PRIVATE_OUTPUT_DIR_KEY == "private_output_dir"


def test_required_quant_tables_are_public_output_contract() -> None:
    assert REQUIRED_QUANT_TABLES == (
        "table_data_verification",
        "table_missingness_prompt_by_group_assignment",
        "table_baseline_balance",
        "table_prompt_trajectory_model",
        "table_prompt_trajectory_estimated_means",
        "table_participant_training_contrasts",
        "table_participant_training_tests",
        "table_learning_outcome_models",
        "table_prompt_grade_correlations",
        "table_calibration_models",
        "table_survey_reliability",
        "table_prepost_survey_change",
        "table_small_sample_sensitivity",
        "table_perceived_usefulness_models",
        "table_complete_case_diagnostics",
        "table_prior_use_mapping",
        "table_scored_assignment_distribution_by_group",
        "table_prompt_sensitivity_min3_assignments",
        "table_prompt_sensitivity_all4_assignments",
    )


def test_quant_table_output_format_is_public_output_contract() -> None:
    assert QUANT_TABLE_OUTPUT_FORMAT == "csv"


def test_quant_table_map_type_alias_is_importable() -> None:
    tables: QuantTableMap = {}

    assert tables == {}


def test_quant_path_map_type_alias_is_importable() -> None:
    paths: QuantPathMap = {}

    assert paths == {}


def test_quant_path_map_declares_required_output_paths() -> None:
    assert get_type_hints(QuantPathMap) == {
        PUBLIC_OUTPUT_DIR_KEY: Path,
        PRIVATE_OUTPUT_DIR_KEY: Path,
    }


def test_quant_model_table_maps_declare_required_tables() -> None:
    assert set(get_type_hints(TrainingEffectTables)) == {"summary", "tests", "contrasts"}
    assert set(get_type_hints(LearningOutcomeTables)) == {"correlations", "models"}
    assert set(get_type_hints(PromptSensitivityTables)) == {
        "scored_assignment_distribution",
        "min3_assignments",
        "all4_assignments",
    }


def test_bootstrap_summary_declares_statistical_result_shape() -> None:
    assert get_type_hints(BootstrapSummary) == {
        "mean": float,
        "ci_low": float,
        "ci_high": float,
        "n": int,
    }


def test_statistical_test_result_declares_common_test_shape() -> None:
    assert get_type_hints(StatisticalTestResult) == {
        "statistic": float,
        "p_value": float,
    }
