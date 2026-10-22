"""Behavioral regressions found during the package review."""

import io

import numpy as np
import pandas as pd
import pytest
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
