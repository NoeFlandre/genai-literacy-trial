from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any

from genai_literacy_trial.analysis import GRADE_POINTS, LIKERT_POINTS


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


def load_quant_config(path: Path | None) -> QuantConfig:
    if path is None:
        return QuantConfig.default()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    columns = QuantColumns(**data.get("columns", {}))
    labels = data.get("labels", {})
    return QuantConfig(
        columns=columns,
        pre_label=str(labels.get("pre", "pre")),
        post_label=str(labels.get("post", "post")),
        groups=tuple(str(x) for x in labels.get("groups", ["A", "B", "C"])),
        assignments=tuple(int(x) for x in labels.get("assignments", [1, 2, 3, 4])),
        min_public_cell_count=int(data.get("privacy", {}).get("min_public_cell_count", 5)),
        survey_dimensions={str(k): list(v) for k, v in data.get("survey_dimensions", QuantConfig.default().survey_dimensions).items()},
        reverse_coded_items={str(k): list(v) for k, v in data.get("reverse_coded_items", {}).items()},
        likert_mapping={str(k): float(v) for k, v in data.get("likert_mapping", LIKERT_POINTS).items()},
        grade_mapping={str(k): float(v) for k, v in data.get("grade_mapping", GRADE_POINTS).items()},
    )


def load_expected_inventory(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))
