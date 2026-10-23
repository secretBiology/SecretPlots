"""Survival statistics (numpy only, no scipy or lifelines): Kaplan-Meier and
Nelson-Aalen estimates, median survival, the log-rank family of tests and
hazard ratios between groups.

Conventions follow R's ``survival`` package, the reference most journals
expect: subjects censored at a time are still at risk at that time, the
Kaplan-Meier interval uses Greenwood's variance, Nelson-Aalen increments are
``d / n`` with Aalen's variance ``d / n**2``, and hazard ratios come from a Cox
model with the group as its only covariate and Efron's handling of ties.
Anything needing more covariates belongs in a modelling library; its numbers
can be passed to the plot as they are.
"""

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import numpy as np

from SecretPlots.errors import DataShapeError

CIMethod = Literal["log-log", "log", "plain"]
Weighting = Literal["logrank", "wilcoxon", "tarone-ware", "peto", "fleming-harrington"]


def z_value(level: float) -> float:
    """Two-sided normal quantile for a confidence level (1.96 for 0.95)."""
    return NormalDist().inv_cdf((1 + level) / 2)


def chi2_sf(x: float, df: int) -> float:
    """Upper tail of the chi-square distribution for whole-number ``df``.

    Closed forms: a Poisson sum for even ``df``; ``erfc`` plus a half-integer
    gamma series for odd ``df``. Terms are summed in log space so large
    statistics keep tiny p-values instead of rounding to 0 early.
    """
    if df < 1:
        raise ValueError("chi-square needs df >= 1")
    if not math.isfinite(x):
        return 0.0 if x > 0 else 1.0
    if x <= 0:
        return 1.0
    half = x / 2
    log_half = math.log(half)
    if df % 2 == 0:
        terms = (-half + i * log_half - math.lgamma(i + 1) for i in range(df // 2))
        return min(1.0, sum(math.exp(t) for t in terms))
    total = math.erfc(math.sqrt(half))
    for i in range(1, (df - 1) // 2 + 1):
        total += math.exp(-half + (i - 0.5) * log_half - math.lgamma(i + 0.5))
    return min(1.0, total)


# ------------------------------------------------------------ estimates
@dataclass(frozen=True)
class Curve:
    """One estimated curve at every distinct observed time (events and
    censorings), with the counts behind it."""

    time: np.ndarray
    at_risk: np.ndarray
    events: np.ndarray
    censored: np.ndarray
    estimate: np.ndarray
    lower: np.ndarray
    upper: np.ndarray


def event_table(
    time: np.ndarray, event: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Distinct times with the number at risk, events and censorings at each."""
    times, inverse = np.unique(time, return_inverse=True)
    events = np.bincount(inverse, weights=event, minlength=len(times)).astype(int)
    total = np.bincount(inverse, minlength=len(times))
    at_risk = len(time) - np.concatenate([[0], np.cumsum(total)[:-1]])
    return times, at_risk.astype(int), events, total - events


def kaplan_meier(
    time: np.ndarray,
    event: np.ndarray,
    *,
    level: float = 0.95,
    ci: CIMethod = "log-log",
) -> Curve:
    """Kaplan-Meier survival with a pointwise Greenwood confidence interval.

    ``ci`` transforms the interval: ``"log-log"`` (lifelines, SAS and Stata
    default; stays within 0..1), ``"log"`` (R's default) or ``"plain"``.
    """
    times, n, d, c = event_table(time, event)
    with np.errstate(divide="ignore", invalid="ignore"):
        surv = np.cumprod(1 - d / n)
        greenwood = np.cumsum(np.where(d > 0, d / (n * (n - d)), 0.0))
        z = z_value(level)
        if ci == "plain":
            half = z * surv * np.sqrt(greenwood)
            lower, upper = surv - half, surv + half
        elif ci == "log":
            spread = np.exp(z * np.sqrt(greenwood))
            lower, upper = surv / spread, surv * spread
        else:
            log_s = np.log(surv)
            centre = np.log(-log_s)
            half = z * np.sqrt(greenwood) / np.abs(log_s)
            lower = np.exp(-np.exp(centre + half))
            upper = np.exp(-np.exp(centre - half))
    # Before the first event the estimate is exactly 1; after the curve
    # reaches 0 it stays there. Both have no spread.
    lower = np.where(surv >= 1, 1.0, np.where(surv <= 0, 0.0, lower))
    upper = np.where(surv >= 1, 1.0, np.where(surv <= 0, 0.0, upper))
    lower, upper = np.clip(np.nan_to_num(lower), 0, 1), np.clip(upper, 0, 1)
    return Curve(times, n, d, c, surv, lower, upper)


def nelson_aalen(time: np.ndarray, event: np.ndarray, *, level: float = 0.95) -> Curve:
    """Nelson-Aalen cumulative hazard with a log-transformed interval
    (Aalen's variance, as R's ``survfit`` ``std.chaz``)."""
    times, n, d, c = event_table(time, event)
    hazard = np.cumsum(d / n)
    se = np.sqrt(np.cumsum(d / n.astype(float) ** 2))
    with np.errstate(divide="ignore", invalid="ignore"):
        spread = np.exp(z_value(level) * se / hazard)
        lower = np.where(hazard > 0, hazard / spread, 0.0)
        upper = np.where(hazard > 0, hazard * spread, 0.0)
    return Curve(times, n, d, c, hazard, lower, upper)


def survival_quantile(curve: Curve, q: float = 0.5) -> tuple[float, float, float]:
    """Time at which survival first falls to ``q`` (the median for 0.5),
    with the interval from where the confidence limits cross ``q``.

    As in R: if the curve sits exactly at ``q`` over an interval, the
    midpoint of that interval is reported. NaN where a curve never gets there.
    """

    def crossing(values: np.ndarray, exact: bool) -> float:
        below = np.flatnonzero(values <= q + 1e-12)
        if not len(below):
            return math.nan
        i = below[0]
        if exact and abs(values[i] - q) < 1e-12:
            later = np.flatnonzero(values < q - 1e-12)
            if len(later):
                return float((curve.time[i] + curve.time[later[0]]) / 2)
        return float(curve.time[i])

    return (
        crossing(curve.estimate, exact=True),
        crossing(curve.lower, exact=False),
        crossing(curve.upper, exact=False),
    )


def counts_at(
    time: np.ndarray, event: np.ndarray, at: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Number at risk at each time in ``at``, and events and censorings up to
    and including it (the rows of a risk table)."""
    ordered = np.sort(time)
    dead = np.sort(time[event == 1])
    lost = np.sort(time[event == 0])
    at_risk = len(time) - np.searchsorted(ordered, at, side="left")
    events = np.searchsorted(dead, at, side="right")
    censored = np.searchsorted(lost, at, side="right")
    return at_risk, events, censored


# ------------------------------------------------------- group comparisons
def _risk_sets(
    time: np.ndarray, event: np.ndarray, group: np.ndarray, k: int
) -> tuple[np.ndarray, np.ndarray]:
    """At distinct event times: number at risk (rows) per group (columns),
    and the number of events per group."""
    event_times = np.unique(time[event == 1])
    at_risk = np.empty((len(event_times), k))
    deaths = np.zeros((len(event_times), k))
    for g in range(k):
        mine = group == g
        ordered = np.sort(time[mine])
        at_risk[:, g] = len(ordered) - np.searchsorted(ordered, event_times, "left")
        dead = time[mine & (event == 1)]
        idx = np.searchsorted(event_times, dead)
        np.add.at(deaths[:, g], idx, 1)
    return at_risk, deaths


def _weights(
    at_risk: np.ndarray,
    deaths: np.ndarray,
    weighting: Weighting,
    rho: float,
    gamma: float,
) -> np.ndarray:
    n, d = at_risk.sum(axis=1), deaths.sum(axis=1)
    if weighting == "logrank":
        return np.ones_like(n)
    if weighting == "wilcoxon":
        return n
    if weighting == "tarone-ware":
        return np.sqrt(n)
    if weighting == "peto":
        # Peto-Peto's modified survival estimate, up to and including t.
        return np.asarray(np.cumprod(1 - d / (n + 1)), dtype=float)
    # Fleming-Harrington G(rho, gamma): the pooled Kaplan-Meier just before t.
    surv = np.cumprod(1 - d / n)
    before = np.concatenate([[1.0], surv[:-1]])
    return np.asarray(before**rho * (1 - before) ** gamma, dtype=float)


def _score(
    time: np.ndarray,
    event: np.ndarray,
    group: np.ndarray,
    strata: np.ndarray,
    k: int,
    weighting: Weighting,
    rho: float,
    gamma: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Observed minus expected events per group and their covariance,
    summed over strata (weights are computed within each stratum)."""
    u = np.zeros(k)
    v = np.zeros((k, k))
    for s in np.unique(strata):
        mine = strata == s
        at_risk, deaths = _risk_sets(time[mine], event[mine], group[mine], k)
        if not len(at_risk):
            continue
        w = _weights(at_risk, deaths, weighting, rho, gamma)
        n, d = at_risk.sum(axis=1), deaths.sum(axis=1)
        share = at_risk / n[:, None]
        u += (w[:, None] * (deaths - d[:, None] * share)).sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            spread = np.where(n > 1, d * (n - d) / (n - 1), 0.0)
        scale = w**2 * spread
        v += np.einsum("t,tk->k", scale, share) * np.eye(k) - np.einsum(
            "t,tk,tl->kl", scale, share, share
        )
    return u, v


@dataclass(frozen=True)
class TestResult:
    statistic: float
    df: int
    p: float


def logrank(
    time: np.ndarray,
    event: np.ndarray,
    group: np.ndarray,
    *,
    strata: np.ndarray | None = None,
    weighting: Weighting = "logrank",
    rho: float = 0.0,
    gamma: float = 1.0,
    scores: np.ndarray | None = None,
) -> TestResult:
    """Log-rank test of k groups (codes ``0..k-1``), optionally weighted,
    stratified, or as a test for trend across ordered ``scores``.

    Without scores: chi-square with k - 1 degrees of freedom. With scores:
    the one-degree-of-freedom trend statistic ``(c'U)^2 / c'Vc``.
    """
    k = int(group.max()) + 1
    if strata is None:
        strata = np.zeros(len(time), dtype=int)
    u, v = _score(time, event, group, strata, k, weighting, rho, gamma)
    if scores is not None:
        denominator = float(scores @ v @ scores)
        if denominator <= 0:
            raise DataShapeError("The trend test needs events in at least two groups")
        stat = float(scores @ u) ** 2 / denominator
        return TestResult(stat, 1, chi2_sf(stat, 1))
    reduced = v[:-1, :-1]
    if np.allclose(reduced, 0):
        raise DataShapeError("A log-rank test needs events in the compared groups")
    stat = float(u[:-1] @ np.linalg.pinv(reduced) @ u[:-1])
    return TestResult(stat, k - 1, chi2_sf(stat, k - 1))


@dataclass(frozen=True)
class HazardRatio:
    """Hazard ratio of each group against the reference (Wald interval)."""

    ratio: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    p: np.ndarray


def cox_groups(
    time: np.ndarray,
    event: np.ndarray,
    group: np.ndarray,
    *,
    ref: int = 0,
    strata: np.ndarray | None = None,
    level: float = 0.95,
) -> HazardRatio:
    """Cox proportional-hazards model with the group as the only covariate
    (one indicator per non-reference group), Efron ties, optional strata.

    Returns one row per group in code order; the reference row is 1 with no
    interval. Matches R's ``coxph(Surv(time, event) ~ group)``.
    """
    k = int(group.max()) + 1
    others = [g for g in range(k) if g != ref]
    if strata is None:
        strata = np.zeros(len(time), dtype=int)
    terms: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    observed = np.zeros(k)
    for s in np.unique(strata):
        mine = strata == s
        at_risk, deaths = _risk_sets(time[mine], event[mine], group[mine], k)
        if not len(at_risk):
            continue
        # One row per (event time, l) term of Efron's approximation: the
        # l-th of d tied deaths sees the risk set minus l/d of those dying.
        tied = deaths.sum(axis=1).astype(int)
        rows = np.repeat(np.arange(len(tied)), tied)
        steps = np.arange(len(rows)) - np.repeat(np.cumsum(tied) - tied, tied)
        terms.append((at_risk[rows], deaths[rows], steps / tied[rows]))
        observed += deaths.sum(axis=0)
    empty = [g for g in range(k) if observed[g] == 0]
    if empty:
        raise DataShapeError(
            f"no events in group {empty[0]}: its hazard ratio is undefined"
        )

    def evaluate(beta: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
        theta = np.ones(k)
        theta[others] = np.exp(beta)
        loglik = float(observed[others] @ beta)
        grad = observed[others].astype(float).copy()
        info = np.zeros((len(others), len(others)))
        for at_risk, deaths, fraction in terms:
            risk = at_risk * theta
            dead = deaths * theta
            phi = risk - fraction[:, None] * dead
            total = phi.sum(axis=1)
            a = phi[:, others] / total[:, None]
            loglik -= float(np.log(total).sum())
            grad -= a.sum(axis=0)
            info += np.diag(a.sum(axis=0)) - a.T @ a
        return loglik, grad, info

    beta = np.zeros(len(others))
    loglik, grad, info = evaluate(beta)
    for _ in range(60):
        try:
            step = np.linalg.solve(info, grad)
        except np.linalg.LinAlgError:
            raise DataShapeError("The hazard-ratio model cannot be fitted") from None
        candidate = beta + step
        new = evaluate(candidate)
        while new[0] < loglik - 1e-12 and np.abs(step).max() > 1e-12:
            step /= 2
            candidate = beta + step
            new = evaluate(candidate)
        beta, (loglik, grad, info) = candidate, new
        if np.abs(step).max() < 1e-10:
            break
    else:
        raise DataShapeError("The hazard-ratio model did not converge")
    if np.abs(beta).max() > 20:
        raise DataShapeError(
            "A hazard ratio is unbounded (a group has events only before or "
            "after all others); report it from a modelling library instead"
        )
    se = np.sqrt(np.diag(np.linalg.inv(info)))
    z = z_value(level)
    ratio, lower, upper, p = (
        np.ones(k),
        np.full(k, np.nan),
        np.full(k, np.nan),
        np.full(k, np.nan),
    )
    ratio[others] = np.exp(beta)
    lower[others] = np.exp(beta - z * se)
    upper[others] = np.exp(beta + z * se)
    p[others] = [
        math.erfc(abs(b / s) / math.sqrt(2)) for b, s in zip(beta, se, strict=True)
    ]
    return HazardRatio(ratio, lower, upper, p)
