"""Box plots (box-and-whisker): median, quartiles, whiskers and outliers per
category, with optional groups, notches, points, means and significance
brackets."""

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
from matplotlib.axes import Axes

from SecretPlots.core.data import Tidy
from SecretPlots.core.missing import DropPolicy
from SecretPlots.core.resolve import Style
from SecretPlots.core.stats import Whiskers, check_whiskers
from SecretPlots.plots.distribution import (
    DistributionPlot,
    Orient,
    _Item,
    distributions,
)

#: Box width (fraction of the slot) without groups, as ggplot2's 0.75 x 0.9.
_SINGLE_WIDTH = 0.75


class BoxPlot(DistributionPlot):
    """Created by :func:`box`."""

    kind = "box"

    def __init__(
        self,
        data: Tidy,
        *,
        whis: Whiskers = 1.5,
        notch: bool = False,
        varwidth: bool = False,
        fill: bool = True,
        outliers: bool | None = None,
        caps: bool = False,
        orient: Orient = "v",
        edgecolor: str | None = None,
        linewidth: float | None = None,
    ) -> None:
        check_whiskers(whis)
        super().__init__(data, orient=orient, edgecolor=edgecolor, linewidth=linewidth)
        self._whis_value: Whiskers = tuple(whis) if isinstance(whis, list) else whis
        self._notch = notch
        self._varwidth = varwidth
        self._fill = fill
        self._outliers = outliers
        self._caps = caps

    @property
    def _whis(self) -> Any:
        return self._whis_value

    def _filled(self) -> bool:
        return self._fill

    @property
    def _show_outliers(self) -> bool:
        if self._outliers is not None:
            return self._outliers
        return self._points is None  # the points already show every value

    # ---------------------------------------------------------------- layout
    def _items(self, style: Style) -> list[_Item]:
        items = super()._items(style)
        if not self._dodge():  # a lone box looks best a little narrower
            for item in items:
                item.width *= _SINGLE_WIDTH
        if self._varwidth and items:
            largest = max(len(i.values) for i in items)
            for item in items:
                item.width *= math.sqrt(len(item.values) / largest)
        return items

    def _extent(self, item: _Item) -> tuple[float, float]:
        s = self._stats(item.values)
        if self._show_outliers and len(s.outliers):
            return float(s.outliers.min(initial=s.whisker_low)), float(
                s.outliers.max(initial=s.whisker_high)
            )
        return s.whisker_low, s.whisker_high

    # --------------------------------------------------------------- drawing
    def _draw_marks(self, ax: Axes, style: Style, items: list[_Item]) -> None:
        theme = style.theme
        thin = self._line_width(style, 0.6)
        thick = self._line_width(style, 1.0)
        labelled: set[Any] = set()
        for item in items:
            s = self._stats(item.values)
            line = self._detail_color(item)
            face = item.color if self._fill else theme.axes_background
            c, half = item.center, item.width / 2
            inv = self._inv

            # Box outline, notched around the median if asked.
            if self._notch:
                low = max(s.notch_low, s.q1)
                high = min(s.notch_high, s.q3)
                inset = half / 2
                pos = [
                    c - half, c - half, c - inset, c - half, c - half,
                    c + half, c + half, c + inset, c + half, c + half,
                ]  # fmt: skip
                val = [
                    s.q1, low, s.median, high, s.q3,
                    s.q3, high, s.median, low, s.q1,
                ]  # fmt: skip
                median_span = (c - inset, c + inset)
            else:
                pos = [c - half, c - half, c + half, c + half]
                val = [s.q1, s.q3, s.q3, s.q1]
                median_span = (c - half, c + half)
            label = None
            if self._grouped and item.group not in labelled:
                label = str(item.group)
                labelled.add(item.group)
            ax.fill(
                *self._xy(pos, inv(np.array(val))),
                facecolor=face,
                edgecolor=self._outline_color(item),
                linewidth=self._outline_width(style),
                label=label,
                zorder=2,
            )

            # Whiskers (and caps), then the median on top.
            for end, edge in ((s.whisker_low, s.q1), (s.whisker_high, s.q3)):
                if end == edge:
                    continue
                ax.plot(
                    *self._xy([c, c], inv(np.array([edge, end]))),
                    color=line,
                    lw=thin,
                    solid_capstyle="butt",
                    zorder=2,
                )
                if self._caps:
                    ax.plot(
                        *self._xy([c - half / 2, c + half / 2], [inv(end)] * 2),
                        color=line,
                        lw=thin,
                        solid_capstyle="butt",
                        zorder=2,
                    )
            ax.plot(
                *self._xy(list(median_span), [inv(s.median)] * 2),
                color=line,
                lw=thick,
                solid_capstyle="butt",
                zorder=3,
            )

            if self._show_outliers and len(s.outliers):
                size = float(theme.marker_size or 5.0) * 0.7
                ax.scatter(
                    *self._xy(np.full(len(s.outliers), c), inv(s.outliers)),
                    s=size**2,
                    color=line,
                    linewidths=0,
                    zorder=3,
                )

    # --------------------------------------------------------------- caption
    def _caption_marks(self) -> list[str]:
        whis = self._whis_value
        if whis == "range":
            whiskers = "the minimum and maximum (whiskers)"
        elif isinstance(whis, tuple):
            whiskers = f"the {whis[0]:g}th and {whis[1]:g}th percentiles (whiskers)"
        else:
            whiskers = (
                f"the most extreme values within {whis:g}x the interquartile "
                "range of the box (whiskers)"
            )
        sentence = (
            "Box plots show the median (centre line), the first and third "
            f"quartiles (box limits) and {whiskers}"
        )
        if self._show_outliers and whis != "range":
            sentence += "; values beyond the whiskers are drawn as points"
        sentence += "."
        parts = [sentence]
        if self._notch:
            parts.append(
                "Notches show median +/- 1.58 x IQR / sqrt(n), roughly a 95% "
                "confidence interval for comparing medians."
            )
        if self._varwidth:
            parts.append("Box widths are proportional to the square root of n.")
        if self._log:
            parts.append("Statistics computed on the log scale.")
        return parts


def box(
    data: Any,
    x: str | None = None,
    y: str | None = None,
    hue: str | None = None,
    *,
    whis: Whiskers = 1.5,
    notch: bool = False,
    varwidth: bool = False,
    fill: bool = True,
    outliers: bool | None = None,
    caps: bool = False,
    edgecolor: str | None = None,
    linewidth: float | None = None,
    orient: Orient = "v",
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
    missing: DropPolicy = "raise",
) -> BoxPlot:
    """Box plot (box-and-whisker) of the values in each category.

    Args:
        data: Long DataFrame with ``y=`` (and ``x=``/``hue=``) column names,
            a wide DataFrame (one box per numeric column), a dict
            ``{category: values}`` or ``{category: {group: values}}``, a
            Series or list (one box), a 2-D array (one box per column) or a
            list of value lists.
        x: Column name for categories.
        y: Column name for numeric values.
        hue: Column name for groups.
        whis: Whisker reach: a multiple of the interquartile range (Tukey's
            1.5, the default in R and matplotlib), percentiles like
            ``(5, 95)``, or ``"range"`` (minimum to maximum, no outliers).
        notch: Notches around the median (R's ``notch=TRUE``); boxes whose
            notches don't overlap have medians that differ, roughly at the
            5 % level.
        varwidth: Box widths proportional to the square root of n.
        fill: Filled boxes (default) or outlines in the group color.
        outliers: Draw values beyond the whiskers. Default: yes, unless
            ``.points()`` already shows every value.
        caps: Short lines at the whisker ends.
        edgecolor: Color of the box outlines, whiskers and medians (default:
            a dark shade of the fill). ``"none"`` removes only the outline.
        linewidth: Width of the box outlines in pt; 0 removes them.
        orient: ``"v"`` (values up) or ``"h"`` (values to the right).
        order: Explicit category order.
        hue_order: Explicit group order.
        missing: "raise" (default) rejects missing/non-finite data; "drop"
            ignores affected observations.

    Missing values raise an error unless missing="drop" is selected.

    Example:
        >>> sp.box(df, x="dose", y="weight").points().compare(ref="0")  # doctest: +SKIP
    """
    return BoxPlot(
        distributions(
            data, x, y, hue, order=order, hue_order=hue_order, missing=missing
        ),
        whis=whis,
        notch=notch,
        varwidth=varwidth,
        fill=fill,
        outliers=outliers,
        caps=caps,
        orient=orient,
        edgecolor=edgecolor,
        linewidth=linewidth,
    )


boxplot = box
