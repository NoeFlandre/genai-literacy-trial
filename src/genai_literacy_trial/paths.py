from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_SYNTHETIC_DIR = REPO_ROOT / "data" / "synthetic"
QUANT_CONFIG_TEMPLATE = REPO_ROOT / "config" / "quant_config.template.toml"
EXPECTED_INVENTORY_TEMPLATE = REPO_ROOT / "config" / "expected_inventory.template.toml"
REPRO_SMALL_PRIVATE_DIR = REPO_ROOT / "repro_outputs" / "small" / "private"
REPRO_SMALL_PUBLIC_DIR = REPO_ROOT / "repro_outputs" / "small" / "public"
