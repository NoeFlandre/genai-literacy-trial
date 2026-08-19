from __future__ import annotations

import tomllib
from pathlib import Path

from scripts.check_crap import MAX_CRAP_SCORE, CrapResult
from scripts.run_mutation_gate import mutation_failures

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_quality_tooling_declares_ty_and_runs_it_in_ci() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = project["dependency-groups"]["dev"]
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert any(dependency == "ty" or dependency.startswith("ty ") or dependency.startswith("ty>") for dependency in dev_dependencies)
    assert "uv run ty check ." in ci_text


def test_crap_score_gate_is_strictly_below_six() -> None:
    assert MAX_CRAP_SCORE == 6.0
    assert CrapResult("module.py", "covered", 1, 5, 100.0).score < MAX_CRAP_SCORE
    assert CrapResult("module.py", "uncovered", 1, 5, 0.0).score >= MAX_CRAP_SCORE


def test_mutation_gate_reports_targeted_survivors_and_unchecked_mutants(tmp_path: Path) -> None:
    metadata_path = tmp_path / "src" / "module.py.meta"
    metadata_path.parent.mkdir()
    metadata_path.write_text(
        "{\"exit_code_by_key\": {"
        "\"genai_literacy_trial.quant_pipeline.x__read_input__mutmut_killed\": 1,"
        "\"genai_literacy_trial.quant_pipeline.x__read_input__mutmut_survived\": 0,"
        "\"genai_literacy_trial.quant_pipeline.x__read_input__mutmut_unchecked\": null,"
        "\"unrelated\": 0}}",
        encoding="utf-8",
    )

    assert mutation_failures(tmp_path) == [
        (
            "genai_literacy_trial.quant_pipeline.x__read_input__mutmut_survived",
            "survived",
        ),
        (
            "genai_literacy_trial.quant_pipeline.x__read_input__mutmut_unchecked",
            "not checked",
        ),
    ]
