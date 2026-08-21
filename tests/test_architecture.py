from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "genai_literacy_trial"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_package_does_not_depend_on_compatibility_scripts() -> None:
    violations = {
        f"{path.relative_to(REPO_ROOT)} imports {module}"
        for path in PACKAGE_ROOT.glob("*.py")
        for module in _imported_modules(path)
        if module == "scripts" or module.startswith("scripts.")
    }

    assert violations == set()


def test_compatibility_wrappers_delegate_to_package_modules() -> None:
    expected = {
        "scripts/check_repo_hygiene.py": "genai_literacy_trial.repo_hygiene",
        "scripts/reproduce_small.py": "genai_literacy_trial.reproduce_small",
        "scripts/validate_artifacts.py": "genai_literacy_trial.validate_artifacts",
    }

    for relative_path, module in expected.items():
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert f"from {module} import main" in source
