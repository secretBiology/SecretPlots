# API reference

Use the [plot guides](gallery.md) for illustrated examples and the
[option discovery guide](options.md) to explore the API interactively.
Constructor arguments are shown below; chainable options are also available
through `plot.options("step")` or a class such as `sp.BarPlot.options("legend")`.

## Shared plot methods

All plot types inherit sizing, labels, legends, styling, option discovery,
rendering, copying, axis formatting, reference lines, and export from `Plot`.

::: SecretPlots.core.plot.Plot

## Bar

::: SecretPlots.bar
::: SecretPlots.BarPlot

## Scatter

::: SecretPlots.scatter
::: SecretPlots.ScatterPlot

## Line

::: SecretPlots.line
::: SecretPlots.LinePlot

## Area and fill between

::: SecretPlots.fill_between
::: SecretPlots.area
::: SecretPlots.FillBetweenPlot

## Histogram

::: SecretPlots.histogram
::: SecretPlots.HistogramPlot

## Heatmap

::: SecretPlots.heatmap
::: SecretPlots.HeatmapPlot

## Forest

::: SecretPlots.forest
::: SecretPlots.ForestPlot

## Box

::: SecretPlots.box
::: SecretPlots.BoxPlot

## Violin and raincloud

::: SecretPlots.violin
::: SecretPlots.raincloud
::: SecretPlots.ViolinPlot
::: SecretPlots.RaincloudPlot

## Themes and discovery

::: SecretPlots.theme_options
::: SecretPlots.list_themes
::: SecretPlots.get_theme
::: SecretPlots.register_theme
::: SecretPlots.colormaps
::: SecretPlots.Theme

## Defaults and presets

::: SecretPlots.use
::: SecretPlots.reset
::: SecretPlots.presets
