from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from genai_literacy_trial import repo_hygiene


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_repo_hygiene_module_entry_point_passes_with_current_threshold() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "genai_literacy_trial.repo_hygiene"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Repository hygiene passed" in result.stdout


def test_repo_hygiene_reports_git_ls_files_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail_git_ls_files(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.CalledProcessError(128, ["git", "ls-files", "-z"], stderr=b"fatal: not a git repository")

    monkeypatch.setattr(repo_hygiene.subprocess, "run", fail_git_ls_files)

    with pytest.raises(RuntimeError, match="git ls-files failed.*not a git repository"):
        repo_hygiene.tracked_files(tmp_path)


def test_oversized_tracked_files_reports_only_files_over_threshold(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    small = tmp_path / "small.txt"
    large = tmp_path / "large.txt"
    small.write_bytes(b"x")
    large.write_bytes(b"x" * 11)
    monkeypatch.setattr(repo_hygiene, "tracked_files", lambda _root: [small, large])

    assert repo_hygiene.oversized_tracked_files(tmp_path, max_mib=10 / (1024 * 1024)) == [(large.relative_to(tmp_path), 11 / (1024 * 1024))]


def test_repo_hygiene_main_reports_pass_and_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr(repo_hygiene, "oversized_tracked_files", lambda *_args: [])
    assert repo_hygiene.main(["--root", str(tmp_path)]) == 0
    assert "Repository hygiene passed" in capsys.readouterr().out

    monkeypatch.setattr(repo_hygiene, "oversized_tracked_files", lambda *_args: [(Path("large.bin"), 6.0)])
    assert repo_hygiene.main(["--root", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "Repository hygiene failed" in output
    assert "large.bin: 6.00 MiB" in output
