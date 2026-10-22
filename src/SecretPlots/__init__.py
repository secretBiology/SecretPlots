"""SecretPlots: easy, publication-ready plots in your own visual design.

>>> import SecretPlots as sp
>>> sp.use(preset="nature")                                   # doctest: +SKIP
>>> sp.bar(df, x="gene", y="tpm", error="sd").save("fig1.pdf")  # doctest: +SKIP
"""

from SecretPlots import fonts, presets
from SecretPlots._config import config
from SecretPlots._version import __version__
from SecretPlots.core.colors import colormaps
from SecretPlots.core.missing import MissingPolicy
from SecretPlots.core.plot import Plot
from SecretPlots.core.state import reset, use
from SecretPlots.errors import (
    ColormapWarning,
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
    SmallSampleWarning,
)
from SecretPlots.plots.area import FillBetweenPlot, area, fill_between
from SecretPlots.plots.bar import BarPlot, bar
from SecretPlots.plots.box import BoxPlot, box, boxplot
from SecretPlots.plots.heatmap import HeatmapPlot, heatmap
from SecretPlots.plots.histogram import HistogramPlot, hist, histogram
from SecretPlots.plots.line import LinePlot, line, plot
from SecretPlots.plots.scatter import ScatterPlot, scatter
from SecretPlots.plots.violin import RaincloudPlot, ViolinPlot, raincloud, violin
from SecretPlots.theme import (
    Theme,
    get_theme,
    list_themes,
    register_theme,
    theme_options,
)

__all__ = [
    "BarPlot",
    "BoxPlot",
    "ColormapWarning",
    "ConstraintAdjustedWarning",
    "DataShapeError",
    "FillBetweenPlot",
    "FontFallbackWarning",
    "FormatWarning",
    "HeatmapPlot",
    "HistogramPlot",
    "LabelsHiddenWarning",
    "LimitExceededWarning",
    "LinePlot",
    "MissingPolicy",
    "PaletteExtendedWarning",
    "Plot",
    "PresetError",
    "PresetNotFoundError",
    "RaincloudPlot",
    "ScatterPlot",
    "SecretPlotsError",
    "SecretPlotsWarning",
    "SmallSampleWarning",
    "Theme",
    "ViolinPlot",
    "__version__",
    "area",
    "bar",
    "box",
    "boxplot",
    "colormaps",
    "config",
    "fill_between",
    "fonts",
    "get_theme",
    "heatmap",
    "hist",
    "histogram",
    "line",
    "list_themes",
    "plot",
    "presets",
    "raincloud",
    "register_theme",
    "reset",
    "scatter",
    "theme_options",
    "use",
    "violin",
]
