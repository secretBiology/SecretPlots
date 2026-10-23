"""Independent SciPy and lifelines oracles (development dependencies only)."""

import numpy as np
import pandas as pd
import pytest
from lifelines import CoxPHFitter, KaplanMeierFitter, NelsonAalenFitter
from lifelines.statistics import multivariate_logrank_test, pairwise_logrank_test
from scipy import stats as reference
from scipy.cluster.hierarchy import cophenet, linkage

import SecretPlots as sp
from SecretPlots.core import cluster, stats
from SecretPlots.core import survival as sv

# lifelines' own pandas/datetime deprecations; not ours to fix.
pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning:lifelines.*"),
    pytest.mark.filterwarnings("ignore::FutureWarning:lifelines.*"),
]


@pytest.mark.parametrize("df", [1, 2, 3, 4, 7.5, 30, 1000])
@pytest.mark.parametrize("p", [0.001, 0.025, 0.5, 0.975, 0.995, 0.9995])
def test_t_quantile_against_scipy(df, p):
    assert stats.t_quantile(p, df) == pytest.approx(
        reference.t.ppf(p, df), rel=2e-8, abs=1e-12
    )


@pytest.mark.parametrize("sizes", [(2, 3), (7, 11), (49, 45), (50, 60)])
@pytest.mark.parametrize("seed", [0, 7, 42])
def test_two_sample_tests_against_scipy(sizes, seed):
    rng = np.random.default_rng(seed)
    a, b = rng.normal(size=sizes[0]), rng.normal(0.7, 2, size=sizes[1])
    for fn, equal_var in ((stats.welch, False), (stats.student, True)):
        actual = fn(a, b)
        expected = reference.ttest_ind(a, b, equal_var=equal_var)
        assert actual.statistic == pytest.approx(expected.statistic, rel=1e-10)
        assert actual.p == pytest.approx(expected.pvalue, rel=1e-9)
    for tied in (False, True):
        x, y = (np.round(a), np.round(b)) if tied else (a, b)
        exact = len(np.unique(np.r_[x, y])) == len(x) + len(y) and max(sizes) < 50
        expected = reference.mannwhitneyu(
            x, y, method="exact" if exact else "asymptotic"
        )
        actual = stats.mann_whitney(x, y)
        assert actual.statistic == expected.statistic
        assert actual.p == pytest.approx(expected.pvalue, rel=1e-10, abs=1e-15)


def test_mann_whitney_retains_small_tail_probabilities():
    a, b = np.arange(60.0), np.arange(60.0, 120.0)
    assert stats.mann_whitney(a, b).p == pytest.approx(
        reference.mannwhitneyu(a, b, method="asymptotic").pvalue, rel=1e-10, abs=0
    )


@pytest.mark.parametrize("method", ["single", "complete", "average", "ward"])
@pytest.mark.parametrize("metric", ["euclidean", "cosine", "correlation"])
@pytest.mark.parametrize("seed", [0, 42])
def test_clustering_against_scipy(method, metric, seed):
    if method == "ward" and metric != "euclidean":
        with pytest.raises(ValueError, match="euclidean"):
            cluster.linkage(np.eye(3), method=method, metric=metric)
        return
    values = np.random.default_rng(seed).normal(size=(15, 6))
    tree = cluster.linkage(values, method=method, metric=metric)
    sizes = dict.fromkeys(range(tree.n), 1)
    rows = []
    for i, (a, b, height) in enumerate(tree.merges):
        count = sizes[a] + sizes[b]
        sizes[tree.n + i] = count
        rows.append([a, b, height, count])
    # Cophenetic distances are independent of arbitrary leaf orientation.
    actual = cophenet(np.asarray(rows))
    expected = cophenet(linkage(values, method=method, metric=metric))
    assert actual == pytest.approx(expected, rel=1e-10, abs=1e-12)


def test_kernel_density_against_scipy():
    values = np.random.default_rng(3).normal(size=50)
    grid = np.linspace(-4, 4, 100)
    bw = stats.bandwidth(values, 0.8)
    oracle = reference.gaussian_kde(values, bw_method=bw / values.std(ddof=1))
    assert stats.gaussian_kde(values, grid, bw) == pytest.approx(
        oracle(grid), rel=1e-12
    )
    expected = [oracle.integrate_box_1d(-np.inf, x) for x in grid]
    assert stats.gaussian_kde(values, grid, bw, cumulative=True) == pytest.approx(
        expected, abs=2e-7
    )


# ---------------------------------------------------------------- survival
def _cohort(seed: int, n: int = 240) -> pd.DataFrame:
    """Three arms, two strata, tied times (rounded) and ~30 % censoring.
    Times start at 1: lifelines' Fleming-Harrington weights fail at t = 0."""
    rng = np.random.default_rng(seed)
    arm = rng.integers(0, 3, n)
    site = rng.integers(0, 2, n)
    event_time = np.round(rng.exponential(12 / (1 + 0.4 * arm + 0.3 * site))) + 1
    censor_time = np.round(rng.exponential(25, n)) + 1
    return pd.DataFrame(
        {
            "t": np.minimum(event_time, censor_time),
            "e": (event_time <= censor_time).astype(int),
            "arm": arm,
            "site": site,
        }
    )


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_kaplan_meier_and_nelson_aalen_against_lifelines(seed):
    frame = _cohort(seed)
    t, e = frame["t"].to_numpy(float), frame["e"].to_numpy()
    km = sv.kaplan_meier(t, e)
    fitter = KaplanMeierFitter().fit(t, e)
    expected = fitter.survival_function_["KM_estimate"].reindex(km.time)
    assert km.estimate == pytest.approx(expected.to_numpy(), abs=1e-12)
    bounds = fitter.confidence_interval_.reindex(km.time).to_numpy()
    assert km.lower == pytest.approx(bounds[:, 0], abs=1e-10)
    assert km.upper == pytest.approx(bounds[:, 1], abs=1e-10)
    assert sv.survival_quantile(km)[0] == fitter.median_survival_time_
    na = sv.nelson_aalen(t, e)
    hazard = NelsonAalenFitter(nelson_aalen_smoothing=False).fit(t, e)
    expected = hazard.cumulative_hazard_.iloc[:, 0].reindex(na.time)
    assert na.estimate == pytest.approx(expected.to_numpy(), abs=1e-12)


@pytest.mark.parametrize(
    "weighting", ["logrank", "wilcoxon", "tarone-ware", "peto", "fleming-harrington"]
)
@pytest.mark.parametrize("seed", [0, 1])
def test_logrank_family_against_lifelines(weighting, seed):
    frame = _cohort(seed)
    kwargs = {"p": 0.5, "q": 1.5} if weighting == "fleming-harrington" else {}
    expected = multivariate_logrank_test(
        frame["t"],
        frame["arm"],
        frame["e"],
        weightings=None if weighting == "logrank" else weighting,
        **kwargs,
    )
    actual = sv.logrank(
        frame["t"].to_numpy(float),
        frame["e"].to_numpy(),
        frame["arm"].to_numpy(),
        weighting=weighting,
        rho=0.5,
        gamma=1.5,
    )
    assert actual.statistic == pytest.approx(expected.test_statistic, rel=1e-10)
    assert actual.p == pytest.approx(expected.p_value, rel=1e-9)
    assert actual.df == 2


def test_pairwise_logrank_against_lifelines():
    frame = _cohort(3)
    expected = pairwise_logrank_test(frame["t"], frame["arm"], frame["e"]).summary
    plot = sp.survival(frame, time="t", event="e", hue="arm", hue_order=[0, 1, 2])
    actual = plot.pvalue(pairwise=True).test_results()
    assert actual["p"].to_numpy() == pytest.approx(expected["p"].to_numpy(), rel=1e-9)


@pytest.mark.parametrize("stratified", [False, True])
@pytest.mark.parametrize("seed", [0, 1])
def test_group_hazard_ratios_against_lifelines(stratified, seed):
    frame = _cohort(seed)
    design = pd.DataFrame(
        {
            "t": frame["t"],
            "e": frame["e"],
            "arm1": (frame["arm"] == 1).astype(int),
            "arm2": (frame["arm"] == 2).astype(int),
            "site": frame["site"],
        }
    )
    # lifelines stops early by default; even with a tight tolerance it
    # agrees with our Newton solution to about 2e-7.
    fitter = CoxPHFitter().fit(
        design if stratified else design.drop(columns="site"),
        "t",
        "e",
        strata=["site"] if stratified else None,
        fit_options={"precision": 1e-12},
    )
    expected = fitter.summary
    actual = sv.cox_groups(
        frame["t"].to_numpy(float),
        frame["e"].to_numpy(),
        frame["arm"].to_numpy(),
        strata=frame["site"].to_numpy() if stratified else None,
    )
    assert actual.ratio[1:] == pytest.approx(expected["exp(coef)"].to_numpy(), rel=1e-6)
    assert actual.lower[1:] == pytest.approx(
        expected["exp(coef) lower 95%"].to_numpy(), rel=1e-6
    )
    assert actual.upper[1:] == pytest.approx(
        expected["exp(coef) upper 95%"].to_numpy(), rel=1e-6
    )
    assert actual.p[1:] == pytest.approx(expected["p"].to_numpy(), rel=1e-5)


@pytest.mark.parametrize("df", [1, 2, 3, 4, 5, 8, 11])
@pytest.mark.parametrize("x", [0.01, 0.5, 3.0, 9.5, 40.0, 300.0])
def test_chi2_sf_against_scipy(df, x):
    assert sv.chi2_sf(x, df) == pytest.approx(
        reference.chi2.sf(x, df), rel=1e-12, abs=1e-300
    )
