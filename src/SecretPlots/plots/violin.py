"""Violin plots: a mirrored density curve per category, with a small box inside;
split and half violins, and raincloud plots (half violin + box + dots)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from matplotlib.axes import Axes

from SecretPlots.core.data import Tidy
from SecretPlots.core.missing import DropPolicy
from SecretPlots.core.resolve import Style
from SecretPlots.core.stats import bandwidth, gaussian_kde
from SecretPlots.errors import DataShapeError
from SecretPlots.plots.distribution import (
    DistributionPlot,
    Orient,
    _choice,
    _Item,
    distributions,
)

Scale = Literal["area", "count", "width"]
Inner = Literal["box", "quartiles", "median"]
Side = Literal["both", "left", "right"]

_SCALES = ("area", "count", "width")
_INNERS = ("box", "quartiles", "median")
_SIDES = ("both", "left", "right")
_CURVE_POINTS = 200
#: Inner box width as a fraction of the violin width.
_INNER_WIDTH = 0.1
#: Raincloud layout as fractions of the slot width: where the cloud starts
#: (from the category center, toward the cloud), how far it reaches, and the
#: strip of rain (dots) on the other side.
_CLOUD_BASE = 0.0
_CLOUD_REACH = 0.55
_RAIN_CENTER = 0.3
_RAIN_HALF = 0.12


@dataclass
class _Curve:
    grid: np.ndarray  # drawing scale
    density: np.ndarray


class ViolinPlot(DistributionPlot):
    """Created by :func:`violin` and :func:`raincloud`."""

    kind = "violin"
    #: Density estimates from fewer values mostly show the kernel's shape.
    small_sample = 10

    def __init__(
        self,
        data: Tidy,
        *,
        bw_adjust: float = 1.0,
        cut: float = 0.0,
        scale: Scale = "area",
        inner: Inner | None = "box",
        split: bool = False,
        side: Side = "both",
        fill: bool = True,
        orient: Orient = "v",
        rain: bool = False,
        edgecolor: str | None = None,
        linewidth: float | None = None,
    ) -> None:
        if bw_adjust <= 0:
            raise ValueError("bw_adjust must be positive")
        if cut < 0:
            raise ValueError("cut must be 0 or more")
        _choice(scale, _SCALES, "scale")
        if inner is not None:
            _choice(inner, _INNERS, "inner")
        _choice(side, _SIDES, "side")
        if split and (data.hue_order is None or len(data.hue_order) != 2):
            raise DataShapeError("split=True needs hue= with exactly 2 groups")
        if split and side != "both":
            raise ValueError("split=True already draws half violins; leave side out")
        super().__init__(data, orient=orient, edgecolor=edgecolor, linewidth=linewidth)
        self._bw_adjust = bw_adjust
        self._cut = cut
        self._scale: str = scale
        self._inner: str | None = inner
        self._split = split
        self._side: str = side
        self._fill = fill
        self._rain = rain

    def _filled(self) -> bool:
        return self._fill

    # ------------------------------------------------------------------ data
    def _curve(self, item: _Item) -> _Curve | None:
        """Density on the drawing scale; ``None`` for fewer than 2 distinct
        values (drawn as a line)."""
        t = item.t
        if len(t) < 2 or np.ptp(t) == 0:
            return None
        bw = bandwidth(t, self._bw_adjust)
        pad = self._cut * bw
        grid = np.linspace(t.min() - pad, t.max() + pad, _CURVE_POINTS)
        return _Curve(grid, gaussian_kde(t, grid, bw))

    def _dodge(self) -> bool:
        return self._grouped and not self._split

    def _anchor(self, item: _Item) -> float:
        # Split halves share a center; meet each in the middle of its half.
        if self._split:
            return item.center + item.side * item.width / 4
        return item.center

    def _items(self, style: Style) -> list[_Item]:
        items = super()._items(style)
        groups = self._groups
        for item in items:
            if self._split:
                item.side = self._visual(-1 if groups.index(item.group) == 0 else 1)
            elif self._rain or self._side == "right":
                item.side = self._visual(1)
            elif self._side == "left":
                item.side = self._visual(-1)
        return items

    def _base(self, item: _Item) -> float:
        """Where the violin's flat side (or center line) is."""
        if self._rain:
            return item.center - item.side * item.width * _CLOUD_BASE
        return item.center

    def _reach(self, item: _Item) -> float:
        """Largest distance from the base for the widest violin."""
        if self._rain:
            return item.width * _CLOUD_REACH
        return item.width / 2

    def _point_geometry(self, item: _Item) -> tuple[float, float]:
        if self._rain:
            return item.center - item.side * item.width * _RAIN_CENTER, (
                item.width * _RAIN_HALF
            )
        if item.side:
            return item.center + item.side * item.width * 0.2, item.width * 0.12
        return item.center, item.width * 0.3

    def _extent(self, item: _Item) -> tuple[float, float]:
        curve = self._curve(item)
        if curve is None:
            return float(item.t.min()), float(item.t.max())
        return float(curve.grid[0]), float(curve.grid[-1])

    # --------------------------------------------------------------- drawing
    def _draw_marks(self, ax: Axes, style: Style, items: list[_Item]) -> None:
        theme = style.theme
        curves = [self._curve(item) for item in items]
        peaks = [
            float(c.density.max()) * (len(i.values) if self._scale == "count" else 1)
            for i, c in zip(items, curves, strict=True)
            if c is not None
        ]
        largest = max(peaks, default=1.0)
        thin = self._line_width(style, 0.6)
        labelled: set[Any] = set()
        for item, curve in zip(items, curves, strict=True):
            line = self._detail_color(item)
            outline = self._outline_color(item)
            face = item.color if self._fill else theme.axes_background
            base, reach = self._base(item), self._reach(item)
            label = None
            if self._grouped and item.group not in labelled:
                label = str(item.group)
                labelled.add(item.group)
            if curve is None:  # one value (or all equal): a flat line
                value = float(self._inv(item.t[0]))
                low = base - reach if item.side <= 0 else base
                high = base + reach if item.side >= 0 else base
                ax.plot(
                    *self._xy([low, high], [value, value]),
                    color=line,
                    lw=max(self._outline_width(style), thin),
                    label=label,
                    zorder=2,
                )
                continue
            if self._scale == "width":
                factor = 1 / float(curve.density.max())
            elif self._scale == "count":
                factor = len(item.values) / largest
            else:
                factor = 1 / largest
            half = curve.density * factor * reach
            values = self._inv(curve.grid)
            if item.side == 0:
                pos = np.r_[base - half, (base + half)[::-1]]
                val = np.r_[values, values[::-1]]
            else:
                pos = np.r_[np.full(len(half), base), (base + item.side * half)[::-1]]
                val = np.r_[values, values[::-1]]
            ax.fill(
                *self._xy(pos, val),
                facecolor=face,
                edgecolor=outline,
                linewidth=self._outline_width(style),
                label=label,
                zorder=2,
            )
            self._draw_inner(ax, style, item, curve, half, line)

    def _draw_inner(
        self,
        ax: Axes,
        style: Style,
        item: _Item,
        curve: _Curve,
        half: np.ndarray,
        line: str,
    ) -> None:
        if self._inner is None:
            return
        theme = style.theme
        s = self._stats(item.values)
        base = self._base(item)
        inv = self._inv
        thin = self._line_width(style, 0.6)
        if self._inner == "box":
            width = item.width * _INNER_WIDTH
            # Inside a split or half violin the box sits in that half.
            center = (
                base + item.side * width * 0.75
                if item.side and not self._rain
                else base
            )
            dark = theme.text_color or "#333333"
            ax.plot(
                *self._xy(
                    [center, center], inv(np.array([s.whisker_low, s.whisker_high]))
                ),
                color=dark,
                lw=thin,
                solid_capstyle="butt",
                zorder=3,
            )
            ax.fill(
                *self._xy(
                    [
                        center - width / 2,
                        center - width / 2,
                        center + width / 2,
                        center + width / 2,
                    ],
                    inv(np.array([s.q1, s.q3, s.q3, s.q1])),
                ),
                facecolor=dark,
                edgecolor="none",
                zorder=3,
            )
            ax.plot(
                *self._xy(
                    [center - width / 2, center + width / 2], [inv(s.median)] * 2
                ),
                color=theme.axes_background,
                lw=self._line_width(style, 0.8),
                solid_capstyle="butt",
                zorder=4,
            )
            return
        marks: list[tuple[float, Any]] = [(s.median, "-")]
        if self._inner == "quartiles":
            marks = [(s.q1, (0, (3, 2))), (s.median, "-"), (s.q3, (0, (3, 2)))]
        for value, dash in marks:
            reach = float(np.interp(value, curve.grid, half))
            low = base - reach if item.side <= 0 else base
            high = base + reach if item.side >= 0 else base
            ax.plot(
                *self._xy([low, high], [inv(value)] * 2),
                color=line,
                lw=thin,
                ls=dash,
                solid_capstyle="butt",
                zorder=3,
            )

    # --------------------------------------------------------------- caption
    def _caption_marks(self) -> list[str]:
        shape = "Half violins (the raincloud's clouds)" if self._rain else "Violins"
        extent = (
            "trimmed to the range of the data"
            if self._cut == 0
            else f"extended {self._cut:g} bandwidths past the data"
        )
        bw = "Scott's rule" + (
            "" if self._bw_adjust == 1 else f" x {self._bw_adjust:g}"
        )
        scaled = {
            "area": "with equal areas",
            "count": "with areas proportional to n",
            "width": "with equal widths",
        }[self._scale]
        parts = [
            f"{shape} show kernel density estimates (Gaussian kernel, "
            f"bandwidth by {bw}), {extent} and drawn {scaled}."
        ]
        if self._inner == "box" and self._rain:
            parts.append(
                "Along the flat side of each cloud, a narrow box spans the first "
                "to third quartiles, a white line marks the median and a thin "
                "line reaches the most extreme values within 1.5x the "
                "interquartile range."
            )
        elif self._inner == "box":
            parts.append(
                "Inside, the white line marks the median, the box the first and "
                "third quartiles and the thin line the most extreme values "
                "within 1.5x the interquartile range."
            )
        elif self._inner == "quartiles":
            parts.append(
                "Solid lines mark the median, dashed lines the first and "
                "third quartiles."
            )
        elif self._inner == "median":
            parts.append("Lines mark the median.")
        if self._log:
            parts.append("Densities computed on the log scale.")
        return parts


class RaincloudPlot(ViolinPlot):
    """Created by :func:`raincloud`."""

    kind = "raincloud"


def violin(
    data: Any,
    x: str | None = None,
    y: str | None = None,
    hue: str | None = None,
    *,
    bw_adjust: float = 1.0,
    cut: float = 0.0,
    scale: Scale = "area",
    inner: Inner | None = "box",
    split: bool = False,
    side: Side = "both",
    fill: bool = True,
    edgecolor: str | None = None,
    linewidth: float | None = None,
    orient: Orient = "v",
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
    missing: DropPolicy = "raise",
) -> ViolinPlot:
    """Violin plot: the distribution of the values in each category as a
    mirrored density curve, with a small box plot inside.

    Args:
        data: Same inputs as :func:`box`: a long DataFrame with ``y=`` (and
            ``x=``/``hue=``), a wide DataFrame, a dict, a Series, list or
            array.
        x: Column name for categories.
        y: Column name for numeric values.
        hue: Column name for groups.
        bw_adjust: Multiplies the automatic bandwidth (Scott's rule on a
            robust spread). Smaller follows the data more closely.
        cut: How far past the smallest and largest value to draw, in
            bandwidths. The default 0 trims at the data (ggplot2's
            ``trim=TRUE``), so violins never suggest impossible values.
        scale: ``"area"`` (all violins have the same area; default),
            ``"count"`` (area proportional to n) or ``"width"`` (same
            maximum width).
        inner: What to draw inside: ``"box"`` (median, quartiles, whiskers),
            ``"quartiles"`` (lines), ``"median"`` or ``None``.
        split: With two ``hue`` groups, draw one half violin per group.
        side: ``"left"`` or ``"right"`` for half violins (for horizontal
            violins, ``"right"`` is the upper side).
        fill: Filled violins (default) or outlines in the group color.
        edgecolor: Color of the violin outlines and the median / quartile
            lines (default: a dark shade of the fill). ``"none"`` removes
            only the outline.
        linewidth: Width of the violin outlines in pt; 0 removes them.
        orient: ``"v"`` (values up) or ``"h"`` (values to the right).
        order: Explicit category order.
        hue_order: Explicit group order.
        missing: "raise" (default) rejects missing/non-finite data; "drop"
            ignores affected observations.

    Example:
        >>> sp.violin(df, x="dose", y="weight").points()  # doctest: +SKIP
    """
    return ViolinPlot(
        distributions(
            data, x, y, hue, order=order, hue_order=hue_order, missing=missing
        ),
        bw_adjust=bw_adjust,
        cut=cut,
        scale=scale,
        inner=inner,
        split=split,
        side=side,
        fill=fill,
        orient=orient,
        edgecolor=edgecolor,
        linewidth=linewidth,
    )


def raincloud(
    data: Any,
    x: str | None = None,
    y: str | None = None,
    hue: str | None = None,
    *,
    bw_adjust: float = 1.0,
    cut: float = 0.0,
    scale: Scale = "area",
    edgecolor: str | None = None,
    linewidth: float | None = None,
    orient: Orient = "h",
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
    missing: DropPolicy = "raise",
) -> RaincloudPlot:
    """Raincloud plot (Allen et al., Wellcome Open Res 4:63, 2019): a half
    violin (the cloud), a small box plot and every value as a dot (the rain).

    Takes the same arguments as :func:`violin` (``edgecolor`` and
    ``linewidth`` set the cloud's outline); horizontal by default. Change
    the dots with ``.points(kind=...)`` or remove them with
    ``.points(False)``.

    Example:
        >>> sp.raincloud(df, x="group", y="reaction_time")  # doctest: +SKIP
    """
    return RaincloudPlot(
        distributions(
            data, x, y, hue, order=order, hue_order=hue_order, missing=missing
        ),
        bw_adjust=bw_adjust,
        cut=cut,
        scale=scale,
        inner="box",
        orient=orient,
        rain=True,
        edgecolor=edgecolor,
        linewidth=linewidth,
    ).points(kind="jitter")
