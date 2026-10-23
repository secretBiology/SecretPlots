"""Base class shared by every plot: chaining verbs, lazy rendering, saving."""

import copy
import difflib
import inspect
import io
import math
import re
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from os import PathLike
from pathlib import Path
from typing import Any, ClassVar, Literal, Self, get_type_hints

import numpy as np
import pandas as pd
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.dates import DateFormatter
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from matplotlib.transforms import ScaledTranslation

from SecretPlots import presets
from SecretPlots.core import state
from SecretPlots.core.chrome import ChromeText, apply_chrome
from SecretPlots.core.colors import extend_palette, with_alpha
from SecretPlots.core.resolve import Style, checked_size, resolve
from SecretPlots.core.units import Length
from SecretPlots.errors import DataShapeError, FormatWarning, emit
from SecretPlots.presets._schema import coerce_theme_field
from SecretPlots.theme import (
    STYLE_FIELDS,
    LegendPosition,
    Theme,
    _describe_type,
    get_theme,
)

_LEGEND_POSITIONS = ("auto", "top", "right", "inside", "none")
_LEGEND_GAP_IN = 0.08

RefAxis = Literal["x", "y"]


@dataclass(frozen=True)
class _RefLine:
    """One ``.refline()`` value with its options (``axis=None``: the plot's
    value axis, decided when drawing)."""

    value: Any
    axis: RefAxis | None
    label: bool | str
    color: str | None
    linestyle: str
    linewidth: float | None
    label_position: Literal["start", "center", "end"] = "end"
    label_rotation: float = 0
    label_side: Literal["left", "right", "above", "below"] | None = None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float | np.number) and not isinstance(value, bool)


def _ref_text(value: Any) -> str:
    """How a reference line's value is written next to it."""
    if isinstance(value, pd.Timestamp | np.datetime64 | date):
        return str(pd.Timestamp(value).date())
    return f"{value:.3g}" if _is_number(value) else str(value)


def _is_date_axis(axis: Any) -> bool:
    get = getattr(axis, "get_converter", None)
    converter = get() if callable(get) else getattr(axis, "converter", None)
    return converter is not None and "Date" in type(converter).__name__


def _outside_anchor(ax: Axes, side: str, offset_in: float) -> dict[str, Any]:
    """Anchor just outside the axes, ``offset_in`` inches away. A physical offset
    stays correct when constrained layout later resizes the axes."""
    dx, dy = (offset_in, 0.0) if side == "right" else (0.0, offset_in)
    return {
        "bbox_to_anchor": (1, 1) if side == "right" else (0, 1),
        "bbox_transform": ax.transAxes
        + ScaledTranslation(dx, dy, ax.get_figure().dpi_scale_trans),  # type: ignore[union-attr]
    }


def _root_figure(artist: Artist) -> Figure:
    """Find the root figure, including on Matplotlib 3.9 and nested SubFigures."""
    root = artist.get_figure()
    while root is not None and not isinstance(root, Figure):
        root = root.get_figure()
    if not isinstance(root, Figure):
        raise ValueError("artist is not attached to a figure")
    return root


def _renderer(fig: Figure) -> RendererBase:
    get = getattr(fig.canvas, "get_renderer", None)
    if callable(get):
        renderer: RendererBase = get()
        return renderer
    return fig._get_renderer()  # type: ignore[attr-defined, no-any-return]


def _restyle_axes(ax: Axes, style: Style) -> None:
    """Apply the style to axes created outside ``style.rc_context()``.

    Ticks, spines and the axis-title texts read rcParams when they are
    created, so a user-made axes keeps matplotlib's defaults otherwise.
    """
    rc = style.rc()
    family = rc["font.family"]
    for axis in ("x", "y"):
        ax.tick_params(
            axis=axis,
            which="major",
            labelsize=rc[f"{axis}tick.labelsize"],
            labelcolor=rc[f"{axis}tick.labelcolor"],
            labelfontfamily=family,
            color=rc[f"{axis}tick.color"],
            width=rc[f"{axis}tick.major.width"],
            length=rc[f"{axis}tick.major.size"],
        )
    for label in (ax.xaxis.label, ax.yaxis.label):
        label.set(fontsize=rc["axes.labelsize"], color=rc["axes.labelcolor"])
        label.set_fontfamily(family)
    for title in (ax.title, ax._left_title, ax._right_title):  # type: ignore[attr-defined]
        title.set(
            fontsize=rc["axes.titlesize"],
            fontweight=rc["axes.titleweight"],
            color=rc["axes.titlecolor"],
        )
        title.set_fontfamily(family)
    for side, spine in ax.spines.items():
        spine.set(
            visible=rc[f"axes.spines.{side}"],
            edgecolor=rc["axes.edgecolor"],
            linewidth=rc["axes.linewidth"],
        )
    ax.set_facecolor(rc["axes.facecolor"])
    ax.set_axisbelow(rc["axes.axisbelow"])
    ax.set_prop_cycle(rc["axes.prop_cycle"])


# ------------------------------------------------------- options() introspection
_ARG_LINE = re.compile(r"^ {4}\*{0,2}(\w+): (.*)$")


def _verbs(cls: type) -> dict[str, Callable[..., Any]]:
    """Public chainable methods (those returning ``Self``), in definition order."""
    found: dict[str, Callable[..., Any]] = {}
    for klass in reversed(cls.__mro__):
        for name, attr in vars(klass).items():
            if name.startswith("_") or not inspect.isfunction(attr):
                continue
            if inspect.signature(attr).return_annotation is Self:
                found[name] = attr
    return found


def _plain(text: str) -> str:
    return re.sub(r"``(.*?)``", r"\1", text)


def _summary(fn: Callable[..., Any]) -> str:
    doc = inspect.getdoc(fn) or ""
    return _plain(" ".join(doc.split("\n\n")[0].split()))


def _arg_docs(fn: Callable[..., Any]) -> dict[str, str]:
    """Parse the Google-style ``Args:`` section of a verb's docstring."""
    lines = (inspect.getdoc(fn) or "").splitlines()
    if "Args:" not in lines:
        return {}
    docs: dict[str, str] = {}
    name: str | None = None
    for line in lines[lines.index("Args:") + 1 :]:
        if not line.startswith("    "):
            break
        match = _ARG_LINE.match(line)
        if match:
            name = match.group(1)
            docs[name] = match.group(2)
        elif name:
            docs[name] += " " + line.strip()
    return {key: _plain(value) for key, value in docs.items()}


def _display_name(param: inspect.Parameter) -> str:
    if param.kind is param.VAR_POSITIONAL:
        return "*" + param.name
    if param.kind is param.VAR_KEYWORD:
        return "**" + param.name
    return param.name


def _legend_title(name: str | None) -> str | None:
    """Sentence case for a plain column name (``"cell_type"`` -> ``"Cell
    type"``); names with capitals (``"pH"``, ``"CD4"``) are kept as written."""
    if not name or not isinstance(name, str) or name != name.lower():
        return name
    text = name.replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def _param_names(fn: Callable[..., Any]) -> list[str]:
    params = list(inspect.signature(fn).parameters.values())[1:]
    return [_display_name(p) for p in params]


def _parameter_table(
    fn: Callable[..., Any], params: list[inspect.Parameter]
) -> pd.DataFrame:
    """One row per parameter: allowed values, default and docstring text."""
    hints = get_type_hints(fn)
    docs = _arg_docs(fn)
    rows = []
    for p in params:
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            default = ""
        elif p.default is p.empty:
            default = "required"
        else:
            default = p.default
        rows.append(
            {
                "option": _display_name(p),
                "allowed": _describe_type(hints.get(p.name, Any)),
                "default": default,
                "description": docs.get(p.name, ""),
            }
        )
    return pd.DataFrame(
        rows, columns=["option", "allowed", "default", "description"]
    ).set_index("option")


class Plot(ABC):
    """A lazily drawn figure. Verbs return the plot so calls can be chained;
    nothing is drawn until :meth:`show`, :meth:`save`, ``.fig``/``.ax`` or
    notebook display."""

    kind: ClassVar[str] = "plot"
    #: Reference lines sit behind points and lines; plots of filled marks
    #: (bars, cells) raise this so the lines stay visible.
    _refline_zorder: ClassVar[float] = 1.5
    #: Plots that redraw their body after layout draw reference lines
    #: themselves (with :meth:`_draw_reflines`) so they are redrawn too.
    _reflines_in_draw: ClassVar[bool] = False
    #: Words a plot's ``.refline()`` accepts besides positions (statistics).
    _refline_words: ClassVar[tuple[str, ...]] = ()
    #: Legend handle length in font sizes; plots of lines need room for dashes.
    _handle_length: ClassVar[float] = 1.0
    #: Name of the function in the plot's module that builds it (``"bar"``
    #: for ``sp.bar``); :meth:`arguments` describes its parameters.
    _constructor: ClassVar[str | None] = None

    def __init__(self) -> None:
        selection = state.current()
        self._selection = replace(selection, theme=selection.theme_obj())
        self._axis_formats: dict[
            RefAxis, tuple[str, int, str, str, float, str | None]
        ] = {}
        self._overrides: dict[str, Any] = {}
        self._labels: dict[str, str] = {}
        self._legend: LegendPosition | None = None
        self._legend_options: dict[str, Any] = {}
        self._chrome = ChromeText()
        self._preset: str | None = None
        self._theme: Theme | str | None = None
        self._width: Length | None = None
        self._height: Length | None = None
        self._scale_text = False
        self._limits: dict[str, tuple[float | None, float | None]] = {}
        self._log_axes: set[str] = set()
        self._highlight: tuple[Any, ...] = ()
        self._color_map: dict[Any, str] = {}
        self._color_alpha: float | None = None
        self._reflines: list[_RefLine] = []

        self._figure: Figure | None = None
        self._axes: Axes | None = None
        self._style: Style | None = None
        self._legend_kwargs: dict[str, Any] | None = None
        self._legend_side: str | None = None
        self._legend_wrap = False

    # ----------------------------------------------------------------- verbs
    def _changed(self) -> Self:
        self._figure = self._axes = self._style = None
        return self

    def _data_changed(self) -> Self:
        """Invalidate a data-dependent result; subclasses rebuild summaries here."""
        return self._changed()

    def copy(self) -> Self:
        """Independent plot specification and data, without rendered artists.

        Useful for ``paper = plot.copy().preset("nature")`` and a separate
        presentation version. Direct matplotlib edits are not copied.
        """
        # Exclude artists and the resolved style (which contains read-only
        # mappings); they are recreated by rendering the copied specification.
        memo: dict[int, Any] = {}
        for name in (
            "_figure",
            "_axes",
            "_style",
            "_legend_kwargs",
            "_cax",
            "_track_legend",
        ):
            value = getattr(self, name, None)
            if value is not None:
                memo[id(value)] = None
        for name in ("_value_texts", "_end_texts", "_point_sets"):
            if hasattr(self, name):
                memo[id(getattr(self, name))] = []
        if hasattr(self, "_body"):
            memo[id(self._body)] = type(self._body)()
        result = copy.deepcopy(self, memo)
        return result._changed()

    def format_axis(
        self,
        axis: Literal["x", "y"] = "y",
        kind: Literal["number", "percent", "currency", "date"] = "number",
        *,
        decimals: int = 0,
        prefix: str = "",
        suffix: str = "",
        scale: float = 1.0,
        date_format: str | None = None,
    ) -> Self:
        """Format tick labels consistently across plots; data stay unchanged.

        Args:
            axis: The displayed "x" or "y" axis.
            kind: "number", "percent" (fractions), "currency", or "date".
            decimals: Digits after the decimal point; default 0.
            prefix: Text before numeric labels; currency defaults to "$".
            suffix: Text after numeric labels, e.g. " kg".
            scale: Multiply values for display only. Use 0.01 with percent
                when data are already percentages, or 1e-6 for millions.
            date_format: strftime pattern for dates; default "%Y-%m-%d".
        """
        if axis not in ("x", "y"):
            raise ValueError("axis must be 'x' or 'y'")
        if kind not in ("number", "percent", "currency", "date"):
            raise ValueError("kind must be 'number', 'percent', 'currency' or 'date'")
        if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
            raise ValueError("decimals must be a non-negative integer")
        if not np.isfinite(scale):
            raise ValueError("scale must be finite")
        self._axis_formats[axis] = (kind, decimals, prefix, suffix, scale, date_format)
        return self._changed()

    def labels(
        self, *, x: str | None = None, y: str | None = None, title: str | None = None
    ) -> Self:
        """Axis titles and plot title.

        ``x`` and ``y`` are the axes as drawn, so with horizontal bars ``x`` is
        the value axis.

        Args:
            x: Bottom axis title. ``""`` hides the automatic one.
            y: Left axis title. ``""`` hides the automatic one.
            title: Title above the axes. A top legend moves right to make room.
        """
        for key, value in (("x", x), ("y", y), ("title", title)):
            if value is not None:
                self._labels[key] = value
        return self._changed()

    def legend(
        self,
        position: LegendPosition | bool = "auto",
        *,
        title: str | None = None,
        ncols: int | None = None,
        fontsize: float | None = None,
        loc: str | None = None,
        anchor: tuple[float, float] | None = None,
    ) -> Self:
        """Place and format the legend. Each call resets options it doesn't pass.

        Args:
            position: ``"auto"`` (top for up to 4 entries or narrow figures,
                else right), ``"top"``, ``"right"``, ``"inside"`` (emptiest
                spot in the axes), or ``False``/``"none"`` to hide it.
            title: Legend title, replacing the hue column name. ``""`` hides
                it. Shown even when the theme turns legend titles off.
            ncols: Fixed number of columns. Without it a top legend wraps to fit.
            fontsize: Text size in pt for the entries and the legend title.
            loc: Which corner of the legend to place, as in matplotlib, e.g.
                ``"upper right"`` or ``"center left"``.
            anchor: ``(x, y)`` in axes fractions where that corner sits;
                ``(0, 0)`` is the bottom-left of the plot area.
        """
        if position is True:
            position = "auto"
        elif position is False:
            position = "none"
        if position not in _LEGEND_POSITIONS:
            raise ValueError(f"legend position must be one of {_LEGEND_POSITIONS}")
        if ncols is not None and (
            isinstance(ncols, bool) or not isinstance(ncols, int) or ncols < 1
        ):
            raise ValueError("legend ncols must be a positive integer")
        if fontsize is not None and fontsize <= 0:
            raise ValueError("legend fontsize must be positive")
        if anchor is not None:
            if len(anchor) != 2:
                raise ValueError("legend anchor must be an (x, y) pair")
            anchor = (float(anchor[0]), float(anchor[1]))
        self._legend = position
        self._legend_options = {
            "title": title,
            "ncols": ncols,
            "fontsize": fontsize,
            "loc": loc,
            "anchor": anchor,
        }
        return self._changed()

    def chrome(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        source: str | None = None,
        note: str | None = None,
    ) -> Self:
        """Headline/subtitle above the plot and note/source line below it.
        Arguments left out keep their current value.

        Args:
            title: Headline above the plot.
            subtitle: Smaller line under the headline.
            source: Data source line below the plot.
            note: Footnote below the plot.
        """
        current = self._chrome
        self._chrome = ChromeText(
            title=title if title is not None else current.title,
            subtitle=subtitle if subtitle is not None else current.subtitle,
            source=source if source is not None else current.source,
            note=note if note is not None else current.note,
        )
        return self._changed()

    def preset(
        self, name: str, *, width: Length | None = None, height: Length | None = None
    ) -> Self:
        """Use a preset for this plot only: ``.preset("nature", width="double")``.

        Args:
            name: Preset name; ``sp.presets.list()`` shows them all.
            width: A width name from the preset (e.g. ``"double"``) or a length:
                a number in inches or text like ``"89mm"``, ``"600px"``.
            height: Length: a number in inches or text like ``"60mm"``.
        """
        presets.get(name)
        self._preset = name
        self._width, self._height = width, height
        return self._changed()

    def size(
        self,
        width: Length | None = None,
        height: Length | None = None,
        *,
        scale_text: bool | None = None,
    ) -> Self:
        """Figure size. Arguments left out keep their current value.

        Args:
            width: A width name from the preset (e.g. ``"double"``) or a length:
                a number in inches or text like ``"89mm"``, ``"600px"``.
            height: Length: a number in inches or text like ``"60mm"``.
            scale_text: Grow text with the width (relative to the preset's
                default width) instead of keeping point sizes, which is what
                print needs. May break the preset's font limits; a warning says
                so, and ``sp.config.enforce_limits = True`` applies them.
        """
        if width is not None:
            self._width = width
        if height is not None:
            self._height = height
        if scale_text is not None:
            self._scale_text = scale_text
        return self._changed()

    def theme(self, theme: Theme | str | None = None, **overrides: Any) -> Self:
        """Switch theme and/or override individual style fields, e.g.
        ``.theme("dark", font_size=8, grid="none")``.

        Args:
            theme: Theme name (``sp.list_themes()``) or a ``Theme`` object.
            **overrides: Individual style fields, e.g. ``font_size=8``.
                ``sp.theme_options()`` lists every field and its allowed values.
        """
        if isinstance(theme, str):
            get_theme(theme)
        if theme is not None:
            self._theme = theme
        unknown = set(overrides) - set(STYLE_FIELDS)
        if unknown:
            raise TypeError(
                f"Unknown style field(s): {sorted(unknown)}. "
                "See SecretPlots.theme_options() for the full list."
            )
        for key, value in overrides.items():
            self._overrides[key] = coerce_theme_field(key, value)
        return self._changed()

    def colors(
        self,
        colors: str | Sequence[str] | Mapping[Any, str] | None = None,
        *,
        alpha: float | None = None,
    ) -> Self:
        """Colors for the bars or groups. Arguments left out keep their
        current value.

        Args:
            colors: A palette (list of colors), one color for everything, or a
                mapping ``{category or group: color}``.
            alpha: Opacity of those colors, 0 (invisible) to 1 (solid). Plots
                that are already see-through (scatter markers, layered
                histograms) get this much more transparent.
        """
        if alpha is not None:
            if not 0 <= alpha <= 1:
                raise ValueError("alpha must be between 0 and 1")
            self._color_alpha = float(alpha)
        if colors is None:
            pass
        elif isinstance(colors, Mapping):
            self._color_map.update(colors)
        elif isinstance(colors, str):
            self._overrides["palette"] = (colors,)
            self._overrides["primary"] = colors
        else:
            self._overrides["palette"] = tuple(colors)
        return self._changed()

    def highlight(self, *names: Any) -> Self:
        """Emphasize some categories (or groups); everything else is muted.

        Args:
            *names: Categories or groups to emphasize.
        """
        self._highlight = names
        return self._changed()

    def xlim(self, low: float | None = None, high: float | None = None) -> Self:
        """Limits of the x axis (as drawn).

        Args:
            low: Lower limit; ``None`` leaves it automatic.
            high: Upper limit; ``None`` leaves it automatic.
        """
        self._limits["x"] = (low, high)
        return self._changed()

    def ylim(self, low: float | None = None, high: float | None = None) -> Self:
        """Limits of the y axis (as drawn).

        Args:
            low: Lower limit; ``None`` leaves it automatic.
            high: Upper limit; ``None`` leaves it automatic.
        """
        self._limits["y"] = (low, high)
        return self._changed()

    def log(self, axis: str = "y") -> Self:
        """Logarithmic axis scale.

        Args:
            axis: ``"x"``, ``"y"`` or ``"xy"`` (axes as drawn).
        """
        if not isinstance(axis, str) or not axis or set(axis) - {"x", "y"}:
            raise ValueError(f"log axis must be 'x', 'y' or 'xy', got {axis!r}")
        self._log_axes.update(axis)
        return self._changed()

    def refline(
        self,
        *values: Any,
        axis: RefAxis | None = None,
        label: bool | str = False,
        color: str | None = None,
        linestyle: str = "--",
        linewidth: float | None = None,
        label_position: Literal["start", "center", "end"] = "end",
        label_rotation: float = 0,
        label_side: Literal["left", "right", "above", "below"] | None = None,
    ) -> Self:
        """Reference lines across the plot, like matplotlib's ``axhline``
        (``axis="y"``) and ``axvline`` (``axis="x"``). Each call adds lines, so
        calls can differ in style; ``.refline()`` without values removes them.

        Args:
            *values: Positions: numbers, dates (on a date axis, also as text
                like ``"2024-03-01"``) or category names (on a category axis).
                Histograms also take ``"mean"`` and ``"median"``.
            axis: ``"y"`` for horizontal lines, ``"x"`` for vertical ones (axes
                as drawn). Default: the value axis (y for vertical bars, boxes,
                violins, lines and scatter plots; the binned axis of a
                histogram). Heatmaps need it: ``"y"`` rows, ``"x"`` columns.
            label: ``True`` writes the value next to each line; text writes
                that text instead (one value per call).
            color: Line color (default: the theme's text color).
            linestyle: ``"--"`` (default), ``":"``, ``"-."`` or ``"-"``.
            linewidth: Line width in pt (default: the theme's
                ``axis_line_width``).
            label_position: Where along the line the label sits: ``"end"``
                (default; the top of a vertical line, the right end of a
                horizontal one), ``"start"`` (bottom / left) or ``"center"``.
            label_rotation: Label angle in degrees, counter-clockwise (``90``
                runs the label up along a vertical line).
            label_side: Which side of the line the label sits on: ``"right"``
                (default) or ``"left"`` of a vertical line, ``"above"``
                (default) or ``"below"`` a horizontal one.
        """
        if axis not in (None, "x", "y"):
            raise ValueError("refline axis must be 'x', 'y' or None (the value axis)")
        if label_position not in ("start", "center", "end"):
            raise ValueError(
                f"Unknown refline label_position {label_position!r}; use "
                "'start', 'center' or 'end'"
            )
        if not _is_number(label_rotation):
            raise TypeError("refline label_rotation must be a number (degrees)")
        if label_side is not None:
            sides = {"x": ("left", "right"), "y": ("above", "below")}[
                axis or self._refline_axis()
            ]
            if label_side not in sides:
                kind = "vertical" if sides[0] == "left" else "horizontal"
                raise ValueError(
                    f"refline label_side {label_side!r} doesn't fit a {kind} "
                    f"line; use {sides[0]!r} or {sides[1]!r}"
                )
        if not values:
            self._reflines = [
                r
                for r in self._reflines
                if axis is not None and (r.axis or self._refline_axis()) != axis
            ]
            return self._changed()
        for value in values:
            if not (
                _is_number(value)
                or isinstance(value, str | pd.Timestamp | np.datetime64 | date)
                or (isinstance(value, Hashable) and not isinstance(value, bool))
            ):
                raise TypeError(
                    f"refline value {value!r} must be a number, a date or a "
                    "category name"
                )
            if _is_number(value) and not math.isfinite(value):
                raise ValueError(f"refline value must be finite, got {value!r}")
            if value is pd.NaT or (
                isinstance(value, np.datetime64) and np.isnat(value)
            ):
                raise ValueError("refline value must be a date, got NaT")
        for value in values:
            words = self._refline_words
            if isinstance(value, str) and words and value not in words:
                close = difflib.get_close_matches(value, words, n=1)
                if close:
                    raise ValueError(
                        f"Unknown refline {value!r}. Did you mean {close[0]!r}?"
                    )
        if isinstance(label, str) and len(values) > 1:
            raise ValueError(
                "label as text names one line; call .refline() once per value"
            )
        if color is not None:
            try:
                to_rgba(color)
            except ValueError:
                raise ValueError(f"Unknown refline color {color!r}") from None
        try:
            Line2D([], [], linestyle=linestyle)  # type: ignore[arg-type]
        except ValueError:
            raise ValueError(
                f"Unknown linestyle {linestyle!r}; use '--', ':', '-.' or '-'"
            ) from None
        if linewidth is not None and not (linewidth >= 0 and math.isfinite(linewidth)):
            raise ValueError(f"refline linewidth must be 0 or more, got {linewidth!r}")
        self._reflines += [
            _RefLine(
                v,
                axis,
                label,
                color,
                linestyle,
                linewidth,
                label_position,
                float(label_rotation),
                label_side,
            )
            for v in values
        ]
        return self._changed()

    @classmethod
    def options(cls, verb: str | None = None) -> pd.DataFrame:
        """What you can chain on this plot, and what each step accepts.

        >>> sp.bar(df).options()            # doctest: +SKIP
        >>> sp.bar(df).options("legend")    # doctest: +SKIP
        >>> sp.BarPlot.options("labels")    # doctest: +SKIP
        """
        verbs = _verbs(cls)
        if verb is None:
            rows = [
                {
                    "verb": name,
                    "options": ", ".join(_param_names(fn)),
                    "description": _summary(fn),
                }
                for name, fn in verbs.items()
            ]
            return pd.DataFrame(rows).set_index("verb")
        if verb not in verbs:
            close = difflib.get_close_matches(verb, verbs, n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise ValueError(
                f"{cls.__name__} has no step {verb!r}.{hint} "
                f"Available: {', '.join(verbs)}"
            )
        fn = verbs[verb]
        return _parameter_table(fn, list(inspect.signature(fn).parameters.values())[1:])

    @classmethod
    def arguments(cls, argument: str | None = None) -> pd.DataFrame:
        """What you pass when creating this plot (``data``, ``x``, ``hue``,
        ``error``...), with allowed values, defaults and descriptions.

        :meth:`options` lists the steps you chain afterwards.

        >>> sp.BarPlot.arguments()             # doctest: +SKIP
        >>> sp.bar(df).arguments("error")      # doctest: +SKIP
        """
        if cls._constructor is None:
            raise TypeError(
                f"{cls.__name__} is not created directly; ask a plot type, "
                "such as sp.BarPlot.arguments()."
            )
        fn = getattr(sys.modules[cls.__module__], cls._constructor)
        table = _parameter_table(fn, list(inspect.signature(fn).parameters.values()))
        if argument is None:
            return table
        if argument not in table.index:
            close = difflib.get_close_matches(argument, table.index, n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise ValueError(
                f"sp.{cls._constructor}() has no argument {argument!r}.{hint} "
                f"Available: {', '.join(table.index)}"
            )
        return table.loc[[argument]]

    # ------------------------------------------------------------ resolution
    def style(self) -> Style:
        """The fully resolved style this plot will be drawn with."""
        selection = self._selection
        preset = presets.get(self._preset) if self._preset else selection.preset_obj()
        if self._theme is None:
            theme = selection.theme_obj()
        else:
            theme = (
                get_theme(self._theme) if isinstance(self._theme, str) else self._theme
            )
        width = self._width
        if width is None and self._preset is None:
            width = selection.width
        return resolve(
            self.kind,
            preset=preset,
            theme=theme,
            overrides=Theme(name="plot", **self._overrides),
            width=width,
            height=self._height,
            scale_text=self._scale_text,
        )

    def explain(self, field: str) -> str:
        """Which value a style field resolved to and where it came from."""
        return self.style().explain(field)

    def style_report(self) -> str:
        return self.style().report()

    # ------------------------------------------------------------- rendering
    @abstractmethod
    def _draw(self, ax: Axes, style: Style) -> None:
        """Draw marks on ``ax``."""

    def _default_labels(self) -> dict[str, str | None]:
        return {}

    def _adapt(  # noqa: B027  (optional hook; default does nothing)
        self, fig: Figure, ax: Axes, style: Style, renderer: RendererBase
    ) -> None:
        """Adjust to the laid-out size (rotate labels, hide what doesn't fit)."""

    def _render_into(self, fig: Figure, ax: Axes, style: Style, *, own: bool) -> None:
        self._legend_kwargs = None
        self._legend_side = None
        self._legend_wrap = False
        if not own:
            _restyle_axes(ax, style)
        self._draw(ax, style)
        if not self._reflines_in_draw:
            self._draw_reflines(ax, style)
        self._finish_axes(ax, style)
        if own:
            apply_chrome(fig, style, self._chrome)
        # Fit oversized legends before constrained layout sees them; otherwise
        # an initial many-column legend can collapse the axes to zero width.
        self._fit_legend(fig, ax, _renderer(fig))
        fig.draw_without_rendering()
        renderer = _renderer(fig)
        self._clear_axis_decorations(fig, ax, renderer)
        self._fit_legend(fig, ax, renderer)
        self._adapt(fig, ax, style, renderer)
        self._figure, self._axes, self._style = fig, ax, style

    def render(self, ax: Axes | None = None) -> Figure:
        """Draw now. With ``ax``, draw into an existing matplotlib axes (size and
        chrome are then up to you)."""
        style = self.style()
        with style.rc_context():
            if ax is None:
                fig = Figure(figsize=style.figsize, layout="constrained")
                FigureCanvasAgg(fig)
                self._render_into(fig, fig.add_subplot(), style, own=True)
            else:
                fig = _root_figure(ax)
                self._render_into(fig, ax, style, own=False)
        return fig

    @property
    def fig(self) -> Figure:
        if self._figure is None:
            self.render()
        assert self._figure is not None
        return self._figure

    @property
    def ax(self) -> Axes:
        if self._axes is None:
            self.render()
        assert self._axes is not None
        return self._axes

    def save(
        self, path: str | PathLike[str], *, dpi: float | None = None, **kwargs: Any
    ) -> Self:
        """Save using the preset's dpi; fonts are embedded (TrueType) in PDF/PS.

        Args:
            path: Output file; the extension picks the format.
            dpi: Resolution for raster formats; defaults to the preset's dpi.
            **kwargs: Passed on to matplotlib's ``Figure.savefig``.
        """
        fig = self.fig
        assert self._style is not None
        style = self._style
        suffix = Path(path).suffix.lstrip(".").lower()
        if suffix and suffix not in style.target.formats:
            emit(
                FormatWarning,
                f"Preset {style.preset.name!r} expects "
                f"{', '.join(style.target.formats)}; "
                f"saving .{suffix} anyway.",
            )
        with style.rc_context():
            fig.savefig(path, dpi=dpi or style.target.dpi, **kwargs)
        return self

    def show(self) -> None:
        """Display in a window (or inline) through pyplot."""
        import matplotlib.pyplot as plt

        style = self.style()
        with style.rc_context():
            fig = plt.figure(figsize=style.figsize, layout="constrained")
            self._render_into(fig, fig.add_subplot(), style, own=True)
        plt.show()

    def _repr_png_(self) -> tuple[bytes, dict[str, int]]:
        fig = self.fig
        assert self._style is not None
        buffer = io.BytesIO()
        with self._style.rc_context():
            fig.savefig(buffer, format="png", dpi=self._style.target.px_per_inch * 2)
        css_width = round(self._style.width * self._style.target.px_per_inch)
        return buffer.getvalue(), {"width": css_width}

    # ------------------------------------------------------ reference lines
    def _refline_axis(self) -> RefAxis:
        """Axis (as drawn) of reference lines without ``axis=``."""
        return "y"

    def _refline_categories(self, axis: RefAxis) -> Mapping[Any, float] | None:
        """``{category: position}`` when ``axis`` shows categories."""
        return None

    def _refline_items(
        self, ref: _RefLine, axis: RefAxis, style: Style
    ) -> list[tuple[Any, str | None, str]]:
        """``(value, color, text)`` of each line one requested value draws
        (statistics such as a histogram's ``"median"`` may draw one per group)."""
        return [(ref.value, None, _ref_text(ref.value))]

    def _refline_position(self, ax: Axes, axis: RefAxis, value: Any) -> Any:
        """Data position of ``value`` on ``axis``."""
        categories = self._refline_categories(axis)
        if (
            categories is not None
            and isinstance(value, Hashable)
            and value in categories
        ):
            return categories[value]
        target = ax.xaxis if axis == "x" else ax.yaxis
        if _is_number(value):
            return float(value)
        if isinstance(value, str | pd.Timestamp | np.datetime64 | date) and (
            _is_date_axis(target)
        ):
            try:
                stamp = pd.Timestamp(value)
            except ValueError:
                raise DataShapeError(
                    f"refline {value!r} is not a date this axis understands"
                ) from None
            return target.convert_units(stamp)  # type: ignore[no-untyped-call]
        if categories:
            shown = ", ".join(map(str, categories))
            close = difflib.get_close_matches(
                str(value), list(map(str, categories)), n=1
            )
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise DataShapeError(
                f"refline {value!r} is not a category on the {axis} axis.{hint} "
                f"Categories: {shown}"
            )
        words = "".join(f", {w!r}" for w in self._refline_words)
        raise DataShapeError(
            f"refline {value!r} on the {axis} axis must be a number"
            + (" or a date" if _is_date_axis(target) else "")
            + (f" (or one of {words[2:]})" if words else "")
        )

    def _draw_reflines(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        for ref in self._reflines:
            axis = ref.axis or self._refline_axis()
            items = self._refline_items(ref, axis, style)
            for i, (value, item_color, text) in enumerate(items):
                position = self._refline_position(ax, axis, value)
                color = ref.color or item_color or theme.text_color or "#333333"
                draw = ax.axvline if axis == "x" else ax.axhline
                draw(
                    position,
                    color=color,
                    lw=theme.axis_line_width
                    if ref.linewidth is None
                    else checked_size(
                        style, "refline linewidth", ref.linewidth, "line"
                    ),
                    ls=ref.linestyle,
                    zorder=self._refline_zorder,
                )
                if not ref.label:
                    continue
                vertical = axis == "x"
                step = style.sizes.tick * 1.3
                # One value can draw several lines (a median per group):
                # stack their labels so close lines stay readable.
                stack = step * i
                along, align, offset = {
                    "start": (0.0, "bottom" if vertical else "left", 2),
                    "center": (0.5, "center", 0),
                    "end": (1.0, "top" if vertical else "right", -2),
                }[ref.label_position]
                if vertical:
                    left = ref.label_side == "left"
                    xy = (position, along)
                    xytext = (
                        -2 if left else 2,
                        offset - stack if offset <= 0 else offset + stack,
                    )
                    ha, va = "right" if left else "left", align
                else:
                    below = ref.label_side == "below"
                    xy = (along, position)
                    xytext = (offset, -2 - stack if below else 2 + stack)
                    ha, va = align, "top" if below else "bottom"
                ax.annotate(
                    ref.label if isinstance(ref.label, str) else text,
                    xy=xy,
                    xycoords=ax.get_xaxis_transform()
                    if vertical
                    else ax.get_yaxis_transform(),
                    xytext=xytext,
                    textcoords="offset points",
                    ha=ha,
                    va=va,
                    rotation=ref.label_rotation,
                    fontsize=style.sizes.tick,
                    color=color,
                )

    # --------------------------------------------------------------- helpers
    def _finish_axes(self, ax: Axes, style: Style) -> None:
        defaults = self._default_labels()
        show_defaults = bool(style.theme.axis_titles)
        for key, setter in (("x", ax.set_xlabel), ("y", ax.set_ylabel)):
            label = self._labels.get(key, defaults.get(key) if show_defaults else None)
            if label:
                setter(label)
        if self._labels.get("title"):
            ax.set_title(self._labels["title"])
        for axis, (low, high) in self._limits.items():
            (ax.set_xlim if axis == "x" else ax.set_ylim)(low, high)
        if "x" in self._log_axes:
            ax.set_xscale("log")
        if "y" in self._log_axes:
            ax.set_yscale("log")
        for axis, options in self._axis_formats.items():
            kind, decimals, prefix, suffix, scale, date_format = options
            target = ax.xaxis if axis == "x" else ax.yaxis
            if kind == "date":
                if not _is_date_axis(target):
                    raise DataShapeError("Date formatting needs a datetime axis")
                target.set_major_formatter(DateFormatter(date_format or "%Y-%m-%d"))  # type: ignore[no-untyped-call]
            else:
                if self._refline_categories(axis) is not None or _is_date_axis(target):
                    raise DataShapeError("Numeric formatting needs a numeric axis")
                factor = scale * (100 if kind == "percent" else 1)
                before = prefix or ("$" if kind == "currency" else "")
                after = ("%" if kind == "percent" else "") + suffix

                def tick_label(
                    value: float,
                    pos: float,
                    factor: float = factor,
                    before: str = before,
                    after: str = after,
                    digits: int = decimals,
                ) -> str:
                    return f"{before}{value * factor:,.{digits}f}{after}"

                target.set_major_formatter(FuncFormatter(tick_label))
        # A plot that fixes its data aspect (square heatmap cells) keeps it.
        aspect = style.theme.aspect
        if isinstance(aspect, float) and ax.get_aspect() == "auto":
            ax.set_box_aspect(aspect)

    def _group_colors(
        self, style: Style, groups: list[Any], *, grouped: bool
    ) -> dict[Any, str]:
        """Palette colors per ``hue`` group (``{None: primary}`` without groups),
        with ``.colors()`` mappings and ``.highlight()`` applied."""
        theme = style.theme
        highlight = set(self._highlight)
        if highlight and not grouped:
            raise DataShapeError(
                f"highlight() picks hue= groups; this {self.kind} plot has no groups"
            )
        unknown = highlight - set(groups)
        if unknown:
            raise DataShapeError(
                f"Cannot highlight {sorted(map(str, unknown))}: not a group. "
                f"Groups: {', '.join(map(str, groups))}"
            )
        if not grouped:
            return {None: self._faded(theme.primary or "#4589ff")}
        base = extend_palette(
            theme.palette or (),
            len(groups),
            background=theme.background or "#ffffff",
            source=f"the palette from {style.provenance['palette']}",
        )
        colors = {g: self._color_map.get(g, base[i]) for i, g in enumerate(groups)}
        if highlight:
            muted = theme.muted or "#c6c6c6"
            colors = {
                g: self._highlighted(theme, g, c, len(highlight))
                if g in highlight
                else muted
                for g, c in colors.items()
            }
        return {g: self._faded(c) for g, c in colors.items()}

    def _highlighted(self, theme: Theme, key: Any, own: str, count: int) -> str:
        """Color of a highlighted group: the theme's highlight color, as
        without groups, unless several are highlighted (they keep their own
        colors to stay apart) or ``.colors()`` names it."""
        if count > 1 or key in self._color_map:
            return own
        return theme.highlight or own

    def _category_color_fn(
        self, style: Style, groups: Sequence[Any], cats: Sequence[Any], *, grouped: bool
    ) -> Callable[[Any, Any], str]:
        """Color of each ``(group, category)`` mark in categorical plots: palette
        colors per ``hue`` group, or the primary color (``.colors({category:
        ...})`` per category) without groups. ``.highlight()`` may name groups
        or categories."""
        theme = style.theme
        highlight = set(self._highlight)
        unknown = highlight - set(groups) - set(cats)
        if unknown:
            raise DataShapeError(
                f"Cannot highlight {sorted(map(str, unknown))}: not in the data"
            )
        muted = theme.muted or "#c6c6c6"
        color: Callable[[Any, Any], str]
        if grouped:
            base = extend_palette(
                theme.palette or (),
                len(groups),
                background=theme.background or "#ffffff",
                source=f"the palette from {style.provenance['palette']}",
            )
            mapping = {g: self._color_map.get(g, base[i]) for i, g in enumerate(groups)}
            if highlight:
                picked = len(highlight & set(groups))

                def color(g: Any, c: Any) -> str:
                    if g in highlight:
                        return self._highlighted(theme, g, mapping[g], picked)
                    # A highlighted category keeps its groups apart.
                    return mapping[g] if c in highlight else muted

            else:

                def color(g: Any, c: Any) -> str:
                    return mapping[g]

        else:
            primary = theme.primary or "#4589ff"
            accent = theme.highlight or primary
            # A palette given to .colors() colors the categories in order; a
            # single color still colors all of them.
            per_category = dict.fromkeys(cats, primary)
            if len(self._overrides.get("palette", ())) > 1:
                palette = extend_palette(
                    self._overrides["palette"],
                    len(cats),
                    background=theme.background or "#ffffff",
                    source="the colors given to .colors()",
                )
                per_category = dict(zip(cats, palette, strict=False))
            if highlight:

                def color(g: Any, c: Any) -> str:
                    return self._color_map.get(c, accent) if c in highlight else muted

            else:

                def color(g: Any, c: Any) -> str:
                    return self._color_map.get(c, per_category.get(c, primary))

        return lambda g, c: self._faded(color(g, c))

    def _faded(self, color: str) -> str:
        """``color`` with the ``.colors(alpha=...)`` opacity applied."""
        return with_alpha(color, self._color_alpha)

    def _legend_position(self, style: Style, n: int) -> LegendPosition:
        position = self._legend or style.theme.legend_position or "auto"
        if position == "auto":
            position = "top" if n <= 4 or style.width < 4.5 else "right"
        if position == "top" and self._labels.get("title"):
            position = "right"
        return position

    def _draw_legend(
        self, ax: Axes, style: Style, *, n: int, title: str | None
    ) -> None:
        position = self._legend_position(style, n)
        if position == "none":
            return
        kwargs: dict[str, Any] = {
            "title": _legend_title(title) if style.theme.legend_title else None,
            "frameon": style.theme.legend_frame,
            "handlelength": self._handle_length,
            "handleheight": 1.0,
            "borderaxespad": 0.0,
            "alignment": "left",
        }
        if position == "top":
            kwargs |= {"loc": "lower left", "ncols": n}
            kwargs |= _outside_anchor(ax, "top", _LEGEND_GAP_IN)
        elif position == "right":
            kwargs |= {"loc": "upper left"}
            kwargs |= _outside_anchor(ax, "right", _LEGEND_GAP_IN)
        else:
            kwargs |= {"loc": "best"}

        options = self._legend_options
        if options.get("title") is not None:
            kwargs["title"] = options["title"] or None
        if options.get("ncols") is not None:
            kwargs["ncols"] = options["ncols"]
        if options.get("fontsize") is not None:
            size = checked_size(style, "legend fontsize", options["fontsize"], "font")
            kwargs["fontsize"] = kwargs["title_fontsize"] = size
        if options.get("anchor") is not None:
            kwargs["bbox_to_anchor"] = options["anchor"]
            kwargs["bbox_transform"] = ax.transAxes
            if position == "inside":
                # "best" is meaningless relative to a single anchor point.
                kwargs["loc"] = "upper left"
        if options.get("loc") is not None:
            kwargs["loc"] = options["loc"]
        ax.legend(**kwargs)

        self._legend_kwargs = kwargs
        moved = options.get("loc") is not None or options.get("anchor") is not None
        if position in ("top", "right") and not moved:
            self._legend_side = position
        self._legend_wrap = (
            position == "top" and not moved and options.get("ncols") is None
        )

    def _fit_category_labels(
        self, fig: Figure, ax: Axes, renderer: RendererBase, rotation: float | None
    ) -> None:
        """Rotate category labels on the x axis (45 or 90 degrees) when they
        overlap, unless ``rotation`` was set by the user."""
        labels = [t for t in ax.get_xticklabels() if t.get_text()]
        if not labels or rotation is not None:
            return
        slot = ax.get_window_extent(renderer).width / len(labels)
        widest = max(t.get_window_extent(renderer).width for t in labels)
        if widest <= slot * 0.95:
            return
        line_height = max(t.get_window_extent(renderer).height for t in labels)
        steep = slot < line_height * 1.6
        for t in labels:
            t.set_rotation(90 if steep else 45)
            t.set_horizontalalignment("center" if steep else "right")
            t.set_rotation_mode("default" if steep else "anchor")
        fig.draw_without_rendering()

    def _clear_axis_decorations(
        self, fig: Figure, ax: Axes, renderer: RendererBase
    ) -> None:
        """Move an outside legend past tick labels and axis titles on its side
        (e.g. a value axis drawn on the right)."""
        side, kwargs, legend = self._legend_side, self._legend_kwargs, ax.get_legend()
        if side is None or kwargs is None or legend is None:
            return
        boxes = [b for a in (ax.xaxis, ax.yaxis) if (b := a.get_tightbbox(renderer))]
        if side == "right":
            overhang = max((b.x1 for b in boxes), default=0.0) - ax.bbox.x1
        else:
            overhang = max((b.y1 for b in boxes), default=0.0) - ax.bbox.y1
        if overhang <= 1:  # pixels
            return
        kwargs |= _outside_anchor(ax, side, _LEGEND_GAP_IN + overhang / fig.dpi)
        legend.remove()
        ax.legend(**kwargs)
        fig.draw_without_rendering()

    def _fit_legend(self, fig: Figure, ax: Axes, renderer: RendererBase) -> None:
        """Wrap a top legend into fewer columns until it fits inside the figure."""
        kwargs = self._legend_kwargs
        if kwargs is None or not self._legend_wrap:
            return
        # The legend starts at the axes' left edge, so check where it ends.
        limit = fig.bbox.x1 - fig.bbox.width * 0.02
        ncols = int(kwargs["ncols"])
        while ncols > 1:
            legend = ax.get_legend()
            if legend is None or legend.get_window_extent(renderer).x1 <= limit:
                return
            ncols -= 1
            legend.remove()
            kwargs["ncols"] = ncols
            ax.legend(**kwargs)
