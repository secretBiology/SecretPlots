from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from SecretPlots.core.units import DEFAULT_PX_PER_INCH, Length, to_inches
from SecretPlots.errors import PresetError
from SecretPlots.theme import FontGeneric, Theme

PresetKind = Literal["journal", "news", "generic"]


@dataclass(frozen=True, kw_only=True)
class Target:
    """Physical output constraints. Lengths are stored in inches."""

    widths: Mapping[str, float]
    default_width: str
    aspect: float = 0.62
    max_height: float | None = None
    min_font_size: float | None = None
    max_font_size: float | None = None
    min_line_width: float | None = None
    font_generic: FontGeneric | None = None
    px_per_inch: float = DEFAULT_PX_PER_INCH
    dpi: float = 300.0
    formats: tuple[str, ...] = ("pdf", "svg", "png")

    def __post_init__(self) -> None:
        if self.default_width not in self.widths:
            raise PresetError(
                f"default_width {self.default_width!r} is not one of the widths "
                f"{sorted(self.widths)}"
            )
        object.__setattr__(self, "widths", MappingProxyType(dict(self.widths)))

    def width(self, value: Length | None = None) -> float:
        """Resolve a width name (``"single"``) or explicit length to inches."""
        if value is None:
            return self.widths[self.default_width]
        if isinstance(value, str) and value in self.widths:
            return self.widths[value]
        try:
            return to_inches(value, px_per_inch=self.px_per_inch)
        except ValueError:
            raise PresetError(
                f"Unknown width {value!r}. Use one of {sorted(self.widths)} or an "
                "explicit length such as '120mm', '600px' or 3.5 (inches)."
            ) from None


@dataclass(frozen=True, kw_only=True)
class Chrome:
    """Furniture around the plot: title block, source line, panel labels."""

    title_align: Literal["left", "center"] = "left"
    source_prefix: str = "Source: "
    footer_rule: bool = False
    accent_bar: str | None = None
    panel_label_case: Literal["lower", "upper"] = "lower"
    panel_label_weight: str = "bold"
    panel_label_size: float | None = None
    padding: float = 0.08


@dataclass(frozen=True, kw_only=True)
class Preset:
    """A named bundle: where the figure goes (target), optionally how it looks
    (theme, per-plot overrides) and the furniture around it (chrome)."""

    name: str
    kind: PresetKind
    target: Target
    description: str = ""
    official: bool = False
    source_url: str | None = None
    verified_on: str | None = None
    disclaimer: str | None = None
    theme: Theme = field(default_factory=Theme)
    chrome: Chrome = field(default_factory=Chrome)
    plots: Mapping[str, Theme] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "plots", MappingProxyType(dict(self.plots)))

    def plot_theme(self, kind: str) -> Theme:
        """Per-plot-type overrides (empty theme if the preset has none)."""
        return self.plots.get(kind, Theme(name=f"{self.name}:{kind}"))
