from __future__ import annotations

from genai_literacy_trial.quant_config import QuantConfig
from genai_literacy_trial.quant_models import (
    calibration_models,
    fit_prompt_trajectory_model,
    learning_outcome_models,
    model_based_learning_prediction_table,
    participant_level_training_effect,
    perceived_usefulness_models,
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


def test_calibration_and_perceived_usefulness_models_apply_fdr_and_report_n() -> None:
    participant, _, _ = _prepared()

    calibration = calibration_models(participant)
    usefulness = perceived_usefulness_models(participant)

    assert "fdr_p_value" in calibration.columns
    assert calibration["n"].min() == len(participant)
    assert set(usefulness["model"]) == {"final_points", "grade_change"}
    assert usefulness["n"].min() == len(participant)


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


def test_learning_prediction_table_uses_adjusted_model_ci() -> None:
    participant, _, _ = _prepared()

    prediction = model_based_learning_prediction_table(participant)

    assert {"mean_prompt_score", "predicted_final_points", "ci_low", "ci_high"} <= set(prediction.columns)
    assert len(prediction) == 30
    assert (prediction["ci_high"] > prediction["ci_low"]).all()
