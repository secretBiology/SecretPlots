"""``.refline()`` works the same on every plot: like ``axhline``/``axvline``."""

import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.colors import to_hex
from matplotlib.lines import Line2D

import SecretPlots as sp


@pytest.fixture
def df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "g": np.repeat(list("ABCD"), 10),
            "v": rng.normal(10, 2, 40),
            "w": rng.normal(5, 1, 40),
            "s": np.tile(["F", "M"], 20),
        }
    )


@pytest.fixture
def matrix() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        rng.normal(size=(4, 3)), index=["r0", "r1", "r2", "r3"], columns=list("abc")
    )


def _reflines(ax: Axes) -> list[Line2D]:
    """Lines spanning the axes (axhline/axvline use axes coordinates)."""
    spans = []
    for line in ax.get_lines():
        x, y = line.get_xdata(), line.get_ydata()
        if len(x) == 2 and (list(x) == [0, 1] or list(y) == [0, 1]):
            spans.append(line)
    return spans


def _horizontal(line: Line2D) -> bool:
    return list(line.get_xdata()) == [0, 1]


def _position(line: Line2D) -> float:
    data = line.get_ydata() if _horizontal(line) else line.get_xdata()
    return float(data[0])


PLOTS = {
    "bar": lambda d: sp.bar(d, x="g", y="v"),
    "scatter": lambda d: sp.scatter(d, x="v", y="w"),
    "line": lambda d: sp.line(d, x="v", y="w"),
    "area": lambda d: sp.area(x=[0, 1, 2], y=[1, 3, 2]),
    "box": lambda d: sp.box(d, x="g", y="v"),
    "violin": lambda d: sp.violin(d, x="g", y="v"),
    "raincloud": lambda d: sp.raincloud(d, x="g", y="v"),
}


@pytest.mark.parametrize("name", PLOTS)
def test_every_plot_draws_horizontal_and_vertical_lines(
    df: pd.DataFrame, name: str
) -> None:
    plot = PLOTS[name](df).refline(2, axis="y").refline(1, axis="x")
    lines = _reflines(plot.ax)
    assert sorted((_horizontal(line), _position(line)) for line in lines) == [
        (False, 1.0),
        (True, 2.0),
    ]


def test_default_axis_is_the_value_axis(df: pd.DataFrame) -> None:
    (line,) = _reflines(sp.bar(df, x="g", y="v").refline(9).ax)
    assert _horizontal(line)
    (line,) = _reflines(sp.bar(df, x="g", y="v", orient="h").refline(9).ax)
    assert not _horizontal(line)
    (line,) = _reflines(sp.box(df, x="g", y="v", orient="h").refline(9).ax)
    assert not _horizontal(line)
    (line,) = _reflines(sp.histogram(df, x="v").refline(9).ax)
    assert not _horizontal(line)
    (line,) = _reflines(sp.scatter(df, x="v", y="w").refline(5).ax)
    assert _horizontal(line)


def test_category_names_on_category_axes(df: pd.DataFrame) -> None:
    (line,) = _reflines(sp.bar(df, x="g", y="v").refline("C", axis="x").ax)
    assert _position(line) == 2
    (line,) = _reflines(sp.box(df, x="g", y="v").refline("B", axis="x").ax)
    assert _position(line) == 1
    plot = sp.bar(df, x="g", y="v", sort="asc").refline("A", axis="x")
    (line,) = _reflines(plot.ax)
    labels = [t.get_text() for t in plot.ax.get_xticklabels()]
    assert labels[int(_position(line))] == "A"
    with pytest.raises(sp.DataShapeError, match="not a category"):
        sp.bar(df, x="g", y="v").refline("Z", axis="x").render()


def test_style_options_and_text_label(df: pd.DataFrame) -> None:
    plot = sp.scatter(df, x="v", y="w").refline(
        5, label="cutoff", color="#ff0000", linestyle=":", linewidth=2
    )
    (line,) = _reflines(plot.ax)
    assert to_hex(line.get_color()) == "#ff0000"
    assert line.get_linestyle() == ":"
    assert line.get_linewidth() == 2
    assert [t.get_text() for t in plot.ax.texts] == ["cutoff"]
    numbered = sp.scatter(df, x="v", y="w").refline(5, 6, label=True)
    assert [t.get_text() for t in numbered.ax.texts] == ["5", "6"]


def test_label_position_and_rotation(df: pd.DataFrame) -> None:
    vertical = sp.scatter(df, x="v", y="w").refline(
        10, axis="x", label="cut", label_position="start", label_rotation=90
    )
    (text,) = vertical.ax.texts
    assert text.xy[1] == 0
    assert text.get_va() == "bottom"
    assert text.get_rotation() == 90
    horizontal = sp.scatter(df, x="v", y="w").refline(
        5, label="cut", label_position="center"
    )
    (text,) = horizontal.ax.texts
    assert text.xy[0] == 0.5
    assert text.get_ha() == "center"
    default = sp.scatter(df, x="v", y="w").refline(5, label="cut")
    assert default.ax.texts[0].xy[0] == 1
    assert default.ax.texts[0].get_ha() == "right"


def test_label_outside_the_axes(df: pd.DataFrame) -> None:
    plot = sp.bar(df, x="g", y="v").refline(5, label=True, label_position="outside")
    (text,) = plot.ax.texts
    assert text.xy == (1.0, 5)
    assert (text.get_ha(), text.get_va()) == ("left", "center")
    renderer = plot.fig.canvas.get_renderer()  # type: ignore[attr-defined]
    assert text.get_window_extent(renderer).x0 >= plot.ax.bbox.x1
    assert text.get_window_extent(renderer).x1 <= plot.fig.bbox.x1
    vertical = sp.scatter(df, x="v", y="w").refline(
        10, axis="x", label="cut", label_position="outside"
    )
    (text,) = vertical.ax.texts
    assert text.xy == (10, 1.0)
    assert (text.get_ha(), text.get_va()) == ("center", "bottom")


def test_value_labels_use_the_tick_minus_sign(df: pd.DataFrame) -> None:
    plot = sp.scatter(df, x="v", y="w").refline(-30, 1e-5, -0.5, label=True)
    assert [t.get_text() for t in plot.ax.texts] == [
        "\N{MINUS SIGN}30",
        "1e-05",
        "\N{MINUS SIGN}0.5",
    ]
    own = sp.scatter(df, x="v", y="w").refline(-30, label="-30 cut")
    assert own.ax.texts[0].get_text() == "-30 cut"
    dated = sp.line(
        pd.DataFrame({"d": pd.date_range("2024-01-01", periods=3), "v": [1, 2, 3]}),
        x="d",
        y="v",
    ).refline("2024-01-02", axis="x", label=True)
    assert dated.ax.texts[0].get_text() == "2024-01-02"


def test_label_side(df: pd.DataFrame) -> None:
    vertical = sp.scatter(df, x="v", y="w").refline(
        10, axis="x", label="cut", label_side="left"
    )
    (text,) = vertical.ax.texts
    assert text.get_ha() == "right"
    assert text.xyann[0] < 0
    horizontal = sp.scatter(df, x="v", y="w").refline(
        5, label="cut", label_side="below"
    )
    (text,) = horizontal.ax.texts
    assert text.get_va() == "top"
    assert text.xyann[1] < 0
    with pytest.raises(ValueError, match="'above' or 'below'"):
        sp.scatter(df, x="v", y="w").refline(5, label=True, label_side="left")
    with pytest.raises(ValueError, match="'left' or 'right'"):
        sp.scatter(df, x="v", y="w").refline(
            5, axis="x", label=True, label_side="below"
        )


def test_label_position_and_rotation_are_checked(df: pd.DataFrame) -> None:
    plot = sp.scatter(df, x="v", y="w")
    with pytest.raises(ValueError, match="label_position"):
        plot.refline(5, label=True, label_position="top")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="label_rotation"):
        plot.refline(5, label=True, label_rotation="90")  # type: ignore[arg-type]


def test_calls_add_lines_and_empty_call_removes_them(df: pd.DataFrame) -> None:
    plot = sp.scatter(df, x="v", y="w").refline(5).refline(10, axis="x")
    assert len(_reflines(plot.ax)) == 2
    assert len(_reflines(plot.refline(axis="x").ax)) == 1
    assert not _reflines(plot.refline().ax)


def test_histogram_statistics_per_group(df: pd.DataFrame) -> None:
    df = pd.concat([df, df], ignore_index=True)  # 40 per group: no small-sample warning
    plot = sp.histogram(df, x="v", hue="s").refline("mean", label=True)
    lines = _reflines(plot.ax)
    means = df.groupby("s")["v"].mean()
    assert sorted(_position(line) for line in lines) == pytest.approx(sorted(means))
    texts = [t for t in plot.ax.texts if t.get_text().startswith("mean")]
    assert len({t.xyann for t in texts}) == 2  # stacked, not on top of each other
    with pytest.raises(ValueError, match="Did you mean 'median'"):
        sp.histogram(df, x="v").refline("medain")
    with pytest.raises(sp.DataShapeError, match="binned axis"):
        sp.histogram(df, x="v").refline("mean", axis="y").render()


def test_heatmap_names_and_edges(matrix: pd.DataFrame) -> None:
    plot = sp.heatmap(matrix).refline("r1", axis="y").refline(2, axis="x")
    by_axis = {_horizontal(line): _position(line) for line in _reflines(plot.ax)}
    assert by_axis == {True: 1.5, False: 2.0}
    with pytest.raises(ValueError, match="need an axis"):
        sp.heatmap(matrix).refline(1).render()
    with pytest.raises(sp.DataShapeError, match="from 0 to 4"):
        sp.heatmap(matrix).refline(5, axis="y").render()


def test_heatmap_edge_sits_in_a_group_gap(matrix: pd.DataFrame) -> None:
    matrix["kind"] = ["x", "x", "y", "y"]
    plot = sp.heatmap(matrix).groups(rows="kind").refline(2, axis="y")
    (line,) = _reflines(plot.ax)
    starts = sorted(t for t in plot.ax.get_yticks())
    # Between the centers of the 2nd and 3rd rows, in the gap.
    assert starts[1] < _position(line) < starts[2]
    assert _position(line) - starts[1] > 0.5


def test_dates_as_text_on_a_date_axis() -> None:
    days = pd.date_range("2024-01-01", periods=5)
    plot = sp.line(x=days, y=range(5)).refline("2024-01-03", axis="x", label=True)
    assert len(_reflines(plot.ax)) == 1
    assert plot.ax.texts[0].get_text() == "2024-01-03"
    with pytest.raises(sp.DataShapeError, match="not a date"):
        sp.line(x=days, y=range(5)).refline("soon", axis="x").render()


def test_validation(df: pd.DataFrame) -> None:
    plot = sp.scatter(df, x="v", y="w")
    with pytest.raises(ValueError, match="axis must be"):
        plot.refline(1, axis="z")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="once per value"):
        plot.refline(1, 2, label="two")
    with pytest.raises(ValueError, match="linestyle"):
        plot.refline(1, linestyle="wavy")
    with pytest.raises(ValueError, match="color"):
        plot.refline(1, color="notacolor")
    with pytest.raises(TypeError, match="number, a date or a category"):
        plot.refline([1, 2])  # type: ignore[arg-type]
    with pytest.raises(sp.DataShapeError, match="must be a number"):
        sp.scatter(df, x="v", y="w").refline("x").render()


@pytest.mark.parametrize("cls", [sp.BarPlot, sp.HeatmapPlot, sp.ViolinPlot])
def test_options_list_refline(cls: type[sp.Plot]) -> None:
    options = cls.options("refline").index.tolist()
    assert options == [
        "*values",
        "axis",
        "label",
        "color",
        "linestyle",
        "linewidth",
        "label_position",
        "label_rotation",
        "label_side",
    ]
