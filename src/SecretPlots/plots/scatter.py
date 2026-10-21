"""Scatter plots: one marker per row, with optional groups, sizes and fit lines."""

import difflib
import math
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from SecretPlots.core.colors import extend_palette
from SecretPlots.core.data import _order
from SecretPlots.core.plot import Plot
from SecretPlots.core.resolve import Style
from SecretPlots.errors import DataShapeError

FitKind = Literal["linear", "lowess"]

_FITS = ("linear", "lowess")
#: Marker area range for size=, relative to marker_size**2.
_SIZE_RANGE = (0.4, 3.0)
_BAND_ALPHA = 0.18
_FIT_POINTS = 100


@dataclass(frozen=True)
class _Points:
    frame: pd.DataFrame  # columns x, y and optionally hue, size
    x_name: str | None
    y_name: str | None
    hue_name: str | None
    size_name: str | None
    hue_order: list[Any] | None


def _name(value: Hashable | None) -> str | None:
    return None if value is None else str(value)


def _points(
    data: Any,
    x: Any,
    y: Any,
    hue: Any,
    size: Any,
    hue_order: Sequence[Any] | None,
) -> _Points:
    if data is None:
        if x is None or y is None:
            raise DataShapeError(
                "Pass a DataFrame with x= and y= column names, or x= and y= as "
                "sequences of numbers"
            )
        if isinstance(x, str) or isinstance(y, str):
            raise DataShapeError(
                f"x={x!r} / y={y!r} look like column names, but no data was "
                "given; pass the DataFrame first: sp.scatter(df, x=..., y=...)"
            )
        columns = {"x": x, "y": y, "hue": hue, "size": size}
        try:
            frame = pd.DataFrame(
                {k: np.asarray(v) for k, v in columns.items() if v is not None}
            )
        except ValueError:
            raise DataShapeError(
                "x=, y= (and hue=/size=) must have equal length"
            ) from None
        names: tuple[Any, ...] = (None, None, None, None)
    else:
        if isinstance(data, Mapping):
            data = pd.DataFrame(data)
        if not isinstance(data, pd.DataFrame):
            arr = np.asarray(data)
            if arr.ndim != 2 or arr.shape[1] != 2:
                raise DataShapeError(
                    "Pass a DataFrame (or dict of columns) with x= and y= names, "
                    "or an array with two columns (x, y)"
                )
            data = pd.DataFrame(arr, columns=["x", "y"])
            x, y = (x or "x"), (y or "y")
        if x is None and y is None:
            numeric = data.select_dtypes("number").columns
            if len(numeric) != 2:
                raise DataShapeError(
                    "Pass x= and y= column names. Available: "
                    + ", ".join(map(str, data.columns))
                )
            x, y = numeric
        for label, column in (("x", x), ("y", y), ("hue", hue), ("size", size)):
            if label in ("x", "y") and column is None:
                raise DataShapeError(f"Pass {label}= (a column name)")
            if column is not None and column not in data.columns:
                raise DataShapeError(
                    f"Column {column!r} not found. "
                    f"Available: {', '.join(map(str, data.columns))}"
                )
        frame = pd.DataFrame({"x": data[x].to_numpy(), "y": data[y].to_numpy()})
        if hue is not None:
            frame["hue"] = data[hue].to_numpy()
            if isinstance(data[hue].dtype, pd.CategoricalDtype):
                frame["hue"] = pd.Categorical(
                    frame["hue"], categories=data[hue].cat.categories
                )
        if size is not None:
            frame["size"] = data[size].to_numpy()
        names = (x, y, hue, size)

    shown = {"x": names[0], "y": names[1], "size": names[3]}
    for column in ("x", "y", "size"):
        if column in frame:
            try:
                frame[column] = pd.to_numeric(frame[column])
            except (TypeError, ValueError):
                raise DataShapeError(
                    f"Values in {shown[column] or column!r} must be numeric"
                ) from None
    frame = frame.dropna().reset_index(drop=True)
    if frame.empty:
        raise DataShapeError("No data to plot (every row has a missing value)")
    if hue_order is not None and "hue" not in frame:
        raise DataShapeError("hue_order= needs hue= groups")
    return _Points(
        frame=frame,
        x_name=_name(names[0]),
        y_name=_name(names[1]),
        hue_name=_name(names[2]),
        size_name=_name(names[3]),
        hue_order=_order(frame["hue"], hue_order, "hue") if "hue" in frame else None,
    )


# ------------------------------------------------------------------ statistics
def _t_quantile(p: float, df: int) -> float:
    """Student's t quantile. Exact for df 1 and 2, otherwise the Cornish-Fisher
    expansion (Abramowitz & Stegun 26.7.5), within 0.2% for df >= 3."""
    if df == 1:
        return math.tan(math.pi * (p - 0.5))
    if df == 2:
        return (2 * p - 1) / math.sqrt(2 * p * (1 - p))
    x = NormalDist().inv_cdf(p)
    g1 = (x**3 + x) / 4
    g2 = (5 * x**5 + 16 * x**3 + 3 * x) / 96
    g3 = (3 * x**7 + 19 * x**5 + 17 * x**3 - 15 * x) / 384
    g4 = (79 * x**9 + 776 * x**7 + 1482 * x**5 - 1920 * x**3 - 945 * x) / 92160
    return x + g1 / df + g2 / df**2 + g3 / df**3 + g4 / df**4


@dataclass(frozen=True)
class _Fit:
    grid: np.ndarray
    line: np.ndarray
    band: tuple[np.ndarray, np.ndarray] | None = None
    slope: float = math.nan
    intercept: float = math.nan
    r2: float = math.nan


def _linear(x: np.ndarray, y: np.ndarray, ci: float | None, what: str) -> _Fit:
    n = len(x)
    if n < 2 or np.ptp(x) == 0:
        raise DataShapeError(
            f"A linear fit for {what} needs at least 2 different x values"
        )
    slope, intercept = np.polyfit(x, y, 1)
    grid = np.linspace(x.min(), x.max(), _FIT_POINTS)
    line = intercept + slope * grid
    resid = y - (intercept + slope * x)
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else math.nan
    band = None
    if ci is not None:
        if n < 3:
            raise DataShapeError(
                f"A confidence band for {what} needs at least 3 points; "
                "use .fit(ci=None)"
            )
        s = math.sqrt(ss_res / (n - 2))
        sxx = float(np.sum((x - x.mean()) ** 2))
        se = s * np.sqrt(1 / n + (grid - x.mean()) ** 2 / sxx)
        t = _t_quantile(0.5 + ci / 2, n - 2)
        band = (line - t * se, line + t * se)
    return _Fit(grid, line, band, float(slope), float(intercept), r2)


def _lowess(x: np.ndarray, y: np.ndarray, frac: float, what: str) -> _Fit:
    """Local linear regression with tricube weights (no robustness passes)."""
    n = len(x)
    if n < 3 or np.ptp(x) == 0:
        raise DataShapeError(
            f"A LOWESS fit for {what} needs at least 3 points with different x"
        )
    k = min(n, max(2, math.ceil(frac * n)))
    grid = np.linspace(x.min(), x.max(), _FIT_POINTS)
    line = np.empty_like(grid)
    for i, x0 in enumerate(grid):
        dist = np.abs(x - x0)
        h = np.partition(dist, k - 1)[k - 1]
        w = (
            np.clip(1 - (dist / h) ** 3, 0, None) ** 3
            if h > 0
            else (dist == 0).astype(float)
        )
        sw = w.sum()
        mx, my = (w * x).sum() / sw, (w * y).sum() / sw
        sxx = (w * (x - mx) ** 2).sum()
        slope = (w * (x - mx) * (y - my)).sum() / sxx if sxx > 1e-12 else 0.0
        line[i] = my + slope * (x0 - mx)
    return _Fit(grid, line)


def _equation(fit: _Fit) -> str:
    sign = "-" if fit.intercept < 0 else "+"
    return (
        f"y = {fit.slope:.3g}x {sign} {abs(fit.intercept):.3g}, "
        f"R\N{SUPERSCRIPT TWO} = {fit.r2:.2f}"
    )


# ------------------------------------------------------------------------ plot
class ScatterPlot(Plot):
    """Created by :func:`scatter`."""

    kind = "scatter"

    def __init__(self, points: _Points) -> None:
        super().__init__()
        self._points = points
        self._fit_kind: FitKind | None = None
        self._fit_ci: float | None = 0.95
        self._fit_per_group = True
        self._fit_frac = 2 / 3
        self._fit_stats = False

    # ----------------------------------------------------------------- verbs
    def fit(
        self,
        kind: FitKind | None = "linear",
        *,
        ci: float | None = 0.95,
        per_group: bool = True,
        frac: float = 2 / 3,
        stats: bool = False,
    ) -> Self:
        """Add a fit line through the points.

        Args:
            kind: ``"linear"`` (least squares), ``"lowess"`` (local smoother)
                or ``None`` to remove the fit.
            ci: Confidence level of the shaded band around a linear fit, e.g.
                ``0.95``; ``None`` for no band. Ignored for LOWESS.
            per_group: One fit per ``hue`` group (in the group's color) instead
                of one fit through all points.
            frac: LOWESS only: fraction of the points used for each local fit,
                0 to 1. Smaller follows the data more closely.
            stats: Linear only: print the equation and R² on the plot.
        """
        if kind is not None and kind not in _FITS:
            close = difflib.get_close_matches(str(kind), _FITS, n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise ValueError(f"Unknown fit {kind!r}.{hint} Use 'linear' or 'lowess'.")
        if ci is not None and not 0 < ci < 1:
            raise ValueError("ci must be between 0 and 1, e.g. 0.95, or None")
        if not 0 < frac <= 1:
            raise ValueError("frac must be between 0 and 1")
        if stats and kind != "linear":
            raise ValueError("stats=True needs a linear fit")
        self._fit_kind = kind
        self._fit_ci = ci
        self._fit_per_group = per_group
        self._fit_frac = frac
        self._fit_stats = stats
        return self._changed()

    # --------------------------------------------------------------- drawing
    def _default_labels(self) -> dict[str, str | None]:
        return {"x": self._points.x_name, "y": self._points.y_name}

    def _group_colors(self, style: Style, groups: list[Any]) -> dict[Any, str]:
        theme = style.theme
        highlight = set(self._highlight)
        if highlight and self._points.hue_order is None:
            raise DataShapeError(
                "highlight() picks hue= groups; this scatter plot has no groups"
            )
        unknown = highlight - set(groups)
        if unknown:
            raise DataShapeError(
                f"Cannot highlight {sorted(map(str, unknown))}: not a group. "
                f"Groups: {', '.join(map(str, groups))}"
            )
        if self._points.hue_order is None:
            return {None: theme.primary or "#4589ff"}
        base = extend_palette(
            theme.palette or (),
            len(groups),
            background=theme.background or "#ffffff",
            source=f"the palette from {style.provenance['palette']}",
        )
        colors = {g: self._color_map.get(g, base[i]) for i, g in enumerate(groups)}
        if highlight:
            muted = theme.muted or "#c6c6c6"
            colors = {g: c if g in highlight else muted for g, c in colors.items()}
        return colors

    def _areas(self, values: Any, base: float) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        sizes = self._points.frame.get("size")
        if sizes is None:
            return np.full(values.shape, base**2)
        lo, hi = float(sizes.min()), float(sizes.max())
        rel = (values - lo) / (hi - lo) if hi > lo else np.full(values.shape, 0.5)
        small, large = _SIZE_RANGE
        return np.asarray(base**2 * (small + (large - small) * rel))

    def _draw(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        frame = self._points.frame
        groups: list[Any] = list(self._points.hue_order or [None])
        colors = self._group_colors(style, groups)
        base = float(theme.marker_size or 5.0)
        areas = self._areas(frame["size"] if "size" in frame else frame["x"], base)

        for group in groups:
            mask = np.ones(len(frame), bool) if group is None else frame["hue"] == group
            ax.scatter(
                frame.loc[mask, "x"],
                frame.loc[mask, "y"],
                s=areas[np.asarray(mask)],
                color=colors[group],
                alpha=theme.marker_alpha,
                linewidths=theme.marker_edge_width,
                edgecolors=theme.axes_background,
                label=None if group is None else str(group),
                zorder=2,
            )

        if self._fit_kind is not None:
            self._draw_fits(ax, style, groups, colors)
        self._style_axes(ax, style)
        self._legend_entries(ax, style, groups)

    def _draw_fits(
        self, ax: Axes, style: Style, groups: list[Any], colors: dict[Any, str]
    ) -> None:
        theme = style.theme
        frame = self._points.frame
        per_group = self._fit_per_group and self._points.hue_order is not None
        targets: list[tuple[Any, pd.DataFrame, str]] = (
            [(g, frame[frame["hue"] == g], colors[g]) for g in groups]
            if per_group
            else [(None, frame, theme.text_color or "#333333")]
        )
        lines: list[tuple[str, str]] = []
        for group, rows, color in targets:
            what = "all points" if group is None else f"group {group!r}"
            x = rows["x"].to_numpy(dtype=float)
            y = rows["y"].to_numpy(dtype=float)
            if self._fit_kind == "linear":
                fit = _linear(x, y, self._fit_ci, what)
            else:
                fit = _lowess(x, y, self._fit_frac, what)
            ax.plot(fit.grid, fit.line, color=color, lw=theme.line_width, zorder=3)
            if fit.band is not None:
                ax.fill_between(
                    fit.grid, *fit.band, color=color, alpha=_BAND_ALPHA, lw=0, zorder=1
                )
            if self._fit_stats:
                prefix = "" if group is None else f"{group}: "
                lines.append((prefix + _equation(fit), color))
        for i, (text, color) in enumerate(lines):
            ax.annotate(
                text,
                xy=(0, 1),
                xycoords="axes fraction",
                xytext=(4, -4 - i * style.sizes.tick * 1.4),
                textcoords="offset points",
                va="top",
                fontsize=style.sizes.tick,
                color=color,
            )

    def _style_axes(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        grid = theme.grid
        # "value"/"category" follow bars; for points the value axis is y.
        if grid in ("both", "value", "y"):
            ax.yaxis.grid(True)
        if grid in ("both", "category", "x"):
            ax.xaxis.grid(True)
        if theme.value_axis_side == "right":
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
        visible = set(theme.spines or ())
        for side, spine in ax.spines.items():
            spine.set_visible(side in visible)

    def _legend_entries(self, ax: Axes, style: Style, groups: list[Any]) -> None:
        points = self._points
        n = len(groups) if points.hue_order is not None else 0
        if "size" in points.frame:
            sizes = points.frame["size"]
            lo, hi = float(sizes.min()), float(sizes.max())
            keys = [lo] if hi == lo else list(np.linspace(lo, hi, 3))
            base = float(style.theme.marker_size or 5.0)
            for value, area in zip(keys, self._areas(keys, base), strict=True):
                ax.scatter(
                    [],
                    [],
                    s=area,
                    color=style.theme.neutral,
                    alpha=style.theme.marker_alpha,
                    label=f"{value:.3g}",
                )
            n += len(keys)
        if n:
            names = [s for s in (points.hue_name, points.size_name) if s]
            self._draw_legend(ax, style, n=n, title=" / ".join(names) or None)


def scatter(
    data: Any = None,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    *,
    size: Any = None,
    hue_order: Sequence[Any] | None = None,
) -> ScatterPlot:
    """Scatter plot: one marker per row.

    Args:
        data: DataFrame or dict of columns (with ``x``/``y`` names), or an array
            with two columns. Leave out to pass ``x=`` and ``y=`` as sequences.
        x, y: Column names (or sequences of numbers when ``data`` is omitted).
        hue: Column with groups, drawn in different colors.
        size: Numeric column scaling marker area (with a size legend).
        hue_order: Explicit group order.

    Rows with a missing x, y, hue or size are left out.

    Example:
        >>> sp.scatter(df, x="age", y="bp", hue="sex").fit("linear")  # doctest: +SKIP
    """
    return ScatterPlot(_points(data, x, y, hue, size, hue_order))
