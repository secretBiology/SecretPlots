import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_hex
from matplotlib.image import AxesImage

import SecretPlots as sp


@pytest.fixture
def energy() -> pd.DataFrame:
    years = np.arange(2000, 2006)
    return pd.DataFrame(
        {
            "year": np.tile(years, 2),
            "TWh": [10, 11, 12, 13, 14, 15, 1, 2, 3, 4, 5, 6],
            "source": ["coal"] * 6 + ["solar"] * 6,
        }
    )


def _fills(plot: sp.FillBetweenPlot) -> list[PolyCollection]:
    """Filled areas (not legend proxies, which have no points)."""
    return [
        c
        for c in plot.ax.collections
        if isinstance(c, PolyCollection) and any(len(p) for p in c.get_paths())
    ]


def test_area_under_a_line_sits_on_zero() -> None:
    plot = sp.area(x=[0, 1, 2], y=[2, 3, 1])
    assert len(_fills(plot)) == 1
    (top,) = plot.ax.get_lines()
    assert list(top.get_ydata()) == [2, 3, 1]
    assert plot.ax.get_ylim()[0] == 0
    assert plot.ax.get_legend() is None


def test_fill_between_two_columns_is_a_band() -> None:
    frame = pd.DataFrame({"x": [0, 1, 2], "lo": [1, 2, 1], "hi": [3, 4, 3]})
    plot = sp.fill_between(frame, x="x", y1="hi", y2="lo")
    assert len(_fills(plot)) == 1
    assert not plot.ax.get_lines()  # bands have no edge lines by default
    assert plot.ax.get_ylabel() == ""
    assert len(plot.lines("both").ax.get_lines()) == 2
    table = plot.source_data()
    assert list(table.columns) == ["x", "hi", "lo"]


def test_groups_overlap_with_legend(energy: pd.DataFrame) -> None:
    plot = sp.area(energy, x="year", y="TWh", hue="source")
    assert len(_fills(plot)) == 2
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["coal", "solar"]
    assert plot.ax.get_ylabel() == "TWh"


def test_stack_accumulates_and_lists_top_layer_first(energy: pd.DataFrame) -> None:
    plot = sp.area(energy, x="year", y="TWh", hue="source", stack=True)
    table = plot.source_data()
    solar = table[table["source"] == "solar"]
    np.testing.assert_allclose(solar["upper"], [11, 13, 15, 17, 19, 21])
    legend = [t.get_text() for t in plot.ax.get_legend().get_texts()]
    assert legend == ["solar", "coal"]
    assert plot.ax.get_ylim()[0] == 0


def test_percent_stack_sums_to_100(energy: pd.DataFrame) -> None:
    plot = sp.area(energy, x="year", y="TWh", hue="source", stack="percent")
    table = plot.source_data()
    totals = table.groupby("year")["percent"].sum()
    np.testing.assert_allclose(totals, 100)
    assert plot.ax.get_ylim() == (0, 100)
    assert plot.ax.get_ylabel() == "Percent"


def test_wide_frame_stacks_columns() -> None:
    wide = pd.DataFrame({"a": [1, 2], "b": [3, 4]}, index=[2020, 2021])
    plot = sp.area(wide, stack=True)
    assert len(_fills(plot)) == 2
    assert plot.source_data()["upper"].tolist() == [1, 2, 4, 6]


def test_split_colors_by_sign() -> None:
    plot = sp.fill_between(x=[0, 1, 2, 3], y1=[1, -1, 2, -2]).split(
        labels=("above", "below")
    )
    theme = plot.style().theme
    colors = [to_hex(c.get_facecolor()[0], keep_alpha=False) for c in _fills(plot)]
    assert colors == [theme.positive, theme.negative]
    legend = [t.get_text() for t in plot.ax.get_legend().get_texts()]
    assert legend == ["above", "below"]


def test_gradient_draws_a_clipped_image(energy: pd.DataFrame) -> None:
    plot = sp.area(energy, x="year", y="TWh", hue="source").gradient()
    images = [a for a in plot.ax.get_images() if isinstance(a, AxesImage)]
    assert len(images) == 2
    assert all(image.get_clip_path() is not None for image in images)
    assert plot.ax.get_ylim()[0] == 0


def test_end_labels_of_a_stack_print_layer_values(energy: pd.DataFrame) -> None:
    plot = sp.area(energy, x="year", y="TWh", hue="source", stack=True)
    plot.endlabels(values=".0f")
    texts = [t.get_text() for t in plot.ax.texts]
    assert texts == ["coal  15", "solar  6"]
    assert plot.ax.get_legend() is None


def test_validation(energy: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="only once per area"):
        sp.area(energy, x="year", y="TWh")
    with pytest.raises(ValueError, match="baseline"):
        sp.fill_between(energy, x="year", y1="TWh", y2="TWh", stack=True)
    with pytest.raises(ValueError, match="gradient"):
        sp.area(energy, x="year", y="TWh", hue="source", stack=True).gradient()
    with pytest.raises(ValueError, match="single area"):
        sp.area(energy, x="year", y="TWh", hue="source").split()
    with pytest.raises(ValueError, match="stack must be"):
        sp.area(x=[0, 1], y=[1, 2], stack="yes")  # type: ignore[arg-type]
    with pytest.raises(sp.DataShapeError, match="no data was given"):
        sp.area(x="year", y="TWh")


def test_dates_and_reflines() -> None:
    days = pd.date_range("2024-01-01", periods=4)
    plot = sp.area(pd.DataFrame({"d": days, "v": [1, 3, 2, 4]}), x="d", y="v")
    plot.refline("2024-01-02", axis="x", label=True)
    assert any(t.get_text().startswith("2024-01-02") for t in plot.ax.texts)
