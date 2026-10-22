"""Small statistics helpers (numpy only, no scipy): kernel densities, box-plot
summaries and two-sample tests for significance brackets."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import numpy as np

from SecretPlots.errors import DataShapeError

Whiskers = float | tuple[float, float] | Literal["range"]
TestName = Literal["mann-whitney", "welch", "t-test"]
Correction = Literal["holm", "bonferroni"]

#: Notch half-width factor: median +- 1.58 IQR / sqrt(n) (McGill, Tukey &
#: Larsen 1978; R's ``boxplot.stats``). Non-overlapping notches suggest the
#: medians differ (roughly at the 5 % level).
NOTCH_FACTOR = 1.58
#: Groups smaller than this (and without ties) get exact Mann-Whitney p-values.
EXACT_LIMIT = 50


# --------------------------------------------------------------- densities
def bandwidth(values: np.ndarray, adjust: float) -> float:
    """Scott's rule (n^-1/5) on a robust spread (the smaller of the standard
    deviation and IQR / 1.349), times ``adjust``."""
    n = len(values)
    sd = float(np.std(values, ddof=1)) if n > 1 else 0.0
    iqr = float(np.subtract(*np.percentile(values, [75, 25])))
    spread = min(sd, iqr / 1.349) if iqr > 0 else sd
    if spread == 0:
        raise DataShapeError("A density curve needs values that are not all equal")
    return float(spread * n ** (-1 / 5) * adjust)


def erf(x: np.ndarray) -> np.ndarray:
    """Error function (Abramowitz & Stegun 7.1.26, error < 1.5e-7)."""
    t = 1 / (1 + 0.3275911 * np.abs(x))
    poly = t * (
        0.254829592
        + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))
    )
    return np.asarray(np.sign(x) * (1 - poly * np.exp(-(x**2))), dtype=float)


def gaussian_kde(
    values: np.ndarray, grid: np.ndarray, bw: float, *, cumulative: bool = False
) -> np.ndarray:
    """Gaussian kernel density (or its cumulative distribution) on ``grid``."""
    total = np.zeros_like(grid)
    for chunk in np.array_split(values, max(1, len(values) // 2000)):
        z = (grid[:, None] - chunk[None, :]) / bw
        if cumulative:
            total += (0.5 * (1 + erf(z / math.sqrt(2)))).sum(axis=1)
        else:
            total += np.exp(-0.5 * z**2).sum(axis=1)
    if cumulative:
        return np.asarray(total / len(values), dtype=float)
    return np.asarray(total / (len(values) * bw * math.sqrt(2 * math.pi)), dtype=float)


# ---------------------------------------------------------------- box plots
@dataclass(frozen=True)
class BoxStats:
    """What one box shows. Quartiles use linear interpolation (R's default
    ``quantile`` type 7, as in ggplot2 and numpy)."""

    n: int
    mean: float
    sd: float
    minimum: float
    q1: float
    median: float
    q3: float
    maximum: float
    whisker_low: float
    whisker_high: float
    notch_low: float
    notch_high: float
    outliers: np.ndarray

    @property
    def iqr(self) -> float:
        return self.q3 - self.q1


def check_whiskers(whis: object) -> None:
    if whis == "range":
        return
    if isinstance(whis, int | float) and not isinstance(whis, bool):
        if whis < 0:
            raise ValueError("whis must be 0 or more (a multiple of the IQR)")
        return
    if isinstance(whis, tuple | list) and len(whis) == 2:
        low, high = whis
        if 0 <= low < 25 and 75 < high <= 100:
            return
        raise ValueError(
            "whis as percentiles must be (low, high) with 0 <= low < 25 and "
            "75 < high <= 100, e.g. (5, 95)"
        )
    raise ValueError(
        f"Unknown whis={whis!r}. Use a multiple of the IQR (1.5, Tukey's rule), "
        "percentiles like (5, 95), or 'range' (minimum to maximum)."
    )


def box_stats(values: np.ndarray, whis: Whiskers = 1.5) -> BoxStats:
    """Median, quartiles, whisker ends and outliers of ``values``.

    ``whis`` is a multiple of the IQR (whiskers reach the most extreme value
    within that distance of the box; Tukey's 1.5 by default), a pair of
    percentiles such as ``(5, 95)``, or ``"range"`` (minimum to maximum).
    """
    values = np.sort(np.asarray(values, dtype=float))
    n = len(values)
    q1, median, q3 = (float(q) for q in np.percentile(values, [25, 50, 75]))
    if whis == "range":
        low, high = float(values[0]), float(values[-1])
    elif isinstance(whis, tuple | list):
        low, high = (float(q) for q in np.percentile(values, whis))
    else:
        reach = float(whis) * (q3 - q1)
        inside = values[(values >= q1 - reach) & (values <= q3 + reach)]
        low, high = float(inside[0]), float(inside[-1])
    half_notch = NOTCH_FACTOR * (q3 - q1) / math.sqrt(n)
    return BoxStats(
        n=n,
        mean=float(values.mean()),
        sd=float(values.std(ddof=1)) if n > 1 else math.nan,
        minimum=float(values[0]),
        q1=q1,
        median=median,
        q3=q3,
        maximum=float(values[-1]),
        whisker_low=min(low, q1),
        whisker_high=max(high, q3),
        notch_low=median - half_notch,
        notch_high=median + half_notch,
        outliers=values[(values < low) | (values > high)],
    )


# -------------------------------------------------------------------- tests
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        for numerator in (
            m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)),
            -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1)),
        ):
            d = 1 + numerator * d
            d = 1 / (d if abs(d) > tiny else tiny)
            c = 1 + numerator / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1) < 1e-14:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    log_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    if x < (a + 1) / (a + b + 2):
        return math.exp(log_front) * _betacf(a, b, x) / a
    return 1 - math.exp(log_front) * _betacf(b, a, 1 - x) / b


def t_two_sided(t: float, df: float) -> float:
    """Two-sided p-value of Student's t distribution."""
    if not math.isfinite(t):
        return 0.0 if not math.isnan(t) else math.nan
    return _betainc(df / 2, 0.5, df / (df + t * t))


@dataclass(frozen=True)
class TestResult:
    statistic: float
    p: float


def welch(a: np.ndarray, b: np.ndarray) -> TestResult:
    """Welch's unequal-variance t-test (two-sided)."""
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se2 = va + vb
    if se2 == 0:
        raise DataShapeError("A t-test needs values that vary within the groups")
    t = float((a.mean() - b.mean()) / math.sqrt(se2))
    df = se2**2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    return TestResult(t, t_two_sided(t, float(df)))


def student(a: np.ndarray, b: np.ndarray) -> TestResult:
    """Student's t-test assuming equal variances (two-sided)."""
    na, nb = len(a), len(b)
    df = na + nb - 2
    pooled = ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / df
    if pooled == 0:
        raise DataShapeError("A t-test needs values that vary within the groups")
    t = float((a.mean() - b.mean()) / math.sqrt(pooled * (1 / na + 1 / nb)))
    return TestResult(t, t_two_sided(t, df))


def _ranks(values: np.ndarray) -> np.ndarray:
    """Ranks starting at 1, ties get their average rank."""
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values))
    sorted_values = values[order]
    start = 0
    for end in range(1, len(values) + 1):
        if end == len(values) or sorted_values[end] != sorted_values[start]:
            ranks[order[start:end]] = (start + end + 1) / 2
            start = end
    return ranks


def _u_counts(n1: int, n2: int) -> np.ndarray:
    """Number of arrangements giving each U (0..n1*n2) without ties."""
    # f[i][j] = distribution for sizes (i, j); U(i, j) = U(i-1, j) + j or U(i, j-1)
    table: dict[tuple[int, int], np.ndarray] = {}
    for i in range(n1 + 1):
        for j in range(n2 + 1):
            if i == 0 or j == 0:
                table[i, j] = np.ones(1)
                continue
            counts = np.zeros(i * j + 1)
            left, right = table[i - 1, j], table[i, j - 1]
            counts[j : j + len(left)] += left
            counts[: len(right)] += right
            table[i, j] = counts
    return table[n1, n2]


def mann_whitney(a: np.ndarray, b: np.ndarray) -> TestResult:
    """Two-sided Mann-Whitney U test (Wilcoxon rank-sum; R's ``wilcox.test``).

    Exact p-value when both groups have fewer than 50 values and there are no
    ties (as R does); otherwise the normal approximation with tie and
    continuity corrections. The statistic is U of ``a``.
    """
    n1, n2 = len(a), len(b)
    joined = np.concatenate([a, b])
    ranks = _ranks(joined)
    u1 = float(ranks[:n1].sum() - n1 * (n1 + 1) / 2)
    u = max(u1, n1 * n2 - u1)
    ties = len(np.unique(joined)) < len(joined)
    if n1 < EXACT_LIMIT and n2 < EXACT_LIMIT and not ties:
        counts = _u_counts(n1, n2)
        upper = counts[round(u) :].sum() / counts.sum()
        return TestResult(u1, float(min(1.0, 2 * upper)))
    n = n1 + n2
    _, tie_sizes = np.unique(joined, return_counts=True)
    tie_term = float((tie_sizes**3 - tie_sizes).sum()) / (n * (n - 1))
    sigma = math.sqrt(n1 * n2 / 12 * ((n + 1) - tie_term))
    if sigma == 0:
        return TestResult(u1, 1.0)
    z = (u - n1 * n2 / 2 - 0.5) / sigma
    return TestResult(u1, float(min(1.0, 2 * (1 - NormalDist().cdf(z)))))


TESTS = {"mann-whitney": mann_whitney, "welch": welch, "t-test": student}
TEST_NAMES = {
    "mann-whitney": "two-sided Mann-Whitney U test",
    "welch": "two-sided Welch's t-test",
    "t-test": "two-sided Student's t-test",
}


def adjust(p: Sequence[float], method: Correction | None) -> np.ndarray:
    """Adjust p-values for multiple comparisons (Holm or Bonferroni)."""
    values = np.asarray(p, dtype=float)
    if method is None or len(values) <= 1:
        return values
    m = len(values)
    if method == "bonferroni":
        return np.asarray(np.minimum(1.0, values * m), dtype=float)
    order = np.argsort(values)
    stepped = np.maximum.accumulate((m - np.arange(m)) * values[order])
    adjusted = np.empty(m)
    adjusted[order] = np.minimum(1.0, stepped)
    return adjusted
