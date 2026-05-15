from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd

NORMALIZED_PRE_LABEL = "pre"
NORMALIZED_POST_LABEL = "post"
PARTICIPANT_KEY_COLUMN = "participant_key"
PUBLIC_OUTPUT_DIR_KEY = "public_output_dir"
PRIVATE_OUTPUT_DIR_KEY = "private_output_dir"
QUANT_TABLE_OUTPUT_FORMAT = "csv"
REQUIRED_QUANT_TABLES = (
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

QuantTableMap = dict[str, pd.DataFrame]


class BootstrapSummary(TypedDict):
    mean: float
    ci_low: float
    ci_high: float
    n: int


class StatisticalTestResult(TypedDict):
    statistic: float
    p_value: float


class CorrelationResult(TypedDict):
    correlation: float
    p_value: float
    ci_low: float
    ci_high: float
    n: int


class EffectSizeResult(TypedDict):
    estimate: float
    ci_low: float
    ci_high: float


class SmallSampleSensitivityResult(TypedDict):
    detectable_d_a_vs_b_80_power: float
    detectable_d_c_vs_pooled_ab_80_power: float
    detectable_r_n45_80_power: float
    interpretation: str


class MeanDifferenceResult(TypedDict):
    mean_difference: float
    mean_difference_ci_low: float
    mean_difference_ci_high: float


class TrainingContrastRow(TypedDict):
    contrast: str
    mean_difference: float
    mean_difference_ci_low: float
    mean_difference_ci_high: float
    hedges_g: float
    hedges_g_ci_low: float
    hedges_g_ci_high: float
    p_value: float
    n: int


class ModelDiagnosticsRow(TypedDict):
    model: str
    starting_n: int
    final_n: int
    loss_type: str
    lost_final_grade: int
    lost_midterm_grade: int
    lost_mean_prompt_score: int
    lost_prior_chatgpt_use_score: int
    lost_survey_composite: int
    lost_group: int


class QuantPathMap(TypedDict):
    public_output_dir: Path
    private_output_dir: Path


class TrainingEffectTables(TypedDict):
    summary: pd.DataFrame
    tests: pd.DataFrame
    contrasts: pd.DataFrame


class LearningOutcomeTables(TypedDict):
    correlations: pd.DataFrame
    models: pd.DataFrame


class PromptSensitivityTables(TypedDict):
    scored_assignment_distribution: pd.DataFrame
    min3_assignments: pd.DataFrame
    all4_assignments: pd.DataFrame
