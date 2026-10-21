"""Theme x Preset -> concrete style (sizes, fonts, rcParams)."""

from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from typing import Any

import matplotlib as mpl
from cycler import cycler

from SecretPlots.core.fonts import FontChain, FontChoice, resolve_font
from SecretPlots.core.merge import Layer, cascade
from SecretPlots.core.units import Length, to_inches
from SecretPlots.errors import ConstraintAdjustedWarning, emit
from SecretPlots.presets import Chrome, Preset, Target
from SecretPlots.theme import BASE_THEME, Theme

PLOT_LAYER = "plot (your settings)"


@dataclass(frozen=True)
class Sizes:
    """Resolved text sizes in points."""

    tick: float
    label: float
    title: float
    subtitle: float
    note: float
    panel: float


@dataclass(frozen=True)
class Style:
    """Everything a plot needs to draw itself."""

    kind: str
    preset: Preset
    theme: Theme
    provenance: Mapping[str, str]
    font: FontChoice
    sizes: Sizes
    width: float
    height: float
    adjustments: tuple[str, ...]

    @property
    def figsize(self) -> tuple[float, float]:
        return (self.width, self.height)

    @property
    def target(self) -> Target:
        return self.preset.target

    @property
    def chrome(self) -> Chrome:
        return self.preset.chrome

    def explain(self, field: str) -> str:
        """Where a resolved value came from, e.g. ``explain("font_family")``."""
        if field in ("font", "font_family"):
            return f"font = {self.font.family!r}  [{self.font.source}" + (
                ", fallback]" if self.font.is_fallback else "]"
            )
        if field not in self.provenance:
            raise KeyError(f"Unknown style field {field!r}")
        return f"{field} = {getattr(self.theme, field)!r}  [{self.provenance[field]}]"

    def report(self) -> str:
        lines = [
            f"preset: {self.preset.name} ({self.preset.kind})",
            f"size: {self.width:.3f} x {self.height:.3f} in",
            self.explain("font"),
            f"text sizes (pt): tick {self.sizes.tick:.2f}, "
            f"label {self.sizes.label:.2f}, "
            f"title {self.sizes.title:.2f}",
        ]
        lines += [
            f"{k} = {getattr(self.theme, k)!r} <- {v}"
            for k, v in self.provenance.items()
        ]
        lines += [f"adjusted: {a}" for a in self.adjustments]
        return "\n".join(lines)

    def rc_context(self) -> AbstractContextManager[None]:
        """Context in which plots are drawn and saved."""
        return mpl.rc_context(self.rc())  # type: ignore[arg-type]

    def rc(self) -> dict[str, Any]:
        """rcParams for :func:`matplotlib.rc_context` while drawing and saving."""
        t, s = self.theme, self.sizes
        spines = set(t.spines or ())
        rc: dict[str, Any] = {
            "font.family": [self.font.family],
            "font.size": s.tick,
            "axes.labelsize": s.label,
            "axes.titlesize": s.title,
            "axes.titleweight": t.title_weight,
            "axes.titlelocation": self.chrome.title_align,
            "xtick.labelsize": s.tick,
            "ytick.labelsize": s.tick,
            "legend.fontsize": s.tick,
            "legend.title_fontsize": s.tick,
            "legend.frameon": t.legend_frame,
            "text.color": t.text_color,
            "axes.labelcolor": t.text_color,
            "axes.titlecolor": t.text_color,
            "xtick.color": t.axis_color,
            "ytick.color": t.axis_color,
            "xtick.labelcolor": t.text_color,
            "ytick.labelcolor": t.text_color,
            "axes.edgecolor": t.axis_color,
            "axes.linewidth": t.axis_line_width,
            "lines.linewidth": t.line_width,
            "xtick.major.width": t.axis_line_width,
            "ytick.major.width": t.axis_line_width,
            "xtick.major.size": t.tick_length,
            "ytick.major.size": t.tick_length,
            "axes.facecolor": t.axes_background,
            "figure.facecolor": t.background,
            "savefig.facecolor": t.background,
            "axes.grid": False,
            "axes.axisbelow": True,
            "grid.color": t.grid_color,
            "grid.linewidth": t.grid_width,
            "grid.linestyle": t.grid_style,
            "axes.prop_cycle": cycler(color=list(t.palette or ())),
            "figure.dpi": 100,
            "savefig.dpi": self.target.dpi,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
        for side in ("left", "right", "top", "bottom"):
            rc[f"axes.spines.{side}"] = side in spines
        return rc


def _fit_sizes(
    theme: Theme, preset: Preset, provenance: Mapping[str, str], adjustments: list[str]
) -> Sizes:
    t = preset.target
    base = float(theme.font_size or 0)
    body = {
        "tick": base,
        "label": base * (theme.label_scale or 1),
        "title": base * (theme.title_scale or 1),
        "subtitle": base * (theme.subtitle_scale or 1),
        "note": base * (theme.note_scale or 1),
    }
    largest = max(body.values())
    if t.max_font_size is not None and largest > t.max_font_size:
        factor = t.max_font_size / largest
        body = {k: v * factor for k, v in body.items()}
        adjustments.append(
            f"text scaled by {factor:.2f} so the largest text is "
            f"{t.max_font_size:g} pt ({preset.name} maximum)"
        )
    if t.min_font_size is not None:
        too_small = [k for k, v in body.items() if v < t.min_font_size - 1e-9]
        if too_small:
            body = {k: max(v, t.min_font_size) for k, v in body.items()}
            adjustments.append(
                f"{', '.join(too_small)} text raised to {t.min_font_size:g} pt "
                f"({preset.name} minimum)"
            )
    # Round to 0.01 pt and re-clamp so float noise never exceeds a limit.
    low = t.min_font_size if t.min_font_size is not None else 0.0
    high = t.max_font_size if t.max_font_size is not None else float("inf")
    body = {k: min(max(round(v, 2), low), high) for k, v in body.items()}
    if adjustments and provenance.get("font_size") == PLOT_LAYER:
        emit(
            ConstraintAdjustedWarning,
            f"font_size={base:g} adjusted for preset {preset.name!r}: "
            + "; ".join(adjustments),
            stacklevel=5,
        )
    panel = preset.chrome.panel_label_size or body["title"]
    return Sizes(panel=panel, **body)


def _fit_lines(
    theme: Theme, preset: Preset, provenance: Mapping[str, str], adjustments: list[str]
) -> Theme:
    minimum = preset.target.min_line_width
    if minimum is None:
        return theme
    changes: dict[str, Any] = {}
    for name in ("line_width", "axis_line_width", "grid_width"):
        value = getattr(theme, name)
        if value is not None and 0 < value < minimum:
            changes[name] = minimum
    if not changes:
        return theme
    adjustments.append(
        f"{', '.join(changes)} raised to {minimum:g} pt ({preset.name} minimum)"
    )
    explicit = [n for n in changes if provenance.get(n) == PLOT_LAYER]
    if explicit:
        emit(
            ConstraintAdjustedWarning,
            f"{', '.join(explicit)} raised to {minimum:g} pt "
            f"for preset {preset.name!r}",
            stacklevel=5,
        )
    return replace(theme, **changes)


def resolve(
    kind: str,
    *,
    preset: Preset,
    theme: Theme,
    overrides: Theme | None = None,
    width: Length | None = None,
    height: Length | None = None,
) -> Style:
    """Combine layers (highest priority first): plot overrides, preset per-plot
    section, preset theme, the active theme, then the base ``"secret"`` theme."""
    layers = [
        Layer(PLOT_LAYER, overrides or Theme()),
        Layer(f"preset {preset.name!r} [plots.{kind}]", preset.plot_theme(kind)),
        Layer(f"preset {preset.name!r}", preset.theme),
        Layer(f"theme {theme.name!r}", theme),
        Layer(f"theme {BASE_THEME.name!r} (base)", BASE_THEME),
    ]
    merged = cascade(layers)
    adjustments: list[str] = []

    chains = [
        FontChain(layer.name, layer.theme.font_family, layer.theme.font_generic)
        for layer in layers
        if layer.theme.font_family
    ]
    font = resolve_font(chains, required_generic=preset.target.font_generic)

    resolved = _fit_lines(merged.theme, preset, merged.provenance, adjustments)
    sizes = _fit_sizes(resolved, preset, merged.provenance, adjustments)

    target = preset.target
    w = target.width(width)
    h = (
        to_inches(height, px_per_inch=target.px_per_inch)
        if height is not None
        else w * target.aspect
    )
    if target.max_height is not None and h > target.max_height:
        adjustments.append(
            f"height {h:.2f} in reduced to {preset.name} maximum "
            f"{target.max_height:.2f} in"
        )
        if height is not None:
            emit(
                ConstraintAdjustedWarning,
                f"height reduced to {target.max_height:.2f} in, the maximum for "
                f"preset {preset.name!r}",
                stacklevel=4,
            )
        h = target.max_height

    return Style(
        kind=kind,
        preset=preset,
        theme=resolved,
        provenance=merged.provenance,
        font=font,
        sizes=sizes,
        width=w,
        height=h,
        adjustments=tuple(adjustments),
    )
