"""Normalize user input into a tidy table with ``x``, ``y`` and optional ``hue``.

Accepted inputs (for categorical plots):

* ``DataFrame`` with ``x=``/``y=``/``hue=`` column names (long form);
* wide ``DataFrame`` (no names given): index → x, numeric columns → hue;
* ``Series``: index → x, values → y;
* ``{"a": 3, "b": 5}``, ``{"a": [3, 4, 5]}`` (replicates) or
  ``{"a": {"ctrl": 3, "treated": 5}}`` (nested → hue);
* a flat list/array of numbers (x = 0..n-1);
* a list of equal-length lists / 2-D array: rows → x, columns → hue.
"""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal

import numpy as np
import pandas as pd

from SecretPlots.core.missing import MissingPolicy, handle_missing, numeric_array
from SecretPlots.errors import DataShapeError


@dataclass(frozen=True)
class Tidy:
    frame: pd.DataFrame
    x_name: str | None
    y_name: str | None
    hue_name: str | None
    x_order: list[Any]
    hue_order: list[Any] | None

    @property
    def has_hue(self) -> bool:
        return self.hue_order is not None

    def rename(
        self, which: Literal["x", "hue"], labels: Sequence[Any] | Mapping[Any, Any]
    ) -> "Tidy":
        """Rename categories (``"x"``) or groups (``"hue"``).

        ``labels`` is either a list in data order (one name per category, in the
        order they appear in your data) or a mapping ``{old: new}`` (partial is
        fine).
        """
        order = self.x_order if which == "x" else self.hue_order
        what = "categories" if which == "x" else "groups"
        mapping = _rename_map(order, labels, what)
        new_order = list(mapping.values())
        frame = self.frame.copy()
        frame[which] = _relabel(frame[which], mapping)
        if which == "x":
            return replace(self, frame=frame, x_order=new_order)
        return replace(self, frame=frame, hue_order=new_order)


def _rename_map(
    order: list[Any] | None, labels: Sequence[Any] | Mapping[Any, Any], what: str
) -> dict[Any, Any]:
    """``{old: new}`` for every value in ``order``, from a list in data order or
    a (partial) mapping. Raises if the result is ambiguous or doesn't fit."""
    if order is None:
        raise DataShapeError("This plot has no groups (hue) to rename")
    if isinstance(labels, Mapping):
        unknown = set(labels) - set(order)
        if unknown:
            raise DataShapeError(
                f"Cannot rename {sorted(map(str, unknown))}: not in the data. "
                f"Current {what}: {', '.join(map(str, order))}"
            )
        mapping = {key: labels.get(key, key) for key in order}
    else:
        if isinstance(labels, str):
            raise TypeError("Pass a list of labels, not a single string")
        names = list(labels)
        if len(names) != len(order):
            raise DataShapeError(f"Got {len(names)} labels for {len(order)} {what}")
        mapping = dict(zip(order, names, strict=True))
    if len({str(n) for n in mapping.values()}) != len(mapping):
        raise DataShapeError(f"Labels must be unique; duplicates would merge {what}")
    return mapping


def _relabel(column: pd.Series, mapping: Mapping[Any, Any]) -> pd.Series:
    if isinstance(column.dtype, pd.CategoricalDtype):
        column = column.astype(object)
    return column.map(mapping)


def _order(values: Any, explicit: Sequence[Any] | None, what: str) -> list[Any]:
    if explicit is not None:
        if len(set(explicit)) != len(explicit):
            raise DataShapeError(f"{what} order must not contain duplicates")
        missing = set(values.dropna().unique()) - set(explicit)
        if missing:
            raise DataShapeError(f"{what} order is missing {sorted(map(str, missing))}")
        return list(explicit)
    if isinstance(values.dtype, pd.CategoricalDtype):
        return [c for c in values.cat.categories if c in set(values.dropna())]
    return list(pd.unique(values.dropna()))


def _from_frame(
    df: pd.DataFrame, x: str | None, y: str | None, hue: str | None
) -> tuple[pd.DataFrame, Hashable | None, Hashable | None, Hashable | None]:
    if x is None and y is None and hue is None:
        numeric = df.select_dtypes("number")
        if numeric.shape[1] == 0:
            raise DataShapeError("DataFrame has no numeric columns to plot")
        x_name = df.index.name
        if numeric.shape[1] == 1:
            col = numeric.columns[0]
            out = pd.DataFrame({"x": df.index, "y": numeric[col].to_numpy()})
            return out, x_name, str(col), None
        long = pd.concat(
            [
                pd.DataFrame({"x": df.index, "hue": col, "y": numeric[col].to_numpy()})
                for col in numeric
            ],
            ignore_index=True,
        )
        return long, x_name, None, numeric.columns.name

    for name in (x, y, hue):
        if name is not None and name not in df.columns:
            raise DataShapeError(
                f"Column {name!r} not found. "
                f"Available: {', '.join(map(str, df.columns))}"
            )
    if y is None:
        raise DataShapeError("Pass y= (the column with the values to plot)")
    out = pd.DataFrame(
        {
            "x": df[x].to_numpy() if x is not None else df.index,
            "y": df[y].to_numpy(),
        }
    )
    if x is not None and isinstance(df[x].dtype, pd.CategoricalDtype):
        out["x"] = pd.Categorical(out["x"], categories=df[x].cat.categories)
    if hue is not None:
        out["hue"] = df[hue].to_numpy()
        if isinstance(df[hue].dtype, pd.CategoricalDtype):
            out["hue"] = pd.Categorical(out["hue"], categories=df[hue].cat.categories)
    return out, x if x is not None else df.index.name, y, hue


def _from_mapping(data: Mapping[Any, Any]) -> tuple[pd.DataFrame, bool]:
    rows: list[tuple[Any, Any, Any]] = []
    nested = False
    for key, value in data.items():
        if isinstance(value, Mapping):
            nested = True
            rows += [(key, h, v) for h, v in value.items()]
        elif np.ndim(value) == 0:
            rows.append((key, None, value))
        else:
            rows += [(key, None, v) for v in numeric_array(value).ravel()]
    frame = pd.DataFrame(rows, columns=["x", "hue", "y"])
    if not nested:
        frame = frame.drop(columns="hue")
    return frame, nested


def _from_array(data: Any) -> tuple[pd.DataFrame, bool]:
    try:
        arr = numeric_array(data)
    except (TypeError, ValueError):
        raise DataShapeError(
            "Could not read the data as numbers. Lists of unequal length are "
            "ambiguous; pass a dict like {'a': [1, 2], 'b': [3]} or a DataFrame."
        ) from None
    if arr.ndim == 1:
        return pd.DataFrame({"x": np.arange(arr.size), "y": arr}), False
    if arr.ndim == 2:
        rows, cols = np.indices(arr.shape)
        return (
            pd.DataFrame({"x": rows.ravel(), "hue": cols.ravel(), "y": arr.ravel()}),
            True,
        )
    raise DataShapeError(f"Expected 1-D or 2-D data, got {arr.ndim}-D")


def tidy(
    data: Any,
    *,
    x: str | None = None,
    y: str | None = None,
    hue: str | None = None,
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
    missing: MissingPolicy = "raise",
) -> Tidy:
    """Convert supported inputs into a :class:`Tidy` table."""
    names_given = any(v is not None for v in (x, y, hue))
    if isinstance(data, Mapping) and names_given:
        data = pd.DataFrame(data)

    x_name: Hashable | None = None
    y_name: Hashable | None = None
    hue_name: Hashable | None = None
    if isinstance(data, pd.DataFrame):
        frame, x_name, y_name, hue_name = _from_frame(data, x, y, hue)
    elif names_given:
        raise DataShapeError("x=/y=/hue= are column names; pass a DataFrame or dict")
    elif isinstance(data, pd.Series):
        frame = pd.DataFrame({"x": data.index, "y": data.to_numpy()})
        x_name, y_name = data.index.name, data.name
    elif isinstance(data, Mapping):
        frame, _ = _from_mapping(data)
    else:
        frame, _ = _from_array(data)

    frame = frame.reset_index(drop=True)
    try:
        frame["y"] = pd.to_numeric(frame["y"])
    except (TypeError, ValueError):
        raise DataShapeError(f"Values in {y_name or 'y'!r} must be numeric") from None
    frame = handle_missing(
        frame, missing, values=["y"], keys=["x", *(["hue"] if "hue" in frame else [])]
    )

    return Tidy(
        frame=frame,
        x_name=None if x_name is None else str(x_name),
        y_name=None if y_name is None else str(y_name),
        hue_name=None if hue_name is None else str(hue_name),
        x_order=_order(frame["x"], order, "x"),
        hue_order=_order(frame["hue"], hue_order, "hue") if "hue" in frame else None,
    )
