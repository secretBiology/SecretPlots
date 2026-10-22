"""Missing data is a user decision, shared across plot families."""

import numpy as np
import pandas as pd
import pytest

import SecretPlots as sp


@pytest.mark.parametrize(
    "factory", [sp.bar, sp.box, sp.violin, sp.raincloud, sp.histogram, sp.line, sp.area]
)
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, None, pd.NA])
def test_missing_is_strict_by_default(factory, bad):
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        factory([1, 2, bad, 3, 4, 5])


@pytest.mark.parametrize(
    "factory", [sp.bar, sp.box, sp.violin, sp.raincloud, sp.histogram, sp.line, sp.area]
)
def test_explicit_drop_renders(factory):
    p = factory([1, 2, np.nan, 3, np.inf, 4, 5] * 10, missing="drop")
    p.render()


@pytest.mark.parametrize(
    "factory", [sp.bar, sp.box, sp.violin, sp.histogram, sp.line, sp.area]
)
def test_no_usable_observations(factory):
    with pytest.raises(sp.DataShapeError, match="No data"):
        factory([np.nan, np.inf], missing="drop")


@pytest.mark.parametrize("policy", ["ignore", "skip", "strict", None])
def test_bad_policy_is_rejected_even_for_complete_data(policy):
    with pytest.raises(ValueError, match="missing="):
        sp.line([1, 2, 3], missing=policy)


def test_scatter_missing_coordinates_and_sizes():
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        sp.scatter(x=[1, 2], y=[3, np.inf])
    p = sp.scatter(x=[1, 2, 3], y=[1, 2, 3], size=[2, np.nan, 4], missing="drop")
    assert len(p.ax.collections[0].get_offsets()) == 2
    with pytest.raises(ValueError, match="missing="):
        sp.scatter(x=[1, 2], y=[2, 3], missing="gap")


def test_line_gap_breaks_path_and_drop_connects():
    gap = sp.line(x=[0, 1, 2], y=[1, np.nan, 3], missing="gap")
    line = gap.ax.lines[0]
    assert line.get_xdata().tolist() == [0, 1, 2]
    assert np.isnan(line.get_ydata()[1])
    drop = sp.line(x=[0, 1, 2], y=[1, np.nan, 3], missing="drop")
    assert drop.ax.lines[0].get_xdata().tolist() == [0, 2]


@pytest.mark.parametrize("estimator", ["mean", "sum", "median"])
def test_missing_replicate_remains_gap_in_summary_and_interval(estimator):
    p = sp.line(
        x=[0, 0, 1, 1, 2, 2],
        y=[1, 2, 3, np.nan, 5, 6],
        missing="gap",
        estimator=estimator,
        error="ci",
    )
    table = p.source_data()
    assert np.isnan(table.loc[1, "y"])
    assert np.isnan(table.loc[1, "ci_low"])
    assert np.isnan(p.ax.lines[0].get_ydata()[1])


def test_gap_requires_positions_and_groups():
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        sp.line(x=[1, np.nan, 3], y=[1, 2, 3], missing="gap")
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        sp.line(x=[1, 2], y=[1, 2], hue=["a", None], missing="gap")


def test_missing_error_columns_are_not_silently_accepted():
    with pytest.raises(sp.DataShapeError, match="yerr"):
        sp.line(x=[0, 1], y=[1, 2], yerr=[0.1, np.nan])


def test_area_gap_and_stack_policy():
    p = sp.area([1, np.nan, 3], missing="gap")
    assert np.isnan(p.ax.lines[0].get_ydata()[1])
    frame = pd.DataFrame({"a": [1, np.nan, 3], "b": [2, 4, 6]})
    p = sp.area(frame, stack=True, missing="gap")
    assert p.source_data().loc[lambda t: t.x == 1, "value"].isna().all()
    p.render()
    dropped = sp.area(frame, stack=True, missing="drop").source_data()
    assert set(dropped.x) == {0, 2}


def test_heatmap_policies_and_sparse_long_data():
    data = pd.DataFrame({"a": [1, 2], "b": [np.nan, 3]}, index=["bad", "good"])
    with pytest.raises(sp.DataShapeError, match="missing='gap'"):
        sp.heatmap(data)
    assert sp.heatmap(data, missing="drop").source_data().index.tolist() == ["good"]
    gap = sp.heatmap(data, missing="gap")
    assert np.isnan(gap.source_data().loc["bad", "b"])
    gap.render()
    long = pd.DataFrame({"r": ["a", "a", "b"], "c": ["x", "y", "x"], "v": [1, 2, 3]})
    with pytest.raises(sp.DataShapeError, match="missing='gap'"):
        sp.heatmap(long, x="c", y="r", value="v")
    assert sp.heatmap(
        long, x="c", y="r", value="v", missing="gap"
    ).source_data().shape == (2, 2)


def test_heatmap_missing_replicate_and_invalid_numeric_text():
    frame = pd.DataFrame(
        {"r": ["a", "a", "b"], "c": ["x", "x", "x"], "v": [1, np.nan, 3]}
    )
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        sp.heatmap(frame, x="c", y="r", value="v")
    result = sp.heatmap(frame, x="c", y="r", value="v", missing="gap").source_data()
    assert np.isnan(result.loc["a", "x"])
    frame["v"] = ["1", "oops", "3"]
    with pytest.raises(sp.DataShapeError, match="numeric"):
        sp.heatmap(frame, x="c", y="r", value="v", missing="drop")


def test_unrelated_metadata_and_unused_groups():
    frame = pd.DataFrame(
        {
            "x": [0, 1],
            "y": [1, 2],
            "unused": [None, None],
            "g": pd.Categorical(["a", "a"], categories=["a", "absent"]),
        }
    )
    sp.line(frame, x="x", y="y", hue="g").render()
    hist = sp.histogram(frame, x="y", hue="g").rug()
    assert set(hist.source_data().g) == {"a"}


def test_duplicate_order_is_rejected():
    with pytest.raises(sp.DataShapeError, match="duplicates"):
        sp.bar({"a": 1, "b": 2}, order=["a", "a", "b"])


def test_nullable_single_distribution_keeps_its_shape():
    p = sp.box([1, 2, pd.NA, 3, 4, 5], missing="drop")
    assert len(p.source_data()) == 1
    assert p.source_data().iloc[0]["n"] == 5


def test_infinite_group_is_missing():
    with pytest.raises(sp.DataShapeError, match="hue"):
        sp.line(x=[1, 2], y=[3, 4], hue=["a", np.inf])


@pytest.mark.parametrize("mode", ["plain", "gradient", "split", "stack"])
def test_area_gaps_keep_paths_separate_and_label_last_valid_value(mode):
    p = sp.area([1, 2, np.nan, 3, 4, np.nan], missing="gap", stack=mode == "stack")
    if mode in ("gradient", "split"):
        p = getattr(p, mode)()
    p.endlabels(values=".1f").render()
    assert [t.get_text() for t in p._end_texts] == ["4.0"]
    assert len(p.ax.collections[0].get_paths()) == 2
