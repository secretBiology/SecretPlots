"""Decision curve analysis (Vickers & Elkin, 2006): the net benefit of
acting on one or more risk models across threshold probabilities, against
the "treat all" and "treat none" strategies.

At threshold probability ``pt`` a patient is treated when their predicted
risk is at least ``pt``, and

    net benefit = TP / n - FP / n * pt / (1 - pt)

so a false positive costs ``pt / (1 - pt)`` true positives: the odds at which
a patient would be indifferent between treatment and none. Treating all has
net benefit ``prevalence - (1 - prevalence) * pt / (1 - pt)``; treating none,
zero. ``measure="interventions_avoided"`` shows the same comparison as net
interventions avoided per 100 patients relative to treating all,
``(NB_model - NB_all) / (pt / (1 - pt)) * 100``.

Confidence bands come from a percentile bootstrap over patients. Each
resample is a vector of case weights, so all thresholds and models of one
resample are a single matrix product.
"""

from collections.abc import Hashable, Sequence
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from SecretPlots.core.colors import combined_alpha
from SecretPlots.core.data import source_columns
from SecretPlots.core.missing import DropPolicy, handle_missing, numeric_array
from SecretPlots.core.plot import Plot
from SecretPlots.core.resolve import Style
from SecretPlots.errors import DataShapeError
from SecretPlots.plots.heatmap import _choice

Measure = Literal["net_benefit", "interventions_avoided"]

_MEASURES = ("net_benefit", "interventions_avoided")
_Y_TITLES = {
    "net_benefit": "Net benefit",
    "interventions_avoided": "Net interventions avoided per 100 patients",
}
_TREAT_ALL = "Treat all"
_TREAT_NONE = "Treat none"


def _net_benefit(
    outcome: np.ndarray,
    risks: np.ndarray,
    thresholds: np.ndarray,
    weights: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Net benefit of each model and of treating all.

    Args:
        outcome: ``(n,)`` 0/1 outcomes.
        risks: ``(n, m)`` predicted probabilities, one column per model.
        thresholds: ``(k,)`` threshold probabilities in (0, 1).
        weights: ``(b, n)`` case weights (bootstrap counts); default one
            resample with every patient once.

    Returns:
        ``(b, m, k)`` model net benefit and ``(b, k)`` treat-all net benefit.
    """
    w = np.ones((1, len(outcome))) if weights is None else weights
    total = w.sum(axis=1)[:, None]
    odds = thresholds / (1 - thresholds)
    events = w @ outcome
    prevalence = events[:, None] / total
    treat_all = prevalence - (1 - prevalence) * odds
    model = np.empty((w.shape[0], risks.shape[1], len(thresholds)))
    for j in range(risks.shape[1]):
        treated = (risks[:, j][:, None] >= thresholds[None, :]).astype(float)
        tp = (w * outcome) @ treated
        fp = (w * (1 - outcome)) @ treated
        model[:, j] = tp / total - fp / total * odds
    return model, treat_all


class DecisionCurvePlot(Plot):
    """Decision curves per model, built by :func:`decision_curve`."""

    kind = "decision"
    _constructor = "decision_curve"
    _handle_length = 1.8

    def __init__(
        self,
        outcome: np.ndarray,
        risks: np.ndarray,
        *,
        models: list[str],
        thresholds: np.ndarray,
        measure: Measure,
    ) -> None:
        super().__init__()
        self._outcome = outcome
        self._risks = risks
        self._models = models
        self._thresholds = thresholds
        self._measure: Measure = measure
        self._ci_options: dict[str, Any] | None = None
        self._show_all = True
        self._show_none = True

    # ----------------------------------------------------------------- verbs
    def ci(
        self,
        show: bool = True,
        *,
        level: float = 0.95,
        n_boot: int = 500,
        seed: int | None = 0,
        alpha: float | None = None,
    ) -> Self:
        """Percentile bootstrap confidence bands around the model curves.

        Args:
            show: ``False`` removes the bands.
            level: Confidence level, e.g. 0.95.
            n_boot: Number of bootstrap resamples of the patients.
            seed: Random seed, so the figure is reproducible; ``None`` draws a
                new one each time.
            alpha: Opacity of the bands (default: the theme's ``fill_alpha``).
        """
        if not show:
            self._ci_options = None
            return self._changed()
        if not 0 < level < 1:
            raise ValueError("ci level must be between 0 and 1, e.g. 0.95")
        if isinstance(n_boot, bool) or not isinstance(n_boot, int) or n_boot < 50:
            raise ValueError("n_boot must be an integer of at least 50")
        if alpha is not None and not 0 <= alpha <= 1:
            raise ValueError("alpha must be between 0 and 1")
        self._ci_options = {
            "level": float(level),
            "n_boot": n_boot,
            "seed": seed,
            "alpha": alpha,
        }
        return self._changed()

    def references(self, *, treat_all: bool = True, treat_none: bool = True) -> Self:
        """Show or hide the "treat all" and "treat none" strategies (both
        shown by default). With ``measure="interventions_avoided"`` treating
        all is the zero line and treating none is not drawn.

        Args:
            treat_all: Draw the treat-all curve.
            treat_none: Draw the treat-none line at zero net benefit.
        """
        self._show_all = bool(treat_all)
        self._show_none = bool(treat_none)
        return self._changed()

    # ------------------------------------------------------------ statistics
    def _curves(self) -> tuple[np.ndarray, np.ndarray]:
        """``(m, k)`` model values and ``(k,)`` treat-all values in the
        chosen measure."""
        model, treat_all = _net_benefit(self._outcome, self._risks, self._thresholds)
        values, reference = self._measured(model, treat_all)
        return values[0], reference[0]

    def _measured(
        self, model: np.ndarray, treat_all: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        if self._measure == "net_benefit":
            return model, treat_all
        odds = self._thresholds / (1 - self._thresholds)
        avoided = (model - treat_all[:, None, :]) / odds * 100
        return avoided, np.zeros_like(treat_all)

    def _intervals(self) -> tuple[np.ndarray, np.ndarray] | None:
        """``(m, k)`` lower and upper bounds, or ``None`` without ``.ci()``."""
        options = self._ci_options
        if options is None:
            return None
        rng = np.random.default_rng(options["seed"])
        n = len(self._outcome)
        draws = rng.integers(0, n, size=(options["n_boot"], n))
        weights = np.stack([np.bincount(row, minlength=n) for row in draws]).astype(
            float
        )
        model, treat_all = _net_benefit(
            self._outcome, self._risks, self._thresholds, weights
        )
        values = self._measured(model, treat_all)[0]
        tail = (1 - options["level"]) / 2 * 100
        low, high = np.percentile(values, [tail, 100 - tail], axis=0)
        return low, high

    def source_data(self) -> pd.DataFrame:
        """The plotted numbers: one row per model (and reference strategy)
        and threshold, with bootstrap bounds when ``.ci()`` is on. Generated
        columns that clash with your column names get a ``_computed``
        suffix."""
        values, treat_all = self._curves()
        bounds = self._intervals()
        k = len(self._thresholds)
        parts = []
        for j, model in enumerate(self._models):
            part: dict[str, Any] = {
                "model": np.full(k, model, dtype=object),
                "threshold": self._thresholds,
                self._measure: values[j],
            }
            if bounds is not None:
                part[f"{self._measure}_low"] = bounds[0][j]
                part[f"{self._measure}_high"] = bounds[1][j]
            parts.append(pd.DataFrame(part))
        references = [(_TREAT_ALL, treat_all)]
        if self._measure == "net_benefit":
            references.append((_TREAT_NONE, np.zeros(k)))
        for name, reference in references:
            parts.append(
                pd.DataFrame(
                    {
                        "model": np.full(k, name, dtype=object),
                        "threshold": self._thresholds,
                        self._measure: reference,
                    }
                )
            )
        table = pd.concat(parts, ignore_index=True)
        spec: list[tuple[Hashable, bool]] = [(c, False) for c in table.columns]
        return table.set_axis(source_columns(spec), axis=1)

    # ------------------------------------------------------------- rendering
    def _default_labels(self) -> dict[str, str | None]:
        return {"x": "Threshold probability", "y": _Y_TITLES[self._measure]}

    def _draw(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        colors = self._group_colors(style, self._models, grouped=True)
        width = theme.line_width or 1.5
        thin = theme.axis_line_width or 0.8
        x = self._thresholds
        values, treat_all = self._curves()
        net_benefit = self._measure == "net_benefit"

        bounds = self._intervals()
        alpha = None if self._ci_options is None else self._ci_options["alpha"]
        if alpha is None:
            alpha = 0.22 if theme.fill_alpha is None else float(theme.fill_alpha)
        # Drawn before the references so the legend lists models first.
        for j, model in enumerate(self._models):
            color = colors[model]
            ax.plot(x, values[j], color=color, lw=width, zorder=3, label=str(model))
            if bounds is not None:
                ax.fill_between(
                    x,
                    bounds[0][j],
                    bounds[1][j],
                    color=color,
                    alpha=combined_alpha(color, alpha),
                    lw=0,
                    zorder=1.6,
                )
        n = len(self._models)
        if self._show_all:
            ax.plot(
                x,
                treat_all,
                color=theme.muted_text_color or theme.text_color,
                lw=width * 0.75 if net_benefit else thin,
                zorder=2.2,
                label=_TREAT_ALL,
            )
            n += 1
        if self._show_none and net_benefit:
            ax.plot(
                x,
                np.zeros_like(x),
                color=theme.text_color,
                lw=thin,
                zorder=2,
                label=_TREAT_NONE,
            )
            n += 1

        ax.set_xlim(float(x[0]), float(x[-1]))
        if net_benefit:
            # Treating all falls steeply past the prevalence; keep the axis on
            # the range where the strategies differ.
            highest = values if bounds is None else bounds[1]
            top = max(float(np.nanmax(highest)), float(treat_all[0]), 0.0)
            top = top * 1.05 if top > 0 else 0.05
            ax.set_ylim(-0.1 * top, top)
        self._style_axes(ax, style)
        self._draw_legend(ax, style, n=n, title=None)

    def _style_axes(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        grid = theme.grid
        if grid in ("both", "value", "y"):
            ax.yaxis.grid(True)
        if grid in ("both", "category", "x"):
            ax.xaxis.grid(True)
        if theme.value_axis_side == "right":
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
        visible = set(theme.spines or ())
        for side, spine in ax.spines.items():
            spine.set_visible(side in visible)


def decision_curve(
    data: Any,
    outcome: str,
    models: str | Sequence[str],
    *,
    thresholds: Sequence[float] | np.ndarray | None = None,
    measure: Measure = "net_benefit",
    missing: DropPolicy = "raise",
) -> DecisionCurvePlot:
    """Decision curve analysis: net benefit of one or more risk models across
    threshold probabilities, with "treat all" and "treat none" for
    reference.

    Args:
        data: DataFrame (or dict of columns), one row per patient.
        outcome: Column marking the outcome (1 or True) or its absence
            (0 or False).
        models: Column, or list of columns, of predicted probabilities
            (0 to 1), one curve each. Column names become legend labels.
        thresholds: Threshold probabilities to evaluate, increasing and
            strictly between 0 and 1. Default 0.01, 0.02, ..., 0.99; limit
            them to the clinically sensible range, e.g.
            ``np.arange(0.05, 0.51, 0.01)``.
        measure: ``"net_benefit"`` (default) or ``"interventions_avoided"``
            (net interventions avoided per 100 patients, relative to treating
            all).
        missing: ``"raise"`` (default) rejects missing outcomes or
            predictions; ``"drop"`` leaves those patients out.

    Example:
        >>> sp.dca(df, outcome="cancer", models=["a", "b"]).ci()  # doctest: +SKIP
    """
    _choice(measure, _MEASURES, "measure")
    frame = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    columns = [models] if isinstance(models, str) else list(models)
    if not columns:
        raise ValueError("models needs at least one column of predicted risks")
    if len(set(columns)) != len(columns):
        raise ValueError("each model column can appear once")
    for role, column in [("outcome", outcome)] + [("model", c) for c in columns]:
        if column not in frame:
            _choice(column, [str(c) for c in frame.columns], f"{role} column")
    raw = frame[outcome]
    coded = pd.to_numeric(
        raw.map(lambda v: int(v) if isinstance(v, bool | np.bool_) else v),
        errors="coerce",
    )
    wrong = raw.notna() & ~coded.isin([0, 1])
    if wrong.any():
        raise DataShapeError(
            f"outcome column {outcome!r} must be 1/True or 0/False, got "
            f"{raw[wrong].iloc[0]!r}. Convert it first, e.g. "
            f"df[{outcome!r}] == 'yes'."
        )
    frame[outcome] = numeric_array(coded)
    for column in columns:
        frame[column] = numeric_array(frame[column])
    frame = handle_missing(frame, missing, values=[outcome, *columns])
    risks = frame[columns].to_numpy(float)
    outside = (risks < 0) | (risks > 1)
    if outside.any():
        bad = columns[int(np.argmax(outside.any(axis=0)))]
        raise DataShapeError(
            f"model column {bad!r} must hold predicted probabilities between "
            "0 and 1. Convert scores or log-odds to risks first, e.g. with a "
            "logistic regression on the outcome."
        )
    events = frame[outcome].to_numpy(float)
    if events.sum() == 0 or events.sum() == len(events):
        raise DataShapeError(
            f"outcome column {outcome!r} needs both patients with and without "
            "the outcome"
        )

    if thresholds is None:
        grid = np.round(np.arange(1, 100) / 100, 2)
    else:
        grid = np.asarray(thresholds, dtype=float).ravel()
        if grid.size < 2 or not np.isfinite(grid).all():
            raise ValueError("thresholds must be at least two finite numbers")
        if (grid <= 0).any() or (grid >= 1).any():
            raise ValueError("thresholds must be strictly between 0 and 1")
        if (np.diff(grid) <= 0).any():
            raise ValueError("thresholds must increase")

    return DecisionCurvePlot(
        events,
        risks,
        models=columns,
        thresholds=grid,
        measure=measure,
    )


dca = decision_curve
