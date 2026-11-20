# API reference

Every plot follows the same pattern: a **function** such as `sp.bar(...)` takes
the data and the column mapping and returns a **plot object** such as
`BarPlot`. You then chain methods on that object to adjust it. Nothing is
drawn until you call `.save()`, `.show()`, or access `.fig`/`.ax`.

```python
import SecretPlots as sp

plot = sp.bar({"Control": 98, "Treated": 71})   # function: data -> BarPlot
plot.labels(y="Viability (%)").preset("nature")  # chained BarPlot methods
```

Each section below lists the function first, then the methods specific to that
plot. Methods every plot has (`labels`, `size`, `legend`, `save`, ...) are under
[Shared plot methods](#shared-plot-methods).

Use the [plot guides](gallery.md) for illustrated examples and the
[option discovery guide](options.md) to explore the API interactively:
`sp.BarPlot.arguments()` shows the constructor arguments as a table, and
`plot.options("legend")` or `sp.BarPlot.options()` lists the chainable methods.

## Shared plot methods

All plot types inherit sizing, labels, legends, styling, option discovery,
rendering, copying, axis formatting, reference lines, and export from `Plot`.

::: SecretPlots.core.plot.Plot

## Bar

Bars for one value per category, grouped or stacked by `hue`, with error bars
from replicate rows.

::: SecretPlots.bar
::: SecretPlots.BarPlot

## Scatter

One marker per row, with optional color/size/style encodings and fit lines.

::: SecretPlots.scatter
::: SecretPlots.ScatterPlot

## Line

One line per group along `x`; replicate rows are summarized with error bars or
bands.

::: SecretPlots.line
::: SecretPlots.LinePlot

## Area and fill between

Filled areas: area charts, stacked composition, and bands between two series.

::: SecretPlots.fill_between
::: SecretPlots.area
::: SecretPlots.FillBetweenPlot

### Shared line and area methods

Line and area plots both have these methods.

::: SecretPlots.plots.series.SeriesPlot
    options:
      heading_level: 4

## Histogram

Distribution of one numeric variable, optionally split into groups, with
density, fit and rug overlays.

::: SecretPlots.histogram
::: SecretPlots.HistogramPlot

## Heatmap

A colored cell per row and column of a matrix, with clustering, groups,
annotation tracks and cell values.

::: SecretPlots.heatmap
::: SecretPlots.HeatmapPlot

## Forest

Estimates and confidence intervals per row beside a table, for subgroup
analyses and meta-analyses.

::: SecretPlots.forest
::: SecretPlots.ForestPlot

## Survival

Kaplan-Meier, cumulative incidence and cumulative hazard curves with risk
tables, tests and hazard ratios.

::: SecretPlots.survival
::: SecretPlots.SurvivalPlot

## Decision curves

Net benefit of risk models across threshold probabilities.

::: SecretPlots.decision_curve
::: SecretPlots.DecisionCurvePlot

## Box

Box-and-whisker summaries per category. The methods are shared with violin and
raincloud plots and are listed under
[Shared box, violin and raincloud methods](#shared-box-violin-and-raincloud-methods).

::: SecretPlots.box
::: SecretPlots.BoxPlot

## Violin and raincloud

Density shapes per category; a raincloud adds the raw points and a box. Shape
options (bandwidth, inner marks, split) are arguments of the function.

::: SecretPlots.violin
::: SecretPlots.raincloud
::: SecretPlots.ViolinPlot
::: SecretPlots.RaincloudPlot

### Shared box, violin and raincloud methods

Points, means, sample sizes and statistical comparisons work the same way on
all three plot types.

::: SecretPlots.plots.distribution.DistributionPlot
    options:
      heading_level: 4

## Themes and discovery

A theme sets how a plot looks; it is independent of the preset, which sets
where the figure goes. Pass any field below to `.theme(...)` on one plot, or
build a `Theme` for `sp.use(theme=...)` or `sp.register_theme(...)`.

::: SecretPlots.theme_options
::: SecretPlots.list_themes
::: SecretPlots.get_theme
::: SecretPlots.register_theme
::: SecretPlots.colormaps
::: SecretPlots.Theme

#### Theme fields

Defaults are those of the built-in `"secret"` theme; `None` in a theme means
"inherit from the next layer". The same table is available as
`sp.theme_options()`.

<!-- theme-fields -->

## Defaults and presets

`sp.use(...)` selects the preset and theme for every plot created afterwards;
`.preset(...)` and `.theme(...)` on a plot override them for that plot only.

::: SecretPlots.use
::: SecretPlots.reset
::: SecretPlots.presets
