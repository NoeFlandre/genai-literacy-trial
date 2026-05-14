from __future__ import annotations

from pathlib import Path

import pandas as pd

NORMALIZED_PRE_LABEL = "pre"
NORMALIZED_POST_LABEL = "post"
PARTICIPANT_KEY_COLUMN = "participant_key"
PUBLIC_OUTPUT_DIR_KEY = "public_output_dir"
PRIVATE_OUTPUT_DIR_KEY = "private_output_dir"

QuantTableMap = dict[str, pd.DataFrame]
QuantPathMap = dict[str, Path]
