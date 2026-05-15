from pathlib import Path
from typing import get_type_hints

from genai_literacy_trial.quant_config import ExpectedInventory, QuantConfig, load_expected_inventory, load_quant_config


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
