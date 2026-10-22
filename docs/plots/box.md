# Box plots

`sp.box()` (alias `sp.boxplot()`) summarizes the values in each category with
the median, the quartiles and whiskers. With a few chained steps you can draw
the individual values on top, mark means, print sample sizes and add
significance brackets with p-values. These are the options that R users get
from ggplot2, ggpubr and ggbeeswarm.

```python
import numpy as np
import pandas as pd
import SecretPlots as sp

rng = np.random.default_rng(4)
df = pd.DataFrame(
    {
        "dose": np.repeat(["0", "10", "50", "100"], 30),
        "weight": np.r_[rng.normal(20, 2, 30), rng.normal(21, 2.5, 30),
                        rng.normal(24, 3, 30), rng.normal(27, 3, 30)],
        "sex": np.tile(["F", "M"], 60),
    }
)

sp.box(df, x="dose", y="weight").points().compare(ref="0")
```

The examples below use `df`: body weight of 30 mice at each of four doses.
Like every SecretPlots plot, nothing is drawn until the plot is displayed,
saved or shown, or until you access `.fig` / `.ax`.

For the shape of a distribution rather than its summary, use
[violin plots and rainclouds](violin.md). They take the same data and the same
steps.

## Contents

- [Signature](#signature)
- [Input data](#input-data)
- [What the box shows](#what-the-box-shows)
- [Groups](#groups)
- [Showing every value](#showing-every-value)
- [Means, sample sizes and reference lines](#means-sample-sizes-and-reference-lines)
- [Significance brackets](#significance-brackets)
- [Figure legend text and source data](#figure-legend-text-and-source-data)
- [Axes, colors, legend and saving](#axes-colors-legend-and-saving)
- [Recipes](#recipes)
- [Journal checklist](#journal-checklist)
- [Warnings and errors](#warnings-and-errors)

## Signature

```text
sp.box(data, x=None, y=None, hue=None, *,
       whis=1.5, notch=False, varwidth=False, fill=True, outliers=None,
       caps=False, edgecolor=None, linewidth=None, orient="v",
       order=None, hue_order=None, missing="raise") -> BoxPlot
```

| Argument | Meaning |
|---|---|
| `missing` | `"raise"` (default), `"drop"`; see [data handling](../usage.md). |
| `data` | A long DataFrame with column names, a wide DataFrame, a dict, a Series, a list or an array; see [Input data](#input-data). |
| `x`, `y`, `hue` | Columns for categories, values and groups. |
| `whis` | Whisker reach: a multiple of the IQR (`1.5`, Tukey), percentiles such as `(5, 95)`, or `"range"`. |
| `notch` | Notches around the median for comparing medians by eye. |
| `varwidth` | Box widths proportional to √n. |
| `fill` | Filled boxes (default) or outlines in the group colour. |
| `outliers` | Draw values beyond the whiskers. Default: yes, unless `.points()` already draws every value. |
| `caps` | Short lines at the whisker ends. |
| `edgecolor` | Colour of the outlines, whiskers and medians (default: a dark shade of the fill). `"none"` removes only the outline. |
| `linewidth` | Outline width in pt; `0` removes it. |
| `orient` | `"v"` (values up) or `"h"` (values to the right). |
| `order`, `hue_order` | Explicit category and group order. |

Steps specific to box and violin plots: `.points()`, `.mean()`, `.show_n()`,
`.refline()`, `.compare()`, `.ticklabels()`, `.grouplabels()`, `.orient()`.
They also have `.test_results()`, `.caption()` and `.source_data()`. Run
`sp.BoxPlot.options()` for the full list.

## Input data

```python
sp.box(df, x="dose", y="weight")                        # long DataFrame
```

```python
sp.box({"control": rng.normal(0, 1, 40),                # dict: one box per key,
        "treated": rng.normal(1, 1, 25)})               # any sizes
```

```python
wide = pd.DataFrame({"WT": rng.normal(5, 1, 20), "KO": rng.normal(7, 1, 20)})
sp.box(wide)                                            # one box per numeric column
```

```python
sp.box(df["weight"])                                    # one distribution
```

```python
sp.box({"liver": {"WT": rng.normal(5, 1, 12), "KO": rng.normal(6, 1, 12)},
        "heart": {"WT": rng.normal(3, 1, 12), "KO": rng.normal(3, 1, 12)}})   # nested: groups
```

Missing and infinite values raise an error by default. Select `missing="drop"`
to ignore affected observations. A categorical `x` column keeps its
category order. Otherwise categories appear in data order unless you pass
`order=`.

## What the box shows

By default the centre line is the median and the box spans the first to third
quartile (the interquartile range, IQR). The whiskers reach the most extreme
values within 1.5 × IQR of the box, and values beyond them are drawn as
points. This is Tukey's rule, also the default in R, ggplot2 and matplotlib.
Quartiles are interpolated linearly (R's default `quantile` type 7).

```python
sp.box(df, x="dose", y="weight", whis=(5, 95))          # whiskers at percentiles
```

```python
sp.box(df, x="dose", y="weight", whis="range")          # min to max, no outliers
```

Notches show median ± 1.58 × IQR / √n (McGill et al. 1978; as R's
`notch = TRUE`). When two boxes' notches don't overlap, the medians differ,
roughly at the 5 % level:

```python
sp.box(df, x="dose", y="weight", notch=True)
```

```python
sp.box(df, x="dose", y="weight", fill=False, caps=True)  # outlined, Prism-style caps
```

With `.log()` the statistics are computed on the log scale, as ggplot2 does,
so whiskers and outliers follow the axis.

## Groups

```python
sp.box(df, x="dose", y="weight", hue="sex")
```

Groups sit side by side within each category and are coloured from the
palette. Rename them with `.grouplabels({"F": "Female", "M": "Male"})`.

## Showing every value

Box plots hide the number and spread of the individual values. Journals ask
authors to show the values when samples are small (Weissgerber et al.,
PLoS Biol 2015). `.points()` draws them on top, and values beyond the
whiskers are then no longer drawn twice:

```python
sp.box(df, x="dose", y="weight").points()
```

| `kind` | Placement | Like |
|---|---|---|
| `"auto"` (default) | A swarm if it fits the box width, else quasirandom. | |
| `"swarm"` | Beeswarm: every dot visible, none overlap. | seaborn `swarmplot`, R `geom_beeswarm` |
| `"quasirandom"` | Spread follows the local density, like a violin. | R `geom_quasirandom` |
| `"jitter"` | Random spread (reproducible through `seed=`). | ggpubr `add = "jitter"` |
| `"strip"` | On the centre line. | |

```python
sp.box(df, x="dose", y="weight").points(kind="jitter", size=2.5, alpha=0.6)
```

On filled boxes the dots take a dark shade of the box colour. On outlined
boxes (`fill=False`) they take the box colour itself. `color=` sets one
colour for all of them.

Each dot has a thin ring in the background colour, which keeps overlapping
dots apart. `edgecolor=` and `linewidth=` change it:

```python
sp.box(df, x="dose", y="weight").points(color="white", edgecolor="black", linewidth=0.6)
```

```python
sp.box(df, x="dose", y="weight").points(linewidth=0)       # no ring
```

The box outline has the same two options on `sp.box()` itself:

```python
sp.box(df, x="dose", y="weight", edgecolor="black", linewidth=1)
```

## Means, sample sizes and reference lines

```python
(
    sp.box(df, x="dose", y="weight")
    .mean()                 # white diamond at each mean
    .show_n()               # "n = 30" under each category label
    .refline(20)            # dashed line, e.g. a baseline
)
```

With `hue`, `.show_n()` lists one n per group, in legend order
(`n = 15, 15`).

`.refline()` works as on every plot (see
[bar plots](bar.md#reference-lines)): lines go across the value axis by
default, `axis="x"` gives vertical lines (a category name puts one through that
box), and each call can have its own `label`, `color`, `linestyle` and
`linewidth`:

```python
(
    sp.box(df, x="dose", y="weight")
    .refline(20, label="baseline")
    .refline(25, label="toxic", color="#da1e28", linestyle=":")
)
```

`label=` is a template with `{n}` where the number goes, in Python's format
syntax, so you can add thousand separators or change the wording. `sep=`
goes between the numbers of several groups:

```python
sp.box(df, x="dose", y="weight").show_n(label="n = {n:,}")     # n = 1,250
```

```python
sp.box(df, x="dose", y="weight").show_n(label="({n})")         # (30)
```

```python
sp.box(df, x="dose", y="weight", hue="sex").show_n(label="{n} mice", sep=" / ")
```

`{n:_}` uses underscores as thousand separators. Write `{{` and `}}` for
literal braces.

## Significance brackets

`.compare()` runs a two-sample test and draws a bracket with the result.
Brackets are stacked so that none of them overlap:

```python
sp.box(df, x="dose", y="weight").compare(ref="0", correction="holm")
```

Choose what to compare:

```python
sp.box(df, x="dose", y="weight").compare(("0", "50"), ("0", "100"))   # chosen pairs
```

```python
sp.box(df, x="dose", y="weight").compare()               # every pair (keep it small)
```

```python
sp.box(df, x="dose", y="weight", hue="sex").compare(("F", "M"))       # within each dose
```

```python
sp.box(df, x="dose", y="weight", hue="sex").compare((("0", "F"), ("100", "F")))
```

| Option | Values |
|---|---|
| `test` | `"mann-whitney"` (default; Wilcoxon rank-sum, R's `wilcox.test`, no normality assumption), `"welch"` (t-test without equal variances) or `"t-test"` (Student's). All are two-sided tests for independent samples. |
| `correction` | `"holm"` or `"bonferroni"` for several comparisons. |
| `format` | `"p"`: exact values (`p = 0.012`, `p < 0.001`), which most journals prefer. `"stars"`: `*` ≤ 0.05, `**` ≤ 0.01, `***` ≤ 0.001, `****` ≤ 0.0001, `ns`. |
| `hide_ns` | Leave out brackets with p > 0.05. |
| `p` | Your own p-values, one per comparison, e.g. from a paired test, an ANOVA post-hoc test or a mixed model. No test is run. |

The tests are built in, so scipy is not needed. Mann–Whitney p-values are
exact for groups of fewer than 50 values without ties, as in R. Larger groups
or groups with ties use the normal approximation with tie and continuity
corrections.

`.test_results()` returns what was computed, for your methods section:

```python
sp.box(df, x="dose", y="weight").compare(ref="0", correction="holm").test_results()
```

For paired data (the same animal before and after), run a paired test
yourself and pass the p-values:

```python
sp.box(df, x="dose", y="weight").compare(("0", "100"), p=[0.004], format="stars")
```

## Figure legend text and source data

Journals ask authors to define the box plot elements in the figure legend.
`.caption()` writes that text for you, from the plot's actual settings:

```python
(
    sp.box(df, x="dose", y="weight")
    .points()
    .compare(ref="0", correction="holm")
    .caption()
)
# 'Box plots show the median (centre line), the first and third quartiles (box
# limits) and the most extreme values within 1.5x the interquartile range of
# the box (whiskers). Dots show individual values. n = 30 per distribution.
# P values: two-sided Mann-Whitney U test, Holm-adjusted for multiple comparisons.'
```

`.source_data()` returns n, mean, SD, minimum, quartiles, maximum, whisker
ends and the number of outliers for each box:

```python
sp.box(df, x="dose", y="weight", hue="sex").source_data()
```

## Axes, colors, legend and saving

These work as for [bar plots](bar.md):

```python
(
    sp.box(df, x="dose", y="weight", hue="sex")
    .colors({"F": "#8d99ae", "M": "#d62828"})
    .labels(x="Dose (mg/kg)", y="Body weight (g)")
    .legend("inside", title="")
    .preset("nature")
)
```

```python
sp.box(df, x="dose", y="weight").highlight("100")       # mute everything else
```

```python
sp.box(df, x="dose", y="weight", orient="h").ticklabels(italic=True)
```

## Recipes

A single-column Nature figure with every value, exact p-values against the
control, and the legend text:

```python
plot = (
    sp.box(df, x="dose", y="weight")
    .points()
    .compare(ref="0", correction="holm")
    .show_n()
    .labels(x="Dose (mg/kg)", y="Body weight (g)")
    .preset("nature")
)
legend_text = plot.caption()
```

The ggpubr look: outlined boxes, jittered points and stars:

```python
(
    sp.box(df, x="dose", y="weight", fill=False)
    .points(kind="jitter")
    .compare(("0", "10"), ("0", "100"), format="stars")
)
```

## Journal checklist

- **Define the elements.** State what the centre line, box limits, whiskers
  and points are. `.caption()` writes this.
- **Show the data when n is small.** Box plots need at least 5 values
  (Krzywinski & Altman, *Nat Methods* 11:119, 2014). SecretPlots warns below
  that. Use `.points()` to show every value.
- **Report n** per box (`.show_n()`).
- **Name the test** and the multiple-comparison correction. Prefer exact
  p-values to stars. Use the right test for paired or repeated measures and
  pass its p-values with `p=`.
- **Never** draw a mean ± SD as a box. Use a [bar plot](bar.md) with error
  bars, or points.

## Warnings and errors

| Message | What it means |
|---|---|
| `SmallSampleWarning: Fewer than 5 values` | Add `.points()` so readers see the individual values. |
| `Cannot compare '5': not a category` | Pair names must be categories, or groups with `hue`. |
| `Got 1 p-values for 2 comparisons` | Pass one p-value per comparison, in order. |
| `A test needs at least 2 values per group` | Too few values to test; drop that comparison. |
| `A t-test needs values that vary within the groups` | All values in both groups are equal. |
| `Unknown whis=...` | Use a number, two percentiles or `"range"`. |
| `A log axis needs positive values` | Drop values ≤ 0 before `.log()`. |
