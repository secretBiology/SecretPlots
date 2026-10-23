"""Line plots: one line per group along x, with error bands or bars from
replicates (or your own errors), markers, dashes, per-unit lines and end labels."""

import difflib
import math
from collections.abc import Callable, Hashable, Sequence
from dataclasses import replace
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle

from SecretPlots.core.colors import combined_alpha
from SecretPlots.core.data import source_frame
from SecretPlots.core.missing import MissingPolicy
from SecretPlots.core.resolve import Style
from SecretPlots.core.stats import t_quantile
from SecretPlots.errors import DataShapeError, PolicyWarning, emit
from SecretPlots.plots.scatter import _MARKERS
from SecretPlots.plots.series import SeriesPlot, _Series, series

Estimator = Literal["mean", "median", "sum"] | Callable[[pd.Series], float]
ErrorKind = Literal["sd", "sem", "ci", "pi"]
ErrorDisplay = Literal["band", "bars"]

_ESTIMATORS = ("mean", "median", "sum")
_ERRORS = ("sd", "sem", "ci", "pi")
# Common spellings from other tools -> what SecretPlots calls them.
_ERROR_ALIASES = {
    "std": "sd",
    "stdev": "sd",
    "se": "sem",
    "stderr": "sem",
    "confidence": "ci",
    "percentile": "pi",
}
_ERROR_NAMES = {
    "sd": "standard deviation",
    "sem": "standard error of the mean",
    "ci": "confidence interval",
    "pi": "percentile interval",
}
#: Dash patterns for style= values (the first is solid).
_DASHES: tuple[Any, ...] = (
    "-",
    (0, (4.0, 1.6)),
    (0, (1.0, 1.4)),
    (0, (6.0, 1.6, 1.0, 1.6)),
    (0, (2.4, 1.6)),
    (0, (6.0, 1.6, 1.0, 1.6, 1.0, 1.6)),
    (0, (8.0, 2.4)),
    (0, (1.0, 2.8)),
)
_BOOTSTRAP = 2000
_UNIT_ALPHA = 0.3
_UNIT_WIDTH = 0.5
_GRADIENT_BOOST = 2.0


def _close(value: str, options: Sequence[str]) -> str:
    match = difflib.get_close_matches(value, options, n=1)
    return f" Did you mean {match[0]!r}?" if match else ""


def _check_error(error: object) -> ErrorKind | None:
    if error is None or error in _ERRORS:
        return error  # type: ignore[return-value]
    if isinstance(error, str) and error in _ERROR_ALIASES:
        hint = f" Did you mean error={_ERROR_ALIASES[error]!r}?"
    else:
        hint = _close(error, _ERRORS) if isinstance(error, str) else ""
    raise ValueError(
        f"Unknown error={error!r}.{hint} Error bars can be 'sd' (standard "
        "deviation), 'sem' (standard error of the mean), 'ci' (confidence "
        "interval of the mean), 'pi' (percentile interval of the values) or None."
    )


def _check_estimator(estimator: object) -> None:
    if estimator is None or callable(estimator) or estimator in _ESTIMATORS:
        return
    if isinstance(estimator, str) and (
        estimator in _ERRORS or estimator in _ERROR_ALIASES
    ):
        kind = _ERROR_ALIASES.get(estimator, estimator)
        raise ValueError(
            f"estimator={estimator!r} looks like an error bar. estimator sets the "
            f"line's value ('mean', 'median', 'sum'); for error bars use "
            f"error={kind!r}."
        )
    hint = _close(estimator, _ESTIMATORS) if isinstance(estimator, str) else ""
    raise ValueError(
        f"Unknown estimator={estimator!r}.{hint} Use 'mean', 'median', 'sum', a "
        "function that takes the values at one x, or None to draw rows as they are."
    )


def _levels(
    kind: ErrorKind | None, level: float | Sequence[float] | None
) -> list[float]:
    """Interval levels, widest first."""
    coverage = kind in ("ci", "pi")
    if level is None:
        return [0.95 if coverage else 1.0]
    levels = [level] if isinstance(level, int | float) else list(level)
    if not levels:
        raise ValueError("level needs at least one value")
    for value in levels:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError("level must be a number or a list of numbers")
        if coverage and not 0 < value < 1:
            raise ValueError(
                f"level for error={kind!r} is a coverage, 0 to 1 (e.g. 0.95)"
            )
        if not coverage and value <= 0:
            raise ValueError(f"level for error={kind!r} is a multiple, e.g. 1 or 2")
    return sorted((float(v) for v in levels), reverse=True)


def _interval(
    values: np.ndarray, center: float, kind: ErrorKind, level: float, estimator: Any
) -> tuple[float, float]:
    values = values[np.isfinite(values)]
    n = len(values)
    if n == 0 or not math.isfinite(center):
        return math.nan, math.nan
    if kind == "pi":
        tail = 50 * (1 - level)
        low, high = np.percentile(values, [tail, 100 - tail])
        return float(low), float(high)
    if n < 2:
        return math.nan, math.nan
    sd = float(np.std(values, ddof=1))
    if kind == "sd":
        return center - level * sd, center + level * sd
    sem = sd / math.sqrt(n)
    if kind == "sem":
        return center - level * sem, center + level * sem
    # ci: t interval for the mean (or a sum of n values); bootstrap for medians.
    if estimator == "median":
        rng = np.random.default_rng(0)
        medians = np.median(values[rng.integers(0, n, (_BOOTSTRAP, n))], axis=1)
        tail = 50 * (1 - level)
        low, high = np.percentile(medians, [tail, 100 - tail])
        return float(low), float(high)
    half = t_quantile(0.5 + level / 2, n - 1) * sem
    if estimator == "sum":
        half *= n
    return center - half, center + half


class LinePlot(SeriesPlot):
    """Created by :func:`line`."""

    kind = "line"

    def __init__(
        self,
        data: _Series,
        *,
        error: ErrorKind | None = None,
        estimator: Estimator | None = "mean",
    ) -> None:
        super().__init__(data)
        error = _check_error(error)
        _check_estimator(estimator)
        frame = data.frame
        own = "yerr_minus" in frame or "xerr_minus" in frame
        if error and own:
            raise ValueError("Pass error= (from replicates) or yerr=/xerr=, not both")
        if error and estimator is None:
            raise ValueError("error= summarizes replicates; it needs an estimator")
        if error == "ci" and estimator not in ("mean", "median", "sum"):
            raise ValueError(
                "error='ci' needs estimator 'mean', 'median' or 'sum'; for your "
                "own function use error='pi' or 'sd'"
            )
        self._error = error
        self._estimator = None if own else estimator
        self._display: ErrorDisplay = "band"
        self._levels = _levels(error, None)
        self._band_edges = False
        self._capsize: float | None = None
        self._dodge = 0.0
        self._markers: str | None = None
        self._marker_size: float | None = None
        self._marker_filled = True
        self._fill: dict[str, Any] | None = None
        self._table = self._aggregate()

    # ----------------------------------------------------------------- verbs
    def errorbars(
        self,
        display: ErrorDisplay = "band",
        *,
        level: float | Sequence[float] | None = None,
        edges: bool = False,
        capsize: float | None = None,
        dodge: float = 0.0,
    ) -> Self:
        """How the error bars look; what they show is set with ``error=`` (or
        ``yerr=``) on :func:`line`.

        Args:
            display: ``"band"`` (a shaded band along the line) or ``"bars"``
                (an error bar at each x).
            level: For ``"ci"``/``"pi"`` the coverage, 0 to 1 (default 0.95);
                for ``"sd"``/``"sem"`` a multiple (default 1). Several values,
                e.g. ``(0.5, 0.8, 0.95)``, draw nested intervals: a fan chart
                with bands, thicker inner bars with bars.
            edges: Bands only: thin lines along the band's edges.
            capsize: Bars only: cap length in pt (default: the theme's
                ``errorbar_capsize``); 0 for none.
            dodge: Shift groups apart along x so their bars don't overlap, as
                a fraction of the smallest step between x values (e.g. 0.3).
        """
        if display not in ("band", "bars"):
            raise ValueError(
                f"Unknown display={display!r}{_close(str(display), ('band', 'bars'))}"
                " Use 'band' or 'bars'."
            )
        has_errors = self._error or "yerr_minus" in self._data.frame
        if not has_errors and "xerr_minus" not in self._data.frame:
            raise ValueError(
                "errorbars() sets how error bars look; first choose what they "
                "show with error='sd'/'sem'/'ci'/'pi' or yerr= in sp.line()"
            )
        if level is not None and not self._error:
            raise ValueError("level= applies to error= from replicates, not yerr=")
        if capsize is not None and capsize < 0:
            raise ValueError("capsize must be 0 or more")
        if not 0 <= dodge < 1:
            raise ValueError("dodge must be between 0 and 1")
        if dodge and self._data.x_kind == "datetime":
            raise ValueError("dodge works with numeric or category x, not dates")
        self._display = display
        self._levels = _levels(self._error, level)
        self._band_edges = edges
        self._capsize = capsize
        self._dodge = dodge
        return self._changed()

    def markers(
        self,
        marker: str | bool = True,
        *,
        size: float | None = None,
        filled: bool = True,
    ) -> Self:
        """A marker at every data point. With ``style=`` each style value gets
        its own shape.

        Args:
            marker: A matplotlib marker like ``"o"``, ``"s"`` or ``"D"``;
                ``True`` uses the theme's marker, ``False`` removes them.
            size: Marker diameter in pt (default: the theme's marker_size).
            filled: ``False`` draws hollow markers (background-colored inside).
        """
        if marker is False:
            self._markers = None
            return self._changed()
        if isinstance(marker, str):
            try:
                MarkerStyle(marker)
            except ValueError:
                raise ValueError(
                    f"Unknown marker {marker!r}. Use a matplotlib marker such as "
                    "'o', 's', '^', 'D', 'v', 'x' or '+'."
                ) from None
        if size is not None and size <= 0:
            raise ValueError("marker size must be positive")
        self._markers = "" if marker is True else marker
        self._marker_size = size
        self._marker_filled = filled
        return self._changed()

    def fill(
        self,
        show: bool = True,
        *,
        to: float = 0.0,
        gradient: bool = False,
        alpha: float | None = None,
    ) -> Self:
        """Shade the area between each line and a baseline.

        Args:
            show: ``False`` removes the shading.
            to: Baseline value the area reaches down (or up) to.
            gradient: Fade the shading from the line toward the baseline.
            alpha: Opacity, 0 to 1 (default: the theme's ``fill_alpha``; twice
                that at the line with ``gradient``).
        """
        if alpha is not None and not 0 <= alpha <= 1:
            raise ValueError("alpha must be between 0 and 1")
        self._fill = {"to": float(to), "gradient": gradient, "alpha": alpha}
        if not show:
            self._fill = None
        return self._changed()

    # ------------------------------------------------------------------ data
    def _keys(self) -> list[str]:
        return [k for k in ("hue", "style") if k in self._data.frame]

    def encode_groups(self, *, markers: bool = True) -> Self:
        """Identify hue groups with color and dash patterns (and markers).

        Args:
            markers: Also use a different marker shape for each group.
                Replaces any existing style mapping with the hue mapping.
        """
        if not self._grouped:
            raise DataShapeError("encode_groups() needs hue= groups")
        frame = self._data.frame.copy()
        frame["style"] = frame["hue"]
        names = {**self._data.names, "style": self._data.names.get("hue")}
        self._data = replace(
            self._data, frame=frame, names=names, style_order=list(self._groups)
        )
        if markers:
            self.markers()
        return self._data_changed()

    def _data_changed(self) -> Self:
        self._table = self._aggregate()
        return super()._data_changed()

    def _aggregate(self) -> pd.DataFrame:
        """One row per line point: ``value``, ``n`` and the error columns."""
        frame = self._data.frame
        keys = [*self._keys(), "x"]
        if self._estimator is None:
            table = frame.rename(columns={"y": "value"}).copy()
            own = "yerr_minus" in table or "xerr_minus" in table
            if own and table.duplicated(keys).any():
                raise DataShapeError(
                    "yerr=/xerr= give the error of each point, so each x can "
                    "appear only once per line; aggregate first, or use error="
                )
            table["n"] = 1
            return table
        grouped = frame.groupby(keys, sort=False, observed=True)["y"]
        table = pd.DataFrame(
            {"value": grouped.agg(self._estimator), "n": grouped.count()}
        ).reset_index()
        if self._error and (table["n"] <= 1).all():
            raise DataShapeError(
                f"error={self._error!r} needs replicates (several rows per x), "
                "but every point has a single value."
            )
        if self._data.missing == "gap":
            # A missing replicate is unknown, not zero or an observed mean.
            incomplete = grouped.count().to_numpy() < grouped.size().to_numpy()
            table.loc[incomplete, "value"] = np.nan
        if self._data.sort:
            table = table.sort_values("x", kind="stable")
        return table.reset_index(drop=True)

    def _intervals(self, level: float) -> tuple[np.ndarray, np.ndarray]:
        table = self._table
        if self._error is None:
            minus = table.get("yerr_minus")
            if minus is None:
                nan = np.full(len(table), np.nan)
                return nan, nan
            return (
                (table["value"] - minus).to_numpy(dtype=float),
                (table["value"] + table["yerr_plus"]).to_numpy(dtype=float),
            )
        frame = self._data.frame
        keys = [*self._keys(), "x"]
        values = {
            k if isinstance(k, tuple) else (k,): g.to_numpy(dtype=float)
            for k, g in frame.groupby(keys, sort=False, observed=True)["y"]
        }
        bounds = [
            _interval(
                values[tuple(row[k] for k in keys)],
                row["value"],
                self._error,
                level,
                self._estimator,
            )
            for _, row in table.iterrows()
        ]
        low, high = np.array(bounds, dtype=float).reshape(-1, 2).T
        return low, high

    def source_data(self) -> pd.DataFrame:
        """The plotted numbers, one row per point of each line (for a journal's
        source-data file). Generated columns that clash with your column
        names get a ``_computed`` suffix."""
        table = self._table
        names = self._data.names
        cols: list[tuple[Hashable, bool, Any]] = [
            (names.get(key) or key, bool(names.get(key)), table[key].to_numpy())
            for key in self._keys()
        ]
        cols.append(
            (
                names.get("x") or "x",
                bool(names.get("x")),
                self._x_values(table["x"].to_numpy()),
            )
        )
        cols.append(
            (names.get("y") or "y", bool(names.get("y")), table["value"].to_numpy())
        )
        cols.append(("n", False, table["n"].to_numpy()))
        if self._error or "yerr_minus" in table:
            prefix = self._error or "error"
            for level in self._levels if self._error else [None]:
                low, high = self._intervals(level or 0.0)
                tag = (
                    prefix
                    if level is None or len(self._levels) == 1
                    else (f"{prefix}{level:g}")
                )
                cols += [(f"{tag}_low", False, low), (f"{tag}_high", False, high)]
        if "xerr_minus" in table:
            cols += [
                ("x_low", False, (table["x"] - table["xerr_minus"]).to_numpy()),
                ("x_high", False, (table["x"] + table["xerr_plus"]).to_numpy()),
            ]
        return source_frame(cols)

    def caption(self) -> str:
        """Figure-legend text saying what the line and error bars show."""
        parts = []
        if self._estimator is not None:
            what = self._estimator if isinstance(self._estimator, str) else "summary"
            parts.append(f"Lines show the {what}")
        if self._error:
            name = _ERROR_NAMES[self._error]
            levels = self._levels
            if self._error in ("ci", "pi"):
                amounts = ", ".join(f"{100 * v:g}%" for v in reversed(levels))
                method = (
                    " (bootstrap)"
                    if self._error == "ci" and self._estimator == "median"
                    else ""
                )
                shown = f"{amounts} {name}{'s' if len(levels) > 1 else ''}{method}"
            else:
                amounts = ", ".join(f"{v:g}" for v in reversed(levels))
                shown = name if levels == [1.0] else f"{amounts} x {name}"
            parts.append(
                f"{'bands' if self._display == 'band' else 'error bars'} the {shown}"
            )
        n = self._table["n"]
        if self._estimator is not None and len(n):
            low, high = int(n.min()), int(n.max())
            parts.append(f"n = {low}" if low == high else f"n = {low}-{high} per point")
        return "; ".join(parts) + "." if parts else ""

    # --------------------------------------------------------------- drawing
    def _line_styles(self, theme: Any) -> tuple[dict[Any, Any], dict[Any, str]]:
        values = self._data.style_order or []
        if len(values) > len(_DASHES):
            raise DataShapeError(
                f"style= has {len(values)} values, but there are only "
                f"{len(_DASHES)} dash patterns; use hue= for more groups"
            )
        dashes = dict(zip(values, _DASHES, strict=False))
        first = self._markers or theme.marker or "o"
        cycle = [first, *(m for m in _MARKERS if m != first)]
        shapes = dict(zip(values, cycle, strict=False))
        return dashes, shapes

    def _marker_kwargs(
        self, theme: Any, color: str, shape: str | None
    ) -> dict[str, Any]:
        if self._markers is None:
            return {}
        marker = shape or self._markers or theme.marker or "o"
        size = self._marker_size or theme.marker_size or 5.0
        filled = MarkerStyle(marker).is_filled()
        if not filled:
            return {
                "marker": marker,
                "markersize": size,
                "markeredgewidth": theme.line_width,
            }
        if self._marker_filled:
            # A background-colored ring separates the marker from the line.
            return {
                "marker": marker,
                "markersize": size,
                "markerfacecolor": color,
                "markeredgecolor": theme.axes_background,
                "markeredgewidth": theme.marker_edge_width,
            }
        return {
            "marker": marker,
            "markersize": size,
            "markerfacecolor": theme.axes_background,
            "markeredgecolor": color,
            "markeredgewidth": max((theme.line_width or 1.5) * 0.75, 0.5),
        }

    def _offsets(self, groups: list[Any]) -> dict[Any, float]:
        if not self._dodge or len(groups) < 2:
            return dict.fromkeys(groups, 0.0)
        steps = np.diff(np.unique(self._table["x"].to_numpy(dtype=float)))
        step = float(steps.min()) if len(steps) else 1.0
        width = self._dodge * step
        return {
            g: -width / 2 + width * (i + 0.5) / len(groups)
            for i, g in enumerate(groups)
        }

    def _draw(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        groups = self._groups
        colors = self._group_colors(style, groups, grouped=self._grouped)
        dashes, shapes = self._line_styles(theme)
        offsets = self._offsets(groups)
        table = self._table
        intervals = [self._intervals(level) for level in self._levels]
        frame = self._data.frame
        ends: dict[Any, tuple[Any, Any, float, str, float]] = {}

        for group in groups:
            color = colors[group]
            if "units" in frame:
                self._draw_units(ax, style, self._rows(group, frame), color, dashes)
            for value in self._data.style_order or [None]:
                mask = np.ones(len(table), bool)
                if group is not None:
                    mask &= (table["hue"] == group).to_numpy()
                if value is not None:
                    mask &= (table["style"] == value).to_numpy()
                if not mask.any() or (self._estimator is None and "units" in frame):
                    continue
                rows = table[mask]
                x = rows["x"].to_numpy() + offsets[group] if self._dodge else rows["x"]
                y = rows["value"].to_numpy(dtype=float)
                if self._fill is not None:
                    self._draw_fill(ax, style, x, y, color)
                self._draw_errors(
                    ax,
                    style,
                    rows,
                    x,
                    y,
                    [(lo[mask], hi[mask]) for lo, hi in intervals],
                    color,
                )
                ax.plot(
                    x,
                    y,
                    color=color,
                    lw=theme.line_width,
                    ls=dashes.get(value, "-"),
                    solid_capstyle="round",
                    solid_joinstyle="round",
                    dash_capstyle="butt",
                    zorder=3,
                    **self._marker_kwargs(
                        theme, color, shapes.get(value) if value is not None else None
                    ),
                )
                finite = np.flatnonzero(np.isfinite(y))
                if len(finite):
                    i = finite[-1]
                    end = (group, np.asarray(x)[i], float(y[i]), color, float(y[i]))
                    if group not in ends or end[1] > ends[group][1]:
                        ends[group] = end

        margin = 0.03 if self._markers is not None or self._display == "bars" else 0.0
        self._style_axes(ax, style, x_margin=margin)
        if self._end_labels:
            self._draw_end_labels(ax, style, list(ends.values()))
        self._legend_entries(ax, style, groups, colors, dashes, shapes)

    def _draw_units(
        self,
        ax: Axes,
        style: Style,
        rows: pd.DataFrame,
        color: str,
        dashes: dict[Any, Any],
    ) -> None:
        theme = style.theme
        alone = self._estimator is None
        for keys, unit in rows.groupby(
            [k for k in ("style", "units") if k in rows], sort=False, observed=True
        ):
            value = keys[0] if "style" in rows else None
            ax.plot(
                unit["x"],
                unit["y"],
                color=color,
                alpha=combined_alpha(color, None if alone else _UNIT_ALPHA),
                lw=(theme.line_width or 1.5) * (1.0 if alone else _UNIT_WIDTH),
                ls=dashes.get(value, "-"),
                solid_joinstyle="round",
                zorder=2.5 if alone else 1.8,
            )

    def _draw_fill(
        self, ax: Axes, style: Style, x: Any, y: np.ndarray, color: str
    ) -> None:
        assert self._fill is not None
        alpha = self._fill["alpha"]
        if alpha is None:
            alpha = (
                0.22
                if style.theme.fill_alpha is None
                else float(style.theme.fill_alpha)
            )
            if self._fill["gradient"]:
                alpha = min(1.0, alpha * _GRADIENT_BOOST)
        base = self._fill["to"]
        if self._fill["gradient"] and "y" not in self._log_axes:
            area = self._gradient(ax, np.asarray(x), y, base, color, alpha, zorder=1.6)
        else:
            area = ax.fill_between(
                x,
                y,
                base,
                color=color,
                alpha=combined_alpha(color, alpha),
                lw=0,
                zorder=1.6,
            )
        area.sticky_edges.y.append(base)  # no margin below the baseline

    def _draw_errors(
        self,
        ax: Axes,
        style: Style,
        rows: pd.DataFrame,
        x: Any,
        y: np.ndarray,
        intervals: list[tuple[np.ndarray, np.ndarray]],
        color: str,
    ) -> None:
        theme = style.theme
        if "xerr_minus" in rows:
            ax.errorbar(
                x,
                y,
                xerr=[
                    rows["xerr_minus"].to_numpy(float),
                    rows["xerr_plus"].to_numpy(float),
                ],
                fmt="none",
                ecolor=color,
                elinewidth=theme.axis_line_width,
                capsize=theme.errorbar_capsize
                if self._capsize is None
                else self._capsize,
                capthick=theme.axis_line_width,
                zorder=2.8,
            )
        if not self._error and "yerr_minus" not in rows:
            return
        if self._error == "pi":
            low = np.min([lo for lo, _ in intervals], axis=0)  # widest level
            high = np.max([hi for _, hi in intervals], axis=0)
            outside = int(np.sum((y < low) | (y > high)))
            if outside:
                what = (
                    self._estimator if isinstance(self._estimator, str) else "estimate"
                )
                emit(
                    PolicyWarning,
                    f"At {outside} x position(s) the {what} lies "
                    "outside the percentile interval. error='pi' shows where "
                    "the individual observations fall, not the uncertainty of "
                    f"the {what}, so the interval is drawn as "
                    "computed rather than stretched to reach the estimate. For "
                    "the uncertainty of the estimate use error='ci'.",
                    stacklevel=6,
                )
        alpha = 0.22 if theme.fill_alpha is None else float(theme.fill_alpha)
        if self._display == "band":
            # Nested bands overlap, so the inner (narrower) ones get darker.
            each = alpha if len(intervals) == 1 else alpha * 0.75
            for low, high in intervals:
                ax.fill_between(
                    x,
                    low,
                    high,
                    color=color,
                    alpha=combined_alpha(color, each),
                    lw=0,
                    zorder=2,
                )
                if self._band_edges:
                    for edge in (low, high):
                        ax.plot(
                            x,
                            edge,
                            color=color,
                            lw=(theme.axis_line_width or 0.8) * 0.6,
                            alpha=combined_alpha(color, 0.6),
                            zorder=2.1,
                        )
            return
        widths = (
            np.linspace(
                theme.axis_line_width or 0.8,
                (theme.line_width or 1.5) * 1.6,
                len(intervals),
            )
            if len(intervals) > 1
            else [theme.axis_line_width]
        )
        caps = theme.errorbar_capsize if self._capsize is None else self._capsize
        for i, ((low, high), width) in enumerate(zip(intervals, widths, strict=True)):
            # Centred on the interval, not the estimate: a percentile interval
            # of the observations need not contain the estimate.
            ax.errorbar(
                x,
                (low + high) / 2,
                yerr=(high - low) / 2,
                fmt="none",
                ecolor=color,
                elinewidth=width,
                capsize=caps if i == 0 else 0,
                capthick=width,
                zorder=2.8,
            )

    def _legend_entries(
        self,
        ax: Axes,
        style: Style,
        groups: list[Any],
        colors: dict[Any, str],
        dashes: dict[Any, Any],
        shapes: dict[Any, str],
    ) -> None:
        data = self._data
        theme = style.theme
        frame = data.frame
        combined = (
            "hue" in frame and "style" in frame and frame["hue"].equals(frame["style"])
        )
        handles: list[Line2D] = []

        def proxy(label: Any, color: str, value: Any) -> None:
            shape = shapes.get(value) if value is not None else None
            handles.append(
                Line2D(
                    [],
                    [],
                    color=color,
                    lw=theme.line_width,
                    ls=dashes.get(value, "-"),
                    label=str(label),
                    **self._marker_kwargs(theme, color, shape),
                )
            )

        # End labels name the groups, so the legend keeps only the styles.
        show_groups = self._grouped and not self._end_labels
        if show_groups:
            for group in groups:
                proxy(group, colors[group], group if combined else None)
        if not combined:
            for value in data.style_order or []:
                proxy(value, theme.neutral or "#8d8d8d", value)
        if not handles:
            return
        for handle in handles:
            ax.add_line(handle)
        names = [data.names.get("hue") if show_groups else None]
        if not combined:
            names.append(data.names.get("style"))
        title = " / ".join(s for s in names if s)
        self._draw_legend(ax, style, n=len(handles), title=title or None)


def line(
    data: Any = None,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    *,
    style: Any = None,
    units: Any = None,
    error: ErrorKind | None = None,
    estimator: Estimator | None = "mean",
    yerr: Any = None,
    xerr: Any = None,
    sort: bool = True,
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
    style_order: Sequence[Any] | None = None,
    missing: MissingPolicy = "raise",
) -> LinePlot:
    """Line plot: one line per group along x. Rows sharing an x are summarized
    with ``estimator``, and ``error`` adds error bands (or bars) from them.

    Args:
        data: Long DataFrame or dict of columns (with ``x``/``y`` names); a
            wide DataFrame (index or ``x`` column → x, one line per numeric
            column); a Series (index → x); or a list/array of y values. Leave
            out to pass ``x=`` and ``y=`` as sequences.
        x: Column name or sequence of numbers, dates, or categories
            (e.g. ``"day 1"``, drawn evenly spaced in data order).
        y: Column name or sequence of numeric values.
        hue: Column with groups, drawn in different colors.
        style: Column with groups, drawn with different dashes (and marker
            shapes with ``.markers()``). Can be the same column as ``hue``.
        units: Column naming repeated measures (a subject, a cell): each is
            drawn as a faint thin line behind the summary line. With
            ``estimator=None`` only those lines are drawn.
        error: Error bands from the rows at each x: ``"sd"``, ``"sem"``,
            ``"ci"`` (confidence interval of the estimate) or ``"pi"``
            (percentile interval of the values). Change the level and look
            with ``.errorbars()``.
        estimator: ``"mean"`` (default), ``"median"``, ``"sum"``, a function,
            or ``None`` to draw the rows as they are.
        yerr: Your own errors: a column (or sequence) of half-widths, or a
            tuple of two columns ``(minus, plus)`` for asymmetric errors.
        xerr: Horizontal error bars, given like ``yerr``.
        sort: Connect points in x order (``False`` keeps the data order).
        order: Explicit order of category x values.
        hue_order: Explicit group order.
        style_order: Explicit order of the ``style`` values.

        missing: "raise" (default) rejects missing/non-finite data; "drop"
            removes affected rows and connects the remaining points; "gap"
            breaks lines/bands at missing values (x and groups must be present).

    Example:
        >>> sp.line(df, x="day", y="weight", hue="diet", error="ci")  # doctest: +SKIP
    """
    values: dict[str, Any] = {"y": y}
    for name, spec in (("yerr", yerr), ("xerr", xerr)):
        if spec is None:
            continue
        minus, plus = spec if isinstance(spec, tuple) else (spec, spec)
        if isinstance(spec, tuple) and len(spec) != 2:
            raise ValueError(f"{name} as a tuple must be (minus, plus)")
        values[f"{name}_minus"], values[f"{name}_plus"] = minus, plus
    data_ = series(
        data,
        x,
        values,
        {"hue": hue, "style": style, "units": units},
        hue_order=hue_order,
        style_order=style_order,
        order=order,
        sort=sort,
        missing=missing,
    )
    if xerr is not None and data_.x_kind == "datetime":
        raise DataShapeError("xerr= needs numeric x values")
    for column in ("yerr_minus", "yerr_plus", "xerr_minus", "xerr_plus"):
        if column in data_.frame and (data_.frame[column] < 0).any():
            raise DataShapeError(f"{column.split('_')[0]}= must not be negative")
    return LinePlot(data_, error=error, estimator=estimator)


plot = line
