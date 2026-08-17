from pathlib import Path
from typing import get_type_hints

import pandas as pd
import pytest

from genai_literacy_trial.quant_config import ExpectedInventory, QuantConfig, load_expected_inventory, load_quant_config
from genai_literacy_trial.quant_preprocess import (
    build_assignment_prompt_table,
    build_participant_table,
    compute_survey_composites,
    prepare_retained_survey,
)
from genai_literacy_trial.quant_schema import NORMALIZED_POST_LABEL, NORMALIZED_PRE_LABEL


def test_load_quant_config_uses_default_optional_sections_when_omitted(tmp_path: Path) -> None:
    path = tmp_path / "minimal.toml"
    path.write_text("[columns]\nid = \"student\"\n", encoding="utf-8")

    loaded = load_quant_config(path)
    default = QuantConfig.default()

    assert loaded.columns.id == "student"
    assert loaded.likert_mapping == default.likert_mapping
    assert loaded.grade_mapping == default.grade_mapping
    assert loaded.survey_dimensions == default.survey_dimensions
    assert loaded.reverse_coded_items == default.reverse_coded_items


def test_expected_inventory_type_contract_is_explicit() -> None:
    expected: ExpectedInventory = load_expected_inventory(None)

    assert expected == {}


def test_missing_explicit_expected_inventory_path_fails_fast(tmp_path: Path) -> None:
    missing = tmp_path / "missing_expected_inventory.toml"

    with pytest.raises(FileNotFoundError, match="Expected inventory file not found"):
        load_expected_inventory(missing)


def test_expected_inventory_declares_known_inventory_keys() -> None:
    assert get_type_hints(ExpectedInventory) == {
        "pre_responses": int,
        "post_responses": int,
        "retained_participants": int,
        "retained_survey_rows": int,
        "prompt_assignment_rows": int,
        "scored_prompt_observations": int,
        "missing_prompt_scores": int,
        "group_counts": dict[str, int],
    }


def test_loaded_column_aliases_drive_public_preprocessing_contract(tmp_path: Path) -> None:
    path = tmp_path / "aliased.toml"
    path.write_text(
        """
[columns]
id = "student"
phase = "wave"
group = "arm"
assignment = "task"
prompt_score = "score"
midterm_grade = "mid"
final_grade = "final"
prior_chatgpt_use = "use"
gender = "sex"
major = "program"

[labels]
pre = "baseline"
post = "followup"
groups = ["control"]
assignments = [1, 2]
""",
        encoding="utf-8",
    )
    config = load_quant_config(path)
    survey = pd.DataFrame(
        {
            "student": ["s1", "s1"],
            "wave": ["baseline", "followup"],
            "arm": ["control", "control"],
            "use": ["low", "low"],
            "useful_1": ["Agree", "Strongly agree"],
            "useful_2": ["Agree", "Agree"],
        }
    )
    grades = pd.DataFrame({"student": ["s1"], "arm": ["control"], "mid": ["B"], "final": ["A"], "sex": ["X"], "program": ["M1"]})
    prompts = pd.DataFrame({"student": ["s1", "s1"], "task": [1, 2], "score": [3.0, 4.0]})

    retained, summary = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    assignment = build_assignment_prompt_table(prompts, participant, config)
    composites = compute_survey_composites(retained, config)

    assert summary["retained_participants"] == 1
    assert participant.loc[0, "group"] == "control"
    assert participant.loc[0, "mean_prompt_score"] == 3.5
    assert assignment["assignment"].tolist() == [1, 2]
    assert composites["phase"].tolist() == [NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL]


@pytest.mark.parametrize(
    ("toml_text", "message"),
    [
        ("[labels]\npre = \"same\"\npost = \"same\"\n", "pre and post labels must differ"),
        ("[labels]\ngroups = [\"A\", \"A\"]\n", "groups must be unique"),
        ("[labels]\nassignments = [1, 1]\n", "assignments must be unique"),
        ("[privacy]\nmin_public_cell_count = 0\n", "min_public_cell_count must be at least 1"),
    ],
)
def test_load_quant_config_rejects_invalid_scientific_contracts(tmp_path: Path, toml_text: str, message: str) -> None:
    path = tmp_path / "invalid.toml"
    path.write_text(toml_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_quant_config(path)
