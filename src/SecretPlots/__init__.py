"""SecretPlots: easy, publication-ready plots in your own visual design.

>>> import SecretPlots as sp
>>> sp.use(preset="nature")                                   # doctest: +SKIP
>>> sp.bar(df, x="gene", y="tpm", error="sd").save("fig1.pdf")  # doctest: +SKIP
"""

from SecretPlots import fonts, presets
from SecretPlots._config import config
from SecretPlots._version import __version__
from SecretPlots.core.plot import Plot
from SecretPlots.core.state import reset, use
from SecretPlots.errors import (
    ConstraintAdjustedWarning,
    DataShapeError,
    FontFallbackWarning,
    FormatWarning,
    LabelsHiddenWarning,
    LimitExceededWarning,
    PaletteExtendedWarning,
    PresetError,
    PresetNotFoundError,
    SecretPlotsError,
    SecretPlotsWarning,
)
from SecretPlots.plots.bar import BarPlot, bar
from SecretPlots.theme import (
    Theme,
    get_theme,
    list_themes,
    register_theme,
    theme_options,
)

__all__ = [
    "BarPlot",
    "ConstraintAdjustedWarning",
    "DataShapeError",
    "FontFallbackWarning",
    "FormatWarning",
    "LabelsHiddenWarning",
    "LimitExceededWarning",
    "PaletteExtendedWarning",
    "Plot",
    "PresetError",
    "PresetNotFoundError",
    "SecretPlotsError",
    "SecretPlotsWarning",
    "Theme",
    "__version__",
    "bar",
    "config",
    "fonts",
    "get_theme",
    "list_themes",
    "presets",
    "register_theme",
    "reset",
    "theme_options",
    "use",
]
