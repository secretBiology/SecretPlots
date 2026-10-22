import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from matplotlib.patches import Polygon

import SecretPlots as sp
from SecretPlots.plots.distribution import p_label


@pytest.fixture
def mice() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "dose": np.repeat(["0", "10", "50"], 20),
            "weight": np.r_[
                rng.normal(20, 1, 20), rng.normal(21, 1, 20), rng.normal(25, 1, 20)
            ],
            "sex": np.tile(["F", "M"], 30),
        }
    )


def _boxes(plot: sp.BoxPlot) -> list[Polygon]:
    return [p for p in plot.ax.patches if isinstance(p, Polygon)]


def _medians(plot: sp.BoxPlot) -> list[float]:
    """y of the thick (median) lines."""
    widest = max(line.get_linewidth() for line in plot.ax.lines)
    return [
        float(line.get_ydata()[0])
        for line in plot.ax.lines
        if line.get_linewidth() == widest
    ]


# ------------------------------------------------------------------ input
def test_long_frame(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight")
    assert len(_boxes(plot)) == 3
    expected = mice.groupby("dose", sort=False)["weight"].median()
    assert _medians(plot) == pytest.approx(expected.tolist())
    assert plot.ax.get_xlabel() == "dose"
    assert plot.ax.get_ylabel() == "weight"
    assert [t.get_text() for t in plot.ax.get_xticklabels()] == ["0", "10", "50"]


@pytest.mark.parametrize(
    "data",
    [
        {"a": [1, 2, 3, 4, 5], "b": [2, 3, 4, 5, 6, 7]},
        [[1, 2, 3, 4, 5], [2, 3, 4, 5, 6, 7]],
        pd.DataFrame({"a": [1, 2, 3, 4, 5, 6], "b": [2, 3, 4, 5, 6, 7]}),
        np.arange(12.0).reshape(6, 2),
    ],
    ids=["dict", "ragged-lists", "wide-frame", "2d-array"],
)
def test_one_box_per_category(data: object) -> None:
    assert len(_boxes(sp.box(data))) == 2


def test_single_distribution_has_no_category_label() -> None:
    plot = sp.box(pd.Series(np.arange(10.0), name="score"))
    assert len(_boxes(plot)) == 1
    assert plot.ax.get_ylabel() == "score"
    assert [t.get_text() for t in plot.ax.get_xticklabels()] == [""]


def test_nested_dict_gives_groups() -> None:
    data = {
        "a": {"x": [1, 2, 3, 4, 5], "y": [2, 3, 4, 5, 6]},
        "b": {"x": [3, 4, 5, 6, 7]},
    }
    plot = sp.box(data)
    assert len(_boxes(plot)) == 3  # b/y has no values
    assert [t.get_text() for t in plot.ax.get_legend().get_texts()] == ["x", "y"]


def test_missing_values_are_dropped() -> None:
    plot = sp.box({"a": [1, 2, np.nan, 4, 5, np.inf]})
    assert plot.source_data()["n"].tolist() == [4]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"x": "dose"}, "Pass y="),
        ({"y": "nope"}, "not found"),
        ({"y": "weight", "hue_order": ["F"]}, "hue_order"),
    ],
)
def test_bad_input(mice: pd.DataFrame, kwargs: dict, message: str) -> None:
    with pytest.raises(sp.DataShapeError, match=message):
        sp.box(mice, **kwargs)


# ------------------------------------------------------------------ boxes
def test_outliers_and_whiskers() -> None:
    plot = sp.box({"a": [*range(1, 11), 30]})
    outliers = [c for c in plot.ax.collections if len(c.get_offsets())]
    assert np.asarray(outliers[0].get_offsets())[:, 1].tolist() == [30.0]
    row = plot.source_data().iloc[0]
    assert (row["whisker_low"], row["whisker_high"], row["n_outliers"]) == (1, 10, 1)


def test_range_whiskers_have_no_outliers() -> None:
    plot = sp.box({"a": [*range(1, 11), 30]}, whis="range")
    assert not plot.ax.collections
    assert plot.source_data()["whisker_high"].iloc[0] == 30


def test_points_replace_outliers_unless_asked() -> None:
    data = {"a": [*range(1, 11), 30]}
    plot = sp.box(data).points()
    assert len(plot.ax.collections) == 1  # only the points
    assert len(np.asarray(plot.ax.collections[0].get_offsets())) == 11
    assert len(sp.box(data, outliers=True).points().ax.collections) == 2


def test_notched_box_has_ten_corners() -> None:
    plot = sp.box({"a": np.arange(30.0)}, notch=True)
    assert len(_boxes(plot)[0].get_xy()) == 11  # closed polygon


def test_varwidth_scales_with_sqrt_n() -> None:
    plot = sp.box({"a": np.arange(5.0) * 3, "b": np.arange(20.0)}, varwidth=True)
    widths = [np.ptp(p.get_xy()[:, 0]) for p in _boxes(plot)]
    assert widths[0] / widths[1] == pytest.approx(0.5)


def test_hue_dodges_boxes(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight", hue="sex")
    centers = sorted(np.mean(p.get_xy()[:-1, 0]) for p in _boxes(plot))
    assert len(centers) == 6
    assert centers[0] < 0 < centers[1] < 1
    assert plot.ax.get_legend().get_title().get_text() == "sex"


def test_fill_false_draws_outlines_in_group_color(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight", fill=False)
    box = _boxes(plot)[0]
    assert to_hex(box.get_edgecolor()) == plot.style().theme.primary
    assert to_hex(box.get_facecolor()) == "#ffffff"


def test_horizontal(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight", orient="h")
    assert plot.ax.get_xlabel() == "weight"
    assert [t.get_text() for t in plot.ax.get_yticklabels()] == ["0", "10", "50"]
    assert plot.ax.get_ylim()[0] > plot.ax.get_ylim()[1]  # first on top


def test_log_axis_computes_on_log_scale() -> None:
    values = [1, 10, 100, 1000, 10000]
    plot = sp.box({"a": values}).log()
    assert plot.ax.get_yscale() == "log"
    q1, q3 = plot.source_data()[["q1", "q3"]].iloc[0]
    assert (q1, q3) == pytest.approx((10, 1000))
    with pytest.raises(sp.DataShapeError, match="positive"):
        sp.box({"a": [0, 1, 2, 3, 4]}).log().render()


def test_highlight_and_color_mapping(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight").highlight("50")
    faces = [to_hex(p.get_facecolor()) for p in _boxes(plot)]
    theme = plot.style().theme
    assert faces == [theme.muted, theme.muted, theme.highlight]
    plot = sp.box(mice, x="dose", y="weight").colors({"10": "#ff0000"})
    assert to_hex(_boxes(plot)[1].get_facecolor()) == "#ff0000"


def test_small_samples_warn_until_points_are_shown() -> None:
    data = {"a": [1, 2, 3], "b": [4, 5, 6, 7, 8]}
    with pytest.warns(sp.SmallSampleWarning, match=r"\(a\).*points"):
        sp.box(data).render()
    sp.box(data).points().render()  # no warning


# ----------------------------------------------------------------- points
def test_swarm_points_do_not_overlap() -> None:
    plot = sp.box({"a": np.round(np.linspace(0, 3, 25))}).points(kind="swarm")
    xy = plot.ax.transData.transform(plot.ax.collections[0].get_offsets())
    distances = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    diameter = plot.ax.collections[0].get_sizes()[0] ** 0.5 * plot.fig.dpi / 72
    assert distances[~np.eye(25, dtype=bool)].min() >= diameter * 0.99


def test_jitter_is_reproducible() -> None:
    data = {"a": np.arange(20.0)}
    first = sp.box(data).points(kind="jitter", seed=3).ax.collections[0].get_offsets()
    again = sp.box(data).points(kind="jitter", seed=3).ax.collections[0].get_offsets()
    assert np.array_equal(first, again)
    strip = sp.box(data).points(kind="strip").ax.collections[0].get_offsets()
    assert np.all(np.asarray(strip)[:, 0] == 0)


def test_points_validation() -> None:
    with pytest.raises(ValueError, match="Did you mean 'swarm'"):
        sp.box([1, 2, 3, 4, 5]).points(kind="swram")  # type: ignore[arg-type]


def test_mean_marker(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight").mean()
    means = [np.asarray(c.get_offsets())[0, 1] for c in plot.ax.collections[-3:]]
    expected = mice.groupby("dose", sort=False)["weight"].mean().tolist()
    assert sorted(means) == pytest.approx(sorted(expected))


def test_show_n_in_tick_labels(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight").show_n()
    assert plot.ax.get_xticklabels()[0].get_text() == "0\nn = 20"
    grouped = sp.box(mice, x="dose", y="weight", hue="sex").show_n()
    assert grouped.ax.get_xticklabels()[0].get_text() == "0\nn = 10, 10"


# ---------------------------------------------------------------- compare
def test_compare_with_reference(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight").compare(ref="0", correction="holm")
    table = plot.test_results()
    assert table[["group1", "group2"]].values.tolist() == [["0", "10"], ["0", "50"]]
    assert (table["p_adjusted"] >= table["p"]).all()
    texts = [t.get_text() for t in plot.ax.texts]
    assert texts == table["label"].tolist()
    # Brackets sit above every box and the axis makes room for them.
    assert plot.ax.get_ylim()[1] > mice["weight"].max()


def test_compare_all_pairs_by_default(mice: pd.DataFrame) -> None:
    table = sp.box(mice, x="dose", y="weight").compare().test_results()
    assert len(table) == 3


def test_compare_groups_within_categories(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight", hue="sex").compare(("F", "M"))
    table = plot.test_results()
    assert table["group1"].tolist() == ["0 / F", "10 / F", "50 / F"]
    explicit = sp.box(mice, x="dose", y="weight", hue="sex").compare(
        (("0", "F"), ("50", "M"))
    )
    assert explicit.test_results()["group2"].tolist() == ["50 / M"]


def test_compare_with_own_p_values_and_stars(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight").compare(
        ("0", "10"), ("0", "50"), p=[0.2, 0.0005], format="stars", hide_ns=True
    )
    assert plot.test_results()["label"].tolist() == ["ns", "***"]
    assert [t.get_text() for t in plot.ax.texts] == ["***"]
    with pytest.raises(sp.DataShapeError, match="1 p-values for 2"):
        sp.box(mice, x="dose", y="weight").compare(("0", "10"), ("0", "50"), p=[0.1])


@pytest.mark.parametrize("test", ["wilcox", "t", "Welch", "mann_whitney"])
def test_test_aliases(mice: pd.DataFrame, test: str) -> None:
    sp.box(mice, x="dose", y="weight").compare(ref="0", test=test).test_results()


def test_compare_errors(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight")
    with pytest.raises(sp.DataShapeError, match="not a category"):
        plot.compare(("0", "5"))
    with pytest.raises(ValueError, match="Did you mean 'welch'"):
        plot.compare(test="welsh")
    with pytest.raises(ValueError, match="pair"):
        plot.compare("0")  # type: ignore[arg-type]
    with pytest.raises(sp.DataShapeError, match="compare"):
        plot.test_results()


def test_renamed_categories_are_compared_by_new_name(mice: pd.DataFrame) -> None:
    plot = (
        sp.box(mice, x="dose", y="weight")
        .ticklabels({"0": "vehicle"})
        .compare(ref="vehicle")
    )
    assert plot.test_results()["group1"].unique().tolist() == ["vehicle"]


@pytest.mark.parametrize(
    ("p", "fmt", "label"),
    [
        (0.0123, "p", "p = 0.012"),
        (0.0004, "p", "p < 0.001"),
        (0.43, "p", "p = 0.43"),
        (0.05, "stars", "*"),
        (0.00005, "stars", "****"),
        (0.051, "stars", "ns"),
    ],
)
def test_p_labels(p: float, fmt: str, label: str) -> None:
    assert p_label(p, fmt) == label  # type: ignore[arg-type]


# ---------------------------------------------------------- caption, etc.
def test_caption_defines_the_elements(mice: pd.DataFrame) -> None:
    text = (
        sp.box(mice, x="dose", y="weight")
        .points()
        .mean()
        .compare(ref="0", correction="holm", format="stars")
        .caption()
    )
    for part in (
        "median (centre line)",
        "quartiles (box limits)",
        "1.5x the interquartile range",
        "Dots show individual values",
        "Diamonds mark the mean",
        "n = 20 per distribution",
        "Mann-Whitney U test, Holm-adjusted",
        "ns, not significant",
    ):
        assert part in text
    assert "percentiles" in sp.box(mice, x="dose", y="weight", whis=(5, 95)).caption()


def test_source_data(mice: pd.DataFrame) -> None:
    table = sp.box(mice, x="dose", y="weight", hue="sex").source_data()
    assert list(table.columns[:3]) == ["dose", "sex", "n"]
    assert len(table) == 6
    first = mice[(mice["dose"] == "0") & (mice["sex"] == "F")]["weight"]
    assert table["median"].iloc[0] == pytest.approx(first.median())
    assert table["sd"].iloc[0] == pytest.approx(first.std())


def test_refline(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight").refline(22)
    assert any(line.get_linestyle() == "--" for line in plot.ax.lines)


def test_options_and_alias() -> None:
    verbs = sp.BoxPlot.options().index.tolist()
    for verb in ("points", "mean", "compare", "show_n", "ticklabels", "orient"):
        assert verb in verbs
    assert sp.boxplot is sp.box


def test_render_into_existing_axes(mice: pd.DataFrame) -> None:
    fig = Figure()
    ax: Axes = fig.add_subplot()
    sp.box(mice, x="dose", y="weight").render(ax=ax)
    assert len([p for p in ax.patches if isinstance(p, Polygon)]) == 3


def test_outline_color_and_width(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight", edgecolor="black", linewidth=2)
    box = _boxes(plot)[0]
    assert to_hex(box.get_edgecolor()) == "#000000"
    assert box.get_linewidth() == 2
    assert {to_hex(line.get_color()) for line in plot.ax.lines} == {"#000000"}


def test_edgecolor_none_removes_only_the_outline(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight", edgecolor="none")
    assert _boxes(plot)[0].get_edgecolor()[3] == 0
    assert all(line.get_color() != "none" for line in plot.ax.lines)  # medians kept
    assert (
        _boxes(sp.box(mice, x="dose", y="weight", linewidth=0))[0].get_linewidth() == 0
    )


def test_point_outline(mice: pd.DataFrame) -> None:
    dots = sp.box(mice, x="dose", y="weight").points(edgecolor="black", linewidth=1.2)
    collection = dots.ax.collections[0]
    assert to_hex(collection.get_edgecolor()[0]) == "#000000"
    assert collection.get_linewidths()[0] == 1.2
    bare = sp.box(mice, x="dose", y="weight").points(linewidth=0)
    assert bare.ax.collections[0].get_linewidths()[0] == 0


def test_outline_validation(mice: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Not a color"):
        sp.box(mice, x="dose", y="weight", edgecolor="blak")
    with pytest.raises(ValueError, match="linewidth"):
        sp.box(mice, x="dose", y="weight").points(linewidth=-1)


@pytest.mark.parametrize("orient", ["v", "h"])
def test_bracket_labels_sit_outside_their_brackets(
    mice: pd.DataFrame, orient: str
) -> None:
    plot = sp.box(mice, x="dose", y="weight", orient=orient).compare(ref="0")
    renderer = plot.fig.canvas.get_renderer()
    brackets = [line for line in plot.ax.lines if len(line.get_xdata()) == 4]
    for text, line in zip(plot.ax.texts, brackets, strict=True):
        label = text.get_window_extent(renderer)
        bracket = line.get_window_extent(renderer)
        if orient == "v":
            assert label.y0 >= bracket.y1 - 1  # above
            assert label.x0 > bracket.x0
            assert label.x1 < bracket.x1
        else:
            assert label.x0 >= bracket.x1 - 1  # to the right
            assert label.y0 > bracket.y0
            assert label.y1 < bracket.y1


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"label": "n = {n:,}"}, "n = 1,250"),
        ({"label": "({n})"}, "(1250)"),
        ({"label": "{n:_} cells"}, "1_250 cells"),
        ({"label": "{{n}} = {n}"}, "{n} = 1250"),
    ],
)
def test_show_n_label(kwargs: dict, expected: str) -> None:
    plot = sp.box({"a": np.arange(1250.0)}).show_n(**kwargs)
    assert plot.ax.get_xticklabels()[0].get_text() == f"a\n{expected}"


def test_show_n_label_with_groups(mice: pd.DataFrame) -> None:
    plot = sp.box(mice, x="dose", y="weight", hue="sex").show_n(
        label="N: {n}", sep=" / "
    )
    assert plot.ax.get_xticklabels()[0].get_text() == "0\nN: 10 / 10"


@pytest.mark.parametrize("label", ["count", "{n} and {n}", "{n:q}"])
def test_show_n_bad_label(label: str) -> None:
    with pytest.raises(ValueError, match="label"):
        sp.box({"a": np.arange(10.0)}).show_n(label=label)
