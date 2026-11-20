import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PolyCollection

import SecretPlots as sp


@pytest.fixture
def tiny() -> pd.DataFrame:
    return pd.DataFrame({"y": [1, 1, 0, 0, 0], "risk": [0.9, 0.4, 0.6, 0.2, 0.1]})


@pytest.fixture
def cohort() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    score = rng.normal(size=300)
    logit = -1.2 + 1.4 * score
    return pd.DataFrame(
        {
            "event": rng.random(300) < 1 / (1 + np.exp(-logit)),
            "model": 1 / (1 + np.exp(-logit)),
            "marker": 1 / (1 + np.exp(-(-1.2 + 0.5 * score))),
        }
    )


def _brute_force(y: np.ndarray, p: np.ndarray, pt: float) -> float:
    treated = p >= pt
    tp = np.sum(treated & (y == 1))
    fp = np.sum(treated & (y == 0))
    return tp / len(y) - fp / len(y) * pt / (1 - pt)


def _values(plot: sp.DecisionCurvePlot, model: str) -> np.ndarray:
    table = plot.source_data()
    return table.loc[table["model"] == model].iloc[:, 2].to_numpy()


# ------------------------------------------------------------ statistics
def test_net_benefit_hand_calculation(tiny: pd.DataFrame) -> None:
    plot = sp.dca(tiny, "y", "risk", thresholds=[0.25, 0.5])
    # pt 0.25: TP 2, FP 1 -> 2/5 - 1/5 * 1/3; pt 0.5: TP 1, FP 1 -> 0.
    assert _values(plot, "risk") == pytest.approx([0.4 - 0.2 / 3, 0.0])
    # Treat all: prevalence 0.4 - 0.6 * odds.
    assert _values(plot, "Treat all") == pytest.approx([0.2, -0.2])
    assert _values(plot, "Treat none") == pytest.approx([0.0, 0.0])


def test_net_benefit_matches_brute_force(cohort: pd.DataFrame) -> None:
    plot = sp.decision_curve(cohort, outcome="event", models=["model", "marker"])
    y = cohort["event"].to_numpy(int)
    for name in ("model", "marker"):
        expected = [
            _brute_force(y, cohort[name].to_numpy(), t) for t in np.arange(1, 100) / 100
        ]
        assert _values(plot, name) == pytest.approx(expected)


def test_threshold_equal_to_risk_counts_as_treated() -> None:
    data = {"y": [1, 0], "r": [0.3, 0.1]}
    assert _values(sp.dca(data, "y", "r", thresholds=[0.3, 0.5]), "r")[0] == 0.5


def test_interventions_avoided(cohort: pd.DataFrame) -> None:
    grid = [0.1, 0.2, 0.3]
    benefit = sp.dca(cohort, "event", "model", thresholds=grid)
    avoided = sp.dca(
        cohort, "event", "model", thresholds=grid, measure="interventions_avoided"
    )
    odds = np.array(grid) / (1 - np.array(grid))
    expected = (_values(benefit, "model") - _values(benefit, "Treat all")) / odds
    assert _values(avoided, "model") == pytest.approx(expected * 100)
    assert _values(avoided, "Treat all") == pytest.approx([0, 0, 0])
    assert "Treat none" not in set(avoided.source_data()["model"])
    assert "interventions_avoided" in avoided.source_data().columns


def test_bootstrap_bands_cover_estimate_and_are_reproducible(
    cohort: pd.DataFrame,
) -> None:
    plot = sp.dca(cohort, "event", "model", thresholds=[0.1, 0.3, 0.5]).ci(n_boot=200)
    table = plot.source_data()
    rows = table[table["model"] == "model"]
    assert (rows["net_benefit_low"] <= rows["net_benefit"]).all()
    assert (rows["net_benefit"] <= rows["net_benefit_high"]).all()
    again = plot.copy().source_data()
    pd.testing.assert_frame_equal(table, again)
    narrower = (
        sp.dca(cohort, "event", "model", thresholds=[0.1, 0.3, 0.5])
        .ci(n_boot=200, level=0.5)
        .source_data()
    )
    n = narrower[narrower["model"] == "model"]
    assert (
        (n["net_benefit_high"] - n["net_benefit_low"]).to_numpy()
        <= (rows["net_benefit_high"] - rows["net_benefit_low"]).to_numpy()
    ).all()


# --------------------------------------------------------------- drawing
def test_draws_models_then_references(cohort: pd.DataFrame) -> None:
    plot = sp.dca(cohort, "event", ["model", "marker"])
    labels = [t.get_text() for t in plot.ax.get_legend().get_texts()]
    assert labels == ["model", "marker", "Treat all", "Treat none"]
    assert plot.ax.get_xlim() == pytest.approx((0.01, 0.99))
    low, high = plot.ax.get_ylim()
    assert low < 0 < high
    assert high >= cohort["event"].mean()
    assert not [c for c in plot.ax.collections if isinstance(c, PolyCollection)]


def test_references_hidden(cohort: pd.DataFrame) -> None:
    plot = sp.dca(cohort, "event", "model").references(treat_all=False)
    labels = [t.get_text() for t in plot.ax.get_legend().get_texts()]
    assert labels == ["model", "Treat none"]
    none = sp.dca(cohort, "event", "model").references(
        treat_all=False, treat_none=False
    )
    assert len(none.ax.lines) == 1


def test_ci_draws_one_band_per_model(cohort: pd.DataFrame) -> None:
    plot = sp.dca(cohort, "event", ["model", "marker"]).ci(n_boot=50)
    bands = [c for c in plot.ax.collections if isinstance(c, PolyCollection)]
    assert len(bands) == 2
    assert len(plot.copy().ci(False).ax.collections) == 0


def test_highlight_and_colors_use_model_names(cohort: pd.DataFrame) -> None:
    plot = sp.dca(cohort, "event", ["model", "marker"]).colors({"model": "#ff0000"})
    assert plot.ax.lines[0].get_color() == "#ff0000"
    sp.dca(cohort, "event", ["model", "marker"]).highlight("marker").render()
    with pytest.raises(sp.DataShapeError, match="not a group"):
        sp.dca(cohort, "event", ["model"]).highlight("nope").render()


def test_default_labels(cohort: pd.DataFrame) -> None:
    ax = sp.dca(cohort, "event", "model").ax
    assert ax.get_xlabel() == "Threshold probability"
    assert ax.get_ylabel() == "Net benefit"


# ------------------------------------------------------------ validation
def test_missing_values_raise_or_drop(tiny: pd.DataFrame) -> None:
    tiny.loc[0, "risk"] = np.nan
    with pytest.raises(sp.DataShapeError, match="missing='drop'"):
        sp.dca(tiny, "y", "risk")
    plot = sp.dca(tiny, "y", "risk", thresholds=[0.5, 0.6], missing="drop")
    assert _values(plot, "Treat all")[0] == pytest.approx(0.25 - 0.75)


def test_rejects_non_probability(tiny: pd.DataFrame) -> None:
    tiny["score"] = [2.0, 1.0, 0.0, -1.0, 0.5]
    with pytest.raises(sp.DataShapeError, match="between 0 and 1"):
        sp.dca(tiny, "y", "score")


def test_rejects_bad_outcome() -> None:
    with pytest.raises(sp.DataShapeError, match="1/True or 0/False"):
        sp.dca({"y": [2, 0], "r": [0.1, 0.2]}, "y", "r")
    with pytest.raises(sp.DataShapeError, match="with and without"):
        sp.dca({"y": [1, 1], "r": [0.1, 0.2]}, "y", "r")


def test_unknown_column_suggests(tiny: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Did you mean 'risk'"):
        sp.dca(tiny, "y", "rsk")


@pytest.mark.parametrize(
    ("thresholds", "match"),
    [
        ([0.5], "at least two"),
        ([0.0, 0.5], "strictly between"),
        ([0.5, 1.0], "strictly between"),
        ([0.5, 0.2], "increase"),
    ],
)
def test_rejects_bad_thresholds(
    tiny: pd.DataFrame, thresholds: list[float], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        sp.dca(tiny, "y", "risk", thresholds=thresholds)


def test_rejects_bad_arguments(tiny: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Did you mean 'net_benefit'"):
        sp.dca(tiny, "y", "risk", measure="net_benefits")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="appear once"):
        sp.dca(tiny, "y", ["risk", "risk"])
    with pytest.raises(ValueError, match="n_boot"):
        sp.dca(tiny, "y", "risk").ci(n_boot=10)
    with pytest.raises(ValueError, match="level"):
        sp.dca(tiny, "y", "risk").ci(level=95)
