import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_hex
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, StepPatch

import SecretPlots as sp


@pytest.fixture
def ages() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "age": np.r_[rng.normal(40, 8, 300), rng.normal(55, 6, 200)],
            "sex": ["F"] * 300 + ["M"] * 200,
        }
    )


def _bars(plot: sp.HistogramPlot) -> list[Rectangle]:
    return [p for p in plot.ax.patches if isinstance(p, Rectangle)]


def _steps(plot: sp.HistogramPlot) -> list[StepPatch]:
    return [p for p in plot.ax.patches if isinstance(p, StepPatch)]


def _curves(plot: sp.HistogramPlot) -> list[Line2D]:
    return [line for line in plot.ax.lines if len(line.get_xdata()) > 2]


def test_counts_match_numpy(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", bins=10)
    counts, edges = np.histogram(ages["age"], 10)
    assert [b.get_height() for b in _bars(plot)] == counts.tolist()
    assert np.allclose(plot.bin_edges, edges)
    assert plot.ax.get_xlabel() == "age"
    assert plot.ax.get_ylabel() == "Count"
    assert {to_hex(b.get_facecolor()) for b in _bars(plot)} == {
        plot.style().theme.primary
    }


@pytest.mark.parametrize(
    ("stat", "total", "label"),
    [
        ("probability", 1.0, "Proportion"),
        ("proportion", 1.0, "Proportion"),
        ("percent", 100.0, "Percent"),
    ],
)
def test_normalized_heights_sum(
    ages: pd.DataFrame, stat: str, total: float, label: str
) -> None:
    plot = sp.histogram(ages, x="age", stat=stat)
    assert sum(b.get_height() for b in _bars(plot)) == pytest.approx(total)
    assert plot.ax.get_ylabel() == label


def test_density_has_unit_area(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", stat="density")
    area = sum(b.get_height() * b.get_width() for b in _bars(plot))
    assert area == pytest.approx(1.0)
    assert plot.ax.get_ylabel() == "Density"


def test_frequency_is_count_per_unit(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", binwidth=5, stat="frequency")
    counts = np.histogram(ages["age"], plot.bin_edges)[0]
    assert [b.get_height() for b in _bars(plot)] == pytest.approx(counts / 5)


def test_density_per_group_unless_common_norm(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", hue="sex", stat="density")
    widths = np.diff(plot.bin_edges)
    for heights, _ in plot._heights(plot.bin_edges).values():
        assert (heights * widths).sum() == pytest.approx(1.0)
    common = sp.histogram(ages, x="age", hue="sex", stat="density", common_norm=True)
    areas = [(h * widths).sum() for h, _ in common._heights(common.bin_edges).values()]
    assert areas == pytest.approx([0.6, 0.4])


def test_groups_overlay_as_steps_with_legend(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", hue="sex")
    assert len(_steps(plot)) == 4  # outline + light fill per group
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["F", "M"]
    assert legend.get_title().get_text() == "sex"


def test_stack_and_dodge(ages: pd.DataFrame) -> None:
    stacked = sp.histogram(ages, x="age", hue="sex", multiple="stack", bins=8)
    bars = _bars(stacked)
    tops = [b.get_y() + b.get_height() for b in bars[8:]]
    assert max(tops) == pytest.approx(
        max(np.histogram(ages["age"], stacked.bin_edges)[0])
    )
    dodged = sp.histogram(ages, x="age", hue="sex", multiple="dodge", bins=8)
    widths = {round(b.get_width(), 6) for b in _bars(dodged)}
    assert len(widths) == 1
    assert widths.pop() == pytest.approx(np.diff(dodged.bin_edges)[0] / 2)


def test_binwidth_binrange_and_discrete() -> None:
    values = [1, 2, 2, 3, 3, 3, 9] * 5
    plot = sp.histogram(values, binwidth=2, binrange=(0, 10))
    assert plot.bin_edges.tolist() == [0, 2, 4, 6, 8, 10]
    discrete = sp.histogram(values, discrete=True)
    assert discrete.bin_edges[0] == 0.5
    assert np.allclose(np.diff(discrete.bin_edges), 1)
    assert [t for t in discrete.ax.get_xticks()][:3] == [1, 2, 3]


def test_log_axis_uses_log_spaced_bins() -> None:
    values = np.geomspace(1, 1000, 60)
    plot = sp.histogram(values, bins=3).log("x")
    assert np.allclose(plot.bin_edges, [1, 10, 100, 1000])
    assert plot.ax.get_xscale() == "log"
    with pytest.raises(sp.DataShapeError, match="positive"):
        sp.histogram([-1.0, *values]).log("x").render()


def test_cumulative(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", stat="probability", cumulative=True)
    heights = [b.get_height() for b in _bars(plot)]
    assert heights[-1] == pytest.approx(1.0)
    assert heights == sorted(heights)
    assert plot.ax.get_ylabel() == "Cumulative proportion"


def test_kde_matches_stat_scale(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", stat="density").kde()
    (curve,) = _curves(plot)
    x, y = curve.get_data()
    assert np.trapezoid(y, x) == pytest.approx(1.0, abs=0.03)
    assert x.min() == pytest.approx(ages["age"].min())  # cut=0: inside data
    counts = sp.histogram(ages, x="age", binwidth=2).kde()
    (curve,) = _curves(counts)
    x, y = curve.get_data()
    assert np.trapezoid(y, x) == pytest.approx(len(ages) * 2, rel=0.03)


def test_kde_per_group_and_normal_fit(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", hue="sex", stat="density").kde().fit()
    curves = _curves(plot)
    assert len(curves) == 4
    assert {c.get_linestyle() for c in curves} == {"-", "--"}
    with pytest.raises(ValueError, match="stacked"):
        sp.histogram(ages, x="age", hue="sex", multiple="stack").kde().render()


def test_kde_color(ages: pd.DataFrame) -> None:
    (curve,) = _curves(sp.histogram(ages, x="age").kde(color="red"))
    assert to_hex(curve.get_color()) == "#ff0000"
    plot = sp.histogram(ages, x="age", hue="sex").kde(color={"F": "black"})
    colors = {to_hex(c.get_color()) for c in _curves(plot)}
    assert "#000000" in colors
    assert len(colors) == 2  # M keeps its group color
    with pytest.raises(ValueError, match="Not a color"):
        sp.histogram(ages, x="age").kde(color="reddish")
    with pytest.raises(sp.DataShapeError, match="not a group"):
        sp.histogram(ages, x="age", hue="sex").kde(color={"X": "red"})


def test_cumulative_curves_end_at_total(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", stat="percent", cumulative=True).kde().fit()
    for curve in _curves(plot):
        y = curve.get_ydata()
        # Smooth curves leave a little mass past the largest value.
        assert y[-1] == pytest.approx(100, abs=3)
        assert (np.diff(y) >= -1e-9).all()


def test_refline_rug_and_show_n(ages: pd.DataFrame) -> None:
    plot = (
        sp.histogram(ages, x="age", hue="sex")
        .refline("median", 50, label=True)
        .rug()
        .show_n()
    )
    vertical = [
        line for line in plot.ax.lines if line.get_xdata()[0] == line.get_xdata()[-1]
    ]
    assert len(vertical) == 3
    positions = sorted(line.get_xdata()[0] for line in vertical)
    assert positions[1] == 50
    texts = [t.get_text() for t in plot.ax.get_legend().get_texts()]
    assert texts == ["F (n = 300)", "M (n = 200)"]
    assert any(t.get_text().startswith("median") for t in plot.ax.texts)
    single = sp.histogram(ages, x="age").show_n()
    assert any(t.get_text() == "n = 500" for t in single.ax.texts)


def test_small_samples_warn_unless_rug() -> None:
    with pytest.warns(sp.SmallSampleWarning, match="rug"):
        sp.histogram([1.0, 2, 3, 4, 5]).render()
    sp.histogram([1.0, 2, 3, 4, 5]).rug().render()


@pytest.mark.parametrize(
    ("make", "groups"),
    [
        (
            lambda r: sp.histogram({"a": r.normal(size=40), "b": r.normal(size=30)}),
            ["a", "b"],
        ),
        (
            lambda r: sp.histogram(
                pd.DataFrame({"x": r.normal(size=40), "y": r.normal(size=40)})
            ),
            ["x", "y"],
        ),
        (lambda r: sp.histogram(r.normal(size=(40, 2))), [0, 1]),
        (lambda r: sp.histogram(x=r.normal(size=60), hue=["p", "q"] * 30), ["p", "q"]),
    ],
)
def test_input_shapes_with_groups(make, groups: list) -> None:
    plot = make(np.random.default_rng(1))
    assert plot._samples.hue_order == groups


def test_series_and_missing_values() -> None:
    values = pd.Series([1.0, np.nan, 2, np.inf, 3] * 10, name="dose")
    plot = sp.histogram(values)
    assert len(plot._samples.frame) == 30
    assert plot.ax.get_xlabel() == "dose"


def test_horizontal(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", orient="h")
    assert plot.ax.get_ylabel() == "age"
    assert plot.ax.get_xlabel() == "Count"
    assert all(b.get_x() == 0 for b in _bars(plot))


def test_highlight_and_colors(ages: pd.DataFrame) -> None:
    plot = sp.histogram(ages, x="age", hue="sex", element="bars").highlight("M")
    colors = {to_hex(b.get_facecolor(), keep_alpha=False) for b in _bars(plot)}
    assert plot.style().theme.muted in colors
    mapped = sp.histogram(ages, x="age", hue="sex").colors({"F": "#ff0000"})
    assert to_hex(_steps(mapped)[0].get_edgecolor(), keep_alpha=False) == "#ff0000"


def test_colors_alpha_multiplies_layer_transparency(ages: pd.DataFrame) -> None:
    def alphas(plot: sp.HistogramPlot) -> list[float]:
        return sorted({round(b.get_facecolor()[3], 3) for b in _bars(plot)})

    layered = sp.histogram(ages, x="age", hue="sex", element="bars")
    (layer,) = alphas(layered)
    faded = alphas(layered.colors(alpha=0.5))
    assert faded == pytest.approx([layer * 0.5], abs=0.005)
    single = alphas(sp.histogram(ages, x="age").colors(alpha=0.5))
    assert single == pytest.approx([0.5], abs=0.005)


def test_source_data(ages: pd.DataFrame) -> None:
    table = sp.histogram(ages, x="age", hue="sex", stat="density", bins=5).source_data()
    assert list(table.columns) == [
        "sex",
        "bin_start",
        "bin_end",
        "count",
        "density",
        "n",
    ]
    assert len(table) == 10
    assert table.groupby("sex")["count"].sum().to_dict() == {"F": 300, "M": 200}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"stat": "frequncy"}, "Did you mean 'frequency'"),
        ({"multiple": "stacked"}, "Did you mean 'stack'"),
        ({"bins": "freedman"}, "Unknown bins"),
        ({"bins": 0}, "at least 1"),
        ({"binwidth": -1}, "positive"),
        ({"stat": "frequency", "cumulative": True}, "cumulative"),
        ({"multiple": "dodge", "element": "step"}, "dodge"),
    ],
)
def test_helpful_errors(kwargs: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        sp.histogram(list(range(40)), **kwargs)


def test_hist_alias() -> None:
    assert sp.hist is sp.histogram


def test_options_document_every_argument() -> None:
    for verb in ("kde", "fit", "refline", "rug", "show_n"):
        assert (sp.HistogramPlot.options(verb)["description"] != "").all()
