from __future__ import annotations

import math
import numpy as np

import pandas as pd
import pytest

from genai_literacy_trial.quant_config import QuantConfig
from genai_literacy_trial.quant_pipeline import _reliability
from genai_literacy_trial.quant_preprocess import (
    EXPECTED_GROUP_COUNTS_KEY,
    GROUP_COUNT_METRIC_PREFIX,
    build_assignment_prompt_table,
    build_participant_table,
    compute_survey_composites,
    map_configured_numeric,
    participant_key,
    prior_use_mapping_table,
    prepare_retained_survey,
    suppress_small_cells,
    validate_analysis_inventory,
)
from genai_literacy_trial.quant_schema import NORMALIZED_PRE_LABEL, PARTICIPANT_KEY_COLUMN
from tests.quant_fixtures import synthetic_quant_frames


def test_preprocess_builds_retained_participant_and_assignment_tables() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()

    retained, summary = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    assignment = build_assignment_prompt_table(prompts, participant, config)

    assert summary["pre_responses"] == 6
    assert summary["post_responses"] == 5
    assert summary["retained_participants"] == 5
    assert participant[PARTICIPANT_KEY_COLUMN].is_unique
    assert set(participant["group"]) == {"A", "B", "C"}
    assert len(participant) == 5
    assert "participant_id" not in participant.columns
    assert "User" + "1" not in assignment.columns
    assert "GPT" + "1" not in assignment.columns
    assert assignment["assignment"].isin([1, 2, 3, 4]).all()
    assert assignment["prompt_score"].dropna().between(1, 5).all()


def test_dropout_prompt_rows_do_not_leak_into_participant_or_assignment_tables() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()

    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    assignment = build_assignment_prompt_table(prompts, participant, config)
    dropout_key = participant_key("p06")

    assert dropout_key not in set(participant[PARTICIPANT_KEY_COLUMN])
    assert dropout_key not in set(assignment[PARTICIPANT_KEY_COLUMN])
    assert len(assignment) == 20


def test_build_participant_table_rejects_duplicate_participant_assignment_rows() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    prompts = pd.concat([prompts, prompts.iloc[[0]].copy()], ignore_index=True)

    retained, _ = prepare_retained_survey(survey, config)

    with pytest.raises(ValueError, match="Duplicate prompt rows.*assignment"):
        build_participant_table(retained, grades, prompts, config)


def test_build_participant_table_allows_exact_duplicate_grade_rows() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()

    duplicate = grades[grades["participant_id"] == "p02"].copy()
    grades = pd.concat([grades, duplicate], ignore_index=True)

    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)

    assert participant.shape[0] == 5
    assert participant[PARTICIPANT_KEY_COLUMN].is_unique


def test_build_participant_table_rejects_conflicting_duplicate_grade_rows() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()

    duplicate = grades[grades["participant_id"] == "p02"].copy()
    duplicate.loc[:, "group"] = "C"
    grades = pd.concat([grades, duplicate], ignore_index=True)

    retained, _ = prepare_retained_survey(survey, config)

    with pytest.raises(ValueError, match="Conflicting grade rows"):
        build_participant_table(retained, grades, prompts, config)


def test_survey_composites_reverse_code_and_require_half_items() -> None:
    survey, _, _ = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)

    composites = compute_survey_composites(retained, config)
    pre = composites[(composites["phase"] == NORMALIZED_PRE_LABEL) & (composites[PARTICIPANT_KEY_COLUMN].notna())].iloc[0]

    assert pre["perceived_usefulness"] >= 3
    assert math.isclose(pre["locus_of_control"], 4.0)
    assert "locus_of_control_items_present" in composites.columns


def test_likert_scoring_accepts_text_and_numeric_strings_and_reverse_codes() -> None:
    config = QuantConfig(
        survey_dimensions={"perceived_usefulness": ["useful_1", "useful_2"], "locus_of_control": ["control_1", "control_reverse"]},
        reverse_coded_items={"locus_of_control": ["control_reverse"]},
    )
    retained_survey = pd.DataFrame(
        {
            "participant_id": ["p01", "p02"],
            "phase": [config.pre_label, config.pre_label],
            "group": ["A", "B"],
            "useful_1": ["Agree", "Neutral"],
            "useful_2": ["3", "4"],
            "control_1": ["Disagree", "5"],
            "control_reverse": ["5", "2"],
        }
    )

    composites = compute_survey_composites(retained_survey, config)

    pre_a = composites.iloc[0]
    pre_b = composites.iloc[1]
    assert math.isclose(pre_a["perceived_usefulness"], 3.5)
    assert math.isclose(pre_b["perceived_usefulness"], 3.5)
    assert math.isclose(pre_a["locus_of_control"], 1.5)
    assert math.isclose(pre_b["locus_of_control"], (5.0 + 4.0) / 2.0)


def test_prior_chatgpt_use_scores_agree_with_mapping_table_for_mapped_and_numeric_values() -> None:
    config = QuantConfig.default()
    retained_survey = pd.DataFrame(
        {
            "participant_id": ["p01", "p02", "p03"],
            "phase": [config.pre_label, config.pre_label, config.pre_label],
            "group": ["A", "B", "C"],
            "prior_chatgpt_use": ["low", "3", "4.0"],
            "useful_1": ["Agree", "Agree", "Agree"],
            "useful_2": ["Agree", "Agree", "Agree"],
            "control_1": ["Agree", "Agree", "Agree"],
            "control_reverse": ["Agree", "Agree", "Agree"],
        }
    )

    composites = compute_survey_composites(retained_survey, config)
    mapping = prior_use_mapping_table(retained_survey, config)
    map_lookup = dict(zip(mapping["prior_chatgpt_use"], mapping["mapped_score"], strict=True))

    merged = (
        retained_survey.assign(**{PARTICIPANT_KEY_COLUMN: retained_survey["participant_id"].map(participant_key)})
        .merge(composites[[PARTICIPANT_KEY_COLUMN, "prior_chatgpt_use_score"]], on=PARTICIPANT_KEY_COLUMN, how="left")
        .merge(mapping, on="prior_chatgpt_use", how="left", suffixes=("", "_from_map"))
    )

    for _, row in merged.iterrows():
        assert pd.isna(row["mapped_score"]) == pd.isna(row["prior_chatgpt_use_score"])
        if pd.isna(row["mapped_score"]):
            continue
        assert row["prior_chatgpt_use_score"] == row["mapped_score"]
    assert map_lookup["low"] == 1.0
    assert map_lookup["3"] == 3.0
    assert map_lookup["4.0"] == 4.0


def test_public_numeric_mapping_helper_matches_composite_scoring() -> None:
    config = QuantConfig.default()
    values = pd.Series(["Strongly disagree", "Agree", "4", "not mapped"])

    mapped = map_configured_numeric(values, config.likert_mapping)

    expected = pd.Series([1.0, 4.0, 4.0, np.nan])
    pd.testing.assert_series_equal(mapped, expected)


def test_reliability_reverse_codes_items_before_alpha() -> None:
    config = QuantConfig.default()
    retained = pd.DataFrame(
        {
            "participant_id": ["p1", "p2", "p3", "p4"],
            "phase": [NORMALIZED_PRE_LABEL] * 4,
            "control_1": ["1", "2", "3", "4"],
            "control_reverse": ["5", "4", "3", "2"],
        }
    )

    reliability = _reliability(retained, config)
    locus = reliability.loc[reliability["dimension"] == "locus_of_control", "cronbach_alpha"].iloc[0]

    assert locus == 1.0


def test_reliability_accepts_text_and_numeric_like_lookups_consistently() -> None:
    config = QuantConfig.default()
    text = pd.DataFrame(
        {
            "participant_id": ["p1", "p2", "p3", "p4"],
            "phase": [NORMALIZED_PRE_LABEL] * 4,
            "control_1": ["Strongly disagree", "Disagree", "Agree", "Strongly agree"],
            "control_reverse": ["Strongly agree", "Agree", "Disagree", "Strongly disagree"],
        }
    )
    numeric = pd.DataFrame(
        {
            "participant_id": ["p1", "p2", "p3", "p4"],
            "phase": [NORMALIZED_PRE_LABEL] * 4,
            "control_1": ["1", "2", "4", "5"],
            "control_reverse": ["5", "4", "2", "1"],
        }
    )

    assert _reliability(text, config).equals(_reliability(numeric, config))


def test_reliability_schema_and_values_unchanged_for_synthetic_fixture() -> None:
    survey, _, _ = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)

    reliability = _reliability(retained, config)

    assert reliability.columns.tolist() == ["dimension", "n_items", "cronbach_alpha"]
    assert reliability.shape[0] == len(config.survey_dimensions)
    expected = pd.DataFrame(
        {
            "dimension": list(config.survey_dimensions.keys()),
            "n_items": [2, 2, 2, 1, 1, 1, 1, 1, 2],
            "cronbach_alpha": [0.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        }
    )
    pd.testing.assert_frame_equal(reliability, expected)


def test_inventory_validation_fails_on_bad_units_and_values() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    prompts.loc[0, "prompt_score"] = 6

    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts.assign(prompt_score=3), config)
    assignment = build_assignment_prompt_table(prompts.assign(prompt_score=3), participant, config)
    duplicated = pd.concat([participant, participant.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicated participant_key"):
        validate_analysis_inventory(duplicated, assignment, retained, config)

    bad_assignment = assignment.copy()
    bad_assignment.loc[0, "assignment"] = 9
    with pytest.raises(ValueError, match="assignment"):
        validate_analysis_inventory(participant, bad_assignment, retained, config)

    bad_prompt = assignment.copy()
    bad_prompt.loc[0, "prompt_score"] = 6
    with pytest.raises(ValueError, match="prompt score"):
        validate_analysis_inventory(participant, bad_prompt, retained, config)


def test_inventory_validation_requires_exactly_one_pre_and_post_row() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    retained = pd.concat([retained, retained.iloc[[0]].copy()], ignore_index=True)
    participant = build_participant_table(retained, grades, prompts, config)
    assignment = build_assignment_prompt_table(prompts, participant, config)

    with pytest.raises(ValueError, match="exactly one pre and one post"):
        validate_analysis_inventory(participant, assignment, retained, config)


def test_inventory_validation_checks_expected_group_counts() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    assignment = build_assignment_prompt_table(prompts, participant, config)

    inventory = validate_analysis_inventory(
        participant,
        assignment,
        retained,
        config,
        expected={"group_counts": {"A": 2, "B": 2, "C": 1}},
    )

    assert {"group_count_A", "group_count_B", "group_count_C"} <= set(inventory["metric"])


def test_group_count_inventory_contract_names_are_centralized() -> None:
    assert EXPECTED_GROUP_COUNTS_KEY == "group_counts"
    assert GROUP_COUNT_METRIC_PREFIX == "group_count_"


def test_participant_key_column_name_is_centralized() -> None:
    assert PARTICIPANT_KEY_COLUMN == "participant_key"


def test_prior_use_mapping_table_flags_unmapped_categories() -> None:
    survey, _, _ = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    retained.loc[retained[config.columns.phase] == config.pre_label, config.columns.prior_chatgpt_use] = "unknown category"

    mapping = prior_use_mapping_table(retained, config)

    assert set(mapping["mapped_status"]) == {"unmapped"}

    unmapped = mapping.loc[mapping["prior_chatgpt_use"] == "unknown category"].iloc[0]
    assert unmapped["mapped_status"] == "unmapped"
    assert pd.isna(unmapped["mapped_score"])


def test_small_cell_suppression_collapses_and_hides_exact_counts() -> None:
    table = pd.DataFrame(
        {
            "metric": ["gender", "gender", "gender"],
            "group": ["A", "A", "A"],
            "gender": ["large", "rare1", "rare2"],
            "n": [6, 1, 2],
        }
    )

    suppressed = suppress_small_cells(table, category_col="gender", min_count=5)

    assert "Other/suppressed" in set(suppressed["gender"])
    assert "1" not in set(suppressed["n"].astype(str))
    assert "2" not in set(suppressed["n"].astype(str))
