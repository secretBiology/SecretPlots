import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import QuadMesh
from matplotlib.colors import BoundaryNorm, LogNorm, to_hex

import SecretPlots as sp
from SecretPlots.core import cluster


@pytest.fixture
def expr() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    values = rng.normal(5, 1, (12, 6))
    values[:4, 3:] += 3
    values[4:8, :3] += 2
    frame = pd.DataFrame(
        values,
        index=pd.Index([f"G{i}" for i in range(12)], name="gene"),
        columns=[f"{c}{r}" for c in ("ctrl", "trt") for r in (1, 2, 3)],
    )
    frame["pathway"] = ["Signal"] * 4 + ["Cycle"] * 4 + ["Metab"] * 4
    return frame


@pytest.fixture
def long() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "gene": ["a", "a", "b", "b", "a"],
            "sample": ["s1", "s2", "s1", "s2", "s1"],
            "tpm": [1.0, 2.0, 3.0, 4.0, 3.0],
        }
    )


def _mesh(plot: sp.HeatmapPlot) -> QuadMesh:
    meshes = [c for c in plot.ax.collections if isinstance(c, QuadMesh)]
    return meshes[-1]


def _ticks(labels) -> list[str]:
    return [t.get_text() for t in labels]


# ------------------------------------------------------------------ input
def test_wide_frame_uses_numeric_columns_and_index(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr)
    assert _ticks(plot.ax.get_yticklabels()) == list(expr.index)
    assert _ticks(plot.ax.get_xticklabels()) == list(expr.columns[:6])
    assert plot.ax.get_ylabel() == "gene"
    assert _mesh(plot).get_array().shape == (12, 6)


def test_long_frame_pivots_with_mean(long: pd.DataFrame) -> None:
    plot = sp.heatmap(long, x="sample", y="gene", value="tpm")
    data = plot.source_data()
    assert data.loc["a", "s1"] == pytest.approx(2.0)
    assert data.loc["b", "s2"] == pytest.approx(4.0)
    assert plot._colorbar_label() == "tpm"


def test_long_frame_aggfunc(long: pd.DataFrame) -> None:
    plot = sp.heatmap(long, x="sample", y="gene", value="tpm", aggfunc="sum")
    assert plot.source_data().loc["a", "s1"] == pytest.approx(4.0)


def test_wide_frame_with_label_column(expr: pd.DataFrame) -> None:
    table = expr.reset_index()
    plot = sp.heatmap(table, y="gene")
    assert list(plot.source_data().index) == list(expr.index)


@pytest.mark.parametrize("data", [[[1, 2], [3, 4]], np.array([[1.0, 2.0], [3.0, 4.0]])])
def test_array_input(data) -> None:
    plot = sp.heatmap(data)
    assert plot.source_data().to_numpy().tolist() == [[1, 2], [3, 4]]


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: sp.heatmap([1, 2, 3]), "2-D"),
        (lambda: sp.heatmap(pd.DataFrame({"a": ["x"]})), "no numeric"),
        (lambda: sp.heatmap(pd.DataFrame({"a": [1]}), x="a"), "long table"),
        (lambda: sp.heatmap(pd.DataFrame({"a": [1]}), y="nope"), "not found"),
        (lambda: sp.heatmap([[1, 2]], row_order=[5]), "row_order"),
    ],
)
def test_input_errors(call, message: str) -> None:
    with pytest.raises(sp.DataShapeError, match=message):
        call()


def test_explicit_order_selects(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr, row_order=["G3", "G1"], col_order=["trt1", "ctrl1"])
    assert plot.source_data().shape == (2, 2)
    assert _ticks(plot.ax.get_yticklabels()) == ["G3", "G1"]


# ----------------------------------------------------------------- colors
def test_default_sequential_and_limits(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr)
    mesh = _mesh(plot)
    values = expr.select_dtypes("number").to_numpy()
    assert mesh.norm.vmin == pytest.approx(values.min())
    assert mesh.norm.vmax == pytest.approx(values.max())
    low = to_hex(mesh.cmap(0.0))
    assert low == plot.style().theme.sequential[0]


def test_center_makes_symmetric_diverging_limits() -> None:
    plot = sp.heatmap([[-1.0, 0.5], [2.0, 0.0]]).cmap(center=0)
    mesh = _mesh(plot)
    assert (mesh.norm.vmin, mesh.norm.vmax) == (-2.0, 2.0)
    assert to_hex(mesh.cmap(0.0)) == plot.style().theme.diverging[0]


def test_zscore_rows(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).scale("row")
    data = plot.source_data()
    assert np.allclose(data.mean(axis=1), 0)
    assert np.allclose(data.std(axis=1, ddof=1), 1)
    assert plot._colorbar_label() == "Z-score"
    mesh = _mesh(plot)
    assert mesh.norm.vmin == pytest.approx(-mesh.norm.vmax)


def test_minmax_columns(expr: pd.DataFrame) -> None:
    data = sp.heatmap(expr).scale("col", method="minmax").source_data()
    assert np.allclose(data.min(axis=0), 0)
    assert np.allclose(data.max(axis=0), 1)


def test_clipped_limits_extend_colorbar(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).cmap(vmin=5, vmax=7)
    plot.render()
    assert plot._cax is not None
    assert _mesh(plot).colorbar.extend == "both"


def test_robust_limits_ignore_outliers() -> None:
    values = np.arange(100.0).reshape(10, 10)
    values[0, 0] = 1e6
    mesh = _mesh(sp.heatmap(values).cmap(robust=True))
    assert mesh.norm.vmax < 1000
    assert mesh.colorbar.extend == "both"  # 2nd percentile clips the low end too


def test_named_colormaps_from_secretcolors_and_matplotlib() -> None:
    for name in ("blues", "RdBu", "tol_sunset", "sc.teal", "viridis", "magma_r"):
        sp.heatmap([[1, 2], [3, 4]]).cmap(name).render()


def test_unknown_colormap_suggests() -> None:
    with pytest.raises(ValueError, match="Did you mean"):
        sp.heatmap([[1, 2]]).cmap("virids")


@pytest.mark.parametrize("name", ["jet", "rainbow", "RdYlGn", "turbo_r"])
def test_misleading_colormaps_warn(name: str) -> None:
    with pytest.warns(sp.ColormapWarning, match="avoid"):
        sp.heatmap([[1, 2]]).cmap(name)


def test_log_and_levels() -> None:
    plot = sp.heatmap([[1, 10], [100, 1000]]).cmap(log=True)
    assert isinstance(_mesh(plot).norm, LogNorm)
    stepped = sp.heatmap([[1, 2], [3, 4]]).cmap(levels=3)
    assert isinstance(_mesh(stepped).norm, BoundaryNorm)
    with pytest.raises(sp.DataShapeError, match="positive"):
        sp.heatmap([[0, 1]]).cmap(log=True).render()


def test_colormaps_listing() -> None:
    table = sp.colormaps()
    assert {"blues", "RdBu", "tol_sunset"} <= set(table.index)
    assert set(sp.colormaps("diverging")["kind"]) == {"diverging"}
    assert "red-green" in table.loc["RdYlGn", "note"]


def test_theme_sequential_can_name_a_colormap() -> None:
    plot = sp.heatmap([[1, 2], [3, 4]]).theme(sequential=["viridis"])
    assert _mesh(plot).cmap.name == "viridis"


# ----------------------------------------------------------------- values
def test_values_pick_readable_text_color() -> None:
    plot = sp.heatmap([[0.0, 1.0]]).values(".1f")
    texts = {t.get_text(): t.get_color() for t in plot.ax.texts}
    assert set(texts) == {"0.0", "1.0"}
    assert texts["1.0"] == "#ffffff"  # darkest cell
    assert texts["0.0"] != "#ffffff"


def test_custom_cell_labels() -> None:
    plot = sp.heatmap([[1, 2], [3, 4]]).values(labels=[["*", ""], ["", "**"]])
    assert sorted(t.get_text() for t in plot.ax.texts) == ["*", "**"]


def test_values_that_do_not_fit_are_all_hidden() -> None:
    values = np.arange(400.0).reshape(20, 20) * 1e6
    plot = sp.heatmap(values).values(".6e").ticklabels(rows=False, cols=False)
    with pytest.warns(sp.LabelsHiddenWarning, match="cell values"):
        plot.render()
    assert not any(t.get_visible() for t in plot._body.value_texts)


def test_mask_triangle_and_nan_cells() -> None:
    corr = pd.DataFrame(np.eye(3), index=list("abc"), columns=list("abc"))
    plot = sp.heatmap(corr).mask("upper").values(".0f")
    assert len(plot.ax.texts) == 6  # lower triangle + diagonal
    data = plot.source_data()
    assert np.isnan(data.loc["a", "c"])
    assert data.loc["c", "a"] == 0
    with_diag = sp.heatmap(corr).mask("lower", diagonal=True).values(".0f")
    assert len(with_diag.ax.texts) == 3
    missing = sp.heatmap([[1.0, np.nan]], missing="gap")
    assert len([c for c in missing.ax.collections if isinstance(c, QuadMesh)]) == 2


def test_mask_errors() -> None:
    with pytest.raises(sp.DataShapeError, match="square"):
        sp.heatmap([[1, 2, 3]]).mask("upper")
    with pytest.raises(sp.DataShapeError, match="shape"):
        sp.heatmap([[1, 2]]).mask(np.zeros((3, 3), bool))


# ---------------------------------------------------------------- grouping
def test_groups_reorder_and_split_rows(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).groups(rows=expr["pathway"])
    rows = list(plot.source_data().index)
    assert rows == list(expr.index)  # already contiguous: data order kept
    plot.render()
    labels = [t.get_text() for t, *_ in plot._body.group_texts]
    assert labels == ["Signal", "Cycle", "Metab"]
    centers = [t.get_position()[1] for t in plot.ax.get_yticklabels()]
    steps = np.diff(centers)
    assert steps.max() > 1.05  # gaps between groups


def test_groups_from_column_name_in_wide_table(expr: pd.DataFrame) -> None:
    shuffled = expr.iloc[[0, 4, 8, 1, 5, 9]]
    plot = sp.heatmap(shuffled).groups(rows="pathway")
    assert list(plot.source_data().index) == ["G0", "G1", "G4", "G5", "G8", "G9"]


def test_column_groups_from_long_table() -> None:
    long = pd.DataFrame(
        {
            "gene": ["a", "a", "a", "b", "b", "b"],
            "sample": ["s1", "s2", "s3"] * 2,
            "cond": ["ctrl", "trt", "ctrl"] * 2,
            "v": range(6),
        }
    )
    plot = sp.heatmap(long, x="sample", y="gene", value="v").groups(cols="cond")
    assert list(plot.source_data().columns) == ["s1", "s3", "s2"]


def test_group_errors(expr: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="not found"):
        sp.heatmap(expr).groups(rows="nope")
    with pytest.raises(sp.DataShapeError, match="wide table"):
        sp.heatmap(expr).groups(cols="pathway")
    with pytest.raises(sp.DataShapeError, match="no group"):
        sp.heatmap(expr).groups(rows={"G0": "x"})
    with pytest.raises(sp.DataShapeError, match="values for"):
        sp.heatmap(expr).groups(rows=["a", "b"])


def test_group_bar_colors_follow_colors_mapping(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).groups(rows="pathway").colors({"Signal": "#ff0000"})
    colors = plot._category_colors(plot.style())
    assert colors["Signal"] == "#ff0000"
    assert len(set(colors.values())) == 3


def test_tracks_add_legend(expr: pd.DataFrame) -> None:
    from matplotlib.text import Text

    cond = {c: c[:-1] for c in expr.columns[:6]}
    plot = sp.heatmap(expr).tracks(
        rows={"Pathway": "pathway"}, cols={"Condition": cond}
    )
    plot.render()
    legend = plot._track_legend
    assert legend is not None
    texts = [a.get_text() for a in legend.findobj(Text) if a.get_text()]
    assert texts == ["Pathway", "Signal", "Cycle", "Metab", "Condition", "ctrl", "trt"]
    hidden = sp.heatmap(expr).tracks(rows={"P": "pathway"}).legend(False)
    hidden.render()
    assert hidden._track_legend is None


def test_track_layout_does_not_overlap(expr: pd.DataFrame) -> None:
    cond = {c: c[:-1] for c in expr.columns[:6]}
    batch = dict(zip(expr.columns[:6], "ABABAB", strict=True))
    plot = sp.heatmap(expr).tracks(
        rows={"Pathway": "pathway"}, cols={"Condition": cond, "Batch": batch}
    )
    fig = plot.fig
    renderer = fig.canvas.get_renderer()
    cells = plot.ax.get_window_extent(renderer)
    strips = [a.get_window_extent(renderer) for a in plot._body.axes[:3]]
    row_strip, *col_strips = strips
    assert row_strip.x1 < cells.x0  # gap between strip and cells
    assert all(b.y0 > cells.y1 for b in col_strips)
    assert (
        abs(col_strips[0].y0 - col_strips[1].y1) > 1
        or abs(col_strips[1].y0 - col_strips[0].y1) > 1
    )
    names = [t.get_window_extent(renderer) for t in plot._body.track_names]
    cbar = plot._cax.get_window_extent(renderer)
    assert all(n.x1 < cbar.x0 for n in names)
    legend = plot._track_legend.get_window_extent(renderer)
    assert legend.y1 <= cbar.y0
    assert legend.x1 <= fig.bbox.x1 + 1


# -------------------------------------------------------------- clustering
def test_cluster_groups_similar_rows() -> None:
    values = np.array([[0, 0], [10, 10], [0.1, 0], [10, 10.2]])
    plot = sp.heatmap(values).cluster(cols=False)
    order = list(plot.source_data().index)
    assert {frozenset(order[:2]), frozenset(order[2:])} == {
        frozenset({0, 2}),
        frozenset({1, 3}),
    }
    plot.render()
    assert len(plot._body.axes) >= 2  # dendrogram + colorbar


def test_cluster_split_rows(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).scale("row").cluster(split_rows=3, cols=False)
    layout = plot._layouts()["row"]
    assert [g for g, _ in layout.blocks] == [1, 2, 3]
    assert sum(len(labels) for _, labels in layout.blocks) == 12


def test_cluster_within_groups(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).groups(rows="pathway").cluster(cols=False)
    blocks = plot._layouts()["row"].blocks
    assert [set(labels) for _, labels in blocks] == [
        {"G0", "G1", "G2", "G3"},
        {"G4", "G5", "G6", "G7"},
        {"G8", "G9", "G10", "G11"},
    ]


def test_cluster_errors(expr: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="missing"):
        sp.heatmap([[1, np.nan], [2, 3]]).cluster().render()
    with pytest.raises(ValueError, match="ward"):
        sp.heatmap(expr).cluster(method="ward", metric="correlation")
    with pytest.raises(ValueError, match="either"):
        sp.heatmap(expr).groups(rows="pathway").cluster(split_rows=2).render()
    with pytest.raises(ValueError, match="Did you mean"):
        sp.heatmap(expr).cluster(method="avarage")


def test_linkage_heights_and_cut() -> None:
    points = np.array([[0.0], [1.0], [5.0], [6.0], [20.0]])
    tree = cluster.linkage(points, "single")
    assert [h for *_, h in tree.merges] == [1.0, 1.0, 4.0, 14.0]
    assert cluster.cut(tree, 2).tolist() == [0, 0, 0, 0, 1]
    assert cluster.cut(tree, 3).tolist() == [0, 0, 1, 1, 2]
    complete = cluster.linkage(points, "complete")
    assert complete.merges[-1][2] == 20.0
    assert sorted(cluster.linkage(points, "ward").order) == [0, 1, 2, 3, 4]


def test_correlation_distance() -> None:
    d = cluster.distances(np.array([[1, 2, 3], [2, 4, 6], [3, 2, 1]]), "correlation")
    assert d[0, 1] == pytest.approx(0)
    assert d[0, 2] == pytest.approx(2)


# ------------------------------------------------------------------ labels
def test_ticklabels_subset_rename_and_hide(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).ticklabels(rows=["G2", "G7"], cols={"ctrl1": "Control 1"})
    assert _ticks(plot.ax.get_yticklabels()) == ["G2", "G7"]
    assert _ticks(plot.ax.get_xticklabels())[0] == "Control 1"
    hidden = sp.heatmap(expr).ticklabels(rows=False)
    assert _ticks(hidden.ax.get_yticklabels()) == []


def test_too_many_rows_hide_labels_with_warning() -> None:
    values = np.zeros((200, 3))
    plot = sp.heatmap(values)
    with pytest.warns(sp.LabelsHiddenWarning, match="200 row labels"):
        plot.render()
    assert _ticks(plot.ax.get_yticklabels()) == []


def test_highlight_emphasizes_labels(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).highlight("G3")
    weights = {t.get_text(): t.get_fontweight() for t in plot.ax.get_yticklabels()}
    assert weights["G3"] == "bold"
    assert weights["G0"] == "normal"


def test_log_axis_is_rejected() -> None:
    with pytest.raises(TypeError, match="cmap"):
        sp.heatmap([[1, 2]]).log()


# ---------------------------------------------------------------- colorbar
def test_colorbar_position_label_and_hiding(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr).colorbar("Expression (TPM)", position="bottom")
    plot.render()
    assert plot._cax is not None
    assert plot._cax.get_xlabel() == "Expression (TPM)"
    assert plot._cax.get_position().y1 < plot.ax.get_position().y0
    hidden = sp.heatmap(expr).colorbar(position=False)
    hidden.render()
    assert len(hidden.ax.child_axes) == 0


def test_colorbar_sits_right_of_row_labels(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr)
    fig = plot.fig
    renderer = fig.canvas.get_renderer()
    labels = plot.ax.yaxis.get_tightbbox(renderer)
    assert plot._cax.get_window_extent(renderer).x0 > labels.x1


def test_colorbar_pad_moves_it_away_from_labels(expr: pd.DataFrame) -> None:
    def gap(plot: sp.HeatmapPlot) -> float:
        renderer = plot.fig.canvas.get_renderer()
        labels = plot.ax.yaxis.get_tightbbox(renderer)
        return plot._cax.get_window_extent(renderer).x0 - labels.x1

    default, padded = sp.heatmap(expr), sp.heatmap(expr).colorbar(pad=20)
    extra = gap(padded) - gap(default)
    assert extra == pytest.approx((20 - 0.06 * 72) / 72 * padded.fig.dpi, abs=1)
    with pytest.raises(ValueError, match="pad"):
        sp.heatmap(expr).colorbar(pad=-1)


def test_everything_stays_inside_the_figure(expr: pd.DataFrame) -> None:
    plot = (
        sp.heatmap(expr)
        .scale("row")
        .groups(rows="pathway")
        .cluster(cols=False)
        .tracks(cols={"Condition": {c: c[:-1] for c in expr.columns[:6]}})
        .preset("nature", width="double")
    )
    fig = plot.fig
    renderer = fig.canvas.get_renderer()
    box = plot.ax.get_tightbbox(renderer)
    assert box.x0 >= -1
    assert box.y0 >= -1
    assert box.x1 <= fig.bbox.x1 + 1
    assert box.y1 <= fig.bbox.y1 + 1


def test_square_cells(expr: pd.DataFrame) -> None:
    plot = sp.heatmap(expr, square=True)
    assert plot.ax.get_aspect() == 1.0


def test_render_into_existing_axes(expr: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    sp.heatmap(expr).groups(rows="pathway").render(ax=ax)
    assert ax.collections
    plt.close(fig)


def test_options_document_every_argument() -> None:
    table = sp.HeatmapPlot.options()
    for verb in ("cmap", "colorbar", "values", "scale", "cluster", "groups", "tracks"):
        assert verb in table.index
        assert (sp.HeatmapPlot.options(verb)["description"] != "").all()


@pytest.mark.parametrize("colorbar", ["right", "bottom", "none"])
def test_layout_is_stable_across_redraws(expr: pd.DataFrame, colorbar: str) -> None:
    cond = {c: c[:-1] for c in expr.columns[:6]}
    plot = (
        sp.heatmap(expr)
        .scale("row")
        .groups(rows="pathway", cols=cond)
        .cluster(cols=False)
        .tracks(rows={"Pathway": "pathway"}, cols={"Condition": cond})
        .colorbar(position=colorbar)
    )
    fig = plot.fig
    before = plot.ax.get_position().bounds
    fig.draw_without_rendering()
    fig.draw_without_rendering()
    assert plot.ax.get_position().bounds == pytest.approx(before)
    renderer = fig.canvas.get_renderer()
    assert plot._track_legend.get_window_extent(renderer).x1 <= fig.bbox.x1 + 1
