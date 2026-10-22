import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

import SecretPlots as sp
from SecretPlots.plots.forest import _difference_ticks, _format_cell, _ratio_ticks


@pytest.fixture
def subgroups() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "variable": [None, "Age", "Age", "Sex", "Sex"],
            "subgroup": ["Overall", "<65 yr", ">=65 yr", "Male", "Female"],
            "n": [1000, 520, 480, 610, 390],
            "hr": [0.74, 0.76, 0.72, 0.73, 0.79],
            "lo": [0.65, 0.63, 0.60, 0.63, 0.62],
            "hi": [0.85, 0.92, 0.87, 0.85, 1.01],
        }
    )


def _forest(frame: pd.DataFrame, **kwargs) -> sp.ForestPlot:
    return sp.forest(
        frame, label="subgroup", estimate="hr", lower="lo", upper="hi", **kwargs
    )


def _texts(plot: sp.ForestPlot) -> list[str]:
    return [t.get_text() for t in plot.ax.texts]


def _markers(ax) -> list[Line2D]:
    return [
        line
        for line in ax.lines
        if line.get_marker() not in ("None", "", None, "<", ">")
        and len(line.get_xdata()) == 1
    ]


# ----------------------------------------------------------------- layout
def test_rows_follow_data_order_with_estimate_column(
    subgroups: pd.DataFrame,
) -> None:
    plot = _forest(subgroups)
    texts = _texts(plot)
    assert texts[:2] == ["Subgroup", "Overall"]
    assert "HR (95% CI)" in texts
    assert "0.74 (0.65\N{EN DASH}0.85)" in texts
    assert plot.ax.get_xscale() == "log"
    assert plot.ax.get_xlabel() == "HR"
    # Ticks bracket the data with doublings, not matplotlib's decades.
    assert list(plot.ax.get_xticks()) == [0.5, 1.0, 2.0]
    assert plot.ax.get_xlim() == (0.5, 2.0)


def test_groups_get_bold_headers_indented_rows_and_gaps(
    subgroups: pd.DataFrame,
) -> None:
    plot = _forest(subgroups, group="variable")
    rows = plot._rows()
    assert [(r.kind, r.label) for r in rows] == [
        ("item", "Overall"),
        ("header", "Age"),
        ("item", "<65 yr"),
        ("item", ">=65 yr"),
        ("header", "Sex"),
        ("item", "Male"),
        ("item", "Female"),
    ]
    assert [r.y for r in rows] == [0, 1.5, 2.5, 3.5, 5, 6, 7]
    age = next(t for t in plot.ax.texts if t.get_text() == "Age")
    young = next(t for t in plot.ax.texts if t.get_text() == "<65 yr")
    assert age.get_fontweight() == "bold"
    renderer = plot.fig.canvas.get_renderer()
    indent = young.get_window_extent(renderer).x0 - age.get_window_extent(renderer).x0
    assert indent > 5  # pixels


def test_groups_without_headers_only_separate_sections(
    subgroups: pd.DataFrame,
) -> None:
    plot = _forest(subgroups, group="variable").groups(headers=False, gap=1)
    assert [r.kind for r in plot._rows()] == ["item"] * 5
    assert [r.y for r in plot._rows()] == [0, 2, 3, 5, 6]
    assert "Age" not in _texts(plot)


def test_summary_rows_are_diamonds(subgroups: pd.DataFrame) -> None:
    plot = _forest(subgroups).summary("Overall")
    diamonds = [p for p in plot.ax.patches if isinstance(p, Polygon)]
    assert len(diamonds) == 1
    xs = diamonds[0].get_xy()[:, 0]
    assert min(xs) == pytest.approx(0.65)
    assert max(xs) == pytest.approx(0.85)
    assert len(_markers(plot.ax)) == 4
    overall = next(t for t in plot.ax.texts if t.get_text() == "Overall")
    assert overall.get_fontweight() == "bold"


def test_summary_unknown_label_suggests(subgroups: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="Did you mean 'Overall'"):
        _forest(subgroups).summary("Overal")


# ------------------------------------------------------------------ table
def test_table_columns_formats_and_group_values(subgroups: pd.DataFrame) -> None:
    plot = _forest(subgroups, group="variable").table(
        left={"Patients": "n"},
        right={"P for interaction": {"Age": 0.0004, "Sex": 0.52}},
        formats={"P for interaction": "p"},
    )
    texts = _texts(plot)
    assert {"Patients", "1,000", "P for interaction", "<0.001", "0.52"} <= set(texts)
    p_age = next(t for t in plot.ax.texts if t.get_text() == "<0.001")
    header = next(t for t in plot.ax.texts if t.get_text() == "Age")
    renderer = plot.fig.canvas.get_renderer()
    # Group values sit on the header row.
    y_value = p_age.get_window_extent(renderer).y0
    y_header = header.get_window_extent(renderer).y0
    assert y_value == pytest.approx(y_header, abs=2)


def test_table_list_of_columns_uses_names_as_headers(
    subgroups: pd.DataFrame,
) -> None:
    assert "n" in _texts(_forest(subgroups).table(left=["n"]))


def test_table_rejects_unknown_columns_and_formats(subgroups: pd.DataFrame) -> None:
    plot = _forest(subgroups, group="variable")
    with pytest.raises(sp.DataShapeError, match="Did you mean 'n'"):
        plot.table(left=["nn"])
    with pytest.raises(sp.DataShapeError, match="neither a group nor a row"):
        plot.table(right={"P": {"Weight": 0.1}})
    with pytest.raises(ValueError, match="not table columns"):
        plot.table(left=["n"], formats={"N": ".1f"})
    with pytest.raises(ValueError, match="not a format spec"):
        plot.table(left=["n"], formats={"n": "{:q}"})


def test_format_cell() -> None:
    assert _format_cell(1234, None) == "1,234"
    assert _format_cell(1234.0, None) == "1,234"
    assert _format_cell(0.04213, None) == "0.0421"
    assert _format_cell(0.760, None) == "0.76"
    assert _format_cell(1234.5, None) == "1,234"
    assert _format_cell(-2.5, ".1f") == "\N{MINUS SIGN}2.5"
    assert _format_cell(12.34, "{:.1f}%") == "12.3%"
    assert _format_cell(0.004, "p") == "0.004"
    assert _format_cell(np.nan, ".1f") == ""
    assert _format_cell("12/150", None) == "12/150"
    assert _format_cell(3, lambda v: f"<{v}>") == "<3>"


def test_estimates_options(subgroups: pd.DataFrame) -> None:
    hidden = _forest(subgroups).estimates(False)
    assert "HR (95% CI)" not in _texts(hidden)
    custom = _forest(subgroups).estimates(decimals=1, header="Hazard ratio")
    assert {"Hazard ratio", "0.7 (0.7\N{EN DASH}0.8)"} <= set(_texts(custom))
    left = _forest(subgroups).estimates(side="left")
    text = next(t for t in left.ax.texts if t.get_text() == "HR (95% CI)")
    renderer = left.fig.canvas.get_renderer()
    assert text.get_window_extent(renderer).x1 < left.ax.bbox.x0
    with pytest.raises(ValueError, match="side"):
        _forest(subgroups).estimates(side="top")  # type: ignore[arg-type]


# ------------------------------------------------------------------ scales
def test_difference_scale_is_linear_with_null_at_zero() -> None:
    frame = pd.DataFrame(
        {"term": ["a", "b"], "md": [-1.5, 0.4], "lo": [-2.6, -0.2], "hi": [-0.4, 1.0]}
    )
    plot = sp.forest(
        frame, label="term", estimate="md", lower="lo", upper="hi", scale="difference"
    )
    assert plot.ax.get_xscale() == "linear"
    null = [line for line in plot.ax.lines if list(line.get_xdata()) == [0, 0]]
    assert null
    m = "\N{MINUS SIGN}"
    assert f"{m}1.50 ({m}2.60 to {m}0.40)" in _texts(plot)
    assert plot.ax.get_xlim()[0] <= -2.6
    assert plot.ax.get_xlim()[1] >= 1.0


def test_ratio_ticks() -> None:
    assert _ratio_ticks(0.6, 1.3) == [0.5, 1.0, 2.0]
    assert _ratio_ticks(0.22, 1.38) == [0.2, 0.5, 1.0, 2.0]
    assert _ratio_ticks(0.01, 50) == [0.01, 0.1, 1.0, 10.0, 100.0]
    assert _difference_ticks(-2.6, 1.0)[0] <= -2.6


def test_null_line_position_and_hidden(subgroups: pd.DataFrame) -> None:
    def nulls(plot: sp.ForestPlot) -> list[float]:
        return [
            line.get_xdata()[0]
            for line in plot.ax.lines
            if len(line.get_xdata()) == 2 and line.get_xdata()[0] == line.get_xdata()[1]
        ]

    assert nulls(_forest(subgroups)) == [1.0]
    assert nulls(_forest(subgroups, null=0.8)) == [0.8]
    assert nulls(_forest(subgroups, null=False)) == []
    with pytest.raises(ValueError, match="line of no effect"):
        _forest(subgroups, null=False).favours("A", "B")


def test_xlim_clips_intervals_with_arrowheads(subgroups: pd.DataFrame) -> None:
    plot = _forest(subgroups).xlim(0.7, 1.5)
    markers = [line.get_marker() for line in plot.ax.lines]
    assert markers.count("<") == 5  # every lower limit is below 0.7
    assert markers.count(">") == 0  # no upper limit is above 1.5
    assert plot.ax.get_xlim() == (0.7, 1.5)


def test_favours_labels_and_arrows(subgroups: pd.DataFrame) -> None:
    plot = _forest(subgroups).favours("Favours drug", "Favours placebo")
    texts = _texts(plot)
    assert "Favours drug" in texts
    assert "Favours placebo" in texts
    arrows = [t for t in plot.ax.texts if t.get_text() == "" and t.arrow_patch]
    assert len(arrows) == 2


def test_refline_defaults_to_value_axis(subgroups: pd.DataFrame) -> None:
    plot = _forest(subgroups).refline(0.74)
    lines = [line for line in plot.ax.lines if line.get_linestyle() == "--"]
    assert list(lines[0].get_xdata()) == [0.74, 0.74]


# -------------------------------------------------------- weights and hue
def test_weights_scale_marker_area(subgroups: pd.DataFrame) -> None:
    frame = subgroups.assign(w=[np.nan, 40, 10, 30, 20])
    plot = _forest(frame, weight="w").summary("Overall")
    sizes = [line.get_markersize() for line in _markers(plot.ax)]
    assert sizes[0] / sizes[1] == pytest.approx(math.sqrt(40 / 10))


def test_item_without_weight_raises(subgroups: pd.DataFrame) -> None:
    frame = subgroups.assign(w=[np.nan, 40, 10, 30, 20])
    with pytest.raises(sp.DataShapeError, match="has no weight"):
        _forest(frame, weight="w").render()


def test_hue_dodges_rows_and_adds_legend() -> None:
    frame = pd.DataFrame(
        {
            "term": ["Age", "Age", "BMI", "BMI"],
            "model": ["Crude", "Adjusted"] * 2,
            "or": [1.4, 1.2, 1.1, 1.05],
            "lo": [1.1, 0.9, 0.9, 0.85],
            "hi": [1.8, 1.6, 1.3, 1.3],
        }
    )
    plot = sp.forest(
        frame, label="term", estimate="or", lower="lo", upper="hi", hue="model"
    )
    ys = sorted({line.get_ydata()[0] for line in _markers(plot.ax)})
    assert len(ys) == 4  # two rows x two models
    legend = plot.ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["Crude", "Adjusted"]
    crude = next(t for t in plot.ax.texts if t.get_text().startswith("1.40"))
    adjusted = next(t for t in plot.ax.texts if t.get_text().startswith("1.20"))
    assert crude.get_color() != adjusted.get_color()


# ------------------------------------------------------------------ panels
@pytest.fixture
def outcomes() -> pd.DataFrame:
    rows = []
    for outcome, shift in (("Efficacy", 0.0), ("Safety", 0.3)):
        for label, hr in (("Overall", 0.8), ("Women", 0.75), ("Men", 0.85)):
            rows.append(
                {
                    "outcome": outcome,
                    "label": label,
                    "n": 100,
                    "events": 10 + int(shift * 10),
                    "hr": hr + shift,
                    "lo": hr + shift - 0.15,
                    "hi": hr + shift + 0.2,
                }
            )
    return pd.DataFrame(rows)


def test_panels_side_by_side_share_rows(outcomes: pd.DataFrame) -> None:
    plot = sp.forest(
        outcomes, label="label", estimate="hr", lower="lo", upper="hi", panel="outcome"
    ).table(left=["n"], right={"Events": "events"})
    fig = plot.fig
    panels = plot._body.panels
    assert len(panels) == 2
    renderer = fig.canvas.get_renderer()
    fig.draw(renderer)
    first, second = (p.get_window_extent(renderer) for p in panels)
    assert first.x1 < second.x0
    assert first.width == pytest.approx(second.width, rel=0.02)
    texts = _texts(plot)
    assert {"Efficacy", "Safety", "10", "13"} <= set(texts)
    assert texts.count("HR (95% CI)") == 2
    assert texts.count("Overall") == 1  # labels are shared


def test_left_column_must_agree_between_panels(outcomes: pd.DataFrame) -> None:
    plot = sp.forest(
        outcomes, label="label", estimate="hr", lower="lo", upper="hi", panel="outcome"
    ).table(left=["events"])
    with pytest.raises(sp.DataShapeError, match=r"table\(right=\.\.\.\)"):
        plot.render()


# ------------------------------------------------------------- validation
def test_bad_input_is_rejected(subgroups: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="Did you mean 'subgroup'"):
        sp.forest(subgroups, label="subgrup", estimate="hr", lower="lo", upper="hi")
    with pytest.raises(sp.DataShapeError, match="lo <= hr <= hi"):
        _forest(subgroups.assign(lo=subgroups["hi"]))
    with pytest.raises(sp.DataShapeError, match="scale='difference'"):
        _forest(subgroups.assign(lo=0.0))
    with pytest.raises(sp.DataShapeError, match="more than once"):
        _forest(pd.concat([subgroups, subgroups.iloc[:1]]))
    with pytest.raises(ValueError, match="scale"):
        _forest(subgroups, scale="log")  # type: ignore[arg-type]


def test_missing_values_raise_or_drop(subgroups: pd.DataFrame) -> None:
    frame = subgroups.copy()
    frame.loc[2, "hi"] = np.nan
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        _forest(frame)
    plot = _forest(frame, missing="drop")
    assert ">=65 yr" not in [r.label for r in plot._rows()]


def test_too_narrow_for_table_raises(subgroups: pd.DataFrame) -> None:
    wide = {f"Column {i}": "n" for i in range(8)}
    with pytest.raises(sp.DataShapeError, match="too little room"):
        _forest(subgroups).table(left=wide).size(width="3in").render()


# ------------------------------------------------------------- integration
def test_height_grows_with_rows(subgroups: pd.DataFrame) -> None:
    sp.use(preset="nature")
    short = _forest(subgroups.iloc[:2]).style().height
    tall = _forest(subgroups).style().height
    assert tall > short
    assert _forest(subgroups).size(height="2in").style().height == pytest.approx(2)


def test_source_data_in_display_order(subgroups: pd.DataFrame) -> None:
    data = _forest(subgroups, group="variable").summary("Overall").source_data()
    assert list(data["label"]) == list(subgroups["subgroup"])
    assert list(data.columns) == [
        "group",
        "label",
        "summary",
        "estimate",
        "lower",
        "upper",
        "text",
    ]
    assert data["summary"].tolist() == [True, False, False, False, False]


def test_index_labels_and_title(subgroups: pd.DataFrame) -> None:
    frame = subgroups.set_index("subgroup")
    plot = sp.forest(frame, estimate="hr", lower="lo", upper="hi").labels(
        title="Primary end point"
    )
    texts = _texts(plot)
    assert "Overall" in texts
    assert "Subgroup" in texts
    assert "Primary end point" in texts
    assert plot.ax.get_title() == ""


def test_render_into_existing_axes_and_copy(subgroups: pd.DataFrame) -> None:
    fig, ax = plt.subplots(layout="constrained")
    try:
        plot = _forest(subgroups)
        plot.render(ax=ax)
        assert "Overall" in [t.get_text() for t in ax.texts]
        clone = plot.copy().stripes()
        assert clone.fig is not fig
    finally:
        plt.close(fig)


def test_highlight_mutes_other_rows(subgroups: pd.DataFrame) -> None:
    plot = _forest(subgroups).highlight("Female")
    colors = {line.get_markerfacecolor() for line in _markers(plot.ax)}
    assert len(colors) == 2


def test_options_lists_forest_steps(subgroups: pd.DataFrame) -> None:
    verbs = _forest(subgroups).options().index
    assert {"table", "estimates", "summary", "favours", "stripes", "groups"} <= set(
        verbs
    )
