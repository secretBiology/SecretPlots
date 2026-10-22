# Bar plots

`sp.bar()` draws one bar per category. When a category has several rows
(replicates), they are summarized into one value, with optional error bars.

```python
import pandas as pd
import SecretPlots as sp

df = pd.DataFrame(
    {
        "gene": ["GATA4", "NKX2-5", "TBX5", "HAND2"] * 6,
        "tpm": [12, 8, 15, 4, 13, 9, 14, 5, 11, 7, 16, 4] * 2,
        "sample": ["ctrl"] * 12 + ["treated"] * 12,
    }
)

sp.bar(df, x="gene", y="tpm", hue="sample", error="sd")
```

Every example on this page uses the `df` above. Nothing is drawn until the plot
is displayed in a notebook, saved, shown, or you access `.fig` / `.ax`, so you
can chain as many steps as you like.

## Contents

- [Signature](#signature)
- [Input data](#input-data)
- [Summary value and error bars](#summary-value-and-error-bars)
- [Groups: side by side or stacked](#groups-side-by-side-or-stacked)
- [Order and sorting](#order-and-sorting)
- [Horizontal bars](#horizontal-bars)
- [Value labels](#value-labels)
- [Category and group names](#category-and-group-names)
- [Colors and highlighting](#colors-and-highlighting)
- [Axes: titles, limits, log scale](#axes-titles-limits-log-scale)
- [Reference lines](#reference-lines)
- [Legend](#legend)
- [Headline, subtitle, source and note](#headline-subtitle-source-and-note)
- [Size, presets and themes](#size-presets-and-themes)
- [Saving and output](#saving-and-output)
- [Discovering options](#discovering-options)
- [Warnings and errors](#warnings-and-errors)

## Signature

```text
sp.bar(data, x=None, y=None, hue=None, *,
       stack=False, error=None, estimator="mean", orient="v",
       sort=None, order=None, hue_order=None) -> BarPlot
```

| Argument | Meaning |
|---|---|
| `data` | Your data; see [Input data](#input-data). |
| `x` | Column with the categories (one bar, or one cluster of bars, each). |
| `y` | Column with the numeric values. Required when `data` is a long DataFrame. |
| `hue` | Column with the groups (colored bars within each category). |
| `stack` | `True` stacks groups on top of each other instead of side by side. |
| `error` | Error bars from replicates: `"sd"` (standard deviation) or `"sem"` (standard error of the mean). |
| `estimator` | Bar height: `"mean"` (default), `"median"`, `"sum"`, or any function of the values, e.g. `np.max`. |
| `orient` | `"v"` vertical (default) or `"h"` horizontal bars. |
| `sort` | `"desc"` / `"asc"` orders categories by value; `None` keeps data order. |
| `order` | Explicit category order (a list). |
| `hue_order` | Explicit group order (a list). |

`x`, `y` and `hue` always name **data columns**. Which side of the plot they end
up on depends on `orient`.

## Input data

A long ("tidy") DataFrame with column names is the most explicit form:

```python
sp.bar(df, x="gene", y="tpm")
```

Without column names, these shapes are understood:

```python
# dict: one value per category
sp.bar({"GATA4": 12, "NKX2-5": 8, "TBX5": 15})
```

```python
# dict of lists: replicates per category (summarized, so error bars work)
sp.bar({"GATA4": [12, 13, 11], "NKX2-5": [8, 9, 7]}, error="sem")
```

```python
# nested dict: categories -> groups
sp.bar({"GATA4": {"ctrl": 12, "treated": 13}, "TBX5": {"ctrl": 15, "treated": 14}})
```

```python
# Series: index -> categories, values -> bars
sp.bar(pd.Series({"GATA4": 12, "NKX2-5": 8}, name="tpm"))
```

```python
# wide DataFrame: index -> categories, numeric columns -> groups
wide = df.pivot_table(index="gene", columns="sample", values="tpm")
sp.bar(wide)
```

```python
# flat list: categories are 0, 1, 2, ... (rename them with .ticklabels)
sp.bar([3, 5, 2]).ticklabels(["a", "b", "c"])
```

```python
# list of equal-length lists / 2-D array: rows -> categories, columns -> groups
sp.bar([[1, 2], [3, 4], [5, 6]]).grouplabels(["ctrl", "treated"])
```

Category and group order follows the order of first appearance in your data,
or the category order of a pandas `Categorical` column.

## Summary value and error bars

When a category (or category + group) has several rows, `estimator` decides the
bar height and `error` adds error bars computed from the same rows.

```python
sp.bar(df, x="gene", y="tpm", error="sd")                  # mean ± SD
```

```python
sp.bar(df, x="gene", y="tpm", estimator="median")          # median, no error bars
```

```python
import numpy as np

sp.bar(df, x="gene", y="tpm", estimator=np.max)            # any function works
```

- `error="sd"` uses the sample standard deviation (`ddof=1`); `error="sem"` is
  SD / √n.
- Error bars need replicates. If every bar has a single value, `error=` raises
  an error explaining that.
- Common spellings from other tools (`"std"`, `"se"`, `"stderr"`) are rejected
  with a hint to the right name, and so is putting an error kind in
  `estimator=`.
- Error bars on stacked bars are not allowed (they would be misleading).

## Groups: side by side or stacked

`hue=` splits every category into colored groups, shown side by side:

```python
sp.bar(df, x="gene", y="tpm", hue="sample", error="sem")
```

`stack=True` stacks them instead. Positive values stack upward and negative
values downward.

```python
sp.bar(df, x="gene", y="tpm", hue="sample", stack=True)
```

Reorder groups with `hue_order=`:

```python
sp.bar(df, x="gene", y="tpm", hue="sample", hue_order=["treated", "ctrl"])
```

A legend is added automatically when there are groups; see [Legend](#legend).

## Order and sorting

```python
sp.bar(df, x="gene", y="tpm", order=["TBX5", "GATA4", "NKX2-5", "HAND2"])
```

```python
sp.bar(df, x="gene", y="tpm").sort("desc")   # tallest first; same as sort="desc"
```

`.sort("asc")` puts the smallest first and `.sort(None)` returns to data order.
With groups, categories are ranked by their tallest bar; with `stack=True`, by
their stack total.

## Horizontal bars

```python
sp.bar(df, x="gene", y="tpm", orient="h")
```

or, on an existing plot, `.orient("h")`. Horizontal bars suit long category
names. The first category is drawn at the top.

With `orient="h"` the values run along the plot's x axis. Methods that talk
about axes (`.labels()`, `.xlim()`, `.ylim()`, `.log()`) always mean **the axes
as drawn**, so for horizontal bars the value axis is `x`:

```python
sp.bar(df, x="gene", y="tpm", orient="h").labels(x="TPM", y="").xlim(0, 20)
```

## Value labels

`.values()` prints each bar's value using a Python format spec:

```python
sp.bar(df, x="gene", y="tpm").values(".1f")
```

```python
shares = {"A": 0.42, "B": 0.35, "C": 0.23}
sp.bar(shares).values("{:.0%}")               # full format strings work too
```

- Labels sit just past the end of each bar (above the error bar, if any).
- Stacked bars get labels **inside** each segment. Force either placement with
  `.values(inside=True)` or `.values(inside=False)`.
- Inside labels switch between dark and white text for contrast with the bar
  color.
- Labels that don't fit their bar are hidden, and a `LabelsHiddenWarning` tells
  you how many. Try a wider figure, a shorter format (`".2g"`), or horizontal
  bars.

```python
sp.bar(df, x="gene", y="tpm", hue="sample", orient="h").values(inside=True)
```

## Category and group names

`.ticklabels()` renames categories and styles their labels; `.grouplabels()`
renames groups (the legend entries). Both take a list in data order or a
partial mapping `{old: new}`:

```python
(
    sp.bar(df, x="gene", y="tpm", hue="sample")
    .ticklabels({"NKX2-5": "Nkx2-5"}, italic=True)
    .grouplabels({"ctrl": "Control", "treated": "Treated"})
)
```

Renaming changes the categories themselves, so later calls such as
`.highlight()` and `.colors({...})` use the **new** names.

Long category labels on vertical bars are rotated automatically (45°, or 90° if
space is very tight). `.ticklabels(rotation=30)` sets the angle yourself and
turns off the automatic rotation.

## Colors and highlighting

```python
sp.bar(df, x="gene", y="tpm").colors("#2a9d8f")                 # one color
```

```python
sp.bar(df, x="gene", y="tpm", hue="sample").colors(["#264653", "#e9c46a"])  # palette
```

```python
sp.bar(df, x="gene", y="tpm", hue="sample").colors({"treated": "#e76f51"})  # by name
```

```python
sp.bar(df, x="gene", y="tpm").colors("#2a9d8f", alpha=0.6)      # see-through
```

- Without groups, a mapping colors individual categories; with groups, it
  colors groups.
- If there are more groups than palette colors, extra shades are generated and
  a `PaletteExtendedWarning` says so.

`.highlight()` emphasizes some categories (or groups) and mutes the rest:

```python
sp.bar(df, x="gene", y="tpm").sort().highlight("TBX5")
```

```python
sp.bar(df, x="gene", y="tpm", hue="sample").highlight("treated")
```

The highlight and muted colors come from the theme (`highlight`, `muted`).

## Axes: titles, limits, log scale

Axis titles default to your column names. Override or hide them with
`.labels()`; `""` hides one:

```python
sp.bar(df, x="gene", y="tpm").labels(x="", y="Expression (TPM)", title="Cardiac TFs")
```

Hide all automatic axis titles with `.theme(axis_titles=False)`; titles you set
with `.labels()` still show.

```python
sp.bar(df, x="gene", y="tpm").ylim(0, 20)
```

```python
sp.bar(df, x="gene", y="tpm").log("y")
```

`.xlim()` / `.ylim()` take `(low, high)`; pass `None` for an end to keep it
automatic. Remember these are axes as drawn (see
[Horizontal bars](#horizontal-bars)).

## Reference lines

`.refline()` draws lines across the whole plot, like matplotlib's `axhline`
and `axvline`: a target, a baseline, a threshold. Every plot type has it and
it works the same way everywhere.

```python
sp.bar(df, x="gene", y="tpm").refline(10)                  # horizontal line at 10
```

```python
sp.bar(df, x="gene", y="tpm").refline("TBX5", axis="x")    # vertical, through a bar
```

```text
.refline(*values, axis=None, label=False, color=None, linestyle="--", linewidth=None)
```

| Option | Effect |
|---|---|
| `*values` | Where the lines go: numbers, dates (on a date axis, also text like `"2024-03-01"`), or category names (on a category axis). |
| `axis` | `"y"`: horizontal lines (`axhline`); `"x"`: vertical lines (`axvline`). Axes as drawn. Default: the value axis (see below). |
| `label` | `True` writes the value next to each line; text (e.g. `"target"`) writes that text instead, one value per call. |
| `color` | Line color; default: the theme's text color. |
| `linestyle` | `"--"` (default), `":"`, `"-."` or `"-"`. |
| `linewidth` | Width in pt; default: the theme's `axis_line_width`. |

Each call adds lines, so lines can differ in style. `.refline()` with no values
removes them all; `.refline(axis="x")` removes only the vertical ones.

```python
(
    sp.bar(df, x="gene", y="tpm", hue="sample")
    .refline(10, label="target", color="#da1e28")
    .refline(5, label="detection limit", linestyle=":")
)
```

Without `axis=`, lines go across the **value axis**:

| Plot | Default `axis` |
|---|---|
| bar, box, violin, raincloud | `"y"`, or `"x"` with `orient="h"` |
| scatter, line, area | `"y"` |
| histogram | the binned axis: `"x"`, or `"y"` with `orient="h"` |
| heatmap | none: say `axis="y"` (rows) or `axis="x"` (columns) |

On a category axis a name puts the line through that category's center,
wherever sorting has moved it:

```python
sp.bar(df, x="gene", y="tpm", sort="desc").refline("HAND2", axis="x", label=True)
```

Horizontal bars swap the axes, so the value axis is `"x"`:

```python
sp.bar(df, x="gene", y="tpm", orient="h").refline(10).refline("TBX5", axis="y")
```

On bars, histograms and heatmaps the lines are drawn above the marks so they
stay visible; on points, lines, boxes and violins they sit behind the data.

## Legend

```python
sp.bar(df, x="gene", y="tpm", hue="sample").legend("right", title="Condition")
```

| Option | Meaning |
|---|---|
| `position` | `"auto"` (top for up to 4 groups or narrow figures, else right), `"top"`, `"right"`, `"inside"` (emptiest spot in the axes), or `False`/`"none"` to hide it. |
| `title` | Legend title; defaults to the `hue` column name. `""` hides it. |
| `ncols` | Fixed number of columns. Without it, a top legend wraps to fit the figure. |
| `fontsize` | Text size in pt. |
| `loc` | Which corner of the legend to place (`"upper right"`, `"center left"`, ...). |
| `anchor` | `(x, y)` in axes fractions where that corner sits; `(0, 0)` is the bottom-left of the plot area. |

```python
sp.bar(df, x="gene", y="tpm", hue="sample").legend(
    "inside", loc="upper left", anchor=(0.02, 0.98), fontsize=7
)
```

Outside legends (`"top"`, `"right"`) automatically move past tick labels and
axis titles on their side. Each `.legend()` call resets the options it doesn't
pass. A plot title from `.labels(title=...)` moves a top legend to the right.

## Headline, subtitle, source and note

`.chrome()` adds text around the whole figure, the way news graphics do:

```python
sp.bar(df, x="gene", y="tpm").chrome(
    title="TBX5 is the most expressed cardiac TF",
    subtitle="Mean TPM ± SD, n = 3",
    source="RNA-seq, batch 4",
    note="HAND2 below detection in one replicate",
)
```

Each call only changes the fields you pass. Chrome is drawn only when
SecretPlots creates the figure (not with `.render(ax=...)`). Journal figures
usually leave it off, since the caption carries that text.

## Size, presets and themes

```python
sp.bar(df, x="gene", y="tpm").preset("nature", width="double")
```

A preset sets the figure size and the publisher's limits (text sizes, line
widths, fonts). See [Presets](../presets.md) for the list, or
`sp.presets.list()`. `sp.use(preset="nature")` makes it the default for every
plot.

```python
sp.bar(df, x="gene", y="tpm").size("120mm", "80mm")
```

Widths can be a preset width name (`"single"`, `"double"`), a number in inches,
or text such as `"89mm"`, `"8.9cm"`, `"3.5in"`, `"600px"`. Without a height,
the preset's aspect ratio is used. Text keeps its point size when you resize;
`.size(..., scale_text=True)` grows it with the width instead.

`.theme()` switches theme and/or overrides individual style fields. Fields that
matter most for bar plots:

| Field | Effect |
|---|---|
| `bar_gap` | Empty fraction of each category slot, 0 to 1. |
| `bar_edge_width` | Outline width around bars in pt (outline uses the axes background color). |
| `errorbar_capsize` | Error bar cap length in pt. |
| `grid` | `"value"` / `"category"` follow the bars when you switch orientation; also `"x"`, `"y"`, `"both"`, `"none"`. |
| `value_axis_side` | Draw the value axis on the `"left"` (default) or `"right"` (top for horizontal bars). |
| `spines` | Which axis lines to draw, e.g. `["left", "bottom"]` (swapped automatically for horizontal bars). |

```python
sp.bar(df, x="gene", y="tpm").theme("dark", bar_gap=0.3, grid="value")
```

`sp.theme_options()` lists every field with its allowed values.

Values you set yourself win over a preset's limits. For example, `font_size=12`
under `nature` (5–7 pt) is kept, and a `LimitExceededWarning` says which limits
it breaks. Set `sp.config.enforce_limits = True` to have limits applied
instead, and `sp.config.strict = True` to turn every SecretPlots warning into
an error (useful in CI before submission).

## Saving and output

```python
plot = sp.bar(df, x="gene", y="tpm", error="sd").preset("nature")
plot.save("fig1.pdf")
```

- `.save(path, dpi=None, **kwargs)` uses the preset's dpi and embeds fonts as
  TrueType in PDF/PS. Extra keyword arguments go to matplotlib's `savefig`.
  Saving in a format the preset's publisher doesn't list gives a
  `FormatWarning`.
- `.show()` opens a window (or displays inline) through pyplot.
- In Jupyter, a plot at the end of a cell displays itself.
- `.fig` and `.ax` give the matplotlib `Figure` / `Axes` for anything not
  covered here:

```python
plot = sp.bar(df, x="gene", y="tpm")
plot.ax.axhline(10, color="grey", linestyle="--")
plot.save("with_threshold.png")
```

- `.render(ax=...)` draws into an axes you created, e.g. one panel of a
  multi-panel figure:

```python
import matplotlib.pyplot as plt

fig, (left, right) = plt.subplots(1, 2, figsize=(7, 3), layout="constrained")
sp.bar(df, x="gene", y="tpm").render(ax=left)
sp.bar(df, x="gene", y="tpm", hue="sample").render(ax=right)
plt.close(fig)
```

## Discovering options

Every chainable step documents itself:

```python
plot = sp.bar(df, x="gene", y="tpm")
plot.options()            # all steps you can chain, with a summary
```

```python
plot.options("values")    # one step's options, allowed values and defaults
```

`plot.explain("palette")` tells you where a style value came from (your
settings, a preset, a theme), and `plot.style_report()` lists every resolved
value plus any adjustments made for the preset.

## Warnings and errors

| Message | What it means |
|---|---|
| `error='sd' needs replicates ...` | Every bar has one value; there is nothing to compute an SD from. |
| `Unknown error='std'. Did you mean error='sd'?` | Use `"sd"` or `"sem"`. |
| `estimator='sd' looks like an error bar` | `estimator` sets bar height; use `error=` for error bars. |
| `Error bars on stacked bars are misleading` | Drop `error=` or use side-by-side groups. |
| `Column 'genes' not found. Available: ...` | Check the column name. |
| `Values in 'tpm' must be numeric` | The `y` column has text in it. |
| `Cannot highlight [...]: not in the data` | Names are case-sensitive and follow `.ticklabels()` renames. |
| `LabelsHiddenWarning` | Some value labels didn't fit their bars and were hidden. |
| `PaletteExtendedWarning` | More groups than palette colors; extra shades were generated. |
| `LimitExceededWarning` | A value you set breaks the preset's limits and was kept. |
| `FormatWarning` | The file format isn't one the preset's publisher lists. |
