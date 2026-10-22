import numpy as np
import pandas as pd
import pytest
from matplotlib.patches import Polygon

import SecretPlots as sp


@pytest.fixture
def scores() -> pd.DataFrame:
    rng = np.random.default_rng(2)
    return pd.DataFrame(
        {
            "group": np.repeat(["a", "b", "c"], [40, 80, 40]),
            "score": np.r_[
                rng.normal(0, 1, 40), rng.normal(1, 0.5, 80), rng.normal(2, 2, 40)
            ],
            "arm": np.tile(["left", "right"], 80),
        }
    )


def _shapes(plot: sp.ViolinPlot) -> list[np.ndarray]:
    """Outline of each violin (the large polygons, not the inner boxes)."""
    polygons = [p.get_xy() for p in plot.ax.patches if isinstance(p, Polygon)]
    return [xy for xy in polygons if len(xy) > 10]


def _area(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def test_one_violin_per_category(scores: pd.DataFrame) -> None:
    plot = sp.violin(scores, x="group", y="score")
    shapes = _shapes(plot)
    assert len(shapes) == 3
    # cut=0 trims every violin to its data range.
    for xy, (_, values) in zip(shapes, scores.groupby("group")["score"], strict=True):
        assert xy[:, 1].min() == pytest.approx(values.min())
        assert xy[:, 1].max() == pytest.approx(values.max())


@pytest.mark.parametrize("scale", ["area", "count", "width"])
def test_scale(scores: pd.DataFrame, scale: str) -> None:
    shapes = _shapes(sp.violin(scores, x="group", y="score", scale=scale))
    areas = [_area(xy) for xy in shapes]
    widths = [np.ptp(xy[:, 0]) for xy in shapes]
    if scale == "area":
        assert areas == pytest.approx([areas[0]] * 3, rel=0.02)
    elif scale == "count":
        assert areas[1] / areas[0] == pytest.approx(2, rel=0.02)
    else:
        assert widths == pytest.approx([widths[0]] * 3)


def test_cut_extends_past_the_data(scores: pd.DataFrame) -> None:
    xy = _shapes(sp.violin(scores, x="group", y="score", cut=2))[0]
    assert xy[:, 1].min() < scores[scores["group"] == "a"]["score"].min()


def test_split_needs_two_groups(scores: pd.DataFrame) -> None:
    plot = sp.violin(scores, x="group", y="score", hue="arm", split=True)
    shapes = _shapes(plot)
    assert len(shapes) == 6
    left, right = shapes[0][:, 0], shapes[1][:, 0]
    assert left.max() == pytest.approx(0)  # left half ends at the center line
    assert right.min() == pytest.approx(0)
    with pytest.raises(sp.DataShapeError, match="exactly 2"):
        sp.violin(scores, x="arm", y="score", hue="group", split=True)


def test_half_violins(scores: pd.DataFrame) -> None:
    xy = _shapes(sp.violin(scores, x="group", y="score", side="right"))[0]
    assert xy[:, 0].min() == pytest.approx(0)
    flipped = _shapes(sp.violin(scores, x="group", y="score", side="left"))[0]
    assert flipped[:, 0].max() == pytest.approx(0)


@pytest.mark.parametrize("inner", ["box", "quartiles", "median", None])
def test_inner(scores: pd.DataFrame, inner: str | None) -> None:
    plot = sp.violin(scores, x="group", y="score", inner=inner)
    lines = len(plot.ax.lines)
    assert lines == {"box": 6, "quartiles": 9, "median": 3, None: 0}[inner]


def test_constant_values_draw_a_line() -> None:
    plot = sp.violin({"a": [3.0] * 12, "b": np.linspace(0, 1, 12)})
    assert len(_shapes(plot)) == 1
    assert any(np.all(line.get_ydata() == 3.0) for line in plot.ax.lines)


def test_small_samples_warn() -> None:
    with pytest.warns(sp.SmallSampleWarning, match="Fewer than 10"):
        sp.violin({"a": np.arange(6.0)}).render()


def test_horizontal_right_side_is_up(scores: pd.DataFrame) -> None:
    xy = _shapes(sp.violin(scores, x="group", y="score", side="right", orient="h"))[0]
    assert xy[:, 1].max() == pytest.approx(0)  # up = toward lower positions


def test_raincloud(scores: pd.DataFrame) -> None:
    plot = sp.raincloud(scores, x="group", y="score")
    assert isinstance(plot, sp.RaincloudPlot)
    assert plot.kind == "raincloud"
    assert plot.ax.get_xlabel() == "score"  # horizontal by default
    cloud = _shapes(plot)[0]
    rain = np.asarray(plot.ax.collections[0].get_offsets())
    assert len(rain) == 40
    # The cloud rises above the category line, the rain falls below it.
    assert cloud[:, 1].max() <= 1e-9
    assert rain[:, 1].min() > 0
    assert "raincloud" in plot.caption()


def test_points_and_compare_on_violins(scores: pd.DataFrame) -> None:
    plot = sp.violin(scores, x="group", y="score").points().compare(ref="a")
    assert len(plot.test_results()) == 2
    assert len(plot.ax.texts) == 2


def test_caption(scores: pd.DataFrame) -> None:
    text = sp.violin(scores, x="group", y="score", bw_adjust=0.5).caption()
    assert "kernel density" in text
    assert "x 0.5" in text
    assert "trimmed to the range of the data" in text
    assert "equal areas" in text


def test_validation() -> None:
    with pytest.raises(ValueError, match="Did you mean 'area'"):
        sp.violin([1.0] * 12, scale="aera")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="bw_adjust"):
        sp.violin([1.0] * 12, bw_adjust=0)


def test_outline(scores: pd.DataFrame) -> None:
    plot = sp.violin(
        scores, x="group", y="score", inner="quartiles", edgecolor="black", linewidth=1
    )
    violin = next(p for p in plot.ax.patches if len(p.get_xy()) > 10)
    assert violin.get_linewidth() == 1
    assert violin.get_edgecolor()[:3] == (0, 0, 0)
    assert all(line.get_color() == "black" for line in plot.ax.lines)
    cloud = sp.raincloud(scores, x="group", y="score", edgecolor="none")
    assert (
        next(p for p in cloud.ax.patches if len(p.get_xy()) > 10).get_edgecolor()[3]
        == 0
    )
