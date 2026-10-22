import itertools
import math

import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_hex
from matplotlib.container import ErrorbarContainer
from matplotlib.dates import DateFormatter, num2date
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D

import SecretPlots as sp
from SecretPlots.core.stats import t_quantile
from SecretPlots.plots.series import spread


@pytest.fixture
def mice() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for diet, slope in (("chow", 0.5), ("fat", 1.0)):
        for mouse in range(4):
            for day in range(5):
                rows.append(
                    {
                        "day": day,
                        "weight": 20 + slope * day + rng.normal(0, 1),
                        "diet": diet,
                        "mouse": f"{diet}{mouse}",
                    }
                )
    return pd.DataFrame(rows)


def _lines(plot: sp.LinePlot) -> list[Line2D]:
    """Data lines (not legend proxies, which have no points)."""
    return [line for line in plot.ax.get_lines() if len(line.get_xdata())]


def _bands(plot: sp.LinePlot) -> list[PolyCollection]:
    return [c for c in plot.ax.collections if isinstance(c, PolyCollection)]


def test_one_line_per_group_with_mean_and_labels(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight", hue="diet")
    lines = _lines(plot)
    assert len(lines) == 2
    expected = mice[mice["diet"] == "chow"].groupby("day")["weight"].mean()
    np.testing.assert_allclose(lines[0].get_ydata(), expected.to_numpy())
    palette = plot.style().theme.palette
    assert [to_hex(line.get_color()) for line in lines] == list(palette[:2])
    assert plot.ax.get_xlabel() == "day"
    assert plot.ax.get_ylabel() == "weight"
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["chow", "fat"]
    assert legend.get_title().get_text() == "diet"


def test_plot_is_an_alias() -> None:
    assert sp.plot is sp.line


@pytest.mark.parametrize(
    "make",
    [
        lambda: sp.line(x=[0, 1, 2], y=[1, 3, 2]),
        lambda: sp.line([1, 3, 2]),
        lambda: sp.line(pd.Series([1, 3, 2])),
        lambda: sp.line({"t": [0, 1, 2], "v": [1, 3, 2]}, x="t", y="v"),
        lambda: sp.line(pd.DataFrame({"v": [1, 3, 2]})),
    ],
)
def test_input_shapes(make) -> None:
    (line,) = _lines(make())
    assert list(line.get_xdata()) == [0, 1, 2]
    assert list(line.get_ydata()) == [1, 3, 2]


def test_wide_frame_draws_one_line_per_column() -> None:
    wide = pd.DataFrame({"a": [1, 2, 3], "b": [3, 2, 1]}, index=[10, 20, 30])
    plot = sp.line(wide)
    assert len(_lines(plot)) == 2
    assert [t.get_text() for t in plot.ax.get_legend().get_texts()] == ["a", "b"]
    assert list(_lines(plot)[0].get_xdata()) == [10, 20, 30]


def test_dates_on_x_get_a_date_axis() -> None:
    days = pd.date_range("2024-01-01", periods=5)
    plot = sp.line(pd.DataFrame({"d": days, "v": range(5)}), x="d", y="v")
    plot.fill(gradient=True).endlabels(values=".0f")
    assert isinstance(plot.ax.xaxis.get_major_formatter(), (DateFormatter,)) or (
        "Date" in type(plot.ax.xaxis.get_major_formatter()).__name__
    )
    low = num2date(plot.ax.get_xlim()[0]).replace(tzinfo=None)
    assert low.year == 2024


def test_category_x_is_evenly_spaced_in_order() -> None:
    frame = pd.DataFrame({"t": ["early", "mid", "late"], "v": [1, 2, 3]})
    plot = sp.line(frame, x="t", y="v", order=["early", "mid", "late"])
    assert [t.get_text() for t in plot.ax.get_xticklabels()] == [
        "early",
        "mid",
        "late",
    ]
    assert list(_lines(plot)[0].get_xdata()) == [0, 1, 2]
    with pytest.raises(sp.DataShapeError, match="order= sets"):
        sp.line(x=[1, 2], y=[1, 2], order=[1, 2])


# ------------------------------------------------------------------ errors
def test_error_sd_band(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight", error="sd")
    table = plot.source_data()
    by_day = mice.groupby("day")["weight"]
    np.testing.assert_allclose(table["sd_low"], by_day.mean() - by_day.std())
    np.testing.assert_allclose(table["sd_high"], by_day.mean() + by_day.std())
    assert len(_bands(plot)) == 1


def test_error_ci_uses_t_interval(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight", error="ci").errorbars(level=0.9)
    table = plot.source_data()
    values = mice[mice["day"] == 0]["weight"]
    half = t_quantile(0.95, len(values) - 1) * values.std() / math.sqrt(len(values))
    assert table["ci_high"][0] == pytest.approx(values.mean() + half)


def test_error_pi_is_percentiles(mice: pd.DataFrame) -> None:
    table = sp.line(mice, x="day", y="weight", error="pi").source_data()
    values = mice[mice["day"] == 2]["weight"]
    assert table["pi_low"][2] == pytest.approx(np.percentile(values, 2.5))


def test_median_ci_is_bootstrapped_and_deterministic(mice: pd.DataFrame) -> None:
    first = sp.line(mice, x="day", y="weight", error="ci", estimator="median")
    second = sp.line(mice, x="day", y="weight", error="ci", estimator="median")
    pd.testing.assert_frame_equal(first.source_data(), second.source_data())
    assert "bootstrap" in first.caption()


def test_fan_draws_nested_bands(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight", hue="diet", error="ci")
    plot.errorbars(level=(0.5, 0.95, 0.8))
    assert len(_bands(plot)) == 6
    columns = plot.source_data().columns
    assert {"ci0.5_low", "ci0.8_high", "ci0.95_low"} <= set(columns)
    assert "50%, 80%, 95% confidence intervals" in plot.caption()


def test_bars_display_and_dodge(mice: pd.DataFrame) -> None:
    plot = (
        sp.line(mice, x="day", y="weight", hue="diet", error="sem")
        .errorbars("bars", dodge=0.4, capsize=0)
        .markers()
    )
    bars = [c for c in plot.ax.containers if isinstance(c, ErrorbarContainer)]
    assert len(bars) == 2
    first, second = (_lines(plot)[i].get_xdata()[0] for i in (0, 1))
    assert second - first == pytest.approx(0.2)
    assert not _bands(plot)


def test_own_errors_symmetric_and_asymmetric() -> None:
    frame = pd.DataFrame(
        {"x": [0, 1, 2], "y": [1.0, 2, 3], "e": [0.1, 0.2, 0.3], "f": [1, 1, 1]}
    )
    table = sp.line(frame, x="x", y="y", yerr="e").source_data()
    np.testing.assert_allclose(table["error_high"], [1.1, 2.2, 3.3])
    table = sp.line(frame, x="x", y="y", yerr=("e", "f")).source_data()
    np.testing.assert_allclose(table["error_low"], [0.9, 1.8, 2.7])
    np.testing.assert_allclose(table["error_high"], [2, 3, 4])
    plot = sp.line(frame, x="x", y="y", xerr="e").errorbars("bars")
    assert any(isinstance(c, ErrorbarContainer) for c in plot.ax.containers)


def test_error_validation(mice: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Did you mean error='sd'"):
        sp.line(mice, x="day", y="weight", error="std")
    with pytest.raises(ValueError, match="looks like an error bar"):
        sp.line(mice, x="day", y="weight", estimator="sem")
    with pytest.raises(ValueError, match="not both"):
        sp.line(mice, x="day", y="weight", error="sd", yerr="weight")
    with pytest.raises(ValueError, match="first choose"):
        sp.line(mice, x="day", y="weight").errorbars("bars")
    with pytest.raises(ValueError, match="coverage"):
        sp.line(mice, x="day", y="weight", error="ci").errorbars(level=95)
    with pytest.raises(sp.DataShapeError, match="needs replicates"):
        sp.line(x=[0, 1], y=[1, 2], error="sd")
    with pytest.raises(sp.DataShapeError, match="only once per line"):
        sp.line(x=[0, 0], y=[1, 2], yerr=[0.1, 0.1])
    with pytest.raises(sp.DataShapeError, match="must not be negative"):
        sp.line(x=[0, 1], y=[1, 2], yerr=[0.1, -0.1])


def test_caption_describes_lines_and_errors(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight", hue="diet", error="sem")
    assert plot.caption() == (
        "Lines show the mean; bands the standard error of the mean; n = 4."
    )


# -------------------------------------------------------------- appearance
def test_units_draw_faint_lines_behind_the_mean(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight", hue="diet", units="mouse")
    lines = _lines(plot)
    assert len(lines) == 8 + 2
    assert sum(1 for line in lines if (line.get_alpha() or 1) < 1) == 8
    raw = sp.line(mice, x="day", y="weight", hue="diet", units="mouse", estimator=None)
    assert len(_lines(raw)) == 8


def test_style_uses_dashes_and_legend_entries(mice: pd.DataFrame) -> None:
    mice["sex"] = np.where(mice["mouse"].str[-1].astype(int) % 2, "F", "M")
    plot = sp.line(mice, x="day", y="weight", hue="diet", style="sex")
    styles = {line.get_linestyle() for line in _lines(plot)}
    assert len(styles) == 2
    legend = [t.get_text() for t in plot.ax.get_legend().get_texts()]
    assert legend == ["chow", "fat", "M", "F"]


def test_markers_filled_and_hollow(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight").markers("s", size=7)
    (line,) = _lines(plot)
    assert line.get_marker() == "s"
    assert line.get_markersize() == 7
    hollow = sp.line(mice, x="day", y="weight").markers(filled=False)
    (line,) = _lines(hollow)
    assert to_hex(line.get_markerfacecolor()) == hollow.style().theme.axes_background
    with pytest.raises(ValueError, match="Unknown marker"):
        sp.line(mice, x="day", y="weight").markers("nope")


def test_fill_sits_on_the_baseline(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight").fill()
    assert _bands(plot)
    assert plot.ax.get_ylim()[0] == 0
    gradient = sp.line(mice, x="day", y="weight").fill(gradient=True)
    assert any(isinstance(a, AxesImage) for a in gradient.ax.get_images())
    assert gradient.ax.get_ylim()[0] == 0


def test_end_labels_replace_the_legend_and_do_not_overlap() -> None:
    frame = pd.DataFrame(
        {
            "x": [0, 1] * 3,
            "y": [1, 2.0, 1, 2.01, 1, 2.02],
            "g": ["a", "a", "b", "b", "c", "c"],
        }
    )
    plot = sp.line(frame, x="x", y="y", hue="g").endlabels(values=".2f")
    assert plot.ax.get_legend() is None
    texts = [t for t in plot.ax.texts if t.get_text()]
    assert [t.get_text() for t in texts] == ["a  2.00", "b  2.01", "c  2.02"]
    renderer = plot.fig.canvas.get_renderer()
    boxes = sorted((t.get_window_extent(renderer) for t in texts), key=lambda b: b.y0)
    for low, high in itertools.pairwise(boxes):
        assert low.y1 <= high.y0 + 0.5
    with pytest.raises(sp.DataShapeError, match="without groups"):
        sp.line(x=[0, 1], y=[1, 2]).endlabels().render()


def test_spread_keeps_labels_apart_and_centered() -> None:
    assert spread([0, 10], [2, 2]) == [0, 10]
    assert spread([5, 5], [2, 2]) == [4, 6]
    placed = spread([0, 0.5, 9], [2, 2, 2])
    assert placed == [-0.75, 1.25, 9]


def test_reflines_on_both_axes(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight").refline(22).refline(2, axis="x")
    dashed = [line for line in plot.ax.get_lines() if line.get_linestyle() == "--"]
    assert len(dashed) == 2


def test_grouplabels_rename_groups(mice: pd.DataFrame) -> None:
    plot = sp.line(mice, x="day", y="weight", hue="diet").grouplabels(
        {"fat": "High fat"}
    )
    legend = [t.get_text() for t in plot.ax.get_legend().get_texts()]
    assert legend == ["chow", "High fat"]


def test_options_lists_line_steps() -> None:
    steps = sp.LinePlot.options().index
    assert {"errorbars", "markers", "fill", "endlabels", "refline"} <= set(steps)
    assert "level" in sp.LinePlot.options("errorbars").index


def test_renders_with_presets_and_dark_theme(mice: pd.DataFrame) -> None:
    plot = (
        sp.line(mice, x="day", y="weight", hue="diet", error="ci")
        .preset("nature")
        .theme("dark")
    )
    assert plot.fig is not None
