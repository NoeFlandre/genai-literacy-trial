from __future__ import annotations

from genai_literacy_trial.quant_schema import (
    NORMALIZED_POST_LABEL,
    NORMALIZED_PRE_LABEL,
    PARTICIPANT_KEY_COLUMN,
    PRIVATE_OUTPUT_DIR_KEY,
    PUBLIC_OUTPUT_DIR_KEY,
    QuantPathMap,
    QuantTableMap,
)


def test_internal_quant_schema_constants_are_explicit() -> None:
    assert PARTICIPANT_KEY_COLUMN == "participant_key"
    assert NORMALIZED_PRE_LABEL == "pre"
    assert NORMALIZED_POST_LABEL == "post"


def test_quant_output_path_keys_are_explicit() -> None:
    assert PUBLIC_OUTPUT_DIR_KEY == "public_output_dir"
    assert PRIVATE_OUTPUT_DIR_KEY == "private_output_dir"


def test_quant_table_map_type_alias_is_importable() -> None:
    tables: QuantTableMap = {}

    assert tables == {}


def test_quant_path_map_type_alias_is_importable() -> None:
    paths: QuantPathMap = {}

    assert paths == {}
