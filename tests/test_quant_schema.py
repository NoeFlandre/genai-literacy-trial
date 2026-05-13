from __future__ import annotations

from genai_literacy_trial.quant_schema import (
    NORMALIZED_POST_LABEL,
    NORMALIZED_PRE_LABEL,
    PARTICIPANT_KEY_COLUMN,
)


def test_internal_quant_schema_constants_are_explicit() -> None:
    assert PARTICIPANT_KEY_COLUMN == "participant_key"
    assert NORMALIZED_PRE_LABEL == "pre"
    assert NORMALIZED_POST_LABEL == "post"
