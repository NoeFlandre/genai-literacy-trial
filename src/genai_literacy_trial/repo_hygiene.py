from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Sequence

from genai_literacy_trial.paths import REPO_ROOT


DEFAULT_MAX_MIB = 5.0


def _git_process_error(root: Path, exc: subprocess.CalledProcessError) -> RuntimeError:
    stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
    detail = stderr.strip() or f"exit status {exc.returncode}"
    return RuntimeError(f"git ls-files failed for {root}: {detail}")


def _run_git_ls_files(root: Path) -> bytes:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable was not found; install git or run this check in an environment with git available") from exc
    except subprocess.CalledProcessError as exc:
        raise _git_process_error(root, exc) from exc
    return result.stdout


def tracked_files(root: Path) -> list[Path]:
    return [root / raw.decode("utf-8") for raw in _run_git_ls_files(root).split(b"\0") if raw]


def oversized_tracked_files(root: Path, max_mib: float) -> list[tuple[Path, float]]:
    max_bytes = int(max_mib * 1024 * 1024)
    oversized: list[tuple[Path, float]] = []
    for path in tracked_files(root):
        if not path.exists() or not path.is_file():
            continue
        size = path.stat().st_size
        if size > max_bytes:
            oversized.append((path.relative_to(root), size / (1024 * 1024)))
    return oversized


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check lightweight repository hygiene rules for CI.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root.")
    parser.add_argument("--max-mib", type=float, default=DEFAULT_MAX_MIB, help="Maximum allowed tracked file size in MiB.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    oversized = oversized_tracked_files(args.root, args.max_mib)
    if not oversized:
        print(f"Repository hygiene passed: no tracked files exceed {args.max_mib:g} MiB.")
        return 0
    print(f"Repository hygiene failed: tracked files exceed {args.max_mib:g} MiB.")
    for path, size_mib in oversized:
        print(f"{path}: {size_mib:.2f} MiB")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
