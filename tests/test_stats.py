import math

import numpy as np
import pytest

from SecretPlots.core import stats
from SecretPlots.errors import DataShapeError

# Reference values from scipy 1.18 (scipy is not a dependency).
A = np.array([5.1, 4.8, 6.0, 5.5, 5.9, 6.3, 4.9])
B = np.array([6.8, 7.1, 5.9, 6.5, 7.4, 6.9])


def test_welch_matches_scipy() -> None:
    result = stats.welch(A, B)
    assert result.statistic == pytest.approx(-4.127927351731532)
    assert result.p == pytest.approx(0.0016865446124608688, rel=1e-9)


def test_student_matches_scipy() -> None:
    result = stats.student(A, B)
    assert result.statistic == pytest.approx(-4.087166241372546)
    assert result.p == pytest.approx(0.0017981658207580403, rel=1e-9)


def test_mann_whitney_exact_without_ties() -> None:
    b = np.array([6.8, 7.1, 5.95, 6.5, 7.4, 6.9])
    result = stats.mann_whitney(A, b)
    assert result.statistic == 2.0
    assert result.p == pytest.approx(0.004662004662004662, rel=1e-12)


def test_mann_whitney_normal_approximation_with_ties() -> None:
    result = stats.mann_whitney(A, B)  # 5.9 appears in both
    assert result.statistic == 2.5
    assert result.p == pytest.approx(0.010024934710329487, rel=1e-9)
    c = np.array([5.0, 5.0, 6.0, 6.0, 7.0, 4.0, 5.5, 6.5])
    d = np.array([6.0, 7.0, 7.0, 8.0, 6.5, 7.5])
    assert stats.mann_whitney(c, d).p == pytest.approx(0.018785774190658848)


def test_exact_u_distribution_counts_all_arrangements() -> None:
    counts = stats._u_counts(4, 6)
    assert counts.sum() == math.comb(10, 4)
    assert len(counts) == 4 * 6 + 1
    assert np.allclose(counts, counts[::-1])  # symmetric


def test_t_test_needs_variation() -> None:
    with pytest.raises(DataShapeError, match="vary"):
        stats.welch(np.ones(3), np.ones(4))


def test_holm_and_bonferroni() -> None:
    p = [0.01, 0.04, 0.03, 0.2]
    assert stats.adjust(p, "holm") == pytest.approx([0.04, 0.09, 0.09, 0.2])
    assert stats.adjust(p, "bonferroni") == pytest.approx([0.04, 0.16, 0.12, 0.8])
    assert stats.adjust(p, None) == pytest.approx(p)


def test_box_stats_tukey_whiskers() -> None:
    values = np.r_[np.arange(1.0, 11.0), 30.0]
    s = stats.box_stats(values)
    q1, median, q3 = np.percentile(values, [25, 50, 75])
    assert (s.q1, s.median, s.q3) == pytest.approx((q1, median, q3))
    assert s.whisker_low == 1.0
    assert s.whisker_high == 10.0
    assert s.outliers.tolist() == [30.0]
    assert s.notch_high - s.median == pytest.approx(1.58 * (q3 - q1) / math.sqrt(11))


def test_box_stats_range_and_percentiles() -> None:
    values = np.r_[np.arange(1.0, 11.0), 30.0]
    full = stats.box_stats(values, "range")
    assert (full.whisker_low, full.whisker_high) == (1.0, 30.0)
    assert len(full.outliers) == 0
    pct = stats.box_stats(values, (10, 90))
    assert pct.whisker_high == pytest.approx(np.percentile(values, 90))


@pytest.mark.parametrize("whis", [-1, (30, 95), (5, 60), "max", True])
def test_bad_whiskers(whis: object) -> None:
    with pytest.raises(ValueError, match="whis"):
        stats.check_whiskers(whis)
