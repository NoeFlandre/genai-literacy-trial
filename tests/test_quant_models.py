from __future__ import annotations

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


def test_prompt_missingness_sensitivity_outputs_min3_and_all4() -> None:
    participant, _, _ = _prepared()

    sensitivity = prompt_missingness_sensitivity(participant, min_all4_n=30)

    assert {"scored_assignment_distribution", "min3_assignments", "all4_assignments"} <= set(sensitivity)
    assert sensitivity["all4_assignments"]["status"].iloc[0] == "not_run_small_n"
