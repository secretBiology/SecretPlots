import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex

import SecretPlots as sp
from SecretPlots.plots.scatter import _lowess, _t_quantile


@pytest.fixture
def people() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    age = rng.uniform(25, 75, 40)
    sex = np.array(["F", "M"] * 20)
    return pd.DataFrame(
        {
            "age": age,
            "bp": 95 + 0.6 * age + np.where(sex == "M", 8, 0) + rng.normal(0, 5, 40),
            "sex": sex,
            "bmi": rng.uniform(18, 35, 40),
        }
    )


def _points(plot: sp.ScatterPlot) -> list[PathCollection]:
    return [c for c in plot.ax.collections if isinstance(c, PathCollection)]


def test_one_marker_per_row_with_column_labels(people: pd.DataFrame) -> None:
    plot = sp.scatter(people, x="age", y="bp")
    (points,) = _points(plot)
    assert len(points.get_offsets()) == 40
    assert plot.ax.get_xlabel() == "age"
    assert plot.ax.get_ylabel() == "bp"
    assert to_hex(points.get_facecolor()[0], keep_alpha=False) == (
        plot.style().theme.primary
    )
    assert plot.ax.get_legend() is None


@pytest.mark.parametrize(
    "make",
    [
        lambda: sp.scatter(x=[1, 2, 3], y=[2, 4, 5]),
        lambda: sp.scatter({"a": [1, 2, 3], "b": [2, 4, 5]}, x="a", y="b"),
        lambda: sp.scatter(np.array([[1, 2], [2, 4], [3, 5]])),
        lambda: sp.scatter(pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 5]})),
    ],
)
def test_input_shapes(make) -> None:
    (points,) = _points(make())
    assert points.get_offsets().tolist() == [[1, 2], [2, 4], [3, 5]]


def test_missing_values_are_dropped() -> None:
    plot = sp.scatter(x=[1, 2, np.nan, 4], y=[1, None, 3, 4])
    (points,) = _points(plot)
    assert len(points.get_offsets()) == 2


def test_hue_groups_get_palette_colors_and_legend(people: pd.DataFrame) -> None:
    plot = sp.scatter(people, x="age", y="bp", hue="sex", hue_order=["M", "F"])
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["M", "F"]
    assert legend.get_title().get_text() == "sex"
    palette = plot.style().theme.palette
    colors = [to_hex(c.get_facecolor()[0], keep_alpha=False) for c in _points(plot)]
    assert colors == list(palette[:2])


def test_size_scales_marker_area_and_adds_size_legend(people: pd.DataFrame) -> None:
    plot = sp.scatter(people, x="age", y="bp", size="bmi")
    points = _points(plot)[0]
    areas = points.get_sizes()
    smallest = people["bmi"].idxmin()
    largest = people["bmi"].idxmax()
    assert areas[largest] > areas[smallest] * 5
    legend = plot.ax.get_legend()
    assert legend.get_title().get_text() == "bmi"
    assert len(legend.get_texts()) == 3


def test_highlight_mutes_other_groups(people: pd.DataFrame) -> None:
    plot = sp.scatter(people, x="age", y="bp", hue="sex").highlight("M")
    theme = plot.style().theme
    colors = {
        c.get_label(): to_hex(c.get_facecolor()[0], keep_alpha=False)
        for c in _points(plot)
    }
    assert colors["F"] == theme.muted
    assert colors["M"] != theme.muted


def test_highlight_needs_groups(people: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="no groups"):
        _ = sp.scatter(people, x="age", y="bp").highlight("x").fig


def test_linear_fit_recovers_line_and_band() -> None:
    x = np.arange(10.0)
    plot = sp.scatter(x=x, y=2 * x + 1).fit("linear", stats=True)
    (line,) = plot.ax.get_lines()
    assert line.get_ydata()[0] == pytest.approx(1)
    assert line.get_ydata()[-1] == pytest.approx(19)
    texts = [t.get_text() for t in plot.ax.texts]
    assert texts == ["y = 2x + 1, R\N{SUPERSCRIPT TWO} = 1.00"]


def test_fit_per_group_and_pooled(people: pd.DataFrame) -> None:
    grouped = sp.scatter(people, x="age", y="bp", hue="sex").fit()
    assert len(grouped.ax.get_lines()) == 2
    assert len(grouped.ax.collections) == 4  # 2 point sets + 2 bands
    pooled = sp.scatter(people, x="age", y="bp", hue="sex").fit(
        per_group=False, ci=None
    )
    assert len(pooled.ax.get_lines()) == 1


def test_fit_can_be_removed(people: pd.DataFrame) -> None:
    plot = sp.scatter(people, x="age", y="bp").fit().fit(None)
    assert plot.ax.get_lines() == []


def test_lowess_follows_a_curve() -> None:
    x = np.linspace(0, 2 * np.pi, 200)
    fit = _lowess(x, np.sin(x), frac=0.2, what="test")
    assert np.max(np.abs(fit.line - np.sin(fit.grid))) < 0.05


@pytest.mark.parametrize(
    ("df", "expected"),
    [(1, 12.7062), (2, 4.3027), (3, 3.1824), (5, 2.5706), (10, 2.2281), (30, 2.0423)],
)
def test_t_quantile_matches_tables(df: int, expected: float) -> None:
    assert _t_quantile(0.975, df) == pytest.approx(expected, rel=2e-3)


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda p: p.fit("loess"), "Did you mean 'lowess'"),
        (lambda p: p.fit(ci=95), "between 0 and 1"),
        (lambda p: p.fit("lowess", stats=True), "linear"),
    ],
)
def test_fit_rejects_bad_options(people: pd.DataFrame, call, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        call(sp.scatter(people, x="age", y="bp"))


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda df: sp.scatter(df, x="ages", y="bp"), "Column 'ages' not found"),
        (lambda df: sp.scatter(df, x="age", y="sex"), "'sex' must be numeric"),
        (lambda df: sp.scatter(df), "Pass x= and y="),
        (lambda df: sp.scatter(x="age", y="bp"), "look like column names"),
        (lambda df: sp.scatter(x=[1, 2], y=[1]), "equal length"),
    ],
)
def test_helpful_data_errors(people: pd.DataFrame, make, match: str) -> None:
    with pytest.raises(sp.DataShapeError, match=match):
        make(people)


def test_too_few_points_for_band() -> None:
    plot = sp.scatter(x=[1, 2], y=[1, 2]).fit()
    with pytest.raises(sp.DataShapeError, match="ci=None"):
        _ = plot.fig
    assert sp.scatter(x=[1, 2], y=[1, 2]).fit(ci=None).fig is not None


def test_marker_style_from_theme(people: pd.DataFrame) -> None:
    plot = sp.scatter(people, x="age", y="bp").theme(marker_size=10, marker_alpha=0.5)
    (points,) = _points(plot)
    assert points.get_sizes()[0] == pytest.approx(100)
    assert points.get_alpha() == 0.5


@pytest.mark.parametrize("marker", ["s", "^", "D"])
def test_marker_shape_from_theme(people: pd.DataFrame, marker: str) -> None:
    from matplotlib.markers import MarkerStyle

    plot = sp.scatter(people, x="age", y="bp", hue="sex").theme(marker=marker)
    style = MarkerStyle(marker)
    expected = style.get_path().transformed(style.get_transform()).vertices
    for points in _points(plot):
        np.testing.assert_allclose(points.get_paths()[0].vertices, expected)


def test_unfilled_marker_uses_group_color(people: pd.DataFrame) -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        plot = sp.scatter(people, x="age", y="bp").theme(marker="x")
        (points,) = _points(plot)
    assert to_hex(points.get_edgecolor()[0], keep_alpha=False) == (
        plot.style().theme.primary
    )


def test_unknown_marker_is_rejected(people: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Unknown marker 'q'"):
        _ = sp.scatter(people, x="age", y="bp").theme(marker="q").fig


def _shape(points: PathCollection) -> np.ndarray:
    return points.get_paths()[0].vertices


def _marker_vertices(marker: str) -> np.ndarray:
    from matplotlib.markers import MarkerStyle

    style = MarkerStyle(marker)
    return style.get_path().transformed(style.get_transform()).vertices


def test_style_column_gets_marker_shapes_and_legend(people: pd.DataFrame) -> None:
    people["smoker"] = np.array(["no", "yes", "yes", "no"] * 10)
    plot = sp.scatter(people, x="age", y="bp", hue="sex", style="smoker")
    drawn = [p for p in _points(plot) if len(p.get_offsets())]
    assert sum(len(p.get_offsets()) for p in drawn) == 40
    assert len(drawn) == 4  # 2 groups x 2 styles
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["F", "M", "no", "yes"]
    assert legend.get_title().get_text() == "sex / smoker"
    handles = legend.legend_handles
    np.testing.assert_allclose(_shape(handles[2]), _marker_vertices("o"))
    np.testing.assert_allclose(_shape(handles[3]), _marker_vertices("s"))


def test_style_starts_from_theme_marker_and_follows_order(
    people: pd.DataFrame,
) -> None:
    plot = sp.scatter(
        people, x="age", y="bp", style="sex", style_order=["M", "F"]
    ).theme(marker="D")
    handles = plot.ax.get_legend().legend_handles
    assert [t.get_text() for t in plot.ax.get_legend().get_texts()] == ["M", "F"]
    np.testing.assert_allclose(_shape(handles[0]), _marker_vertices("D"))
    np.testing.assert_allclose(_shape(handles[1]), _marker_vertices("o"))


def test_style_same_as_hue_merges_legend(people: pd.DataFrame) -> None:
    plot = sp.scatter(people, x="age", y="bp", hue="sex", style="sex")
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["F", "M"]
    assert legend.get_title().get_text() == "sex"
    handles = legend.legend_handles
    np.testing.assert_allclose(_shape(handles[1]), _marker_vertices("s"))
    palette = plot.style().theme.palette
    assert to_hex(handles[1].get_facecolor()[0], keep_alpha=False) == palette[1]


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda df: sp.scatter(df, x="age", y="bp", style_order=["F"]), "style_order"),
        (lambda df: sp.scatter(df, x="age", y="bp", style="smoke"), "not found"),
        (
            lambda df: sp.scatter(
                df.assign(k=df.index % 9), x="age", y="bp", style="k"
            ),
            "only 8 marker shapes",
        ),
    ],
)
def test_style_errors(people: pd.DataFrame, make, match: str) -> None:
    with pytest.raises(sp.DataShapeError, match=match):
        make(people)


def test_options_documented() -> None:
    assert "fit" in sp.ScatterPlot.options().index
    table = sp.ScatterPlot.options("fit")
    assert (table.description != "").all()
