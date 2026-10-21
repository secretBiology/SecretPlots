"""Base class shared by every plot: chaining verbs, lazy rendering, saving."""

import io
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from os import PathLike
from pathlib import Path
from typing import Any, ClassVar, Self

from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from SecretPlots import presets
from SecretPlots.core import state
from SecretPlots.core.chrome import ChromeText, apply_chrome
from SecretPlots.core.resolve import Style, resolve
from SecretPlots.core.units import Length
from SecretPlots.errors import FormatWarning, emit
from SecretPlots.theme import STYLE_FIELDS, LegendPosition, Theme, get_theme

_LEGEND_POSITIONS = ("auto", "top", "right", "inside", "none")


def _renderer(fig: Figure) -> RendererBase:
    get = getattr(fig.canvas, "get_renderer", None)
    if callable(get):
        renderer: RendererBase = get()
        return renderer
    return fig._get_renderer()  # type: ignore[attr-defined, no-any-return]


class Plot(ABC):
    """A lazily drawn figure. Verbs return the plot so calls can be chained;
    nothing is drawn until :meth:`show`, :meth:`save`, ``.fig``/``.ax`` or
    notebook display."""

    kind: ClassVar[str] = "plot"

    def __init__(self) -> None:
        self._overrides: dict[str, Any] = {}
        self._labels: dict[str, str] = {}
        self._legend: LegendPosition | None = None
        self._chrome = ChromeText()
        self._preset: str | None = None
        self._theme: Theme | str | None = None
        self._width: Length | None = None
        self._height: Length | None = None
        self._limits: dict[str, tuple[float | None, float | None]] = {}
        self._log_axes: set[str] = set()
        self._highlight: tuple[Any, ...] = ()
        self._color_map: dict[Any, str] = {}

        self._figure: Figure | None = None
        self._axes: Axes | None = None
        self._style: Style | None = None
        self._legend_kwargs: dict[str, Any] | None = None

    # ----------------------------------------------------------------- verbs
    def _changed(self) -> Self:
        self._figure = self._axes = self._style = None
        return self

    def labels(
        self, *, x: str | None = None, y: str | None = None, title: str | None = None
    ) -> Self:
        """Axis titles and plot title. Pass ``""`` to hide an automatic label."""
        for key, value in (("x", x), ("y", y), ("title", title)):
            if value is not None:
                self._labels[key] = value
        return self._changed()

    def legend(self, position: LegendPosition | bool = "auto") -> Self:
        """``"auto"``, ``"top"``, ``"right"``, ``"inside"``, or ``False``/``"none"``."""
        if position is True:
            position = "auto"
        elif position is False:
            position = "none"
        if position not in _LEGEND_POSITIONS:
            raise ValueError(f"legend position must be one of {_LEGEND_POSITIONS}")
        self._legend = position
        return self._changed()

    def chrome(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        source: str | None = None,
        note: str | None = None,
    ) -> Self:
        """Headline/subtitle above the plot and note/source line below it."""
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
        """Use a preset for this plot only: ``.preset("nature", width="double")``."""
        presets.get(name)
        self._preset = name
        self._width, self._height = width, height
        return self._changed()

    def size(self, width: Length | None = None, height: Length | None = None) -> Self:
        """Width (preset width name or length) and/or height (length)."""
        if width is not None:
            self._width = width
        if height is not None:
            self._height = height
        return self._changed()

    def theme(self, theme: Theme | str | None = None, **overrides: Any) -> Self:
        """Switch theme and/or override individual style fields, e.g.
        ``.theme("dark", font_size=8, grid="none")``."""
        if isinstance(theme, str):
            get_theme(theme)
        if theme is not None:
            self._theme = theme
        unknown = set(overrides) - set(STYLE_FIELDS)
        if unknown:
            raise TypeError(f"Unknown style field(s): {sorted(unknown)}")
        for key, value in overrides.items():
            if isinstance(value, list):
                value = tuple(value)
            self._overrides[key] = value
        return self._changed()

    def colors(self, colors: str | Sequence[str] | Mapping[Any, str]) -> Self:
        """A palette (list), one color for everything (str), or a mapping from
        category/group to color."""
        if isinstance(colors, Mapping):
            self._color_map.update(colors)
        elif isinstance(colors, str):
            self._overrides["palette"] = (colors,)
            self._overrides["primary"] = colors
        else:
            self._overrides["palette"] = tuple(colors)
        return self._changed()

    def highlight(self, *names: Any) -> Self:
        """Emphasize these categories (or groups); everything else is muted."""
        self._highlight = names
        return self._changed()

    def xlim(self, low: float | None = None, high: float | None = None) -> Self:
        self._limits["x"] = (low, high)
        return self._changed()

    def ylim(self, low: float | None = None, high: float | None = None) -> Self:
        self._limits["y"] = (low, high)
        return self._changed()

    def log(self, axis: str = "y") -> Self:
        """Logarithmic ``"x"``, ``"y"`` or ``"xy"`` axis."""
        self._log_axes.update(axis)
        return self._changed()

    # ------------------------------------------------------------ resolution
    def style(self) -> Style:
        """The fully resolved style this plot will be drawn with."""
        selection = state.current()
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
        self._draw(ax, style)
        self._finish_axes(ax, style)
        if own:
            apply_chrome(fig, style, self._chrome)
        fig.draw_without_rendering()
        renderer = _renderer(fig)
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
                root = ax.get_figure(root=True)
                if not isinstance(root, Figure):
                    raise ValueError("ax is not attached to a figure")
                fig = root
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
        """Save using the preset's dpi; fonts are embedded (TrueType) in PDF/PS."""
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
            "title": title if style.theme.legend_title else None,
            "frameon": style.theme.legend_frame,
            "handlelength": 1.0,
            "handleheight": 1.0,
            "borderaxespad": 0.0,
            "alignment": "left",
        }
        if position == "top":
            kwargs |= {"loc": "lower left", "bbox_to_anchor": (0, 1.02), "ncols": n}
        elif position == "right":
            kwargs |= {"loc": "upper left", "bbox_to_anchor": (1.02, 1)}
        else:
            kwargs |= {"loc": "best"}
        ax.legend(**kwargs)
        self._legend_kwargs = kwargs

    def _fit_legend(self, fig: Figure, ax: Axes, renderer: RendererBase) -> None:
        """Wrap a top legend into fewer columns until it fits the figure width."""
        kwargs = self._legend_kwargs
        if kwargs is None or kwargs.get("loc") != "lower left":
            return
        limit = fig.bbox.width * 0.98
        ncols = int(kwargs["ncols"])
        while ncols > 1:
            legend = ax.get_legend()
            if legend is None or legend.get_window_extent(renderer).width <= limit:
                return
            ncols -= 1
            legend.remove()
            kwargs["ncols"] = ncols
            ax.legend(**kwargs)
            fig.draw_without_rendering()
