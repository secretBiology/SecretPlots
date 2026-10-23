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


# --------------------------------------------------- independent audit findings


def test_notch_drawn_at_full_width():
    p = sp.box({"A": [0, 1, 2, 3], "B": [2, 3, 4, 5]}, notch=True).points()
    with pytest.warns(sp.SmallSampleWarning, match="reaches beyond the box"):
        p.render()
    ys = [patch.get_xy()[:, 1] for patch in p.ax.patches[:2]]
    for y, median in zip(ys, (1.5, 3.5), strict=True):
        half = 1.58 * 1.5 / 2  # IQR 1.5, n 4
        assert y.min() == pytest.approx(median - half)
        assert y.max() == pytest.approx(median + half)


def test_forest_marker_area_proportional_to_weight():
    d = pd.DataFrame(
        {
            "label": ["zero", "1%", "100%"],
            "w": [0, 1, 100],
            "estimate": [0.8, 0.9, 1.1],
            "lower": [0.5, 0.6, 0.8],
            "upper": [1.2, 1.4, 1.5],
        }
    )
    p = sp.forest(d, label="label", weight="w")
    with pytest.warns(sp.PolicyWarning, match="zero weight"):
        p.render()
    sizes = [
        line.get_markersize()
        for ax in p.fig.axes
        for line in ax.lines
        if line.get_marker() == "s"
    ]
    assert len(sizes) == 2  # no marker for the zero weight
    assert (sizes[0] / sizes[1]) ** 2 == pytest.approx(0.01)
    floored = sp.forest(d[d.w > 0], label="label", weight="w").markers(min_size=3)
    with pytest.warns(sp.PolicyWarning, match="min_size"):
        floored.render()


def test_forest_all_zero_weights_rejected():
    d = pd.DataFrame(
        {"label": ["a"], "w": [0], "estimate": [1.0], "lower": [0.5], "upper": [2.0]}
    )
    with pytest.raises(sp.DataShapeError, match="zero"):
        sp.forest(d, label="label", weight="w").render()


def test_source_data_never_overwrites_input_columns():
    d = pd.DataFrame({"x": [0, 0, 1, 1], "n": [10.0, 20.0, 30.0, 40.0]})
    with pytest.warns(sp.PolicyWarning, match="'n' -> 'n_computed'"):
        out = sp.line(d, x="x", y="n").source_data()
    assert out["n"].tolist() == [15.0, 35.0]
    assert out["n_computed"].tolist() == [2, 2]

    cats = pd.DataFrame({"n": ["A"] * 4 + ["B"] * 4, "v": np.arange(8.0)})
    with pytest.warns(sp.PolicyWarning):
        out = sp.box(cats, x="n", y="v").source_data()
    assert out["n"].tolist() == ["A", "B"]

    h = pd.DataFrame({"v": np.arange(40.0), "count": ["a", "b"] * 20})
    with pytest.warns(sp.PolicyWarning):
        out = sp.histogram(h, x="v", hue="count", bins=3).source_data()
    assert set(out["count"]) == {"a", "b"}


def test_mixed_sign_stack_keeps_contributions_apart():
    d = pd.DataFrame({"Positive": [10.0] * 3, "Negative": [-8.0] * 3})
    p = sp.area(d, stack=True)
    out = p.source_data()
    pos, neg = out[out.group == "Positive"], out[out.group == "Negative"]
    assert (pos.lower == 0).all()
    assert (pos.upper == 10).all()
    assert (neg.lower == -8).all()
    assert (neg.upper == 0).all()
    assert (neg.value == -8).all()
    crossing = pd.DataFrame({"A": [1.0, -2.0, 3.0], "B": [1.0, 1.0, 1.0]})
    with pytest.warns(sp.PolicyWarning, match="change sign"):
        sp.area(crossing, stack=True).render()


def test_percent_stack_rejects_baseline():
    d = pd.DataFrame({"A": [1.0, 2.0, 3.0], "B": [3.0, 2.0, 1.0]})
    with pytest.raises(ValueError, match="baseline 0"):
        sp.area(d, stack="percent", baseline=50)


def test_percentile_bars_need_not_contain_estimate():
    p = sp.line(x=[0, 0, 1, 1], y=[10, 20, 30, 40], estimator="sum", error="pi")
    p = p.errorbars("bars")
    with pytest.warns(sp.PolicyWarning, match="outside the percentile interval"):
        p.render()
    segments = [s[:, 1] for c in p.ax.collections for s in c.get_segments()]
    assert [list(s) for s in segments] == [[10.25, 19.75], [30.25, 39.75]]


def test_lowess_finite_with_equidistant_neighbours():
    from SecretPlots.plots.scatter import _lowess

    fit = _lowess(np.array([0.0, 2.0, 99.0]), np.array([1.0, 2.0, 3.0]), 0.5, "x")
    assert np.isfinite(fit.line).all()


@pytest.mark.parametrize("offset", [1e6, 1e9, 1e12])
def test_euclidean_distances_translation_invariant(offset):
    from SecretPlots.core.cluster import distances

    a = np.array([[0.0, 0.0], [7.0, 8.0], [1.0, 1.0], [3.0, 5.0]])
    np.testing.assert_allclose(distances(a + offset), distances(a), atol=1e-6)


def test_count_curve_rejected_for_unequal_bins():
    p = sp.histogram(np.linspace(0, 10, 501), bins=[0, 1, 10], stat="count").kde()
    with pytest.raises(sp.DataShapeError, match="unequal bin"):
        p.render()
    sp.histogram(
        np.linspace(0, 10, 501), bins=[0, 1, 10], stat="density"
    ).kde().render()


def test_dense_brackets_do_not_overlap_labels():
    from matplotlib.text import Annotation

    d = {
        f"Group {i}": np.random.default_rng(i).normal(i * 0.3, 1, 12) for i in range(6)
    }
    p = sp.box(d).points().compare(correction="holm", format="stars")
    p.preset("nature").render()
    renderer = p.fig.canvas.get_renderer()
    boxes = [
        t.get_window_extent(renderer) for t in p.ax.texts if isinstance(t, Annotation)
    ]
    brackets = [line for line in p.ax.lines if len(line.get_xdata()) == 4]
    hits = 0
    for box in boxes:
        for line in brackets:
            pts = p.ax.transData.transform(np.c_[line.get_xdata(), line.get_ydata()])
            (x1, y), (x2, _) = pts[1], pts[2]
            if box.y0 + 0.5 < y < box.y1 - 0.5 and x1 < box.x1 and x2 > box.x0:
                hits += 1
    assert hits == 0


def test_dense_brackets_warn_when_they_cannot_fit():
    d = {f"G{i}": np.random.default_rng(i).normal(i * 0.3, 1, 12) for i in range(8)}
    p = sp.box(d).compare(correction="holm").preset("nature")
    with pytest.warns(sp.LabelsHiddenWarning, match="don't fit"):
        p.render()


def test_method_overrides_respect_preset_limits():
    d = pd.DataFrame(
        {"x": [0, 1, 0, 1], "y": [1, 2, 2, 3], "arm": ["A", "A", "B", "B"]}
    )
    p = sp.line(d, x="x", y="y", hue="arm").preset("nature").legend(fontsize=16)
    with pytest.warns(sp.LimitExceededWarning, match="legend fontsize 16"):
        p.render()
    sp.config.enforce_limits = True
    p = sp.box({"A": np.arange(10.0)}, linewidth=0.01).preset("cell")
    with pytest.warns(sp.ConstraintAdjustedWarning, match="outline linewidth"):
        p.render()
    assert p.ax.patches[0].get_linewidth() == pytest.approx(0.5)


def test_strict_raises_for_warning_seen_before():
    from SecretPlots.errors import emit

    with pytest.warns(sp.PaletteExtendedWarning):
        emit(sp.PaletteExtendedWarning, "first", once_key="k")
    sp.config.strict = True
    with pytest.raises(sp.PaletteExtendedWarning):
        emit(sp.PaletteExtendedWarning, "again", once_key="k")


@pytest.mark.parametrize(
    "make",
    [
        lambda: sp.area([1, 2, 3]),
        lambda: sp.line(x=[0, 0, 1, 1], y=[1, 2, 3, 4], error="sd"),
    ],
)
def test_zero_fill_alpha_is_kept(make):
    p = make().theme(fill_alpha=0)
    p.render()
    alphas = [c.get_alpha() for c in p.ax.collections if c.get_alpha() is not None]
    assert alphas
    assert all(a == 0 for a in alphas)


def test_palette_alpha_is_kept():
    p = sp.scatter(x=[1, 2], y=[2, 3], hue=["A", "B"])
    p.colors(["#ff000080", "#0000ff80"]).render()
    for points in p.ax.collections:
        assert points.get_alpha() == pytest.approx(0.85 * 128 / 255)


def test_unused_hue_levels_are_skipped_consistently():
    d = pd.DataFrame(
        {"x": [0, 1, 2, 0, 1, 2], "y": [1, 2, 3, 2, 3, 4], "arm": ["A"] * 3 + ["B"] * 3}
    )
    order = ["A", "B", "absent"]
    with pytest.warns(sp.PolicyWarning, match="'absent', which has no data"):
        sp.scatter(d, x="x", y="y", hue="arm", hue_order=order).fit().render()
    h = pd.DataFrame({"v": np.arange(40.0), "g": ["a", "b"] * 20})
    with pytest.warns(sp.PolicyWarning):
        sp.histogram(h, x="v", hue="g", hue_order=["a", "b", "c"]).kde().rug().render()
    rng = np.random.default_rng(1)
    s = pd.DataFrame(
        {"t": rng.exponential(5, 60), "e": rng.integers(0, 2, 60), "g": ["a", "b"] * 30}
    )
    with pytest.warns(sp.PolicyWarning):
        extra = sp.survival(s, time="t", event="e", hue="g", hue_order=["c", "a", "b"])
    extra = extra.pvalue()
    extra.render()
    plain = sp.survival(s, time="t", event="e", hue="g").pvalue()
    pd.testing.assert_frame_equal(extra.test_results(), plain.test_results())


@pytest.mark.parametrize(
    "make",
    [
        lambda: sp.bar([1, 2]).theme(bar_gap=1.5),
        lambda: sp.bar([1, 2]).theme(line_width=-1),
        lambda: sp.bar([1, 2]).theme(fill_alpha=float("nan")),
        lambda: sp.box({"A": np.arange(10.0)}, whis=np.nan),
        lambda: sp.violin({"A": np.arange(10.0)}, bw_adjust=np.nan),
        lambda: sp.bar([1, 2]).refline(np.nan),
        lambda: sp.bar([1, 2]).log("z"),
    ],
)
def test_invalid_numeric_options_rejected(make):
    with pytest.raises((ValueError, sp.PresetError)):
        make()


def test_infinite_whiskers_mean_range():
    p = sp.box({"A": np.arange(10.0)}, whis=np.inf)
    assert "minimum and maximum" in " ".join(p._caption_marks())


@pytest.mark.parametrize("p", [1e-10, 0.025, 0.975, 0.9999999999])
def test_t_quantile_df1_tail(p):
    from SecretPlots.core.stats import t_quantile

    expected = np.tan(np.pi * (p - 0.5)) if 0.01 < p < 0.99 else None
    value = t_quantile(p, 1)
    exact = 1 / np.tan(np.pi * min(p, 1 - p)) * (1 if p > 0.5 else -1)
    assert value == pytest.approx(exact, rel=1e-14)
    if expected is not None:
        assert value == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("test", ["wilcoxon", "Wilcox", "signed-rank"])
def test_ambiguous_wilcoxon_rejected(test):
    with pytest.raises(ValueError, match="ambiguous"):
        sp.box({"A": [1, 2, 3, 4, 5], "B": [2, 3, 4, 5, 6]}).compare(test=test)
