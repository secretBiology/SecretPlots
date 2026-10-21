from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_hex
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
