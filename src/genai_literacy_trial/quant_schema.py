from __future__ import annotations

from pathlib import Path

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
QuantPathMap = dict[str, Path]
