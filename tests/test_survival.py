import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_hex

import SecretPlots as sp
from SecretPlots.core import survival as sv

# Freireich et al. (1963) leukaemia remission times, weeks: 6-MP vs placebo.
# Published: log-rank chi-square 16.79 (p = 4.2e-5); medians 23 and 8 weeks;
# Cox (Efron) hazard ratio placebo vs 6-MP 4.82 (95% CI 2.15-10.8).
_MP = [6, 6, 6, 6, 7, 9, 10, 10, 11, 13, 16, 17, 19, 20, 22, 23, 25, 32, 32, 34, 35]
_MP_EVENT = [1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
_PLACEBO = [1, 1, 2, 2, 3, 4, 4, 5, 5, 8, 8, 8, 8, 11, 11, 12, 12, 15, 17, 22, 23]


@pytest.fixture
def leukaemia() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "weeks": _MP + _PLACEBO,
            "relapse": _MP_EVENT + [1] * len(_PLACEBO),
            "arm": ["6-MP"] * len(_MP) + ["Placebo"] * len(_PLACEBO),
            "site": (["A", "B"] * 21),
        }
    )


def _km(frame: pd.DataFrame, **kwargs) -> sp.SurvivalPlot:
    return sp.survival(frame, time="weeks", event="relapse", hue="arm", **kwargs)


def _texts(plot: sp.SurvivalPlot) -> list[str]:
    return [t.get_text() for t in plot.ax.texts]


def _note(plot: sp.SurvivalPlot) -> list[str]:
    """Lines of the statistics box (the only multi-purpose text with a bbox)."""
    boxes = [t for t in plot.ax.texts if t.get_bbox_patch() is not None]
    assert len(boxes) == 1
    return boxes[0].get_text().split("\n")


# ------------------------------------------------------------ statistics
def test_kaplan_meier_matches_published_values() -> None:
    curve = sv.kaplan_meier(np.array(_MP, float), np.array(_MP_EVENT))
    at = dict(zip(curve.time, curve.estimate, strict=True))
    expected = {6: 0.857, 7: 0.807, 10: 0.753, 13: 0.690, 16: 0.627, 22: 0.538}
    for time, value in expected.items():
        assert at[time] == pytest.approx(value, abs=5e-4)
    assert at[23] == pytest.approx(0.448, abs=5e-4)
    assert curve.at_risk[0] == 21
    assert (curve.lower <= curve.estimate).all()
    assert (curve.estimate <= curve.upper).all()


def test_statistics_medians_and_counts(leukaemia: pd.DataFrame) -> None:
    stats = _km(leukaemia).statistics()
    assert list(stats.index) == ["6-MP", "Placebo"]
    assert stats.loc["6-MP", "median"] == 23
    assert stats.loc["Placebo", "median"] == 8
    assert stats.loc["6-MP", "events"] == 9
    assert stats.loc["6-MP", "censored"] == 12
    assert stats.loc["Placebo", "n"] == 21


def test_median_midpoint_when_curve_sits_at_half() -> None:
    # Survival is exactly 0.5 from t=2 until the next death at t=4.
    curve = sv.kaplan_meier(np.array([1.0, 2, 4, 5]), np.array([1, 1, 1, 1]))
    assert sv.survival_quantile(curve)[0] == 3.0


def test_logrank_and_hazard_ratio_match_published(leukaemia: pd.DataFrame) -> None:
    plot = _km(leukaemia).pvalue().hazard_ratio(ref="6-MP")
    results = plot.test_results()
    logrank = results.iloc[0]
    assert logrank["statistic"] == pytest.approx(16.79, abs=0.01)
    assert logrank["p"] == pytest.approx(4.17e-5, rel=0.01)
    cox = results.iloc[1]
    assert cox["comparison"] == "Placebo vs 6-MP"
    assert cox["hr"] == pytest.approx(4.82, abs=0.01)
    assert cox["hr_low"] == pytest.approx(2.15, abs=0.01)
    assert cox["hr_high"] == pytest.approx(10.8, abs=0.05)
    assert _note(plot) == [
        "Log-rank p < 0.001",
        "Placebo vs 6-MP: HR 4.82 (95% CI 2.15\N{EN DASH}10.81)",
    ]


@pytest.mark.parametrize(("x", "df"), [(0.0, 1), (3.84, 1), (5.99, 2), (7.81, 3)])
def test_chi2_sf_critical_values(x: float, df: int) -> None:
    assert sv.chi2_sf(x, df) == pytest.approx(0.05 if x else 1.0, abs=2e-4)


def test_trend_with_two_groups_equals_logrank(leukaemia: pd.DataFrame) -> None:
    plot = _km(leukaemia).pvalue().pvalue(trend=True)
    overall, trend = plot.test_results()["statistic"]
    assert trend == pytest.approx(overall)


def test_stratified_test_with_one_stratum_is_unstratified(
    leukaemia: pd.DataFrame,
) -> None:
    plain = _km(leukaemia).pvalue().test_results()["p"].iloc[0]
    single = _km(leukaemia.assign(site="all"), strata="site").pvalue()
    assert single.test_results()["p"].iloc[0] == pytest.approx(plain)
    assert single.test_results()["test"].iloc[0] == "Stratified log-rank"


def test_hazard_ratio_without_events_names_the_group(
    leukaemia: pd.DataFrame,
) -> None:
    frame = leukaemia.assign(
        relapse=np.where(leukaemia["arm"] == "6-MP", 0, leukaemia["relapse"])
    )
    with pytest.raises(sp.DataShapeError, match="no events in group '6-MP'"):
        _km(frame).hazard_ratio()


# ---------------------------------------------------------------- drawing
def test_curves_bands_and_censor_marks(leukaemia: pd.DataFrame) -> None:
    plot = _km(leukaemia)
    ax = plot.ax
    steps = [line for line in ax.lines if line.get_drawstyle() == "steps-post"]
    assert len(steps) == 2
    assert steps[0].get_ydata()[0] == 1.0
    assert len([c for c in ax.collections if isinstance(c, PolyCollection)]) == 2
    marks = [line for line in ax.lines if line.get_marker() == "|"]
    # 6-MP has 12 censorings at 11 distinct times; placebo has none.
    assert [len(m.get_xdata()) for m in marks] == [11]
    assert ax.get_ylim() == (0, 1)
    assert ax.get_xlim()[0] == 0
    assert ax.get_ylabel() == "Survival probability"
    assert ax.get_xlabel() == "Weeks"


def test_ci_and_censors_can_be_hidden(leukaemia: pd.DataFrame) -> None:
    ax = _km(leukaemia).ci(False).censors(False).ax
    assert not [c for c in ax.collections if isinstance(c, PolyCollection)]
    assert not [line for line in ax.lines if line.get_marker() == "|"]


def test_failure_is_one_minus_survival(leukaemia: pd.DataFrame) -> None:
    survival = _km(leukaemia).source_data()
    failure = _km(leukaemia, kind="failure").source_data()
    np.testing.assert_allclose(failure["failure"], 1 - survival["survival"])
    np.testing.assert_allclose(failure["failure_low"], 1 - survival["survival_high"])
    assert _km(leukaemia, kind="failure").ax.get_ylabel() == "Cumulative incidence"


def test_cumulative_hazard_rises_and_has_no_median(leukaemia: pd.DataFrame) -> None:
    plot = _km(leukaemia, kind="cumhaz")
    data = plot.source_data()
    for _, part in data.groupby("arm"):
        assert np.all(np.diff(part["cumhaz"]) >= 0)
    assert plot.ax.get_ylabel() == "Cumulative hazard"
    with pytest.raises(sp.DataShapeError, match="median lines"):
        plot.median()


def test_median_lines(leukaemia: pd.DataFrame) -> None:
    ax = _km(leukaemia).median(label=True).ax
    dotted = [line for line in ax.lines if line.get_linestyle() == ":"]
    assert [list(line.get_xdata()) for line in dotted] == [[0, 23], [23, 23], [8, 8]]
    assert {"23", "8"} <= {t.get_text() for t in ax.texts}


# ------------------------------------------------------------- risk table
def test_risk_table_counts_under_ticks(leukaemia: pd.DataFrame) -> None:
    plot = _km(leukaemia).risk_table("at_risk", "events", times=[0, 10, 20, 30])
    texts = _texts(plot)
    assert list(plot.ax.get_xticks()) == [0, 10, 20, 30]
    assert texts[:2] == ["Number at risk", "6-MP"]
    # 6-MP at risk: 21 at 0, 15 at 10 (time >= 10), 8 at 20, 4 at 30.
    assert texts[2:6] == ["21", "15", "8", "4"]
    assert texts[6:11] == ["Placebo", "21", "8", "2", "0"]
    assert "Cumulative events" in texts
    events = texts[texts.index("Cumulative events") + 1 :][:10]
    assert events == ["6-MP", "0", "5", "7", "9", "Placebo", "0", "13", "19", "21"]


def test_risk_table_sits_below_the_axis_title(leukaemia: pd.DataFrame) -> None:
    plot = _km(leukaemia).risk_table()
    fig = plot.fig
    renderer = fig.canvas.get_renderer()
    title = plot.ax.xaxis.label.get_window_extent(renderer)
    header = next(t for t in plot.ax.texts if t.get_text() == "Number at risk")
    box = header.get_window_extent(renderer)
    assert box.y1 <= title.y0
    assert box.y0 >= 0  # still inside the figure
    six = next(t for t in plot.ax.texts if t.get_text() == "6-MP")
    curve = next(line for line in plot.ax.lines if line.get_drawstyle() == "steps-post")
    assert to_hex(six.get_color()) == to_hex(curve.get_color())
    # Labels clear the first column, which is centred on the axes' edge.
    first = next(t for t in plot.ax.texts if t.get_text() == "21")
    assert six.get_window_extent(renderer).x1 < first.get_window_extent(renderer).x0


def test_risk_table_grows_the_figure_unless_height_is_set(
    leukaemia: pd.DataFrame,
) -> None:
    plain = _km(leukaemia).style().height
    assert _km(leukaemia).risk_table().style().height > plain
    fixed = _km(leukaemia).risk_table().size(height=3).style().height
    assert fixed == 3


def test_risk_table_without_groups_and_removal(leukaemia: pd.DataFrame) -> None:
    plot = sp.survival(leukaemia, time="weeks", event="relapse").risk_table()
    assert "All" in _texts(plot)
    assert plot.ax.get_legend() is None
    assert "Number at risk" not in _texts(plot.risk_table(show=False))


def test_risk_table_validates(leukaemia: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Did you mean 'at_risk'"):
        _km(leukaemia).risk_table("at risk")
    with pytest.raises(ValueError, match="increase"):
        _km(leukaemia).risk_table(times=[0, 20, 10])


# ------------------------------------------------------------- annotations
def test_user_values_and_free_text(leukaemia: pd.DataFrame) -> None:
    plot = (
        _km(leukaemia)
        .pvalue(0.04, label="P for interaction")
        .pvalue(0.0002)
        .hazard_ratio((0.21, 0.09, 0.47), label="Adjusted HR", ref="Placebo")
        .annotate("Median follow-up 24 weeks")
    )
    assert _note(plot) == [
        "P for interaction = 0.04",
        "p < 0.001",
        "6-MP vs Placebo: Adjusted HR 0.21 (95% CI 0.09\N{EN DASH}0.47)",
        "Median follow-up 24 weeks",
    ]
    assert plot.test_results().empty
    cleared = plot.pvalue(False).hazard_ratio(False)
    assert _note(cleared) == ["Median follow-up 24 weeks"]


def test_note_location(leukaemia: pd.DataFrame) -> None:
    def anchor(plot: sp.SurvivalPlot) -> tuple[str, str]:
        box = next(t for t in plot.ax.texts if t.get_bbox_patch() is not None)
        return box.get_ha(), box.get_va()

    assert anchor(_km(leukaemia).pvalue()) == ("left", "bottom")
    assert anchor(_km(leukaemia, kind="failure").pvalue()) == ("left", "top")
    assert anchor(_km(leukaemia).pvalue().annotate(loc="upper right")) == (
        "right",
        "top",
    )
    with pytest.raises(ValueError, match="Did you mean 'upper left'"):
        _km(leukaemia).annotate(loc="upper-left")


def test_pairwise_and_trend_lines() -> None:
    rng = np.random.default_rng(0)
    stage = np.repeat(["I", "II", "III"], 40)
    time = rng.exponential(np.repeat([30, 20, 10], 40))
    frame = pd.DataFrame({"t": time, "e": 1, "stage": stage})
    plot = (
        sp.survival(frame, time="t", event="e", hue="stage")
        .pvalue(trend=[1, 2, 4])
        .pvalue(test="wilcoxon", pairwise=True, correction="holm")
    )
    lines = _note(plot)
    assert lines[0].startswith("Log-rank test for trend p")
    assert lines[1] == "Gehan-Breslow-Wilcoxon (Holm-adjusted)"
    assert [line.split(":")[0] for line in lines[2:]] == [
        "I vs II",
        "I vs III",
        "II vs III",
    ]
    assert len(plot.test_results()) == 4


def test_annotation_validation(leukaemia: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="hue="):
        sp.survival(leukaemia, time="weeks", event="relapse").pvalue()
    with pytest.raises(ValueError, match="between 0 and 1"):
        _km(leukaemia).pvalue(1.5)
    with pytest.raises(ValueError, match="pairwise"):
        _km(leukaemia).pvalue(correction="holm")
    with pytest.raises(ValueError, match="one score per group"):
        _km(leukaemia).pvalue(trend=[1, 2, 3])
    with pytest.raises(ValueError, match="Did you mean 'wilcoxon'"):
        _km(leukaemia).pvalue(test="wilcoxen")
    with pytest.raises(ValueError, match=r"\(hr, lower, upper\)"):
        _km(leukaemia).hazard_ratio((0.5, 0.6, 0.9))
    with pytest.raises(sp.DataShapeError, match="not a group"):
        _km(leukaemia).hazard_ratio({"Drug": 0.5})
    with pytest.raises(sp.DataShapeError, match="not a group"):
        _km(leukaemia).hazard_ratio(ref="Drug")


# ------------------------------------------------------------------ input
def test_boolean_events_and_hue_order(leukaemia: pd.DataFrame) -> None:
    frame = leukaemia.assign(relapse=leukaemia["relapse"].astype(bool))
    plot = _km(frame, hue_order=["Placebo", "6-MP"])
    assert plot.statistics().index.tolist() == ["Placebo", "6-MP"]


def test_input_validation(leukaemia: pd.DataFrame) -> None:
    with pytest.raises(sp.DataShapeError, match="must be 1/True"):
        _km(leukaemia.assign(relapse="dead"))
    with pytest.raises(sp.DataShapeError, match="negative"):
        _km(leukaemia.assign(weeks=-leukaemia["weeks"]))
    with pytest.raises(ValueError, match="Did you mean 'weeks'"):
        sp.survival(leukaemia, time="week", event="relapse")
    with pytest.raises(ValueError, match="Did you mean 'cumhaz'"):
        _km(leukaemia, kind="cumhazard")
    missing = leukaemia.astype({"weeks": float})
    missing.loc[0, "weeks"] = np.nan
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        _km(missing)
    assert _km(missing, missing="drop").statistics().loc["6-MP", "n"] == 20


def test_copy_and_drawing_into_user_axes(leukaemia: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plot = _km(leukaemia).risk_table().pvalue()
    fig, axes = plt.subplots(1, 2, figsize=(9, 5), layout="constrained")
    plot.copy().render(ax=axes[0])
    plot.render(ax=axes[1])
    assert "Number at risk" in [t.get_text() for t in axes[0].texts]
    plt.close(fig)


def test_options_lists_survival_steps() -> None:
    verbs = sp.SurvivalPlot.options().index
    for verb in ("ci", "censors", "risk_table", "median", "pvalue", "hazard_ratio"):
        assert verb in verbs
