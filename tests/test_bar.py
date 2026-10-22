from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_hex, to_rgb
from matplotlib.figure import Figure

import SecretPlots as sp


def _bars(plot: sp.BarPlot) -> list:
    return [p for p in plot.ax.patches]


def test_simple_bars_use_primary_color() -> None:
    plot = sp.bar({"a": 3, "b": 5, "c": 2})
    heights = [p.get_height() for p in _bars(plot)]
    assert heights == [3, 5, 2]
    assert {to_hex(p.get_facecolor()) for p in _bars(plot)} == {
        plot.style().theme.primary
    }


def test_grouped_means_and_error(expression: pd.DataFrame) -> None:
    plot = sp.bar(expression, x="gene", y="tpm", hue="sample", error="sd")
    table = plot._table
    gata4 = table[(table.x == "GATA4") & (table.hue == "ctrl")].iloc[0]
    assert gata4.value == pytest.approx(12)
    assert gata4.sd == pytest.approx(1.0)
    assert len(_bars(plot)) == 8
    assert plot.ax.get_legend() is not None
    assert plot.ax.get_xlabel() == "gene"
    assert plot.ax.get_ylabel() == "tpm"


def test_stacked_bars_accumulate() -> None:
    plot = sp.bar({"a": {"x": 1, "y": 2}, "b": {"x": 3, "y": 4}}, stack=True)
    tops = sorted(p.get_y() + p.get_height() for p in _bars(plot))
    assert tops == [1, 3, 3, 7]


def test_error_needs_replicates() -> None:
    with pytest.raises(sp.DataShapeError, match="replicates"):
        sp.bar({"a": 1, "b": 2}, error="sd")


def test_stack_with_error_rejected() -> None:
    with pytest.raises(ValueError, match="stacked"):
        sp.bar({"a": [1, 2]}, stack=True, error="sd")


def test_horizontal_first_category_on_top() -> None:
    plot = sp.bar({"first": 1, "second": 2}, orient="h")
    low, high = plot.ax.get_ylim()
    assert low > high  # inverted
    assert [t.get_text() for t in plot.ax.get_yticklabels()] == ["first", "second"]


def test_sort_desc() -> None:
    plot = sp.bar({"a": 1, "b": 3, "c": 2}).sort("desc")
    assert [t.get_text() for t in plot.ax.get_xticklabels()] == ["b", "c", "a"]


def test_highlight_mutes_others() -> None:
    plot = sp.bar({"a": 1, "b": 3}).highlight("b")
    theme = plot.style().theme
    colors = [to_hex(p.get_facecolor()) for p in _bars(plot)]
    assert colors == [theme.muted, theme.highlight]


def test_highlight_unknown_category() -> None:
    with pytest.raises(sp.DataShapeError, match="highlight"):
        _ = sp.bar({"a": 1}).highlight("zzz").fig


def test_colors_mapping_and_palette() -> None:
    plot = sp.bar({"a": 1, "b": 2}).colors({"b": "#ff0000"})
    assert to_hex(_bars(plot)[1].get_facecolor()) == "#ff0000"
    plot = sp.bar({"a": 1}).colors(["#123456"])
    assert (
        to_hex(_bars(plot)[0].get_facecolor()) == "#123456"
    )  # primary derived from palette


def test_colors_alpha() -> None:
    plot = sp.bar({"a": 1, "b": 2}).colors({"b": "#ff0000"}, alpha=0.4)
    faces = [p.get_facecolor() for p in _bars(plot)]
    assert [f[3] for f in faces] == pytest.approx([0.4, 0.4], abs=0.005)
    assert to_hex(faces[1]) == "#ff0000"
    # alpha alone keeps the colors; colors alone keeps the alpha
    plot = sp.bar({"a": 1}).colors(alpha=0.5).colors("#123456")
    assert _bars(plot)[0].get_facecolor() == pytest.approx(
        (*to_rgb("#123456"), 0.5), abs=0.005
    )
    with pytest.raises(ValueError, match="between 0 and 1"):
        sp.bar({"a": 1}).colors(alpha=1.5)


def test_values_and_hidden_labels_warning() -> None:
    plot = sp.bar({"a": 1.5, "b": 2.25}).values(".2f")
    texts = [t.get_text() for t in plot.ax.texts]
    assert texts == ["1.50", "2.25"]

    crowded = sp.bar({f"c{i}": 123456.789 for i in range(30)}).values(".6g").size("2in")
    with pytest.warns(sp.LabelsHiddenWarning):
        _ = crowded.fig


def test_many_groups_extend_palette() -> None:
    data = {"a": {f"g{i}": i + 1 for i in range(10)}}
    plot = sp.bar(data).legend(False)
    with pytest.warns(sp.PaletteExtendedWarning):
        plot.render()
    colors = {to_hex(p.get_facecolor()) for p in _bars(plot)}
    assert len(colors) == 10


def test_long_labels_rotate() -> None:
    plot = sp.bar({f"a rather long category name {i}": i for i in range(8)}).size("3in")
    assert plot.ax.get_xticklabels()[0].get_rotation() in (45, 90)


def test_axis_titles_hidden_by_preset_but_explicit_wins(
    expression: pd.DataFrame,
) -> None:
    plot = sp.bar(expression, x="gene", y="tpm").preset("bbc")
    assert plot.ax.get_xlabel() == ""
    plot = sp.bar(expression, x="gene", y="tpm").preset("bbc").labels(y="TPM")
    assert plot.ax.get_ylabel() == "TPM"


def test_use_context_and_per_plot_preset() -> None:
    with sp.use(preset="nature"):
        assert sp.bar([1]).style().preset.name == "nature"
        assert sp.bar([1]).preset("bbc").style().preset.name == "bbc"
    assert sp.bar([1]).style().preset.name == "screen"


def test_use_width_name() -> None:
    with sp.use(preset="nature", width="double"):
        assert sp.bar([1]).fig.get_size_inches()[0] == pytest.approx(183 / 25.4)


def test_chrome_reserves_space() -> None:
    plain = sp.bar({"a": 1}).fig
    titled = sp.bar({"a": 1}).chrome(title="Headline", subtitle="Sub", source="Lab").fig
    plain.draw_without_rendering()
    titled.draw_without_rendering()
    assert titled.axes[0].get_position().height < plain.axes[0].get_position().height
    assert {"Headline", "Sub", "Source: Lab"} <= {t.get_text() for t in titled.texts}


def test_render_into_existing_axes() -> None:
    fig = Figure()
    ax = fig.add_subplot()
    assert sp.bar({"a": 1}).render(ax) is fig
    assert len(ax.patches) == 1


def test_nature_pdf_size_and_embedded_fonts(tmp_path: Path) -> None:
    path = tmp_path / "fig.pdf"
    sp.bar({"a": 1, "b": 2}).preset("nature").save(path)
    content = path.read_bytes()
    assert b"/FontFile2" in content  # TrueType embedded, not Type 3
    width_pt = 89 / 25.4 * 72
    assert f"{width_pt:.2f}".encode()[:5] in content


def test_save_warns_for_unaccepted_format(tmp_path: Path) -> None:
    with pytest.warns(sp.FormatWarning, match="expects"):
        sp.bar({"a": 1}).preset("nature").save(tmp_path / "fig.jpg")


def test_repr_png_for_notebooks() -> None:
    data, meta = sp.bar({"a": 1}).preset("web", width="mobile")._repr_png_()
    assert data.startswith(b"\x89PNG")
    assert meta["width"] == 360


def test_verbs_invalidate_cache() -> None:
    plot = sp.bar({"a": 1})
    first = plot.fig
    plot.labels(title="New")
    assert plot.fig is not first


def test_nan_values_skipped() -> None:
    plot = sp.bar({"a": 1, "b": np.nan, "c": 2}).values()
    assert [t.get_text() for t in plot.ax.texts] == ["1", "", "2"]


def _ticks(plot: sp.BarPlot) -> list[str]:
    return [t.get_text() for t in plot.ax.get_xticklabels()]


def test_ticklabels_for_plain_list() -> None:
    plot = sp.bar([3, 5, 2]).ticklabels(["ctrl", "drug A", "drug B"])
    assert _ticks(plot) == ["ctrl", "drug A", "drug B"]


def test_ticklabels_follow_data_order_when_sorted() -> None:
    plot = sp.bar([3, 5, 2]).ticklabels(["a", "b", "c"]).sort("desc")
    assert _ticks(plot) == ["b", "a", "c"]
    assert [p.get_height() for p in _bars(plot)] == [5, 3, 2]


def test_ticklabels_mapping_is_partial() -> None:
    plot = sp.bar({"GATA4": 1, "TBX5": 2}).ticklabels({"GATA4": "Gata4"})
    assert _ticks(plot) == ["Gata4", "TBX5"]


def test_renamed_categories_work_with_highlight_and_colors() -> None:
    plot = sp.bar([3, 5]).ticklabels(["a", "b"]).highlight("b")
    theme = plot.style().theme
    assert [to_hex(p.get_facecolor()) for p in _bars(plot)] == [
        theme.muted,
        theme.highlight,
    ]
    plot = sp.bar([3, 5]).ticklabels(["a", "b"]).colors({"a": "#ff0000"})
    assert to_hex(_bars(plot)[0].get_facecolor()) == "#ff0000"


def test_ticklabel_style() -> None:
    plot = sp.bar({"a rather long name": 1, "another long name": 2}).size("2in")
    plot.ticklabels(rotation=30, italic=True)
    label = plot.ax.get_xticklabels()[0]
    assert label.get_rotation() == 30
    assert label.get_fontstyle() == "italic"


def test_ticklabels_horizontal() -> None:
    plot = sp.bar([1, 2], orient="h").ticklabels(["x", "y"])
    assert [t.get_text() for t in plot.ax.get_yticklabels()] == ["x", "y"]


def test_grouplabels_for_matrix_input() -> None:
    plot = (
        sp.bar([[1, 2], [3, 4], [5, 6]])
        .ticklabels(["GATA4", "NKX2-5", "TBX5"])
        .grouplabels(["ctrl", "treated"])
    )
    assert _ticks(plot) == ["GATA4", "NKX2-5", "TBX5"]
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["ctrl", "treated"]


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda p: p.ticklabels(["only one"]), "1 labels for 3"),
        (lambda p: p.ticklabels(["a", "a", "b"]), "unique"),
        (lambda p: p.ticklabels({"zzz": "x"}), "not in the data"),
        (lambda p: p.grouplabels(["g"]), "no groups"),
    ],
)
def test_ticklabel_errors(call, message: str) -> None:
    with pytest.raises(sp.DataShapeError, match=message):
        call(sp.bar([1, 2, 3]))


def test_ticklabels_rejects_single_string() -> None:
    with pytest.raises(TypeError, match="list"):
        sp.bar([1, 2]).ticklabels("ab")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"estimator": "sd"}, r"error='sd'"),
        ({"estimator": "std"}, r"error='sd'"),
        ({"estimator": "sem"}, r"error='sem'"),
        ({"estimator": "meen"}, "Did you mean 'mean'"),
        ({"estimator": 3}, "Unknown estimator"),
        ({"error": "std"}, r"Did you mean error='sd'"),
        ({"error": "se"}, r"Did you mean error='sem'"),
        ({"error": "ci"}, "Unknown error='ci'"),
    ],
)
def test_helpful_errors_for_estimator_and_error(kwargs: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        sp.bar({"a": [1, 2]}, **kwargs)


def test_callable_estimator() -> None:
    plot = sp.bar({"a": [1, 5], "b": [2, 3]}, estimator=np.max)
    assert [p.get_height() for p in _bars(plot)] == [5, 3]


def _grid_on(axis) -> bool:
    return any(line.get_visible() for line in axis.get_gridlines())


@pytest.mark.parametrize(
    ("grid", "orient", "x_on", "y_on"),
    [
        ("x", "v", True, False),
        ("y", "v", False, True),
        ("x", "h", True, False),
        ("y", "h", False, True),
        ("value", "v", False, True),
        ("value", "h", True, False),
        ("category", "v", True, False),
        ("both", "v", True, True),
        ("none", "v", False, False),
        (True, "v", True, True),
        (False, "v", False, False),
    ],
)
def test_grid_modes(grid: object, orient: str, x_on: bool, y_on: bool) -> None:
    plot = sp.bar({"a": 1, "b": 2}, orient=orient).theme(grid=grid)
    assert _grid_on(plot.ax.xaxis) is x_on
    assert _grid_on(plot.ax.yaxis) is y_on


def test_legend_options(expression: pd.DataFrame) -> None:
    plot = sp.bar(expression, x="gene", y="tpm", hue="sample").legend(
        "inside", ncols=2, fontsize=7, loc="lower right", anchor=(0.9, 0.1)
    )
    legend = plot.ax.get_legend()
    assert legend._ncols == 2
    assert {t.get_fontsize() for t in legend.get_texts()} == {7}
    assert legend.get_title().get_fontsize() == 7
    assert legend._loc == 4  # "lower right"
    box = legend.get_bbox_to_anchor().transformed(plot.ax.transAxes.inverted())
    assert (box.x0, box.y0) == pytest.approx((0.9, 0.1))


def test_legend_explicit_ncols_disables_wrapping(expression: pd.DataFrame) -> None:
    plot = (
        sp.bar(expression, x="gene", y="tpm", hue="sample")
        .size(2, 2)
        .legend("top", ncols=2)
    )
    assert plot.ax.get_legend()._ncols == 2


@pytest.mark.parametrize(
    "kwargs",
    [{"ncols": 0}, {"ncols": 1.5}, {"fontsize": 0}, {"anchor": (1, 2, 3)}],
)
def test_legend_rejects_bad_options(kwargs: dict) -> None:
    with pytest.raises(ValueError, match="legend"):
        sp.bar({"a": 1}).legend(**kwargs)


def test_options_lists_every_verb() -> None:
    table = sp.bar({"a": 1}).options()
    assert {"labels", "legend", "theme", "values", "ticklabels"} <= set(table.index)
    assert {"options", "show", "render", "explain"}.isdisjoint(table.index)
    assert table.loc["labels", "options"] == "x, y, title"


@pytest.mark.parametrize("verb", list(sp.BarPlot.options().index))
def test_options_documents_every_argument(verb: str) -> None:
    table = sp.BarPlot.options(verb)
    undocumented = table.index[table.description == ""].tolist()
    assert not undocumented, f"{verb}(): add {undocumented} to the Args: docstring"


def test_options_for_one_verb() -> None:
    table = sp.BarPlot.options("legend")
    assert list(table.index) == [
        "position",
        "title",
        "ncols",
        "fontsize",
        "loc",
        "anchor",
    ]
    assert table.loc["position", "default"] == "auto"
    assert "'inside'" in table.loc["position", "allowed"]
    assert table.loc["anchor", "allowed"] == "(number, number)"
    assert "``" not in table.loc["loc", "description"]
    assert sp.BarPlot.options("theme").index[-1] == "**overrides"


def test_options_unknown_verb_suggests() -> None:
    with pytest.raises(ValueError, match="Did you mean 'legend'"):
        sp.BarPlot.options("legnd")


def _legend_title(plot: sp.BarPlot) -> str:
    return plot.ax.get_legend().get_title().get_text()


def test_legend_title(expression: pd.DataFrame) -> None:
    plot = sp.bar(expression, x="gene", y="tpm", hue="sample")
    assert _legend_title(plot) == "sample"
    assert _legend_title(plot.legend(title="Condition")) == "Condition"
    assert _legend_title(plot.legend(title="")) == ""
    hidden_by_theme = plot.theme(legend_title=False).legend(title="Condition")
    assert _legend_title(hidden_by_theme) == "Condition"


def test_top_legend_wraps_inside_figure(expression: pd.DataFrame) -> None:
    plot = (
        sp.bar(expression, x="sample", y="tpm", hue="gene")
        .preset("nature")
        .size(8, 4, scale_text=True)
    )
    with pytest.warns(sp.LimitExceededWarning):
        fig = plot.fig
    extent = plot.ax.get_legend().get_window_extent(fig.canvas.get_renderer())
    assert extent.x1 <= fig.bbox.x1
    assert plot.ax.get_legend()._ncols < 4


@pytest.mark.parametrize("position", ["right", "top"])
def test_outside_legend_clears_axis_decorations(
    expression: pd.DataFrame, position: str
) -> None:
    # economist-like draws the value axis (ticks and title) on the right.
    plot = (
        sp.bar(expression, x="sample", y="tpm", hue="gene", error="sd")
        .preset("economist-like")
        .legend(position)
        .labels(y="TPM")
    )
    fig = plot.fig
    renderer = fig.canvas.get_renderer()
    legend = plot.ax.get_legend().get_window_extent(renderer)
    for axis in (plot.ax.xaxis, plot.ax.yaxis):
        assert not legend.overlaps(axis.get_tightbbox(renderer))
    assert legend.x1 <= fig.bbox.x1 + 1
