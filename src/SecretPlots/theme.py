"""Themes: how a figure looks (fonts, colors, lines, grid).

A :class:`Theme` is *partial*: every field may be ``None``, meaning "not decided
here, ask the next layer". Only the built-in ``"secret"`` base theme sets every
field, so style resolution always ends with a complete value. See
:mod:`SecretPlots.core.merge` for the cascade.
"""

import difflib
from dataclasses import dataclass, fields
from typing import Literal

from SecretColors import Palette

from SecretPlots.errors import PresetNotFoundError

GridMode = Literal["none", "value", "category", "both"]
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
