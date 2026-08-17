from __future__ import annotations

import argparse
import warnings
from contextlib import nullcontext
from pathlib import Path
from typing import Sequence

from statsmodels.tools.sm_exceptions import ConvergenceWarning

from genai_literacy_trial.paths import (
    DATA_SYNTHETIC_DIR,
    EXPECTED_INVENTORY_TEMPLATE,
    QUANT_CONFIG_TEMPLATE,
    REPRO_SMALL_PRIVATE_DIR,
    REPRO_SMALL_PUBLIC_DIR,
)
from genai_literacy_trial.quant_pipeline import run_quant_analysis
from genai_literacy_trial.validate_artifacts import print_validation_report, validate_artifacts


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the public synthetic quantitative smoke workflow.")
    parser.add_argument("--input-dir", type=Path, default=DATA_SYNTHETIC_DIR, help="Directory containing public synthetic inputs.")
    parser.add_argument("--config", type=Path, default=QUANT_CONFIG_TEMPLATE, help="Quantitative TOML configuration.")
    parser.add_argument("--expected-inventory", type=Path, default=EXPECTED_INVENTORY_TEMPLATE, help="Expected synthetic inventory TOML.")
    parser.add_argument("--output-dir", type=Path, default=REPRO_SMALL_PRIVATE_DIR, help="Local private diagnostics directory.")
    parser.add_argument("--public-output-dir", type=Path, default=REPRO_SMALL_PUBLIC_DIR, help="Public aggregate artifact directory.")
    parser.add_argument("--allow-stale", action="store_true", help="Allow validator stale-output warnings to pass.")
    parser.add_argument("--show-model-warnings", action="store_true", help="Show statsmodels/numpy warnings from tiny synthetic-data model fits.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    warning_context = nullcontext() if args.show_model_warnings else warnings.catch_warnings()
    with warning_context:
        if not args.show_model_warnings:
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
        paths = run_quant_analysis(
            args.input_dir,
            args.config,
            args.expected_inventory,
            args.output_dir,
            args.public_output_dir,
        )
    issues = validate_artifacts(
        mode="small",
        input_dir=args.input_dir,
        config=args.config,
        expected_inventory=args.expected_inventory,
        public_output_dir=args.public_output_dir,
        allow_stale=args.allow_stale,
    )
    print_validation_report(issues)
    if issues:
        return 1
    print(f"Small reproducibility run complete. Public outputs: {paths['public_output_dir']}")
    print(f"Local diagnostics directory: {paths['private_output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
