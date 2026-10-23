"""Filled areas: under a line, between two lines (a band), stacked (also as
percentages), or split into above/below colors."""

from collections.abc import Hashable, Sequence
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.ticker import PercentFormatter

from SecretPlots.core.colors import combined_alpha, with_alpha
from SecretPlots.core.data import source_columns, source_frame
from SecretPlots.core.missing import MissingPolicy
from SecretPlots.core.resolve import Style, checked_size
from SecretPlots.errors import DataShapeError, PolicyWarning, emit
from SecretPlots.plots.series import SeriesPlot, _is_number, _Series, series

Stack = bool | Literal["percent"]
Lines = Literal["auto", "top", "both", "none"]

_GRADIENT_BOOST = 2.0
_SPLIT_ALPHA = 0.75
#: Background-colored line between stacked layers, relative to line_width.
_SEPARATOR = 0.5


class FillBetweenPlot(SeriesPlot):
    """Created by :func:`fill_between` (alias :func:`area`)."""

    kind = "area"

    def __init__(self, data: _Series, *, band: bool, stack: Stack = False) -> None:
        super().__init__(data)
        if stack not in (False, True, "percent"):
            raise ValueError("stack must be True, False or 'percent'")
        if stack and band:
            raise ValueError(
                "Stacked areas start at a baseline; pass y2 as a number (or "
                "leave it out), not a column"
            )
        if stack == "percent" and len(data.frame) and data.frame["y2"].iloc[0] != 0:
            raise ValueError(
                "Percent stacks must start at baseline 0: their axis is fixed "
                "to 0-100%, so a stack lifted to "
                f"{data.frame['y2'].iloc[0]:g}-{data.frame['y2'].iloc[0] + 100:g} "
                "would be cut off. Leave baseline at 0."
            )
        keys = ["hue", "x"] if "hue" in data.frame else ["x"]
        if data.frame.duplicated(keys).any():
            raise DataShapeError(
                "Each x can appear only once per area. Summarize first (e.g. "
                "df.groupby(['group', 'x']).mean()), or use sp.line(..., error=) "
                "to draw a summary with error bands."
            )
        self._band = band
        self._stack: Stack = stack
        self._lines: Lines = "auto"
        self._line_width: float | None = None
        self._gradient_on = False
        self._split: dict[str, Any] | None = None

    # ----------------------------------------------------------------- verbs
    def lines(self, which: Lines = "auto", *, width: float | None = None) -> Self:
        """Lines along the edges of the areas.

        Args:
            which: ``"top"`` (the ``y1`` edge), ``"both"`` (``y1`` and ``y2``),
                ``"none"``, or ``"auto"``: the top edge for areas and stacks
                (thin background-colored separators between layers), no lines
                for bands, both lines when split by sign.
            width: Line width in pt (default: the theme's ``line_width``).
        """
        if which not in ("auto", "top", "both", "none"):
            raise ValueError("lines must be 'auto', 'top', 'both' or 'none'")
        if width is not None and width < 0:
            raise ValueError("line width must be 0 or more")
        self._lines = which
        self._line_width = width
        return self._changed()

    def gradient(self, show: bool = True) -> Self:
        """Fade each area from its ``y1`` edge (twice the theme's
        ``fill_alpha``) to transparent at its ``y2`` edge.

        Args:
            show: ``False`` goes back to an even fill.
        """
        if show and self._stack:
            raise ValueError("A gradient would blur stacked layers; use stack=False")
        self._gradient_on = show
        return self._changed()

    def split(
        self,
        show: bool = True,
        *,
        colors: tuple[str, str] | None = None,
        labels: tuple[str, str] | None = None,
    ) -> Self:
        """Color the area by sign: where ``y1`` is above ``y2`` and where it is
        below (e.g. a temperature anomaly, or a surplus against a deficit).

        Args:
            show: ``False`` goes back to one color.
            colors: ``(above, below)`` colors (default: the theme's
                ``positive`` and ``negative``).
            labels: ``(above, below)`` names for a legend; none without them.
        """
        if show and (self._grouped or self._stack):
            raise ValueError("split() works on a single area without hue= or stack=")
        for name, pair in (("colors", colors), ("labels", labels)):
            if pair is not None and len(pair) != 2:
                raise ValueError(f"split {name} must be a pair (above, below)")
        self._split = {"colors": colors, "labels": labels} if show else None
        return self._changed()

    # ------------------------------------------------------------------ data
    def _layers(self) -> tuple[np.ndarray, dict[Any, tuple[np.ndarray, np.ndarray]]]:
        """Stacked layers on a shared x grid: ``{group: (lower, upper)}``.
        Incomplete x positions follow the selected missing-data policy."""
        frame = self._data.frame
        groups = self._groups
        if not self._grouped:
            frame = frame.assign(hue=0)
            groups = [0]
        wide = frame.pivot(index="x", columns="hue", values="y1")
        wide = wide.reindex(columns=groups)
        wide = (
            wide.sort_index()
            if self._data.sort
            else wide.reindex(pd.unique(frame["x"]))
        )
        incomplete = wide.isna().any(axis=1)
        if incomplete.any():
            if self._data.missing == "raise":
                raise DataShapeError(
                    "Stacked areas need every group at each x. "
                    "Use missing='drop' to omit incomplete x positions "
                    "or missing='gap' to leave a gap."
                )
            if self._data.missing == "drop":
                wide = wide.loc[~incomplete]
            else:
                wide.loc[incomplete, :] = np.nan
        if wide.empty:
            raise DataShapeError("No complete x positions to stack")
        if self._stack == "percent":
            if (wide < 0).any(axis=None):
                raise DataShapeError("Percent stacks need non-negative values")
            totals = wide.sum(axis=1, min_count=1)
            if (totals == 0).any():
                raise DataShapeError("Percent stacks need a positive total at every x")
            wide = wide.div(totals, axis=0) * 100
        base = float(frame["y2"].iloc[0])
        # Like stacked bars: positive values stack up from the baseline and
        # negative ones down from it, so no layer paints over another.
        top = wide.clip(lower=0).cumsum(axis=1) + base
        bottom = wide.clip(upper=0).cumsum(axis=1) + base
        negative = wide < 0
        upper = top.where(~negative, bottom - wide)
        lower = bottom.where(negative, top - wide)
        crossing = [
            str(g)
            for g, k in zip(self._groups, groups, strict=True)
            if negative[k].any() and (wide[k] > 0).any()
        ]
        if crossing:
            names = (
                ", ".join(map(repr, crossing[:4])) if self._grouped else "the series"
            )
            emit(
                PolicyWarning,
                f"Values change sign along x in {names}. Positive values are stacked "
                "above the baseline and negative values below it (as in stacked "
                "bars), so where a series crosses zero its band jumps from one "
                "stack to the other and the jump is drawn as a sloped edge. "
                "Consider stack=False or a line plot for signed series.",
                stacklevel=6,
            )
        layers = {
            g: (lower[k].to_numpy(dtype=float), upper[k].to_numpy(dtype=float))
            for g, k in zip(self._groups, groups, strict=True)
        }
        return wide.index.to_numpy(), layers

    def source_data(self) -> pd.DataFrame:
        """The plotted numbers, one row per x and group (for a journal's
        source-data file). Generated columns that clash with your column
        names get a ``_computed`` suffix."""
        names = self._data.names
        x_col = (names.get("x") or "x", bool(names.get("x")))
        hue_col = (names.get("hue") or "group", bool(names.get("hue")))
        if self._stack:
            x, layers = self._layers()
            base = float(self._data.frame["y2"].iloc[0])
            grouped = any(group is not None for group in layers)
            parts = []
            for group, (lower, upper) in layers.items():
                # Bands below the baseline are negative contributions.
                value = np.where(lower < base, lower - upper, upper - lower)
                columns: list[Any] = [self._x_values(x), value, lower, upper]
                if grouped:
                    columns.insert(0, np.full(len(x), group, dtype=object))
                parts.append(pd.DataFrame(dict(enumerate(columns))))
            spec: list[tuple[Hashable, bool]] = [
                x_col,
                ("percent" if self._stack == "percent" else "value", False),
                ("lower", False),
                ("upper", False),
            ]
            if grouped:
                spec.insert(0, hue_col)
            table = pd.concat(parts, ignore_index=True)
            return table.set_axis(source_columns(spec), axis=1)
        frame = self._data.frame
        cols: list[tuple[Hashable, bool, Any]] = []
        if "hue" in frame:
            cols.append((*hue_col, frame["hue"].to_numpy()))
        cols.append((*x_col, self._x_values(frame["x"].to_numpy())))
        for key in ("y1", "y2"):
            cols.append(
                (names.get(key) or key, bool(names.get(key)), frame[key].to_numpy())
            )
        return source_frame(cols)

    # --------------------------------------------------------------- drawing
    def _default_labels(self) -> dict[str, str | None]:
        names = self._data.names
        if self._stack == "percent":
            y = "Percent"
        elif self._band:
            y = None  # two columns: neither name describes the axis alone
        else:
            y = names.get("y1")
        return {"x": names.get("x"), "y": y}

    def _which_lines(self) -> Lines:
        if self._lines != "auto":
            return self._lines
        if self._split is not None:
            return "both" if self._band else "top"
        return "none" if self._band else "top"

    def _draw(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        groups = self._groups
        colors = self._group_colors(style, groups, grouped=self._grouped)
        width = (
            float(theme.line_width or 1.5)
            if self._line_width is None
            else checked_size(style, "area line width", self._line_width, "line")
        )
        lines = self._which_lines()
        ends: list[tuple[Any, Any, float, str, float]] = []

        if self._stack:
            x, layers = self._layers()
            base = float(self._data.frame["y2"].iloc[0])
            for group in groups:
                lower, upper = layers[group]
                layer = ax.fill_between(
                    x, lower, upper, color=colors[group], lw=0, zorder=2
                )
                layer.sticky_edges.y.append(base)
                if lines != "none":
                    ax.plot(
                        x,
                        np.where(lower < base, lower, upper),  # edge away from base
                        color=theme.axes_background,
                        lw=width * _SEPARATOR,
                        zorder=2.5,
                    )
                finite = np.flatnonzero(np.isfinite(lower) & np.isfinite(upper))
                if len(finite):
                    i = finite[-1]
                    ends.append(
                        (
                            group,
                            x[i],
                            (lower[i] + upper[i]) / 2,
                            colors[group],
                            upper[i] - lower[i],
                        )
                    )
        elif self._split is not None:
            ends.append(self._draw_split(ax, style, lines, width))
        else:
            alpha = 0.22 if theme.fill_alpha is None else float(theme.fill_alpha)
            for group in groups:
                color = colors[group]
                rows = self._rows(group)
                x = rows["x"].to_numpy()
                y1 = rows["y1"].to_numpy(dtype=float)
                y2 = rows["y2"].to_numpy(dtype=float)
                if self._gradient_on and "y" not in self._log_axes:
                    boosted = min(1.0, alpha * _GRADIENT_BOOST)
                    area = self._gradient(ax, x, y1, y2, color, boosted, zorder=2)
                else:
                    area = ax.fill_between(
                        x,
                        y1,
                        y2,
                        color=color,
                        alpha=combined_alpha(color, alpha),
                        lw=0,
                        zorder=2,
                    )
                if not self._band and len(y2):
                    area.sticky_edges.y.append(float(y2[0]))
                edges = {"top": [y1], "both": [y1, y2], "none": []}[lines]
                for edge in edges:
                    ax.plot(
                        x,
                        edge,
                        color=color,
                        lw=width,
                        zorder=3,
                        solid_capstyle="round",
                        solid_joinstyle="round",
                    )
                finite = np.flatnonzero(np.isfinite(y1) & np.isfinite(y2))
                if len(finite):
                    i = finite[-1]
                    y = (y1[i] + y2[i]) / 2 if self._band else y1[i]
                    ends.append((group, x[i], float(y), color, float(y1[i])))

        self._style_axes(ax, style, x_margin=0.0)
        if self._stack == "percent":
            ax.set_ylim(0, 100)
            ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
        if self._end_labels:
            self._draw_end_labels(ax, style, ends)
        if self._grouped and not self._end_labels:
            self._legend_entries(ax, style, groups, colors, lines, width)

    def _draw_split(
        self, ax: Axes, style: Style, lines: Lines, width: float
    ) -> tuple[Any, Any, float, str, float]:
        """Draw the above/below areas; returns where the end label goes."""
        assert self._split is not None
        theme = style.theme
        frame = self._data.frame
        x = frame["x"].to_numpy()
        y1 = frame["y1"].to_numpy(dtype=float)
        y2 = frame["y2"].to_numpy(dtype=float)
        above, below = self._split["colors"] or (
            theme.positive or "#24a148",
            theme.negative or "#da1e28",
        )
        labels = self._split["labels"] or (None, None)
        for color, where, label in (
            (above, y1 >= y2, labels[0]),
            (below, y1 <= y2, labels[1]),
        ):
            color = self._faded(color)
            area = ax.fill_between(
                x,
                y1,
                y2,
                where=where,
                interpolate=True,
                color=color,
                alpha=combined_alpha(color, _SPLIT_ALPHA),
                lw=0,
                zorder=2,
                label=label,
            )
            if not self._band:
                area.sticky_edges.y.append(float(y2[0]))
        ink = theme.text_color or "#333333"
        edges = {"top": [y1], "both": [y1, y2], "none": []}[lines]
        for i, edge in enumerate(edges):
            ax.plot(
                x,
                edge,
                color=ink if i == 0 else (theme.neutral or "#8d8d8d"),
                lw=min(width, (theme.axis_line_width or 0.8) * 1.25),
                zorder=3,
                solid_joinstyle="round",
            )
        if self._split["labels"]:
            self._draw_legend(ax, style, n=2, title=None)
        finite = np.flatnonzero(np.isfinite(y1) & np.isfinite(y2))
        i = finite[-1] if len(finite) else -1
        return (None, x[i], float(y1[i]), ink, float(y1[i]))

    def _legend_entries(
        self,
        ax: Axes,
        style: Style,
        groups: list[Any],
        colors: dict[Any, str],
        lines: Lines,
        width: float,
    ) -> None:
        alpha = (
            1.0
            if self._stack
            else (
                0.22
                if style.theme.fill_alpha is None
                else float(style.theme.fill_alpha)
            )
        )
        outlined = not self._stack and lines != "none"
        # A stack reads top-down, so its legend lists the top layer first.
        for group in reversed(groups) if self._stack else groups:
            color = colors[group]
            ax.fill_between(
                [],
                [],
                [],
                facecolor=with_alpha(color, alpha),
                edgecolor=color if outlined else "none",
                lw=width * 0.6 if outlined else 0,
                label=str(group),
            )
        self._draw_legend(ax, style, n=len(groups), title=self._data.names.get("hue"))

    def _end_label(self, group: Any, last: float) -> str:
        if self._stack == "percent" and self._end_values is None and group is None:
            return f"{last:.0f}%"
        return super()._end_label(group, last)


def fill_between(
    data: Any = None,
    x: Any = None,
    y1: Any = None,
    y2: Any = 0.0,
    hue: Any = None,
    *,
    stack: Stack = False,
    sort: bool = True,
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
    missing: MissingPolicy = "raise",
) -> FillBetweenPlot:
    """Filled area between ``y1`` and ``y2`` along x: an area chart (``y2``
    is a baseline), a band between two columns, or stacked areas.

    Args:
        data: Long DataFrame or dict of columns (with ``x``/``y1`` names); a
            wide DataFrame (index or ``x`` column → x, one area per numeric
            column); a Series (index → x); or a list/array of y values. Leave
            out to pass ``x=`` and ``y1=`` as sequences.
        x: Column name (or sequence) of numbers, dates or categories.
        y1: Column name (or sequence) of the top (or first) edge.
        y2: The other edge: a number (baseline, default 0), a column name or a
            sequence. With a column, the plot is a band (e.g. a range or an
            interval you computed).
        hue: Column with groups: one area per group.
        stack: Stack the groups' areas on top of each other; ``"percent"``
            scales each x to 100 %.
        sort: Connect points in x order (``False`` keeps the data order).
        order: Explicit order of category x values.
        hue_order: Explicit group order.

        missing: "raise" (default), "drop" affected rows, or "gap" to
            break areas at missing values. For stacks, drop removes incomplete
            x positions from all layers; gap breaks all layers at those positions.

    Each x appears once per area.

    Example:
        >>> sp.fill_between(df, x="year", y1="low", y2="high")  # doctest: +SKIP
    """
    data_ = series(
        data,
        x,
        {"y1": y1, "y2": y2},
        {"hue": hue},
        hue_order=hue_order,
        order=order,
        sort=sort,
        required=("y2",),
        missing=missing,
    )
    return FillBetweenPlot(data_, band=not _is_number(y2), stack=stack)


def area(
    data: Any = None,
    x: Any = None,
    y: Any = None,
    hue: Any = None,
    *,
    baseline: float = 0.0,
    stack: Stack = False,
    sort: bool = True,
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
    missing: MissingPolicy = "raise",
) -> FillBetweenPlot:
    """Area chart: the area between ``y`` and a ``baseline``. Same as
    :func:`fill_between` with ``y1=y, y2=baseline``.

    Example:
        >>> sp.area(df, x="year", y="sales", hue="region", stack=True)  # doctest: +SKIP
    """
    if not _is_number(baseline):
        raise TypeError("baseline must be a number; for a band use sp.fill_between")
    return fill_between(
        data,
        x,
        y,
        baseline,
        hue,
        stack=stack,
        sort=sort,
        order=order,
        hue_order=hue_order,
        missing=missing,
    )
