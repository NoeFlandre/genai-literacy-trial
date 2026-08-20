from __future__ import annotations

import math
from typing import Any, cast

import numpy as np

import pandas as pd
import pytest

import genai_literacy_trial.quant_preprocess as quant_preprocess
from genai_literacy_trial.quant_config import ExpectedInventory, QuantConfig
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

    assert summary == {
        "pre_responses": 6,
        "post_responses": 5,
        "dropouts": 1,
        "retained_participants": 5,
        "retained_survey_rows": 10,
    }
    assert participant[PARTICIPANT_KEY_COLUMN].is_unique
    assert set(participant["group"]) == {"A", "B", "C"}
    assert len(participant) == 5
    assert "participant_id" not in participant.columns
    assert "User" + "1" not in assignment.columns
    assert "GPT" + "1" not in assignment.columns
    assert assignment["assignment"].isin([1, 2, 3, 4]).all()
    assert assignment["prompt_score"].dropna().between(1, 5).all()


def test_participant_key_is_a_stable_12_character_public_identifier() -> None:
    assert participant_key("p05") == "ccb7957f96e5"
    assert len(participant_key("p05")) == 12


def test_participant_and_assignment_tables_keep_exact_public_columns_and_values() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)

    participant = build_participant_table(retained, grades, prompts, config)
    assignment = build_assignment_prompt_table(prompts, participant, config)

    assert participant.columns.tolist() == [
        PARTICIPANT_KEY_COLUMN,
        "group",
        "prior_chatgpt_use",
        "gender",
        "major",
        "midterm_points",
        "final_points",
        "mean_prompt_score",
        "scored_assignments",
    ]
    p05 = participant.loc[participant[PARTICIPANT_KEY_COLUMN] == participant_key("p05")].iloc[0]
    assert p05[["group", "prior_chatgpt_use", "gender", "major"]].to_dict() == {
        "group": "C",
        "prior_chatgpt_use": "low",
        "gender": "X",
        "major": "M1",
    }
    assert p05[["midterm_points", "final_points", "mean_prompt_score", "scored_assignments"]].to_dict() == {
        "midterm_points": 3.7,
        "final_points": 4.0,
        "mean_prompt_score": 11.0 / 3.0,
        "scored_assignments": 3,
    }
    assert assignment.columns.tolist() == [PARTICIPANT_KEY_COLUMN, "group", "assignment", "prompt_score"]
    p05_assignment_2 = assignment.loc[
        (assignment[PARTICIPANT_KEY_COLUMN] == participant_key("p05")) & (assignment["assignment"] == 2)
    ]
    assert len(p05_assignment_2) == 1
    assert pd.isna(p05_assignment_2["prompt_score"].iloc[0])


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


def test_assignment_table_accepts_group_x_participant_sources() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    group_x_source = participant.rename(columns={"group": "group_x"})

    assignment = build_assignment_prompt_table(prompts, group_x_source, config)

    assert assignment["group"].notna().all()
    assert set(assignment["group"]) == {"A", "B", "C"}


def test_merge_participant_metadata_prefers_grade_values_and_fills_missing_values() -> None:
    grade_df = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p2"],
            "group": ["A", "B"],
            "prior_chatgpt_use": [None, "grade"],
        }
    )
    prior = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p2"],
            "prior_chatgpt_use": ["survey", "survey"],
        }
    )

    participant = quant_preprocess._merge_participant_metadata(
        grade_df,
        prior,
        [PARTICIPANT_KEY_COLUMN, "group"],
        ["prior_chatgpt_use"],
    )

    assert participant["prior_chatgpt_use"].tolist() == ["survey", "grade"]
    assert "prior_chatgpt_use_survey" not in participant.columns


def test_merge_participant_metadata_keeps_grade_rows_without_prior_survey() -> None:
    grade_df = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p2"],
            "group": ["A", "B"],
            "prior_chatgpt_use": ["grade", "grade"],
        }
    )
    prior = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1"],
            "prior_chatgpt_use": ["survey"],
        }
    )

    participant = quant_preprocess._merge_participant_metadata(
        grade_df,
        prior,
        [PARTICIPANT_KEY_COLUMN, "group"],
        ["prior_chatgpt_use"],
    )

    assert participant[PARTICIPANT_KEY_COLUMN].tolist() == ["p1", "p2"]
    assert participant["prior_chatgpt_use"].tolist() == ["grade", "grade"]


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
    duplicate.loc[:, "gender"] = "different-but-optional"
    grades = pd.concat([grades, duplicate], ignore_index=True)

    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)

    assert participant.shape[0] == 5
    assert participant[PARTICIPANT_KEY_COLUMN].is_unique


def test_prepare_grade_rows_accepts_survey_without_precomputed_key() -> None:
    config = QuantConfig.default()
    survey = pd.DataFrame({"participant_id": ["p1"]})
    grades = pd.DataFrame(
        {
            "participant_id": ["p1"],
            "group": ["A"],
            "midterm_grade": ["B"],
            "final_grade": ["A"],
        }
    )

    prepared, required, _ = quant_preprocess._prepare_grade_rows(survey, grades, config)

    assert prepared[PARTICIPANT_KEY_COLUMN].tolist() == [participant_key("p1")]
    assert required == [PARTICIPANT_KEY_COLUMN, "group", "midterm_grade", "final_grade"]


def test_map_grade_rejects_unmapped_values_with_column_name() -> None:
    with pytest.raises(ValueError) as exc_info:
        quant_preprocess._map_grade(pd.Series(["Z"]), QuantConfig.default(), "final_grade")

    assert str(exc_info.value) == "Unmapped letter grades in final_grade: ['Z']"


def test_map_configured_scalar_does_not_map_missing_values_to_literal_text() -> None:
    assert quant_preprocess._map_configured_scalar(np.nan, {"XXXX": 9.0}) is None


def test_validate_grade_key_consistency_keeps_missing_keys_and_all_conflicts() -> None:
    grade_df = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: [None, None],
            "group": ["A", "B"],
            "midterm_grade": ["A", "B"],
        }
    )

    with pytest.raises(ValueError) as exc_info:
        quant_preprocess._validate_grade_key_consistency(
            grade_df,
            PARTICIPANT_KEY_COLUMN,
            ["group", "midterm_grade"],
        )

    assert str(exc_info.value) == (
        "Conflicting grade rows for participant_key in: nan -> group: ['A', 'B'], "
        "midterm_grade: ['A', 'B']"
    )


def test_validate_grade_key_consistency_separates_multiple_conflicting_keys() -> None:
    grade_df = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1", "p2", "p2"],
            "group": ["A", "B", "A", "C"],
            "midterm_grade": ["A", "A", "B", "B"],
        }
    )

    with pytest.raises(ValueError) as exc_info:
        quant_preprocess._validate_grade_key_consistency(grade_df, PARTICIPANT_KEY_COLUMN, ["group", "midterm_grade"])

    message = str(exc_info.value)
    assert "; " in message
    assert "XX; XX" not in message


def test_build_participant_table_rejects_conflicting_duplicate_grade_rows() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()

    duplicate = grades[grades["participant_id"] == "p02"].copy()
    duplicate.loc[:, "group"] = "C"
    grades = pd.concat([grades, duplicate], ignore_index=True)

    retained, _ = prepare_retained_survey(survey, config)

    with pytest.raises(ValueError, match="Conflicting grade rows"):
        build_participant_table(retained, grades, prompts, config)


@pytest.mark.parametrize("column", ["midterm_grade", "final_grade"])
def test_build_participant_table_preserves_grade_column_in_mapping_errors(column: str) -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    grades.loc[0, column] = "Z"
    retained, _ = prepare_retained_survey(survey, config)

    with pytest.raises(ValueError) as exc_info:
        build_participant_table(retained, grades, prompts, config)

    assert str(exc_info.value) == f"Unmapped letter grades in {column}: ['Z']"


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


def test_prior_survey_rows_select_only_configured_pre_phase() -> None:
    config = QuantConfig.default()
    survey = pd.DataFrame(
        {
            "participant_id": ["p1", "p1"],
            "phase": [config.pre_label, config.post_label],
            "prior_chatgpt_use": ["pre-value", "post-value"],
        }
    )

    prior = quant_preprocess._prior_survey_rows(survey, config)

    assert prior["prior_chatgpt_use"].tolist() == ["pre-value"]


def test_dimension_composite_reports_zero_items_when_dimension_is_absent() -> None:
    result = quant_preprocess._dimension_composite(
        pd.DataFrame({"participant_id": ["p1"]}),
        "missing_dimension",
        ["missing_item"],
        QuantConfig.default(),
    )

    assert pd.isna(result["missing_dimension"])
    assert result["missing_dimension_items_present"] == 0


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

    with pytest.raises(ValueError) as duplicate_error:
        validate_analysis_inventory(duplicated, assignment, retained, config)
    assert str(duplicate_error.value) == "participant-level table contains duplicated participant_key"

    bad_assignment = assignment.copy()
    bad_assignment.loc[0, "assignment"] = 9
    with pytest.raises(ValueError, match="assignment"):
        validate_analysis_inventory(participant, bad_assignment, retained, config)

    bad_prompt = assignment.copy()
    bad_prompt.loc[0, "prompt_score"] = 6
    with pytest.raises(ValueError, match="prompt score"):
        validate_analysis_inventory(participant, bad_prompt, retained, config)


def test_inventory_validation_error_messages_are_stable() -> None:
    config = QuantConfig.default()
    participant = pd.DataFrame({PARTICIPANT_KEY_COLUMN: ["p1"], "group": ["A"]})
    assignment = pd.DataFrame({"assignment": [9], "prompt_score": [1.0]})
    retained = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: ["p1", "p1"],
            "participant_id": ["p1", "p1"],
            "phase": [config.pre_label, config.post_label],
        }
    )

    with pytest.raises(ValueError) as assignment_error:
        validate_analysis_inventory(participant, assignment, retained, config)
    assert str(assignment_error.value) == "Invalid assignment values outside configured assignments"

    assignment["assignment"] = 1
    assignment["prompt_score"] = 6
    with pytest.raises(ValueError) as prompt_error:
        validate_analysis_inventory(participant, assignment, retained, config)
    assert str(prompt_error.value) == "Invalid prompt score outside 1-5"


def test_validate_no_transcripts_rejects_transcript_like_columns() -> None:
    with pytest.raises(ValueError) as exc_info:
        quant_preprocess._validate_no_transcripts(pd.DataFrame(columns=["participant_key", "user1"]))

    assert str(exc_info.value) == "prompt table contains transcript columns after preprocessing"


def test_inventory_validation_requires_exactly_one_pre_and_post_row() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    retained = pd.concat([retained, retained.iloc[[0]].copy()], ignore_index=True)
    participant = build_participant_table(retained, grades, prompts, config)
    assignment = build_assignment_prompt_table(prompts, participant, config)

    with pytest.raises(ValueError) as inventory_error:
        validate_analysis_inventory(participant, assignment, retained, config)
    assert str(inventory_error.value) == "retained survey participants must have exactly one pre and one post row"


def test_phase_inventory_rejects_participants_missing_one_phase() -> None:
    config = QuantConfig.default()
    retained = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: [participant_key("p1"), participant_key("p2")],
            "participant_id": ["p1", "p2"],
            "phase": [config.pre_label, config.post_label],
        }
    )

    with pytest.raises(ValueError) as phase_error:
        quant_preprocess._validate_phase_inventory(retained, config)
    assert str(phase_error.value) == "retained survey participants must have exactly one pre and one post row"


def test_phase_inventory_rejects_a_missing_phase_column() -> None:
    config = QuantConfig.default()
    retained = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: [participant_key("p1")],
            "participant_id": ["p1"],
            "phase": [config.pre_label],
        }
    )

    with pytest.raises(ValueError) as phase_error:
        quant_preprocess._validate_phase_inventory(retained, config)
    assert str(phase_error.value) == "retained survey participants must have exactly one pre and one post row"


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
    expected_rows = inventory.set_index("metric")["expected"]
    assert expected_rows["group_count_A"] == 2
    assert inventory.loc[inventory["metric"] == "group_count_A", "status"].iloc[0] == "pass"


def test_observed_inventory_preserves_all_public_metric_names_and_values() -> None:
    participant = pd.DataFrame({"group": ["B", "A", "A"]})
    assignment = pd.DataFrame({"prompt_score": [1.0, np.nan, 3.0]})
    retained = pd.DataFrame(index=range(4))

    assert quant_preprocess._observed_inventory(participant, assignment, retained) == {
        "retained_participants": 3,
        "retained_survey_rows": 4,
        "prompt_assignment_rows": 3,
        "scored_prompt_observations": 2,
        "missing_prompt_scores": 1,
        "group_count_A": 2,
        "group_count_B": 1,
    }


def test_expected_inventory_value_supports_direct_and_group_metrics() -> None:
    expected = cast(ExpectedInventory, {"retained_participants": 3, "group_counts": {"A": 2}})

    assert quant_preprocess._expected_inventory_value("retained_participants", expected) == 3
    assert quant_preprocess._expected_inventory_value("group_count_A", expected) == 2
    assert quant_preprocess._expected_inventory_value("group_count_B", expected) is None


def test_group_count_inventory_contract_names_are_centralized() -> None:
    assert EXPECTED_GROUP_COUNTS_KEY == "group_counts"
    assert GROUP_COUNT_METRIC_PREFIX == "group_count_"


@pytest.mark.parametrize("columns", [("participant_id",), ("assignment",)])
def test_prompt_assignment_uniqueness_ignores_incomplete_input_schema(columns: tuple[str, ...]) -> None:
    prompts = pd.DataFrame({column: ["value"] for column in columns})

    quant_preprocess._validate_prompt_assignment_uniqueness(prompts, QuantConfig.default())


def test_prompt_assignment_uniqueness_uses_participant_and_assignment_keys() -> None:
    prompts = pd.DataFrame(
        {
            "participant_id": ["p1", "p1"],
            "assignment": [1, 1],
            "prompt_score": [1.0, 2.0],
        }
    )

    with pytest.raises(ValueError, match="Duplicate prompt rows"):
        quant_preprocess._validate_prompt_assignment_uniqueness(prompts, QuantConfig.default())


def test_prompt_assignment_uniqueness_reports_only_first_three_duplicate_examples() -> None:
    prompts = pd.DataFrame(
        {
            "participant_id": [f"p{i}" for i in range(4) for _ in range(2)],
            "assignment": [1] * 8,
            "prompt_score": list(range(8)),
        }
    )

    with pytest.raises(ValueError) as exc_info:
        quant_preprocess._validate_prompt_assignment_uniqueness(prompts, QuantConfig.default())
    message = str(exc_info.value)
    assert message.count("assignment 1") == 3
    assert participant_key("p3") not in message
    assert "; " in message
    assert "XX; XX" not in message


def test_prompt_assignment_uniqueness_uses_participant_and_assignment_only() -> None:
    prompts = pd.DataFrame(
        {
            "participant_id": ["p1", "p1"],
            "assignment": [1, 1],
            "prompt_score": [1.0, 2.0],
        }
    )

    with pytest.raises(ValueError) as exc_info:
        quant_preprocess._validate_prompt_assignment_uniqueness(prompts, QuantConfig.default())

    assert str(exc_info.value).startswith("Duplicate prompt rows for participant assignment:")


def test_assignment_table_keeps_existing_group_when_group_x_is_also_present() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    participant["group_x"] = "wrong"

    assignment = build_assignment_prompt_table(prompts, participant, config)

    assert set(assignment["group"]) == {"A", "B", "C"}


def test_prompt_summary_drops_unscored_rows_and_keeps_key_column() -> None:
    prompts = pd.DataFrame(
        {
            "participant_id": ["p1", "p1"],
            "prompt_score": [4.0, np.nan],
        }
    )

    summary = quant_preprocess._prompt_summary(prompts, QuantConfig.default())

    assert summary.columns.tolist() == [PARTICIPANT_KEY_COLUMN, "mean_prompt_score", "scored_assignments"]
    assert summary[["mean_prompt_score", "scored_assignments"]].to_dict("records") == [
        {"mean_prompt_score": 4.0, "scored_assignments": 1}
    ]


def test_prompt_summary_drops_rows_for_missing_scores_only() -> None:
    prompts = pd.DataFrame(
        {
            "participant_id": [None, "p1"],
            "prompt_score": [4.0, np.nan],
        }
    )

    summary = quant_preprocess._prompt_summary(prompts, QuantConfig.default())

    assert len(summary) == 1
    assert summary["scored_assignments"].tolist() == [1]


def test_prompt_summary_preserves_explicit_groupby_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts = pd.DataFrame({"participant_id": ["p1"], "prompt_score": [4.0]})
    calls: list[dict[str, Any]] = []
    original_groupby = pd.DataFrame.groupby

    def recording_groupby(self: pd.DataFrame, *args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        return original_groupby(self, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "groupby", recording_groupby)

    quant_preprocess._prompt_summary(prompts, QuantConfig.default())

    assert calls[-1]["as_index"] is False


def test_phase_inventory_preserves_explicit_pivot_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    config = QuantConfig.default()
    retained = pd.DataFrame(
        {
            PARTICIPANT_KEY_COLUMN: [participant_key("p1"), participant_key("p1")],
            "participant_id": ["p1", "p1"],
            "phase": [config.pre_label, config.post_label],
        }
    )
    calls: list[dict[str, Any]] = []
    original_pivot_table = pd.DataFrame.pivot_table

    def recording_pivot_table(self: pd.DataFrame, *args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        return original_pivot_table(self, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "pivot_table", recording_pivot_table)

    quant_preprocess._validate_phase_inventory(retained, config)

    assert calls[-1]["values"] == config.columns.id
    assert calls[-1]["fill_value"] == 0


def test_build_assignment_prompt_table_removes_transcript_like_columns() -> None:
    survey, grades, prompts = synthetic_quant_frames()
    prompts["user1"] = "private transcript"
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts.drop(columns="user1"), config)

    assignment = build_assignment_prompt_table(prompts, participant, config)

    assert "user1" not in assignment.columns


def test_validate_assignment_labels_accepts_numeric_string_labels() -> None:
    quant_preprocess._validate_assignment_labels(
        pd.DataFrame({"assignment": ["1"]}),
        QuantConfig.default(),
    )


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


def test_prior_use_mapping_table_normalizes_missing_categories() -> None:
    config = QuantConfig.default()
    retained_survey = pd.DataFrame(
        {
            "participant_id": ["p1"],
            "phase": [config.pre_label],
            "prior_chatgpt_use": [None],
        }
    )

    mapping = prior_use_mapping_table(retained_survey, config)

    assert mapping.to_dict("records") == [
        {"prior_chatgpt_use": "", "n": 1, "mapped_score": None, "mapped_status": "unmapped"}
    ]


def test_prior_use_mapping_table_suppresses_only_counts_below_threshold() -> None:
    config = QuantConfig.default()
    retained_survey = pd.DataFrame(
        {
            "participant_id": ["p1", "p2", "p3", "p4"],
            "phase": [config.pre_label] * 4,
            "prior_chatgpt_use": ["low", "low", "high", "unknown"],
        }
    )

    mapping = prior_use_mapping_table(retained_survey, config, min_count=2)

    records = mapping[["prior_chatgpt_use", "n", "mapped_score", "mapped_status"]].to_dict("records")
    assert records[:2] == [
        {"prior_chatgpt_use": "high", "n": "suppressed", "mapped_score": 5.0, "mapped_status": "mapped"},
        {"prior_chatgpt_use": "low", "n": 2, "mapped_score": 1.0, "mapped_status": "mapped"},
    ]
    assert records[2]["prior_chatgpt_use"] == "unknown"
    assert records[2]["n"] == "suppressed"
    assert pd.isna(records[2]["mapped_score"])
    assert records[2]["mapped_status"] == "unmapped"


def test_inventory_row_reports_pass_and_rejects_mismatch() -> None:
    assert quant_preprocess._inventory_row("group_count_A", 2, {"group_counts": {"A": 2}}) == {
        "metric": "group_count_A",
        "observed": 2,
        "expected": 2,
        "status": "pass",
    }
    assert quant_preprocess._inventory_row("unconfigured_metric", 2, None) == {
        "metric": "unconfigured_metric",
        "observed": 2,
        "expected": None,
        "status": "pass",
    }

    with pytest.raises(ValueError, match="Inventory mismatch for group_count_A: observed 2, expected 3"):
        quant_preprocess._inventory_row("group_count_A", 2, {"group_counts": {"A": 3}})


def test_expected_inventory_value_handles_missing_group_counts_table() -> None:
    expected = cast(ExpectedInventory, {"retained_participants": 3})

    assert quant_preprocess._expected_inventory_value("group_count_A", expected) is None


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
