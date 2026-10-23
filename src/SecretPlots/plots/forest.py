"""Forest plots: an estimate and its confidence interval per row, beside the
table of numbers behind it, as in subgroup analyses, meta-analyses and
regression models.

The layout follows clinical journals: a label column and optional data
columns on the left, the intervals in the middle against a line of no effect,
and "estimate (95% CI)" text on the right. Rows share the axes' data
coordinates, so text and marks always line up. Table columns sit a fixed
physical distance (inches) from the axes, so constrained layout makes room for
them and they keep their spacing when the figure is resized.

``panel=`` splits the intervals into side-by-side forests (e.g. efficacy and
safety) that share the row labels; each panel has its own estimate column.
"""

import difflib
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import pairwise
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.patches import Polygon, Rectangle
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator, NullLocator
from matplotlib.transforms import (
    Bbox,
    BboxTransformTo,
    IdentityTransform,
    ScaledTranslation,
    Transform,
    TransformedBbox,
    blended_transform_factory,
)

from SecretPlots.core.colors import with_alpha
from SecretPlots.core.data import _order
from SecretPlots.core.missing import DropPolicy, handle_missing, numeric_array
from SecretPlots.core.plot import Plot, _legend_title, _renderer, _root_figure
from SecretPlots.core.resolve import Style, checked_size
from SecretPlots.errors import DataShapeError, PolicyWarning, emit

Scale = Literal["ratio", "difference"]
Side = Literal["left", "right"]
Align = Literal["left", "center", "right"]
#: A table format: a format spec (``".1f"``), a template (``"{:.1f}%"``),
#: ``"p"`` for p-values, or a function of the value.
CellFormat = str | Callable[[Any], str]
ColumnSource = str | Mapping[Any, Any]
Columns = Sequence[str] | Mapping[str, ColumnSource]

_PT = 72.0
_MINUS = "\N{MINUS SIGN}"
_DASH = "\N{EN DASH}"
#: Tick families for ratio axes, tried in order: the first that gives a
#: readable number of ticks across the data wins.
#: Tick families for ratio axes ``(mantissas, base, short labels only)``,
#: tried in order.
_RATIO_FAMILIES: tuple[tuple[tuple[float, ...], float, bool], ...] = (
    ((1.0,), 2.0, True),
    ((1.0, 2.0, 5.0), 10.0, False),
    ((1.0,), 10.0, False),
)
_MIN_PANEL_IN = 0.5


# ------------------------------------------------------------ formatting
def _number(value: float, decimals: int) -> str:
    return f"{value:,.{decimals}f}".replace("-", _MINUS)


def _auto_number(value: float) -> str:
    """Up to three significant digits, without scientific notation or
    trailing zeros (0.76, 12.5, 1,234)."""
    if value == 0 or not math.isfinite(value):
        return f"{value:g}"
    if float(value).is_integer() and abs(value) < 1e15:
        return _number(value, 0)
    digits = max(0, 2 - math.floor(math.log10(abs(value))))
    text = _number(value, digits)
    return text.rstrip("0").rstrip(".") if "." in text else text


def _p_value(value: float) -> str:
    if value < 0.001:
        return "<0.001"
    return f"{value:.3f}" if value < 0.01 else f"{value:.2f}"


def _format_cell(value: Any, fmt: CellFormat | None) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    if callable(fmt):
        return str(fmt(value))
    if isinstance(value, str):
        return value
    if fmt == "p":
        return _p_value(float(value))
    if fmt is not None:
        text = fmt.format(value) if "{" in fmt else format(value, fmt)
        return text.replace("-", _MINUS) if isinstance(value, int | float) else text
    if isinstance(value, bool | np.bool_):
        return str(value)
    if isinstance(value, int | np.integer):
        return _number(float(value), 0)
    if isinstance(value, float | np.floating):
        return _auto_number(float(value))
    return str(value)


def _check_format(fmt: CellFormat, header: str) -> None:
    if callable(fmt) or fmt == "p":
        return
    if not isinstance(fmt, str):
        raise TypeError(f"format for {header!r} must be text or a function")
    try:
        fmt.format(1.5) if "{" in fmt else format(1.5, fmt)
    except (ValueError, IndexError, KeyError):
        raise ValueError(
            f"format {fmt!r} for {header!r} is not a format spec like '.2f', "
            "a template like '{:.1f}%', or 'p'"
        ) from None


def _measure_name(column: str) -> str:
    """``"hr"`` -> ``"HR"``: short lowercase names are abbreviations."""
    if column == column.lower() and len(column) <= 4 and column.isalpha():
        return column.upper()
    return _legend_title(column) or column


def _tick_text(value: float, pos: float | None = None) -> str:
    return f"{value:g}".replace("-", _MINUS)


def _text_size(
    fig: Figure, text: str, size: float, bold: bool = False
) -> tuple[float, float]:
    """Width and height of ``text`` in inches, in the current rc fonts."""
    if not text:
        return 0.0, 0.0
    t = Text(0, 0, text, fontsize=size, fontweight="bold" if bold else "normal")
    t.set_figure(fig)
    box = t.get_window_extent(_renderer(fig))
    return box.width / fig.dpi, box.height / fig.dpi


# ----------------------------------------------------------------- ticks
def _ratio_ticks(low: float, high: float) -> list[float]:
    """Ticks that bracket ``[low, high]``: doublings (0.25, 0.5, 1, 2, 4) when
    their labels stay short, else 1-2-5 steps, else decades."""
    for mantissas, base, short_only in _RATIO_FAMILIES:
        start = math.floor(math.log(low, base)) - 1
        stop = math.ceil(math.log(high, base)) + 1
        values = sorted(
            {m * base**k for k in range(start, stop + 1) for m in mantissas}
        )
        first = max(v for v in values if v <= low * (1 + 1e-9))
        last = min(v for v in values if v >= high * (1 - 1e-9))
        ticks = [v for v in values if first <= v <= last]
        if short_only and (first < 0.25 or last > 8):
            continue
        if len(ticks) <= 7 or (len(mantissas) == 1 and base == 10.0):
            return ticks
    raise AssertionError(
        "decades always fit"
    )  # pragma: no cover  # pragma: no cover  (decades always succeed)


def _difference_ticks(low: float, high: float) -> list[float]:
    ticks = MaxNLocator(nbins=5, steps=[1, 2, 2.5, 5, 10]).tick_values(low, high)
    ticks = [float(t) for t in ticks]
    while len(ticks) > 2 and ticks[1] <= low:
        ticks = ticks[1:]
    while len(ticks) > 2 and ticks[-2] >= high:
        ticks = ticks[:-1]
    return [0.0 if abs(t) < 1e-12 else t for t in ticks]


# ------------------------------------------------------------- geometry
class _PanelLocator:
    """Axes locator: panel ``index`` of ``count`` side-by-side panels sharing
    the parent's laid-out box, ``gap`` inches apart."""

    def __init__(self, parent: Axes, index: int, count: int, gap: float) -> None:
        self.parent, self.index, self.count, self.gap = parent, index, count, gap

    def __call__(self, ax: Any, renderer: RendererBase | None) -> Bbox:
        fig = _root_figure(self.parent)
        box = self.parent.get_position(original=True)
        gap = self.gap / fig.get_size_inches()[0]
        width = max((box.width - gap * (self.count - 1)) / self.count, 1e-4)
        x0 = box.x0 + self.index * (width + gap)
        return Bbox.from_bounds(x0, box.y0, width, box.height)


class _Span(Rectangle):
    """A rectangle across the whole table: from ``left`` inches before the
    plot region to ``right`` inches after it, resolved at draw time so it
    follows the layout. ``y`` is in ``y_transform`` units; ``height_pt`` gives
    a rule of fixed thickness instead of a ``(y0, y1)`` band."""

    def __init__(
        self,
        frame: Transform,
        fig: Figure,
        left: float,
        right: float,
        y: tuple[float, float],
        y_transform: Transform,
        *,
        height_pt: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__((0, 0), 0, 0, transform=IdentityTransform(), **kwargs)
        self._frame, self._fig = frame, fig
        self._left, self._right = left, right
        self._y, self._y_transform, self._height_pt = y, y_transform, height_pt
        self.set_clip_on(False)
        self.set_in_layout(False)

    def draw(self, renderer: RendererBase) -> None:
        dpi = self._fig.dpi
        x0 = self._frame.transform((0, 0))[0] - self._left * dpi
        x1 = self._frame.transform((1, 0))[0] + self._right * dpi
        ya = self._y_transform.transform((0, self._y[0]))[1]
        if self._height_pt is None:
            yb = self._y_transform.transform((0, self._y[1]))[1]
        else:
            yb = ya + self._height_pt * dpi / _PT
        self.set_bounds(x0, min(ya, yb), x1 - x0, abs(yb - ya))
        super().draw(renderer)


class _Rule(Line2D):
    """A horizontal line across the whole table, like :class:`_Span` but a
    line, so it can be dashed."""

    def __init__(
        self,
        frame: Transform,
        fig: Figure,
        left: float,
        right: float,
        y: float,
        y_transform: Transform,
        **kwargs: Any,
    ) -> None:
        super().__init__([0, 0], [0, 0], transform=IdentityTransform(), **kwargs)
        # Line2D keeps its data in ``_x``/``_y``: avoid those names.
        self._frame, self._fig = frame, fig
        self._left, self._right = left, right
        self._rule_y, self._rule_transform = y, y_transform
        self.set_clip_on(False)
        self.set_in_layout(False)

    def draw(self, renderer: RendererBase) -> None:
        dpi = self._fig.dpi
        x0 = self._frame.transform((0, 0))[0] - self._left * dpi
        x1 = self._frame.transform((1, 0))[0] + self._right * dpi
        y = self._rule_transform.transform((0, self._rule_y))[1]
        self.set_data([x0, x1], [y, y])
        super().draw(renderer)


@dataclass
class _Row:
    kind: Literal["header", "item", "summary"]
    group: Any
    label: str
    y: float


def _bands(rows: list[_Row], by: Literal["row", "group"]) -> list[tuple[float, float]]:
    """``(top, bottom)`` y of each row, or each ``group=`` section (a header
    and its rows; an ungrouped row on its own), meeting halfway across the
    gaps between them so they tile the table."""
    blocks: list[list[_Row]] = []
    for row in rows:
        if (
            by == "group"
            and blocks
            and row.group is not None
            and row.group == blocks[-1][-1].group
        ):
            blocks[-1].append(row)
        else:
            blocks.append([row])
    edges = [blocks[0][0].y - 0.5]
    for above, below in pairwise(blocks):
        edges.append((above[-1].y + below[0].y) / 2)
    edges.append(blocks[-1][-1].y + 0.5)
    return list(pairwise(edges))


@dataclass(frozen=True)
class _Column:
    header: str
    source: ColumnSource | None  # None: the estimate text
    fmt: CellFormat | None = None
    align: Align = "center"


@dataclass
class _Placed:
    """A table column ready to draw: ``x`` is the anchor in inches from the
    plot region's left (negative) or a panel's right edge."""

    column: _Column
    cells: dict[int, list[tuple[str, float, str | None]]]
    width: float
    x: float = 0.0
    bold_rows: frozenset[int] = frozenset()


@dataclass
class _Body:
    """Per-render layout (reset by :meth:`Plot.copy`)."""

    panels: list[Axes] = field(default_factory=list)
    frame: Transform | None = None
    left: float = 0.0
    right: float = 0.0
    header: float = 0.0


class ForestPlot(Plot):
    """Forest plot; create with :func:`forest`."""

    kind = "forest"
    _refline_zorder = 1.2
    _reflines_in_draw = True

    def __init__(
        self,
        frame: pd.DataFrame,
        *,
        names: dict[str, str | None],
        scale: Scale,
        log: bool,
        hues: list[Any],
        panels: list[Any],
    ) -> None:
        super().__init__()
        self._frame = frame
        self._names = names
        self._scale: Scale = scale
        self._log = log
        self._xticks: list[float] | None = None
        self._null: float | None = None
        self._null_options: dict[str, Any] = {}
        self._hues = hues
        self._panel_names = panels
        self._summary: tuple[Any, ...] = ()
        self._left: list[_Column] = []
        self._right: list[_Column] = []
        self._estimates: bool = True
        self._estimate_side: Side = "right"
        self._estimate_header: str | None = None
        self._decimals = 2
        self._favours: tuple[str | None, str | None] = (None, None)
        self._stripes: dict[str, Any] | None = None
        self._dividers: dict[str, Any] | None = None
        self._group_gap = 0.5
        self._group_headers = True
        self._indent: float | None = None
        self._marker = "s"
        self._marker_size: float | None = None
        self._marker_min: float | None = None
        self._body = _Body()
        keys = zip(frame["_g"], frame["_l"], frame["_p"], frame["_h"], strict=True)
        self._records = {key: i for i, key in enumerate(keys)}

    # ----------------------------------------------------------------- verbs
    def table(
        self,
        left: Columns | None = None,
        right: Columns | None = None,
        *,
        formats: Mapping[str, CellFormat] | None = None,
        align: Mapping[str, Align] | None = None,
    ) -> Self:
        """Extra table columns beside the forest, e.g. patient numbers on the
        left and p-values on the right. Each call replaces the columns;
        ``.table()`` removes them.

        Args:
            left: Columns before the forest: a list of column names, or
                ``{header: column}``. A ``{group: value}`` mapping instead of
                a column name fills the group header rows (e.g. P for
                interaction); its keys may also be row labels.
            right: Columns after the estimates, repeated for every panel.
            formats: ``{header: format}``: a format spec like ``".1f"`` or
                ``",d"``, a template like ``"{:.1f}%"``, ``"p"`` for p-values
                (``<0.001``, ``0.004``, ``0.42``) or a function.
            align: ``{header: "left" | "center" | "right"}``; default center.
        """
        formats = dict(formats or {})
        align = dict(align or {})
        columns = {
            side: self._columns(spec, side, formats, align)
            for side, spec in (("left", left), ("right", right))
        }
        named = {c.header for side in columns.values() for c in side}
        unknown = (set(formats) | set(align)) - named
        if unknown:
            raise ValueError(
                f"formats/align name {sorted(unknown)}, which are not table "
                f"columns. Columns: {', '.join(sorted(named)) or 'none'}"
            )
        self._left, self._right = columns["left"], columns["right"]
        return self._changed()

    def estimates(
        self,
        show: bool = True,
        *,
        decimals: int = 2,
        header: str | None = None,
        side: Side = "right",
    ) -> Self:
        """The "estimate (lower to upper)" text column, shown by default.

        Args:
            show: ``False`` hides the column (labels and forest only).
            decimals: Digits after the decimal point; default 2.
            header: Column header; default e.g. "HR (95% CI)" from the
                estimate column name.
            side: ``"right"`` of each panel (default) or ``"left"``, beside
                the labels.
        """
        if side not in ("left", "right"):
            raise ValueError("estimates side must be 'left' or 'right'")
        if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
            raise ValueError("decimals must be a non-negative integer")
        if side == "left" and len(self._panel_names) > 1:
            raise ValueError(
                "With panels each panel has its own estimates; use side='right'"
            )
        self._estimates = bool(show)
        self._decimals = decimals
        self._estimate_header = header
        self._estimate_side = side
        return self._changed()

    def summary(self, *labels: Any) -> Self:
        """Draw rows as summary diamonds with bold labels, e.g. ``"Overall"``
        or a meta-analysis's pooled estimate. ``.summary()`` clears them.

        Args:
            *labels: Row labels to draw as summaries.
        """
        known = list(dict.fromkeys(self._frame["_l"]))
        unknown = [label for label in labels if label not in known]
        if unknown:
            close = difflib.get_close_matches(str(unknown[0]), map(str, known), n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise DataShapeError(f"No row labelled {unknown[0]!r}.{hint}")
        self._summary = labels
        return self._changed()

    def favours(self, left: str | None = None, right: str | None = None) -> Self:
        """Direction labels under the axis, either side of the line of no
        effect: ``.favours("Favours drug", "Favours placebo")``.

        Args:
            left: Text left of the null line, with an arrow pointing left.
            right: Text right of the null line, with an arrow pointing right.
        """
        if self._null is None and (left or right):
            raise ValueError(
                "favours() needs the line of no effect; turn it on with .null()"
            )
        self._favours = (left or None, right or None)
        return self._changed()

    def null(
        self,
        value: float | bool = True,
        *,
        label: str | None = None,
        color: str | None = None,
        linestyle: str = "-",
        linewidth: float | None = None,
    ) -> Self:
        """The line of no effect (the baseline): where it sits and how it
        looks. Each call resets the options it doesn't pass.

        Args:
            value: Position, e.g. ``0.8`` for a non-inferiority margin.
                ``True`` (default) uses 1 on a ratio scale and 0 on a
                difference scale; ``False`` hides the line.
            label: Text above the line, e.g. ``"No effect"``; ``""`` or
                ``None`` writes nothing.
            color: Line color (default: the theme's text color).
            linestyle: ``"-"`` (default), ``"--"``, ``":"`` or ``"-."``.
            linewidth: Line width in pt (default: the theme's
                ``axis_line_width``).
        """
        if value is False:
            if any(self._favours):
                raise ValueError(
                    "favours() labels point away from the null line; remove "
                    "them with .favours() before hiding it"
                )
            position = None
        elif value is True:
            position = 1.0 if self._scale == "ratio" else 0.0
        elif isinstance(value, int | float) and math.isfinite(value):
            position = float(value)
            if self._scale == "ratio" and position <= 0:
                raise ValueError("null must be positive on a ratio scale")
        else:
            raise TypeError("null value must be a number, True or False")
        if color is not None:
            try:
                to_rgba(color)
            except ValueError:
                raise ValueError(f"Unknown null line color {color!r}") from None
        try:
            Line2D([], [], linestyle=linestyle)  # type: ignore[arg-type]
        except ValueError:
            raise ValueError(
                f"Unknown linestyle {linestyle!r}; use '-', '--', ':' or '-.'"
            ) from None
        if linewidth is not None and linewidth < 0:
            raise ValueError("null linewidth must be 0 or more")
        self._null = position
        self._null_options = {
            "label": label or None,
            "color": color,
            "linestyle": linestyle,
            "linewidth": linewidth,
        }
        return self._changed()

    def stripes(
        self,
        show: bool = True,
        *,
        by: Literal["row", "group"] = "row",
        color: str | None = None,
    ) -> Self:
        """Shade every other row, or every other ``group=`` section, across
        the table and forest, which helps follow a row in wide tables.

        Args:
            show: ``False`` removes the shading.
            by: ``"row"`` (default) bands each row (with ``hue=``, all of a
                label's estimates together); ``"group"`` bands each section,
                header included. Without ``group=`` both band rows.
            color: Band color (default: a light tint of the text color).
        """
        if by not in ("row", "group"):
            raise ValueError("stripes by must be 'row' or 'group'")
        if color is not None:
            try:
                to_rgba(color)
            except ValueError:
                raise ValueError(f"Unknown stripes color {color!r}") from None
        self._stripes = {"by": by, "color": color} if show else None
        return self._changed()

    def dividers(
        self,
        show: bool = True,
        *,
        by: Literal["row", "group"] = "group",
        color: str | None = None,
        linewidth: float | None = None,
        linestyle: str = "-",
    ) -> Self:
        """Rules across the table and forest between ``group=`` sections, or
        between rows.

        Args:
            show: ``False`` removes them.
            by: ``"group"`` (default) rules between sections; ``"row"``
                between every row. Without ``group=`` both rule rows.
            color: Rule color (default: the theme's ``grid_color``).
            linewidth: Rule width in pt (default: the theme's
                ``axis_line_width``).
            linestyle: ``"-"`` (default), ``"--"``, ``":"`` or ``"-."``.
        """
        if by not in ("row", "group"):
            raise ValueError("dividers by must be 'row' or 'group'")
        if color is not None:
            try:
                to_rgba(color)
            except ValueError:
                raise ValueError(f"Unknown dividers color {color!r}") from None
        if linewidth is not None and linewidth < 0:
            raise ValueError("dividers linewidth must be 0 or more")
        try:
            Line2D([], [], linestyle=linestyle)  # type: ignore[arg-type]
        except ValueError:
            raise ValueError(
                f"Unknown linestyle {linestyle!r}; use '-', '--', ':' or '-.'"
            ) from None
        self._dividers = (
            {"by": by, "color": color, "linewidth": linewidth, "linestyle": linestyle}
            if show
            else None
        )
        return self._changed()

    def groups(
        self,
        *,
        gap: float = 0.5,
        headers: bool = True,
        indent: float | None = None,
    ) -> Self:
        """How ``group=`` sections are separated.

        Args:
            gap: Space between sections, in rows; default 0.5.
            headers: A bold header row naming each section (default). With
                ``False`` sections are only split by the gap.
            indent: Indent of the rows under a header, in pt (default: one
                text height).
        """
        if gap < 0:
            raise ValueError("group gap must be 0 or more")
        if indent is not None and indent < 0:
            raise ValueError("indent must be 0 or more")
        self._group_gap, self._group_headers, self._indent = gap, headers, indent
        return self._changed()

    def markers(
        self,
        marker: str = "s",
        *,
        size: float | None = None,
        min_size: float | None = None,
    ) -> Self:
        """Shape and size of the point estimates.

        Args:
            marker: A matplotlib marker; ``"s"`` (square, default), ``"o"``,
                ``"D"``...
            size: Marker diameter in pt (default: the theme's marker_size).
                With ``weight=`` this is the size of the heaviest row.
            min_size: With ``weight=``, the smallest marker diameter in pt.
                Default: none, so marker area stays exactly proportional to
                weight and very light rows get tiny markers. Setting it keeps
                light rows visible but enlarges them beyond their weight; a
                :class:`PolicyWarning` names the affected rows.
        """
        if min_size is not None and min_size <= 0:
            raise ValueError("min_size must be positive")
        try:
            MarkerStyle(marker)
        except ValueError:
            raise ValueError(
                f"Unknown marker {marker!r}. Use a matplotlib marker such as "
                "'s', 'o' or 'D'."
            ) from None
        if size is not None and size <= 0:
            raise ValueError("marker size must be positive")
        self._marker, self._marker_size, self._marker_min = marker, size, min_size
        return self._changed()

    def xlim(self, low: float | None = None, high: float | None = None) -> Self:
        """Limits of the estimate axis. Ticks are chosen for the new range;
        intervals reaching past it end in arrowheads.

        Args:
            low: Lower limit; ``None`` leaves it automatic. Must be positive
                on a log axis.
            high: Upper limit; ``None`` leaves it automatic.
        """
        for value in (low, high):
            if value is None:
                continue
            if not isinstance(value, int | float) or not math.isfinite(value):
                raise TypeError("xlim values must be finite numbers or None")
            if self._log and value <= 0:
                raise ValueError(
                    f"xlim({low}, {high}): limits must be positive on the log "
                    "axis of a ratio forest, e.g. .xlim(0.1, 10). Use "
                    "forest(..., log=False) for a linear axis."
                )
        if low is not None and high is not None and low >= high:
            raise ValueError("xlim low must be below high")
        return super().xlim(low, high)

    def xticks(self, ticks: Sequence[float] | None = None) -> Self:
        """Exact tick positions on the estimate axis (e.g. ``[0.5, 1, 2, 4]``).
        Without ``.xlim()``, the axis widens to show every tick.

        Args:
            ticks: Tick values; ``None`` restores automatic ticks.
        """
        if ticks is None:
            self._xticks = None
            return self._changed()
        values = sorted({float(t) for t in ticks})
        if not values or not all(math.isfinite(v) for v in values):
            raise ValueError("xticks must be a non-empty sequence of finite numbers")
        if self._log and values[0] <= 0:
            raise ValueError("xticks must be positive on a log axis")
        self._xticks = values
        return self._changed()

    def log(self, axis: str = "y") -> Self:
        """Not used by forest plots: choose the axis with
        ``forest(..., log=True/False)``."""
        raise TypeError(
            "Forest plots set their axis scale with forest(..., log=True) or "
            "log=False; ratio scales default to a log axis."
        )

    def source_data(self) -> pd.DataFrame:
        """The plotted rows in display order, with the estimate text (for a
        journal's source-data file)."""
        out = []
        for row in self._rows():
            if row.kind == "header":
                continue
            for panel in self._panel_names:
                for hue in self._hues:
                    record = self._record(row, panel, hue)
                    if record is None:
                        continue
                    out.append(
                        {
                            "group": row.group,
                            "label": row.label,
                            "panel": panel,
                            "hue": hue,
                            "summary": row.kind == "summary",
                            "estimate": record["_e"],
                            "lower": record["_lo"],
                            "upper": record["_hi"],
                            "weight": record["_w"],
                            "text": self._estimate_text(record),
                        }
                    )
        frame = pd.DataFrame(out)
        drop = [
            name
            for name, used in (
                ("group", self._names["group"]),
                ("panel", self._names["panel"]),
                ("hue", self._names["hue"]),
                ("weight", self._names["weight"]),
            )
            if not used
        ]
        return frame.drop(columns=drop)

    # ----------------------------------------------------------- data model
    def _columns(
        self,
        spec: Columns | None,
        side: str,
        formats: dict[str, CellFormat],
        align: dict[str, Align],
    ) -> list[_Column]:
        if spec is None:
            return []
        if isinstance(spec, str):
            raise TypeError(f"table {side}= takes a list of columns or a mapping")
        items = (
            list(spec.items())
            if isinstance(spec, Mapping)
            else [(str(name), name) for name in spec]
        )
        columns = []
        for header, source in items:
            if isinstance(source, str):
                if source not in self._frame.columns or source.startswith("_"):
                    known = [c for c in self._frame.columns if not c.startswith("_")]
                    close = difflib.get_close_matches(source, known, n=1)
                    hint = f" Did you mean {close[0]!r}?" if close else ""
                    raise DataShapeError(
                        f"Table column {source!r} is not in the data.{hint}"
                    )
            elif isinstance(source, Mapping):
                keys = set(self._frame["_g"].dropna()) | set(self._frame["_l"])
                unknown = [k for k in source if k not in keys]
                if unknown:
                    raise DataShapeError(
                        f"Table column {header!r} has values for "
                        f"{unknown[0]!r}, which is neither a group nor a row label"
                    )
            else:
                raise TypeError(
                    f"Table column {header!r} must name a data column or be a "
                    "{group: value} mapping"
                )
            fmt = formats.get(header)
            if fmt is not None:
                _check_format(fmt, header)
            where = align.get(header, "center")
            if where not in ("left", "center", "right"):
                raise ValueError("align must be 'left', 'center' or 'right'")
            columns.append(_Column(str(header), source, fmt, where))
        return columns

    def _rows(self) -> list[_Row]:
        """Rows top to bottom, with section gaps, in data order."""
        frame = self._frame
        blocks: list[tuple[Any, list[str]]] = []
        seen: dict[Any, list[str]] = {}
        for g, label in dict.fromkeys(zip(frame["_g"], frame["_l"], strict=True)):
            if g is None:
                blocks.append((None, [label]))
            elif g in seen:
                seen[g].append(label)
            else:
                seen[g] = [label]
                blocks.append((g, seen[g]))
        rows: list[_Row] = []
        y = 0.0
        previous: Any = ...
        summary = set(self._summary)
        for group, labels in blocks:
            if previous is not ... and (group is not None or previous is not None):
                y += self._group_gap
            if group is not None and self._group_headers:
                rows.append(_Row("header", group, str(group), y))
                y += 1
            for label in labels:
                kind: Literal["item", "summary"] = (
                    "summary" if label in summary else "item"
                )
                rows.append(_Row(kind, group, label, y))
                y += 1
            previous = group
        return rows

    def _record(self, row: _Row, panel: Any, hue: Any) -> pd.Series | None:
        index = self._records.get((row.group, row.label, panel, hue))
        return None if index is None else self._frame.iloc[index]

    def _estimate_text(self, record: pd.Series) -> str:
        d = self._decimals
        e, lo, hi = (_number(record[k], d) for k in ("_e", "_lo", "_hi"))
        if self._scale == "difference":
            return f"{e} ({lo} to {hi})"
        return f"{e} ({lo}{_DASH}{hi})"

    def _hue_offsets(self, style: Style) -> dict[Any, float]:
        """Vertical offset (in rows) of each hue within its row."""
        n = len(self._hues)
        if n == 1:
            return {self._hues[0]: 0.0}
        step = self._line_pt(style) / self._row_pt(style)
        return {h: (i - (n - 1) / 2) * step for i, h in enumerate(self._hues)}

    def _line_pt(self, style: Style) -> float:
        return style.sizes.tick * 1.3

    def _row_pt(self, style: Style) -> float:
        n = len(self._hues)
        return max(style.sizes.tick * 2.1, self._line_pt(style) * (n + 0.6))

    def _cells(
        self, column: _Column, rows: list[_Row], panel: Any, style: Style
    ) -> dict[int, list[tuple[str, float, str | None]]]:
        """Text lines ``(text, dy, color)`` of a column for each row index.
        Per-hue values become dodged lines in the hue colors."""
        offsets = self._hue_offsets(style)
        dodged = len(self._hues) > 1
        source = column.source
        cells: dict[int, list[tuple[str, float, str | None]]] = {}
        for i, row in enumerate(rows):
            if isinstance(source, Mapping):
                key = row.group if row.kind == "header" else row.label
                if key in source:
                    cells[i] = [(_format_cell(source[key], column.fmt), 0.0, None)]
                continue
            if row.kind == "header":
                continue
            per_hue: dict[Any, str] = {}
            for hue in self._hues:
                values = []
                panels = self._panel_names if panel is ... else [panel]
                for p in panels:
                    record = self._record(row, p, hue)
                    if record is not None:
                        values.append(
                            self._estimate_text(record)
                            if source is None
                            else _format_cell(record[source], column.fmt)
                        )
                if len(set(values)) > 1:
                    raise DataShapeError(
                        f"Column {column.header!r} differs between panels for "
                        f"row {row.label!r}; put it in table(right=...) so each "
                        "panel shows its own value"
                    )
                if values:
                    per_hue[hue] = values[0]
            if not per_hue:
                continue
            if len(set(per_hue.values())) == 1 and source is not None:
                cells[i] = [(next(iter(per_hue.values())), 0.0, None)]
            else:
                cells[i] = [
                    (
                        text,
                        offsets[h],
                        self._mark_color(style, row, h) if dodged else None,
                    )
                    for h, text in per_hue.items()
                ]
        return cells

    # ------------------------------------------------------------- colors
    def _hue_text_colors(self, style: Style) -> dict[Any, str | None]:
        if len(self._hues) == 1:
            return {self._hues[0]: None}
        labels = list(dict.fromkeys(self._frame["_l"]))
        fn = self._category_color_fn(style, self._hues, labels, grouped=True)
        return {h: fn(h, None) for h in self._hues}

    def _mark_color(self, style: Style, row: _Row, hue: Any) -> str:
        grouped = self._names["hue"] is not None
        if row.kind == "summary" and not grouped and row.label not in self._color_map:
            return self._faded(style.theme.text_color or "#262626")
        labels = list(dict.fromkeys(self._frame["_l"]))
        fn = self._category_color_fn(style, self._hues, labels, grouped=grouped)
        return fn(hue, row.label)

    # ------------------------------------------------------------- styling
    def style(self) -> Style:
        """The resolved style; without an explicit height the figure is as
        tall as its rows need."""
        style = super().style()
        if self._height is not None:
            return style
        height = self._natural_height(style)
        limit = style.target.max_height
        adjustments = style.adjustments
        if limit is not None and height > limit:
            adjustments += (
                f"height {height:.2f} in for {len(self._rows())} rows reduced to "
                f"{style.preset.name} maximum {limit:.2f} in",
            )
            height = limit
        return replace(style, height=height, adjustments=adjustments)

    def _natural_height(self, style: Style) -> float:
        rows = self._rows()
        span = rows[-1].y - rows[0].y + 1.3 if rows else 1.0
        tick, label = style.sizes.tick, style.sizes.label
        header_lines = max(
            [
                1,
                *(
                    len(c.header.splitlines())
                    for c in self._left + self._right
                    if c.header
                ),
                *(len(str(p).splitlines()) for p in self._panel_names),
            ]
        )
        pt = span * self._row_pt(style)
        if self._null is not None and self._null_options.get("label"):
            header_lines += 1 if len(self._panel_names) > 1 else 0
        pt += header_lines * tick * 1.25 + 6
        pt += (style.theme.tick_length or 3.5) + 3.5 + tick * 1.3
        if any(self._favours):
            pt += tick * 1.5
        if style.theme.axis_titles or self._labels.get("x"):
            pt += label * 1.5
        if self._labels.get("title"):
            pt += style.sizes.title * 1.6
        if self._names["hue"] is not None:
            pt += tick * 2.0
        chrome = self._chrome
        for text, size in (
            (chrome.title, style.sizes.title),
            (chrome.subtitle, style.sizes.subtitle),
            (chrome.source, style.sizes.note),
            (chrome.note, style.sizes.note),
        ):
            if text:
                pt += size * 1.3 * (text.count("\n") + 1) + style.chrome.padding * 36
        return max(1.2, pt / _PT + 0.12)

    def _default_labels(self) -> dict[str, str | None]:
        return {"x": self._names["measure"], "y": None}

    def _refline_axis(self) -> Literal["x", "y"]:
        return "x"

    # ------------------------------------------------------------- drawing
    def _draw(self, ax: Axes, style: Style) -> None:
        fig = _root_figure(ax)
        theme = style.theme
        rows = self._rows()
        body = self._body = _Body()
        top, bottom = rows[0].y - 0.5, rows[-1].y + 0.8

        # Table columns: measure, then place outward from the plot region.
        left_cols = [
            _Column(self._names["label_header"] or "", "_l", None, "left"),
            *self._left,
        ]
        estimate_col = _Column(
            self._estimate_header
            if self._estimate_header is not None
            else f"{self._names['measure']} (95% CI)",
            None,
            None,
            "left",
        )
        if self._estimates and self._estimate_side == "left":
            left_cols.append(estimate_col)
        right_cols = (
            [estimate_col] if self._estimates and self._estimate_side == "right" else []
        )
        right_cols += self._right
        indent = (style.sizes.tick if self._indent is None else self._indent) / _PT
        gap = style.sizes.tick * 1.6 / _PT
        edge = style.sizes.tick * 0.9 / _PT
        size = style.sizes.tick

        def measure(text: str, bold: bool = False) -> tuple[float, float]:
            return _text_size(fig, text, size, bold)

        bold_rows = frozenset(
            i for i, r in enumerate(rows) if r.kind in ("header", "summary")
        )

        def place(column: _Column, panel: Any) -> _Placed:
            cells: dict[int, list[tuple[str, float, str | None]]]
            if column.source == "_l":
                cells = {i: [(r.label, 0.0, None)] for i, r in enumerate(rows)}
            else:
                cells = self._cells(column, rows, panel, style)
            width = measure(column.header, True)[0]
            for i, lines in cells.items():
                extra = (
                    indent if column.source == "_l" and self._indented(rows[i]) else 0
                )
                for text, _, _ in lines:
                    width = max(width, measure(text, i in bold_rows)[0] + extra)
            header_h = measure(column.header, True)[1]
            body.header = max(body.header, header_h)
            return _Placed(column, cells, width, bold_rows=bold_rows)

        count = count_panels = len(self._panel_names)
        left = [place(c, ...) for c in left_cols]
        cursor = -edge
        for placed in reversed(left):
            placed.x = cursor - placed.width
            cursor = placed.x - gap
        body.left = -(cursor + gap)

        panel_tables: list[list[_Placed]] = []
        right_extent = 0.0
        for panel in self._panel_names:
            placed_cols = [place(c, panel) for c in right_cols]
            cursor = edge
            for placed in placed_cols:
                placed.x = cursor
                cursor += placed.width + gap
            right_extent = max(right_extent, cursor - gap if placed_cols else 0.0)
            panel_tables.append(placed_cols)
        body.right = right_extent
        null_label = self._null_options.get("label") if self._null is not None else None
        label_height = measure(null_label)[1] + 2 / _PT if null_label else 0.0
        for name in self._panel_names:
            name_height = measure(str(name), True)[1] if count_panels > 1 else 0.0
            body.header = max(body.header, label_height + name_height)

        panel_gap = right_extent + edge * 2
        available = (
            style.width - body.left - right_extent - panel_gap * (count - 1) - 0.15
        ) / count
        if available < _MIN_PANEL_IN:
            raise DataShapeError(
                "The table leaves too little room for the forest "
                f"({max(available, 0):.2f} in per panel). Widen the figure "
                "(.size(width=...) or .preset(..., width='double')), shorten "
                "labels, or drop table columns."
            )

        # Panels: the main axes is the first; the rest are laid out beside it.
        panels = [ax]
        if count > 1:
            ax.set_axes_locator(_PanelLocator(ax, 0, count, panel_gap))
            for k in range(1, count):
                child = ax.inset_axes((0, 0, 1, 1))
                child.set_axes_locator(_PanelLocator(ax, k, count, panel_gap))
                child.patch.set_visible(False)
                panels.append(child)
            body.frame = BboxTransformTo(
                TransformedBbox(ax._originalPosition, fig.transSubfigure)  # type: ignore[attr-defined]
            )
        else:
            body.frame = ax.transAxes
        body.panels = panels
        frame = body.frame

        # Shading and rules span the table, behind everything.
        if self._stripes:
            color = self._stripes["color"] or with_alpha(
                theme.text_color or "#262626", 0.06
            )
            bands = (
                _bands(rows, "group")
                if self._stripes["by"] == "group"
                else [(r.y - 0.5, r.y + 0.5) for r in rows]
            )
            for i, band in enumerate(bands):
                if i % 2 == 0:
                    ax.add_artist(
                        _Span(
                            frame,
                            fig,
                            body.left,
                            right_extent,
                            band,
                            ax.transData,
                            facecolor=color,
                            edgecolor="none",
                            zorder=0.1,
                        )
                    )
        if self._dividers:
            divider = self._dividers
            for _, bottom_edge in _bands(rows, divider["by"])[:-1]:
                ax.add_artist(
                    _Rule(
                        frame,
                        fig,
                        body.left,
                        right_extent,
                        bottom_edge,
                        ax.transData,
                        color=divider["color"]
                        or theme.grid_color
                        or with_alpha(theme.text_color or "#262626", 0.2),
                        linewidth=theme.axis_line_width or 0.8
                        if divider["linewidth"] is None
                        else checked_size(
                            style, "divider linewidth", divider["linewidth"], "line"
                        ),
                        linestyle=divider["linestyle"],
                        zorder=0.2,
                    )
                )
        rule = theme.axis_line_width or 0.8
        ax.add_artist(
            _Span(
                frame,
                fig,
                body.left,
                right_extent,
                (1.0, 1.0),
                blended_transform_factory(frame, frame),
                height_pt=rule,
                facecolor=theme.axis_color or theme.text_color,
                edgecolor="none",
                zorder=2.5,
            )
        )

        # Text: the shared left table, then each panel's right table.
        text_color = theme.text_color
        row_frame = blended_transform_factory(frame, ax.transData)
        header_frame = blended_transform_factory(frame, frame)
        self._draw_table(
            ax, fig, left, rows, row_frame, header_frame, 0.0, style, indent
        )
        for panel_ax, placed_cols, name in zip(
            panels, panel_tables, self._panel_names, strict=True
        ):
            self._draw_table(
                ax,
                fig,
                placed_cols,
                rows,
                blended_transform_factory(panel_ax.transAxes, panel_ax.transData),
                blended_transform_factory(panel_ax.transAxes, frame),
                1.0,
                style,
                indent,
            )
            if null_label:
                ax.text(
                    self._null,  # type: ignore[arg-type]
                    1,
                    null_label,
                    transform=blended_transform_factory(panel_ax.transData, frame)
                    + ScaledTranslation(0, 3 / _PT, fig.dpi_scale_trans),
                    ha="center",
                    va="bottom",
                    fontsize=size,
                    color=theme.muted_text_color or text_color,
                    clip_on=False,
                )
            if count > 1:
                ax.text(
                    0.5,
                    1,
                    str(name),
                    transform=blended_transform_factory(panel_ax.transAxes, frame)
                    + ScaledTranslation(0, 3 / _PT + label_height, fig.dpi_scale_trans),
                    ha="center",
                    va="bottom",
                    fontsize=size,
                    fontweight="bold",
                    color=text_color,
                    clip_on=False,
                )

        # Marks.
        weights = self._frame["_w"].to_numpy(dtype=float)
        max_weight = float(np.nanmax(weights)) if self._names["weight"] else 1.0
        if self._names["weight"]:
            self._warn_weights(style, weights, max_weight)
        for k, (panel_ax, panel) in enumerate(
            zip(panels, self._panel_names, strict=True)
        ):
            self._draw_panel(panel_ax, style, rows, panel, max_weight, (top, bottom))
            if k == 0:
                self._draw_legend_proxies(panel_ax, style)
            self._draw_reflines(panel_ax, style)

    def _indented(self, row: _Row) -> bool:
        return (
            row.kind != "header"
            and row.group is not None
            and self._group_headers
            and row.kind != "summary"
        )

    def _draw_table(
        self,
        ax: Axes,
        fig: Figure,
        columns: list[_Placed],
        rows: list[_Row],
        row_transform: Transform,
        header_transform: Transform,
        x: float,
        style: Style,
        indent: float,
    ) -> None:
        size = style.sizes.tick
        color = style.theme.text_color
        for placed in columns:
            column = placed.column
            anchor = {
                "left": placed.x,
                "center": placed.x + placed.width / 2,
                "right": placed.x + placed.width,
            }[column.align]
            if column.header:
                ax.text(
                    x,
                    1,
                    column.header,
                    transform=header_transform
                    + ScaledTranslation(anchor, 3 / _PT, fig.dpi_scale_trans),
                    ha=column.align,
                    va="bottom",
                    multialignment=column.align,
                    fontsize=size,
                    fontweight="bold",
                    color=color,
                    clip_on=False,
                )
            for i, lines in placed.cells.items():
                row = rows[i]
                shift = indent if column.source == "_l" and self._indented(row) else 0.0
                for text, dy, line_color in lines:
                    if not text:
                        continue
                    ax.text(
                        x,
                        row.y + dy,
                        text,
                        transform=row_transform
                        + ScaledTranslation(anchor + shift, 0, fig.dpi_scale_trans),
                        ha=column.align,
                        va="center_baseline",
                        fontsize=size,
                        fontweight="bold"
                        if i in placed.bold_rows and column.source == "_l"
                        else "normal",
                        color=line_color or color,
                        clip_on=False,
                    )

    def _limits_for(self, panel: Any) -> tuple[float, float, list[float]]:
        """x limits and ticks of one panel: the user's limits and ticks, or
        ticks that bracket the intervals and the null line."""
        frame = self._frame
        data = frame if self._names["panel"] is None else frame[frame["_p"] == panel]
        low, high = float(data["_lo"].min()), float(data["_hi"].max())
        if self._null is not None:
            low, high = min(low, self._null), max(high, self._null)
        if self._xticks is not None:
            low, high = min(low, self._xticks[0]), max(high, self._xticks[-1])
        user_low, user_high = self._limits.get("x", (None, None))
        if self._log:
            if high / low < 1.05:
                low, high = low / 1.1, high * 1.1
            ticks_for = _ratio_ticks
        else:
            if math.isclose(low, high):
                low, high = low - 1, high + 1
            ticks_for = _difference_ticks
        ticks = ticks_for(low, high)
        lo = ticks[0] if user_low is None else float(user_low)
        hi = ticks[-1] if user_high is None else float(user_high)
        if self._xticks is not None and user_low is None:
            lo = min(lo, self._xticks[0])
        if self._xticks is not None and user_high is None:
            hi = max(hi, self._xticks[-1])
        if lo >= hi:
            raise ValueError(
                f"xlim gives an empty axis ({lo:g} to {hi:g}); set both limits"
            )
        if self._xticks is not None:
            ticks = self._xticks
        elif user_low is not None or user_high is not None:
            ticks = ticks_for(lo, hi)
        tol = 1e-9 * max(abs(lo), abs(hi))
        inside = [t for t in ticks if lo - tol <= t <= hi + tol]
        if self._xticks is None and len(inside) < 2:
            # A narrow user range can fall between two "nice" ticks.
            inside = sorted({lo, *inside, hi})
        return lo, hi, inside

    def _draw_panel(
        self,
        ax: Axes,
        style: Style,
        rows: list[_Row],
        panel: Any,
        max_weight: float,
        ylim: tuple[float, float],
    ) -> None:
        theme = style.theme
        ax.set_ylim(ylim[1], ylim[0])
        ax.set_xscale("log" if self._log else "linear")
        low, high, ticks = self._limits_for(panel)
        ax.set_xlim(low, high)
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(FuncFormatter(_tick_text))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_yticks([])
        ax.tick_params(axis="y", left=False, right=False, labelleft=False)
        for side, spine in ax.spines.items():
            spine.set_visible(side == "bottom" and "bottom" in (theme.spines or ()))
        if theme.grid in ("both", "value", "x"):
            ax.xaxis.grid(True)

        if self._null is not None:
            options = self._null_options
            ax.axvline(
                self._null,
                color=options.get("color") or theme.text_color,
                lw=theme.axis_line_width
                if options.get("linewidth") is None
                else checked_size(
                    style, "null linewidth", options["linewidth"], "line"
                ),
                ls=options.get("linestyle", "-"),
                zorder=1.3,
            )
        offsets = self._hue_offsets(style)
        base = self._marker_size or theme.marker_size or 5.0
        # Intervals are thinner than data lines: many rows, read as a table.
        lw = max((theme.line_width or 1.0) * 0.6, theme.axis_line_width or 0.5)
        for row in rows:
            if row.kind == "header":
                continue
            for hue in self._hues:
                record = self._record(row, panel, hue)
                if record is None:
                    continue
                color = self._mark_color(style, row, hue)
                y = row.y + offsets[hue]
                e, lo, hi = (
                    float(record["_e"]),
                    float(record["_lo"]),
                    float(record["_hi"]),
                )
                if row.kind == "summary":
                    h = (
                        0.32
                        if len(self._hues) == 1
                        else 0.4 * abs(next(iter(offsets.values())) or 0.5)
                    )
                    ax.add_patch(
                        Polygon(
                            [(lo, y), (e, y - h), (hi, y), (e, y + h)],
                            closed=True,
                            facecolor=color,
                            edgecolor="none",
                            zorder=3,
                        )
                    )
                    continue
                self._draw_interval(ax, y, lo, hi, (low, high), color, lw)
                ms = base
                if self._names["weight"]:
                    w = float(record["_w"])
                    if not math.isfinite(w):
                        raise DataShapeError(
                            f"Row {row.label!r} has no weight. Give it one, or "
                            "draw it as a diamond with .summary()."
                        )
                    if w == 0:
                        continue  # zero area; the interval alone remains
                    ms = base * 1.5 * math.sqrt(w / max_weight)
                    if self._marker_min is not None:
                        ms = max(ms, self._marker_min)
                if low <= e <= high:
                    ax.plot(
                        [e],
                        [y],
                        ls="",
                        marker=self._marker,
                        ms=ms,
                        mfc=color,
                        mec="none",
                        zorder=3,
                    )

    def _warn_weights(
        self, style: Style, weights: np.ndarray, max_weight: float
    ) -> None:
        labels = self._frame["_l"].astype(str).to_numpy()
        if not max_weight > 0:
            raise DataShapeError(
                f"Every weight in {self._names['weight']!r} is zero, so no marker "
                "could have any area. Give at least one row a positive weight."
            )
        zero = list(dict.fromkeys(labels[weights == 0]))
        if zero:
            emit(
                PolicyWarning,
                f"Row(s) {', '.join(map(repr, zero[:4]))}"
                f"{', ...' if len(zero) > 4 else ''} "
                "have zero weight, so no marker is drawn for them: marker area "
                "encodes weight, and a visible marker would claim a weight they "
                "do not have. Their intervals are still shown.",
                stacklevel=5,
            )
        if self._marker_min is not None:
            base = self._marker_size or style.theme.marker_size or 5.0
            sizes = base * 1.5 * np.sqrt(weights / max_weight)
            floored = list(
                dict.fromkeys(labels[(weights > 0) & (sizes < self._marker_min)])
            )
            if floored:
                emit(
                    PolicyWarning,
                    f"Row(s) {', '.join(map(repr, floored[:4]))}"
                    f"{', ...' if len(floored) > 4 else ''} are drawn at "
                    f"min_size={self._marker_min:g} pt, larger than their weight "
                    "implies, so marker area is no longer proportional to weight "
                    "for them. Report the weights in a column, or drop min_size "
                    "to keep areas exact.",
                    stacklevel=5,
                )

    def _draw_interval(
        self,
        ax: Axes,
        y: float,
        lo: float,
        hi: float,
        limits: tuple[float, float],
        color: str,
        lw: float,
    ) -> None:
        """CI line; ends beyond the axis are cut with an arrowhead."""
        low, high = limits
        start, stop = max(lo, low), min(hi, high)
        if start >= stop:
            return
        ax.plot(
            [start, stop], [y, y], color=color, lw=lw, solid_capstyle="butt", zorder=2
        )
        head = lw * 3.2
        if lo < low:
            ax.plot(
                [start],
                [y],
                ls="",
                marker="<",
                ms=head,
                mfc=color,
                mec="none",
                zorder=2,
            )
        if hi > high:
            ax.plot(
                [stop], [y], ls="", marker=">", ms=head, mfc=color, mec="none", zorder=2
            )

    def _draw_legend_proxies(self, ax: Axes, style: Style) -> None:
        if self._names["hue"] is None:
            return
        colors = self._hue_text_colors(style)
        base = self._marker_size or style.theme.marker_size or 5.0
        for hue in self._hues:
            ax.plot(
                [],
                [],
                ls="",
                marker=self._marker,
                ms=base,
                mfc=colors[hue],
                mec="none",
                label=str(hue),
            )

    def _finish_axes(self, ax: Axes, style: Style) -> None:
        labels, limits = self._labels, self._limits
        title = labels.get("title")
        self._labels = {k: v for k, v in labels.items() if k != "title"}
        # x limits were already applied per panel, with matching ticks.
        self._limits = {k: v for k, v in limits.items() if k != "x"}
        try:
            for panel in self._body.panels or [ax]:
                super()._finish_axes(panel, style)
                panel.set_box_aspect(None)
                if any(self._favours):
                    self._draw_favours(panel, style)
        finally:
            self._labels, self._limits = labels, limits
        if title:
            self._draw_title(ax, style, title)
        if self._names["hue"] is not None:
            self._draw_legend(ax, style, n=len(self._hues), title=self._names["hue"])

    def _draw_favours(self, ax: Axes, style: Style) -> None:
        # Arrows are drawn, not typed: many journal fonts lack arrow glyphs.
        fig = _root_figure(ax)
        size = style.sizes.tick
        color = style.theme.text_color
        drop = ((style.theme.tick_length or 3.5) + 3.5 + size * 1.35 + 1.5) / _PT
        middle = -drop - size * 0.38 / _PT
        gap, length = size * 0.5 / _PT, size * 1.8 / _PT
        base = blended_transform_factory(ax.transData, ax.transAxes)
        for text, sign in ((self._favours[0], -1), (self._favours[1], 1)):
            if not text:
                continue
            ax.text(
                self._null,  # type: ignore[arg-type]
                0,
                text,
                transform=base
                + ScaledTranslation(sign * gap, -drop, fig.dpi_scale_trans),
                ha="right" if sign < 0 else "left",
                va="top",
                fontsize=size,
                color=color,
                clip_on=False,
            )
            start = gap * 2 + _text_size(fig, text, size)[0]
            ax.annotate(
                "",
                xy=(self._null, 0),
                xycoords=base
                + ScaledTranslation(
                    sign * (start + length), middle, fig.dpi_scale_trans
                ),
                xytext=(self._null, 0),
                textcoords=base
                + ScaledTranslation(sign * start, middle, fig.dpi_scale_trans),
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": color,
                    "lw": style.theme.axis_line_width or 0.8,
                    "mutation_scale": size * 0.9,
                    "shrinkA": 0,
                    "shrinkB": 0,
                },
                annotation_clip=False,
            )
        ax.xaxis.labelpad = 4 + size * 1.5

    def _draw_title(self, ax: Axes, style: Style, title: str) -> None:
        fig = _root_figure(ax)
        body = self._body
        frame = body.frame or ax.transAxes
        left = style.chrome.title_align == "left"
        dx = -body.left if left else (body.right - body.left) / 2
        ax.text(
            0 if left else 0.5,
            1,
            title,
            transform=blended_transform_factory(frame, frame)
            + ScaledTranslation(dx, body.header + 8 / _PT, fig.dpi_scale_trans),
            ha="left" if left else "center",
            va="bottom",
            fontsize=style.sizes.title,
            fontweight=style.theme.title_weight,
            color=style.theme.text_color,
            clip_on=False,
        )

    def _draw_legend(
        self, ax: Axes, style: Style, *, n: int, title: str | None
    ) -> None:
        # Called from _finish_axes (after the table is placed), not by the base.
        if self._names["hue"] is None or self._body.frame is None:
            return
        super()._draw_legend(ax, style, n=n, title=title)
        legend, kwargs = ax.get_legend(), self._legend_kwargs
        side = self._legend_side
        if legend is None or kwargs is None or side is None:
            return
        fig = _root_figure(ax)
        body = self._body
        frame = body.frame
        assert frame is not None
        if side == "top":
            lift = body.header + 6 / _PT
            if self._labels.get("title"):
                lift += style.sizes.title * 1.5 / _PT
            anchor = blended_transform_factory(frame, frame) + ScaledTranslation(
                -body.left, lift, fig.dpi_scale_trans
            )
            kwargs |= {"bbox_to_anchor": (0, 1), "bbox_transform": anchor}
        else:
            anchor = blended_transform_factory(frame, frame) + ScaledTranslation(
                body.right + 0.1, 0, fig.dpi_scale_trans
            )
            kwargs |= {"bbox_to_anchor": (1, 1), "bbox_transform": anchor}
        legend.remove()
        ax.legend(**kwargs)
        # The legend already clears the table; the base would move it again.
        self._legend_side = None


def _check_columns(frame: pd.DataFrame, **columns: str | None) -> None:
    for role, name in columns.items():
        if name is None:
            continue
        if name not in frame.columns:
            close = difflib.get_close_matches(str(name), map(str, frame.columns), n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise DataShapeError(
                f"{role}={name!r} is not a column.{hint} "
                f"Columns: {', '.join(map(str, frame.columns))}"
            )


def forest(
    data: Any,
    label: str | None = None,
    estimate: str = "estimate",
    lower: str = "lower",
    upper: str = "upper",
    *,
    group: str | None = None,
    hue: str | None = None,
    panel: str | None = None,
    weight: str | None = None,
    scale: Scale = "ratio",
    log: bool | None = None,
    null: float | bool | None = None,
    hue_order: Sequence[Any] | None = None,
    panel_order: Sequence[Any] | None = None,
    missing: DropPolicy = "raise",
) -> ForestPlot:
    """Forest plot: one estimate and confidence interval per row, with the
    labels and "estimate (95% CI)" text in a table beside it. Rows are drawn
    in data order.

    Args:
        data: DataFrame (or dict of columns), one row per estimate.
        label: Column of row labels (default: the index).
        estimate: Column of point estimates.
        lower: Column of lower confidence limits.
        upper: Column of upper confidence limits.
        group: Column of sections (e.g. "Age", "Sex"): a bold header row
            each, with their rows indented below. Rows with an empty group
            (e.g. "Overall") stand alone.
        hue: Column of models or arms shown together in each row, dodged and
            colored, with a legend.
        panel: Column that splits the intervals into side-by-side forests
            sharing the row labels (e.g. outcomes).
        weight: Column of study weights; marker area is proportional (zero
            weight draws no marker; see ``.markers(min_size=...)``).
        scale: ``"ratio"`` (default; odds, hazard, risk, rate ratios) has no
            effect at 1 and needs positive values; ``"difference"`` (mean or
            risk differences, coefficients) has no effect at 0.
        log: Log axis for the estimates. Default: ``True`` for ratios (so
            0.5 and 2 sit equally far from 1), ``False`` for differences.
            ``log=False`` draws ratios on a linear axis. Set limits and ticks
            with ``.xlim()`` and ``.xticks()``.
        null: Position of the line of no effect (default 1 for ratios, 0
            for differences); ``False`` hides it. ``.null()`` also styles
            and labels it.
        hue_order: Explicit order of the ``hue`` values.
        panel_order: Explicit order of the panels.
        missing: "raise" (default) rejects missing/non-finite estimates or
            limits; "drop" leaves those rows out.

    Example:
        >>> sp.forest(df, label="subgroup", estimate="hr", lower="lo",  # doctest: +SKIP
        ...           upper="hi", group="variable").favours("Drug", "Placebo")
    """
    if scale not in ("ratio", "difference"):
        raise ValueError("scale must be 'ratio' or 'difference'")
    if log is None:
        log = scale == "ratio"
    elif not isinstance(log, bool):
        raise TypeError("log must be True, False or None")
    elif log and scale == "difference":
        raise ValueError(
            "log=True needs scale='ratio': differences can be zero or negative"
        )
    frame = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if label is None:
        index_name = frame.index.name
        frame = frame.reset_index(names="_index_label")
        label, label_header = "_index_label", index_name
    else:
        label_header = label
    _check_columns(
        frame,
        label=label,
        estimate=estimate,
        lower=lower,
        upper=upper,
        group=group,
        hue=hue,
        panel=panel,
        weight=weight,
    )
    # Weights are checked when drawing: summary rows need none.
    values = [estimate, lower, upper]
    keys = [label, *(c for c in (hue, panel) if c)]
    for column in [*values, *([weight] if weight else [])]:
        frame[column] = numeric_array(frame[column])
    frame = handle_missing(frame, missing, values=values, keys=keys)

    frame["_l"] = frame[label].astype(str)
    # Object columns keep None ("no group"); inferred string dtypes turn it
    # into NaN, which never compares equal in the row lookups.
    for key, role in (("_g", group), ("_h", hue), ("_p", panel)):
        cells = frame[role] if role else [None] * len(frame)
        frame[key] = pd.Series(
            [None if pd.isna(v) else v for v in cells], index=frame.index, dtype=object
        )
    frame["_e"], frame["_lo"], frame["_hi"] = (
        frame[estimate],
        frame[lower],
        frame[upper],
    )
    frame["_w"] = frame[weight] if weight else 1.0

    bad = frame[(frame["_lo"] > frame["_e"]) | (frame["_e"] > frame["_hi"])]
    if not bad.empty:
        raise DataShapeError(
            f"{len(bad)} row(s) do not satisfy {lower} <= {estimate} <= {upper}, "
            f"e.g. {bad['_l'].iloc[0]!r}. Check the column order."
        )
    if scale == "ratio" and (frame["_lo"] <= 0).any():
        raise DataShapeError(
            "Ratios must be positive for the log axis of scale='ratio'. "
            "For differences or coefficients use scale='difference'; "
            "exponentiate log ratios first."
        )
    if weight and (frame["_w"] < 0).any():
        raise DataShapeError(f"weight column {weight!r} must not be negative")
    dupes = frame.duplicated(["_g", "_l", "_h", "_p"])
    if dupes.any():
        raise DataShapeError(
            f"Row {frame.loc[dupes, '_l'].iloc[0]!r} appears more than once"
            + (" in its group" if group else "")
            + ". Give each estimate its own label, or use hue=/panel= for "
            "several estimates per row."
        )
    hues = _order(frame[hue], hue_order, "hue") if hue else [None]
    panels = _order(frame[panel], panel_order, "panel") if panel else [None]
    if hue:
        frame = frame[frame[hue].isin(hues)]
    if panel:
        frame = frame[frame[panel].isin(panels)]
    frame = frame.reset_index(drop=True)

    plot = ForestPlot(
        frame,
        names={
            "measure": _measure_name(estimate),
            "label_header": _legend_title(label_header)
            if isinstance(label_header, str)
            else None,
            "group": group,
            "hue": hue,
            "panel": panel,
            "weight": weight,
        },
        scale=scale,
        log=log,
        hues=hues,
        panels=panels,
    )
    return plot.null(True if null is None else null)
