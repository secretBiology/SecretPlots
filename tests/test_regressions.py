"""Behavioral regressions found during the package review."""

import io
import typing

import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_rgb
from matplotlib.figure import Figure

import SecretPlots as sp


@pytest.fixture
def grouped():
    return pd.DataFrame(
        {
            "x": [1, 2, 1, 2] * 2,
            "y": [3, 4, 5, 6, 4, 5, 6, 7],
            "group": ["a", "a", "b", "b"] * 2,
        }
    )


@pytest.mark.parametrize("error", [None, "sd", "ci"])
def test_rename_preserves_line_values_and_intervals(grouped, error):
    p = sp.line(grouped, x="x", y="y", hue="group", error=error)
    before = p.source_data()
    p.render()
    p.grouplabels({"a": "Control", "b": "Treatment"})
    after = p.source_data()
    pd.testing.assert_frame_equal(
        before.drop(columns="group"), after.drop(columns="group")
    )
    assert set(after.group) == {"Control", "Treatment"}
    assert sum(len(line.get_ydata()) for line in p.ax.lines) == 4


@pytest.mark.parametrize("bins", [2, 3, "auto"])
@pytest.mark.parametrize("values", [[1, 2, 4, 8], [0.1, 0.3, 0.7], [3, 9, 27]])
def test_log_histogram_conserves_observations(values, bins):
    p = sp.histogram(values, bins=bins).log("x")
    assert p.source_data()["count"].sum() == len(values)


def test_log_binwidth_and_explicit_range():
    for width in (0.5, 1):
        with pytest.raises(ValueError, match="ratio"):
            sp.histogram([1, 2, 4, 8], binwidth=width).log("x").source_data()
    p = sp.histogram([1, 2, 4, 8], binwidth=2).log("x")
    assert p.source_data()["count"].sum() == 4
    p = sp.histogram([0.5, 1, 2, 4, 8, 16], bins=3, binrange=(1, 8)).log("x")
    assert p.source_data()["count"].sum() == 4


@pytest.mark.parametrize("bad", [np.nan, np.inf, -0.1, 1.1])
def test_invalid_p_values_rejected(bad):
    with pytest.raises(ValueError, match="p-values"):
        sp.box({"a": [1, 2, 3], "b": [2, 3, 4]}).compare(p=[bad], format="stars")


@pytest.mark.parametrize("estimator", ["mean", "sum", None])
def test_line_sort_false_preserves_trajectory(estimator):
    p = sp.line(x=[3, 1, 2], y=[30, 10, 20], sort=False, estimator=estimator)
    assert p.source_data().x.tolist() == [3, 1, 2]
    assert p.ax.lines[0].get_xdata().tolist() == [3, 1, 2]


def test_categorical_order_survives_long_and_wide_input():
    cat = pd.Categorical(
        ["high", "low", "medium"], categories=["low", "medium", "high"], ordered=True
    )
    frame = pd.DataFrame({"dose": cat, "response": [3, 1, 2]})
    for p in (
        sp.line(frame, x="dose", y="response"),
        sp.area(frame, x="dose", y="response"),
        sp.line(frame.set_index("dose")),
    ):
        assert [t.get_text() for t in p.ax.get_xticklabels()] == [
            "low",
            "medium",
            "high",
        ]


def test_context_selection_survives_lazy_render_and_mutation():
    with sp.use(preset="nature", width="double", theme="dark"):
        p = sp.bar([1, 2])
    assert p.style().preset.name == "nature"
    assert p.style().width == pytest.approx(
        sp.presets.get("nature").target.width("double")
    )
    first = p.fig
    sp.use(preset="web")
    p.labels(y="Value")
    assert p.style().preset.name == "nature"
    assert p.fig is not first


@pytest.mark.parametrize("column", ["x", "y", "hue"])
def test_wide_column_names_do_not_collide(column):
    p = sp.bar(pd.DataFrame({column: [1, 2], "other": [3, 4]}))
    assert sorted(r.get_height() for r in p.ax.patches) == [1, 2, 3, 4]


@pytest.mark.parametrize("whis", [0, 0.1])
def test_two_observation_box_has_valid_whiskers(whis):
    p = sp.box([1, 2], whis=whis).points()
    row = p.source_data().iloc[0]
    assert row.whisker_low == row.q1
    assert row.whisker_high == row.q3
    p.render()


@pytest.mark.parametrize("value", [0.01, 0.1, 1, 10])
def test_constant_log_heatmap_renders(value):
    p = sp.heatmap([[value, value]]).cmap(log=True)
    norm = p.ax.collections[0].norm
    assert 0 < norm.vmin < value < norm.vmax


@pytest.mark.parametrize(
    "factory",
    [
        lambda: sp.bar([1, 2]),
        lambda: sp.line([1, 2, 3]).endlabels(values=".0f"),
        lambda: sp.heatmap([[1, 2], [3, 4]]).cluster(),
        lambda: sp.box([1, 2, 3, 4, 5]).points(),
        lambda: sp.raincloud([1, 2, 3, 4, 5]),
    ],
)
def test_copy_after_render_is_independent(factory):
    original = factory()
    first = original.fig
    clone = original.copy().labels(title="Copy").preset("nature")
    assert clone.fig is not first
    assert original.fig is first
    assert original.ax.get_title() == ""
    assert "Copy" in [
        clone.ax.get_title(loc=loc) for loc in ("left", "center", "right")
    ]


def test_copy_data_and_renames_are_independent(grouped):
    original = sp.line(grouped, x="x", y="y", hue="group")
    clone = original.copy().grouplabels(["Control", "Treatment"])
    assert set(original.source_data().group) == {"a", "b"}
    assert set(clone.source_data().group) == {"Control", "Treatment"}


def test_axis_formats_do_not_change_source_values():
    p = sp.line([0.1, 0.25, 0.5]).format_axis("y", "percent", decimals=1)
    assert p.ax.yaxis.get_major_formatter()(0.25, 0) == "25.0%"
    assert p.source_data()["0"].tolist() == [0.1, 0.25, 0.5]
    p.format_axis("y", "currency", prefix="€", scale=1e-3, suffix="k")
    assert p.ax.yaxis.get_major_formatter()(2500, 0) == "€2k"
    dates = pd.date_range("2026-01-01", periods=3)
    p = sp.line(pd.Series([1, 2, 3], index=dates)).format_axis(
        "x", "date", date_format="%b %d"
    )
    p.render()
    assert any("Jan" in t.get_text() for t in p.ax.get_xticklabels())


def test_encode_groups_distinguishes_shapes_and_dashes(grouped):
    line = sp.line(grouped, x="x", y="y", hue="group").encode_groups()
    lines = [a for a in line.ax.lines if len(a.get_xdata())]
    assert len({a.get_linestyle() for a in lines}) == 2
    assert len({a.get_marker() for a in lines}) == 2
    points = sp.scatter(grouped, x="x", y="y", hue="group").encode_groups()
    paths = [c.get_paths()[0].vertices for c in points.ax.collections]
    assert not np.array_equal(paths[0], paths[1])


def test_chrome_wraps_inside_mobile_figure_and_exports(tmp_path):
    p = (
        sp.bar([3, 4])
        .preset("ft-like", width="mobile")
        .size(height="4in")
        .chrome(
            title="A long but perfectly ordinary chart title explaining the result",
            source="A rather long source description that must fit within this narrow figure",
        )
    )
    fig = p.fig
    fig.canvas.draw()
    assert "\n" in fig.texts[0].get_text()
    for text in fig.texts:
        bounds = text.get_window_extent(fig.canvas.get_renderer())
        assert bounds.x0 >= 0
        assert bounds.x1 <= fig.bbox.x1
        assert bounds.y0 >= 0
        assert bounds.y1 <= fig.bbox.y1
    for fmt in ("png", "svg"):
        p.save(tmp_path / f"wrapped.{fmt}")
        assert (tmp_path / f"wrapped.{fmt}").stat().st_size > 0
    p.copy().preset("nature").size(width="180mm", height="120mm").save(
        tmp_path / "wrapped.pdf"
    )


def test_existing_axes_and_subfigure_rendering():
    fig = Figure()
    sub = fig.subfigures(1, 1)
    ax = sub.subplots()
    assert sp.bar([1, 2]).render(ax=ax) is fig
    buffer = io.BytesIO()
    fig.savefig(buffer, format="pdf")
    assert buffer.getvalue().startswith(b"%PDF")


@pytest.mark.parametrize("fmt", ["svg", "pdf"])
def test_heatmap_tracks_save_as_vector(tmp_path, fmt):
    matrix = pd.DataFrame(np.arange(16.0).reshape(4, 4), columns=list("abcd"))
    track = {"a": "x", "b": "x", "c": "y", "d": "y"}
    sp.heatmap(matrix).tracks(cols={"Group": track}).save(tmp_path / f"h.{fmt}")
    assert (tmp_path / f"h.{fmt}").stat().st_size > 0


def test_render_into_existing_axes_keeps_style():
    sp.use(preset="nature")
    own = sp.bar([1, 2]).render().axes[0]
    fig = Figure()
    ax = fig.subplots()
    sp.bar([1, 2]).render(ax=ax)
    sp.reset()
    fig.draw_without_rendering()  # outside the style's rc_context
    theirs, mine = ax.get_yticklabels()[0], own.get_yticklabels()[0]
    assert theirs.get_fontsize() == mine.get_fontsize()
    assert theirs.get_fontfamily() == mine.get_fontfamily()
    assert ax.yaxis.label.get_fontsize() == own.yaxis.label.get_fontsize()
    assert ax.spines["top"].get_visible() == own.spines["top"].get_visible()


@pytest.mark.parametrize(
    "factory", [sp.histogram, sp.box, sp.violin, sp.raincloud, sp.scatter, sp.bar]
)
def test_signatures_only_offer_supported_missing_policies(factory):
    assert typing.get_type_hints(factory)["missing"] == sp.DropPolicy


@pytest.mark.parametrize(("preset", "minimum"), [("slide-16x9", 2.0), ("poster", 3.0)])
def test_large_presets_scale_marks(preset, minimum):
    base = sp.scatter(x=[1, 2], y=[1, 2]).style().theme
    theme = sp.scatter(x=[1, 2], y=[1, 2]).preset(preset).style().theme
    assert theme.line_width >= minimum
    assert theme.marker_size > base.marker_size * 1.5


def test_economist_end_labels_clear_right_ticks_and_axis_title():
    frame = pd.DataFrame(
        {
            "year": np.tile(np.arange(2000, 2011), 2),
            "g": np.repeat(["Alpha", "Beta"], 11),
            "v": np.r_[np.linspace(0, 5, 11), np.linspace(2, 3, 11)],
        }
    )
    p = (
        sp.line(frame, x="year", y="v", hue="g")
        .endlabels()
        .labels(y="Index")
        .preset("economist-like")
    )
    fig, ax = p.fig, p.ax
    renderer = fig.canvas.get_renderer()
    low, high = sorted(ax.get_ylim())
    ticks = [
        t.label2.get_window_extent(renderer)
        for t in ax.yaxis.get_major_ticks()
        if low <= t.get_loc() <= high and t.label2.get_text()
    ]
    ends = [t.get_window_extent(renderer) for t in p._end_texts]
    title = ax.yaxis.label.get_window_extent(renderer)
    assert min(e.x0 for e in ends) > max(t.x1 for t in ticks)
    assert title.x0 > max(e.x1 for e in ends)


@pytest.mark.parametrize("kind", ["box", "violin", "raincloud", "bar"])
def test_color_list_without_hue_colors_each_category(kind):
    frame = pd.DataFrame({"g": np.repeat(list("abc"), 5), "v": np.arange(15.0)})
    colors = ["#ff0000", "#00ff00", "#0000ff"]
    plot = getattr(sp, kind)(frame, x="g", y="v").colors(colors)
    color = plot._category_color_fn(plot.style(), [None], list("abc"), grouped=False)
    assert [color(None, c) for c in "abc"] == colors
    single = getattr(sp, kind)(frame, x="g", y="v").colors(["#ff0000"])
    color = single._category_color_fn(
        single.style(), [None], list("abc"), grouped=False
    )
    assert {color(None, c) for c in "abc"} == {"#ff0000"}


def test_split_violin_brackets_span_both_halves():
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {"g": np.repeat(list("ab"), 20), "h": np.tile(["m", "f"], 20)}
    ).assign(v=rng.normal(size=40))
    ax = sp.violin(frame, x="g", y="v", hue="h", split=True).compare().ax
    brackets = [line.get_xdata() for line in ax.lines if len(line.get_xdata()) == 4]
    assert brackets
    assert all(xs[2] - xs[0] > 0.1 for xs in brackets)


@pytest.mark.parametrize("stat", ["count", "density", "percent"])
def test_kde_on_log_axis_matches_bars(stat):
    values = np.random.default_rng(0).lognormal(1, 0.6, 4000)
    p = sp.histogram(values, stat=stat, bins=30).log("x").kde()
    curve = p.ax.lines[-1]
    edges = p.bin_edges
    heights = np.array([bar.get_height() for bar in p.ax.patches])
    expected = np.interp(
        np.sqrt(edges[:-1] * edges[1:]), curve.get_xdata(), curve.get_ydata()
    )
    tall = heights > heights.max() / 3
    np.testing.assert_allclose(expected[tall], heights[tall], rtol=0.15)


def test_default_diverging_map_runs_blue_to_red():
    stops = sp.heatmap([[0.0, 1.0]]).style().theme.diverging
    blue, red = stops[0], stops[-1]
    assert int(blue[5:7], 16) > int(blue[1:3], 16)  # more blue than red
    assert int(red[1:3], 16) > int(red[5:7], 16)


def test_raincloud_caption_describes_box_beside_cloud():
    frame = pd.DataFrame({"g": np.repeat(list("ab"), 10), "v": np.arange(20.0)})
    caption = sp.raincloud(frame, x="g", y="v").caption()
    assert "raincloud" in caption
    assert "Inside" not in caption


def test_default_legend_title_is_sentence_case():
    frame = pd.DataFrame(
        {"x": list("aabb"), "y": [1, 2, 3, 4], "cell_type": list("pqpq")}
    )
    plot = sp.bar(frame, x="x", y="y", hue="cell_type")
    assert plot.ax.get_legend().get_title().get_text() == "Cell type"
    frame = frame.rename(columns={"cell_type": "pH"})
    plot = sp.bar(frame, x="x", y="y", hue="pH")
    assert plot.ax.get_legend().get_title().get_text() == "pH"


def test_one_highlighted_group_uses_highlight_color_with_or_without_hue():
    frame = pd.DataFrame({"x": list("aabbcc"), "h": list("pqpqpq"), "y": range(6)})
    accent = sp.bar(frame, x="x", y="y").style().theme.highlight
    no_hue = sp.bar(frame.iloc[::2], x="x", y="y").highlight("b")
    hue = sp.bar(frame, x="x", y="y", hue="h").highlight("q")
    for plot in (no_hue, hue):
        faces = {bar.get_facecolor()[:3] for bar in plot.ax.patches}
        assert to_rgb(accent) in faces
