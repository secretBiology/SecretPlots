"""Themes: how a figure looks (fonts, colors, lines, grid).

A :class:`Theme` is *partial*: every field may be ``None``, meaning "not decided
here, ask the next layer". Only the built-in ``"secret"`` base theme sets every
field, so style resolution always ends with a complete value. See
:mod:`SecretPlots.core.merge` for the cascade.
"""

import collections.abc
import difflib
import types
from dataclasses import dataclass, fields
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

import pandas as pd
from SecretColors import Palette

from SecretPlots.errors import PresetNotFoundError

GridMode = Literal["none", "x", "y", "both", "value", "category"]
Side = Literal["left", "bottom", "right", "top"]
LegendPosition = Literal["auto", "top", "right", "inside", "none"]
FontGeneric = Literal["sans-serif", "serif", "monospace"]


@dataclass(frozen=True, kw_only=True)
class Theme:
    """Visual design tokens. ``None`` means "inherit from the next layer".

    Sizes are in points. ``*_scale`` fields are relative to ``font_size``.
    """

    name: str = "custom"

    # Typography
    font_family: tuple[str, ...] | None = None
    font_generic: FontGeneric | None = None
    font_size: float | None = None
    label_scale: float | None = None
    title_scale: float | None = None
    subtitle_scale: float | None = None
    note_scale: float | None = None
    title_weight: str | None = None
    text_color: str | None = None
    muted_text_color: str | None = None

    # Canvas
    background: str | None = None
    axes_background: str | None = None

    # Axes, lines, grid
    line_width: float | None = None
    axis_line_width: float | None = None
    axis_color: str | None = None
    spines: tuple[Side, ...] | None = None
    tick_length: float | None = None
    value_axis_side: Literal["left", "right"] | None = None
    axis_titles: bool | None = None
    grid: GridMode | None = None
    grid_color: str | None = None
    grid_width: float | None = None
    grid_style: str | None = None

    # Colors (semantic roles)
    palette: tuple[str, ...] | None = None
    primary: str | None = None
    highlight: str | None = None
    neutral: str | None = None
    muted: str | None = None
    positive: str | None = None
    negative: str | None = None
    sequential: tuple[str, ...] | None = None
    diverging: tuple[str, ...] | None = None

    # Marks
    bar_gap: float | None = None
    bar_edge_width: float | None = None
    errorbar_capsize: float | None = None
    missing_hatch: str | None = None
    marker: str | None = None
    marker_size: float | None = None
    marker_alpha: float | None = None
    marker_edge_width: float | None = None

    # Legend
    legend_frame: bool | None = None
    legend_position: LegendPosition | None = None
    legend_title: bool | None = None


#: Theme fields that participate in style resolution (everything but ``name``).
STYLE_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(Theme) if f.name != "name")


class _Colors:
    """Typed access to SecretColors' IBM palette (its API returns a union type)."""

    def __init__(self) -> None:
        self._palette = Palette("ibm")

    def __call__(self, name: str, shade: float | None = None) -> str:
        return str(self._palette.get(name, shade=shade))

    def categorical(
        self, n: int = 8, *, background: str = "#ffffff"
    ) -> tuple[str, ...]:
        cycle = self._palette.cycle(colorblind_safe=True, background=background)
        return tuple(str(next(cycle)) for _ in range(n))


def _secret() -> Theme:
    c = _Colors()
    return Theme(
        name="secret",
        font_family=(
            "Inter",
            "Helvetica Neue",
            "Helvetica",
            "Arial",
            "Liberation Sans",
            "DejaVu Sans",
        ),
        font_generic="sans-serif",
        font_size=9.0,
        label_scale=1.1,
        title_scale=1.45,
        subtitle_scale=1.1,
        note_scale=0.85,
        title_weight="bold",
        text_color=c("gray", 90),
        muted_text_color=c("gray", 60),
        background="#ffffff",
        axes_background="#ffffff",
        line_width=1.5,
        axis_line_width=0.8,
        axis_color=c("gray", 70),
        spines=("left", "bottom"),
        tick_length=3.0,
        value_axis_side="left",
        axis_titles=True,
        grid="value",
        grid_color=c("gray", 20),
        grid_width=0.6,
        grid_style="-",
        palette=c.categorical(),
        primary=c("blue"),
        highlight=c("blue"),
        neutral=c("gray", 50),
        muted=c("gray", 30),
        positive=c("green"),
        negative=c("red"),
        sequential=(c("blue", 10), c("blue", 50), c("blue", 90)),
        diverging=(c("red", 60), c("gray", 10), c("blue", 60)),
        bar_gap=0.2,
        bar_edge_width=0.0,
        errorbar_capsize=2.5,
        missing_hatch="////",
        marker="o",
        marker_size=5.0,
        marker_alpha=0.85,
        marker_edge_width=0.5,
        legend_frame=False,
        legend_position="auto",
        legend_title=True,
    )


def _dark() -> Theme:
    c = _Colors()
    bg = c("gray", 100)
    return Theme(
        name="dark",
        text_color=c("gray", 10),
        muted_text_color=c("gray", 40),
        background=bg,
        axes_background=bg,
        axis_color=c("gray", 50),
        grid_color=c("gray", 80),
        palette=c.categorical(background=bg),
        primary=c("blue", 40),
        highlight=c("blue", 40),
        muted=c("gray", 70),
        sequential=(c("blue", 90), c("blue", 50), c("blue", 10)),
        diverging=(c("red", 50), c("gray", 80), c("blue", 50)),
    )


def _print_bw() -> Theme:
    c = _Colors()
    return Theme(
        name="print-bw",
        palette=tuple(c("gray", s) for s in (90, 60, 40, 20)),
        primary=c("gray", 80),
        highlight=c("gray", 100),
        muted=c("gray", 20),
        positive=c("gray", 80),
        negative=c("gray", 40),
        sequential=(c("gray", 10), c("gray", 50), c("gray", 100)),
        diverging=(c("gray", 80), c("gray", 10), c("gray", 80)),
    )


BASE_THEME: Theme = _secret()
_THEMES: dict[str, Theme] = {t.name: t for t in (BASE_THEME, _dark(), _print_bw())}


def get_theme(name: str) -> Theme:
    """Return a registered theme by name."""
    try:
        return _THEMES[name]
    except KeyError:
        close = difflib.get_close_matches(name, _THEMES, n=1)
        hint = f" Did you mean {close[0]!r}?" if close else ""
        raise PresetNotFoundError(
            f"No theme named {name!r}.{hint} Available: {', '.join(sorted(_THEMES))}"
        ) from None


def list_themes() -> list[str]:
    """Names of all registered themes."""
    return sorted(_THEMES)


def register_theme(theme: Theme, *, overwrite: bool = False) -> None:
    """Make ``theme`` available by ``theme.name`` (e.g. in ``sp.use(theme=...)``)."""
    if theme.name in _THEMES and not overwrite:
        raise ValueError(f"Theme {theme.name!r} exists; pass overwrite=True")
    _THEMES[theme.name] = theme


FIELD_DOCS: dict[str, str] = {
    "font_family": "Preferred fonts, in order; the first installed one is used",
    "font_generic": (
        "Generic family used when none of the fonts are installed; set alone "
        "on a plot, it picks a common font of that kind"
    ),
    "font_size": "Base text size in pt (tick labels, legend, values)",
    "label_scale": "Axis title size, relative to font_size",
    "title_scale": "Title size, relative to font_size",
    "subtitle_scale": "Subtitle size, relative to font_size",
    "note_scale": "Source/note line size, relative to font_size",
    "title_weight": "Title weight, e.g. 'bold' or 'normal'",
    "text_color": "Main text color",
    "muted_text_color": "Color of the source and note lines",
    "background": "Figure background color",
    "axes_background": "Plot area background (defaults to background)",
    "line_width": "Width of data lines in pt",
    "axis_line_width": "Width of axis lines and ticks in pt",
    "axis_color": "Color of axis lines and ticks",
    "spines": "Visible frame lines: any of left, bottom, right, top",
    "tick_length": "Tick mark length in pt (0 hides tick marks)",
    "value_axis_side": "Which side the value axis is drawn on",
    "axis_titles": "Show automatic axis titles taken from column names",
    "grid": (
        "Gridlines: 'x' or 'y' (as in matplotlib), 'both', 'none', True/False, "
        "or 'value'/'category' to follow the bars when you switch orientation"
    ),
    "grid_color": "Gridline color",
    "grid_width": "Gridline width in pt",
    "grid_style": "Gridline style: '-', '--', ':' or '-.'",
    "palette": "Colors for groups, in order",
    "primary": "Color of single-series plots (defaults to first palette color)",
    "highlight": "Color of highlighted items (defaults to primary)",
    "neutral": "Neutral grey",
    "muted": "Color of de-emphasized items when highlighting",
    "positive": "Color for positive values / increases",
    "negative": "Color for negative values / decreases",
    "sequential": "Colormap stops for heatmaps, low to high",
    "diverging": "Colormap stops for diverging data: negative, middle, positive",
    "bar_gap": "Empty fraction of each category slot, 0 to 1",
    "bar_edge_width": "Outline width around bars in pt",
    "errorbar_capsize": "Error bar cap length in pt",
    "missing_hatch": "Hatch pattern marking missing values",
    "marker": "Scatter marker shape (matplotlib marker): 'o', 's', '^', 'D', 'x', ...",
    "marker_size": "Scatter marker diameter in pt (base size when size= is used)",
    "marker_alpha": "Scatter marker opacity, 0 (invisible) to 1 (solid)",
    "marker_edge_width": "Outline width around scatter markers in pt",
    "legend_frame": "Draw a box around the legend",
    "legend_position": "Default legend position",
    "legend_title": "Show the legend title",
}


def _describe_type(tp: Any) -> str:
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if float in args and int in args:
            args.remove(int)
        return " | ".join(_describe_type(a) for a in args)
    if origin is Literal:
        return " | ".join(repr(a) for a in get_args(tp))
    if origin is tuple:
        items = get_args(tp)
        if len(items) == 2 and items[1] is Ellipsis:
            return f"list of {_describe_type(items[0])}"
        return "(" + ", ".join(_describe_type(a) for a in items) + ")"
    if origin is collections.abc.Sequence:
        return "list"
    if origin is collections.abc.Mapping:
        return "mapping"
    names = {float: "number", int: "integer", str: "text", bool: "True | False"}
    if tp in names:
        return names[tp]
    if tp is Any:
        return "any"
    return getattr(tp, "__name__", str(tp))


def theme_options(theme: Theme | str | None = None) -> pd.DataFrame:
    """Every style option you can pass to ``.theme(...)``.

    Shows the allowed values, a description, and the value in ``theme``
    (default: the built-in ``"secret"`` theme). ``None`` in a partial theme
    means "inherited from the next layer".

    >>> import SecretPlots as sp
    >>> sp.theme_options()            # doctest: +SKIP
    >>> sp.theme_options("dark")      # doctest: +SKIP
    """
    chosen = get_theme(theme) if isinstance(theme, str) else (theme or BASE_THEME)
    hints = get_type_hints(Theme)
    rows = [
        {
            "option": name,
            "allowed": _describe_type(hints[name]),
            "value": getattr(chosen, name),
            "description": FIELD_DOCS[name],
        }
        for name in STYLE_FIELDS
    ]
    return pd.DataFrame(rows).set_index("option")
