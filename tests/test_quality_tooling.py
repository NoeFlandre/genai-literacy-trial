from __future__ import annotations

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_quality_tooling_declares_ty_and_runs_it_in_ci() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = project["dependency-groups"]["dev"]
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert any(dependency == "ty" or dependency.startswith("ty ") or dependency.startswith("ty>") for dependency in dev_dependencies)
    assert "uv run ty check ." in ci_text
