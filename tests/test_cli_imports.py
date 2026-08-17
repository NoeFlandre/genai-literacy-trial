from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_importing_cli_does_not_initialize_matplotlib() -> None:
    environment = os.environ.copy()
    source_path = str(REPO_ROOT / "src")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [source_path, environment.get("PYTHONPATH", "")]))
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import genai_literacy_trial.cli; assert 'matplotlib' not in sys.modules",
        ],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
