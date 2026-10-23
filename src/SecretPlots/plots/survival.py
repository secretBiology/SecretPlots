"""Survival curves: Kaplan-Meier (or 1 - KM, or the Nelson-Aalen cumulative
hazard) per group, with confidence bands, censoring ticks, a number-at-risk
table below the axes, and p-values and hazard ratios written on the plot.

Estimates and the log-rank family of tests are computed here (see
``core/survival.py``); hazard ratios too, from a Cox model with the group as
its only covariate. Anything that needs a fuller model (adjusted hazard
ratios, interaction p-values) is passed in as numbers and written in the
same style.

The risk table is text in the axes: x in data coordinates, so columns sit
under their ticks; y a fixed physical distance (inches) below the x-axis
decorations, so constrained layout makes room for it and the rows keep their
spacing when the figure is resized.
"""

import math
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import combinations, pairwise
from typing import Any, Literal, Self

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import (
    ScaledTranslation,
    Transform,
    blended_transform_factory,
)

from SecretPlots.core import survival as sv
from SecretPlots.core.colors import combined_alpha
from SecretPlots.core.data import _order, source_columns
from SecretPlots.core.missing import DropPolicy, handle_missing, numeric_array
from SecretPlots.core.plot import Plot, _legend_title, _root_figure
from SecretPlots.core.resolve import Style
from SecretPlots.core.stats import Correction, adjust
from SecretPlots.errors import DataShapeError
from SecretPlots.plots.distribution import p_label
from SecretPlots.plots.forest import _DASH, _number, _text_size
from SecretPlots.plots.heatmap import _choice

Kind = Literal["survival", "failure", "cumhaz"]
TestName = Literal["logrank", "wilcoxon", "tarone-ware", "peto", "fleming-harrington"]
RiskRow = Literal["at_risk", "events", "censored"]
Location = Literal["auto", "lower left", "lower right", "upper left", "upper right"]
#: An estimate with its interval, ``(hr, lower, upper)``, or the estimate alone.
Ratio = float | tuple[float, float, float]

_PT = 72.0
_KINDS = ("survival", "failure", "cumhaz")
_TESTS = ("logrank", "wilcoxon", "tarone-ware", "peto", "fleming-harrington")
_CI_METHODS = ("log-log", "log", "plain")
_ROWS = ("at_risk", "events", "censored")
_LOCATIONS = ("auto", "lower left", "lower right", "upper left", "upper right")
_Y_TITLES = {
    "survival": "Survival probability",
    "failure": "Cumulative incidence",
    "cumhaz": "Cumulative hazard",
}
_ROW_TITLES = {
    "at_risk": "Number at risk",
    "events": "Cumulative events",
    "censored": "Cumulative censored",
}
_TEST_TITLES = {
    "logrank": "Log-rank",
    "wilcoxon": "Gehan-Breslow-Wilcoxon",
    "tarone-ware": "Tarone-Ware",
    "peto": "Peto-Peto",
    "fleming-harrington": "Fleming-Harrington",
}
#: Line spacing of risk-table rows, in font sizes.
_ROW_SPACING = 1.35


@dataclass(frozen=True)
class _Note:
    """One request for text in the statistics box: a test to run, numbers
    given by the user, or free text."""

    kind: Literal["pvalue", "hr", "text"]
    options: dict[str, Any]


@dataclass
class _TableArtists:
    """Risk-table texts as ``(text, base transform, x shift in inches, line)``,
    moved together once the height of the x-axis decorations is known."""

    texts: list[tuple[Text, Transform, float, int]] = field(default_factory=list)
    offset: float = 0.0


def _p_text(label: str, p: float) -> str:
    """``"Log-rank p = 0.012"`` / ``"P for interaction < 0.001"``."""
    return label + p_label(p, "p")[1:]


def _ratio_text(label: str, ratio: Ratio, level: float, decimals: int) -> str:
    if isinstance(ratio, tuple):
        hr, low, high = ratio
        return (
            f"{label} {_number(hr, decimals)} ({level * 100:g}% CI "
            f"{_number(low, decimals)}{_DASH}{_number(high, decimals)})"
        )
    return f"{label} {_number(ratio, decimals)}"


def _check_ratio(value: Any) -> Ratio:
    if isinstance(value, int | float) and not isinstance(value, bool):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"hazard ratio {value!r} must be a positive number")
        return float(value)
    if isinstance(value, Sequence) and not isinstance(value, str) and len(value) == 3:
        hr, low, high = (float(v) for v in value)
        if not all(math.isfinite(v) and v > 0 for v in (hr, low, high)):
            raise ValueError(f"hazard ratio {value!r} must be positive numbers")
        if not low <= hr <= high:
            raise ValueError(f"hazard ratio {value!r} must be (hr, lower, upper)")
        return (hr, low, high)
    raise TypeError(
        f"hazard ratio {value!r} must be a number or an (hr, lower, upper) tuple"
    )


class SurvivalPlot(Plot):
    """Survival curves per group, built by :func:`survival`."""

    kind = "survival"
    _handle_length = 1.8

    def __init__(
        self,
        frame: pd.DataFrame,
        *,
        names: dict[str, str | None],
        kind: Kind,
        hues: list[Any],
    ) -> None:
        super().__init__()
        self._frame = frame
        self._names = names
        self._kind: Kind = kind
        # Colors follow the full order (so they match other plots sharing it);
        # curves, tables and tests use only the groups that have data.
        self._color_order = hues
        present = set(frame["_h"])
        self._hues = [h for h in hues if h in present]
        self._ci_options: dict[str, Any] = {
            "show": True,
            "level": 0.95,
            "method": "log-log",
            "alpha": None,
        }
        self._censor_options: dict[str, Any] = {
            "show": True,
            "marker": "|",
            "size": None,
        }
        self._table: dict[str, Any] | None = None
        self._median: dict[str, Any] | None = None
        self._notes: list[_Note] = []
        self._loc: Location = "auto"
        self._body = _TableArtists()

    # ----------------------------------------------------------------- verbs
    def ci(
        self,
        show: bool = True,
        *,
        level: float = 0.95,
        method: sv.CIMethod = "log-log",
        alpha: float | None = None,
    ) -> Self:
        """Confidence bands around the curves (shown by default).

        Args:
            show: ``False`` hides the bands.
            level: Confidence level, e.g. 0.95. Also used for median and
                hazard-ratio intervals.
            method: Transformation of the Kaplan-Meier interval:
                ``"log-log"`` (default; lifelines, SAS and Stata), ``"log"``
                (R's default) or ``"plain"``. The cumulative hazard always
                uses a log-transformed interval.
            alpha: Opacity of the bands (default: the theme's ``fill_alpha``).
        """
        if not 0 < level < 1:
            raise ValueError("ci level must be between 0 and 1, e.g. 0.95")
        _choice(method, _CI_METHODS, "method")
        if alpha is not None and not 0 <= alpha <= 1:
            raise ValueError("alpha must be between 0 and 1")
        self._ci_options = {
            "show": bool(show),
            "level": float(level),
            "method": method,
            "alpha": alpha,
        }
        return self._changed()

    def censors(
        self, show: bool = True, *, marker: str = "|", size: float | None = None
    ) -> Self:
        """Tick marks where subjects were censored (shown by default).

        Args:
            show: ``False`` hides them.
            marker: Matplotlib marker, e.g. ``"|"`` (default) or ``"+"``.
            size: Marker size in pt (default: from the font size).
        """
        if size is not None and size <= 0:
            raise ValueError("censor marker size must be positive")
        Line2D([], [], marker=marker)  # validates the marker
        self._censor_options = {"show": bool(show), "marker": marker, "size": size}
        return self._changed()

    def risk_table(
        self,
        *rows: RiskRow,
        times: Sequence[float] | None = None,
        show: bool = True,
    ) -> Self:
        """Table of numbers at risk below the plot, one line per group,
        aligned with the time ticks.

        Args:
            *rows: Which blocks to show, in order: ``"at_risk"`` (default),
                ``"events"`` (cumulative events) and ``"censored"``
                (cumulative censorings).
            times: Times of the columns; they also become the x ticks.
                Default: the x ticks.
            show: ``False`` removes the table.
        """
        for row in rows:
            _choice(row, _ROWS, "risk table row")
        if len(set(rows)) != len(rows):
            raise ValueError("each risk table row can appear once")
        if times is not None:
            values = [float(t) for t in times]
            if not values or any(not math.isfinite(t) or t < 0 for t in values):
                raise ValueError("risk table times must be numbers >= 0")
            if any(b <= a for a, b in pairwise(values)):
                raise ValueError("risk table times must increase")
            times = values
        self._table = (
            {"rows": list(rows) or ["at_risk"], "times": times} if show else None
        )
        return self._changed()

    def median(self, show: bool = True, *, label: bool = False) -> Self:
        """Dotted guide lines at the median survival time of each group.

        Args:
            show: ``False`` removes them.
            label: Write each median time on the x axis side of its line.
        """
        if show and self._kind == "cumhaz":
            raise DataShapeError("median lines need kind='survival' or kind='failure'")
        self._median = {"label": bool(label)} if show else None
        return self._changed()

    def pvalue(
        self,
        value: float | bool | None = None,
        *,
        test: TestName = "logrank",
        rho: float = 0.0,
        gamma: float = 1.0,
        trend: bool | Sequence[float] = False,
        pairwise: bool = False,
        correction: Correction | None = None,
        label: str | None = None,
    ) -> Self:
        """Write a p-value on the plot: computed between the ``hue`` groups,
        or your own (e.g. a P for interaction from a Cox model). Each call
        adds a line; ``.pvalue(False)`` removes them all.

        With ``strata=`` in :func:`survival`, computed tests are stratified.

        Args:
            value: Your own p-value; no test is run. ``False`` removes the
                p-values.
            test: ``"logrank"`` (default), ``"wilcoxon"`` (Gehan-Breslow;
                weights early differences), ``"tarone-ware"``, ``"peto"``
                (Peto-Peto) or ``"fleming-harrington"`` (see ``rho``, ``gamma``).
            rho: Fleming-Harrington weight S(t)^rho (1 - S(t))^gamma; rho > 0
                weights early differences.
            gamma: Fleming-Harrington gamma; gamma > 0 (default 1) weights late
                differences, as in delayed treatment effects.
            trend: ``True`` tests for a trend across the groups in their
                order (scores 1, 2, 3...); a list gives the scores.
            pairwise: One p-value per pair of groups instead of one overall.
            correction: With ``pairwise``: ``"holm"`` or ``"bonferroni"``.
            label: Text before the value; default from the test (e.g.
                ``"Log-rank p"``), or ``"p"`` for your own value.
        """
        if value is False:
            self._notes = [n for n in self._notes if n.kind != "pvalue"]
            return self._changed()
        if value is not None and value is not True:
            if not isinstance(value, int | float) or not 0 <= value <= 1:
                raise ValueError("p-value must be a number between 0 and 1")
            self._notes.append(
                _Note("pvalue", {"value": float(value), "label": label or "p"})
            )
            return self._changed()
        _choice(test, _TESTS, "test")
        if correction is not None:
            _choice(correction, ("holm", "bonferroni"), "correction")
            if not pairwise:
                raise ValueError("correction applies to pairwise=True")
        if rho < 0 or gamma < 0:
            raise ValueError("rho and gamma must be 0 or more")
        if trend is not False and pairwise:
            raise ValueError("choose either trend or pairwise")
        if self._names["hue"] is None or len(self._hues) < 2:
            raise DataShapeError("A test compares groups: pass hue= to sp.survival()")
        scores = None
        if trend is not False:
            scores = (
                [float(i + 1) for i in range(len(self._hues))]
                if trend is True
                else [float(s) for s in trend]
            )
            if len(scores) != len(self._hues):
                raise ValueError(
                    f"trend needs one score per group ({len(self._hues)}), "
                    f"got {len(scores)}"
                )
        options = {
            "test": test,
            "rho": float(rho),
            "gamma": float(gamma),
            "scores": scores,
            "pairwise": pairwise,
            "correction": correction,
            "label": label,
        }
        self._notes.append(_Note("pvalue", options))
        self._test_result(options)  # fail now on data the test cannot use
        return self._changed()

    def hazard_ratio(
        self,
        values: Ratio | Mapping[Any, Ratio] | bool | None = None,
        *,
        ref: Any = None,
        label: str = "HR",
        decimals: int = 2,
    ) -> Self:
        """Write hazard ratios on the plot: computed from a Cox model with
        the ``hue`` group as its only covariate (stratified by ``strata=``),
        or your own (e.g. adjusted ones from a fuller model).
        ``.hazard_ratio(False)`` removes them.

        Args:
            values: Your own ``(hr, lower, upper)`` (or just the hr) for two
                groups, or ``{group: (hr, lower, upper)}`` against ``ref``.
                Default: compute them. ``False`` removes the hazard ratios.
            ref: The reference group (default: the first group).
            label: Text before each ratio, e.g. ``"Adjusted HR"``.
            decimals: Digits after the decimal point.
        """
        if values is False:
            self._notes = [n for n in self._notes if n.kind != "hr"]
            return self._changed()
        if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
            raise ValueError("decimals must be a non-negative integer")
        grouped = self._names["hue"] is not None
        if ref is not None and (not grouped or ref not in self._hues):
            raise DataShapeError(
                f"ref {ref!r} is not a group. Groups: "
                + ", ".join(map(str, self._hues))
            )
        given: dict[Any, Ratio] | None = None
        if values is None or values is True:
            if not grouped or len(self._hues) < 2:
                raise DataShapeError(
                    "Hazard ratios compare groups: pass hue= to sp.survival()"
                )
        elif isinstance(values, Mapping):
            unknown = [g for g in values if g not in self._hues]
            if not grouped or unknown:
                raise DataShapeError(
                    f"{unknown[0] if unknown else next(iter(values))!r} is not a "
                    "group. Groups: " + ", ".join(map(str, self._hues))
                )
            given = {g: _check_ratio(v) for g, v in values.items()}
        else:
            if grouped and len(self._hues) > 2:
                raise ValueError(
                    "With more than two groups, give {group: (hr, lower, upper)}"
                )
            given = {None: _check_ratio(values)}
        options = {"values": given, "ref": ref, "label": label, "decimals": decimals}
        self._notes.append(_Note("hr", options))
        if given is None:
            self._hazard_ratios(ref)
        return self._changed()

    def annotate(self, *lines: str, loc: Location | None = None) -> Self:
        """Add your own lines to the statistics box (p-values, hazard ratios),
        and/or move the box.

        Args:
            *lines: Text lines, e.g. ``"Median follow-up 24 months"``.
            loc: ``"auto"`` (lower left for survival, upper left otherwise),
                ``"lower left"``, ``"lower right"``, ``"upper left"`` or
                ``"upper right"``.
        """
        if loc is not None:
            _choice(loc, _LOCATIONS, "loc")
            self._loc = loc
        for line in lines:
            self._notes.append(_Note("text", {"text": str(line)}))
        return self._changed()

    # ------------------------------------------------------------ statistics
    def _arrays(
        self, frame: pd.DataFrame | None = None
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
        frame = self._frame if frame is None else frame
        codes = np.array([self._hues.index(h) for h in frame["_h"]], dtype=int)
        strata = (
            pd.factorize(frame["_s"])[0] if self._names["strata"] is not None else None
        )
        return (
            frame["_t"].to_numpy(float),
            frame["_e"].to_numpy(int),
            codes,
            strata,
        )

    def _test_result(
        self, options: Mapping[str, Any]
    ) -> list[tuple[str, sv.TestResult, float]]:
        """``(comparison, result, p to print)`` for one computed test."""
        time, event, group, strata = self._arrays()
        kwargs: dict[str, Any] = {
            "strata": strata,
            "weighting": options["test"],
            "rho": options["rho"],
            "gamma": options["gamma"],
        }
        if not options["pairwise"]:
            scores = options["scores"]
            result = sv.logrank(
                time,
                event,
                group,
                scores=None if scores is None else np.asarray(scores),
                **kwargs,
            )
            return [("overall", result, result.p)]
        results = []
        for a, b in combinations(range(len(self._hues)), 2):
            mine = (group == a) | (group == b)
            result = sv.logrank(
                time[mine],
                event[mine],
                (group[mine] == b).astype(int),
                **{**kwargs, "strata": None if strata is None else strata[mine]},
            )
            results.append((f"{self._hues[a]} vs {self._hues[b]}", result))
        adjusted = adjust([r.p for _, r in results], options["correction"])
        return [
            (name, result, float(p))
            for (name, result), p in zip(results, adjusted, strict=True)
        ]

    def _test_title(self, options: Mapping[str, Any]) -> str:
        test = options["test"]
        title = _TEST_TITLES[test]
        if self._names["strata"] is not None:
            title = "Stratified " + ("log-rank" if test == "logrank" else title)
        if test == "fleming-harrington":
            title += f" ({options['rho']:g}, {options['gamma']:g})"
        if options["scores"] is not None:
            title += " test for trend"
        return title

    def _hazard_ratios(self, ref: Any) -> sv.HazardRatio:
        time, event, group, strata = self._arrays()
        code = 0 if ref is None else self._hues.index(ref)
        try:
            return sv.cox_groups(
                time,
                event,
                group,
                ref=code,
                strata=strata,
                level=self._ci_options["level"],
            )
        except DataShapeError as error:
            # Name the group instead of its code.
            message = str(error)
            for i, name in enumerate(self._hues):
                message = message.replace(f"group {i}:", f"group {name!r}:")
            raise DataShapeError(message) from None

    def _note_lines(self) -> list[str]:
        lines: list[str] = []
        level = self._ci_options["level"]
        for note in self._notes:
            options = note.options
            if note.kind == "text":
                lines.append(options["text"])
            elif note.kind == "pvalue" and "value" in options:
                lines.append(_p_text(options["label"], options["value"]))
            elif note.kind == "pvalue":
                title = self._test_title(options)
                results = self._test_result(options)
                if not options["pairwise"]:
                    lines.append(
                        _p_text(options["label"] or f"{title} p", results[0][2])
                    )
                    continue
                correction = options["correction"]
                lines.append(
                    (options["label"] or title)
                    + (f" ({correction.capitalize()}-adjusted)" if correction else "")
                )
                lines += [_p_text(f"{name}: p", p) for name, _, p in results]
            else:
                lines += self._ratio_lines(options, level)
        return lines

    def _ratio_lines(self, options: Mapping[str, Any], level: float) -> list[str]:
        label, decimals, given = (
            options["label"],
            options["decimals"],
            options["values"],
        )
        grouped = self._names["hue"] is not None
        ref = options["ref"]
        if given is None:
            hr = self._hazard_ratios(ref)
            ref = self._hues[0] if ref is None else ref
            given = {
                g: (float(hr.ratio[i]), float(hr.lower[i]), float(hr.upper[i]))
                for i, g in enumerate(self._hues)
                if g != ref
            }
        elif None in given:
            # One ratio for two groups: the second against the first, unless
            # ref says otherwise.
            if not grouped:
                return [_ratio_text(label, given[None], level, decimals)]
            ref = self._hues[0] if ref is None else ref
            other = next(g for g in self._hues if g != ref)
            given = {other: given[None]}
        elif ref is None:
            ref = next(g for g in self._hues if g not in given)
        return [
            f"{g} vs {ref}: " + _ratio_text(label, value, level, decimals)
            for g, value in given.items()
        ]

    def _curve(self, frame: pd.DataFrame) -> sv.Curve:
        time = frame["_t"].to_numpy(float)
        event = frame["_e"].to_numpy(int)
        level = self._ci_options["level"]
        if self._kind == "cumhaz":
            return sv.nelson_aalen(time, event, level=level)
        curve = sv.kaplan_meier(time, event, level=level, ci=self._ci_options["method"])
        if self._kind == "failure":
            curve = replace(
                curve,
                estimate=1 - curve.estimate,
                lower=1 - curve.upper,
                upper=1 - curve.lower,
            )
        return curve

    def _groups(self) -> list[tuple[Any, pd.DataFrame]]:
        """Groups with data, in order; levels of hue_order without data are
        left out."""
        frame = self._frame
        labels = frame["_h"].to_numpy(object)
        groups = [(h, frame.loc[[v == h for v in labels]]) for h in self._hues]
        return [(h, rows) for h, rows in groups if len(rows)]

    def source_data(self) -> pd.DataFrame:
        """The plotted numbers: one row per distinct time of each group, with
        the counts behind the estimate (for a journal's source-data file).
        Generated columns that clash with your column names get a
        ``_computed`` suffix."""
        column = self._kind
        hue = self._names["hue"]
        spec: list[tuple[Hashable, bool]] = [
            (self._names["time"] or "time", self._names["time"] is not None),
            ("at_risk", False),
            ("events", False),
            ("censored", False),
            (column, False),
            (f"{column}_low", False),
            (f"{column}_high", False),
        ]
        if hue is not None:
            spec.insert(0, (hue, True))
        parts = []
        for group, frame in self._groups():
            curve = self._curve(frame)
            columns: list[Any] = [
                curve.time,
                curve.at_risk,
                curve.events,
                curve.censored,
                curve.estimate,
                curve.lower,
                curve.upper,
            ]
            if hue is not None:
                columns.insert(0, np.full(len(curve.time), group, dtype=object))
            parts.append(pd.DataFrame(dict(enumerate(columns))))
        table = pd.concat(parts, ignore_index=True)
        return table.set_axis(source_columns(spec), axis=1)

    def statistics(self) -> pd.DataFrame:
        """Per group: subjects, events, censorings and median survival with
        its confidence interval (NaN where the curve never reaches 0.5)."""
        rows = []
        level = self._ci_options["level"]
        for group, frame in self._groups():
            time = frame["_t"].to_numpy(float)
            event = frame["_e"].to_numpy(int)
            curve = sv.kaplan_meier(
                time, event, level=level, ci=self._ci_options["method"]
            )
            median, low, high = sv.survival_quantile(curve)
            rows.append(
                {
                    "group": group,
                    "n": len(time),
                    "events": int(event.sum()),
                    "censored": int(len(event) - event.sum()),
                    "median": median,
                    "median_low": low,
                    "median_high": high,
                }
            )
        out = pd.DataFrame(rows)
        if self._names["hue"] is None:
            return out.drop(columns="group")
        return out.rename(columns={"group": self._names["hue"]}).set_index(
            self._names["hue"]
        )

    def test_results(self) -> pd.DataFrame:
        """The tests behind computed p-values (and hazard ratios), one row
        per comparison."""
        rows: list[dict[str, Any]] = []
        for note in self._notes:
            options = note.options
            if note.kind == "pvalue" and "value" not in options:
                title = self._test_title(options)
                for name, result, p in self._test_result(options):
                    rows.append(
                        {
                            "test": title,
                            "comparison": name,
                            "statistic": result.statistic,
                            "df": result.df,
                            "p": p,
                        }
                    )
            elif note.kind == "hr" and options["values"] is None:
                ref = options["ref"]
                hr = self._hazard_ratios(ref)
                ref = self._hues[0] if ref is None else ref
                for i, group in enumerate(self._hues):
                    if group == ref:
                        continue
                    rows.append(
                        {
                            "test": "Cox model (Wald)",
                            "comparison": f"{group} vs {ref}",
                            "hr": hr.ratio[i],
                            "hr_low": hr.lower[i],
                            "hr_high": hr.upper[i],
                            "p": hr.p[i],
                        }
                    )
        columns = [
            "test",
            "comparison",
            "statistic",
            "df",
            "hr",
            "hr_low",
            "hr_high",
            "p",
        ]
        return pd.DataFrame(rows, columns=columns).dropna(axis=1, how="all")

    # ------------------------------------------------------------- rendering
    def style(self) -> Style:
        """The resolved style; without an explicit height the figure grows
        by the risk table's height."""
        style = super().style()
        if self._height is not None or self._table is None:
            return style
        height = style.height + self._table_height(style) + self._decor_height(style)
        limit = style.target.max_height
        adjustments = style.adjustments
        if limit is not None and height > limit:
            adjustments += (
                f"height {height:.2f} in with the risk table reduced to "
                f"{style.preset.name} maximum {limit:.2f} in",
            )
            height = limit
        return replace(style, height=height, adjustments=adjustments)

    def _line_height(self, style: Style) -> float:
        return style.sizes.tick * _ROW_SPACING / _PT

    def _table_lines(self) -> int:
        if self._table is None:
            return 0
        return len(self._table["rows"]) * (len(self._hues) + 1)

    def _table_height(self, style: Style) -> float:
        gap = style.sizes.tick * 0.8 / _PT
        return self._table_lines() * self._line_height(style) + gap

    def _decor_height(self, style: Style) -> float:
        """Rough height of the x ticks, tick labels and title below the axes
        (measured and corrected after the first layout)."""
        theme = style.theme
        pt = (theme.tick_length or 3.5) + 3.5 + style.sizes.tick * 1.2
        if theme.axis_titles or self._labels.get("x"):
            pt += 4 + style.sizes.label * 1.2
        return pt / _PT

    def _default_labels(self) -> dict[str, str | None]:
        return {"x": _legend_title(self._names["time"]), "y": _Y_TITLES[self._kind]}

    def _ticks(self, style: Style, x_max: float) -> list[float]:
        if self._table is not None and self._table["times"] is not None:
            return list(self._table["times"])
        nbins = max(3, min(10, int(style.width * 1.6)))
        locator = MaxNLocator(nbins=nbins, steps=[1, 2, 2.5, 3, 5, 6, 10])
        return [float(t) for t in locator.tick_values(0, x_max) if t >= 0]

    def _draw(self, ax: Axes, style: Style) -> None:
        theme = style.theme
        grouped = self._names["hue"] is not None
        colors = self._group_colors(style, self._color_order, grouped=grouped)
        if not grouped:
            colors = {self._hues[0]: colors[None]}
        width = theme.line_width or 1.5
        alpha = self._ci_options["alpha"]
        if alpha is None:
            alpha = 0.22 if theme.fill_alpha is None else float(theme.fill_alpha)
        start = 1.0 if self._kind == "survival" else 0.0
        clip = "x" in self._limits
        curves: dict[Any, sv.Curve] = {}

        for group, frame in self._groups():
            curve = curves[group] = self._curve(frame)
            color = colors[group]
            x = np.concatenate([[0.0], curve.time])
            y = np.concatenate([[start], curve.estimate])
            ax.step(
                x,
                y,
                where="post",
                color=color,
                lw=width,
                zorder=3,
                solid_joinstyle="miter",
                clip_on=clip,
            )
            if self._ci_options["show"]:
                band = ax.fill_between(
                    x,
                    np.concatenate([[start], curve.lower]),
                    np.concatenate([[start], curve.upper]),
                    step="post",
                    color=color,
                    alpha=combined_alpha(color, alpha),
                    lw=0,
                    zorder=1.6,
                    clip_on=clip,
                )
                band.sticky_edges.y.append(0.0)
            lost = curve.censored > 0
            # An empty unclipped line would count as a point at the figure's
            # origin in constrained layout.
            if self._censor_options["show"] and lost.any():
                ax.plot(
                    curve.time[lost],
                    curve.estimate[lost],
                    ls="none",
                    marker=self._censor_options["marker"],
                    markersize=self._censor_options["size"] or style.sizes.tick * 0.7,
                    markeredgewidth=max(width * 0.7, 0.5),
                    color=color,
                    zorder=3.5,
                    clip_on=clip,
                )

        x_max = max(float(c.time.max()) for c in curves.values())
        low, high = self._limits.get("x", (None, None))
        ticks = self._ticks(style, x_max if high is None else high)
        right = high if high is not None else max(x_max, ticks[-1] if ticks else x_max)
        left = 0.0 if low is None else low
        ax.set_xticks([t for t in ticks if left <= t <= right])
        ax.set_xlim(left, right)
        if self._kind == "cumhaz":
            ax.set_ylim(bottom=0)
        else:
            ax.set_ylim(0, 1)
        self._style_axes(ax, style)

        if self._median is not None:
            self._draw_medians(ax, style, curves, colors)
        if self._table is not None:
            self._draw_table(ax, style, colors, ticks, left, right)
        self._draw_notes(ax, style)
        if grouped:
            handles = [
                Line2D([], [], color=colors[g], lw=width, label=str(g))
                for g in self._hues
            ]
            for handle in handles:
                ax.add_line(handle)
            self._draw_legend(ax, style, n=len(handles), title=self._names["hue"])

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

    def _draw_medians(
        self,
        ax: Axes,
        style: Style,
        curves: Mapping[Any, sv.Curve],
        colors: Mapping[Any, str],
    ) -> None:
        theme = style.theme
        lw = theme.axis_line_width or 0.8
        medians = {}
        for group, curve in curves.items():
            survival = (
                curve
                if self._kind == "survival"
                else replace(
                    curve,
                    estimate=1 - curve.estimate,
                    lower=1 - curve.upper,
                    upper=1 - curve.lower,
                )
            )
            value = sv.survival_quantile(survival)[0]
            if math.isfinite(value):
                medians[group] = value
        if not medians:
            return
        ax.plot(
            [0, max(medians.values())],
            [0.5, 0.5],
            color=theme.muted_text_color or theme.text_color,
            lw=lw,
            ls=":",
            zorder=2,
        )
        for group, value in medians.items():
            ax.plot(
                [value, value], [0, 0.5], color=colors[group], lw=lw, ls=":", zorder=2
            )
            if self._median and self._median["label"]:
                ax.annotate(
                    f"{value:g}",
                    xy=(value, 0),
                    xytext=(2, 2),
                    textcoords="offset points",
                    ha="left",
                    va="bottom",
                    fontsize=style.sizes.tick,
                    color=colors[group],
                )

    def _draw_table(
        self,
        ax: Axes,
        style: Style,
        colors: Mapping[Any, str],
        ticks: Sequence[float],
        left: float,
        right: float,
    ) -> None:
        assert self._table is not None
        fig = _root_figure(ax)
        size = style.sizes.tick
        body = self._body = _TableArtists(offset=self._decor_height(style))
        times = np.array([t for t in ticks if left <= t <= right], dtype=float)
        grouped = self._names["hue"] is not None
        names = [str(g) if grouped else "All" for g in self._hues]
        text_color = style.theme.text_color or "#262626"
        cells = blended_transform_factory(ax.transData, ax.transAxes)

        def add(
            x: float, line: int, text: str, base: Transform, dx: float, **kwargs: Any
        ) -> None:
            artist = ax.text(
                x, 0, text, va="top", fontsize=size, clip_on=False, **kwargs
            )
            body.texts.append((artist, base, dx, line))

        counts = {
            g: sv.counts_at(
                frame["_t"].to_numpy(float), frame["_e"].to_numpy(int), times
            )
            for g, frame in self._groups()
        }
        # Counts are centred under their ticks; a column at the axes' left
        # edge reaches halfway into the label column.
        edge = [
            f"{int(v):,}"
            for c in counts.values()
            for values in c
            for t, v in zip(times, values, strict=True)
            if t == left
        ]
        overhang = max((_text_size(fig, s, size)[0] / 2 for s in edge), default=0.0)
        pad = size * 0.8 / _PT + overhang
        label_width = max(_text_size(fig, n, size)[0] for n in names)
        line = 0
        for row in self._table["rows"]:
            # Headers start where the widest group label starts.
            add(
                0,
                line,
                _ROW_TITLES[row],
                ax.transAxes,
                -(pad + label_width),
                ha="left",
                fontweight="bold",
                color=text_color,
            )
            line += 1
            for group, name in zip(self._hues, names, strict=True):
                add(0, line, name, ax.transAxes, -pad, ha="right", color=colors[group])
                values = counts[group][_ROWS.index(row)]
                for t, v in zip(times, values, strict=True):
                    add(
                        float(t),
                        line,
                        f"{int(v):,}",
                        cells,
                        0.0,
                        ha="center",
                        color=text_color,
                    )
                line += 1
        self._place_table(fig, style)

    def _place_table(self, fig: Figure, style: Style) -> None:
        """Shift every table text to its line below the x-axis decorations."""
        body = self._body
        step = self._line_height(style)
        gap = style.sizes.tick * 0.8 / _PT
        for text, base, dx, line in body.texts:
            dy = -(body.offset + gap + line * step)
            text.set_transform(base + ScaledTranslation(dx, dy, fig.dpi_scale_trans))

    def _draw_notes(self, ax: Axes, style: Style) -> None:
        lines = self._note_lines()
        if not lines:
            return
        loc = self._loc
        if loc == "auto":
            loc = "lower left" if self._kind == "survival" else "upper left"
        vertical, horizontal = loc.split()
        inset = style.sizes.tick * 0.6 / _PT
        fig = _root_figure(ax)
        x = 0.0 if horizontal == "left" else 1.0
        y = 0.0 if vertical == "lower" else 1.0
        dx = inset if horizontal == "left" else -inset
        dy = inset if vertical == "lower" else -inset
        ax.text(
            x,
            y,
            "\n".join(lines),
            transform=ax.transAxes + ScaledTranslation(dx, dy, fig.dpi_scale_trans),
            ha=horizontal,
            va="bottom" if vertical == "lower" else "top",
            ma=horizontal,
            fontsize=style.sizes.tick,
            color=style.theme.text_color,
            linespacing=1.4,
            zorder=4,
            # Keeps the text readable where it crosses a curve.
            bbox={
                "boxstyle": "square,pad=0.15",
                "facecolor": style.theme.axes_background or "#ffffff",
                "edgecolor": "none",
                "alpha": 0.8,
            },
        )

    def _adapt(
        self, fig: Figure, ax: Axes, style: Style, renderer: RendererBase
    ) -> None:
        """Put the risk table just below the measured x-axis decorations."""
        if self._table is None or not self._body.texts:
            return
        box = ax.xaxis.get_tightbbox(renderer)
        if box is None:
            return
        measured = max(0.0, (ax.bbox.y0 - box.y0) / fig.dpi)
        if abs(measured - self._body.offset) * _PT < 0.5:
            return
        self._body.offset = measured
        self._place_table(fig, style)
        fig.draw_without_rendering()


def survival(
    data: Any,
    time: str = "time",
    event: str = "event",
    *,
    hue: str | None = None,
    strata: str | None = None,
    kind: Kind = "survival",
    hue_order: Sequence[Any] | None = None,
    missing: DropPolicy = "raise",
) -> SurvivalPlot:
    """Kaplan-Meier survival curves (or cumulative incidence, or the
    Nelson-Aalen cumulative hazard), one per group.

    Args:
        data: DataFrame (or dict of columns), one row per subject.
        time: Column of follow-up times (numbers >= 0).
        event: Column marking an event (1 or True) or censoring (0 or False).
        hue: Column of groups (e.g. treatment arm): one curve each.
        strata: Column to stratify tests and hazard ratios by (e.g. region).
            Not drawn.
        kind: ``"survival"`` (default; Kaplan-Meier), ``"failure"``
            (1 - Kaplan-Meier, the cumulative incidence without competing
            risks) or ``"cumhaz"`` (Nelson-Aalen cumulative hazard).
        hue_order: Explicit order of the ``hue`` groups.
        missing: ``"raise"`` (default) rejects missing times, events or
            groups; ``"drop"`` leaves those subjects out.

    Example:
        >>> sp.survival(df, time="months", event="died", hue="arm")  # doctest: +SKIP
        ...     .risk_table().pvalue().hazard_ratio()
    """
    _choice(kind, _KINDS, "kind")
    frame = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    for role, column in (
        ("time", time),
        ("event", event),
        ("hue", hue),
        ("strata", strata),
    ):
        if column is not None and column not in frame:
            _choice(column, [str(c) for c in frame.columns], f"{role} column")
    raw = frame[event]
    coded = pd.to_numeric(
        raw.map(lambda v: int(v) if isinstance(v, bool | np.bool_) else v),
        errors="coerce",
    )
    wrong = raw.notna() & ~coded.isin([0, 1])
    if wrong.any():
        raise DataShapeError(
            f"event column {event!r} must be 1/True (event) or 0/False "
            f"(censored), got {raw[wrong].iloc[0]!r}. Convert it first, e.g. "
            f"df[{event!r}] == 'dead'."
        )
    frame[time] = numeric_array(frame[time])
    frame[event] = numeric_array(coded)
    keys = [c for c in (hue, strata) if c]
    frame = handle_missing(frame, missing, values=[time, event], keys=keys)
    if (frame[time] < 0).any():
        raise DataShapeError(f"time column {time!r} must not be negative")
    hues = _order(frame[hue], hue_order, "hue") if hue else [None]
    if hue:
        frame = frame[frame[hue].isin(hues)].reset_index(drop=True)
    frame["_t"] = frame[time].astype(float)
    frame["_e"] = frame[event].astype(int)
    frame["_h"] = pd.Series(
        list(frame[hue]) if hue else [None] * len(frame),
        index=frame.index,
        dtype=object,
    )
    if strata:
        frame["_s"] = frame[strata].astype(str)
    return SurvivalPlot(
        frame,
        names={"time": time, "event": event, "hue": hue, "strata": strata},
        kind=kind,
        hues=hues,
    )
