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
    prepare_retained_survey,
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
