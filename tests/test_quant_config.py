from pathlib import Path
from typing import get_type_hints

import pandas as pd
import pytest

import genai_literacy_trial.quant_config as quant_config
from genai_literacy_trial.quant_config import (
    ExpectedInventory,
    QuantColumns,
    QuantConfig,
    load_expected_inventory,
    load_quant_config,
)
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
    assert loaded.pre_label == default.pre_label
    assert loaded.post_label == default.post_label
    assert loaded.groups == default.groups
    assert loaded.assignments == default.assignments
    assert loaded.min_public_cell_count == default.min_public_cell_count
    assert loaded.likert_mapping == default.likert_mapping
    assert loaded.grade_mapping == default.grade_mapping
    assert loaded.survey_dimensions == default.survey_dimensions
    assert loaded.reverse_coded_items == default.reverse_coded_items


def test_load_quant_config_honors_every_public_section(tmp_path: Path) -> None:
    path = tmp_path / "complete.toml"
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
groups = ["control", "treatment"]
assignments = [10, 20]

[privacy]
min_public_cell_count = 7

[survey_dimensions]
confidence = ["confidence_1", "confidence_2"]

[reverse_coded_items]
confidence = ["confidence_2"]

[likert_mapping]
low = 1.0
high = 5.0

[grade_mapping]
A = 4.0
B = 3.0
""",
        encoding="utf-8",
    )

    assert load_quant_config(path) == QuantConfig(
        columns=QuantColumns(
            id="student",
            phase="wave",
            group="arm",
            assignment="task",
            prompt_score="score",
            midterm_grade="mid",
            final_grade="final",
            prior_chatgpt_use="use",
            gender="sex",
            major="program",
        ),
        pre_label="baseline",
        post_label="followup",
        groups=("control", "treatment"),
        assignments=(10, 20),
        min_public_cell_count=7,
        survey_dimensions={"confidence": ["confidence_1", "confidence_2"]},
        reverse_coded_items={"confidence": ["confidence_2"]},
        likert_mapping={"low": 1.0, "high": 5.0},
        grade_mapping={"A": 4.0, "B": 3.0},
    )


def test_expected_inventory_type_contract_is_explicit() -> None:
    expected: ExpectedInventory = load_expected_inventory(None)

    assert expected == {}


def test_missing_explicit_expected_inventory_path_fails_fast(tmp_path: Path) -> None:
    missing = tmp_path / "missing_expected_inventory.toml"

    with pytest.raises(FileNotFoundError, match="Expected inventory file not found"):
        load_expected_inventory(missing)


def test_load_expected_inventory_accepts_partial_known_inventory(tmp_path: Path) -> None:
    path = tmp_path / "partial_expected_inventory.toml"
    path.write_text("[group_counts]\nA = 2\n", encoding="utf-8")

    assert load_expected_inventory(path) == {"group_counts": {"A": 2}}


def test_load_expected_inventory_accepts_zero_counts(tmp_path: Path) -> None:
    path = tmp_path / "zero_expected_inventory.toml"
    path.write_text(
        "pre_responses = 0\npost_responses = 0\n[group_counts]\nA = 0\n",
        encoding="utf-8",
    )

    assert load_expected_inventory(path) == {
        "pre_responses": 0,
        "post_responses": 0,
        "group_counts": {"A": 0},
    }


@pytest.mark.parametrize(
    ("toml_text", "message"),
    [
        ("pre_response = 6\n", "Unknown expected inventory keys: pre_response"),
        ("pre_responses = \"6\"\n", "pre_responses must be a non-negative integer"),
        ("pre_responses = -1\n", "pre_responses must be a non-negative integer"),
        ("group_counts = 1\n", "group_counts must be a table"),
        ("[group_counts]\nA = \"2\"\n", "group_counts.A must be a non-negative integer"),
    ],
)
def test_load_expected_inventory_rejects_invalid_schema(tmp_path: Path, toml_text: str, message: str) -> None:
    path = tmp_path / "invalid_expected_inventory.toml"
    path.write_text(toml_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_expected_inventory(path)


def test_expected_inventory_errors_preserve_source_path(tmp_path: Path) -> None:
    path = tmp_path / "invalid_expected_inventory.toml"
    path.write_text("pre_responses = -1\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        load_expected_inventory(path)

    assert str(exc_info.value) == f"pre_responses must be a non-negative integer: {path}"


def test_expected_inventory_unknown_key_error_sorts_all_keys(tmp_path: Path) -> None:
    path = tmp_path / "unknown_expected_inventory.toml"
    path.write_text("z_extra = 1\na_extra = 2\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        load_expected_inventory(path)

    assert str(exc_info.value) == f"Unknown expected inventory keys: a_extra, z_extra: {path}"


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

    with pytest.raises(ValueError) as exc_info:
        load_quant_config(path)
    assert str(exc_info.value) == message


@pytest.mark.parametrize(
    "section",
    (
        "columns",
        "labels",
        "privacy",
        "survey_dimensions",
        "reverse_coded_items",
        "likert_mapping",
        "grade_mapping",
    ),
)
def test_build_quant_config_preserves_non_table_section_name(section: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        quant_config._build_quant_config({section: 1}, QuantConfig.default())

    assert str(exc_info.value) == f"{section} must be a table"


def test_quant_config_schema_preserves_root_and_unknown_section_errors() -> None:
    with pytest.raises(ValueError) as root_error:
        quant_config._validate_quant_config_schema([])
    assert str(root_error.value) == "configuration must be a table"

    with pytest.raises(ValueError) as unknown_error:
        quant_config._validate_quant_config_schema({"z_extra": {}, "a_extra": {}})
    assert str(unknown_error.value) == "Unknown configuration section: a_extra, z_extra"


def test_mapping_helpers_preserve_section_name_for_non_tables() -> None:
    with pytest.raises(ValueError) as string_error:
        quant_config._string_list_mapping(1, "survey_dimensions")
    assert str(string_error.value) == "survey_dimensions must be a table"

    with pytest.raises(ValueError) as numeric_error:
        quant_config._numeric_mapping(1, "grade_mapping")
    assert str(numeric_error.value) == "grade_mapping must be a table"


def test_quant_config_accepts_minimum_public_cell_count() -> None:
    config = QuantConfig(min_public_cell_count=1)

    assert quant_config._validate_quant_config(config) == config


@pytest.mark.parametrize(
    ("toml_text", "message"),
    [
        ("[lables]\npre = \"baseline\"\n", "Unknown configuration section: lables"),
        ("[columns]\nid = 1\n", "columns.id must be a string"),
        ("[labels]\npre = 1\n", "labels.pre must be a string"),
        ("[labels]\npost = 1\n", "labels.post must be a string"),
        ("[labels]\ngroups = \"ABC\"\n", "labels.groups must be an array of strings"),
        ("[labels]\ngroups = [\"A\", 2]\n", "labels.groups must be an array of strings"),
        ("[labels]\nassignments = \"12\"\n", "labels.assignments must be an array of integers"),
        ("[labels]\nassignments = [true]\n", "labels.assignments must be an array of integers"),
        ("[privacy]\nmin_public_cell_count = \"5\"\n", "privacy.min_public_cell_count must be an integer"),
        ("[survey_dimensions]\nattitude = \"useful_1\"\n", "survey_dimensions.attitude must be an array of strings"),
        ("[reverse_coded_items]\nattitude = [1]\n", "reverse_coded_items.attitude must be an array of strings"),
        ("[likert_mapping]\nlow = \"5\"\n", "likert_mapping.low must be a number"),
        ("[grade_mapping]\nA = true\n", "grade_mapping.A must be a number"),
    ],
)
def test_load_quant_config_rejects_malformed_toml_schema(tmp_path: Path, toml_text: str, message: str) -> None:
    path = tmp_path / "malformed.toml"
    path.write_text(toml_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_quant_config(path)


@pytest.mark.parametrize(
    ("toml_text", "message"),
    [
        ("columns = 1\n", "columns must be a table"),
        ("labels = 1\n", "labels must be a table"),
        ("privacy = 1\n", "privacy must be a table"),
        ("survey_dimensions = 1\n", "survey_dimensions must be a table"),
        ("reverse_coded_items = 1\n", "reverse_coded_items must be a table"),
        ("likert_mapping = 1\n", "likert_mapping must be a table"),
        ("grade_mapping = 1\n", "grade_mapping must be a table"),
    ],
)
def test_load_quant_config_rejects_non_tables_for_known_sections(tmp_path: Path, toml_text: str, message: str) -> None:
    path = tmp_path / "non_table.toml"
    path.write_text(toml_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_quant_config(path)


@pytest.mark.parametrize(
    ("toml_text", "message"),
    [
        ("[columns]\nunknown = \"value\"\n", "Unknown configuration keys in columns: unknown"),
        ("[labels]\nunknown = \"value\"\n", "Unknown configuration keys in labels: unknown"),
        ("[privacy]\nunknown = 1\n", "Unknown configuration keys in privacy: unknown"),
    ],
)
def test_load_quant_config_rejects_unknown_keys_in_known_sections(tmp_path: Path, toml_text: str, message: str) -> None:
    path = tmp_path / "unknown_key.toml"
    path.write_text(toml_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_quant_config(path)
