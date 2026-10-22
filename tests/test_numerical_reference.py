"""Independent SciPy oracles (development dependency only)."""

import numpy as np
import pytest
from scipy import stats as reference
from scipy.cluster.hierarchy import cophenet, linkage

from SecretPlots.core import cluster, stats


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
