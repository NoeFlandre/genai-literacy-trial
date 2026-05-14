from __future__ import annotations

from pathlib import Path

import pandas as pd

NORMALIZED_PRE_LABEL = "pre"
NORMALIZED_POST_LABEL = "post"
PARTICIPANT_KEY_COLUMN = "participant_key"

QuantTableMap = dict[str, pd.DataFrame]
QuantPathMap = dict[str, Path]
