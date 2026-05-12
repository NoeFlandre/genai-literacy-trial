from __future__ import annotations

import math

import pandas as pd

import genai_literacy_trial.quant_models as quant_models
from genai_literacy_trial.quant_config import QuantConfig
from genai_literacy_trial.quant_models import (
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
from tests.quant_fixtures import synthetic_quant_frames


def _prepared():
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    composites = compute_survey_composites(retained, config)
    pre = composites[composites["phase"] == "pre"].drop(columns=["phase"])
    participant = participant.merge(pre, on="participant_key", how="left")
    assignment = build_assignment_prompt_table(prompts, participant, config)
    return participant, assignment, composites


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

    final_points = outcome["models"].query("model == 'final_points' and term == 'mean_prompt_score'").iloc[0]
    grade_change = outcome["models"].query("model == 'grade_change' and term == 'mean_prompt_score'").iloc[0]

    assert final_points["n"] == len(participant)
    assert grade_change["n"] == len(participant)
    assert math.isclose(float(final_points["estimate"]), 1.052903225806446, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(final_points["std_beta"]), 1.831171367380462, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(grade_change["estimate"]), 0.13887096774193544, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(float(grade_change["std_beta"]), 0.25149780744258415, rel_tol=1e-12, abs_tol=1e-12)
    assert not math.isclose(float(final_points["estimate"]), float(final_points["std_beta"]))
    assert not math.isclose(float(grade_change["estimate"]), float(grade_change["std_beta"]))


def test_calibration_and_perceived_usefulness_models_apply_fdr_and_report_n() -> None:
    participant, _, _ = _prepared()

    calibration = calibration_models(participant)
    usefulness = perceived_usefulness_models(participant)

    assert "fdr_p_value" in calibration.columns
    assert calibration["n"].min() == len(participant)
    assert set(usefulness["model"]) == {"final_points", "grade_change"}
    assert usefulness["n"].min() == len(participant)


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


def test_learning_prediction_table_uses_adjusted_model_ci() -> None:
    participant, _, _ = _prepared()

    prediction = model_based_learning_prediction_table(participant)

    assert {"mean_prompt_score", "predicted_final_points", "ci_low", "ci_high"} <= set(prediction.columns)
    assert len(prediction) == 30
    assert (prediction["ci_high"] > prediction["ci_low"]).all()


def test_model_based_learning_prediction_table_schema_and_values() -> None:
    participant, _, _ = _prepared()

    prediction = model_based_learning_prediction_table(participant)

    assert set(prediction.columns) == {"mean_prompt_score", "predicted_final_points", "ci_low", "ci_high"}
    assert len(prediction) == 30
    assert math.isclose(float(prediction["mean_prompt_score"].min()), 2.5, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(float(prediction["mean_prompt_score"].max()), 3.6666666666666665, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(float(prediction["predicted_final_points"].iloc[0]), 3.3, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(float(prediction["predicted_final_points"].iloc[-1]), 4.52838709677418, rel_tol=0, abs_tol=1e-12)
    assert float(prediction["ci_low"].iloc[0]) < float(prediction["predicted_final_points"].iloc[0]) < float(prediction["ci_high"].iloc[0])


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


def test_prepost_phase_p_value_excludes_interaction_terms(monkeypatch) -> None:
    composites = pd.DataFrame(
        {
            "participant_key": ["p1", "p1", "p2", "p2", "p3", "p3", "p4", "p4"],
            "phase": ["pre", "post"] * 4,
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
