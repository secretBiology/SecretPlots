"""Histograms: counts or normalized distributions of one numeric variable, with
optional groups, density curves and reference lines."""

import difflib
import math
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from SecretPlots.core.data import _order
from SecretPlots.core.plot import Plot
from SecretPlots.core.resolve import Style
from SecretPlots.errors import DataShapeError, SmallSampleWarning, emit

Stat = Literal["count", "frequency", "probability", "percent", "density"]
Multiple = Literal["layer", "stack", "dodge"]
Element = Literal["bars", "step"]
Orient = Literal["v", "h"]
BinRule = Literal["auto", "fd", "sturges", "scott", "rice", "sqrt", "doane"]
RefLine = Literal["mean", "median"] | float

_STATS = ("count", "frequency", "probability", "percent", "density")
_STAT_ALIASES = {"proportion": "probability", "fraction": "probability"}
_MULTIPLE = ("layer", "stack", "dodge")
_ELEMENTS = ("bars", "step")
_BIN_RULES = ("auto", "fd", "sturges", "scott", "rice", "sqrt", "doane")
_STAT_LABELS = {
    "count": "Count",
    "frequency": "Count per unit",
    "probability": "Proportion",
    "percent": "Percent",
    "density": "Density",
}
_SPINE_SWAP = {"left": "bottom", "bottom": "left", "right": "top", "top": "right"}
#: Below this many values a histogram's shape mostly reflects the bin choice
#: (Krzywinski & Altman, Nature Methods 11:119, 2014).
SMALL_SAMPLE = 30
_LAYER_ALPHA = 0.5
_STEP_FILL_ALPHA = 0.12
_CURVE_POINTS = 200
_RUG_HEIGHT = 0.035


@dataclass(frozen=True)
class _Samples:
    frame: pd.DataFrame  # column "x" and optionally "hue"
    x_name: str | None
    hue_name: str | None
    hue_order: list[Any] | None


def _name(value: Hashable | None) -> str | None:
    return None if value is None else str(value)


def _samples(data: Any, x: Any, hue: Any, hue_order: Sequence[Any] | None) -> _Samples:
    x_name: Hashable | None = None
    hue_name: Hashable | None = None
    if data is None:
        if x is None or isinstance(x, str):
            raise DataShapeError(
                "Pass the data first: sp.histogram(values) or "
                "sp.histogram(df, x='column')"
            )
        frame = pd.DataFrame({"x": np.asarray(x).ravel()})
        if hue is not None:
            if np.ndim(hue) != 1 or len(hue) != len(frame):
                raise DataShapeError("hue= must have one group per value")
            frame["hue"] = np.asarray(hue)
    elif isinstance(data, Mapping) and x is None and hue is None:
        rows = [
            pd.DataFrame({"x": np.asarray(values, dtype=object).ravel(), "hue": key})
            for key, values in data.items()
        ]
        if not rows:
            raise DataShapeError("No data to plot")
        frame = pd.concat(rows, ignore_index=True)
    elif isinstance(data, pd.Series):
        if x is not None or hue is not None:
            raise DataShapeError("x=/hue= are column names; pass a DataFrame")
        frame = pd.DataFrame({"x": data.to_numpy()})
        x_name = data.name
    elif isinstance(data, pd.DataFrame | Mapping):
        df = pd.DataFrame(data)
        for column in (x, hue):
            if column is not None and column not in df.columns:
                raise DataShapeError(
                    f"Column {column!r} not found. "
                    f"Available: {', '.join(map(str, df.columns))}"
                )
        if x is None:
            if hue is not None:
                raise DataShapeError("Pass x= (the column with the values)")
            numeric = df.select_dtypes("number")
            if numeric.shape[1] == 0:
                raise DataShapeError("DataFrame has no numeric columns to plot")
            if numeric.shape[1] == 1:
                frame = pd.DataFrame({"x": numeric.iloc[:, 0].to_numpy()})
                x_name = numeric.columns[0]
            else:  # wide: one group per column
                frame = pd.DataFrame(
                    {
                        "x": numeric.to_numpy().ravel(order="F"),
                        "hue": np.repeat(numeric.columns, len(numeric)),
                    }
                )
                hue_name = numeric.columns.name
        else:
            frame = pd.DataFrame({"x": df[x].to_numpy()})
            x_name = x
            if hue is not None:
                frame["hue"] = df[hue].to_numpy()
                if isinstance(df[hue].dtype, pd.CategoricalDtype):
                    frame["hue"] = pd.Categorical(
                        frame["hue"], categories=df[hue].cat.categories
                    )
                hue_name = hue
    else:
        if x is not None or hue is not None:
            raise DataShapeError("x=/hue= are column names; pass a DataFrame or dict")
        try:
            arr = np.asarray(data, dtype=float)
        except (TypeError, ValueError):
            raise DataShapeError(
                "Could not read the data as numbers. For groups of different "
                "sizes pass a dict like {'ctrl': [...], 'treated': [...]}."
            ) from None
        if arr.ndim == 1:
            frame = pd.DataFrame({"x": arr})
        elif arr.ndim == 2:  # one group per column
            frame = pd.DataFrame(arr).melt(var_name="hue", value_name="x")
        else:
            raise DataShapeError(f"Expected 1-D or 2-D data, got {arr.ndim}-D")

    try:
        frame["x"] = pd.to_numeric(frame["x"])
    except (TypeError, ValueError):
        raise DataShapeError(f"Values in {x_name or 'x'!r} must be numeric") from None
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    if frame.empty:
        raise DataShapeError("No data to plot (every value is missing)")
    if hue_order is not None and "hue" not in frame:
        raise DataShapeError("hue_order= needs hue= groups")
    return _Samples(
        frame=frame,
        x_name=_name(x_name),
        hue_name=_name(hue_name),
        hue_order=_order(frame["hue"], hue_order, "hue") if "hue" in frame else None,
    )


def _choice(value: object, options: Sequence[str], what: str) -> None:
    if value in options:
        return
    match = difflib.get_close_matches(str(value), options, n=1)
    hint = f" Did you mean {match[0]!r}?" if match else ""
    raise ValueError(
        f"Unknown {what}={value!r}.{hint} Use one of {', '.join(map(repr, options))}."
    )


def _check_stat(stat: str) -> str:
    stat = _STAT_ALIASES.get(stat, stat)
    _choice(stat, _STATS, "stat")
    return stat


def _bandwidth(values: np.ndarray, adjust: float) -> float:
    """Scott's rule (n^-1/5) on a robust spread (the smaller of the standard
    deviation and IQR / 1.349), times ``adjust``."""
    n = len(values)
    sd = float(np.std(values, ddof=1)) if n > 1 else 0.0
    iqr = float(np.subtract(*np.percentile(values, [75, 25])))
    spread = min(sd, iqr / 1.349) if iqr > 0 else sd
    if spread == 0:
        raise DataShapeError("A density curve needs values that are not all equal")
    return float(spread * n ** (-1 / 5) * adjust)


def _erf(x: np.ndarray) -> np.ndarray:
    """Error function (Abramowitz & Stegun 7.1.26, error < 1.5e-7)."""
    t = 1 / (1 + 0.3275911 * np.abs(x))
    poly = t * (
        0.254829592
        + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))
    )
    return np.asarray(np.sign(x) * (1 - poly * np.exp(-(x**2))), dtype=float)


def _gaussian_kde(
    values: np.ndarray, grid: np.ndarray, bw: float, *, cumulative: bool = False
) -> np.ndarray:
    """Gaussian kernel density (or its cumulative distribution) on ``grid``."""
    total = np.zeros_like(grid)
    for chunk in np.array_split(values, max(1, len(values) // 2000)):
        z = (grid[:, None] - chunk[None, :]) / bw
        if cumulative:
            total += (0.5 * (1 + _erf(z / math.sqrt(2)))).sum(axis=1)
        else:
            total += np.exp(-0.5 * z**2).sum(axis=1)
    if cumulative:
        return np.asarray(total / len(values), dtype=float)
    return np.asarray(total / (len(values) * bw * math.sqrt(2 * math.pi)), dtype=float)


class HistogramPlot(Plot):
    """Created by :func:`histogram`."""

    kind = "histogram"

    def __init__(
        self,
        samples: _Samples,
        *,
        bins: int | BinRule | Sequence[float] = "auto",
        binwidth: float | None = None,
        binrange: tuple[float, float] | None = None,
        discrete: bool = False,
        stat: Stat = "count",
        common_norm: bool = False,
        cumulative: bool = False,
        multiple: Multiple = "layer",
        element: Element | None = None,
        orient: Orient = "v",
    ) -> None:
        super().__init__()
        stat = _check_stat(stat)  # type: ignore[assignment]
        _choice(multiple, _MULTIPLE, "multiple")
        if element is not None:
            _choice(element, _ELEMENTS, "element")
        _choice(orient, ("v", "h"), "orient")
        if isinstance(bins, str):
            _choice(bins, _BIN_RULES, "bins")
        elif (
            isinstance(bins, int | np.integer)
            and not isinstance(bins, bool)
            and bins < 1
        ):
            raise ValueError("bins must be at least 1")
        if binwidth is not None and binwidth <= 0:
            raise ValueError("binwidth must be positive")
        if binrange is not None and not binrange[0] < binrange[1]:
            raise ValueError("binrange must be (low, high) with low < high")
        if cumulative and stat == "frequency":
            raise ValueError(
                "A cumulative histogram of counts per unit has no clear meaning; "
                "use stat='count', 'probability', 'percent' or 'density'"
            )
        if multiple == "dodge" and element == "step":
            raise ValueError("multiple='dodge' needs element='bars'")
        self._samples = samples
        self._bins = bins
        self._binwidth = binwidth
        self._binrange = binrange
        self._discrete = discrete
        self._stat: str = stat
        self._common_norm = common_norm
        self._cumulative = cumulative
        self._multiple: str = multiple
        self._element = element
        self._orient: str = orient
        self._kde: dict[str, Any] | None = None
        self._fit: str | None = None
        self._reflines: tuple[Any, ...] = ()
        self._refline_labels = False
        self._rug = False
        self._show_n = False

    # ----------------------------------------------------------------- verbs
    def kde(
        self, show: bool = True, *, bw_adjust: float = 1.0, cut: float = 0.0
    ) -> Self:
        """Overlay a smooth density curve (Gaussian kernel), scaled to match
        the bars' ``stat``.

        Args:
            show: ``False`` removes the curve.
            bw_adjust: Multiplies the automatic bandwidth (Scott's rule on a
                robust spread).
                Smaller follows the data more closely.
            cut: How far past the smallest and largest value to draw the curve,
                in bandwidths. The default 0 keeps it inside the data range, so
                it never suggests impossible values (e.g. negative ages).
        """
        if bw_adjust <= 0:
            raise ValueError("bw_adjust must be positive")
        if cut < 0:
            raise ValueError("cut must be 0 or more")
        self._kde = {"bw_adjust": bw_adjust, "cut": cut} if show else None
        return self._changed()

    def fit(self, dist: Literal["normal"] | None = "normal") -> Self:
        """Overlay a fitted distribution (sample mean and standard deviation).

        Args:
            dist: ``"normal"``, or ``None`` to remove the curve.
        """
        if dist is not None:
            _choice(dist, ("normal",), "dist")
        self._fit = dist
        return self._changed()

    def refline(self, *values: RefLine, label: bool = False) -> Self:
        """Dashed reference lines across the value axis. ``"mean"`` and
        ``"median"`` are drawn per group in the group's color.

        Args:
            *values: ``"mean"``, ``"median"`` or numbers, e.g.
                ``.refline("median", 0)``. No values removes the lines.
            label: Write the value next to each line.
        """
        for value in values:
            if isinstance(value, str):
                _choice(value, ("mean", "median"), "refline")
            elif isinstance(value, bool) or not isinstance(value, int | float):
                raise TypeError("refline values must be 'mean', 'median' or numbers")
        self._reflines = values
        self._refline_labels = label
        return self._changed()

    def rug(self, show: bool = True) -> Self:
        """Short ticks at every value along the value axis: shows the individual
        data points, which journals ask for when there are few of them.

        Args:
            show: ``False`` removes the rug.
        """
        self._rug = show
        return self._changed()

    def show_n(self, show: bool = True) -> Self:
        """Print the number of values (per group, in the legend).

        Args:
            show: ``False`` hides it again.
        """
        self._show_n = show
        return self._changed()

    # ------------------------------------------------------------------ data
    @property
    def _groups(self) -> list[Any]:
        return list(self._samples.hue_order or [None])

    def _values(self, group: Any) -> np.ndarray:
        frame = self._samples.frame
        rows = frame if group is None else frame[frame["hue"] == group]
        return rows["x"].to_numpy(dtype=float)

    @property
    def _log(self) -> bool:
        return ("x" if self._orient == "v" else "y") in self._log_axes

    @property
    def bin_edges(self) -> np.ndarray:
        """Bin edges shared by every group (report the bin width in the
        figure legend: the shape of a histogram depends on it)."""
        values = self._samples.frame["x"].to_numpy(dtype=float)
        if self._log:
            if (values <= 0).any():
                raise DataShapeError(
                    "A log axis needs positive values; drop values <= 0 first"
                )
            values = np.log10(values)
        low, high = self._binrange or (float(values.min()), float(values.max()))
        if self._log and self._binrange is not None:
            if min(self._binrange) <= 0:
                raise DataShapeError("binrange on a log axis must be positive")
            low, high = math.log10(low), math.log10(high)
        if self._discrete:
            edges = np.arange(math.floor(low) - 0.5, math.ceil(high) + 1.0)
        elif self._binwidth is not None:
            width = math.log10(self._binwidth) if self._log else self._binwidth
            count = max(1, math.ceil((high - low) / width - 1e-9))
            edges = low + width * np.arange(count + 1)
        elif isinstance(self._bins, str | int | np.integer):
            if high == low:
                low, high = low - 0.5, high + 0.5
            edges = np.histogram_bin_edges(values, self._bins, range=(low, high))
        else:
            edges = np.asarray(self._bins, dtype=float)
            if edges.ndim != 1 or len(edges) < 2 or (np.diff(edges) <= 0).any():
                raise ValueError("bins as edges must be an increasing sequence")
            return edges
        return np.asarray(10**edges if self._log else edges, dtype=float)

    def _heights(self, edges: np.ndarray) -> dict[Any, tuple[np.ndarray, int]]:
        """``stat`` value per bin and the number of values, per group."""
        total = len(self._samples.frame)
        widths = np.diff(edges)
        result = {}
        for group in self._groups:
            values = self._values(group)
            counts = np.histogram(values, edges)[0].astype(float)
            norm = total if self._common_norm else len(values)
            if self._cumulative:
                counts = np.cumsum(counts)
            heights = {
                "count": counts,
                "frequency": counts / widths,
                "probability": counts / norm,
                "percent": 100 * counts / norm,
                "density": counts / norm
                if self._cumulative
                else counts / norm / widths,
            }[self._stat]
            result[group] = (heights, len(values))
        return result

    def source_data(self) -> pd.DataFrame:
        """The plotted numbers, one row per bin and group (for a journal's
        source-data file)."""
        edges = self.bin_edges
        rows = []
        for group, (heights, n) in self._heights(edges).items():
            counts = np.histogram(self._values(group), edges)[0]
            table = pd.DataFrame(
                {
                    "bin_start": edges[:-1],
                    "bin_end": edges[1:],
                    "count": np.cumsum(counts) if self._cumulative else counts,
                    f"cumulative_{self._stat}"
                    if self._cumulative
                    else self._stat: heights,
                    "n": n,
                }
            )
            if group is not None:
                table.insert(0, self._samples.hue_name or "group", group)
            rows.append(table)
        return pd.concat(rows, ignore_index=True)

    def _stat_label(self) -> str:
        label = _STAT_LABELS[self._stat]
        if self._cumulative:
            return (
                "Cumulative proportion"
                if self._stat == "density"
                else (f"Cumulative {label.lower()}")
            )
        return label

    # --------------------------------------------------------------- drawing
    def _default_labels(self) -> dict[str, str | None]:
        value, stat = self._samples.x_name, self._stat_label()
        return (
            {"x": value, "y": stat} if self._orient == "v" else {"x": stat, "y": value}
        )

    def _draw(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        groups = self._groups
        grouped = self._samples.hue_order is not None
        colors = self._group_colors(style, groups, grouped=grouped)
        edges = self.bin_edges
        heights = self._heights(edges)
        vertical = self._orient == "v"
        multiple = self._multiple if grouped else "layer"
        element = self._element or (
            "step" if grouped and multiple == "layer" else "bars"
        )
        if multiple == "dodge" and element == "step":
            raise ValueError("multiple='dodge' needs element='bars'")
        if self._kde is not None and multiple == "stack":
            raise ValueError("Density curves are not stacked; use multiple='layer'")

        small = [g for g in groups if heights[g][1] < SMALL_SAMPLE]
        if small and not self._rug:
            which = "" if not grouped else f" (groups: {', '.join(map(str, small))})"
            emit(
                SmallSampleWarning,
                f"Fewer than {SMALL_SAMPLE} values{which}: the histogram's shape "
                "will mostly reflect the bin choice. Show the individual values "
                "too, e.g. with .rug().",
                stacklevel=5,
            )

        base = np.zeros(len(edges) - 1)
        widths = np.diff(edges)
        for i, group in enumerate(groups):
            values, n = heights[group]
            label = None
            if grouped:
                label = f"{group} (n = {n})" if self._show_n else str(group)
            color = colors[group]
            if element == "step":
                bottom = base if multiple == "stack" else 0
                ax.stairs(
                    values + base if multiple == "stack" else values,
                    edges,
                    baseline=bottom,
                    orientation="vertical" if vertical else "horizontal",
                    color=color,
                    linewidth=theme.line_width,
                    label=label,
                    zorder=3,
                )
                ax.stairs(
                    values + base if multiple == "stack" else values,
                    edges,
                    baseline=bottom,
                    orientation="vertical" if vertical else "horizontal",
                    fill=True,
                    color=color,
                    alpha=_STEP_FILL_ALPHA,
                    linewidth=0,
                    zorder=2,
                )
            else:
                if multiple == "dodge":
                    step = widths / len(groups)
                    left, size = edges[:-1] + step * i, step
                else:
                    left, size = edges[:-1], widths
                kwargs: dict[str, Any] = {
                    "color": color,
                    "label": label,
                    "align": "edge",
                    "linewidth": theme.bar_edge_width,
                    "edgecolor": theme.axes_background,
                    "alpha": _LAYER_ALPHA if multiple == "layer" and grouped else None,
                    "zorder": 2,
                }
                offset = base if multiple == "stack" else 0
                if vertical:
                    ax.bar(left, values, size, bottom=offset, **kwargs)
                else:
                    ax.barh(left, values, size, left=offset, **kwargs)
            if multiple == "stack":
                base = base + values

        if self._kde is not None or self._fit is not None:
            self._draw_curves(ax, style, colors, edges, heights)
        if self._rug:
            self._draw_rug(ax, style, colors)
        if self._reflines:
            self._draw_reflines(ax, style, colors)
        self._style_axes(ax, style, edges)
        if grouped:
            self._draw_legend(ax, style, n=len(groups), title=self._samples.hue_name)
        elif self._show_n:
            ax.annotate(
                f"n = {heights[None][1]}",
                xy=(1, 1),
                xycoords="axes fraction",
                xytext=(-2, -2),
                textcoords="offset points",
                ha="right",
                va="top",
                fontsize=style.sizes.tick,
                color=theme.text_color,
            )

    def _scale(self, n: int, edges: np.ndarray) -> float:
        """Factor turning a probability density into the bars' ``stat``."""
        total = len(self._samples.frame)
        share = n / total if self._common_norm else 1.0
        width = float(np.mean(np.diff(edges)))
        if self._cumulative:
            return {"count": n, "probability": share, "percent": 100 * share}.get(
                self._stat, share
            )
        return {
            "count": n * width,
            "frequency": float(n),
            "probability": share * width,
            "percent": 100 * share * width,
            "density": share,
        }[self._stat]

    def _draw_curves(
        self,
        ax: Axes,
        style: Style,
        colors: dict[Any, str],
        edges: np.ndarray,
        heights: dict[Any, tuple[np.ndarray, int]],
    ) -> None:
        theme = style.theme
        grouped = self._samples.hue_order is not None
        if self._log and self._kde is not None:
            raise DataShapeError("Density curves on a log axis are not supported")
        for group in self._groups:
            values = self._values(group)
            n = heights[group][1]
            color = colors[group] if grouped else (theme.text_color or "#333333")
            factor = self._scale(n, edges)
            curves: list[tuple[np.ndarray, np.ndarray, str]] = []
            if self._kde is not None:
                if n < 2:
                    raise DataShapeError(
                        f"A density curve needs at least 2 values{_of(group)}"
                    )
                bw = _bandwidth(values, self._kde["bw_adjust"])
                pad = self._kde["cut"] * bw
                grid = np.linspace(
                    values.min() - pad, values.max() + pad, _CURVE_POINTS
                )
                curve = _gaussian_kde(values, grid, bw, cumulative=self._cumulative)
                curves.append((grid, curve, "-"))
            if self._fit == "normal":
                if n < 2 or np.ptp(values) == 0:
                    raise DataShapeError(
                        f"A normal fit needs at least 2 different values{_of(group)}"
                    )
                dist = NormalDist(float(values.mean()), float(values.std(ddof=1)))
                grid = np.linspace(edges[0], edges[-1], _CURVE_POINTS)
                at = dist.cdf if self._cumulative else dist.pdf
                curves.append((grid, np.array([at(v) for v in grid]), "--"))
            for grid, curve, linestyle in curves:
                ys = curve * factor
                xy = (grid, ys) if self._orient == "v" else (ys, grid)
                ax.plot(*xy, color=color, lw=theme.line_width, ls=linestyle, zorder=4)

    def _draw_rug(self, ax: Axes, style: Style, colors: dict[Any, str]) -> None:
        theme = style.theme
        grouped = self._samples.hue_order is not None
        for group in self._groups:
            color = colors[group] if grouped else (theme.text_color or "#333333")
            values = self._values(group)
            if self._orient == "v":
                ax.vlines(
                    values,
                    0,
                    _RUG_HEIGHT,
                    transform=ax.get_xaxis_transform(),
                    color=color,
                    lw=theme.axis_line_width,
                    alpha=0.7,
                    zorder=5,
                )
            else:
                ax.hlines(
                    values,
                    0,
                    _RUG_HEIGHT,
                    transform=ax.get_yaxis_transform(),
                    color=color,
                    lw=theme.axis_line_width,
                    alpha=0.7,
                    zorder=5,
                )

    def _draw_reflines(self, ax: Axes, style: Style, colors: dict[Any, str]) -> None:
        theme = style.theme
        grouped = self._samples.hue_order is not None
        lines: list[tuple[float, str, str]] = []
        for value in self._reflines:
            if isinstance(value, str):
                for group in self._groups:
                    data = self._values(group)
                    center = float(
                        np.mean(data) if value == "mean" else np.median(data)
                    )
                    color = colors[group] if grouped else (theme.text_color or "#333")
                    lines.append((center, color, value))
            else:
                lines.append((float(value), theme.text_color or "#333", ""))
        vertical = self._orient == "v"
        for position, color, name in lines:
            line = ax.axvline if vertical else ax.axhline
            line(position, color=color, lw=theme.axis_line_width, ls="--", zorder=4)
            if self._refline_labels:
                text = f"{name} {position:.3g}".strip()
                ax.annotate(
                    text,
                    xy=(position, 1) if vertical else (1, position),
                    xycoords=ax.get_xaxis_transform()
                    if vertical
                    else ax.get_yaxis_transform(),
                    xytext=(2, -2),
                    textcoords="offset points",
                    ha="left" if vertical else "right",
                    va="top" if vertical else "bottom",
                    fontsize=style.sizes.tick,
                    color=color,
                )

    def _style_axes(self, ax: Axes, style: Style, edges: np.ndarray) -> None:
        theme = style.theme
        vertical = self._orient == "v"
        value_axis, count_axis = (
            (ax.xaxis, ax.yaxis) if vertical else (ax.yaxis, ax.xaxis)
        )
        if vertical:
            ax.set_xlim(edges[0], edges[-1])
            ax.margins(y=0.05)
        else:
            ax.set_ylim(edges[0], edges[-1])
            ax.margins(x=0.05)
        if self._discrete and len(edges) <= 25:
            centers = (edges[:-1] + edges[1:]) / 2
            if vertical:
                ax.set_xticks(centers)
            else:
                ax.set_yticks(centers)
        grid = theme.grid
        # "value"/"category" follow bars: the bar height (count) is the value.
        if grid in ("both", "value") or grid == ("y" if vertical else "x"):
            count_axis.grid(True)
        if grid in ("both", "category") or grid == ("x" if vertical else "y"):
            value_axis.grid(True)
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


def _of(group: Any) -> str:
    return "" if group is None else f" in group {group!r}"


def histogram(
    data: Any = None,
    x: Any = None,
    hue: Any = None,
    *,
    bins: int | BinRule | Sequence[float] = "auto",
    binwidth: float | None = None,
    binrange: tuple[float, float] | None = None,
    discrete: bool = False,
    stat: Stat = "count",
    common_norm: bool = False,
    cumulative: bool = False,
    multiple: Multiple = "layer",
    element: Element | None = None,
    orient: Orient = "v",
    hue_order: Sequence[Any] | None = None,
) -> HistogramPlot:
    """Histogram of one numeric variable, optionally split into groups.

    Args:
        data: Values (list, array, Series), a DataFrame with ``x=``/``hue=``
            column names, a wide DataFrame or 2-D array (one group per column),
            or a dict ``{group: values}``.
        x: Column with the values (or the values themselves without ``data``).
        hue: Column with groups (or one group per value without ``data``).
        bins: Number of bins, bin edges, or a rule: ``"auto"`` (default),
            ``"fd"`` (Freedman-Diaconis), ``"sturges"``, ``"scott"``, ...
        binwidth: Width of each bin; overrides ``bins``.
        binrange: ``(low, high)`` range covered by the bins.
        discrete: One bin per integer, centered on it (counts, scores).
        stat: Bar height: ``"count"``, ``"probability"`` (sums to 1),
            ``"percent"`` (sums to 100), ``"density"`` (area 1) or
            ``"frequency"`` (count divided by bin width).
        common_norm: Normalize all groups together instead of each on its own,
            so group sizes show. Ignored for ``stat="count"``.
        cumulative: Running total from left to right.
        multiple: How groups share bins: ``"layer"`` (overlaid), ``"stack"``
            or ``"dodge"`` (side by side).
        element: ``"bars"`` or ``"step"`` (outlines). Default: outlines for
            overlaid groups, which stay readable where they overlap.
        orient: ``"v"`` (bars up) or ``"h"`` (bars to the right).
        hue_order: Explicit group order.

    Missing values are left out. All groups share the same bins.

    Example:
        >>> sp.histogram(df, x="age", hue="sex", stat="density").kde()  # doctest: +SKIP
    """
    return HistogramPlot(
        _samples(data, x, hue, hue_order),
        bins=bins,
        binwidth=binwidth,
        binrange=binrange,
        discrete=discrete,
        stat=stat,
        common_norm=common_norm,
        cumulative=cumulative,
        multiple=multiple,
        element=element,
        orient=orient,
    )


hist = histogram
