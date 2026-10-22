"""Shared machinery for plots that summarize the distribution of a numeric value
per category (box plots, violin plots, rainclouds): data input, layout,
individual points, means, sample sizes and significance brackets."""

import difflib
import math
from abc import abstractmethod
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.collections import PathCollection
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure

from SecretPlots.core.colors import combined_alpha, darken
from SecretPlots.core.data import Tidy, _order
from SecretPlots.core.plot import Plot
from SecretPlots.core.resolve import Style
from SecretPlots.core.stats import (
    TEST_NAMES,
    TESTS,
    BoxStats,
    Correction,
    TestName,
    adjust,
    bandwidth,
    box_stats,
    gaussian_kde,
)
from SecretPlots.errors import DataShapeError, SmallSampleWarning, emit

Orient = Literal["v", "h"]
PointKind = Literal["auto", "swarm", "quasirandom", "jitter", "strip"]
PFormat = Literal["p", "stars"]

_POINT_KINDS = ("auto", "swarm", "quasirandom", "jitter", "strip")
_TEST_ALIASES = {
    "mann_whitney": "mann-whitney",
    "mannwhitney": "mann-whitney",
    "mwu": "mann-whitney",
    "wilcox": "mann-whitney",
    "wilcoxon": "mann-whitney",
    "rank-sum": "mann-whitney",
    "t": "t-test",
    "ttest": "t-test",
    "t_test": "t-test",
    "student": "t-test",
    "welch-t": "welch",
}
_CORRECTIONS = ("holm", "bonferroni")
_SPINE_SWAP = {"left": "bottom", "bottom": "left", "right": "top", "top": "right"}
#: Significance stars as in ggpubr / GraphPad Prism: upper p bound -> label.
_STARS = ((1e-4, "****"), (1e-3, "***"), (1e-2, "**"), (0.05, "*"))
#: Point diameter relative to the theme's marker_size when drawn over boxes.
_POINT_SCALE = 0.7
_SWARM_GAP = 1.05  # spacing between swarm points, in point diameters
#: Bracket geometry, as fractions of the data range on the value axis.
_BRACKET_STEP = 0.1
_BRACKET_LEG = 0.02
_BRACKET_GAP = 0.04


# ------------------------------------------------------------------ data input
def _name(value: Hashable | None) -> str | None:
    return None if value is None else str(value)


def _from_mapping(data: Mapping[Any, Any]) -> tuple[pd.DataFrame, bool]:
    frames = []
    nested = False
    for key, value in data.items():
        if isinstance(value, Mapping):
            nested = True
            for group, values in value.items():
                y = np.asarray(values, dtype=object).ravel()
                frames.append(pd.DataFrame({"x": key, "hue": group, "y": y}))
        else:
            y = np.asarray(value, dtype=object).ravel()
            frames.append(pd.DataFrame({"x": key, "y": y}))
    if not frames:
        raise DataShapeError("No data to plot")
    frame = pd.concat(frames, ignore_index=True)
    if nested and frame["hue"].isna().any():
        raise DataShapeError(
            "Mix of nested and flat values; use {category: {group: values}} "
            "for every category"
        )
    return frame, nested


def _from_frame(
    df: pd.DataFrame, x: Any, y: Any, hue: Any
) -> tuple[pd.DataFrame, Hashable | None, Hashable | None, Hashable | None]:
    for column in (x, y, hue):
        if column is not None and column not in df.columns:
            raise DataShapeError(
                f"Column {column!r} not found. "
                f"Available: {', '.join(map(str, df.columns))}"
            )
    if y is None:
        if x is not None or hue is not None:
            raise DataShapeError("Pass y= (the column with the values)")
        numeric = df.select_dtypes("number")
        if numeric.shape[1] == 0:
            raise DataShapeError("DataFrame has no numeric columns to plot")
        frame = pd.DataFrame(
            {
                "x": pd.Categorical(
                    np.repeat(numeric.columns, len(numeric)),
                    categories=numeric.columns,
                ),
                "y": numeric.to_numpy().ravel(order="F"),
            }
        )
        return frame, numeric.columns.name, None, None
    frame = pd.DataFrame({"y": df[y].to_numpy()})
    for key, column in (("x", x), ("hue", hue)):
        if column is None:
            continue
        frame[key] = df[column].to_numpy()
        if isinstance(df[column].dtype, pd.CategoricalDtype):
            frame[key] = pd.Categorical(
                frame[key], categories=df[column].cat.categories
            )
    if x is None:
        frame["x"] = ""
    return frame, x, y, hue


def distributions(
    data: Any,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    *,
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
) -> Tidy:
    """Read data for distribution plots into a :class:`Tidy` table.

    Accepts a long DataFrame with ``y=`` (and optional ``x=``/``hue=``)
    columns, a wide DataFrame (one category per numeric column), a Series or
    1-D values (one distribution), a dict ``{category: values}`` or
    ``{category: {group: values}}``, a 2-D array (one category per column) or
    a list of value lists of any lengths.
    """
    names_given = any(v is not None for v in (x, y, hue))
    x_name: Hashable | None = None
    y_name: Hashable | None = None
    hue_name: Hashable | None = None
    if isinstance(data, Mapping) and not names_given:
        frame, _ = _from_mapping(data)
    elif isinstance(data, pd.DataFrame | Mapping):
        frame, x_name, y_name, hue_name = _from_frame(pd.DataFrame(data), x, y, hue)
    elif names_given:
        raise DataShapeError("x=/y=/hue= are column names; pass a DataFrame or dict")
    elif isinstance(data, pd.Series):
        frame = pd.DataFrame({"x": "", "y": data.to_numpy()})
        y_name = data.name
    else:
        try:
            arr = np.asarray(data, dtype=float)
        except (TypeError, ValueError):
            try:  # a list of value lists of different lengths
                frame, _ = _from_mapping(dict(enumerate(data)))
            except (TypeError, ValueError):
                raise DataShapeError(
                    "Could not read the data as numbers. Pass a DataFrame, a "
                    "dict like {'ctrl': [...], 'treated': [...]} or a list of "
                    "value lists."
                ) from None
        else:
            if arr.ndim == 1:
                frame = pd.DataFrame({"x": "", "y": arr})
            elif arr.ndim == 2:  # one category per column
                frame = pd.DataFrame(arr).melt(var_name="x", value_name="y")
            else:
                raise DataShapeError(f"Expected 1-D or 2-D data, got {arr.ndim}-D")

    try:
        frame["y"] = pd.to_numeric(frame["y"])
    except (TypeError, ValueError):
        raise DataShapeError(f"Values in {y_name or 'y'!r} must be numeric") from None
    frame["y"] = frame["y"].astype(float).replace([np.inf, -np.inf], np.nan)
    keys = ["x", "y", "hue"] if "hue" in frame else ["x", "y"]
    frame = frame.dropna(subset=keys).reset_index(drop=True)
    if frame.empty:
        raise DataShapeError("No data to plot (every value is missing)")
    if hue_order is not None and "hue" not in frame:
        raise DataShapeError("hue_order= needs hue= groups")
    return Tidy(
        frame=frame,
        x_name=_name(x_name),
        y_name=_name(y_name),
        hue_name=_name(hue_name),
        x_order=_order(frame["x"], order, "x"),
        hue_order=_order(frame["hue"], hue_order, "hue") if "hue" in frame else None,
    )


# --------------------------------------------------------------------- helpers
def _choice(value: object, options: Sequence[str], what: str) -> None:
    if value in options:
        return
    match = difflib.get_close_matches(str(value), options, n=1)
    hint = f" Did you mean {match[0]!r}?" if match else ""
    raise ValueError(
        f"Unknown {what}={value!r}.{hint} Use one of {', '.join(map(repr, options))}."
    )


def _check_outline(color: str | None, width: float | None) -> None:
    if color is not None and not is_color_like(color):
        raise ValueError(f"Not a color: {color!r}")
    if width is not None and (isinstance(width, bool) or width < 0):
        raise ValueError("linewidth must be 0 or more (pt)")


def _check_test(test: str) -> str:
    key = test.lower().replace(" ", "-")
    key = _TEST_ALIASES.get(key, key)
    _choice(key, tuple(TESTS), "test")
    return key


def p_label(p: float, fmt: PFormat) -> str:
    """``"p = 0.012"`` / ``"p < 0.001"``, or significance stars (``"ns"`` above
    0.05)."""
    if fmt == "stars":
        return next((stars for bound, stars in _STARS if p <= bound), "ns")
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.2g}" if p < 0.1 else f"p = {p:.2f}"


def _vdc(n: int) -> np.ndarray:
    """First ``n`` terms of the base-2 van der Corput sequence (in 0..1)."""
    out = np.zeros(n)
    for i in range(n):
        k, denominator, value = i + 1, 1.0, 0.0
        while k:
            denominator *= 2
            k, remainder = divmod(k, 2)
            value += remainder / denominator
        out[i] = value
    return out


def _swarm(along: np.ndarray, diameter: float) -> np.ndarray:
    """Beeswarm offsets (same units as ``along`` and ``diameter``): each point
    goes as close to the center line as it can without overlapping."""
    order = np.argsort(along, kind="mergesort")
    placed_v: list[float] = []
    placed_o: list[float] = []
    offsets = np.zeros(len(along))
    d2 = diameter**2
    start = 0
    for index in order:
        v = float(along[index])
        while start < len(placed_v) and v - placed_v[start] >= diameter:
            start += 1
        near = list(zip(placed_v[start:], placed_o[start:], strict=True))
        candidates = [0.0]
        for pv, po in near:
            dx = math.sqrt(max(d2 - (v - pv) ** 2, 0.0))
            candidates += [po - dx, po + dx]
        candidates.sort(key=abs)
        chosen = candidates[-1]
        for c in candidates:
            if all((v - pv) ** 2 + (c - po) ** 2 >= d2 * 0.999 for pv, po in near):
                chosen = c
                break
        placed_v.append(v)
        placed_o.append(chosen)
        offsets[index] = chosen
    return offsets


@dataclass
class _Item:
    """One distribution: the values of one category (and group)."""

    cat: Any
    group: Any
    values: np.ndarray  # raw values
    t: np.ndarray  # values on the drawing scale (log10 on a log axis)
    center: float
    width: float
    color: str
    side: int = 0  # 0 both sides, +1 / -1: only toward higher / lower positions

    @property
    def key(self) -> tuple[Any, Any]:
        return (self.cat, self.group)


@dataclass
class _PointSet:
    artist: PathCollection
    item: _Item
    center: float
    halfwidth: float
    diameter_pt: float
    kind: str
    fallback: np.ndarray  # quasirandom offsets for "auto" when a swarm overflows


@dataclass(frozen=True)
class _Comparison:
    a: tuple[Any, Any]
    b: tuple[Any, Any]


class DistributionPlot(Plot):
    """Base for :class:`~SecretPlots.BoxPlot` and
    :class:`~SecretPlots.ViolinPlot`."""

    #: Below this many values per distribution, a warning suggests .points().
    small_sample: int = 5

    def __init__(
        self,
        data: Tidy,
        *,
        orient: Orient = "v",
        edgecolor: str | None = None,
        linewidth: float | None = None,
    ) -> None:
        _check_outline(edgecolor, linewidth)
        super().__init__()
        self._data = data
        self._edgecolor = edgecolor
        self._linewidth = linewidth
        self._orient: Orient = "v"
        self.orient(orient)
        self._points: dict[str, Any] | None = None
        self._mean = False
        self._show_n = False
        self._compare: dict[str, Any] | None = None
        self._reflines: tuple[float, ...] = ()
        self._tick_rotation: float | None = None
        self._tick_italic = False
        self._point_sets: list[_PointSet] = []

    # ----------------------------------------------------------------- verbs
    def orient(self, orient: Orient) -> Self:
        """Direction of the value axis.

        Args:
            orient: ``"v"`` (values up) or ``"h"`` (values to the right).
        """
        _choice(orient, ("v", "h"), "orient")
        self._orient = orient
        return self._changed()

    def points(
        self,
        show: bool = True,
        *,
        kind: PointKind = "auto",
        size: float | None = None,
        alpha: float | None = None,
        color: str | None = None,
        edgecolor: str | None = None,
        linewidth: float | None = None,
        seed: int = 0,
    ) -> Self:
        """Draw every value as a dot on top (journals ask for this when samples
        are small). Outliers are then not drawn twice.

        Args:
            show: ``False`` removes the points.
            kind: ``"swarm"`` (beeswarm: no overlap), ``"quasirandom"``
                (spread follows the density, like R's ggbeeswarm), ``"jitter"``
                (random spread), ``"strip"`` (on the center line), or
                ``"auto"``: a swarm when it fits, else quasirandom.
            size: Dot diameter in pt (default: 0.7 x the theme's marker_size).
            alpha: Dot opacity, 0 to 1 (default: the theme's marker_alpha).
            color: One color for all dots. Default: a dark shade of each box's
                color (filled boxes) or the box color itself (outlines).
            edgecolor: Color of the ring around each dot (default: the
                background, which separates overlapping dots).
            linewidth: Width of that ring in pt (default: the theme's
                marker_edge_width); 0 removes it.
            seed: Random seed for ``"jitter"``, so figures are reproducible.
        """
        _choice(kind, _POINT_KINDS, "kind")
        if size is not None and size <= 0:
            raise ValueError("size must be positive")
        if alpha is not None and not 0 <= alpha <= 1:
            raise ValueError("alpha must be between 0 and 1")
        if color is not None and not is_color_like(color):
            raise ValueError(f"Not a color: {color!r}")
        _check_outline(edgecolor, linewidth)
        self._points = (
            {
                "kind": kind,
                "size": size,
                "alpha": alpha,
                "color": color,
                "edgecolor": edgecolor,
                "linewidth": linewidth,
                "seed": seed,
            }
            if show
            else None
        )
        return self._changed()

    def mean(self, show: bool = True) -> Self:
        """Mark each mean with a white diamond.

        Args:
            show: ``False`` removes the markers.
        """
        self._mean = show
        return self._changed()

    def show_n(self, show: bool = True) -> Self:
        """Print the number of values under each category label (one number
        per group, in legend order, with ``hue``).

        Args:
            show: ``False`` hides them again.
        """
        self._show_n = show
        return self._changed()

    def refline(self, *values: float) -> Self:
        """Dashed lines across the plot at fixed values, e.g. ``.refline(0)``
        or ``.refline(1)`` for fold changes.

        Args:
            *values: Positions on the value axis. No values removes the lines.
        """
        for value in values:
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise TypeError("refline values must be numbers")
        self._reflines = tuple(float(v) for v in values)
        return self._changed()

    def compare(
        self,
        *pairs: Sequence[Any],
        ref: Any = None,
        test: TestName | str = "mann-whitney",
        correction: Correction | None = None,
        p: Sequence[float] | None = None,
        format: PFormat = "p",
        hide_ns: bool = False,
    ) -> Self:
        """Significance brackets between distributions.

        Without ``hue``, pairs name categories: ``.compare(("ctrl", "drug"))``.
        With ``hue``, pairs name groups and are compared within every category;
        use ``((category, group), (category, group))`` for anything else.
        Without pairs, ``ref`` is compared against all others; with neither,
        every pair is compared.

        Args:
            *pairs: Pairs to compare, each a 2-item tuple.
            ref: A reference category (or group with ``hue``), e.g. the
                control: each other one is compared with it.
            test: ``"mann-whitney"`` (default; Wilcoxon rank-sum, no
                normality assumption), ``"welch"`` (t-test without equal
                variances) or ``"t-test"`` (Student's). All two-sided and
                for independent samples.
            correction: Adjust p-values for multiple comparisons:
                ``"holm"`` or ``"bonferroni"``.
            p: Your own p-values (e.g. from a paired or post-hoc test), one
                per comparison in order; no test is run.
            format: ``"p"`` writes exact values (``p = 0.012``), which most
                journals prefer; ``"stars"`` writes ``*`` (p <= 0.05), ``**``
                (0.01), ``***`` (0.001), ``****`` (0.0001) or ``ns``.
            hide_ns: Leave out brackets with p > 0.05.
        """
        test_key = _check_test(str(test))
        if correction is not None:
            _choice(correction, _CORRECTIONS, "correction")
        _choice(format, ("p", "stars"), "format")
        for pair in pairs:
            if isinstance(pair, str) or len(pair) != 2:
                raise ValueError(
                    f"Each comparison is a pair like ('ctrl', 'drug'), got {pair!r}"
                )
        self._compare = {
            "pairs": [tuple(pair) for pair in pairs],
            "ref": ref,
            "test": test_key,
            "correction": correction,
            "p": None if p is None else [float(v) for v in p],
            "format": format,
            "hide_ns": hide_ns,
        }
        self._comparisons()  # validate names now
        return self._changed()

    def ticklabels(
        self,
        labels: Sequence[Any] | Mapping[Any, Any] | None = None,
        *,
        rotation: float | None = None,
        italic: bool = False,
    ) -> Self:
        """Name the categories and style their labels.

        Args:
            labels: New names as a list in data order or a mapping
                ``{old: new}``. The categories themselves are renamed, so later
                ``.highlight()``, ``.colors({...})`` or ``.compare()`` use the
                new names.
            rotation: Label angle in degrees; turns off automatic rotation.
            italic: Italic labels, e.g. for gene names.
        """
        if labels is not None:
            self._data = self._data.rename("x", labels)
        self._tick_rotation = rotation
        self._tick_italic = italic
        return self._changed()

    def grouplabels(self, labels: Sequence[Any] | Mapping[Any, Any]) -> Self:
        """Name the ``hue`` groups shown in the legend.

        Args:
            labels: New names as a list in group order or a mapping
                ``{old: new}``.
        """
        self._data = self._data.rename("hue", labels)
        return self._changed()

    # ------------------------------------------------------------------ data
    @property
    def _grouped(self) -> bool:
        return self._data.has_hue

    @property
    def _groups(self) -> list[Any]:
        return list(self._data.hue_order or [None])

    @property
    def _single(self) -> bool:
        return self._data.x_order == [""] and self._data.x_name is None

    @property
    def _value_axis(self) -> str:
        return "y" if self._orient == "v" else "x"

    @property
    def _log(self) -> bool:
        return self._value_axis in self._log_axes

    def _fwd(self, values: np.ndarray) -> np.ndarray:
        if not self._log:
            return values
        if (values <= 0).any():
            raise DataShapeError(
                "A log axis needs positive values; drop values <= 0 first"
            )
        return np.asarray(np.log10(values), dtype=float)

    def _inv(self, values: Any) -> Any:
        return np.power(10.0, values) if self._log else values

    def _values(self, cat: Any, group: Any) -> np.ndarray:
        frame = self._data.frame
        rows = frame[frame["x"] == cat]
        if group is not None:
            rows = rows[rows["hue"] == group]
        return np.asarray(rows["y"].to_numpy(dtype=float))

    def _keys(self) -> list[tuple[Any, Any]]:
        """Every (category, group) with values, in drawing order."""
        return [
            (cat, group)
            for cat in self._data.x_order
            for group in self._groups
            if len(self._values(cat, group))
        ]

    def _stats(self, values: np.ndarray) -> BoxStats:
        """Box statistics on the drawing scale (log10 on a log axis)."""
        return box_stats(self._fwd(values), self._whis)

    @property
    def _whis(self) -> Any:
        return 1.5

    def source_data(self) -> pd.DataFrame:
        """Summary numbers per distribution (n, mean, SD, quartiles, whisker
        ends, outliers) for a journal's source-data file."""
        rows = []
        for cat, group in self._keys():
            values = self._values(cat, group)
            s = self._stats(values)
            row: dict[str, Any] = {self._data.x_name or "category": cat}
            if self._grouped:
                row[self._data.hue_name or "group"] = group
            row |= {
                "n": s.n,
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=1)) if s.n > 1 else math.nan,
                "min": s.minimum,
                "q1": s.q1,
                "median": s.median,
                "q3": s.q3,
                "max": s.maximum,
                "whisker_low": s.whisker_low,
                "whisker_high": s.whisker_high,
                "n_outliers": len(s.outliers),
            }
            for key in ("min", "q1", "median", "q3", "max"):
                row[key] = float(self._inv(row[key]))
            for key in ("whisker_low", "whisker_high"):
                row[key] = float(self._inv(row[key]))
            rows.append(row)
        table = pd.DataFrame(rows)
        if self._single:
            table = table.drop(columns=table.columns[0])
        return table

    def _comparisons(self) -> list[_Comparison]:
        assert self._compare is not None
        pairs, ref = self._compare["pairs"], self._compare["ref"]
        cats = list(self._data.x_order)
        groups = self._groups
        names = groups if self._grouped else cats
        what = "group" if self._grouped else "category"

        def check(name: Any) -> None:
            if name not in names:
                raise DataShapeError(
                    f"Cannot compare {name!r}: not a {what}. "
                    f"{what.capitalize()}s: {', '.join(map(str, names))}"
                )

        def key(item: Any) -> tuple[Any, Any] | None:
            if (
                self._grouped
                and isinstance(item, tuple)
                and len(item) == 2
                and item[0] in cats
                and item[1] in groups
            ):
                return (item[0], item[1])
            return None

        if pairs:
            chosen = pairs
        elif ref is not None:
            check(ref)
            chosen = [(ref, other) for other in names if other != ref]
        else:
            chosen = [(a, b) for i, a in enumerate(names) for b in names[i + 1 :]]
        if self._single:
            raise DataShapeError("compare() needs at least two categories or groups")
        result: list[_Comparison] = []
        for a, b in chosen:
            ka, kb = key(a), key(b)
            if ka is not None and kb is not None:
                result.append(_Comparison(ka, kb))
                continue
            check(a)
            check(b)
            if a == b:
                raise DataShapeError(f"Cannot compare {a!r} with itself")
            if self._grouped:
                result += [_Comparison((c, a), (c, b)) for c in cats]
            else:
                result.append(_Comparison((a, None), (b, None)))
        present = set(self._keys())
        result = [c for c in result if c.a in present and c.b in present]
        user_p = self._compare["p"]
        if user_p is not None and len(user_p) != len(result):
            raise DataShapeError(
                f"Got {len(user_p)} p-values for {len(result)} comparisons"
            )
        return result

    def test_results(self) -> pd.DataFrame:
        """The comparisons from :meth:`compare`: sizes, test statistic,
        p-value (adjusted if requested) and the printed label."""
        if self._compare is None:
            raise DataShapeError("No comparisons; call .compare(...) first")
        options = self._compare
        comparisons = self._comparisons()
        rows = []
        for i, comp in enumerate(comparisons):
            a, b = self._values(*comp.a), self._values(*comp.b)
            if options["p"] is not None:
                statistic, p = math.nan, options["p"][i]
            else:
                if min(len(a), len(b)) < 2:
                    raise DataShapeError(
                        "A test needs at least 2 values per group; "
                        f"{comp.a if len(a) < 2 else comp.b} has fewer"
                    )
                result = TESTS[options["test"]](a, b)
                statistic, p = result.statistic, result.p
            rows.append(
                {
                    "group1": self._describe_key(comp.a),
                    "group2": self._describe_key(comp.b),
                    "n1": len(a),
                    "n2": len(b),
                    "test": "user" if options["p"] is not None else options["test"],
                    "statistic": statistic,
                    "p": p,
                }
            )
        table = pd.DataFrame(rows)
        if table.empty:
            return table
        if options["correction"]:
            table["p_adjusted"] = adjust(table["p"].tolist(), options["correction"])
        used = table["p_adjusted"] if options["correction"] else table["p"]
        table["label"] = [p_label(float(p), options["format"]) for p in used]
        return table

    def _describe_key(self, key: tuple[Any, Any]) -> Any:
        cat, group = key
        if not self._grouped:
            return cat
        return f"{cat} / {group}" if not self._single else group

    # --------------------------------------------------------------- caption
    @abstractmethod
    def _caption_marks(self) -> list[str]:
        """Sentences describing the marks, for :meth:`caption`."""

    def caption(self) -> str:
        """A sentence or two for the figure legend that defines what is drawn
        (centre line, box limits, whiskers, points), the sample sizes and the
        statistical test. Journals ask for these definitions; edit to taste."""
        parts = self._caption_marks()
        if self._points is not None:
            parts.append("Dots show individual values.")
        if self._mean:
            parts.append("Diamonds mark the mean.")
        counts = [len(self._values(*key)) for key in self._keys()]
        if counts:
            if len(set(counts)) == 1:
                parts.append(f"n = {counts[0]} per distribution.")
            elif len(counts) <= 8:
                parts.append(f"n = {', '.join(map(str, counts))}.")
            else:
                parts.append(f"n = {min(counts)} to {max(counts)} per distribution.")
        if self._compare is not None:
            options = self._compare
            if options["p"] is not None:
                sentence = "P values as given"
            else:
                sentence = f"P values: {TEST_NAMES[options['test']]}"
            if options["correction"]:
                name = "Holm" if options["correction"] == "holm" else "Bonferroni"
                sentence += f", {name}-adjusted for multiple comparisons"
            sentence += "."
            if options["format"] == "stars":
                sentence += (
                    " *p <= 0.05, **p <= 0.01, ***p <= 0.001, ****p <= 0.0001; "
                    "ns, not significant."
                )
            parts.append(sentence)
        return " ".join(parts)

    # ---------------------------------------------------------------- layout
    def _dodge(self) -> bool:
        return self._grouped

    def _items(self, style: Style) -> list[_Item]:
        cats = list(self._data.x_order)
        groups = self._groups
        color = self._category_color_fn(style, groups, cats, grouped=self._grouped)
        span = 1 - (style.theme.bar_gap or 0)
        dodge = self._dodge()
        each = span / len(groups) if dodge else span
        items = []
        for cat, group in self._keys():
            pos = float(cats.index(cat))
            j = groups.index(group)
            center = pos - span / 2 + each * (j + 0.5) if dodge else pos
            values = self._values(cat, group)
            items.append(
                _Item(
                    cat=cat,
                    group=group,
                    values=values,
                    t=self._fwd(values),
                    center=center,
                    width=each * (0.9 if dodge else 1.0),
                    color=color(group, cat),
                )
            )
        return items

    def _xy(self, pos: Any, val: Any) -> tuple[Any, Any]:
        """(x, y) for a position on the category axis and a value."""
        return (pos, val) if self._orient == "v" else (val, pos)

    def _visual(self, direction: int) -> int:
        """Position-axis sign for a visual side: +1 is right (vertical plots)
        or up (horizontal plots, whose first category is on top)."""
        return direction if self._orient == "v" else -direction

    def _line_width(self, style: Style, factor: float) -> float:
        width = float(style.theme.line_width or 1.5) * factor
        return max(width, style.target.min_line_width or 0.0)

    def _line_color(self, color: str, fill: bool) -> str:
        return darken(color, 0.55) if fill else color

    def _outline_color(self, item: _Item) -> str:
        """Outline of a box or violin: ``edgecolor=`` or a dark shade of the
        fill (the fill color itself for outlined shapes)."""
        return self._edgecolor or self._line_color(item.color, self._filled())

    def _detail_color(self, item: _Item) -> str:
        """Whiskers, medians and other lines: follow ``edgecolor=`` unless it
        is ``"none"``, which only removes the outline."""
        if self._edgecolor is not None and self._edgecolor.lower() != "none":
            return self._edgecolor
        return self._line_color(item.color, self._filled())

    def _outline_width(self, style: Style) -> float:
        if self._linewidth is not None:
            return float(self._linewidth)
        return self._line_width(style, 0.6)

    # --------------------------------------------------------------- drawing
    @abstractmethod
    def _draw_marks(self, ax: Axes, style: Style, items: list[_Item]) -> None:
        """Draw boxes / violins."""

    @abstractmethod
    def _extent(self, item: _Item) -> tuple[float, float]:
        """Lowest and highest drawn value of ``item`` (drawing scale)."""

    def _point_geometry(self, item: _Item) -> tuple[float, float]:
        """Center and half-width of the strip where an item's dots go."""
        return item.center, item.width * 0.35

    def _filled(self) -> bool:
        return True

    def _default_labels(self) -> dict[str, str | None]:
        cat, val = self._data.x_name, self._data.y_name
        return {"x": cat, "y": val} if self._orient == "v" else {"x": val, "y": cat}

    def _draw(self, ax: Axes, style: Style) -> None:
        items = self._items(style)
        self._warn_small(items)
        self._draw_marks(ax, style, items)
        self._point_sets = []
        if self._points is not None:
            self._draw_points(ax, style, items)
        if self._mean:
            self._draw_means(ax, style, items)
        for value in self._reflines:
            line = ax.axhline if self._orient == "v" else ax.axvline
            line(
                value,
                color=style.theme.text_color,
                lw=style.theme.axis_line_width,
                ls="--",
                zorder=1.5,
            )
        if self._compare is not None:
            self._draw_brackets(ax, style, items)
        self._style_axes(ax, style)
        if self._grouped:
            self._draw_legend(ax, style, n=len(self._groups), title=self._data.hue_name)

    def _warn_small(self, items: list[_Item]) -> None:
        if self._points is not None:
            return
        small = [i for i in items if len(i.values) < self.small_sample]
        if not small:
            return
        names = ", ".join(str(self._describe_key(i.key)) for i in small[:4])
        which = "" if self._single else f" ({names}{', ...' if len(small) > 4 else ''})"
        emit(
            SmallSampleWarning,
            f"Fewer than {self.small_sample} values{which}: a {self.kind} plot "
            "of so few values hides more than it shows. Show the individual "
            "values with .points() (Krzywinski & Altman, Nat Methods 11:119, "
            "2014).",
            stacklevel=5,
        )

    def _draw_points(self, ax: Axes, style: Style, items: list[_Item]) -> None:
        assert self._points is not None
        theme = style.theme
        options = self._points
        diameter = options["size"] or float(theme.marker_size or 5.0) * _POINT_SCALE
        alpha = options["alpha"] if options["alpha"] is not None else theme.marker_alpha
        rng = np.random.default_rng(options["seed"])
        kind = options["kind"]
        for item in items:
            center, half = self._point_geometry(item)
            n = len(item.t)
            if kind == "jitter":
                offsets = rng.uniform(-half, half, n)
            elif kind in ("quasirandom", "auto"):
                offsets = self._quasirandom(item.t, half)
            else:  # strip, and swarm until the layout is known (_adapt)
                offsets = np.zeros(n)
            color = options["color"] or (
                self._line_color(item.color, True) if self._filled() else item.color
            )
            artist = ax.scatter(
                *self._xy(center + offsets, item.values),
                s=diameter**2,
                color=color,
                alpha=combined_alpha(color, alpha),
                linewidths=options["linewidth"]
                if options["linewidth"] is not None
                else theme.marker_edge_width,
                edgecolors=options["edgecolor"] or theme.axes_background,
                zorder=4,
            )
            self._point_sets.append(
                _PointSet(artist, item, center, half, diameter, kind, offsets)
            )

    @staticmethod
    def _quasirandom(t: np.ndarray, half: float) -> np.ndarray:
        """Offsets from a van der Corput sequence scaled by the local density
        (as R's vipor / ggbeeswarm ``geom_quasirandom``)."""
        n = len(t)
        if n == 0:
            return np.zeros(0)
        spread = 2 * _vdc(n) - 1
        if n < 3 or np.ptp(t) == 0:
            return np.asarray(spread * half, dtype=float)
        density = gaussian_kde(t, t, bandwidth(t, 1.0))
        width = density / density.max()
        ranks = np.argsort(np.argsort(t, kind="mergesort"))
        return np.asarray(spread[ranks] * width * half, dtype=float)

    def _draw_means(self, ax: Axes, style: Style, items: list[_Item]) -> None:
        theme = style.theme
        size = float(theme.marker_size or 5.0) * 0.9
        for item in items:
            line = self._detail_color(item)
            ax.scatter(
                *self._xy([item.center], [float(item.values.mean())]),
                s=size**2,
                marker="D",
                color=theme.axes_background,
                edgecolors=line,
                linewidths=self._line_width(style, 0.6),
                zorder=5,
            )

    def _draw_brackets(self, ax: Axes, style: Style, items: list[_Item]) -> None:
        assert self._compare is not None
        table = self.test_results()
        if table.empty:
            return
        theme = style.theme
        by_key = {item.key: item for item in items}
        tops: dict[tuple[Any, Any], float] = {}
        lows = []
        for item in items:
            low, high = self._extent(item)
            if self._points is not None:
                low, high = (
                    min(low, float(item.t.min())),
                    max(high, float(item.t.max())),
                )
            tops[item.key] = high
            lows.append(low)
        span = (max(tops.values()) - min(lows)) or 1.0
        step, leg, gap = (span * f for f in (_BRACKET_STEP, _BRACKET_LEG, _BRACKET_GAP))
        p_column = "p_adjusted" if "p_adjusted" in table else "p"

        jobs = []
        for comp, (_, row) in zip(self._comparisons(), table.iterrows(), strict=True):
            if self._compare["hide_ns"] and float(row[p_column]) > 0.05:
                continue
            x1, x2 = sorted((by_key[comp.a].center, by_key[comp.b].center))
            jobs.append((x1, x2, str(row["label"])))
        jobs.sort(key=lambda job: (job[1] - job[0], job[0]))

        placed: list[tuple[float, float, float]] = []
        highest = max(tops.values())
        for x1, x2, label in jobs:
            under = [
                tops[item.key]
                for item in items
                if x1 - 1e-9 <= item.center <= x2 + 1e-9
            ]
            level = max(under) + gap + leg
            for px1, px2, py in placed:
                if px1 <= x2 + 1e-9 and x1 <= px2 + 1e-9:
                    level = max(level, py + step)
            placed.append((x1, x2, level))
            highest = max(highest, level)
            xs = [x1, x1, x2, x2]
            ys = self._inv(np.array([level - leg, level, level, level - leg]))
            ax.plot(
                *self._xy(xs, ys),
                color=theme.text_color,
                lw=theme.axis_line_width,
                solid_capstyle="butt",
                zorder=6,
            )
            vertical = self._orient == "v"
            ax.annotate(
                label,
                xy=self._xy((x1 + x2) / 2, float(self._inv(level))),
                xytext=(0, 1.5) if vertical else (1.5, 0),
                textcoords="offset points",
                ha="center" if vertical else "left",
                va="bottom" if vertical else "center",
                rotation=0 if vertical else -90,
                rotation_mode="anchor" if not vertical else "default",
                fontsize=style.sizes.tick,
                color=theme.text_color,
                zorder=6,
            )
        top = float(self._inv(highest + step * 0.8))
        ax.update_datalim([self._xy(by_key[next(iter(by_key))].center, top)])
        ax.autoscale_view()

    def _tick_texts(self) -> list[str]:
        labels = []
        for cat in self._data.x_order:
            text = "" if self._single else str(cat)
            if self._show_n:
                counts = [
                    len(self._values(cat, g))
                    for g in self._groups
                    if len(self._values(cat, g))
                ]
                n = f"n = {', '.join(map(str, counts))}"
                text = f"{text}\n{n}" if text else n
            labels.append(text)
        return labels

    def _style_axes(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        vertical = self._orient == "v"
        cats = list(self._data.x_order)
        positions = np.arange(len(cats), dtype=float)
        labels = self._tick_texts()
        cat_axis, value_axis = (
            (ax.xaxis, ax.yaxis) if vertical else (ax.yaxis, ax.xaxis)
        )
        if vertical:
            ax.set_xticks(positions, labels=labels)
            ax.set_xlim(-0.5, len(cats) - 0.5)
            ax.margins(y=0.05)
        else:
            ax.set_yticks(positions, labels=labels)
            ax.set_ylim(len(cats) - 0.5, -0.5)  # first category on top
            ax.margins(x=0.05)
        ax.tick_params(axis="x" if vertical else "y", length=0)
        for text in ax.get_xticklabels() if vertical else ax.get_yticklabels():
            if self._tick_italic:
                text.set_fontstyle("italic")
            if self._tick_rotation is not None:
                text.set_rotation(self._tick_rotation)
                if vertical and self._tick_rotation % 90:
                    text.set_horizontalalignment("right")
                    text.set_rotation_mode("anchor")

        grid = theme.grid
        if grid in ("both", "value") or grid == ("y" if vertical else "x"):
            value_axis.grid(True)
        if grid in ("both", "category") or grid == ("x" if vertical else "y"):
            cat_axis.grid(True)
        if theme.value_axis_side == "right":
            if vertical:
                ax.yaxis.tick_right()
                ax.yaxis.set_label_position("right")
            else:
                ax.xaxis.tick_top()
                ax.xaxis.set_label_position("top")
        visible: set[str] = set(theme.spines or ())
        if not vertical:
            visible = {_SPINE_SWAP[s] for s in visible}
        for side, spine in ax.spines.items():
            spine.set_visible(side in visible)

    # -------------------------------------------------------------- adapting
    def _adapt(
        self, fig: Figure, ax: Axes, style: Style, renderer: RendererBase
    ) -> None:
        if self._orient == "v" and not self._single:
            self._fit_category_labels(fig, ax, renderer, self._tick_rotation)
        self._place_swarms(fig, ax)

    def _place_swarms(self, fig: Figure, ax: Axes) -> None:
        """Beeswarm offsets need the plot's size in pixels, so they are placed
        after layout. With ``kind="auto"`` a swarm that is wider than its strip
        falls back to quasirandom offsets (already drawn)."""
        sets = [s for s in self._point_sets if s.kind in ("swarm", "auto")]
        if not sets:
            return
        vertical = self._orient == "v"
        transform = ax.transData
        unit = abs(
            transform.transform(self._xy(1.0, 1.0))[0 if vertical else 1]
            - transform.transform(self._xy(0.0, 1.0))[0 if vertical else 1]
        )
        value_index = 1 if vertical else 0
        results: list[tuple[_PointSet, np.ndarray]] = []
        overflow = False
        for s in sets:
            display = transform.transform(
                np.column_stack(
                    self._xy(np.full(len(s.item.values), s.center), s.item.values)
                )
            )[:, value_index]
            diameter_px = s.diameter_pt * fig.dpi / 72 * _SWARM_GAP
            offsets = _swarm(display, diameter_px) / unit
            if np.abs(offsets).max(initial=0) > s.halfwidth * 1.6:
                overflow = True
            results.append((s, offsets))
        if overflow and all(s.kind == "auto" for s in sets):
            return
        for s, offsets in results:
            if s.kind == "auto" and overflow:
                offsets = s.fallback
            limit = s.halfwidth * 1.6
            offsets = np.clip(offsets, -limit, limit)
            s.artist.set_offsets(
                np.column_stack(self._xy(s.center + offsets, s.item.values))
            )
