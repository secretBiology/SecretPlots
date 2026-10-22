"""Explicit, shared handling of missing and non-finite plot input."""

from collections.abc import Sequence
from typing import Literal

import numpy as np
import pandas as pd

from SecretPlots.errors import DataShapeError

MissingPolicy = Literal["raise", "drop", "gap"]
# For plots with no position to leave empty (bars, distributions, points).
DropPolicy = Literal["raise", "drop"]


def numeric_array(data: object) -> np.ndarray:
    """Read numeric arrays without mistaking pd.NA for a shape error."""
    values = np.asarray(data, dtype=object)
    values = np.where(pd.isna(values), np.nan, values)
    return np.asarray(values, dtype=float)


def check_missing(policy: MissingPolicy, *, gap: bool = False) -> None:
    allowed = ("raise", "drop", "gap") if gap else ("raise", "drop")
    if policy not in allowed:
        raise ValueError(
            f"missing={policy!r} is not supported here. Use "
            + ", ".join(f"missing={p!r}" for p in allowed)
            + "."
        )


def handle_missing(
    frame: pd.DataFrame,
    policy: MissingPolicy,
    *,
    values: Sequence[str],
    keys: Sequence[str] = (),
    gap: bool = False,
) -> pd.DataFrame:
    """Validate plotted columns; gap preserves value NaNs but requires keys.

    Only plotted fields participate, so unrelated metadata may be missing.
    Infinities count as missing values. The caller owns numeric conversion.
    """
    check_missing(policy, gap=gap)
    frame = frame.copy()
    columns = list(dict.fromkeys([*keys, *values]))
    for column in columns:
        frame[column] = frame[column].mask(frame[column].isin([np.inf, -np.inf]))
    bad = frame[columns].isna()
    affected = bad.any(axis=1)
    if affected.any():
        invalid_keys = bool(keys) and bool(bad[list(keys)].any(axis=None))
        if policy == "raise" or (policy == "gap" and invalid_keys):
            fields = ", ".join(str(c) for c in bad.columns[bad.any()])
            hint = "Use missing='drop' to ignore those rows"
            if gap and not invalid_keys:
                hint += ", or missing='gap' to preserve missing positions"
            raise DataShapeError(
                f"Missing or non-finite data in {fields} "
                f"({int(affected.sum())} row(s)). {hint}. "
                "Alternatively, fill the values before plotting."
            )
        if policy == "drop":
            frame = frame.loc[~affected]
    if frame.empty or not frame[values[0]].notna().any():
        raise DataShapeError("No data to plot after handling missing values")
    return frame.reset_index(drop=True)
