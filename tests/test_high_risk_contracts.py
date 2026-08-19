from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import genai_literacy_trial.quant_models as quant_models
from genai_literacy_trial.quant_config import QuantConfig
from genai_literacy_trial.quant_models import fit_prompt_trajectory_model, prepost_survey_change_models
from genai_literacy_trial.quant_pipeline import _read_input, _validate_quant_input_frames
from genai_literacy_trial.quant_preprocess import build_participant_table, prepare_retained_survey, suppress_small_cells
from genai_literacy_trial.quant_stats import hedges_g, welch_anova
from tests.quant_fixtures import synthetic_quant_frames


def test_conflicting_grade_rows_fail_before_duplicate_collapse() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    conflicting = grades.loc[grades["participant_id"] == "p02"].copy()
    conflicting["final_grade"] = "C"
    grades = pd.concat([grades, conflicting], ignore_index=True)

    retained, _ = prepare_retained_survey(survey, config)

    with pytest.raises(ValueError, match="Conflicting grade rows.*final_grade"):
        build_participant_table(retained, grades, prompts, config)


def test_small_cell_suppression_keeps_groups_separate() -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender", "gender", "gender"],
            "group": ["A", "B", "A"],
            "gender": ["rare_a", "rare_b", "large_a"],
            "n": [1, 2, 6],
        }
    )

    suppressed = suppress_small_cells(table, category_col="gender", min_count=5)
    collapsed = suppressed[suppressed["gender"] == "Other/suppressed"]

    assert collapsed["group"].tolist() == ["A", "B"]
    assert collapsed["n"].tolist() == ["suppressed", "suppressed"]
    assert suppressed.loc[suppressed["gender"] == "large_a", "n"].iloc[0] == 6


def test_small_cell_suppression_preserves_default_boundary_and_contiguous_index() -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender"],
            "group": ["A"],
            "gender": ["large_enough"],
            "n": [5],
            "note": ["keep"],
        }
    )

    table.index = [10]
    suppressed = suppress_small_cells(table, category_col="gender")

    pd.testing.assert_frame_equal(suppressed, table)


def test_small_cell_suppression_infers_the_category_column() -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender"],
            "group": ["A"],
            "gender": ["rare"],
            "n": [1],
        }
    )

    suppressed = suppress_small_cells(table)

    assert suppressed.loc[0, "gender"] == "Other/suppressed"
    assert suppressed.loc[0, "n"] == "suppressed"


@pytest.mark.parametrize(
    "columns",
    [
        ["group", "gender", "n", "metric"],
        ["metric", "gender", "n", "group"],
    ],
)
def test_small_cell_suppression_inference_excludes_contract_columns(columns: list[str]) -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender"],
            "group": ["A"],
            "gender": ["rare"],
            "n": [1],
        }
    )[columns]

    suppressed = suppress_small_cells(table)

    assert suppressed.loc[0, "gender"] == "Other/suppressed"
    assert suppressed.loc[0, "n"] == "suppressed"


def test_small_cell_suppression_groups_by_metric_and_group() -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender", "gender", "age", "age"],
            "group": ["A", "B", "A", "B"],
            "category": ["rare"] * 4,
            "n": [1] * 4,
        }
    )

    suppressed = suppress_small_cells(table, category_col="category", min_count=5)

    assert len(suppressed) == 4
    assert suppressed[["metric", "group"]].drop_duplicates().shape[0] == 4


def test_small_cell_suppression_coerces_bad_counts_and_keeps_group_order() -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender", "gender", "gender"],
            "group": ["B", "A", "C"],
            "gender": ["rare_b", "rare_a", "safe"],
            "n": ["not-a-count", np.nan, 6],
            "note": ["discard_b", "discard_a", "keep"],
        }
    )

    suppressed = suppress_small_cells(table, category_col="gender", min_count=1)

    assert suppressed["group"].tolist() == ["C", "A", "B"]
    assert suppressed["gender"].tolist() == ["safe", "Other/suppressed", "Other/suppressed"]
    assert suppressed["n"].tolist() == [6, "suppressed", "suppressed"]
    assert suppressed["note"].tolist() == ["keep", "", ""]
    assert suppressed.index.tolist() == [0, 1, 2]


def test_small_cell_suppression_retains_missing_group_cells() -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender", "gender"],
            "group": ["A", None],
            "gender": ["rare_a", "rare_missing_group"],
            "n": [1, 1],
        }
    )

    suppressed = suppress_small_cells(table, category_col="gender", min_count=5)

    assert len(suppressed) == 2
    assert suppressed["group"].notna().sum() == 1
    assert suppressed["group"].isna().sum() == 1


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("assignment", 1.5, "noninteger assignment"),
        ("prompt_score", np.inf, "nonfinite prompt_score"),
    ],
)
def test_quant_input_validation_rejects_non_scientific_numeric_values(column: str, value: object, message: str) -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    if column == "assignment":
        prompts[column] = prompts[column].astype(float)
    prompts.loc[0, column] = value

    with pytest.raises(ValueError, match=message):
        _validate_quant_input_frames(survey, grades, prompts, config)


def test_read_input_accepts_compatibility_name_and_reports_missing_input(tmp_path) -> None:
    compatibility = tmp_path / "public_cli_input_survey.csv"
    compatibility.write_text("value\n1\n", encoding="utf-8")

    observed = _read_input(tmp_path, "survey")

    pd.testing.assert_frame_equal(observed, pd.DataFrame({"value": [1]}))
    with pytest.raises(FileNotFoundError, match="Missing grades.csv or grades.xlsx"):
        _read_input(tmp_path, "grades")


def test_read_input_reports_the_dataset_name_for_empty_compatibility_input(tmp_path) -> None:
    (tmp_path / "public_cli_input_grades.csv").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Input dataset grades is empty"):
        _read_input(tmp_path, "grades")


def test_read_input_prefers_a_primary_file_and_rejects_multiple_primary_formats(tmp_path) -> None:
    frame = pd.DataFrame({"value": [1, 2]})
    frame.to_csv(tmp_path / "survey.csv", index=False)

    observed = _read_input(tmp_path, "survey")

    pd.testing.assert_frame_equal(observed, frame)
    frame.to_excel(tmp_path / "survey.xlsx", index=False)
    with pytest.raises(ValueError, match="Multiple input files found for survey") as exc_info:
        _read_input(tmp_path, "survey")
    assert str(exc_info.value) == (
        "Multiple input files found for survey: survey.csv, survey.xlsx; keep exactly one primary input file"
    )


def test_quant_input_validation_accepts_valid_synthetic_frames() -> None:
    survey, grades, prompts = synthetic_quant_frames()

    _validate_quant_input_frames(survey, grades, prompts, QuantConfig.default())


def test_quant_input_validation_reports_missing_and_malformed_prompt_columns() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()

    missing_score = prompts.drop(columns=[config.columns.assignment, config.columns.prompt_score])
    with pytest.raises(ValueError, match="prompts is missing required columns: assignment, prompt_score"):
        _validate_quant_input_frames(survey, grades, missing_score, config)

    malformed = prompts.copy()
    malformed[config.columns.assignment] = malformed[config.columns.assignment].astype(object)
    malformed.loc[0, config.columns.assignment] = "not-a-number"
    with pytest.raises(ValueError, match="nonnumeric assignment values: not-a-number"):
        _validate_quant_input_frames(survey, grades, malformed, config)

    malformed_score = prompts.copy()
    malformed_score[config.columns.prompt_score] = malformed_score[config.columns.prompt_score].astype(object)
    malformed_score.loc[0, config.columns.prompt_score] = "not-a-score"
    with pytest.raises(ValueError, match="nonnumeric prompt_score values: not-a-score"):
        _validate_quant_input_frames(survey, grades, malformed_score, config)


def test_quant_input_validation_does_not_stop_after_an_earlier_frame_issue() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    survey = survey.drop(columns=[config.columns.phase])
    prompts[config.columns.assignment] = prompts[config.columns.assignment].astype(float)
    prompts.loc[0, config.columns.assignment] = 1.5

    with pytest.raises(ValueError) as exc_info:
        _validate_quant_input_frames(survey, grades, prompts, config)

    assert str(exc_info.value) == (
        "Invalid quantitative inputs: survey is missing required columns: phase; "
        "prompts contains noninteger assignment values: 1.5"
    )


def test_quant_input_validation_reports_all_numeric_issues_with_stable_message() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    prompts[config.columns.assignment] = prompts[config.columns.assignment].astype(float)
    prompts.loc[0, config.columns.assignment] = 1.5
    prompts.loc[1, config.columns.prompt_score] = np.inf

    with pytest.raises(ValueError) as exc_info:
        _validate_quant_input_frames(survey, grades, prompts, config)

    assert str(exc_info.value) == (
        "Invalid quantitative inputs: prompts contains noninteger assignment values: 1.5; "
        "prompts contains nonfinite prompt_score values: inf"
    )


def test_welch_anova_uses_defined_fallback_when_one_group_has_zero_variance() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "value": [1.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )

    result = welch_anova(frame, "group", "value")

    assert np.isfinite(result["statistic"])
    assert np.isfinite(result["p_value"])


def test_welch_anova_computes_two_group_result() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )

    result = welch_anova(frame, "group", "value")

    assert np.isclose(result["statistic"], 8.0)
    assert np.isfinite(result["p_value"])


def test_hedges_g_returns_zero_for_identical_constant_groups() -> None:
    result = hedges_g(pd.Series([2.0, 2.0]), pd.Series([2.0, 2.0]), n_boot=50)

    assert result == {"estimate": 0.0, "ci_low": 0.0, "ci_high": 0.0}


def test_prompt_trajectory_uses_clustered_ols_when_mixedlm_fails(monkeypatch) -> None:
    _, _, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(synthetic_quant_frames()[0], config)
    participant = build_participant_table(retained, synthetic_quant_frames()[1], prompts, config)
    from genai_literacy_trial.quant_preprocess import build_assignment_prompt_table

    assignment = build_assignment_prompt_table(prompts, participant, config)

    def fail_mixedlm(*_args: object, **_kwargs: object) -> None:
        raise ValueError("forced mixed model failure")

    monkeypatch.setattr(quant_models.smf, "mixedlm", fail_mixedlm)

    result = fit_prompt_trajectory_model(assignment)

    assert result.method == "clustered_ols_fallback"
    assert result.tidy["warning"].str.contains("forced mixed model failure").all()


def test_prepost_models_reject_composites_without_group() -> None:
    composites = pd.DataFrame(
        {
            "participant_key": ["p1", "p1"],
            "phase": ["pre", "post"],
            "perceived_usefulness": [2.0, 3.0],
        }
    )

    with pytest.raises(ValueError, match="require group"):
        prepost_survey_change_models(composites)
