# Histograms

`sp.histogram()` (alias `sp.hist()`) shows how one numeric variable is
distributed. You can show counts or normalized heights such as proportion,
percent or density, split the data into groups, overlay smooth curves and
mark reference values.

```python
import numpy as np
import pandas as pd
import SecretPlots as sp

rng = np.random.default_rng(7)
df = pd.DataFrame(
    {
        "age": np.r_[rng.normal(42, 9, 320), rng.normal(56, 7, 180)],
        "group": ["control"] * 320 + ["patient"] * 180,
    }
)

sp.histogram(df, x="age", hue="group", stat="density").kde()
```

The examples below use `df`: age for 320 controls and 180 patients. Like every
SecretPlots plot, nothing is drawn until the plot is displayed, saved, shown,
or you access `.fig` / `.ax`.

## Contents

- [Signature](#signature)
- [Input data](#input-data)
- [Count, proportion, percent or density](#count-proportion-percent-or-density)
- [Bins](#bins)
- [Groups](#groups)
- [Density curves and fits](#density-curves-and-fits)
- [Cumulative histograms](#cumulative-histograms)
- [Reference lines, rug and sample size](#reference-lines-rug-and-sample-size)
- [Axes, colors, legend and saving](#axes-colors-legend-and-saving)
- [Recipes](#recipes)
- [Journal checklist](#journal-checklist)
- [Warnings and errors](#warnings-and-errors)

## Signature

```text
sp.histogram(data=None, x=None, hue=None, *,
             bins="auto", binwidth=None, binrange=None, discrete=False,
             stat="count", common_norm=False, cumulative=False,
             multiple="layer", element=None, orient="v", hue_order=None) -> HistogramPlot
```

| Argument | Meaning |
|---|---|
| `data` | Values (list, array, Series), a DataFrame with `x=`/`hue=` column names, a wide DataFrame or 2-D array (one group per column), or a dict `{group: values}`. |
| `x` | Column with the values (or the values themselves when `data` is left out). |
| `hue` | Column with groups. |
| `bins`, `binwidth`, `binrange`, `discrete` | How values are binned; see [Bins](#bins). |
| `stat` | Bar height: `"count"`, `"probability"`, `"percent"`, `"density"` or `"frequency"`. |
| `common_norm` | Normalize all groups together instead of each on its own. |
| `cumulative` | Running total from left to right. |
| `multiple` | Groups `"layer"` (overlaid, default), `"stack"` or `"dodge"` (side by side). |
| `element` | `"bars"` or `"step"` (outlines). |
| `orient` | `"v"` (bars up) or `"h"` (bars to the right). |
| `hue_order` | Explicit group order. |

Steps specific to histograms: `.kde()`, `.fit()`, `.refline()`, `.rug()`,
`.show_n()`, plus `.bin_edges` and `.source_data()`. Run
`sp.HistogramPlot.options()` for the full list.

## Input data

```python
sp.histogram(df["age"])                                  # a Series (or list/array)
```

```python
sp.histogram(df, x="age", hue="group")                   # DataFrame + column names
```

```python
sp.histogram({"control": rng.normal(0, 1, 200),          # dict: one group per key,
              "treated": rng.normal(1, 1, 150)})         # groups of any size
```

Missing and infinite values are left out. All groups share the same bins.

## Count, proportion, percent or density

`stat` sets what the bar heights mean. The names follow seaborn:

| `stat` | Bar height | Use it for |
|---|---|---|
| `"count"` (default) | Number of values in the bin | Raw numbers; readers see n directly. |
| `"probability"` (or `"proportion"`) | Fraction of values; heights sum to 1 | Comparing groups of different sizes. |
| `"percent"` | Percent of values; heights sum to 100 | Same, for a general audience. |
| `"density"` | Fraction ÷ bin width; total area is 1 | Overlaying a density curve or fitted distribution; unequal bins. |
| `"frequency"` | Count ÷ bin width | Counts per unit with unequal bins. |

```python
sp.histogram(df, x="age", stat="density")
```

```python
sp.histogram(df, x="age", hue="group", stat="percent")
```

With groups, each group is normalized on its own, so groups of different
sizes can be compared by shape. With `common_norm=True` all groups share one
normalization, so the patients' smaller share shows:

```python
sp.histogram(df, x="age", hue="group", stat="density", common_norm=True)
```

The axis title follows `stat` ("Density", "Proportion", …); change it with
`.labels(y=...)`.

## Bins

The default `bins="auto"` takes whichever of the Sturges and Freedman–Diaconis
rules gives the narrower bins (as numpy does). A histogram's shape depends
on the bin width, so try a few widths, and state the one you use in the
figure legend.

```python
sp.histogram(df, x="age", binwidth=5)                    # bin width in data units
```

```python
sp.histogram(df, x="age", bins=20, binrange=(20, 80))    # number of bins over a range
```

```python
sp.histogram(df, x="age", bins="fd")                     # a rule: fd, sturges, scott, rice, sqrt, doane
```

```python
sp.histogram(df, x="age", bins=[20, 30, 40, 50, 60, 80], stat="density")   # explicit edges
```

```python
sp.histogram(rng.poisson(3, 400), discrete=True, stat="probability")   # one bin per integer
```

`plot.bin_edges` returns the edges actually used:

```python
plot = sp.histogram(df, x="age", bins="fd")
width = plot.bin_edges[1] - plot.bin_edges[0]
plot.labels(x=f"Age (years; bins of {width:.1f})")
```

On a log axis (`.log("x")`) the bins are evenly spaced in log space, so they
appear equally wide:

```python
sp.histogram(rng.lognormal(2, 1, 500)).log("x").labels(x="Concentration (nM)")
```

## Groups

By default, groups are overlaid as outlines with a light fill. Overlapping
filled bars blend into what looks like a third group; outlines stay readable
where they cross.

```python
sp.histogram(df, x="age", hue="group")
```

```python
sp.histogram(df, x="age", hue="group", element="bars")               # translucent bars
```

```python
sp.histogram(df, x="age", hue="group", multiple="stack")             # stacked
```

```python
sp.histogram(df, x="age", hue="group", multiple="dodge", binwidth=5)  # side by side
```

Stacking makes every group except the bottom one hard to read. Use it only
when the total matters as much as the parts.

## Density curves and fits

`.kde()` overlays a smooth density estimate (Gaussian kernel) for each group.
It is scaled to the bars' `stat`, so it lines up with counts as well as with
densities:

```python
sp.histogram(df, x="age", hue="group", stat="density").kde()
```

```python
sp.histogram(df, x="age").kde(bw_adjust=0.5)                  # follow the data more closely
sp.histogram(df, x="age").kde(color="#d62728")                 # curve color
sp.histogram(df, x="age", hue="group").kde(color={"patient": "black"})  # one group
```

Without `hue` the curve is drawn in the text color; with `hue`, in each
group's color. `color=` changes only the curve, not the bars.

The curve stops at the smallest and largest value (`cut=0`), so it never
suggests impossible values such as negative ages. Use `cut=3` to draw the
tails.

`.fit("normal")` overlays a normal distribution with the sample mean and
standard deviation, as a dashed line:

```python
sp.histogram(df[df.group == "control"], x="age", stat="density").fit("normal")
```

## Cumulative histograms

```python
sp.histogram(df, x="age", hue="group", stat="percent", cumulative=True).kde()
```

Each group rises to 100% (or 1, or its count). This is a binned version of
the empirical cumulative distribution. The `.kde()` curve is its smooth
counterpart. With `stat="density"` the axis is "Cumulative proportion".

## Reference lines, rug and sample size

```python
(
    sp.histogram(df, x="age", hue="group")
    .refline("median", label=True)       # per group, in the group's colour
    .show_n()                            # "control (n = 320)" in the legend
)
```

`.refline()` takes `"mean"`, `"median"` and numbers (e.g. a clinical cutoff:
`.refline(65)`). `"mean"` and `"median"` draw one line per group, in the
group's colour; their labels are stacked so close lines stay readable.
`label=True` prints the value next to each line, and text prints that text.

Without `axis=` the lines cross the binned axis (vertical lines for vertical
bars). `axis="y"` draws horizontal lines on the count axis instead, e.g. a
count threshold. Each call adds lines and can have its own `color`,
`linestyle` and `linewidth`; see [bar plots](bar.md#reference-lines) for all
options.

```python
(
    sp.histogram(df, x="age")
    .refline(65, label="retirement", color="#da1e28", linestyle="-")
    .refline(20, axis="y", linestyle=":")
)
```

With few values, a histogram's shape mostly reflects the bin choice.
SecretPlots warns below 30 values (`SmallSampleWarning`). `.rug()` adds a tick
for every value, which shows readers the individual data points:

```python
sp.histogram(rng.normal(5, 1, 18)).rug()
```

## Axes, colors, legend and saving

These work as for [bar plots](bar.md):

```python
(
    sp.histogram(df, x="age", hue="group", stat="probability")
    .colors({"control": "#8d99ae", "patient": "#d62828"})
    .labels(x="Age (years)")
    .legend("inside", loc="upper left", title="")
    .preset("nature")
)
```

```python
sp.histogram(df, x="age", hue="group").highlight("patient")
```

```python
sp.histogram(df, x="age", orient="h")                     # horizontal bars
```

`plot.source_data()` returns one row per bin and group, with the bin edges,
counts, the plotted `stat` and n. Use it for a journal's source-data file:

```python
sp.histogram(df, x="age", hue="group", binwidth=5).source_data().head()
```

## Recipes

Comparing two distributions of different size, for a single-column figure:

```python
(
    sp.histogram(df, x="age", hue="group", stat="density", binwidth=4)
    .kde()
    .refline("median")
    .show_n()
    .labels(x="Age (years)")
    .legend(title="")
    .preset("nature")
)
```

Discrete scores with percentages and a cutoff:

```python
scores = pd.DataFrame({"score": rng.binomial(10, 0.6, 250)})
(
    sp.histogram(scores, x="score", discrete=True, stat="percent")
    .refline(7, label=True)
    .labels(x="Symptom score (0-10)")
)
```

## Journal checklist

- **n.** Report the number of values per group; `.show_n()` puts it on the
  plot. Nature's reporting checklist asks for individual data points when n is
  small. Use `.rug()`, or a dot or strip plot instead of a histogram.
- **Bin width.** State it in the legend (`plot.bin_edges`). Check that your
  conclusion doesn't depend on it.
- **Normalization.** Say what the y axis is. Counts, proportions and
  densities differ by factors of n and bin width, and density is not a
  probability.
- **Groups.** Prefer overlaid outlines or separate panels over stacked bars.

## Warnings and errors

| Message | What it means |
|---|---|
| `SmallSampleWarning: Fewer than 30 values` | Add `.rug()` (or use a dot plot) so readers see the individual values. |
| `Unknown stat='frequncy'. Did you mean 'frequency'?` | `stat` is one of count, probability, percent, density, frequency. |
| `Unknown bins='freedman'` | Use a number, edges, or a rule name such as `"fd"`. |
| `A log axis needs positive values` | Drop values ≤ 0 before `.log("x")`. |
| `Density curves are not stacked` | Use `multiple="layer"` with `.kde()`. |
| `multiple='dodge' needs element='bars'` | Side-by-side outlines aren't supported. |
| `A cumulative histogram of counts per unit has no clear meaning` | Use another `stat` with `cumulative=True`. |
