from __future__ import annotations

import inspect
import math
from typing import cast

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

import genai_literacy_trial.quant_models as quant_models
from genai_literacy_trial.quant_config import QuantConfig
from genai_literacy_trial.quant_models import (
    CALIBRATION_DIMENSIONS,
    calibration_models,
    complete_case_diagnostics,
    fit_prompt_trajectory_model,
    learning_outcome_models,
    model_based_learning_prediction_table,
    prompt_missingness_sensitivity,
    participant_level_training_effect,
    perceived_usefulness_models,
    prepost_survey_change_models,
)
from genai_literacy_trial.quant_preprocess import (
    build_assignment_prompt_table,
    build_participant_table,
    compute_survey_composites,
    prepare_retained_survey,
)
from genai_literacy_trial.quant_schema import NORMALIZED_POST_LABEL, NORMALIZED_PRE_LABEL, PARTICIPANT_KEY_COLUMN
from tests.quant_fixtures import synthetic_quant_frames


def _prepared():
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    composites = compute_survey_composites(retained, config)
    pre = composites[composites["phase"] == NORMALIZED_PRE_LABEL].drop(columns=["phase"])
    participant = participant.merge(pre, on=PARTICIPANT_KEY_COLUMN, how="left")
    assignment = build_assignment_prompt_table(prompts, participant, config)
    return participant, assignment, composites


def test_canonical_group_prefers_group_x_and_drops_group_y() -> None:
    frame = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1"],
            "group_x": ["A"],
            "group_y": ["stale"],
            "value": [1.0],
        }
    )

    normalized = quant_models._canonical_group(frame)

    assert normalized.columns.tolist() == [PARTICIPANT_KEY_COLUMN, "group", "value"]
    assert normalized.loc[0, "group"] == "A"


def test_canonical_group_does_not_replace_an_existing_group() -> None:
    frame = pd.DataFrame({"group": ["A"], "group_x": ["wrong"], "group_y": ["stale"]})

    normalized = quant_models._canonical_group(frame)

    assert normalized.columns.tolist() == ["group", "group_x"]
    assert normalized.loc[0, "group"] == "A"


def test_tidy_result_preserves_model_output_contract_for_missing_p_values() -> None:
    class FakeResult:
        params = pd.Series({"x": 2.0, "y": -1.0})
        pvalues = pd.Series({"x": 0.25})
        rsquared = 0.8
        rsquared_adj = 0.7

        @staticmethod
        def conf_int() -> pd.DataFrame:
            return pd.DataFrame({0: [1.0, -2.0], 1: [3.0, 0.0]}, index=["x", "y"])

    tidy = quant_models._tidy_result(FakeResult(), "demo", n=12, adjusted_r2=0.6)

    expected = pd.DataFrame(
        {
            "model": ["demo", "demo"],
            "term": ["x", "y"],
            "estimate": [2.0, -1.0],
            "ci_low": [1.0, -2.0],
            "ci_high": [3.0, 0.0],
            "p_value": [0.25, math.nan],
            "n": [12, 12],
            "r_squared": [0.8, 0.8],
            "adj_r_squared": [0.6, 0.6],
            "stability": ["exploratory_unstable", "exploratory_unstable"],
        }
    )
    assert_frame_equal(tidy, expected)


def test_tidy_result_uses_adjusted_r_squared_and_boundary_stability() -> None:
    class FakeResult:
        params = pd.Series({"x": 2.0})
        pvalues = pd.Series({"x": 0.25})
        rsquared = 0.8
        rsquared_adj = 0.7

        @staticmethod
        def conf_int() -> pd.DataFrame:
            return pd.DataFrame({0: [1.0], 1: [3.0]}, index=["x"])

    result_29 = quant_models._tidy_result(FakeResult(), "demo", n=29)
    result_30 = quant_models._tidy_result(FakeResult(), "demo", n=30)
    result_with_model_adj = quant_models._tidy_result(FakeResult(), "demo", n=30, adjusted_r2=None)

    assert result_29.loc[0, "stability"] == "exploratory_unstable"
    assert result_30.loc[0, "stability"] == "standard"
    assert result_with_model_adj.loc[0, "adj_r_squared"] == 0.7


def test_ensure_prior_use_score_maps_only_when_public_score_is_absent() -> None:
    frame = pd.DataFrame({"prior_chatgpt_use": ["1", "not-a-number"]})
    mapped = quant_models._ensure_prior_use_score(frame)
    existing = quant_models._ensure_prior_use_score(frame.assign(prior_chatgpt_use_score=[7.0, 8.0]))

    assert mapped["prior_chatgpt_use_score"].iloc[0] == 1.0
    assert pd.isna(mapped["prior_chatgpt_use_score"].iloc[1])
    assert existing["prior_chatgpt_use_score"].tolist() == [7.0, 8.0]


def test_complete_cases_only_drops_rows_missing_required_columns() -> None:
    frame = pd.DataFrame({"required": [1.0, 2.0], "unrelated": [None, 3.0]})

    complete = quant_models._complete_cases(frame, ["required"])

    assert complete.index.tolist() == [0, 1]


def test_standardized_effect_helpers_preserve_ci_scaling() -> None:
    work = pd.DataFrame({"x": [1.0, 3.0], "y": [2.0, 6.0]})
    tidy = pd.DataFrame(
        {
            "term": ["x"],
            "estimate": [2.0],
            "ci_low": [1.0],
            "ci_high": [3.0],
        }
    )

    scaled = quant_models._add_standardized_effect(
        tidy,
        work,
        "x",
        "y",
        from_standardized_predictor=False,
        include_ci=True,
    )

    assert scaled.loc[0, "std_beta"] == 1.0
    assert scaled.loc[0, "std_ci_low"] == 0.5
    assert scaled.loc[0, "std_ci_high"] == 1.5
    assert quant_models._standardized_effect_scale(work, "x", "y", False) == 0.5


def test_finite_standard_deviation_rejects_zero_and_nonfinite_values() -> None:
    assert quant_models._finite_standard_deviation(pd.Series([1.0, 1.0])) is None
    assert quant_models._finite_standard_deviation(pd.Series([1.0, np.inf])) is None
    assert quant_models._finite_standard_deviation(pd.Series([1.0, 3.0])) == np.sqrt(2)


def test_model_diagnostics_counts_missing_named_survey_composite() -> None:
    frame = pd.DataFrame({"survey": [1.0, None], "group": ["A", "B"]})

    result = quant_models._model_diagnostics(frame, "survey_model", ["survey"], "survey")

    assert result["lost_survey_composite"] == 1


def test_fit_prompt_trajectory_model_reports_clustered_ols_fallback(monkeypatch) -> None:
    observed_assignments: list[object] = []
    assignment = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p2", "p2"],
            "group": ["A", "A", "B", "B"],
            "assignment": [1.0, 2.0, 1.0, 2.0],
            "prompt_score": [2.0, 3.0, 4.0, 5.0],
            "ignored": [None, None, None, None],
        }
    )

    class FakeMixedResult:
        converged = False

    class FakeMixedModel:
        @staticmethod
        def fit(*, reml: bool, disp: bool) -> FakeMixedResult:
            assert reml is False
            assert disp is False
            return FakeMixedResult()

    class FakeOlsResult:
        pass

    class FakeOlsModel:
        @staticmethod
        def fit(*, cov_type: str, cov_kwds: dict[str, object]) -> FakeOlsResult:
            assert cov_type == "cluster"
            assert list(cov_kwds) == ["groups"]
            return FakeOlsResult()

    def fake_mixedlm(*args, **kwargs):
        observed_assignments.extend(kwargs["data"]["assignment"].tolist())
        return FakeMixedModel()

    monkeypatch.setattr(quant_models.smf, "mixedlm", fake_mixedlm)
    monkeypatch.setattr(quant_models.smf, "ols", lambda *args, **kwargs: FakeOlsModel())
    monkeypatch.setattr(
        quant_models,
        "_tidy_result",
        lambda _result, model_name, n: pd.DataFrame(
            {"model": [model_name], "term": ["Intercept"], "n": [n]}
        ),
    )

    summary = fit_prompt_trajectory_model(assignment)

    assert summary.formula == "prompt_score ~ group * C(assignment)"
    assert summary.n_observations == 4
    assert summary.n_participants == 2
    assert summary.method == "clustered_ols_fallback"
    assert summary.tidy.loc[0, "model"] == "prompt_trajectory_clustered_ols"
    assert summary.tidy.loc[0, "n"] == 4
    assert summary.tidy.loc[0, "warning"] == "MixedLM failed; used clustered OLS fallback: MixedLM did not converge"
    assert observed_assignments == ["1", "2", "1", "2"]


def test_fit_prompt_trajectory_treats_missing_converged_as_converged(monkeypatch) -> None:
    assignment = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p2"],
            "group": ["A", "B"],
            "assignment": [1, 1],
            "prompt_score": [2.0, 3.0],
        }
    )

    class ResultWithoutConverged:
        pass

    class MixedModel:
        @staticmethod
        def fit(*, reml: bool, disp: bool) -> ResultWithoutConverged:
            return ResultWithoutConverged()

    monkeypatch.setattr(quant_models.smf, "mixedlm", lambda *_args, **_kwargs: MixedModel())
    monkeypatch.setattr(quant_models.smf, "ols", lambda *_args, **_kwargs: pytest.fail("unexpected OLS fallback"))
    monkeypatch.setattr(
        quant_models,
        "_tidy_result",
        lambda _result, model_name, n: pd.DataFrame({"model": [model_name], "n": [n]}),
    )

    summary = quant_models.fit_prompt_trajectory_model(assignment)

    assert summary.method == "mixedlm"
    assert summary.tidy.loc[0, "model"] == "prompt_trajectory_mixedlm"


def test_model_diagnostics_reports_each_required_missingness_dimension() -> None:
    frame = pd.DataFrame(
        {
            "final_points": [10.0, None, 12.0],
            "midterm_points": [8.0, 9.0, None],
            "mean_prompt_score": [4.0, None, 3.0],
            "prior_chatgpt_use_score": [2.0, 3.0, None],
            "perceived_usefulness": [1.0, 2.0, None],
            "group": ["A", None, "B"],
            "grade_change": [2.0, None, 1.0],
        }
    )

    row = quant_models._model_diagnostics(
        frame,
        "grade_model",
        ["grade_change", "perceived_usefulness", "group", "prior_chatgpt_use_score"],
        "perceived_usefulness",
    )

    assert row == {
        "model": "grade_model",
        "starting_n": 3,
        "final_n": 1,
        "loss_type": "marginal_non_additive",
        "lost_final_grade": 1,
        "lost_midterm_grade": 1,
        "lost_mean_prompt_score": 0,
        "lost_prior_chatgpt_use_score": 1,
        "lost_survey_composite": 1,
        "lost_group": 1,
    }


def test_complete_case_diagnostics_reports_exact_model_rows() -> None:
    participant = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p2", "p3"],
            "group": ["A", None, "B"],
            "mean_prompt_score": [4.0, 2.0, None],
            "midterm_points": [8.0, 4.0, None],
            "final_points": [10.0, None, 6.0],
            "prior_chatgpt_use_score": [2.0, 3.0, None],
            "perceived_usefulness": [1.0, 2.0, 3.0],
            "trust": [1.0, 2.0, 3.0],
        }
    )

    diagnostics = complete_case_diagnostics(participant)

    expected = pd.DataFrame(
        {
            "model": [
                "prompt_quality_academic_predictors",
                "perceived_usefulness_final_points",
                "perceived_usefulness_grade_change",
                "calibration_trust",
                "calibration_perceived_usefulness",
            ],
            "starting_n": [3, 3, 3, 3, 3],
            "final_n": [1, 1, 1, 1, 1],
            "loss_type": ["marginal_non_additive"] * 5,
            "lost_final_grade": [0, 1, 1, 0, 0],
            "lost_midterm_grade": [1, 1, 1, 0, 0],
            "lost_mean_prompt_score": [1, 0, 0, 1, 1],
            "lost_prior_chatgpt_use_score": [1, 1, 1, 1, 1],
            "lost_survey_composite": [0, 0, 0, 0, 0],
            "lost_group": [1, 1, 1, 1, 1],
        }
    )
    assert_frame_equal(diagnostics, expected)


def test_calibration_dimensions_are_shared_across_model_outputs() -> None:
    participant, _, _ = _prepared()

    calibration = calibration_models(participant)
    diagnostics = complete_case_diagnostics(participant)

    assert tuple(calibration["dimension"]) == CALIBRATION_DIMENSIONS
    assert tuple(diagnostics.query("model.str.startswith('calibration_')")["model"].str.removeprefix("calibration_")) == CALIBRATION_DIMENSIONS


def test_models_use_participant_n_and_assignment_categorical_formula() -> None:
    participant, assignment, _ = _prepared()

    trajectory = fit_prompt_trajectory_model(assignment)
    training = participant_level_training_effect(participant)
    learning = learning_outcome_models(participant)

    assert "C(assignment)" in trajectory.formula
    assert trajectory.n_observations == int(assignment["prompt_score"].notna().sum())
    assert training["summary"]["n_participants"].iloc[0] == len(participant)
    assert set(learning["correlations"]["n"]) == {len(participant)}


def test_learning_outcome_model_schema_and_stable_values() -> None:
    participant, _, _ = _prepared()

    outcome = learning_outcome_models(participant)

    assert set(outcome) == {"correlations", "models"}
    assert set(outcome["correlations"].columns) == {
        "metric",
        "method",
        "correlation",
        "p_value",
        "ci_low",
        "ci_high",
        "n",
    }
    assert set(outcome["models"].columns) >= {
        "model",
        "term",
        "estimate",
        "ci_low",
        "ci_high",
        "p_value",
        "n",
        "r_squared",
        "adj_r_squared",
        "stability",
        "std_beta",
    }
    assert outcome["correlations"][["metric", "method"]].to_dict("records") == [
        {"metric": "mean_prompt_score vs midterm_points", "method": "pearson"},
        {"metric": "mean_prompt_score vs midterm_points", "method": "spearman"},
        {"metric": "mean_prompt_score vs final_points", "method": "pearson"},
        {"metric": "mean_prompt_score vs final_points", "method": "spearman"},
    ]

    adjusted = outcome["models"]
    assert set(adjusted["model"]) == {"prompt_quality_academic_predictors"}
    assert "final_points" not in set(adjusted["model"])
    assert "grade_change" not in set(adjusted["model"])
    assert "final_points" not in set(adjusted["term"])

    midterm = adjusted.query("term == 'midterm_points'").iloc[0]
    prior = adjusted.query("term == 'prior_chatgpt_use_score'").iloc[0]

    assert midterm["n"] == len(participant)
    assert prior["n"] == len(participant)
    assert math.isclose(float(midterm["estimate"]), -4.033826577618834e-15, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(midterm["std_beta"]), -2.711489600395708e-15, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(prior["estimate"]), 3.3306690738754696e-16, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(prior["std_beta"]), 1.3985901057127095e-15, rel_tol=1e-12, abs_tol=1e-12)
    assert not math.isclose(float(midterm["estimate"]), float(midterm["std_beta"]))


def test_calibration_and_perceived_usefulness_models_apply_fdr_and_report_n() -> None:
    participant, _, _ = _prepared()

    calibration = calibration_models(participant)
    usefulness = perceived_usefulness_models(participant)

    assert "fdr_p_value" in calibration.columns
    assert calibration["n"].min() == len(participant)
    assert set(usefulness["model"]) == {"final_points", "grade_change"}
    assert usefulness["n"].min() == len(participant)


def test_mean_difference_ci_has_stable_seeded_and_empty_contracts() -> None:
    result = quant_models._mean_difference_ci(pd.Series([1.0, 2.0, 3.0]), pd.Series([2.0, 4.0]), seed=123, n_boot=500)
    repeat = quant_models._mean_difference_ci(pd.Series([1.0, 2.0, 3.0]), pd.Series([2.0, 4.0]), seed=123, n_boot=500)
    empty = quant_models._mean_difference_ci(pd.Series(dtype=float), pd.Series([1.0]), seed=123, n_boot=10)

    assert inspect.signature(quant_models._mean_difference_ci).parameters["n_boot"].default == 1000
    assert result == {
        "mean_difference": -1.0,
        "mean_difference_ci_low": -2.666666666666667,
        "mean_difference_ci_high": 0.6666666666666665,
    }
    assert result == repeat
    assert set(empty) == {"mean_difference", "mean_difference_ci_low", "mean_difference_ci_high"}
    assert pd.isna(empty["mean_difference"])
    assert pd.isna(empty["mean_difference_ci_low"])
    assert pd.isna(empty["mean_difference_ci_high"])


def test_contrast_rows_handles_singleton_comparison_groups() -> None:
    frame = pd.DataFrame(
        {
            "group": ["C", "C", "A", "A", "B"],
            "mean_prompt_score": [4.0, 5.0, 1.0, 2.0, 3.0],
        }
    )

    rows = quant_models._contrast_rows(frame, "mean_prompt_score")
    by_contrast = {row["contrast"]: row for row in rows}

    assert np.isfinite(by_contrast["C vs B"]["p_value"])
    assert by_contrast["C vs B"]["n"] == 3


def test_contrast_rows_uses_fixed_bootstrap_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int | None] = []

    def fake_hedges(_a: pd.Series, _b: pd.Series, *, n_boot: int = 10000):
        calls.append(n_boot)
        return {"estimate": 0.0, "ci_low": 0.0, "ci_high": 0.0}

    monkeypatch.setattr(quant_models, "hedges_g", fake_hedges)
    monkeypatch.setattr(
        quant_models,
        "_mean_difference_ci",
        lambda _a, _b: {
            "mean_difference": 0.0,
            "mean_difference_ci_low": 0.0,
            "mean_difference_ci_high": 0.0,
        },
    )

    quant_models._contrast_rows(
        pd.DataFrame({"group": ["A", "B", "C"], "mean_prompt_score": [1.0, 2.0, 3.0]}),
        "mean_prompt_score",
    )

    assert calls == [1000, 1000, 1000, 1000]


def test_perceived_usefulness_and_calibration_model_outputs_stable_and_schema() -> None:
    participant, _, _ = _prepared()

    usefulness = perceived_usefulness_models(participant)
    calibration = calibration_models(participant)

    assert set(usefulness.columns) == {
        "model",
        "term",
        "estimate",
        "ci_low",
        "ci_high",
        "p_value",
        "n",
        "r_squared",
        "adj_r_squared",
        "stability",
        "std_beta",
        "std_ci_low",
        "std_ci_high",
    }
    assert set(calibration.columns) == {
        "model",
        "term",
        "estimate",
        "ci_low",
        "ci_high",
        "p_value",
        "n",
        "r_squared",
        "adj_r_squared",
        "stability",
        "std_beta",
        "std_ci_low",
        "std_ci_high",
        "dimension",
        "fdr_p_value",
    }

    final_points = usefulness.query("model == 'final_points' and term == 'perceived_usefulness_z'").iloc[0]
    grade_change = usefulness.query("model == 'grade_change' and term == 'perceived_usefulness_z'").iloc[0]
    trust = calibration.query("dimension == 'trust'").iloc[0]

    assert final_points["n"] == len(participant)
    assert grade_change["n"] == len(participant)
    assert trust["n"] == len(participant)
    assert all(calibration["n"] == len(participant))

    assert math.isclose(float(final_points["estimate"]), -0.18795701932320813, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(final_points["std_beta"]), -0.6265233977440269, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(trust["estimate"]), 0.0, abs_tol=1e-12)
    assert math.isclose(float(trust["std_beta"]), 0.0, abs_tol=1e-12)
    assert not math.isclose(float(final_points["estimate"]), float(final_points["std_beta"]))
    assert not math.isclose(float(grade_change["estimate"]), float(grade_change["std_beta"]))


def test_standardized_betas_use_complete_case_model_sample() -> None:
    participant, _, _ = _prepared()
    participant.loc[0, "prior_chatgpt_use_score"] = None

    calibration = calibration_models(participant)
    usefulness = perceived_usefulness_models(participant)

    assert calibration["n"].min() == len(participant) - 1
    assert usefulness["n"].min() == len(participant) - 1


def test_training_contrasts_report_p_values() -> None:
    participant, _, _ = _prepared()

    training = participant_level_training_effect(participant)

    assert training["contrasts"]["p_value"].notna().all()


def test_prompt_missingness_sensitivity_outputs_min3_and_all4() -> None:
    participant, _, _ = _prepared()

    sensitivity = prompt_missingness_sensitivity(participant, min_all4_n=30)

    assert {"scored_assignment_distribution", "min3_assignments", "all4_assignments"} <= set(sensitivity)
    assert sensitivity["all4_assignments"]["status"].iloc[0] == "not_run_small_n"


def test_prompt_missingness_sensitivity_schema_and_n() -> None:
    participant, _, _ = _prepared()

    sensitivity = prompt_missingness_sensitivity(participant, min_all4_n=30)

    assert set(sensitivity) == {"scored_assignment_distribution", "min3_assignments", "all4_assignments"}
    assert set(sensitivity["scored_assignment_distribution"].columns) == {"group", "scored_assignments", "n"}
    assert set(sensitivity["min3_assignments"].columns) == {
        "model",
        "term",
        "estimate",
        "ci_low",
        "ci_high",
        "p_value",
        "n",
        "r_squared",
        "adj_r_squared",
        "stability",
        "status",
    }
    assert set(sensitivity["all4_assignments"].columns) == {"model", "status", "n"}

    assert (sensitivity["min3_assignments"]["status"] == "run").all()
    assert all(sensitivity["min3_assignments"]["n"] == len(participant))
    assert sensitivity["all4_assignments"]["n"].iloc[0] == 4
    assert sensitivity["all4_assignments"]["status"].iloc[0] == "not_run_small_n"


def test_prompt_missingness_sensitivity_runs_all4_at_threshold_and_has_stable_default() -> None:
    participant, _, _ = _prepared()

    sensitivity = prompt_missingness_sensitivity(participant, min_all4_n=4)

    assert inspect.signature(prompt_missingness_sensitivity).parameters["min_all4_n"].default == 30
    assert sensitivity["all4_assignments"]["model"].iloc[0] == "all4_scored_assignments"
    assert sensitivity["all4_assignments"]["status"].iloc[0] == "run"
    assert sensitivity["all4_assignments"]["n"].iloc[0] == 4

    tiny = participant.iloc[:2].copy()
    tiny["scored_assignments"] = [3, 4]
    small = prompt_missingness_sensitivity(tiny, min_all4_n=2)
    assert small["min3_assignments"]["status"].iloc[0] == "not_run_small_n"
    assert small["min3_assignments"]["n"].iloc[0] == 2


def test_learning_prediction_table_uses_adjusted_model_ci() -> None:
    participant, _, _ = _prepared()

    prediction = model_based_learning_prediction_table(participant)

    assert {"midterm_points", "predicted_mean_prompt_score", "ci_low", "ci_high"} <= set(prediction.columns)
    assert len(prediction) == 30
    assert (prediction["ci_high"] > prediction["ci_low"]).all()


def test_model_based_learning_prediction_table_returns_empty_contract_for_constant_predictor() -> None:
    participant = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p2"],
            "group": ["A", "B"],
            "mean_prompt_score": [2.0, 3.0],
            "midterm_points": [4.0, 4.0],
            "prior_chatgpt_use": [1.0, 2.0],
        }
    )

    prediction = model_based_learning_prediction_table(participant)

    assert prediction.columns.tolist() == ["midterm_points", "predicted_mean_prompt_score", "ci_low", "ci_high"]
    assert prediction.empty


def test_model_based_learning_prediction_table_schema_and_values() -> None:
    participant, _, _ = _prepared()

    prediction = model_based_learning_prediction_table(participant)

    assert set(prediction.columns) == {"midterm_points", "predicted_mean_prompt_score", "ci_low", "ci_high"}
    assert len(prediction) == 30
    assert math.isclose(float(prediction["midterm_points"].min()), 3.0, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(float(prediction["midterm_points"].max()), 3.7, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(float(prediction["predicted_mean_prompt_score"].iloc[0]), 2.5, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(float(prediction["predicted_mean_prompt_score"].iloc[-1]), 2.5, rel_tol=0, abs_tol=1e-12)
    assert float(prediction["ci_low"].iloc[0]) < float(prediction["predicted_mean_prompt_score"].iloc[0]) < float(prediction["ci_high"].iloc[0])


def test_complete_case_diagnostics_report_marginal_loss() -> None:
    participant, _, _ = _prepared()
    participant.loc[0, "prior_chatgpt_use_score"] = None

    diagnostics = complete_case_diagnostics(participant)

    assert "loss_type" in diagnostics.columns
    assert set(diagnostics["loss_type"]) == {"marginal_non_additive"}
    assert diagnostics["lost_prior_chatgpt_use_score"].max() == 1
    assert diagnostics["final_n"].min() == len(participant) - 1


def test_contrast_table_separates_mean_and_effect_size_cis() -> None:
    participant, _, _ = _prepared()

    contrasts = participant_level_training_effect(participant)["contrasts"]

    assert {"mean_difference_ci_low", "mean_difference_ci_high", "hedges_g_ci_low", "hedges_g_ci_high"} <= set(contrasts.columns)
    assert {"ci_low", "ci_high"}.isdisjoint(contrasts.columns)


def test_participant_level_training_effect_columns_stable() -> None:
    participant, _, _ = _prepared()

    training = participant_level_training_effect(participant)

    assert set(training) == {"summary", "tests", "contrasts"}
    assert set(training["summary"].columns) == {
        "metric",
        "group",
        "n",
        "mean",
        "sd",
        "ci_low",
        "ci_high",
        "n_participants",
    }
    assert set(training["tests"].columns) == {"test", "statistic", "p_value"}
    assert set(training["contrasts"].columns) == {
        "contrast",
        "mean_difference",
        "mean_difference_ci_low",
        "mean_difference_ci_high",
        "hedges_g",
        "hedges_g_ci_low",
        "hedges_g_ci_high",
        "p_value",
        "n",
    }
    assert training["tests"]["test"].tolist() == ["welch_anova", "kruskal_wallis", "permutation_anova"]
    assert training["summary"]["metric"].tolist() == ["mean_prompt_score"] * len(training["summary"])


def test_participant_level_training_effect_contrasts_are_deterministic_and_stable() -> None:
    participant, _, _ = _prepared()

    first = participant_level_training_effect(participant)["contrasts"].reset_index(drop=True)
    second = participant_level_training_effect(participant)["contrasts"].reset_index(drop=True)

    assert_frame_equal(first, second)


def test_participant_level_training_effect_contrast_outputs_match_fixture() -> None:
    participant, _, _ = _prepared()

    contrasts = participant_level_training_effect(participant)["contrasts"]
    expected = pd.DataFrame(
        [
            {
                "contrast": "C vs A",
                "mean_difference": 1.1666666666666665,
                "mean_difference_ci_low": 1.1666666666666665,
                "mean_difference_ci_high": 1.1666666666666665,
                "hedges_g": float("nan"),
                "hedges_g_ci_low": float("nan"),
                "hedges_g_ci_high": float("nan"),
                "p_value": 0.37181409295352325,
                "n": 3,
            },
            {
                "contrast": "C vs B",
                "mean_difference": 1.1666666666666665,
                "mean_difference_ci_low": 1.1666666666666665,
                "mean_difference_ci_high": 1.1666666666666665,
                "hedges_g": float("nan"),
                "hedges_g_ci_low": float("nan"),
                "hedges_g_ci_high": float("nan"),
                "p_value": 0.37181409295352325,
                "n": 3,
            },
            {
                "contrast": "B vs A",
                "mean_difference": 0.0,
                "mean_difference_ci_low": 0.0,
                "mean_difference_ci_high": 0.0,
                "hedges_g": 0.0,
                "hedges_g_ci_low": 0.0,
                "hedges_g_ci_high": 0.0,
                "p_value": 1.0,
                "n": 4,
            },
            {
                "contrast": "C vs pooled A+B",
                "mean_difference": 1.1666666666666665,
                "mean_difference_ci_low": 1.1666666666666665,
                "mean_difference_ci_high": 1.1666666666666665,
                "hedges_g": float("nan"),
                "hedges_g_ci_low": float("nan"),
                "hedges_g_ci_high": float("nan"),
                "p_value": 0.22488755622188905,
                "n": 5,
            },
        ]
    )

    assert_frame_equal(contrasts, expected, check_like=False, check_exact=False, rtol=1e-12, atol=1e-12)


def test_calibration_keeps_raw_and_standardized_estimates_separate() -> None:
    participant, _, _ = _prepared()

    calibration = calibration_models(participant)

    assert {"estimate", "ci_low", "ci_high", "std_beta", "std_ci_low", "std_ci_high"} <= set(calibration.columns)
    assert not calibration["estimate"].equals(calibration["std_beta"])


def test_prepost_model_requires_group_and_labels_analysis_type() -> None:
    _, _, composites = _prepared()

    prepost = prepost_survey_change_models(composites)

    assert "analysis_type" in prepost.columns
    assert prepost["analysis_type"].notna().all()


def test_prepost_helpers_normalize_columns_and_exclude_metadata() -> None:
    composites = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p2"],
            "phase": [NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL, NORMALIZED_PRE_LABEL],
            "group_x": ["A", "A", "B"],
            "prior_chatgpt_use_score": [1.0, 1.0, 2.0],
            "trust": [1.0, 2.0, 3.0],
            "trust_items_present": [1, 1, 1],
        }
    )

    normalized = quant_models._normalise_prepost_composites(composites)

    assert "group" in normalized.columns
    assert "group_x" not in normalized.columns
    assert quant_models._prepost_dimensions(normalized) == ["trust"]
    with pytest.raises(ValueError, match="require group"):
        quant_models._normalise_prepost_composites(composites.drop(columns="group_x"))


def test_prepost_wide_averages_duplicate_phase_rows() -> None:
    composites = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p1", "p2"],
            "phase": [NORMALIZED_PRE_LABEL, NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL, NORMALIZED_POST_LABEL],
            "trust": [1.0, 3.0, 5.0, 7.0],
        }
    )

    wide = quant_models._prepost_wide(composites, "trust")

    expected = pd.DataFrame(
        {NORMALIZED_POST_LABEL: [5.0, 7.0], NORMALIZED_PRE_LABEL: [2.0, float("nan")]},
        index=pd.Index(["p1", "p2"], name=PARTICIPANT_KEY_COLUMN),
    )
    expected.columns.name = "phase"
    assert_frame_equal(wide, expected)


def test_prepost_fallback_row_has_stable_paired_output_contract() -> None:
    composites = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p2", "p2", "p3", "p3"],
            "phase": [NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL] * 3,
            "group": ["A", "A", "A", "A", "B", "B"],
            "trust": [1.0, 2.0, 2.0, 4.0, 3.0, 3.0],
        }
    )

    row = quant_models._prepost_fallback_row(composites, "trust")

    assert row is not None
    assert row["dimension"] == "trust"
    assert row["analysis_type"] == "paired_descriptive_fallback"
    assert row["pre_mean"] == 2.0
    assert row["post_mean"] == 3.0
    assert row["change"] == 1.0
    assert row["ci_low"] == 0.0
    assert row["ci_high"] == 2.0
    assert row["n"] == 3
    assert math.isclose(cast(float, row["phase_p_value"]), 0.22540333075851665)
    assert pd.isna(row["interaction_p_value"])
    assert quant_models._prepost_fallback_row(composites[composites["phase"] == NORMALIZED_PRE_LABEL], "trust") is None


def test_prepost_mixed_row_preserves_model_and_change_contract(monkeypatch) -> None:
    composites = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p2", "p2", "p3", "p3"],
            "phase": [NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL] * 3,
            "group": ["A", "A", "A", "A", "B", "B"],
            "trust": [1.0, 2.0, 2.0, 4.0, 3.0, 3.0],
        }
    )

    class FakeResult:
        converged = True
        nobs = 6

    class FakeModel:
        @staticmethod
        def fit(*, reml: bool, disp: bool) -> FakeResult:
            assert reml is False
            assert disp is False
            return FakeResult()

    monkeypatch.setattr(quant_models.smf, "mixedlm", lambda *args, **kwargs: FakeModel())
    monkeypatch.setattr(
        quant_models,
        "_tidy_result",
        lambda *_args, **_kwargs: pd.DataFrame(
            {
                "term": ["Intercept", "phase[T.post]", "phase[T.post]:group[T.B]"],
                "p_value": [0.9, 0.2, 0.01],
            }
        ),
    )

    row = quant_models._prepost_mixed_row(composites, "trust")

    assert row == {
        "dimension": "trust",
        "analysis_type": "mixed_model",
        "pre_mean": 2.0,
        "post_mean": 3.0,
        "change": 1.0,
        "ci_low": 0.0,
        "ci_high": 2.0,
        "n": 3,
        "phase_p_value": 0.2,
        "interaction_p_value": 0.01,
    }


def test_prepost_phase_p_value_excludes_interaction_terms(monkeypatch) -> None:
    composites = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p2", "p2", "p3", "p3", "p4", "p4"],
            "phase": [NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL] * 4,
            "group": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "trust": [1.0, 2.0, 1.0, 2.0, 1.0, 4.0, 1.0, 4.0],
        }
    )

    class FakeModel:
        def fit(self, reml=False, disp=False):
            class FakeResult:
                converged = True
                nobs = len(composites)

            return FakeResult()

    monkeypatch.setattr(quant_models.smf, "mixedlm", lambda *args, **kwargs: FakeModel())
    monkeypatch.setattr(
        quant_models,
        "_tidy_result",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "term": ["Intercept", "phase[T.pre]", "group[T.B]", "phase[T.pre]:group[T.B]"],
                "p_value": [0.9, 0.42, 0.8, 0.01],
            }
        ),
    )

    prepost = prepost_survey_change_models(composites)

    assert prepost.loc[0, "phase_p_value"] == 0.42
    assert prepost.loc[0, "interaction_p_value"] == 0.01
