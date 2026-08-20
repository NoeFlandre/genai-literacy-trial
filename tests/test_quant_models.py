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


def test_model_diagnostics_uses_the_named_composite_column() -> None:
    frame = pd.DataFrame({"trust": [1.0, 2.0], "XXXX": [None, 2.0]})

    result = quant_models._model_diagnostics(frame, "survey_model", ["trust"], "trust")

    assert result["lost_survey_composite"] == 0


def test_model_diagnostics_treats_an_empty_composite_name_as_missing() -> None:
    frame = pd.DataFrame({"": [1.0, None], "XXXX": [1.0, 2.0]})

    result = quant_models._model_diagnostics(frame, "survey_model", [], "")

    assert result["lost_survey_composite"] == 1


def test_fit_ols_hc3_passes_the_explicit_covariance_type(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeResult:
        pass

    class FakeModel:
        def fit(self, **kwargs: object) -> FakeResult:
            calls.append(kwargs)
            return FakeResult()

    monkeypatch.setattr(quant_models.smf, "ols", lambda *_args, **_kwargs: FakeModel())

    result = quant_models._fit_ols_hc3("y ~ x", pd.DataFrame({"x": [1.0], "y": [2.0]}))

    assert isinstance(result, FakeResult)
    assert calls == [{"cov_type": "HC3"}]


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


def test_fit_prompt_trajectory_mixed_model_preserves_tidy_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    assignment = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p2", "p2"],
            "group": ["A", "A", "B", "B"],
            "assignment": [1, 2, 1, 2],
            "prompt_score": [2.0, 3.0, 4.0, 5.0],
        }
    )

    class FakeResult:
        converged = True

    class FakeModel:
        @staticmethod
        def fit(*, reml: bool, disp: bool) -> FakeResult:
            return FakeResult()

    tidy_calls: list[tuple[object, object, object]] = []

    def fake_tidy(result: object, model_name: object, n: object) -> pd.DataFrame:
        tidy_calls.append((result, model_name, n))
        return pd.DataFrame({"model": [model_name], "n": [n]})

    monkeypatch.setattr(quant_models.smf, "mixedlm", lambda *_args, **_kwargs: FakeModel())
    monkeypatch.setattr(quant_models, "_tidy_result", fake_tidy)

    summary = fit_prompt_trajectory_model(assignment)

    assert summary.method == "mixedlm"
    assert tidy_calls[0][0].__class__ is FakeResult
    assert tidy_calls[0][1:] == ("prompt_trajectory_mixedlm", 4)


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


def test_learning_outcome_models_preserve_sample_and_standardization_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    participant, _, _ = _prepared()
    complete_case_calls: list[list[str] | None] = []
    spearman_calls: list[int | None] = []
    effect_calls: list[tuple[str, str, bool | None, bool | None]] = []
    original_complete_cases = quant_models._complete_cases

    def recording_complete_cases(frame: pd.DataFrame, required: list[str]) -> pd.DataFrame:
        complete_case_calls.append(required)
        return original_complete_cases(frame, required)

    def fake_spearman(_x: pd.Series, _y: pd.Series, *, n_boot: int = 10000):
        spearman_calls.append(n_boot)
        return {"correlation": 0.0, "p_value": 1.0, "ci_low": 0.0, "ci_high": 0.0, "n": len(participant)}

    def recording_effect(
        tidy: pd.DataFrame,
        _work: pd.DataFrame,
        term: str,
        outcome: str,
        *,
        from_standardized_predictor: bool | None,
        include_ci: bool | None,
    ) -> pd.DataFrame:
        effect_calls.append((term, outcome, from_standardized_predictor, include_ci))
        return tidy

    monkeypatch.setattr(quant_models, "_complete_cases", recording_complete_cases)
    monkeypatch.setattr(quant_models, "spearman_with_ci", fake_spearman)
    monkeypatch.setattr(quant_models, "_add_standardized_effect", recording_effect)

    learning_outcome_models(participant)

    assert complete_case_calls == [["mean_prompt_score", "midterm_points", "group", "prior_chatgpt_use_score"]]
    assert spearman_calls == [1000, 1000]
    assert effect_calls == [
        ("midterm_points", "mean_prompt_score", False, False),
        ("prior_chatgpt_use_score", "mean_prompt_score", False, False),
    ]


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
    empty_other = quant_models._mean_difference_ci(pd.Series([1.0]), pd.Series(dtype=float), seed=123, n_boot=10)

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
    assert pd.isna(empty_other["mean_difference"])
    assert pd.isna(empty_other["mean_difference_ci_low"])
    assert pd.isna(empty_other["mean_difference_ci_high"])


def test_mean_difference_ci_coerces_numeric_string_inputs() -> None:
    result = quant_models._mean_difference_ci(pd.Series(["1", "2"]), pd.Series(["2", "3"]), seed=123, n_boot=10)

    assert result["mean_difference"] == -1.0
    assert np.isfinite(result["mean_difference_ci_low"])
    assert np.isfinite(result["mean_difference_ci_high"])


def test_mean_difference_ci_uses_the_default_bootstrap_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    class FakeRng:
        def choice(self, _values: np.ndarray, *, size: tuple[int, int], replace: bool) -> np.ndarray:
            calls.append(size)
            assert replace is True
            return np.ones(size)

    monkeypatch.setattr(quant_models.np.random, "default_rng", lambda _seed: FakeRng())

    quant_models._mean_difference_ci(pd.Series([1.0, 2.0]), pd.Series([2.0, 3.0]))

    assert calls == [(1000, 2), (1000, 2)]


def test_mean_difference_ci_uses_the_deterministic_default_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    seeds: list[int | None] = []
    original_default_rng = quant_models.np.random.default_rng

    def recording_default_rng(seed: int | None):
        seeds.append(seed)
        return original_default_rng(seed)

    monkeypatch.setattr(quant_models.np.random, "default_rng", recording_default_rng)

    quant_models._mean_difference_ci(pd.Series([1.0, 2.0]), pd.Series([2.0, 3.0]), n_boot=3)

    assert seeds == [quant_models.DEFAULT_SEED]


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


def test_contrast_rows_returns_nan_for_an_empty_comparison_group() -> None:
    frame = pd.DataFrame(
        {
            "group": ["C", "C", "A", "A"],
            "mean_prompt_score": [4.0, 5.0, 1.0, 2.0],
        }
    )

    rows = {row["contrast"]: row for row in quant_models._contrast_rows(frame, "mean_prompt_score")}

    assert pd.isna(rows["C vs B"]["p_value"])
    assert pd.isna(rows["B vs A"]["p_value"])


def test_contrast_rows_uses_fixed_bootstrap_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int | None, int, int]] = []

    def fake_hedges(_a: pd.Series, _b: pd.Series, *, n_boot: int = 10000):
        calls.append((n_boot, len(_a), len(_b)))
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

    assert calls == [(1000, 1, 1), (1000, 1, 1), (1000, 1, 1), (1000, 1, 2)]


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
    assert calibration["model"].tolist() == list(CALIBRATION_DIMENSIONS)
    assert calibration.index.tolist() == list(range(len(calibration)))
    assert usefulness.index.tolist() == list(range(len(usefulness)))
    assert calibration["fdr_p_value"].notna().all()


def test_standardized_betas_use_complete_case_model_sample() -> None:
    participant, _, _ = _prepared()
    participant.loc[0, "prior_chatgpt_use_score"] = None
    participant.loc[1, "trust"] = None

    calibration = calibration_models(participant)
    usefulness = perceived_usefulness_models(participant)

    assert calibration["n"].min() == len(participant) - 2
    assert calibration.loc[calibration["dimension"] == "trust", "n"].min() == len(participant) - 2
    assert calibration.loc[calibration["dimension"] == "perceived_usefulness", "n"].min() == len(participant) - 1
    assert usefulness["n"].min() == len(participant) - 1


def test_perceived_usefulness_models_preserve_model_specific_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    participant, _, _ = _prepared()
    complete_case_calls: list[tuple[list[str] | None, pd.Series]] = []
    effect_calls: list[tuple[str, str, bool | None, bool | None]] = []
    original_complete_cases = quant_models._complete_cases

    def recording_complete_cases(frame: pd.DataFrame, required: list[str]) -> pd.DataFrame:
        complete_case_calls.append((required, frame["grade_change"].copy()))
        return original_complete_cases(frame, required)

    def recording_effect(
        tidy: pd.DataFrame,
        _work: pd.DataFrame,
        term: str,
        outcome: str,
        *,
        from_standardized_predictor: bool | None,
        include_ci: bool | None,
    ) -> pd.DataFrame:
        effect_calls.append((term, outcome, from_standardized_predictor, include_ci))
        return tidy

    monkeypatch.setattr(quant_models, "_complete_cases", recording_complete_cases)
    monkeypatch.setattr(quant_models, "_add_standardized_effect", recording_effect)

    perceived_usefulness_models(participant)

    expected_change = participant["final_points"] - participant["midterm_points"]
    assert [required for required, _ in complete_case_calls] == [
        ["perceived_usefulness", "prior_chatgpt_use_score", "group", "final_points", "midterm_points"],
        ["perceived_usefulness", "prior_chatgpt_use_score", "group", "final_points", "grade_change"],
    ]
    for _, observed_change in complete_case_calls:
        pd.testing.assert_series_equal(observed_change, expected_change, check_names=False)
    assert effect_calls == [
        ("perceived_usefulness_z", "final_points", True, True),
        ("perceived_usefulness_z", "grade_change", True, True),
    ]


def test_training_contrasts_report_p_values() -> None:
    participant, _, _ = _prepared()

    training = participant_level_training_effect(participant)

    assert training["contrasts"]["p_value"].notna().all()


def test_prompt_missingness_sensitivity_outputs_min3_and_all4() -> None:
    participant, _, _ = _prepared()

    sensitivity = prompt_missingness_sensitivity(participant, min_all4_n=30)

    assert {"scored_assignment_distribution", "min3_assignments", "all4_assignments"} <= set(sensitivity)
    assert sensitivity["all4_assignments"]["status"].iloc[0] == "not_run_small_n"
    assert sensitivity["all4_assignments"]["model"].iloc[0] == "all4_scored_assignments"


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
    assert small["min3_assignments"]["model"].iloc[0] == "min3_scored_assignments"


def test_prompt_missingness_sensitivity_keeps_missing_distribution_keys() -> None:
    participant, _, _ = _prepared()
    participant.loc[participant.index[0], "group"] = None

    sensitivity = prompt_missingness_sensitivity(participant, min_all4_n=99)

    assert sensitivity["scored_assignment_distribution"]["group"].isna().any()


def test_prompt_missingness_sensitivity_preserves_small_n_and_formula_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    participant, _, _ = _prepared()
    participant = participant.iloc[:3].copy()
    participant["scored_assignments"] = [4, 4, 4]
    participant["prior_chatgpt_use_score"] = participant["prior_chatgpt_use_score"].fillna(1.0)
    participant["irrelevant_missing_column"] = None
    formulas: list[str] = []

    class FakeResult:
        nobs = 3

    monkeypatch.setattr(
        quant_models,
        "_fit_ols_hc3",
        lambda formula, _data: formulas.append(formula) or FakeResult(),
    )
    monkeypatch.setattr(
        quant_models,
        "_tidy_result",
        lambda _result, model_name, n: pd.DataFrame({"model": [model_name], "n": [n]}),
    )

    sensitivity = prompt_missingness_sensitivity(participant, min_all4_n=3)

    assert sensitivity["min3_assignments"]["status"].iloc[0] == "run"
    assert sensitivity["min3_assignments"]["n"].iloc[0] == 3
    assert sensitivity["min3_assignments"]["model"].iloc[0] == "min3_scored_assignments"
    assert sensitivity["all4_assignments"]["status"].iloc[0] == "run"
    assert sensitivity["all4_assignments"]["model"].iloc[0] == "all4_scored_assignments"
    assert formulas == [
        "mean_prompt_score ~ midterm_points + group + prior_chatgpt_use_score + scored_assignments",
        "mean_prompt_score ~ midterm_points + group + prior_chatgpt_use_score",
    ]


def test_prompt_missingness_sensitivity_uses_the_default_all4_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    participant, _, _ = _prepared()
    participant = pd.concat([participant.iloc[[0]]] * 30, ignore_index=True)
    participant["scored_assignments"] = 4

    class FakeResult:
        nobs = 30

    monkeypatch.setattr(quant_models, "_fit_ols_hc3", lambda *_args, **_kwargs: FakeResult())
    monkeypatch.setattr(
        quant_models,
        "_tidy_result",
        lambda _result, model_name, n: pd.DataFrame({"model": [model_name], "n": [n]}),
    )

    sensitivity = prompt_missingness_sensitivity(participant)

    assert sensitivity["all4_assignments"]["status"].iloc[0] == "run"
    assert sensitivity["all4_assignments"]["n"].iloc[0] == 30


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


def test_model_based_learning_prediction_uses_complete_cases_and_unique_group_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    participant = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p2", "p3", "p4"],
            "group": ["A", "A", "A", "B"],
            "mean_prompt_score": [1.0, 2.0, 3.0, 4.0],
            "midterm_points": [1.0, 1.0, 2.0, 2.0],
            "prior_chatgpt_use": [1.0, 2.0, 3.0, 4.0],
        }
    )
    complete_case_calls: list[list[str] | None] = []
    references: list[pd.DataFrame] = []
    original_complete_cases = quant_models._complete_cases

    def recording_complete_cases(frame: pd.DataFrame, required: list[str]) -> pd.DataFrame:
        complete_case_calls.append(required)
        return original_complete_cases(frame, required)

    class FakePrediction:
        def summary_frame(self, *, alpha: float) -> pd.DataFrame:
            assert alpha == 0.05
            return pd.DataFrame({"mean": np.zeros(30), "mean_ci_lower": np.full(30, -1.0), "mean_ci_upper": np.ones(30)})

    class FakeResult:
        def get_prediction(self, reference: pd.DataFrame) -> FakePrediction:
            references.append(reference)
            return FakePrediction()

    monkeypatch.setattr(quant_models, "_complete_cases", recording_complete_cases)
    monkeypatch.setattr(quant_models, "_fit_ols_hc3", lambda *_args, **_kwargs: FakeResult())

    prediction = model_based_learning_prediction_table(participant)

    assert prediction.shape == (30, 4)
    assert complete_case_calls == [["mean_prompt_score", "midterm_points", "group", "prior_chatgpt_use_score"]]
    assert references[0]["group"].iloc[0] == "A"


def test_complete_case_diagnostics_report_marginal_loss() -> None:
    participant, _, _ = _prepared()
    participant.loc[0, "prior_chatgpt_use_score"] = None

    diagnostics = complete_case_diagnostics(participant)

    assert "loss_type" in diagnostics.columns
    assert set(diagnostics["loss_type"]) == {"marginal_non_additive"}
    assert diagnostics["lost_prior_chatgpt_use_score"].max() == 1
    assert diagnostics["final_n"].min() == len(participant) - 1


def test_complete_case_diagnostics_preserves_named_survey_composites() -> None:
    participant = pd.DataFrame(
        {
            "mean_prompt_score": [1.0, 2.0],
            "midterm_points": [2.0, 3.0],
            "final_points": [3.0, 4.0],
            "group": ["A", "A"],
            "prior_chatgpt_use_score": [1.0, 1.0],
            "perceived_usefulness": [1.0, None],
            "trust": [None, 2.0],
            "XXXX": [None, 2.0],
        }
    )

    diagnostics = complete_case_diagnostics(participant)
    final_points = diagnostics.loc[diagnostics["model"] == "perceived_usefulness_final_points"].iloc[0]
    grade_change = diagnostics.loc[diagnostics["model"] == "perceived_usefulness_grade_change"].iloc[0]
    calibration = diagnostics.loc[diagnostics["model"] == "calibration_trust"].iloc[0]

    assert final_points["lost_survey_composite"] == 1
    assert grade_change["lost_survey_composite"] == 1
    assert calibration["lost_survey_composite"] == 1


def test_complete_case_diagnostics_computes_grade_change_by_subtraction(monkeypatch: pytest.MonkeyPatch) -> None:
    participant = pd.DataFrame(
        {
            "mean_prompt_score": [1.0, 2.0],
            "midterm_points": [4.0, 5.0],
            "final_points": [10.0, 13.0],
            "group": ["A", "A"],
            "prior_chatgpt_use_score": [1.0, 1.0],
            "perceived_usefulness": [1.0, 2.0],
        }
    )
    observed: list[float] = []

    def fake_diagnostics(
        frame: pd.DataFrame,
        model: str,
        _required: list[str],
        _survey: str | None = None,
    ) -> dict[str, object]:
        if model == "perceived_usefulness_grade_change":
            observed.extend(frame["grade_change"].tolist())
        return {"model": model}

    monkeypatch.setattr(quant_models, "_model_diagnostics", fake_diagnostics)

    quant_models.complete_case_diagnostics(participant)

    assert observed == [6.0, 8.0]


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
    assert training["summary"].columns.tolist() == [
        "metric",
        "group",
        "n",
        "mean",
        "sd",
        "ci_low",
        "ci_high",
        "n_participants",
    ]


def test_participant_level_training_effect_uses_fixed_permutation_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int | None] = []

    monkeypatch.setattr(
        quant_models,
        "group_summary_ci",
        lambda *_args: pd.DataFrame({"group": ["A"], "n": [1], "mean": [1.0], "sd": [np.nan], "ci_low": [1.0], "ci_high": [1.0]}),
    )
    monkeypatch.setattr(quant_models, "welch_anova", lambda *_args: {"statistic": 1.0, "p_value": 0.5})
    monkeypatch.setattr(quant_models, "kruskal_test", lambda *_args: {"statistic": 1.0, "p_value": 0.5})
    monkeypatch.setattr(
        quant_models,
        "permutation_anova",
        lambda *_args, n_perm=2000: calls.append(n_perm) or {"statistic": 1.0, "p_value": 0.5},
    )
    monkeypatch.setattr(quant_models, "_contrast_rows", lambda *_args: [])

    quant_models.participant_level_training_effect(pd.DataFrame({"group": ["A"], "mean_prompt_score": [1.0]}))

    assert calls == [1000]


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
    both = composites.assign(group="correct")
    normalized_both = quant_models._normalise_prepost_composites(both)
    assert normalized_both["group"].tolist() == ["correct", "correct", "correct"]

    with pytest.raises(ValueError) as exc_info:
        quant_models._normalise_prepost_composites(composites.drop(columns="group_x"))
    assert str(exc_info.value) == "pre/post survey change models require group in the composite table"


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
        nobs = 6

    class FakeModel:
        @staticmethod
        def fit(*, reml: bool, disp: bool) -> FakeResult:
            assert reml is False
            assert disp is False
            return FakeResult()

    monkeypatch.setattr(quant_models.smf, "mixedlm", lambda *args, **kwargs: FakeModel())
    tidy_calls: list[tuple[object, object, object]] = []

    def fake_tidy(result: object, model_name: object, n: object) -> pd.DataFrame:
        tidy_calls.append((result, model_name, n))
        return pd.DataFrame(
            {
                "term": ["Intercept", "phase[T.post]", "phase[T.post]:group[T.B]"],
                "p_value": [0.9, 0.2, 0.01],
            }
        )

    monkeypatch.setattr(quant_models, "_tidy_result", fake_tidy)

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
    assert tidy_calls[0][1:] == ("prepost_trust", 6)


def test_prepost_mixed_row_rejects_nonconverged_models_with_stable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    composites = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1"],
            "phase": [NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL],
            "group": ["A", "A"],
            "trust": [1.0, 2.0],
        }
    )

    class FakeResult:
        converged = False

    class FakeModel:
        @staticmethod
        def fit(*, reml: bool, disp: bool) -> FakeResult:
            return FakeResult()

    monkeypatch.setattr(quant_models.smf, "mixedlm", lambda *_args, **_kwargs: FakeModel())

    with pytest.raises(ValueError) as exc_info:
        quant_models._prepost_mixed_row(composites, "trust")

    assert str(exc_info.value) == "MixedLM did not converge"


def test_prepost_change_statistics_uses_fixed_bootstrap_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int | None] = []

    def fake_mean_ci(values: pd.Series, *, n_boot: int = 10000):
        calls.append(n_boot)
        return {"mean": 1.0, "ci_low": 0.0, "ci_high": 2.0, "n": len(values)}

    monkeypatch.setattr(quant_models, "mean_ci_bootstrap", fake_mean_ci)
    wide = pd.DataFrame({NORMALIZED_PRE_LABEL: [1.0], NORMALIZED_POST_LABEL: [2.0]})

    diff, stat = quant_models._prepost_change_statistics(wide)

    assert diff.tolist() == [1.0]
    assert stat == {"mean": 1.0, "ci_low": 0.0, "ci_high": 2.0, "n": 1}
    assert calls == [1000]


def test_paired_p_value_is_defined_for_two_pairs() -> None:
    wide = pd.DataFrame(
        {NORMALIZED_PRE_LABEL: [1.0, 2.0], NORMALIZED_POST_LABEL: [2.0, 4.0]},
        index=["p1", "p2"],
    )
    paired = pd.Series([1.0, 2.0], index=["p1", "p2"])

    assert np.isfinite(quant_models._paired_p_value(wide, paired))


def test_paired_p_value_short_circuits_a_single_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    wide = pd.DataFrame({NORMALIZED_PRE_LABEL: [1.0], NORMALIZED_POST_LABEL: [2.0]}, index=["p1"])
    paired = pd.Series([1.0], index=["p1"])
    monkeypatch.setattr(quant_models.stats, "ttest_rel", lambda *_args, **_kwargs: pytest.fail("unexpected t-test"))

    assert pd.isna(quant_models._paired_p_value(wide, paired))


def test_paired_p_value_omits_missing_values_from_the_t_test() -> None:
    wide = pd.DataFrame(
        {
            NORMALIZED_PRE_LABEL: [1.0, np.nan, 3.0],
            NORMALIZED_POST_LABEL: [2.0, 3.0, 5.0],
        },
        index=["p1", "p2", "p3"],
    )
    paired = pd.Series([1.0, 2.0, 3.0], index=["p1", "p2", "p3"])

    assert np.isfinite(quant_models._paired_p_value(wide, paired))


def test_prepost_survey_change_models_adds_fdr_to_nonempty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    composites = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1"],
            "phase": [NORMALIZED_PRE_LABEL],
            "group": ["A"],
            "trust": [1.0],
        }
    )
    monkeypatch.setattr(
        quant_models,
        "_prepost_row",
        lambda _composites, dimension: {"dimension": dimension, "phase_p_value": 0.2},
    )
    fdr_calls: list[list[float]] = []

    def fake_fdr(values: pd.Series) -> list[float]:
        fdr_calls.append(values.tolist())
        return [0.3]

    monkeypatch.setattr(quant_models, "benjamini_hochberg", fake_fdr)

    result = prepost_survey_change_models(composites)

    assert result["fdr_p_value"].tolist() == [0.3]
    assert fdr_calls == [[0.2]]


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
