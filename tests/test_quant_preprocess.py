from __future__ import annotations

import math

import pandas as pd
import pytest

from genai_literacy_trial.quant_config import QuantConfig
from genai_literacy_trial.quant_pipeline import _reliability
from genai_literacy_trial.quant_preprocess import (
    build_assignment_prompt_table,
    build_participant_table,
    compute_survey_composites,
    prior_use_mapping_table,
    prepare_retained_survey,
    suppress_small_cells,
    validate_analysis_inventory,
)
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
    assert participant["participant_key"].is_unique
    assert set(participant["group"]) == {"A", "B", "C"}
    assert len(participant) == 5
    assert "participant_id" not in participant.columns
    assert "User" + "1" not in assignment.columns
    assert "GPT" + "1" not in assignment.columns
    assert assignment["assignment"].isin([1, 2, 3, 4]).all()
    assert assignment["prompt_score"].dropna().between(1, 5).all()


def test_survey_composites_reverse_code_and_require_half_items() -> None:
    survey, _, _ = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)

    composites = compute_survey_composites(retained, config)
    pre = composites[(composites["phase"] == "pre") & (composites["participant_key"].notna())].iloc[0]

    assert pre["perceived_usefulness"] >= 3
    assert math.isclose(pre["locus_of_control"], 4.0)
    assert "locus_of_control_items_present" in composites.columns


def test_reliability_reverse_codes_items_before_alpha() -> None:
    config = QuantConfig.default()
    retained = pd.DataFrame(
        {
            "participant_id": ["p1", "p2", "p3", "p4"],
            "phase": ["pre", "pre", "pre", "pre"],
            "control_1": [1, 2, 4, 5],
            "control_reverse": [5, 4, 2, 1],
        }
    )

    reliability = _reliability(retained, config)
    locus = reliability.loc[reliability["dimension"] == "locus_of_control", "cronbach_alpha"].iloc[0]

    assert locus > 0


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


def test_prior_use_mapping_table_flags_unmapped_categories() -> None:
    survey, _, _ = synthetic_quant_frames()
    config = QuantConfig.default()
    retained, _ = prepare_retained_survey(survey, config)
    retained.loc[retained[config.columns.phase] == config.pre_label, config.columns.prior_chatgpt_use] = "unknown category"

    mapping = prior_use_mapping_table(retained, config)

    assert set(mapping["mapped_status"]) == {"unmapped"}


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
