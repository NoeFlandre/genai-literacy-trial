from pathlib import Path

from genai_literacy_trial.quant_config import QuantConfig, load_quant_config


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
