"""Shared parts of line and area plots: values along an x axis (numbers, dates or
categories), one series per ``hue`` group."""

import string
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.text import Annotation
from matplotlib.ticker import ScalarFormatter

from SecretPlots.core.data import _order, _relabel, _rename_map
from SecretPlots.core.missing import MissingPolicy, handle_missing
from SecretPlots.core.plot import Plot, RefAxis
from SecretPlots.core.resolve import Style
from SecretPlots.errors import DataShapeError

XKind = Literal["numeric", "datetime", "category"]

#: Gap between the end of a line and its label, in pt.
_LABEL_PAD = 4.0
_GRADIENT_STEPS = 256


@dataclass(frozen=True)
class _Series:
    """Tidy input: ``x``, value columns and optional ``hue``/``style``/``units``.

    Categorical x values are stored as positions 0..k-1 (labels in ``x_order``).
    """

    frame: pd.DataFrame
    main: str
    names: Mapping[str, str | None]
    x_kind: XKind
    hue_order: list[Any] | None
    style_order: list[Any] | None = None
    x_order: list[Any] | None = None
    sort: bool = True
    missing: MissingPolicy = "raise"


def _name(value: Any) -> str | None:
    return None if value is None or not isinstance(value, Hashable) else str(value)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float | np.number) and not isinstance(value, bool)


def _column(spec: Any, data: pd.DataFrame | None, n: int, what: str) -> Any:
    """Values for one argument: a column name, one number for every row, or a
    sequence of ``n`` values."""
    if spec is None:
        return None
    if isinstance(spec, str) or (
        data is not None and isinstance(spec, Hashable) and spec in data.columns
    ):
        if data is None:
            raise DataShapeError(
                f"{what}={spec!r} looks like a column name, but no data was given; "
                "pass the DataFrame first"
            )
        if spec not in data.columns:
            raise DataShapeError(
                f"Column {spec!r} not found. "
                f"Available: {', '.join(map(str, data.columns))}"
            )
        return data[spec].array
    if _is_number(spec):
        return np.full(n, float(spec))
    if np.ndim(spec) != 1 or len(spec) != n:
        raise DataShapeError(f"{what}= must have one value per row ({n})")
    # NumPy coerces mixed string/numeric lists to strings, hiding NaN/inf.
    return pd.Series(spec).array


def _wide(data: Any, x: Any) -> tuple[pd.DataFrame, dict[str, str | None]]:
    """Wide input (one column per series) as long rows: ``x``, ``value``, ``hue``."""
    if isinstance(data, pd.Series):
        frame = pd.DataFrame({"x": data.index.array, "value": data.to_numpy()})
        return frame, {"x": _name(data.index.name), "value": _name(data.name)}
    if not isinstance(data, pd.DataFrame):
        arr = np.asarray(data)
        if arr.ndim == 1:
            arr = arr[:, None]
        if arr.ndim != 2:
            raise DataShapeError("Pass a 1-D sequence or a 2-D array of numbers")
        try:
            data = pd.DataFrame(arr).apply(pd.to_numeric)
        except (TypeError, ValueError):
            raise DataShapeError("Values must be numeric") from None
    if x is not None:
        if x not in data.columns:
            raise DataShapeError(
                f"Column {x!r} not found. "
                f"Available: {', '.join(map(str, data.columns))}"
            )
        index = data[x].array
        data = data.drop(columns=[x])
        x_name = _name(x)
    else:
        index = data.index.array
        x_name = _name(data.index.name)
    numeric = data.select_dtypes("number").columns
    if len(numeric) == 0:
        raise DataShapeError("No numeric columns to plot")
    if len(numeric) == 1:
        frame = pd.DataFrame({"x": index, "value": data[numeric[0]].to_numpy()})
        return frame, {"x": x_name, "value": _name(numeric[0])}
    parts = [
        pd.DataFrame({"x": index, "value": data[c].to_numpy(), "hue": c})
        for c in numeric
    ]
    frame = pd.concat(parts, ignore_index=True)
    frame["hue"] = pd.Categorical(frame["hue"], categories=list(numeric))
    return frame, {"x": x_name, "value": None, "hue": _name(data.columns.name)}


def series(
    data: Any,
    x: Any,
    values: Mapping[str, Any],
    groups: Mapping[str, Any],
    *,
    hue_order: Sequence[Any] | None = None,
    style_order: Sequence[Any] | None = None,
    order: Sequence[Any] | None = None,
    sort: bool = True,
    required: Sequence[str] = (),
    missing: MissingPolicy = "raise",
) -> _Series:
    """Read ``data`` into a :class:`_Series`.

    ``values`` maps numeric columns to what the user passed; the first one is
    the main value. Left out with a DataFrame (or a Series, list or array as
    ``data``), every numeric column is one series (wide form) and the other
    values can only be single numbers. ``groups`` maps ``hue``/``style``/
    ``units`` to columns. Missing plotted fields follow ``missing``: raise
    by default, drop affected rows, or preserve value gaps with valid keys.
    """
    main, *others = values
    if isinstance(data, Mapping):
        data = pd.DataFrame(data)
    names: dict[str, str | None] = {}
    if data is None:
        if values[main] is None:
            raise DataShapeError(
                f"Pass a DataFrame with x= and {main}= column names, or {main}= "
                "as a sequence of numbers"
            )
        if isinstance(values[main], str):
            _column(values[main], None, 0, main)  # raises: a name without data
        n = len(np.atleast_1d(np.asarray(values[main])))
        frame = pd.DataFrame(
            {"x": np.arange(n) if x is None else _column(x, None, n, "x")}
        )
        for key, spec in {**values, **groups}.items():
            column = _column(spec, None, n, key)
            if column is not None:
                frame[key] = column
    elif values[main] is None or not isinstance(data, pd.DataFrame):
        if values[main] is not None:
            raise DataShapeError(
                f"{main}= names a column, so pass a DataFrame or a dict of columns"
            )
        if any(v is not None for v in groups.values()):
            used = ", ".join(f"{k}=" for k, v in groups.items() if v is not None)
            raise DataShapeError(
                f"{used} needs long-form data (a DataFrame with a {main}= column). "
                "Wide data gets one series per column already."
            )
        frame, wide_names = _wide(data, x)
        frame = frame.rename(columns={"value": main})
        names = {"x": wide_names["x"], main: wide_names["value"]}
        names["hue"] = wide_names.get("hue")
        for key in others:
            spec = values[key]
            if spec is not None and not _is_number(spec):
                raise DataShapeError(
                    f"With one column per series, {key}= can only be one number"
                )
            if spec is not None:
                frame[key] = float(spec)
    else:
        if x is None:
            raise DataShapeError(
                f"Pass x= (a column name) with {main}=. "
                f"Available: {', '.join(map(str, data.columns))}"
            )
        n = len(data)
        frame = pd.DataFrame({"x": _column(x, data, n, "x")})
        for key, spec in {**values, **groups}.items():
            column = _column(spec, data, n, key)
            if column is None:
                continue
            frame[key] = column
            if (
                key in groups
                and isinstance(spec, Hashable)
                and spec in data.columns
                and isinstance(data[spec].dtype, pd.CategoricalDtype)
            ):
                frame[key] = pd.Categorical(
                    frame[key], categories=data[spec].cat.categories
                )
        names = {k: _name(v) for k, v in {"x": x, **values, **groups}.items()}
        names = {k: v for k, v in names.items() if not _is_number(values.get(k))}

    for key in values:
        if key in frame:
            try:
                frame[key] = pd.to_numeric(frame[key])
            except (TypeError, ValueError):
                shown = names.get(key) or key
                raise DataShapeError(f"Values in {shown!r} must be numeric") from None

    x_kind: XKind
    if pd.api.types.is_datetime64_any_dtype(frame["x"]):
        x_kind = "datetime"
    elif isinstance(frame["x"].dtype, pd.CategoricalDtype):
        x_kind = "category"
    else:
        try:
            frame["x"] = pd.to_numeric(frame["x"])
            x_kind = "numeric"
        except (TypeError, ValueError):
            x_kind = "category"
    if order is not None and x_kind != "category":
        raise DataShapeError("order= sets the order of category x values")

    frame = handle_missing(
        frame,
        missing,
        values=[k for k in values if k in frame],
        keys=["x", *(k for k in groups if k in frame)],
        gap=True,
    )
    x_order = None
    if x_kind == "category":
        x_order = _order(frame["x"], order, "x")
        positions = {v: float(i) for i, v in enumerate(x_order)}
        frame["x"] = frame["x"].map(positions).astype(float)
    if sort:
        frame = frame.sort_values("x", kind="stable").reset_index(drop=True)
    if hue_order is not None and "hue" not in frame:
        raise DataShapeError("hue_order= needs hue= groups")
    if style_order is not None and "style" not in frame:
        raise DataShapeError("style_order= needs a style= column")
    return _Series(
        frame=frame,
        main=main,
        names=names,
        x_kind=x_kind,
        hue_order=_order(frame["hue"], hue_order, "hue") if "hue" in frame else None,
        style_order=_order(frame["style"], style_order, "style")
        if "style" in frame
        else None,
        x_order=x_order,
        sort=sort,
        missing=missing,
    )


def spread(wanted: Sequence[float], sizes: Sequence[float]) -> list[float]:
    """1-D label placement: positions as close as possible to ``wanted`` with
    no two labels overlapping. Overlapping labels are merged into a block
    centered on the mean of their wanted positions, until no blocks overlap."""
    blocks: list[tuple[list[int], float]] = []
    for i in sorted(range(len(wanted)), key=wanted.__getitem__):
        blocks.append(([i], wanted[i]))
        while len(blocks) > 1:
            (low, low_center), (high, high_center) = blocks[-2], blocks[-1]
            low_top = low_center + sum(sizes[j] for j in low) / 2
            high_bottom = high_center - sum(sizes[j] for j in high) / 2
            if low_top <= high_bottom:
                break
            merged = low + high
            blocks[-2:] = [(merged, float(np.mean([wanted[j] for j in merged])))]
    placed = [0.0] * len(wanted)
    for members, center in blocks:
        edge = center - sum(sizes[j] for j in members) / 2
        for j in members:
            placed[j] = edge + sizes[j] / 2
            edge += sizes[j]
    return placed


def _has_group_field(template: str) -> bool:
    return any(
        field == "group" for _, field, _, _ in string.Formatter().parse(template)
    )


def _formatter(fmt: str) -> Any:
    template = fmt if "{" in fmt else "{:" + fmt + "}"
    return template.format


class SeriesPlot(Plot):
    """Shared steps of :class:`LinePlot` and :class:`FillBetweenPlot`."""

    _handle_length = 1.8

    def __init__(self, data: _Series) -> None:
        super().__init__()
        self._data = data
        self._end_labels = False
        self._end_values: str | None = None
        self._end_template: str | None = None
        self._end_pad = _LABEL_PAD
        self._tick_rotation: float | None = None
        self._end_texts: list[Annotation] = []

    # ----------------------------------------------------------------- verbs
    def endlabels(
        self,
        show: bool = True,
        *,
        values: str | None = None,
        label: str | None = None,
        pad: float = _LABEL_PAD,
    ) -> Self:
        """Name each line at its right end, in its color, instead of a legend
        (as news graphics do). Labels that would overlap are moved apart.

        Args:
            show: ``False`` removes the labels and brings the legend back.
            values: Also print the last value, with a format like ``".1f"`` or
                ``"{:.0%}"``. Without groups, the label is just this value.
            label: Text in place of the group name, with ``{group}`` where the
                name goes: ``"Diet {group}"`` adds a prefix. Without groups,
                plain text such as ``"Revenue"`` names the single line.
            pad: Gap in points before the labels. When the value axis is on
                the right, the labels start after its tick labels.
        """
        if pad < 0:
            raise ValueError(f"pad is a gap in points and can't be negative; got {pad}")
        if values is not None:
            _formatter(values)(1.0)
        if label is not None:
            try:
                label.format(group="")
            except (KeyError, IndexError, ValueError):
                raise ValueError(
                    "label takes text with an optional {group} field, e.g. "
                    f"'Diet {{group}}'; got {label!r}"
                ) from None
        self._end_labels = show
        self._end_values = values
        self._end_template = label
        self._end_pad = float(pad)
        return self._changed()

    def grouplabels(self, labels: Sequence[Any] | Mapping[Any, Any]) -> Self:
        """Name the ``hue`` groups shown in the legend or end labels.

        Args:
            labels: New names as a list in group order or a mapping
                ``{old: new}``. The groups themselves are renamed, so later
                ``.highlight()`` or ``.colors({...})`` use the new names. When
                ``style`` is the same column as ``hue``, it is renamed too.
        """
        data = self._data
        mapping = _rename_map(data.hue_order, labels, "groups")
        frame = data.frame.copy()
        changes: dict[str, Any] = {"hue_order": list(mapping.values())}
        if "style" in frame and frame["hue"].equals(frame["style"]):
            frame["style"] = _relabel(frame["style"], mapping)
            changes["style_order"] = [mapping[v] for v in data.style_order or []]
        frame["hue"] = _relabel(frame["hue"], mapping)
        self._data = replace(data, frame=frame, **changes)
        return self._data_changed()

    def ticklabels(self, *, rotation: float | None = None) -> Self:
        """Style the x tick labels.

        Args:
            rotation: Label angle in degrees; turns off automatic rotation of
                category labels.
        """
        self._tick_rotation = rotation
        return self._changed()

    # ------------------------------------------------------------------ data
    @property
    def _grouped(self) -> bool:
        return self._data.hue_order is not None

    @property
    def _groups(self) -> list[Any]:
        return list(self._data.hue_order or [None])

    def _rows(self, group: Any, frame: pd.DataFrame | None = None) -> pd.DataFrame:
        frame = self._data.frame if frame is None else frame
        return frame if group is None else frame[frame["hue"] == group]

    def _x_values(self, x: Any) -> Any:
        """x as stored (category positions) back to what the user passed."""
        order = self._data.x_order
        if order is None:
            return x
        return [order[int(i)] for i in x]

    def _refline_categories(self, axis: RefAxis) -> Mapping[Any, float] | None:
        order = self._data.x_order
        if axis != "x" or order is None:
            return None
        return {value: float(i) for i, value in enumerate(order)}

    # --------------------------------------------------------------- drawing
    def _default_labels(self) -> dict[str, str | None]:
        names = self._data.names
        return {"x": names.get("x"), "y": names.get(self._data.main)}

    def _style_axes(self, ax: Axes, style: Style, *, x_margin: float) -> None:
        theme = style.theme
        order = self._data.x_order
        if order is not None:
            ax.set_xticks(range(len(order)), labels=[str(v) for v in order])
            x_margin = max(x_margin, 0.05)
        if self._tick_rotation is not None:
            for text in ax.get_xticklabels():
                text.set_rotation(self._tick_rotation)
                if self._tick_rotation % 90:
                    text.set_horizontalalignment("right")
                    text.set_rotation_mode("anchor")
        ax.margins(x=x_margin)
        formatter = ax.xaxis.get_major_formatter()
        if self._data.x_kind == "numeric" and isinstance(formatter, ScalarFormatter):
            formatter.set_useOffset(False)  # years read 2000..2010, not 0..10 +2e3
        grid = theme.grid
        # "value"/"category" follow bars; for lines the value axis is y.
        if grid in ("both", "value", "y"):
            ax.yaxis.grid(True)
        if grid in ("both", "category", "x"):
            ax.xaxis.grid(True)
        if theme.value_axis_side == "right":
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
        visible = set(theme.spines or ())
        for side, spine in ax.spines.items():
            spine.set_visible(side in visible)

    def _end_label(self, group: Any, last: float) -> str:
        template = self._end_template
        if template is not None and group is None and _has_group_field(template):
            raise DataShapeError(
                "endlabels(label=) has {group} but the plot has no hue= groups"
            )
        if template is not None:
            parts = [template.format(group="" if group is None else group)]
        else:
            parts = [] if group is None else [str(group)]
        if self._end_values is not None:
            parts.append(_formatter(self._end_values)(last))
        if not parts:
            raise DataShapeError(
                "endlabels() names hue= groups; without groups pass a format "
                "for the last value, e.g. .endlabels(values='.1f'), or a "
                "name, e.g. .endlabels(label='Revenue')"
            )
        return "  ".join(parts)

    def _draw_end_labels(
        self, ax: Axes, style: Style, ends: list[tuple[Any, Any, float, str, float]]
    ) -> None:
        """``ends`` holds ``(group, x, y, color, value)`` for each series: where
        its label goes and the value it prints."""
        self._end_texts = []
        for group, x, y, color, value in ends:
            if not np.isfinite(y) or not np.isfinite(value):
                continue
            text = ax.annotate(
                self._end_label(group, value),
                xy=(ax.convert_xunits(x), y),  # type: ignore[no-untyped-call]
                xytext=(self._end_pad, 0),
                textcoords="offset points",
                va="center",
                ha="left",
                fontsize=style.sizes.tick,
                color=color,
                annotation_clip=False,
            )
            self._end_texts.append(text)

    def _gradient(
        self,
        ax: Axes,
        x: np.ndarray,
        opaque: np.ndarray,
        clear: np.ndarray | float,
        color: str,
        alpha: float,
        zorder: float,
    ) -> PolyCollection:
        """Fill between ``opaque`` and ``clear``, fading from ``alpha`` at the
        ``opaque`` side to transparent at the ``clear`` side. Returns the
        (invisible) outline of the area."""
        ax.xaxis.update_units(x)  # type: ignore[no-untyped-call]  # dates: set up the date axis before converting
        x_num = np.asarray(ax.convert_xunits(x), dtype=np.float64)  # type: ignore[no-untyped-call]
        clear = np.broadcast_to(np.asarray(clear, dtype=float), x_num.shape)
        outline = ax.fill_between(x_num, opaque, clear, color="none", lw=0)
        paths = [p for p in outline.get_paths() if np.size(p.vertices)]
        if not paths:
            return outline
        clip = Path.make_compound_path(*paths)
        low = float(np.nanmin([np.nanmin(opaque), np.nanmin(clear)]))
        high = float(np.nanmax([np.nanmax(opaque), np.nanmax(clear)]))
        if high <= low:
            return outline
        rgba = np.zeros((_GRADIENT_STEPS, 1, 4))
        rgba[..., :3] = to_rgba(color)[:3]
        ramp = np.linspace(0, alpha * to_rgba(color)[3], _GRADIENT_STEPS)
        top_opaque = np.nanmean(opaque) >= np.nanmean(clear)
        rgba[:, 0, 3] = ramp if top_opaque else ramp[::-1]
        image = ax.imshow(
            rgba,
            extent=(float(np.nanmin(x_num)), float(np.nanmax(x_num)), low, high),
            origin="lower",
            aspect="auto",
            interpolation="bilinear",
            zorder=zorder,
        )
        image.set_clip_path(clip, ax.transData)
        # imshow pins the limits to the image; let the data and margins decide.
        image.sticky_edges.x[:] = []
        image.sticky_edges.y[:] = []
        ax.set_autoscale_on(True)
        return outline

    # -------------------------------------------------------------- adapting
    def _adapt(
        self, fig: Figure, ax: Axes, style: Style, renderer: RendererBase
    ) -> None:
        if self._data.x_order is not None:
            self._fit_category_labels(fig, ax, renderer, self._tick_rotation)
        self._clear_right_ticks(fig, ax, renderer)
        self._spread_end_labels(fig, renderer)

    def _clear_right_ticks(self, fig: Figure, ax: Axes, renderer: RendererBase) -> None:
        """Move the end labels past tick labels on the right axis, and the
        right-hand axis title past the end labels."""
        ticks = [
            t.label2
            for t in ax.yaxis.get_major_ticks()
            if t.label2.get_visible() and t.label2.get_text()
        ]
        if not self._end_texts or not ticks:
            return
        low, high = sorted(ax.get_ylim())
        inside = [t for t in ticks if low <= t.get_position()[1] <= high]
        if not inside:
            return
        px_to_pt = 72 / fig.dpi
        right = ax.get_window_extent(renderer).x1
        edge = max(t.get_window_extent(renderer).x1 for t in inside)
        # Anchored to the axes edge, the offset is in points and independent
        # of the layout; a data anchor would drift back into the tick labels
        # when constrained layout shrinks the axes to fit the moved labels.
        offset = (edge - right) * px_to_pt + self._end_pad
        widest = 0.0
        for text in self._end_texts:
            box = text.get_window_extent(renderer)
            if box.x0 < edge + self._end_pad / px_to_pt - 1e-3:
                text.xycoords = ("axes fraction", "data")
                text.xy = (1.0, text.xy[1])
                text.xyann = (offset, text.xyann[1])
                widest = max(widest, box.width * px_to_pt)
        if not widest:
            return
        label = ax.yaxis.label
        # str(): matplotlib's stubs type YAxis label positions as top/bottom.
        on_right = str(ax.yaxis.get_label_position()) == "right"
        if on_right and label.get_visible() and label.get_text():
            ax.yaxis.labelpad += self._end_pad + widest
        fig.draw_without_rendering()

    def _spread_end_labels(self, fig: Figure, renderer: RendererBase) -> None:
        texts = self._end_texts
        if len(texts) < 2:
            return
        boxes = [t.get_window_extent(renderer) for t in texts]
        wanted = [(b.y0 + b.y1) / 2 for b in boxes]
        sizes = [b.height * 1.05 for b in boxes]
        placed = spread(wanted, sizes)
        moved = False
        for text, want, place in zip(texts, wanted, placed, strict=True):
            shift = (place - want) * 72 / fig.dpi
            if abs(shift) > 1e-3:
                dx, dy = text.xyann
                text.xyann = (dx, dy + shift)
                moved = True
        if moved:
            fig.draw_without_rendering()
