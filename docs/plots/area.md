# Area plots and fill between

`sp.fill_between()` fills the area between two edges along x: `y1` and `y2`.
`y2` is a baseline number (0 by default), which makes an area chart, or a
column, which makes a band. `sp.area()` is the same with `y=` and `baseline=`.
Groups can overlap, be stacked, or be stacked to 100 %.

```python
import numpy as np
import pandas as pd
import SecretPlots as sp

rng = np.random.default_rng(2)
years = np.arange(2000, 2025)
energy = pd.DataFrame(
    {
        "year": years,
        "Coal": 40 - 0.9 * (years - 2000) + rng.normal(0, 1, 25),
        "Gas": 25 + 0.2 * (years - 2000),
        "Solar": 0.5 * np.exp(0.17 * (years - 2000)),
        "Wind": 1 + 0.6 * (years - 2000),
    }
)

sp.area(energy, x="year", stack=True).endlabels()
```

Examples on this page use `energy` above (a wide table: one column per
electricity source) and its long form `long`:

```python
long = energy.melt("year", var_name="source", value_name="TWh")
long.head()
```

## Contents

- [Signature](#signature)
- [Input data](#input-data)
- [Area charts](#area-charts)
- [Bands between two columns](#bands-between-two-columns)
- [Stacked areas](#stacked-areas)
- [Above and below: split by sign](#above-and-below-split-by-sign)
- [Gradients](#gradients)
- [Edge lines](#edge-lines)
- [Labels, reference lines and source data](#labels-reference-lines-and-source-data)
- [Warnings and errors](#warnings-and-errors)

## Signature

```text
sp.fill_between(data=None, x=None, y1=None, y2=0, hue=None, *,
                stack=False, sort=True, order=None, hue_order=None) -> FillBetweenPlot

sp.area(data=None, x=None, y=None, hue=None, *,
        baseline=0, stack=False, sort=True, order=None, hue_order=None) -> FillBetweenPlot
```

| Argument | Meaning |
|---|---|
| `data` | Long DataFrame or dict of columns; a wide DataFrame (one area per numeric column); a Series; a list/array of values. Can be left out. |
| `x` | Column name or sequence: numbers, dates or categories. |
| `y1` (`y`) | The top (or first) edge. |
| `y2` (`baseline`) | The other edge: a number (baseline) or, for `fill_between`, a column (a band). |
| `hue` | Column with groups: one area per group. |
| `stack` | `True` stacks the groups' areas; `"percent"` scales every x to 100 %. |
| `sort` | Connect points in x order. |
| `order`, `hue_order` | Order of category x values / of groups. |

Chainable steps specific to area plots: `.lines()`, `.gradient()`, `.split()`,
`.endlabels()`, `.refline()`, `.grouplabels()`, `.ticklabels()`, and
`.source_data()`. Everything else (labels, legend, colors, highlight, limits,
presets, themes, saving) works as for [bar plots](bar.md). Run
`sp.FillBetweenPlot.options()` for the full list.

## Input data

```python
sp.area(x=[0, 1, 2, 3, 4], y=[1, 3, 2, 5, 4])                 # sequences
```

```python
sp.area(long, x="year", y="TWh", hue="source")                # long form
```

```python
sp.area(energy, x="year")                                     # wide: one area per column
```

```python
sp.area(energy.set_index("year")["Solar"])                    # Series: index -> x
```

Each x appears once per area: summarize replicates first, or use
[`sp.line(..., error=...)`](line.md) to draw a summary with an error band.
Rows with a missing value are left out.

## Area charts

An area chart fills down to the baseline, draws the top edge as a line, and
sits on the baseline without a gap below it:

```python
sp.area(energy, x="year", y="Solar")
```

```python
sp.area(energy, x="year", y="Coal", baseline=20)
```

Overlapping groups are see-through (`fill_alpha` in the theme), each with its
top edge in the group color:

```python
sp.area(long[long["source"].isin(["Coal", "Wind"])], x="year", y="TWh", hue="source")
```

## Bands between two columns

With `y2` as a column the area is a band: a range, an interval from a model, a
min-max envelope. Bands have no edge lines by default:

```python
months = pd.DataFrame({"month": pd.date_range("2023-01-01", periods=24, freq="MS")})
months["mid"] = 50 + rng.normal(0, 2, 24).cumsum()
months["low"], months["high"] = months["mid"] - 6, months["mid"] + 6

sp.fill_between(months, x="month", y1="high", y2="low").labels(y="Forecast")
```

To combine a band with a line, draw the line into the same axes:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
sp.fill_between(months, x="month", y1="high", y2="low").render(ax=ax)
sp.line(months, x="month", y="mid").render(ax=ax)
plt.close(fig)
```

## Stacked areas

`stack=True` stacks the groups. Layers are separated by thin background-colored
lines, and the legend lists the top layer first, as you read the stack:

```python
sp.area(long, x="year", y="TWh", hue="source", stack=True)
```

`stack="percent"` shows each group's share of the total at every x; the y axis
runs from 0 % to 100 %:

```python
sp.area(long, x="year", y="TWh", hue="source", stack="percent")
```

Missing combinations of x and group count as 0 in a stack.

## Above and below: split by sign

`.split()` colors the area where `y1` is above `y2` differently from where it is
below, using the theme's `positive` and `negative` colors. Crossings are
interpolated, so the colors change exactly where the lines cross:

```python
t = np.linspace(0, 10, 200)
anomaly = pd.DataFrame({"t": t, "anomaly": np.sin(t) * 0.8 + 0.1 * t - 0.4})
(
    sp.fill_between(anomaly, x="t", y1="anomaly")
    .split(labels=("warmer", "cooler"))
    .refline(0)
)
```

With two columns it shades the gap between two series: here exports against
imports, with both lines drawn:

```python
trade = pd.DataFrame(
    {"year": years, "exports": 50 + 8 * np.sin(years / 3), "imports": 50 + 0.4 * (years - 2000)}
)
(
    sp.fill_between(trade, x="year", y1="exports", y2="imports")
    .split(colors=("#2a9d8f", "#e76f51"), labels=("surplus", "deficit"))
)
```

## Gradients

`.gradient()` fades each area from its `y1` edge to transparent at `y2`:

```python
sp.area(energy, x="year", y="Solar").gradient().endlabels(values=".0f")
```

```python
sp.fill_between(months, x="month", y1="high", y2="low").gradient()
```

Gradients don't apply to stacks (they would blur the layers) and fall back to
an even fill on a log y axis.

## Edge lines

`.lines()` picks which edges get a line: `"top"`, `"both"`, `"none"`, or
`"auto"` (top for areas, none for bands, separators for stacks, both when a
band is split by sign). `width=` sets the line width in pt:

```python
sp.fill_between(months, x="month", y1="high", y2="low").lines("both", width=0.6)
```

```python
sp.area(long, x="year", y="TWh", hue="source", stack=True).lines("none")
```

## Labels, reference lines and source data

`.endlabels()` names each area at its right end instead of a legend (stacked
layers are labeled at their middle); `values=` adds the last value (the layer's
own value in a stack):

```python
sp.area(long, x="year", y="TWh", hue="source", stack="percent").endlabels(values=".0f")
```

`.refline()` adds dashed reference lines, horizontal or (`axis="x"`) vertical:

```python
sp.area(energy, x="year", y="Wind").refline(2015, axis="x", label=True)
```

`.source_data()` returns the plotted numbers; for stacks it includes each
layer's lower and upper edge:

```python
sp.area(long, x="year", y="TWh", hue="source", stack=True).source_data().head()
```

The opacity of overlapping areas and bands is the theme's `fill_alpha`
(0.22 by default), and edge lines use `line_width`:

```python
sp.area(long, x="year", y="TWh", hue="source").theme(fill_alpha=0.35)
```

## Warnings and errors

- Each x can appear only once per area (`DataShapeError` with a hint to
  summarize first or use `sp.line(error=...)`).
- Stacks need a number as `y2`, not a column.
- `.gradient()` can't be used with stacks; `.split()` works on a single area
  without `hue=` or `stack=`.
