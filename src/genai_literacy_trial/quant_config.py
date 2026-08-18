from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import TypedDict, cast

from genai_literacy_trial.scales import GRADE_POINTS, LIKERT_POINTS


class ExpectedInventory(TypedDict, total=False):
    pre_responses: int
    post_responses: int
    retained_participants: int
    retained_survey_rows: int
    prompt_assignment_rows: int
    scored_prompt_observations: int
    missing_prompt_scores: int
    group_counts: dict[str, int]


_EXPECTED_INVENTORY_SCALAR_KEYS = (
    "pre_responses",
    "post_responses",
    "retained_participants",
    "retained_survey_rows",
    "prompt_assignment_rows",
    "scored_prompt_observations",
    "missing_prompt_scores",
)
_EXPECTED_INVENTORY_KEYS = frozenset((*_EXPECTED_INVENTORY_SCALAR_KEYS, "group_counts"))


@dataclass(frozen=True)
class QuantColumns:
    id: str = "participant_id"
    phase: str = "phase"
    group: str = "group"
    assignment: str = "assignment"
    prompt_score: str = "prompt_score"
    midterm_grade: str = "midterm_grade"
    final_grade: str = "final_grade"
    prior_chatgpt_use: str = "prior_chatgpt_use"
    gender: str = "gender"
    major: str = "major"


@dataclass(frozen=True)
class QuantConfig:
    columns: QuantColumns = field(default_factory=QuantColumns)
    pre_label: str = "pre"
    post_label: str = "post"
    groups: tuple[str, ...] = ("A", "B", "C")
    assignments: tuple[int, ...] = (1, 2, 3, 4)
    min_public_cell_count: int = 5
    survey_dimensions: dict[str, list[str]] = field(
        default_factory=lambda: {
            "perceived_usefulness": ["useful_1", "useful_2"],
            "locus_of_control": ["control_1", "control_reverse"],
            "trust": ["trust_1", "trust_2"],
            "perceived_ease_of_use": ["useful_1"],
            "behavioral_intention": ["useful_2"],
            "hedonic_motivation": ["trust_1"],
            "facilitating_conditions": ["trust_2"],
            "social_influence": ["control_1"],
            "attitude": ["useful_1", "trust_1"],
        }
    )
    reverse_coded_items: dict[str, list[str]] = field(default_factory=lambda: {"locus_of_control": ["control_reverse"]})
    likert_mapping: dict[str, float] = field(
        default_factory=lambda: {**{k: float(v) for k, v in LIKERT_POINTS.items()}, "low": 1.0, "high": 5.0}
    )
    grade_mapping: dict[str, float] = field(default_factory=lambda: {k: float(v) for k, v in GRADE_POINTS.items()})

    @classmethod
    def default(cls) -> "QuantConfig":
        return cls()


_CONFIG_SECTIONS = frozenset(
    {
        "columns",
        "labels",
        "privacy",
        "survey_dimensions",
        "reverse_coded_items",
        "likert_mapping",
        "grade_mapping",
    }
)
_COLUMN_KEYS = frozenset(QuantColumns.__dataclass_fields__)
_LABEL_KEYS = frozenset({"pre", "post", "groups", "assignments"})
_PRIVACY_KEYS = frozenset({"min_public_cell_count"})


def _as_table(value: object, section: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{section} must be a table")
    return cast(dict[str, object], value)


def _reject_unknown_keys(data: dict[str, object], allowed: frozenset[str], section: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"Unknown configuration keys in {section}: {', '.join(unknown)}")


def _require_string(value: object, field: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")


def _require_string_list(value: object, field: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be an array of strings")


def _require_integer(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")


def _require_integer_list(value: object, field: str) -> None:
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise ValueError(f"{field} must be an array of integers")


def _validate_string_list_table(value: object, section: str) -> None:
    table = _as_table(value, section)
    for key, items in table.items():
        _require_string_list(items, f"{section}.{key}")


def _validate_numeric_table(value: object, section: str) -> None:
    table = _as_table(value, section)
    for key, item in table.items():
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{section}.{key} must be a number")


def _validate_quant_config_schema(data: object) -> None:
    config = _as_table(data, "configuration")
    unknown_sections = sorted(set(config) - _CONFIG_SECTIONS)
    if unknown_sections:
        raise ValueError(f"Unknown configuration section: {', '.join(unknown_sections)}")

    columns = _as_table(config.get("columns", {}), "columns")
    _reject_unknown_keys(columns, _COLUMN_KEYS, "columns")
    for key, value in columns.items():
        _require_string(value, f"columns.{key}")

    labels = _as_table(config.get("labels", {}), "labels")
    _reject_unknown_keys(labels, _LABEL_KEYS, "labels")
    for key in ("pre", "post"):
        if key in labels:
            _require_string(labels[key], f"labels.{key}")
    if "groups" in labels:
        _require_string_list(labels["groups"], "labels.groups")
    if "assignments" in labels:
        _require_integer_list(labels["assignments"], "labels.assignments")

    privacy = _as_table(config.get("privacy", {}), "privacy")
    _reject_unknown_keys(privacy, _PRIVACY_KEYS, "privacy")
    if "min_public_cell_count" in privacy:
        _require_integer(privacy["min_public_cell_count"], "privacy.min_public_cell_count")

    _validate_string_list_table(config.get("survey_dimensions", {}), "survey_dimensions")
    _validate_string_list_table(config.get("reverse_coded_items", {}), "reverse_coded_items")
    _validate_numeric_table(config.get("likert_mapping", {}), "likert_mapping")
    _validate_numeric_table(config.get("grade_mapping", {}), "grade_mapping")


def load_quant_config(path: Path | None) -> QuantConfig:
    if path is None:
        return _validate_quant_config(QuantConfig.default())
    default = QuantConfig.default()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    _validate_quant_config_schema(data)
    columns = QuantColumns(**data.get("columns", {}))
    labels = data.get("labels", {})
    return _validate_quant_config(
        QuantConfig(
            columns=columns,
            pre_label=str(labels.get("pre", default.pre_label)),
            post_label=str(labels.get("post", default.post_label)),
            groups=tuple(str(x) for x in labels.get("groups", default.groups)),
            assignments=tuple(int(x) for x in labels.get("assignments", default.assignments)),
            min_public_cell_count=int(data.get("privacy", {}).get("min_public_cell_count", default.min_public_cell_count)),
            survey_dimensions={str(k): list(v) for k, v in data.get("survey_dimensions", default.survey_dimensions).items()},
            reverse_coded_items={str(k): list(v) for k, v in data.get("reverse_coded_items", default.reverse_coded_items).items()},
            likert_mapping={str(k): float(v) for k, v in data.get("likert_mapping", default.likert_mapping).items()},
            grade_mapping={str(k): float(v) for k, v in data.get("grade_mapping", default.grade_mapping).items()},
        )
    )


def _validate_quant_config(config: QuantConfig) -> QuantConfig:
    if config.pre_label == config.post_label:
        raise ValueError("pre and post labels must differ")
    if not config.groups:
        raise ValueError("groups must include at least one label")
    if len(set(config.groups)) != len(config.groups):
        raise ValueError("groups must be unique")
    if not config.assignments:
        raise ValueError("assignments must include at least one value")
    if len(set(config.assignments)) != len(config.assignments):
        raise ValueError("assignments must be unique")
    if config.min_public_cell_count < 1:
        raise ValueError("min_public_cell_count must be at least 1")
    return config


def load_expected_inventory(path: Path | None) -> ExpectedInventory:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Expected inventory file not found: {path}")
    data = cast(dict[str, object], tomllib.loads(path.read_text(encoding="utf-8")))
    unknown_keys = sorted(set(data) - _EXPECTED_INVENTORY_KEYS)
    if unknown_keys:
        raise ValueError(f"Unknown expected inventory keys: {', '.join(unknown_keys)}: {path}")

    for key in _EXPECTED_INVENTORY_SCALAR_KEYS:
        value = data.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{key} must be a non-negative integer: {path}")

    if "group_counts" in data:
        group_counts = data["group_counts"]
        if not isinstance(group_counts, dict):
            raise ValueError(f"group_counts must be a table: {path}")
        for group, value in group_counts.items():
            if not isinstance(group, str):
                raise ValueError(f"group_counts keys must be strings: {path}")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"group_counts.{group} must be a non-negative integer: {path}")

    return cast(ExpectedInventory, data)
