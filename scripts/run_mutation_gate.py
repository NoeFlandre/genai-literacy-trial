#!/usr/bin/env python
from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path


MUTATION_PATTERNS = (
    "genai_literacy_trial.quant_pipeline.x__read_input*",
    "genai_literacy_trial.quant_pipeline.x__validate_quant_input_frames*",
    "genai_literacy_trial.quant_preprocess.x_suppress_small_cells*",
    "genai_literacy_trial.quant_stats.x_welch_anova*",
    "genai_literacy_trial.validate_artifacts.x__validate_manifest*",
)

MUTATION_STATUS_BY_EXIT_CODE = {
    None: "not checked",
    0: "survived",
    1: "killed",
    2: "check was interrupted by user",
    3: "killed",
    5: "no tests",
    24: "timeout",
    33: "no tests",
    34: "skipped",
    35: "suspicious",
    36: "timeout",
    37: "caught by type check",
    152: "timeout",
    255: "timeout",
    -9: "segfault",
    -11: "segfault",
    -24: "timeout",
}


def mutation_failures(mutants_dir: Path = Path("mutants")) -> list[tuple[str, str]]:
    """Return targeted mutants that were not killed by the selected tests."""
    failures: list[tuple[str, str]] = []
    metadata_paths = sorted(mutants_dir.rglob("*.meta"))
    if not metadata_paths:
        return [(str(mutants_dir), "not checked")]

    for metadata_path in metadata_paths:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        exit_codes = metadata.get("exit_code_by_key")
        if not isinstance(exit_codes, dict):
            raise ValueError(f"Mutation metadata has no exit_code_by_key: {metadata_path}")
        for mutant_name, exit_code in exit_codes.items():
            if not isinstance(mutant_name, str):
                raise ValueError(f"Mutation metadata has a non-string mutant name: {metadata_path}")
            if not any(fnmatch.fnmatch(mutant_name, pattern) for pattern in MUTATION_PATTERNS):
                continue
            status = MUTATION_STATUS_BY_EXIT_CODE.get(exit_code, "suspicious")
            if status != "killed":
                failures.append((mutant_name, status))
    return sorted(failures)


def main() -> None:
    # Import numerical dependencies before mutmut's coverage pre-pass. This avoids
    # duplicate NumPy extension imports on macOS when mutmut unloads test modules.
    import matplotlib  # noqa: F401
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import scipy  # noqa: F401
    import statsmodels  # noqa: F401
    from mutmut.__main__ import cli

    default_run = len(sys.argv) == 1
    if default_run:
        sys.argv.extend(("run", "--max-children", "8", *MUTATION_PATTERNS))
    cli()
    if default_run:
        failures = mutation_failures()
        if failures:
            print(f"Mutation gate failed: {len(failures)} targeted mutant(s) were not killed.")
            for mutant_name, status in failures:
                print(f"  {mutant_name}: {status}")
            raise SystemExit(1)
        print("Mutation gate passed: all targeted mutants were killed.")


if __name__ == "__main__":
    main()
