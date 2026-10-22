"""Bar plots: simple, grouped and stacked; vertical or horizontal."""

import difflib
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colors import to_hex
from matplotlib.container import BarContainer
from matplotlib.figure import Figure
from matplotlib.text import Text

from SecretPlots.core.colors import extend_palette, readable_on
from SecretPlots.core.data import Tidy, tidy
from SecretPlots.core.plot import Plot
from SecretPlots.core.resolve import Style
from SecretPlots.errors import DataShapeError, LabelsHiddenWarning, emit

Estimator = Literal["mean", "median", "sum"] | Callable[[pd.Series], float]
ErrorKind = Literal["sd", "sem"]
Orient = Literal["v", "h"]
SortOrder = Literal["asc", "desc"]

_Bars = tuple[BarContainer, np.ndarray, np.ndarray | None]
_SPINE_SWAP = {"left": "bottom", "bottom": "left", "right": "top", "top": "right"}


def _formatter(fmt: str) -> Callable[[float], str]:
    template = fmt if "{" in fmt else "{:" + fmt + "}"
    return template.format


_ESTIMATORS = ("mean", "median", "sum")
_ERRORS = ("sd", "sem")
# Common spellings from other tools -> what SecretPlots calls them.
_ERROR_ALIASES = {"std": "sd", "stdev": "sd", "se": "sem", "stderr": "sem"}


def _close(value: str, options: Sequence[str]) -> str:
    match = difflib.get_close_matches(value, options, n=1)
    return f" Did you mean {match[0]!r}?" if match else ""


def _check_error(error: object) -> None:
    if error is None or error in _ERRORS:
        return
    if isinstance(error, str) and error in _ERROR_ALIASES:
        hint = f" Did you mean error={_ERROR_ALIASES[error]!r}?"
    else:
        hint = _close(error, _ERRORS) if isinstance(error, str) else ""
    raise ValueError(
        f"Unknown error={error!r}.{hint} Error bars can be 'sd' (standard "
        "deviation), 'sem' (standard error of the mean) or None."
    )


def _check_estimator(estimator: object) -> None:
    if callable(estimator) or estimator in _ESTIMATORS:
        return
    if isinstance(estimator, str) and (
        estimator in _ERRORS or estimator in _ERROR_ALIASES
    ):
        kind = _ERROR_ALIASES.get(estimator, estimator)
        raise ValueError(
            f"estimator={estimator!r} looks like an error bar. estimator sets the "
            f"bar height ('mean', 'median', 'sum'); for error bars use "
            f"error={kind!r}, e.g. sp.bar(df, x=..., y=..., error={kind!r})."
        )
    hint = _close(estimator, _ESTIMATORS) if isinstance(estimator, str) else ""
    raise ValueError(
        f"Unknown estimator={estimator!r}.{hint} Use 'mean', 'median', 'sum' or "
        "a function that takes the values of one bar, e.g. estimator=np.max."
    )


class BarPlot(Plot):
    """Created by :func:`bar`."""

    kind = "bar"

    def __init__(
        self,
        data: Tidy,
        *,
        stack: bool = False,
        error: ErrorKind | None = None,
        estimator: Estimator = "mean",
        orient: Orient = "v",
        sort: SortOrder | None = None,
    ) -> None:
        super().__init__()
        _check_error(error)
        _check_estimator(estimator)
        if stack and error:
            raise ValueError(
                "Error bars on stacked bars are misleading; use stack=False"
            )
        self._data = data
        self._stack = stack
        self._error = error
        self._estimator = estimator
        self._orient: Orient = "v"
        self._sort: SortOrder | None = None
        self.orient(orient).sort(sort)
        self._value_fmt: Callable[[float], str] | None = None
        self._values_inside: bool | None = None
        self._tick_rotation: float | None = None
        self._tick_italic = False
        self._table = self._aggregate()
        self._value_texts: list[tuple[list[Text], BarContainer]] = []

    # ----------------------------------------------------------------- verbs
    def values(self, fmt: str = ".3g", *, inside: bool | None = None) -> Self:
        """Print each bar's value, e.g. ``.values(".1f")`` or ``.values("{:.0%}")``.
        Labels that don't fit are hidden with a warning.

        Args:
            fmt: Format spec like ``".1f"`` or format string like ``"{:.0%}"``.
            inside: ``True`` puts labels inside the bars, ``False`` above them;
                ``None`` decides automatically (inside only for stacked bars).
        """
        self._value_fmt = _formatter(fmt)
        self._values_inside = inside
        return self._changed()

    def sort(self, order: SortOrder | None = "desc") -> Self:
        """Order categories by value.

        Args:
            order: ``"desc"``, ``"asc"``, or ``None`` to keep data order.
        """
        if order not in (None, "asc", "desc"):
            raise ValueError("sort must be 'asc', 'desc' or None")
        self._sort = order
        return self._changed()

    def orient(self, orient: Orient) -> Self:
        """Bar direction.

        Args:
            orient: ``"v"`` for vertical or ``"h"`` for horizontal bars.
        """
        if orient not in ("v", "h"):
            raise ValueError("orient must be 'v' or 'h'")
        self._orient = orient
        return self._changed()

    def ticklabels(
        self,
        labels: Sequence[Any] | Mapping[Any, Any] | None = None,
        *,
        rotation: float | None = None,
        italic: bool = False,
    ) -> Self:
        """Name the categories and style their labels.

        Args:
            labels: New names as a list in data order
                (``sp.bar([3, 5]).ticklabels(["a", "b"])``) or a mapping
                ``{old: new}``. The categories themselves are renamed, so later
                ``.highlight("a")`` or ``.colors({"a": ...})`` use new names.
            rotation: Label angle in degrees; turns off automatic rotation.
            italic: Italic labels, e.g. for gene names.
        """
        if labels is not None:
            self._data = self._data.rename("x", labels)
            self._table = self._aggregate()
        self._tick_rotation = rotation
        self._tick_italic = italic
        return self._changed()

    def grouplabels(self, labels: Sequence[Any] | Mapping[Any, Any]) -> Self:
        """Name the groups shown in the legend.

        Args:
            labels: New names as a list in data order or a mapping
                ``{old: new}``.
        """
        self._data = self._data.rename("hue", labels)
        self._table = self._aggregate()
        return self._changed()

    # ------------------------------------------------------------------ data
    def _aggregate(self) -> pd.DataFrame:
        keys = ["x", "hue"] if self._data.has_hue else ["x"]
        grouped = self._data.frame.groupby(keys, sort=False, observed=True)["y"]
        table = pd.DataFrame(
            {
                "value": grouped.agg(self._estimator),
                "n": grouped.count(),
                "sd": grouped.std(ddof=1),
            }
        )
        table["sem"] = table["sd"] / np.sqrt(table["n"])
        if self._error and (table["n"] <= 1).all():
            raise DataShapeError(
                f"error={self._error!r} needs replicates (several rows per bar), "
                "but every bar has a single value."
            )
        return table.reset_index()

    def _categories(self) -> list[Any]:
        order = list(self._data.x_order)
        if self._sort is None:
            return order
        by_x = self._table.groupby("x", sort=False, observed=True)["value"]
        totals: dict[Any, float] = (by_x.sum() if self._stack else by_x.max()).to_dict()
        return sorted(
            order, key=lambda c: totals.get(c, -np.inf), reverse=self._sort == "desc"
        )

    def _color_fn(
        self, style: Style, groups: Sequence[Any], cats: Sequence[Any]
    ) -> Callable[[Any, Any], str]:
        color = self._base_color_fn(style, groups, cats)
        return lambda g, c: self._faded(color(g, c))

    def _base_color_fn(
        self, style: Style, groups: Sequence[Any], cats: Sequence[Any]
    ) -> Callable[[Any, Any], str]:
        theme = style.theme
        highlight = set(self._highlight)
        unknown = highlight - set(groups) - set(cats)
        if unknown:
            raise DataShapeError(
                f"Cannot highlight {sorted(map(str, unknown))}: not in the data"
            )
        muted = theme.muted or "#c6c6c6"

        if self._data.has_hue:
            base = extend_palette(
                theme.palette or (),
                len(groups),
                background=theme.background or "#ffffff",
                source=f"the palette from {style.provenance['palette']}",
            )
            mapping = {g: self._color_map.get(g, base[i]) for i, g in enumerate(groups)}
            if highlight:
                return lambda g, c: (
                    mapping[g] if g in highlight or c in highlight else muted
                )
            return lambda g, c: mapping[g]

        primary = theme.primary or "#4589ff"
        if highlight:
            accent = theme.highlight or primary
            return lambda g, c: accent if c in highlight else muted
        return lambda g, c: self._color_map.get(c, primary)

    # --------------------------------------------------------------- drawing
    def _default_labels(self) -> dict[str, str | None]:
        cat, val = self._data.x_name, self._data.y_name
        return {"x": cat, "y": val} if self._orient == "v" else {"x": val, "y": cat}

    def _draw(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        vertical = self._orient == "v"
        cats = self._categories()
        groups: list[Any] = list(self._data.hue_order or [None])
        color = self._color_fn(style, groups, cats)
        positions = np.arange(len(cats), dtype=float)

        span = 1 - (theme.bar_gap or 0)
        grouped = self._data.has_hue and not self._stack
        width = span / len(groups) if grouped else span
        up = np.zeros(len(cats))
        down = np.zeros(len(cats))
        self._value_texts = []
        containers: list[_Bars] = []

        for i, group in enumerate(groups):
            rows = (
                self._table
                if group is None
                else self._table[self._table["hue"] == group]
            )
            rows = rows.set_index("x").reindex(cats)
            values = rows["value"].to_numpy(dtype=float)
            offset = -span / 2 + width * (i + 0.5) if grouped else 0.0
            base = np.where(values >= 0, up, down) if self._stack else 0.0
            kwargs: dict[str, Any] = {
                "color": [color(group, c) for c in cats],
                "label": None if group is None else str(group),
                "linewidth": theme.bar_edge_width,
                "edgecolor": theme.axes_background,
                "zorder": 2,
            }
            if vertical:
                bars = ax.bar(positions + offset, values, width, bottom=base, **kwargs)
            else:
                bars = ax.barh(positions + offset, values, width, left=base, **kwargs)
            errors = rows[self._error].to_numpy(dtype=float) if self._error else None
            containers.append((bars, values, errors))

            if self._stack:
                finite = np.nan_to_num(values)
                up += np.where(finite >= 0, finite, 0)
                down += np.where(finite < 0, finite, 0)
            if errors is not None:
                ax.errorbar(
                    positions + offset if vertical else values,
                    values if vertical else positions + offset,
                    yerr=errors if vertical else None,
                    xerr=None if vertical else errors,
                    fmt="none",
                    ecolor=theme.text_color,
                    elinewidth=theme.axis_line_width,
                    capsize=theme.errorbar_capsize,
                    capthick=theme.axis_line_width,
                    zorder=3,
                )

        self._style_axes(ax, style, cats, positions)
        if self._value_fmt is not None:
            self._draw_values(ax, style, containers)
        if self._data.has_hue:
            self._draw_legend(ax, style, n=len(groups), title=self._data.hue_name)

    def _style_axes(
        self, ax: Axes, style: Style, cats: list[Any], positions: np.ndarray
    ) -> None:
        theme = style.theme
        vertical = self._orient == "v"
        labels = [str(c) for c in cats]
        cat_axis, value_axis = (
            (ax.xaxis, ax.yaxis) if vertical else (ax.yaxis, ax.xaxis)
        )
        if vertical:
            ax.set_xticks(positions, labels=labels)
            ax.set_xlim(-0.5, len(cats) - 0.5)
        else:
            ax.set_yticks(positions, labels=labels)
            ax.set_ylim(len(cats) - 0.5, -0.5)  # first category on top
        ax.tick_params(axis="x" if vertical else "y", length=0)
        for text in ax.get_xticklabels() if vertical else ax.get_yticklabels():
            if self._tick_italic:
                text.set_fontstyle("italic")
            if self._tick_rotation is not None:
                text.set_rotation(self._tick_rotation)
                if vertical and self._tick_rotation % 90:
                    text.set_horizontalalignment("right")
                    text.set_rotation_mode("anchor")
        headroom = 0.12 if self._value_fmt is not None else 0.05
        if vertical:
            ax.margins(y=headroom)
        else:
            ax.margins(x=headroom)

        grid = theme.grid
        if grid in ("both", "value") or grid == ("y" if vertical else "x"):
            value_axis.grid(True)
        if grid in ("both", "category") or grid == ("x" if vertical else "y"):
            cat_axis.grid(True)

        if theme.value_axis_side == "right":
            if vertical:
                ax.yaxis.tick_right()
                ax.yaxis.set_label_position("right")
            else:
                ax.xaxis.tick_top()
                ax.xaxis.set_label_position("top")

        visible: set[str] = set(theme.spines or ())
        if not vertical:
            visible = {_SPINE_SWAP[s] for s in visible}
        for side, spine in ax.spines.items():
            spine.set_visible(side in visible)

    def _draw_values(self, ax: Axes, style: Style, containers: list[_Bars]) -> None:
        assert self._value_fmt is not None
        theme = style.theme
        vertical = self._orient == "v"
        inside = self._stack if self._values_inside is None else self._values_inside
        for bars, values, errors in containers:
            labels = [self._value_fmt(v) if np.isfinite(v) else "" for v in values]
            texts = ax.bar_label(
                bars,
                labels=labels,
                label_type="center" if inside else "edge",
                padding=0 if inside else 2,
                fontsize=style.sizes.tick,
                color=theme.text_color,
            )
            if inside:
                for text, patch in zip(texts, bars.patches, strict=True):
                    text.set_color(
                        readable_on(
                            to_hex(patch.get_facecolor()),
                            dark=theme.text_color or "#000000",
                            light="#ffffff",
                        )
                    )
            elif errors is not None:
                # Sit above the error bar instead of colliding with its cap.
                for text, value, err in zip(texts, values, errors, strict=True):
                    if np.isfinite(value) and np.isfinite(err):
                        shift = err if value >= 0 else -err
                        x, y = text.xy
                        text.xy = (x, y + shift) if vertical else (x + shift, y)
            self._value_texts.append((list(texts), bars))

    # -------------------------------------------------------------- adapting
    def _adapt(
        self, fig: Figure, ax: Axes, style: Style, renderer: RendererBase
    ) -> None:
        if self._orient == "v":
            self._fit_category_labels(fig, ax, renderer)
        self._fit_values(fig, renderer)

    def _fit_category_labels(
        self, fig: Figure, ax: Axes, renderer: RendererBase
    ) -> None:
        labels = [t for t in ax.get_xticklabels() if t.get_text()]
        if not labels or self._tick_rotation is not None:
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

    def _fit_values(self, fig: Figure, renderer: RendererBase) -> None:
        if not self._value_texts:
            return
        vertical = self._orient == "v"
        inside = self._stack if self._values_inside is None else self._values_inside
        hidden = total = 0
        for texts, bars in self._value_texts:
            for text, patch in zip(texts, bars.patches, strict=True):
                if not text.get_text():
                    continue
                total += 1
                tb = text.get_window_extent(renderer)
                pb = patch.get_window_extent(renderer)
                if inside:
                    too_big = tb.width > pb.width or tb.height > pb.height
                elif vertical:
                    too_big = tb.width > pb.width * 1.15
                else:
                    too_big = tb.height > pb.height * 1.15
                if too_big:
                    text.set_visible(False)
                    hidden += 1
        if hidden:
            emit(
                LabelsHiddenWarning,
                f"{hidden} of {total} value labels hidden because they don't fit "
                "their bars at this size. Try a wider width, a shorter format "
                "(e.g. '.2g'), or orient='h'.",
                stacklevel=6,
            )


def bar(
    data: Any,
    x: str | None = None,
    y: str | None = None,
    hue: str | None = None,
    *,
    stack: bool = False,
    error: ErrorKind | None = None,
    estimator: Estimator = "mean",
    orient: Orient = "v",
    sort: SortOrder | None = None,
    order: Sequence[Any] | None = None,
    hue_order: Sequence[Any] | None = None,
) -> BarPlot:
    """Bar plot of one value per category (aggregated with ``estimator``).

    Args:
        data: DataFrame (with ``x``/``y``/``hue`` column names), wide DataFrame,
            Series, dict, list or 2-D array. See :mod:`SecretPlots.core.data`.
        x, y, hue: Column names for categories, values and groups.
        stack: Stack groups instead of placing them side by side.
        error: Error bars from replicates: ``"sd"`` or ``"sem"``.
        estimator: ``"mean"`` (default), ``"median"``, ``"sum"`` or a function.
        orient: ``"v"`` or ``"h"``.
        sort: ``"desc"``/``"asc"`` to order categories by value.
        order, hue_order: Explicit category / group order.

    Example:
        >>> sp.bar(df, x="gene", y="tpm", error="sd").values(".1f")  # doctest: +SKIP
    """
    return BarPlot(
        tidy(data, x=x, y=y, hue=hue, order=order, hue_order=hue_order),
        stack=stack,
        error=error,
        estimator=estimator,
        orient=orient,
        sort=sort,
    )
