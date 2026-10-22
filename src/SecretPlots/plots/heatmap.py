"""Heatmaps: a matrix of colored cells, with optional value labels, row/column
groups, annotation tracks, clustering and scaling."""

import difflib
import math
import warnings
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.axes._base import _AxesBase
from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import Colorbar
from matplotlib.colors import BoundaryNorm, Colormap, LogNorm, Normalize, to_hex
from matplotlib.figure import Figure
from matplotlib.offsetbox import (
    AnchoredOffsetbox,
    DrawingArea,
    HPacker,
    TextArea,
    VPacker,
)
from matplotlib.patches import Rectangle
from matplotlib.transforms import (
    Bbox,
    BboxBase,
    ScaledTranslation,
    Transform,
    blended_transform_factory,
)

from SecretPlots.core import cluster
from SecretPlots.core.colors import extend_palette, readable_on, resolve_cmap
from SecretPlots.core.missing import (
    MissingPolicy,
    check_missing,
    handle_missing,
    numeric_array,
)
from SecretPlots.core.plot import Plot, RefAxis, _is_number, _root_figure
from SecretPlots.core.resolve import Style
from SecretPlots.core.units import PT_PER_INCH
from SecretPlots.errors import DataShapeError, LabelsHiddenWarning, emit

Axis = Literal["row", "col"]
ScaleMethod = Literal["zscore", "minmax"]
ColorbarPosition = Literal["right", "bottom", "none"]
Extend = Literal["neither", "both", "min", "max"]
Triangle = Literal["upper", "lower"]
AttributeSpec = str | Sequence[Any] | Mapping[Any, Any] | pd.Series
LabelSpec = bool | Literal["auto"] | Sequence[Any] | Mapping[Any, Any]

# Sizes of the furniture around the cells, in inches.
_STRIP = 0.09
_DENDROGRAM = 0.35
_PAD = 0.03
_COLORBAR_WIDTH = 0.09
_COLORBAR_MIN_LENGTH = 0.9
_COLORBAR_PAD = 2 * _PAD * PT_PER_INCH  # pt between the labels and the colorbar
_NAME_OFFSET = 3.0  # pt between a track and its name
#: Above this many cells, cells are rasterized inside vector files (PDF/SVG)
#: so the file stays small and fast to open.
_RASTERIZE_CELLS = 5000
_SCALE_LABELS = {"zscore": "Z-score", "minmax": "Scaled (0-1)"}


# ------------------------------------------------------------------- input
@dataclass(frozen=True)
class _Matrix:
    values: pd.DataFrame  # rows x columns, float
    row_name: str | None
    col_name: str | None
    value_name: str | None
    source: pd.DataFrame | None = None  # original table, for group columns
    x: Hashable | None = None  # long form: column holding column labels
    y: Hashable | None = None  # long form: column holding row labels


def _name(value: Hashable | None) -> str | None:
    return None if value is None else str(value)


def _matrix(
    data: Any,
    x: Hashable | None,
    y: Hashable | None,
    value: Hashable | None,
    aggfunc: str | Callable[[pd.Series], float],
    missing: MissingPolicy = "raise",
) -> _Matrix:
    if isinstance(data, Mapping) and not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    if not isinstance(data, pd.DataFrame):
        if x is not None or y is not None or value is not None:
            raise DataShapeError("x=/y=/value= are column names; pass a DataFrame")
        try:
            arr = numeric_array(data)
        except (TypeError, ValueError):
            raise DataShapeError(
                "Could not read the data as a matrix of numbers"
            ) from None
        if arr.ndim != 2:
            raise DataShapeError(f"A heatmap needs 2-D data, got {arr.ndim}-D")
        return _Matrix(pd.DataFrame(arr), None, None, None)

    for name in (x, y, value):
        if name is not None and name not in data.columns:
            raise DataShapeError(
                f"Column {name!r} not found. "
                f"Available: {', '.join(map(str, data.columns))}"
            )
    if x is not None or value is not None:  # long form
        if x is None or y is None or value is None:
            raise DataShapeError(
                "For a long table pass x= (columns), y= (rows) and value=; for a "
                "wide table (rows x columns) pass only y= or nothing"
            )
        frame = data.copy()
        try:
            frame[value] = pd.to_numeric(frame[value])
        except (TypeError, ValueError):
            raise DataShapeError(f"Values in {value!r} must be numeric") from None
        # Normalize into private names without reserving user column names.
        normalized = handle_missing(
            pd.DataFrame({"row": frame[y], "column": frame[x], "value": frame[value]}),
            missing,
            values=["value"],
            keys=["row", "column"],
            gap=True,
        )
        frame = pd.DataFrame(
            {y: normalized["row"], x: normalized["column"], value: normalized["value"]}
        )
        table = frame.pivot_table(
            index=y,
            columns=x,
            values=value,
            aggfunc=aggfunc,  # type: ignore[arg-type]
            sort=False,
            observed=True,
            dropna=False,
        )
        table = table.reindex(
            index=_appearance(frame[y]), columns=_appearance(frame[x])
        )
        if missing == "gap":
            for row, col in frame.loc[frame[value].isna(), [y, x]].itertuples(
                index=False, name=None
            ):
                table.loc[row, col] = np.nan
        return _Matrix(
            table.astype(float), _name(y), _name(x), _name(value), data, x, y
        )

    frame = data.set_index(y) if y is not None else data
    numeric = frame.select_dtypes("number")
    if numeric.shape[1] == 0:
        raise DataShapeError("DataFrame has no numeric columns to plot")
    if not numeric.index.is_unique:
        raise DataShapeError(
            "Row labels repeat; pass a long table with x=, y=, value= to "
            "aggregate duplicates"
        )
    return _Matrix(
        numeric.astype(float),
        _name(numeric.index.name),
        _name(numeric.columns.name),
        None,
        frame,  # indexed by row label: other columns describe the rows
    )


def _appearance(values: pd.Series) -> list[Any]:
    if isinstance(values.dtype, pd.CategoricalDtype):
        return [c for c in values.cat.categories if c in set(values)]
    return list(pd.unique(values.dropna()))


def _choice(value: object, options: Sequence[str], what: str) -> None:
    if value in options:
        return
    match = difflib.get_close_matches(str(value), options, n=1)
    hint = f" Did you mean {match[0]!r}?" if match else ""
    raise ValueError(
        f"Unknown {what}={value!r}.{hint} Use one of {', '.join(map(repr, options))}."
    )


# ------------------------------------------------------------------ layout
@dataclass
class _AxisLayout:
    """Display order of one axis: blocks (groups) separated by gaps."""

    blocks: list[tuple[Any, list[Any]]]  # (group or None, labels in order)
    trees: list[cluster.Tree | None]
    grouped: bool

    @property
    def order(self) -> list[Any]:
        return [label for _, labels in self.blocks for label in labels]

    def starts(self, gap: float) -> list[float]:
        """Coordinate of each label's first edge."""
        out: list[float] = []
        for b, (_, labels) in enumerate(self.blocks):
            base = len(out) + b * gap
            out += [base + i for i in range(len(labels))]
        return out

    def extent(self, gap: float) -> float:
        return len(self.order) + gap * (len(self.blocks) - 1)


def _gap_units(gap_in: float, n: int, blocks: int, length_in: float) -> float:
    """Gap in data units so that it measures ``gap_in`` inches on an axis of
    ``length_in`` inches holding ``n`` cells and ``blocks`` blocks."""
    gaps = blocks - 1
    if gaps <= 0 or gap_in <= 0:
        return 0.0
    room = length_in - gaps * gap_in
    if room <= 0:
        return 0.0
    return gap_in * n / room


class _Beside:
    """Axes locator: a band of fixed thickness beside the parent axes."""

    def __init__(self, parent: Axes, side: str, offset: float, size: float) -> None:
        self.parent, self.side, self.offset, self.size = parent, side, offset, size

    def __call__(self, child: _AxesBase, renderer: RendererBase | None) -> Bbox:
        fig = _root_figure(self.parent)
        assert fig is not None
        width, height = fig.get_size_inches()
        box = self.parent.get_position(original=False)
        if self.side == "left":
            x1 = box.x0 - self.offset / width
            return Bbox.from_extents(x1 - self.size / width, box.y0, x1, box.y1)
        y0 = box.y1 + self.offset / height
        return Bbox.from_extents(box.x0, y0, box.x1, y0 + self.size / height)


class _ColorbarLocator:
    """Colorbar right of the row labels (or below the column labels)."""

    def __init__(
        self,
        parent: Axes,
        side: str,
        beside: Callable[[], list[Artist]] = list,
        pad: float = _COLORBAR_PAD,
    ) -> None:
        self.parent, self.side, self.beside = parent, side, beside
        self.pad = pad / PT_PER_INCH  # inches

    def __call__(self, child: _AxesBase, renderer: RendererBase | None) -> Bbox:
        fig = _root_figure(self.parent)
        assert fig is not None
        renderer = renderer or fig.canvas.get_renderer()  # type: ignore[attr-defined]
        dpi = fig.dpi
        box = self.parent.get_window_extent(renderer)
        width, height = fig.bbox.width, fig.bbox.height
        if self.side == "right":
            labels = self.parent.yaxis.get_tightbbox(renderer)
            edges = [box.x1, labels.x1 if labels else box.x1]
            # Column track names stick out to the right above the row labels.
            # Only their width is used: their position may be from the last
            # draw, and the layout would never settle.
            edges += [
                box.x1
                + _NAME_OFFSET / PT_PER_INCH * dpi
                + a.get_window_extent(renderer).width
                for a in self.beside()
            ]
            x0 = max(edges) + self.pad * dpi
            length = min(box.height, max(_COLORBAR_MIN_LENGTH * dpi, box.height / 2))
            y1 = box.y1
            return Bbox.from_extents(
                x0 / width,
                (y1 - length) / height,
                (x0 + _COLORBAR_WIDTH * dpi) / width,
                y1 / height,
            )
        labels = self.parent.xaxis.get_tightbbox(renderer)
        y1 = min(box.y0, labels.y0 if labels else box.y0) - self.pad * dpi
        length = min(box.width, max(_COLORBAR_MIN_LENGTH * dpi, box.width / 2))
        return Bbox.from_extents(
            box.x0 / width,
            (y1 - _COLORBAR_WIDTH * dpi) / height,
            (box.x0 + length) / width,
            y1 / height,
        )


class _BelowColorbar(BboxBase):
    """Zero-height box just under the colorbar (in pixels), recomputed every
    time it is read. Anchoring the track legend to the colorbar axes would use
    their position from the previous draw, and the layout never settles."""

    def __init__(
        self,
        parent: Axes,
        under: bool,
        beside: Callable[[], list[Artist]],
        pad: float = _COLORBAR_PAD,
    ) -> None:
        super().__init__()
        # The right-hand column the colorbar uses, whether or not it is shown.
        self.locator = _ColorbarLocator(parent, "right", beside, pad)
        self.parent, self.under = parent, under

    def get_points(self) -> np.ndarray:
        fig = _root_figure(self.parent)
        assert fig is not None
        box = self.locator(self.parent, None).transformed(fig.transFigure)
        if self.under:  # colorbar on the right: legend under it
            y = box.y0 - 4 * _PAD * fig.dpi
        else:  # no colorbar there: legend at the top, right of the row labels
            y = self.parent.get_window_extent().y1
        return np.array([[box.x0, y], [box.x0, y]])


@dataclass
class _Body:
    """Everything drawn for the cells; removed and redrawn when the gaps
    between groups need to be re-measured after layout."""

    artists: list[Artist] = field(default_factory=list)
    axes: list[_AxesBase] = field(default_factory=list)
    value_texts: list[Any] = field(default_factory=list)
    group_texts: list[tuple[Any, str, float]] = field(default_factory=list)
    track_names: list[Artist] = field(default_factory=list)
    row_gap: float = 0.0
    col_gap: float = 0.0


# -------------------------------------------------------------------- plot
class HeatmapPlot(Plot):
    """Created by :func:`heatmap`."""

    kind = "heatmap"
    _refline_zorder = 4  # above the cells
    _reflines_in_draw = True  # redrawn with the cells after layout

    def __init__(self, matrix: _Matrix, *, square: bool = False) -> None:
        super().__init__()
        if matrix.values.size == 0:
            raise DataShapeError("No data to plot")
        self._matrix = matrix
        self._square = square
        self._cmap: dict[str, Any] = {}
        self._colorbar: dict[str, Any] = {"position": "right"}
        self._value_fmt: Callable[[float], str] | None = None
        self._value_labels: pd.DataFrame | None = None
        self._scale_axis: Axis | None = None
        self._scale_method: ScaleMethod = "zscore"
        self._cluster: dict[str, Any] = {}
        self._groups: dict[str, Any] = {"gap": 2.0, "labels": True, "bar": True}
        self._group_specs: dict[str, AttributeSpec | None] = {"row": None, "col": None}
        self._tracks: dict[str, dict[str, AttributeSpec]] = {"row": {}, "col": {}}
        self._mask: Triangle | np.ndarray | None = None
        self._mask_diagonal = False
        self._ticklabels: dict[str, LabelSpec] = {"row": "auto", "col": "auto"}
        self._renames: dict[str, dict[Any, Any]] = {"row": {}, "col": {}}
        self._tick_rotation: float | None = None
        self._tick_italic = False
        self._body = _Body()
        #: Row ("y") and column ("x") labels and cell starts, for reflines.
        self._cell_starts: dict[str, tuple[list[Any], np.ndarray]] = {}
        self._layout_cache: dict[str, _AxisLayout] | None = None
        self._cax: Axes | None = None
        self._track_legend: AnchoredOffsetbox | None = None

    # ----------------------------------------------------------------- verbs
    def cmap(
        self,
        name: str | Sequence[str] | Colormap | None = None,
        *,
        center: float | None = None,
        vmin: float | None = None,
        vmax: float | None = None,
        robust: bool = False,
        reverse: bool = False,
        log: bool = False,
        levels: int | Sequence[float] | None = None,
    ) -> Self:
        """Colormap and color limits. Each call resets options it doesn't pass.

        Args:
            name: A SecretColors map (``"blues"``, ``"RdBu"``, ``"tol_sunset"``;
                ``sp.colormaps()`` lists them), a palette color (``"teal"``), a
                matplotlib map (``"viridis"``), or a list of colors, low to
                high. Default: the theme's sequential map, or its diverging map
                when ``center`` is set or values are z-scored.
            center: Value at the middle of a diverging map (e.g. 0 or 1 for
                fold change). Limits become symmetric around it.
            vmin: Value at the low end; lower values get the end color and an
                arrow on the colorbar.
            vmax: Value at the high end.
            robust: Set missing limits from the 2nd and 98th percentiles, so a
                few outliers don't wash out the rest.
            reverse: Flip the colormap.
            log: Logarithmic color scale (positive values only).
            levels: Number of discrete color steps, or the boundaries between
                them. Discrete steps are easier to read off in print.
        """
        if name is not None:
            resolve_cmap(name)  # fail fast on unknown names
        if vmin is not None and vmax is not None and vmin >= vmax:
            raise ValueError("vmin must be smaller than vmax")
        if log and center is not None:
            raise ValueError("log=True and center= cannot be combined")
        if isinstance(levels, int) and not isinstance(levels, bool) and levels < 2:
            raise ValueError("levels must be at least 2")
        self._cmap = {
            "name": name,
            "center": center,
            "vmin": vmin,
            "vmax": vmax,
            "robust": robust,
            "reverse": reverse,
            "log": log,
            "levels": levels,
        }
        return self._changed()

    def colorbar(
        self,
        label: str | None = None,
        *,
        position: ColorbarPosition | bool = "right",
        ticks: Sequence[float] | None = None,
        fmt: str | None = None,
        pad: float | None = None,
    ) -> Self:
        """Colorbar title, position, ticks and spacing. Each call resets options it
        doesn't pass.

        Args:
            label: Title (what the color means, with units). Default: the
                ``value`` column name, or "Z-score" for scaled data.
            position: ``"right"`` (default), ``"bottom"``, or ``False`` /
                ``"none"`` to hide it. Journals expect a colorbar on every
                heatmap.
            ticks: Tick values.
            fmt: Tick format, e.g. ``".1f"`` or ``"{:.0%}"``.
            pad: Space in pt between the tick labels (row labels for
                ``"right"``, column labels for ``"bottom"``) and the
                colorbar. Default: about 4 pt.
        """
        if pad is not None and pad < 0:
            raise ValueError("pad must be 0 or more")
        if position is True:
            position = "right"
        elif position is False:
            position = "none"
        _choice(position, ("right", "bottom", "none"), "position")
        self._colorbar = {
            "label": label,
            "position": position,
            "ticks": ticks,
            "fmt": fmt,
            "pad": _COLORBAR_PAD if pad is None else pad,
        }
        return self._changed()

    def values(
        self,
        fmt: str = ".2g",
        *,
        labels: pd.DataFrame | Sequence[Sequence[Any]] | np.ndarray | None = None,
    ) -> Self:
        """Print a label in every cell, in black or white, whichever reads
        better on the cell. If labels don't fit the cells they are all hidden
        with a warning (hiding only some would mislead).

        Args:
            fmt: Format spec like ``".2f"``, or format string like
                ``"{:.0%}"``, for the cell values.
            labels: Your own text per cell instead of the values (e.g.
                significance stars): a DataFrame with the same row and column
                labels, or a 2-D list in data order. ``""`` leaves a cell blank.
        """
        template = fmt if "{" in fmt else "{:" + fmt + "}"
        self._value_fmt = template.format
        if labels is None:
            self._value_labels = None
        elif isinstance(labels, pd.DataFrame):
            values = self._matrix.values
            missing_rows = set(values.index) - set(labels.index)
            missing_cols = set(values.columns) - set(labels.columns)
            if missing_rows or missing_cols:
                raise DataShapeError(
                    "labels= must have every row and column of the heatmap; "
                    f"missing {sorted(map(str, missing_rows | missing_cols))}"
                )
            self._value_labels = labels.reindex(
                index=values.index, columns=values.columns
            ).astype(object)
        else:
            arr = np.asarray(labels, dtype=object)
            if arr.shape != self._matrix.values.shape:
                raise DataShapeError(
                    f"labels= has shape {arr.shape}, the heatmap has "
                    f"{self._matrix.values.shape} (rows, columns)"
                )
            self._value_labels = pd.DataFrame(
                arr,
                index=self._matrix.values.index,
                columns=self._matrix.values.columns,
            )
        return self._changed()

    def scale(
        self, axis: Axis | None = "row", *, method: ScaleMethod = "zscore"
    ) -> Self:
        """Rescale values within each row (or column), as for gene expression,
        where the pattern across samples matters more than the level.

        Args:
            axis: ``"row"``, ``"col"``, or ``None`` for the raw values.
            method: ``"zscore"`` (mean 0, standard deviation 1; shown on a
                diverging map centered at 0) or ``"minmax"`` (0 to 1).
        """
        if axis is not None:
            _choice(axis, ("row", "col"), "axis")
        _choice(method, ("zscore", "minmax"), "method")
        self._scale_axis = axis
        self._scale_method = method
        return self._changed()

    def cluster(
        self,
        rows: bool = True,
        cols: bool = True,
        *,
        method: cluster.Method = "average",
        metric: cluster.Metric = "euclidean",
        dendrogram: bool = True,
        split_rows: int | None = None,
        split_cols: int | None = None,
    ) -> Self:
        """Order rows and/or columns by hierarchical clustering, with a
        dendrogram. Within groups (see :meth:`groups`), each group is
        clustered on its own.

        Args:
            rows: Cluster the rows.
            cols: Cluster the columns. Keep ``False`` for ordered columns
                such as time points or doses.
            method: Linkage: ``"average"``, ``"complete"``, ``"single"`` or
                ``"ward"``.
            metric: Distance: ``"euclidean"``, ``"correlation"`` (1 - Pearson
                r) or ``"cosine"``.
            dendrogram: Draw the tree(s) beside the heatmap.
            split_rows: Cut the row tree into this many clusters, separated
                by gaps and labeled 1, 2, ...
            split_cols: Same for columns.
        """
        _choice(method, cluster.METHODS, "method")
        _choice(metric, cluster.METRICS, "metric")
        if method == "ward" and metric != "euclidean":
            raise ValueError("method='ward' needs metric='euclidean'")
        for name, k, on in (
            ("split_rows", split_rows, rows),
            ("split_cols", split_cols, cols),
        ):
            if k is None:
                continue
            if isinstance(k, bool) or not isinstance(k, int) or k < 1:
                raise ValueError(f"{name} must be a positive integer")
            if not on:
                raise ValueError(f"{name} needs that axis to be clustered")
        self._cluster = {
            "row": rows,
            "col": cols,
            "method": method,
            "metric": metric,
            "dendrogram": dendrogram,
            "split_row": split_rows,
            "split_col": split_cols,
        }
        return self._changed()

    def groups(
        self,
        rows: AttributeSpec | None = None,
        cols: AttributeSpec | None = None,
        *,
        gap: float = 2.0,
        labels: bool = True,
        bar: bool = True,
    ) -> Self:
        """Split rows and/or columns into groups: each group is kept together,
        separated by a gap, marked with a color bar and labeled.

        Args:
            rows: Group of each row: a column name (from your table), a
                mapping ``{row: group}``, a Series indexed by row, or a list
                in data order. Groups appear in order of first appearance
                (or category order).
            cols: Group of each column, in the same forms.
            gap: Space between groups in pt (0 for none).
            labels: Write the group names beside the groups.
            bar: Draw a color bar along the groups (colors from the palette,
                or ``.colors({group: color})``).
        """
        if gap < 0:
            raise ValueError("gap must be 0 or more")
        for axis, spec in (("row", rows), ("col", cols)):
            if spec is not None:
                self._attribute(axis, spec, "groups")  # validate now
        self._group_specs = {"row": rows, "col": cols}
        self._groups = {"gap": gap, "labels": labels, "bar": bar}
        return self._changed()

    def tracks(
        self,
        rows: Mapping[str, AttributeSpec] | None = None,
        cols: Mapping[str, AttributeSpec] | None = None,
    ) -> Self:
        """Color bars annotating rows or columns with categories (e.g. tissue,
        batch), explained in a legend. Unlike :meth:`groups` they don't reorder
        or split anything.

        Args:
            rows: ``{track name: categories}``; categories in any form
                :meth:`groups` accepts (column name, mapping, Series, list).
            cols: Same for columns.
        """
        out: dict[str, dict[str, AttributeSpec]] = {"row": {}, "col": {}}
        for axis, specs in (("row", rows), ("col", cols)):
            for name, spec in (specs or {}).items():
                self._attribute(axis, spec, f"track {name!r}")
                out[axis][str(name)] = spec
        self._tracks = out
        return self._changed()

    def mask(
        self,
        which: Triangle | np.ndarray | pd.DataFrame | None = "upper",
        *,
        diagonal: bool = False,
    ) -> Self:
        """Leave some cells empty, e.g. the redundant half of a correlation
        matrix. Masked cells stay blank; missing values (NaN) are drawn grey.

        Args:
            which: ``"upper"`` or ``"lower"`` triangle, a boolean matrix
                (``True`` = hide) in data order or as a DataFrame, or ``None``
                to show every cell.
            diagonal: Hide the diagonal too (with a triangle).
        """
        if isinstance(which, str):
            _choice(which, ("upper", "lower"), "which")
            n_rows, n_cols = self._matrix.values.shape
            if n_rows != n_cols:
                raise DataShapeError(
                    f"A triangle mask needs a square matrix, got {n_rows} x {n_cols}"
                )
        elif which is not None:
            values = self._matrix.values
            if isinstance(which, pd.DataFrame):
                which = (
                    which.reindex(index=values.index, columns=values.columns)
                    .fillna(False)
                    .to_numpy(dtype=bool)
                )
            which = np.asarray(which, dtype=bool)
            if which.shape != values.shape:
                raise DataShapeError(
                    f"mask has shape {which.shape}, the heatmap has {values.shape}"
                )
        self._mask = which
        self._mask_diagonal = diagonal
        return self._changed()

    def ticklabels(
        self,
        rows: LabelSpec | None = None,
        cols: LabelSpec | None = None,
        *,
        rotation: float | None = None,
        italic: bool = False,
    ) -> Self:
        """Which row/column labels to show and how.

        Args:
            rows: ``True``/``False`` to show/hide, ``"auto"`` (hide with a
                warning if they don't fit), a list of rows to label (others
                stay unlabeled, e.g. marker genes in a large heatmap), or a
                mapping ``{row: shown name}`` to rename.
            cols: Same for columns.
            rotation: Column label angle in degrees; turns off automatic
                rotation.
            italic: Italic row labels, e.g. for gene names.
        """
        for axis, spec in (("row", rows), ("col", cols)):
            if spec is None:
                continue
            labels = list(
                getattr(self._matrix.values, "index" if axis == "row" else "columns")
            )
            if isinstance(spec, Mapping):
                unknown = set(spec) - set(labels)
                if unknown:
                    raise DataShapeError(
                        f"Cannot rename {sorted(map(str, unknown))}: not a {axis}"
                    )
                self._renames[axis] = dict(spec)
                self._ticklabels[axis] = True
            elif isinstance(spec, bool) or spec == "auto":
                self._ticklabels[axis] = spec
            elif isinstance(spec, str):
                raise TypeError(f"{axis}s= takes a list of labels, not one string")
            else:
                unknown = set(spec) - set(labels)
                if unknown:
                    raise DataShapeError(
                        f"Cannot label {sorted(map(str, unknown))}: not a {axis}"
                    )
                self._ticklabels[axis] = list(spec)
        self._tick_rotation = rotation
        self._tick_italic = italic
        return self._changed()

    def log(self, axis: str = "y") -> Self:
        """Not available: heatmap axes are categories. Use ``.cmap(log=True)``
        for a logarithmic color scale.

        Args:
            axis: Unused.
        """
        raise TypeError("Heatmap axes are categories; use .cmap(log=True)")

    # ------------------------------------------------------------------ data
    def _axis_labels(self, axis: str) -> list[Any]:
        values = self._matrix.values
        return list(values.index if axis == "row" else values.columns)

    def _attribute(self, axis: str, spec: AttributeSpec, what: str) -> pd.Series:
        """Category of every row/column (indexed by label, in data order)."""
        labels = self._axis_labels(axis)
        m = self._matrix
        if isinstance(spec, str):
            source = m.source
            if source is None or spec not in source.columns:
                available = (
                    ""
                    if source is None
                    else f" Available: {', '.join(map(str, source.columns))}"
                )
                raise DataShapeError(f"{what}: column {spec!r} not found.{available}")
            key = m.y if axis == "row" else m.x
            if key is None:
                if axis == "col":
                    raise DataShapeError(
                        f"{what}: columns of a wide table can't be grouped by a "
                        "column name; pass a mapping {column: group}"
                    )
                values = source[spec]
                return pd.Series(values.to_numpy(), index=values.index).reindex(labels)
            per = source.groupby(by=[key], sort=False, observed=True)[spec].nunique()
            mixed = per[per > 1]
            if len(mixed):
                raise DataShapeError(
                    f"{what}: column {spec!r} has several values for {axis} "
                    f"{mixed.index[0]!r}; it must be constant per {axis}"
                )
            first = source.drop_duplicates(key).set_index(key)[spec]
            return first.reindex(labels)
        if isinstance(spec, pd.Series | Mapping):
            mapping = spec.to_dict() if isinstance(spec, pd.Series) else dict(spec)
            missing = [label for label in labels if label not in mapping]
            if missing:
                raise DataShapeError(
                    f"{what}: no group for {sorted(map(str, missing))[:5]}"
                )
            return pd.Series([mapping[label] for label in labels], index=labels)
        items = list(spec)
        if len(items) != len(labels):
            raise DataShapeError(
                f"{what}: got {len(items)} values for {len(labels)} {axis}s"
            )
        return pd.Series(items, index=labels)

    def _scaled(self) -> pd.DataFrame:
        values = self._matrix.values
        if self._scale_axis is None:
            return values
        arr = values.to_numpy(dtype=float)
        along = 1 if self._scale_axis == "row" else 0
        with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN rows
            if self._scale_method == "zscore":
                center = np.nanmean(arr, axis=along, keepdims=True)
                spread = np.nanstd(arr, axis=along, ddof=1, keepdims=True)
            else:
                center = np.nanmin(arr, axis=along, keepdims=True)
                spread = np.nanmax(arr, axis=along, keepdims=True) - center
            spread[spread == 0] = np.nan  # constant rows have no pattern
            scaled = (arr - center) / spread
        return pd.DataFrame(scaled, index=values.index, columns=values.columns)

    def _layouts(self) -> dict[str, _AxisLayout]:
        if self._layout_cache is None:
            self._layout_cache = {a: self._axis_layout(a) for a in ("row", "col")}
        return self._layout_cache

    def _changed(self) -> Self:
        self._layout_cache = None
        return super()._changed()

    def _axis_layout(self, axis: str) -> _AxisLayout:
        labels = self._axis_labels(axis)
        spec = self._group_specs[axis]
        clustered = bool(self._cluster.get(axis))
        split = self._cluster.get(f"split_{axis}")
        if spec is not None and split is not None:
            raise ValueError(
                f"Use either .groups({axis}s=...) or .cluster(split_{axis}s=...)"
            )
        blocks: list[tuple[Any, list[Any]]]
        if spec is not None:
            groups = self._attribute(axis, spec, "groups")
            if groups.isna().any():
                missing = list(groups[groups.isna()].index)[:5]
                raise DataShapeError(f"groups: no group for {missing}")
            names = _appearance(groups)
            blocks = [(g, list(groups.index[groups == g])) for g in names]
        else:
            blocks = [(None, labels)]
        if not clustered:
            return _AxisLayout(blocks, [None] * len(blocks), spec is not None)

        data = self._scaled()
        frame = data if axis == "row" else data.T
        if frame.isna().to_numpy().any():
            raise DataShapeError(
                "Clustering needs complete data, but some values are missing. "
                "Fill or drop them first (e.g. df.dropna())."
            )
        method, metric = self._cluster["method"], self._cluster["metric"]
        if split is not None:
            tree = cluster.linkage(frame.to_numpy(), method, metric)
            ids = cluster.cut(tree, split)
            blocks = [
                (k + 1, [labels[i] for i in tree.order if ids[i] == k])
                for k in range(split)
            ]
        out_blocks: list[tuple[Any, list[Any]]] = []
        trees: list[cluster.Tree | None] = []
        for group, members in blocks:
            tree = cluster.linkage(frame.loc[members].to_numpy(), method, metric)
            out_blocks.append((group, [members[i] for i in tree.order]))
            trees.append(tree)
        return _AxisLayout(out_blocks, trees, spec is not None or split is not None)

    def _cell_mask(self) -> np.ndarray:
        """Hidden cells, in data order."""
        shape = self._matrix.values.shape
        if self._mask is None:
            return np.zeros(shape, bool)
        if isinstance(self._mask, str):
            k = 0 if self._mask_diagonal else 1
            upper = np.triu(np.ones(shape, bool), k)
            lower = np.tril(np.ones(shape, bool), -k)
            return upper if self._mask == "upper" else lower
        return self._mask

    def source_data(self) -> pd.DataFrame:
        """The plotted matrix, in display order and after scaling (for a
        journal's source-data file). Masked cells are NaN."""
        layout = self._layouts()
        data = self._scaled().mask(self._cell_mask())
        return data.loc[layout["row"].order, layout["col"].order]

    # ---------------------------------------------------------------- colors
    def _norm_and_cmap(
        self, style: Style, data: np.ndarray
    ) -> tuple[Normalize, Colormap, Extend]:
        options = self._cmap
        center = options.get("center")
        if center is None and self._scale_axis and self._scale_method == "zscore":
            center = 0.0
        name = options.get("name")
        if name is None:
            theme = style.theme
            stops = theme.diverging if center is not None else theme.sequential
            name = list(stops or ())
        cmap = resolve_cmap(name, reverse=bool(options.get("reverse")))
        finite = data[np.isfinite(data)]
        if finite.size == 0:
            raise DataShapeError("Every value is missing or masked")
        vmin, vmax = options.get("vmin"), options.get("vmax")
        log = bool(options.get("log"))
        if log and (finite <= 0).any():
            raise DataShapeError("cmap(log=True) needs positive values")
        if options.get("robust"):
            low, high = np.percentile(finite, [2, 98])
        else:
            low, high = float(finite.min()), float(finite.max())
        vmin = low if vmin is None else vmin
        vmax = high if vmax is None else vmax
        if center is not None:
            reach = max(abs(vmax - center), abs(center - vmin)) or 1.0
            vmin, vmax = center - reach, center + reach
        if log and (vmin <= 0 or vmax <= 0):
            raise DataShapeError("cmap(log=True) needs positive vmin and vmax")
        if vmin == vmax:
            vmin, vmax = (vmin / 2, vmax * 2) if log else (vmin - 0.5, vmax + 0.5)
        below = bool(finite.min() < vmin - 1e-12)
        above = bool(finite.max() > vmax + 1e-12)
        extend: Extend = (
            ("both" if above else "min") if below else ("max" if above else "neither")
        )
        levels = options.get("levels")
        norm: Normalize
        if levels is not None:
            if isinstance(levels, int):
                if log:
                    bounds = np.geomspace(vmin, vmax, levels + 1)
                else:
                    bounds = np.linspace(vmin, vmax, levels + 1)
            else:
                bounds = np.asarray(levels, dtype=float)
            norm = BoundaryNorm(bounds, cmap.N, extend=extend)
        elif log:
            norm = LogNorm(vmin, vmax)
        else:
            norm = Normalize(vmin, vmax)
        return norm, cmap, extend

    def _category_colors(self, style: Style) -> dict[Any, str]:
        """One color per group/track category, shared by rows and columns."""
        names: list[Any] = []
        layouts = self._layouts()
        for axis in ("row", "col"):
            if layouts[axis].grouped and self._groups["bar"]:
                names += [g for g, _ in layouts[axis].blocks]
        for axis in ("row", "col"):
            for spec in self._tracks[axis].values():
                names += _appearance(self._attribute(axis, spec, "tracks").dropna())
        unique = list(dict.fromkeys(names))
        if not unique:
            return {}
        theme = style.theme
        palette = [
            c for c in (theme.palette or ()) if c not in self._color_map.values()
        ]
        base = extend_palette(
            palette or (theme.palette or ()),
            len(unique),
            background=theme.background or "#ffffff",
            source=f"the palette from {style.provenance['palette']}",
        )
        return {
            name: self._faded(self._color_map.get(name, base[i]))
            for i, name in enumerate(unique)
        }

    # --------------------------------------------------------------- drawing
    def _left_side_used(self) -> bool:
        grouped = self._layouts()["row"].grouped
        return bool(
            (grouped and (self._groups["bar"] or self._groups["labels"]))
            or self._tracks["row"]
            or (self._cluster.get("row") and self._cluster.get("dendrogram"))
        )

    def _default_labels(self) -> dict[str, str | None]:
        # The row title goes on the free left side; beside the row labels it
        # would crowd the colorbar.
        row = None if self._left_side_used() else self._matrix.row_name
        return {"x": self._matrix.col_name, "y": row}

    def _draw(self, ax: Axes, style: Style) -> None:
        layouts = self._layouts()
        gap_in = float(self._groups["gap"]) / PT_PER_INCH
        # First guess of the cell area; corrected in _adapt once laid out.
        width, height = style.figsize
        self._draw_body(
            ax,
            style,
            row_gap=_gap_units(
                gap_in,
                len(layouts["row"].order),
                len(layouts["row"].blocks),
                height * 0.6,
            ),
            col_gap=_gap_units(
                gap_in,
                len(layouts["col"].order),
                len(layouts["col"].blocks),
                width * 0.6,
            ),
        )

    def _draw_body(
        self, ax: Axes, style: Style, *, row_gap: float, col_gap: float
    ) -> None:
        theme = style.theme
        layouts = self._layouts()
        rows, cols = layouts["row"], layouts["col"]
        before_children = set(ax.get_children())
        before_axes = list(ax.child_axes)
        self._body = _Body(row_gap=row_gap, col_gap=col_gap)

        data = self._scaled()
        hidden = pd.DataFrame(self._cell_mask(), index=data.index, columns=data.columns)
        shown = data.mask(hidden).loc[rows.order, cols.order]
        values = shown.to_numpy(dtype=float)
        is_hidden = hidden.loc[rows.order, cols.order].to_numpy()
        norm, cmap, extend = self._norm_and_cmap(style, values)

        row_starts = np.array(rows.starts(row_gap))
        col_starts = np.array(cols.starts(col_gap))
        edge = theme.cell_edge_width or 0.0
        rasterized = values.size > _RASTERIZE_CELLS
        nan_cells = ~np.isfinite(values) & ~is_hidden

        def mesh_edges(starts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            """Edges for pcolormesh with gap rows/columns, and the index of the
            real cell drawn in each mesh slot (-1 for gaps)."""
            edges = [float(starts[0])]
            index: list[int] = []
            for i, start in enumerate(starts):
                if start > edges[-1] + 1e-9:  # gap before this cell
                    edges.append(float(start))
                    index.append(-1)
                edges.append(float(start) + 1)
                index.append(i)
            return np.array(edges), np.array(index)

        y_edges, y_index = mesh_edges(row_starts)
        x_edges, x_index = mesh_edges(col_starts)
        grid = np.full((len(y_index), len(x_index)), np.nan)
        missing = np.zeros_like(grid)
        real_y, real_x = y_index >= 0, x_index >= 0
        grid[np.ix_(real_y, real_x)] = values
        missing[np.ix_(real_y, real_x)] = nan_cells
        mesh_kwargs: dict[str, Any] = {
            "edgecolors": theme.axes_background,
            "linewidth": edge,
            "rasterized": rasterized,
            "snap": True,
        }
        if nan_cells.any():
            ax.pcolormesh(
                x_edges,
                y_edges,
                np.ma.masked_where(missing == 0, missing),
                cmap=resolve_cmap([theme.muted or "#c6c6c6"] * 2),
                **mesh_kwargs,
            )
        mesh = ax.pcolormesh(
            x_edges,
            y_edges,
            np.ma.masked_invalid(grid),
            cmap=cmap,
            norm=norm,
            **mesh_kwargs,
        )
        ax.set_xlim(0, x_edges[-1])
        ax.set_ylim(y_edges[-1], 0)  # first row on top
        if self._square:
            ax.set_aspect("equal")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("left")

        self._set_ticks(ax, style, rows.order, row_starts + 0.5, "row")
        self._set_ticks(ax, style, cols.order, col_starts + 0.5, "col")
        if self._value_fmt is not None:
            self._draw_values(
                ax, style, shown, is_hidden, row_starts, col_starts, cmap, norm
            )

        colors = self._category_colors(style)
        offsets = {"left": _PAD, "top": _PAD}
        for axis, side in (("row", "left"), ("col", "top")):
            layout = layouts[axis]
            starts = row_starts if axis == "row" else col_starts
            if layout.grouped and self._groups["bar"]:
                strip = pd.Series(
                    [g for g, labels in layout.blocks for _ in labels],
                    index=layout.order,
                )
                self._draw_strip(ax, side, offsets[side], strip, starts, colors, None)
                offsets[side] += _STRIP + _PAD
            for name, spec in self._tracks[axis].items():
                track = self._attribute(axis, spec, "tracks").loc[layout.order]
                self._draw_strip(
                    ax, side, offsets[side], track, starts, colors, name, style
                )
                offsets[side] += _STRIP + _PAD
            if self._cluster.get(axis) and self._cluster.get("dendrogram"):
                self._draw_dendrogram(ax, style, side, offsets[side], layout, starts)
                offsets[side] += _DENDROGRAM + _PAD
            if layout.grouped and self._groups["labels"]:
                self._draw_group_labels(ax, style, side, offsets[side], layout, starts)

        if self._colorbar["position"] != "none":
            self._draw_colorbar(ax, style, mesh, extend)
        self._draw_track_legend(ax, style, colors)
        self._cell_starts = {
            "y": (rows.order, row_starts),
            "x": (cols.order, col_starts),
        }
        self._draw_reflines(ax, style)

        self._body.artists = [
            a
            for a in ax.get_children()
            if a not in before_children and not isinstance(a, Axes)
        ]
        self._body.axes = [a for a in ax.child_axes if a not in before_axes]

    def _refline_axis(self) -> RefAxis:
        raise ValueError(
            "Heatmap reference lines need an axis: refline(..., axis='y') for "
            "rows, axis='x' for columns"
        )

    def _refline_categories(self, axis: RefAxis) -> Mapping[Any, float] | None:
        order, starts = self._cell_starts[axis]
        which = "row" if axis == "y" else "col"
        centers: dict[Any, float] = {}
        for label, start in zip(order, starts, strict=True):
            centers[label] = centers[self._shown(which, label)] = float(start) + 0.5
        return centers

    def _refline_position(self, ax: Axes, axis: RefAxis, value: Any) -> Any:
        """Row/column names go through the cells' centers; a number ``n``
        is the edge after the first ``n`` rows/columns (0 = the first edge),
        in the middle of a group gap if there is one."""
        order, starts = self._cell_starts[axis]
        names = self._refline_categories(axis) or {}
        if value in names or not _is_number(value):
            return super()._refline_position(ax, axis, value)
        n = len(order)
        if float(value) != int(value) or not 0 <= value <= n:
            what = "rows" if axis == "y" else "columns"
            raise DataShapeError(
                f"refline {value!r}: numbers count edges between {what}, from 0 to {n}"
            )
        k = int(value)
        if k == 0:
            return float(starts[0])
        if k == n:
            return float(starts[-1]) + 1
        return (float(starts[k - 1]) + 1 + float(starts[k])) / 2

    def _shown(self, axis: str, label: Any) -> str:
        return str(self._renames[axis].get(label, label))

    def _set_ticks(
        self, ax: Axes, style: Style, order: list[Any], centers: np.ndarray, axis: str
    ) -> None:
        spec = self._ticklabels[axis]
        if spec is False:
            picked: list[int] = []
        elif isinstance(spec, list):
            wanted = set(spec)
            picked = [i for i, label in enumerate(order) if label in wanted]
        else:
            picked = list(range(len(order)))
        setter = ax.set_yticks if axis == "row" else ax.set_xticks
        setter(centers[picked], labels=[self._shown(axis, order[i]) for i in picked])
        texts = ax.get_yticklabels() if axis == "row" else ax.get_xticklabels()
        highlight = set(self._highlight)
        theme = style.theme
        for i, text in zip(picked, texts, strict=True):
            if axis == "row" and self._tick_italic:
                text.set_fontstyle("italic")
            if highlight:
                if order[i] in highlight:
                    text.set_fontweight("bold")
                else:
                    text.set_color(theme.muted_text_color or "#6f6f6f")
        if axis == "col" and self._tick_rotation is not None:
            for text in texts:
                text.set_rotation(self._tick_rotation)
                if self._tick_rotation % 180:
                    text.set_horizontalalignment("right")
                    text.set_rotation_mode("anchor")

    def _draw_values(
        self,
        ax: Axes,
        style: Style,
        shown: pd.DataFrame,
        hidden: np.ndarray,
        row_starts: np.ndarray,
        col_starts: np.ndarray,
        cmap: Colormap,
        norm: Normalize,
    ) -> None:
        assert self._value_fmt is not None
        theme = style.theme
        dark = theme.text_color or "#000000"
        custom = self._value_labels
        texts = []
        grid = shown.to_numpy(dtype=float)
        for r, row in enumerate(shown.index):
            for c, col in enumerate(shown.columns):
                if hidden[r, c]:
                    continue
                value = float(grid[r, c])
                if custom is not None:
                    label = custom.at[row, col]
                    text = "" if pd.isna(label) else str(label)
                else:
                    text = self._value_fmt(value) if np.isfinite(value) else ""
                if not text:
                    continue
                background = (
                    to_hex(cmap(norm(value)))
                    if np.isfinite(value)
                    else theme.muted or "#c6c6c6"
                )
                texts.append(
                    ax.text(
                        col_starts[c] + 0.5,
                        row_starts[r] + 0.5,
                        text,
                        ha="center",
                        va="center",
                        fontsize=style.sizes.tick,
                        color=readable_on(background, dark=dark, light="#ffffff"),
                    )
                )
        self._body.value_texts = texts

    def _side_axes(self, ax: Axes, side: str, offset: float, size: float) -> Axes:
        child = ax.inset_axes((0, 0, 1, 1))
        child.set_axes_locator(_Beside(ax, side, offset, size))
        child.set_axis_off()
        if side == "left":
            child.set_ylim(ax.get_ylim())
            child.set_xlim(0, 1)
        else:
            child.set_xlim(ax.get_xlim())
            child.set_ylim(0, 1)
        return child

    def _draw_strip(
        self,
        ax: Axes,
        side: str,
        offset: float,
        categories: pd.Series,
        starts: np.ndarray,
        colors: dict[Any, str],
        name: str | None,
        style: Style | None = None,
    ) -> None:
        child = self._side_axes(ax, side, offset, _STRIP)
        for start, value in zip(starts, categories, strict=True):
            if pd.isna(value):
                continue
            color = colors[value]
            if side == "left":
                child.fill_between([0, 1], start, start + 1, color=color, lw=0)
            else:
                child.fill_between([start, start + 1], 0, 1, color=color, lw=0)
        if name and style is not None:
            # Row tracks: name under the strip, reading upwards (as in
            # pheatmap). Column tracks: name right of the strip, above the
            # row labels.
            below = side == "left"
            text = child.annotate(
                name,
                xy=(0.5, 0) if below else (1, 0.5),
                xycoords="axes fraction",
                xytext=(0, -_NAME_OFFSET) if below else (_NAME_OFFSET, 0),
                textcoords="offset points",
                rotation=90 if below else 0,
                ha="center" if below else "left",
                va="top" if below else "center",
                fontsize=style.sizes.tick,
                color=style.theme.text_color,
                annotation_clip=False,
            )
            if not below:
                self._body.track_names.append(text)

    def _draw_dendrogram(
        self,
        ax: Axes,
        style: Style,
        side: str,
        offset: float,
        layout: _AxisLayout,
        starts: np.ndarray,
    ) -> None:
        theme = style.theme
        child = self._side_axes(ax, side, offset, _DENDROGRAM)
        tallest = (
            max(
                (h for tree in layout.trees if tree for *_, h in tree.merges),
                default=0.0,
            )
            or 1.0
        )
        first = 0
        for tree, (_, labels) in zip(layout.trees, layout.blocks, strict=True):
            if tree is None:
                first += len(labels)
                continue
            block_start = starts[first]
            first += len(labels)
            for positions, heights in cluster.dendrogram_segments(tree):
                pos = [block_start + p + 0.5 for p in positions]
                depth = [h / tallest for h in heights]
                if side == "left":  # root on the left, leaves at the cells
                    child.plot(
                        [1 - d for d in depth],
                        pos,
                        color=theme.axis_color,
                        lw=theme.axis_line_width,
                        solid_capstyle="butt",
                    )
                else:
                    child.plot(
                        pos,
                        depth,
                        color=theme.axis_color,
                        lw=theme.axis_line_width,
                        solid_capstyle="butt",
                    )
        if side == "left":
            child.set_xlim(-0.02, 1)
        else:
            child.set_ylim(0, 1.02)

    def _draw_group_labels(
        self,
        ax: Axes,
        style: Style,
        side: str,
        offset: float,
        layout: _AxisLayout,
        starts: np.ndarray,
    ) -> None:
        fig = _root_figure(ax)
        assert fig is not None
        first = 0
        for group, labels in layout.blocks:
            middle = (starts[first] + starts[first + len(labels) - 1] + 1) / 2
            first += len(labels)
            if side == "left":
                transform: Transform = blended_transform_factory(
                    ax.transAxes, ax.transData
                )
                transform += ScaledTranslation(-offset - _PAD, 0, fig.dpi_scale_trans)
                kwargs: dict[str, Any]
                xy, kwargs = (
                    (0, middle),
                    {"rotation": 90, "ha": "right", "va": "center"},
                )
            else:
                transform = blended_transform_factory(ax.transData, ax.transAxes)
                transform += ScaledTranslation(0, offset + _PAD, fig.dpi_scale_trans)
                xy, kwargs = (middle, 1), {"ha": "center", "va": "bottom"}
            text = ax.text(
                *xy,
                str(group),
                transform=transform,
                fontsize=style.sizes.tick,
                fontweight="bold",
                color=style.theme.text_color,
                clip_on=False,
                **kwargs,
            )
            self._body.group_texts.append((text, side, float(len(labels))))

    def _colorbar_label(self) -> str | None:
        label = self._colorbar.get("label")
        if label is not None:
            return label or None
        if self._scale_axis is not None:
            return _SCALE_LABELS[self._scale_method]
        return self._matrix.value_name

    def _draw_colorbar(self, ax: Axes, style: Style, mesh: Any, extend: Extend) -> None:
        fig = _root_figure(ax)
        assert isinstance(fig, Figure)
        theme = style.theme
        position = self._colorbar["position"]
        cax = ax.inset_axes((0, 0, 1, 1))
        cax.set_axes_locator(
            _ColorbarLocator(
                ax,
                position,
                lambda: self._body.track_names,
                self._colorbar.get("pad", _COLORBAR_PAD),
            )
        )
        fmt = self._colorbar.get("fmt")
        formatter = None
        if fmt:
            template = fmt if "{" in fmt else "{:" + fmt + "}"
            formatter = lambda value, _: template.format(value)  # noqa: E731
        bar: Colorbar = fig.colorbar(
            mesh,
            cax=cax,
            orientation="vertical" if position == "right" else "horizontal",
            extend=extend,
            ticks=self._colorbar.get("ticks"),
            format=formatter,
            extendfrac=0.06,
        )
        bar.outline.set_linewidth(theme.axis_line_width or 0.8)
        bar.outline.set_edgecolor(theme.axis_color)
        cax.tick_params(
            length=2,
            width=theme.axis_line_width,
            labelsize=style.sizes.tick,
            color=theme.axis_color,
        )
        label = self._colorbar_label()
        if label:
            if position == "right":
                cax.set_title(
                    label,
                    fontsize=style.sizes.tick,
                    loc="left",
                    color=theme.text_color,
                    pad=4,
                )
            else:
                bar.set_label(label, fontsize=style.sizes.tick, color=theme.text_color)
        self._cax = cax

    def _draw_track_legend(
        self, ax: Axes, style: Style, colors: dict[Any, str]
    ) -> None:
        self._track_legend = None
        if not any(self._tracks.values()):
            return
        position = self._legend or "auto"
        if position == "none":
            return
        theme = style.theme
        size = float(self._legend_options.get("fontsize") or style.sizes.tick)
        text_props = {"fontsize": size, "color": theme.text_color}
        sections: list[Any] = []
        for axis in ("row", "col"):
            for name, spec in self._tracks[axis].items():
                rows: list[Any] = [
                    TextArea(name, textprops=text_props | {"fontweight": "bold"})
                ]
                values = _appearance(self._attribute(axis, spec, "tracks").dropna())
                for value in values:
                    swatch = DrawingArea(size, size)
                    swatch.add_artist(
                        Rectangle((0, 0), size, size, facecolor=colors[value], lw=0)
                    )
                    rows.append(
                        HPacker(
                            children=[
                                swatch,
                                TextArea(str(value), textprops=text_props),
                            ],
                            pad=0,
                            sep=size * 0.4,
                            align="center",
                        )
                    )
                sections.append(
                    VPacker(children=rows, pad=0, sep=size * 0.3, align="left")
                )
        fig = _root_figure(ax)
        assert fig is not None
        anchor = _BelowColorbar(
            ax,
            self._colorbar["position"] == "right",
            lambda: self._body.track_names,
            self._colorbar.get("pad", _COLORBAR_PAD),
        )
        box = AnchoredOffsetbox(
            loc="upper left",
            child=VPacker(children=sections, pad=0, sep=size * 0.9, align="left"),
            pad=0,
            borderpad=0,
            frameon=False,
            bbox_to_anchor=anchor,
        )
        ax.add_artist(box)
        self._track_legend = box

    # -------------------------------------------------------------- adapting
    def _adapt(
        self, fig: Figure, ax: Axes, style: Style, renderer: RendererBase
    ) -> None:
        layouts = self._layouts()
        gap_in = float(self._groups["gap"]) / PT_PER_INCH
        box = ax.get_window_extent(renderer)
        row_gap = _gap_units(
            gap_in,
            len(layouts["row"].order),
            len(layouts["row"].blocks),
            box.height / fig.dpi,
        )
        col_gap = _gap_units(
            gap_in,
            len(layouts["col"].order),
            len(layouts["col"].blocks),
            box.width / fig.dpi,
        )
        body = self._body
        if not (
            math.isclose(row_gap, body.row_gap, rel_tol=0.03, abs_tol=1e-3)
            and math.isclose(col_gap, body.col_gap, rel_tol=0.03, abs_tol=1e-3)
        ):
            # Child axes first: removing the colorbar looks up its mappable.
            for child in body.axes:
                child.remove()
            for artist in body.artists:
                artist.remove()
            with style.rc_context():
                self._draw_body(ax, style, row_gap=row_gap, col_gap=col_gap)
                fig.draw_without_rendering()
        self._fit_labels(fig, ax, renderer)

    def _fit_labels(self, fig: Figure, ax: Axes, renderer: RendererBase) -> None:
        layouts = self._layouts()
        box = ax.get_window_extent(renderer)
        row_slot = box.height / layouts["row"].extent(self._body.row_gap)
        col_slot = box.width / layouts["col"].extent(self._body.col_gap)
        hidden: list[str] = []

        rows = [t for t in ax.get_yticklabels() if t.get_text()]
        if rows and self._ticklabels["row"] == "auto":
            tallest = max(t.get_window_extent(renderer).height for t in rows)
            if tallest > row_slot * 1.05:
                ax.set_yticks([])
                hidden.append(f"{len(rows)} row labels")

        cols = [t for t in ax.get_xticklabels() if t.get_text()]
        if cols and self._tick_rotation is None:
            widest = max(t.get_window_extent(renderer).width for t in cols)
            if widest > col_slot * 0.95:
                for t in cols:
                    t.set_rotation(90)
                    t.set_horizontalalignment("center")
                # Rotated, the width of each label is its line height.
                line = max(t.get_window_extent(renderer).width for t in cols)
                if line > col_slot * 1.05 and self._ticklabels["col"] == "auto":
                    ax.set_xticks([])
                    hidden.append(f"{len(cols)} column labels")

        overflowing = 0
        for text, side, cells in self._body.group_texts:
            extent = text.get_window_extent(renderer)
            room = cells * (row_slot if side == "left" else col_slot)
            if (extent.height if side == "left" else extent.width) > room:
                text.set_visible(False)
                overflowing += 1
        if overflowing:
            hidden.append(f"{overflowing} group labels")

        texts = [t for t in self._body.value_texts if t.get_text()]
        if texts:
            too_big = any(
                t.get_window_extent(renderer).width > col_slot * 0.95
                or t.get_window_extent(renderer).height > row_slot * 0.95
                for t in texts
            )
            if too_big:
                for t in texts:
                    t.set_visible(False)
                hidden.append(f"{len(texts)} cell values")
        if hidden:
            emit(
                LabelsHiddenWarning,
                f"{' and '.join(hidden)} hidden because they don't fit the cells "
                "at this size. Make the figure larger, use .ticklabels(rows=[...]) "
                "to label selected rows, a shorter .values() format, or turn "
                "them off explicitly (.ticklabels(rows=False)) to silence this.",
                stacklevel=6,
            )
        fig.draw_without_rendering()


def heatmap(
    data: Any,
    x: Hashable | None = None,
    y: Hashable | None = None,
    value: Hashable | None = None,
    *,
    aggfunc: str | Callable[[pd.Series], float] = "mean",
    row_order: Sequence[Any] | None = None,
    col_order: Sequence[Any] | None = None,
    square: bool = False,
    missing: MissingPolicy = "raise",
) -> HeatmapPlot:
    """Heatmap: one colored cell per row and column of a matrix.

    Args:
        data: A wide DataFrame (rows x columns; numeric columns become heatmap
            columns, other columns stay available for ``.groups()`` and
            ``.tracks()``), a long DataFrame with ``x``/``y``/``value``
            columns, a 2-D array or list of lists, or a dict of columns.
        x: Long table: column with the heatmap's column labels.
        y: Column with the row labels (long or wide table). Without it, a
            wide table's index labels the rows.
        value: Long table: column with the values.
        aggfunc: Long table: how repeated (x, y) pairs are combined,
            ``"mean"`` (default), ``"median"``, ``"sum"`` or a function.
        row_order: Explicit row order (also selects rows).
        col_order: Explicit column order (also selects columns).
        square: Square cells.
        missing: "raise" (default) rejects missing/non-finite cells; "gap"
            displays them as missing; "drop" removes incomplete matrix rows.

    Example:
        >>> sp.heatmap(expr).scale("row").cluster(cols=False)  # doctest: +SKIP
    """
    check_missing(missing, gap=True)
    matrix = _matrix(data, x, y, value, aggfunc, missing)
    values = matrix.values
    for what, order, labels in (
        ("row", row_order, values.index),
        ("column", col_order, values.columns),
    ):
        if order is not None:
            unknown = set(order) - set(labels)
            if unknown:
                raise DataShapeError(
                    f"{what}_order has {sorted(map(str, unknown))}, not in the data"
                )
    values = values.reindex(
        index=list(row_order) if row_order is not None else values.index,
        columns=list(col_order) if col_order is not None else values.columns,
    )
    if not values.index.is_unique or not values.columns.is_unique:
        raise DataShapeError("Row and column labels must be unique")
    values = values.replace([np.inf, -np.inf], np.nan)
    if values.isna().any(axis=None):
        if missing == "raise":
            raise DataShapeError(
                "Missing or non-finite heatmap cells. "
                "Use missing='gap' to show missing cells, "
                "or missing='drop' to remove incomplete rows. "
                "Alternatively, fill the matrix before plotting."
            )
        if missing == "drop":
            values = values.dropna(axis=0)
    if values.empty or not values.notna().any(axis=None):
        raise DataShapeError("No data to plot after handling missing values")
    matrix = _Matrix(
        values,
        matrix.row_name,
        matrix.col_name,
        matrix.value_name,
        matrix.source,
        matrix.x,
        matrix.y,
    )
    return HeatmapPlot(matrix, square=square)
