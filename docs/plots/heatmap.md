# Heatmaps

`sp.heatmap()` draws a matrix as colored cells: expression across samples,
correlation matrices, any table of numbers. It covers what journal heatmaps
usually need: a colorbar, a sensible colormap, values in the cells, row and
column groups, annotation tracks, z-scoring and clustering.

```python
import numpy as np
import pandas as pd
import SecretPlots as sp

rng = np.random.default_rng(3)
genes = ["GATA4", "NKX2-5", "TBX5", "HAND2", "MYH6", "MYL7",
         "TNNT2", "ACTC1", "CDK1", "MKI67", "TOP2A", "CCNB1"]
samples = ["ctrl1", "ctrl2", "ctrl3", "trt1", "trt2", "trt3"]
values = rng.normal(5, 0.8, (12, 6))
values[:6, 3:] += 2.5          # cardiac genes up with treatment
values[8:, :3] += 1.5          # cell-cycle genes down
expr = pd.DataFrame(values, index=pd.Index(genes, name="gene"), columns=samples)
expr["pathway"] = ["Cardiac TF"] * 4 + ["Sarcomere"] * 4 + ["Cell cycle"] * 4

sp.heatmap(expr).scale("row").groups(rows="pathway")
```

The examples below use `expr`: 12 genes (rows) by 6 samples (columns), plus a
`pathway` column that describes the rows. Like every SecretPlots plot, nothing
is drawn until the plot is displayed, saved, shown, or you access `.fig` / `.ax`.

## Contents

- [Signature](#signature)
- [Input data](#input-data)
- [Colormap and limits](#colormap-and-limits)
- [Colorbar](#colorbar)
- [Values in the cells](#values-in-the-cells)
- [Scaling rows or columns](#scaling-rows-or-columns)
- [Groups](#groups)
- [Annotation tracks](#annotation-tracks)
- [Clustering](#clustering)
- [Masks and missing values](#masks-and-missing-values)
- [Row and column labels](#row-and-column-labels)
- [Size, presets and saving](#size-presets-and-saving)
- [Recipes](#recipes)
- [Journal checklist](#journal-checklist)
- [Warnings and errors](#warnings-and-errors)

## Signature

```text
sp.heatmap(data, x=None, y=None, value=None, *,
           aggfunc="mean", row_order=None, col_order=None, square=False) -> HeatmapPlot
```

| Argument | Meaning |
|---|---|
| `data` | Wide DataFrame (rows × columns), long DataFrame, 2-D array or list of lists. |
| `x`, `y`, `value` | Long table: columns holding the column labels, row labels and values. For a wide table, `y=` names the column with the row labels. |
| `aggfunc` | Long table: how repeated (x, y) pairs combine: `"mean"`, `"median"`, `"sum"` or a function. |
| `row_order`, `col_order` | Explicit order (and selection) of rows / columns. |
| `square` | Square cells. |

Steps specific to heatmaps: `.cmap()`, `.colorbar()`, `.values()`, `.scale()`,
`.groups()`, `.tracks()`, `.cluster()`, `.mask()`, `.ticklabels()`, and
`.source_data()` to get the plotted matrix. Run `sp.HeatmapPlot.options()` for
the full list.

## Input data

A wide table: numeric columns become heatmap columns, the index labels the
rows. Text columns (like `pathway`) are not drawn; you can refer to them by
name in `.groups()` and `.tracks()`.

```python
sp.heatmap(expr)
```

A long ("tidy") table, one row per measurement:

```python
long = expr.drop(columns="pathway").reset_index().melt(
    id_vars="gene", var_name="sample", value_name="TPM"
)
sp.heatmap(long, x="sample", y="gene", value="TPM")
```

Repeated `(sample, gene)` pairs are averaged (`aggfunc="mean"`). The value
column's name becomes the colorbar title.

A matrix of numbers:

```python
sp.heatmap([[1.0, 0.4, 0.1], [0.4, 1.0, 0.7], [0.1, 0.7, 1.0]])
```

## Colormap and limits

The default colormap is the theme's sequential map, a single hue running from
light to dark. Lightness rises steadily, so the map stays readable in
greyscale and for colour-blind readers. With `center=`, or when values are
z-scored, the theme's diverging map is used and the limits become symmetric
around the center.

```python
sp.heatmap(expr).cmap("viridis")                     # any matplotlib name
```

```python
sp.heatmap(expr).cmap("teal")                        # SecretColors palette colour
```

```python
log2fc = expr.drop(columns="pathway").sub(expr["ctrl1"], axis=0)
sp.heatmap(log2fc).cmap("tol_sunset", center=0).colorbar("log2 fold change")
```

| Option | Meaning |
|---|---|
| `name` | SecretColors map (`"blues"`, `"RdBu"`, `"tol_sunset"`, … — `sp.colormaps()` lists them), palette colour (`"teal"`), matplotlib map (`"viridis"`), or a list of colours, low to high. Append `_r` or pass `reverse=True` to flip. |
| `center` | Middle of a diverging map, e.g. `0` for differences or `1` for ratios. |
| `vmin`, `vmax` | Limits. Values outside get the end colour and an arrow on the colorbar. |
| `robust` | Limits from the 2nd–98th percentile, so a few outliers don't wash out the rest. |
| `log` | Logarithmic colour scale. |
| `levels` | Number of discrete colour steps (or their boundaries); easier to read off in print. |

```python
sp.heatmap(expr).cmap("YlGnBu", levels=6)
```

```python
sp.colormaps("diverging")      # name, kind, source, and notes on maps to avoid
```

Rainbow maps (`jet`, `rainbow`, `turbo`, `Spectral`, …) and red–green maps
(`RdYlGn`, …) work but raise a `ColormapWarning`. Their uneven lightness
invents boundaries in the data, and red–green can't be read by about 1 in 12
men. Nature's figure guide and Crameri et al. (2020) both ask authors not to
use them.

## Colorbar

Every heatmap gets a colorbar to the right of the row labels. `.colorbar()`
sets its title, place and ticks:

```python
sp.heatmap(expr).colorbar("Expression (TPM)", position="bottom", ticks=[4, 6, 8])
```

| Option | Meaning |
|---|---|
| `label` | Title: what the colour means, with units. Defaults to the `value` column name, or "Z-score" for scaled data. |
| `position` | `"right"` (default), `"bottom"`, or `False` to hide it. |
| `ticks` | Tick values. |
| `fmt` | Tick format, e.g. `".1f"` or `"{:.0%}"`. |

## Values in the cells

`.values()` prints each cell's value in black or white, whichever reads better
on that cell. The text uses the preset's tick label size, so it never drops
below a journal's minimum (Nature: 5 pt).

```python
sp.heatmap(expr.iloc[:6]).values(".1f")
```

Your own text per cell, such as significance stars, goes in `labels=`. It can
be a DataFrame with the same rows and columns, or a 2-D list in data order.
Empty strings leave a cell blank.

```python
stars = pd.DataFrame("", index=expr.index[:4], columns=samples)
stars.loc["GATA4", "trt1"] = "**"
stars.loc["TBX5", "trt2"] = "*"
sp.heatmap(expr.iloc[:4]).values(labels=stars)
```

If the labels don't fit the cells they are all hidden with a
`LabelsHiddenWarning`; hiding only some would mislead. Use a wider figure or a
shorter format (`".2g"`).

## Scaling rows or columns

Gene-expression heatmaps usually show each gene's pattern across samples
rather than its level. `.scale("row")` z-scores each row (mean 0, standard
deviation 1), switches to the diverging map centered at 0 and titles the
colorbar "Z-score":

```python
sp.heatmap(expr).scale("row")
```

`.scale("col")` scales columns instead, and `method="minmax"` rescales to
0–1. Constant rows have no pattern and are left blank.

## Groups

`.groups()` keeps each group's rows (or columns) together and separates the
groups with a gap. A colour bar marks each group and its name is written
beside it. This is the split heatmap common in journals, like
ComplexHeatmap's `row_split` or pheatmap's `gaps_row` with `annotation_row`.

```python
condition = {s: s.rstrip("123") for s in samples}
sp.heatmap(expr).scale("row").groups(rows="pathway", cols=condition)
```

A group can be given as:

- a column name from your table (`"pathway"`). In a long table this works for
  columns too, and the value must be the same within each row or column;
- a mapping `{row: group}`;
- a Series indexed by row;
- a list in data order.

Groups appear in order of first appearance; use a categorical column to fix
the order.

| Option | Meaning |
|---|---|
| `gap` | Space between groups in pt (default 2; `0` for none). |
| `labels` | Write the group names. |
| `bar` | Draw the colour bar. Colours come from the palette, or set them with `.colors({"Sarcomere": "#e76f51"})`. |

```python
(
    sp.heatmap(expr)
    .scale("row")
    .groups(rows="pathway", gap=4, bar=False)
    .colors({"Cardiac TF": "#264653"})
)
```

## Annotation tracks

Tracks are extra colour bars that describe rows or columns, such as batch,
tissue or genotype, with a legend. Unlike groups they don't reorder anything.
You can add as many tracks as you need:

```python
batch = {s: b for s, b in zip(samples, ["A", "B", "A", "B", "A", "B"])}
(
    sp.heatmap(expr)
    .scale("row")
    .tracks(cols={"Condition": condition, "Batch": batch}, rows={"Pathway": "pathway"})
)
```

Tracks take the same forms as groups. The legend sits under the colorbar;
`.legend(False)` hides it.

## Clustering

`.cluster()` orders rows and columns by hierarchical clustering and draws the
dendrograms. Results match `scipy.cluster.hierarchy.linkage`, but scipy is not
required.

```python
sp.heatmap(expr).scale("row").cluster()
```

Keep columns in order when they are time points or doses, and cut the row
tree into clusters, which get gaps and labels:

```python
sp.heatmap(expr).scale("row").cluster(cols=False, split_rows=3)
```

| Option | Meaning |
|---|---|
| `rows`, `cols` | Which axes to cluster. |
| `method` | `"average"` (default), `"complete"` (pheatmap's default), `"single"` or `"ward"`. |
| `metric` | `"euclidean"` (default), `"correlation"` (1 − Pearson r) or `"cosine"`. |
| `dendrogram` | Draw the trees. |
| `split_rows`, `split_cols` | Cut a tree into this many clusters. |

With `.groups()`, each group is clustered on its own and keeps its place:

```python
sp.heatmap(expr).scale("row").groups(rows="pathway").cluster(cols=False)
```

Clustering runs on the values as drawn, so after `.scale()`. It needs complete
data; drop or fill missing values first.

## Masks and missing values

Missing values (NaN) are drawn in the theme's muted grey. `.mask()` leaves
cells blank instead, for example the redundant half of a correlation matrix:

```python
corr = expr.drop(columns="pathway").T.corr()
sp.heatmap(corr, square=True).mask("upper").cmap(center=0).colorbar("Pearson r")
```

`"upper"` or `"lower"` hides that triangle; add `diagonal=True` to hide the
diagonal too. A boolean matrix (`True` = hide) masks any cells you choose.

Thin lines between cells help readers see where one cell ends; they come from
the theme field `cell_edge_width`:

```python
sp.heatmap(expr.iloc[:6]).theme(cell_edge_width=1).values(".1f")
```

## Row and column labels

Row labels sit to the right of the cells and column labels below them.
Column labels turn vertical when they are too wide. When there are too many
rows for readable labels, they are hidden with a `LabelsHiddenWarning`.
Instead you can label only the rows that matter, rename labels, or turn them
off:

```python
big = pd.DataFrame(rng.normal(size=(300, 6)), columns=samples,
                   index=[f"gene{i}" for i in range(300)])
big = big.rename(index={"gene7": "NKX2-5", "gene150": "MYH6"})
sp.heatmap(big).scale("row").cluster(cols=False).ticklabels(rows=["NKX2-5", "MYH6"])
```

```python
sp.heatmap(expr).ticklabels(cols={"ctrl1": "Control 1"}, italic=True)   # italic gene names
```

```python
sp.heatmap(big).ticklabels(rows=False)            # no row labels, no warning
```

`.highlight("GATA4", "TBX5")` makes those labels bold and mutes the rest.

## Size, presets and saving

Sizes, presets, themes, chrome and saving work as for every plot:

```python
(
    sp.heatmap(expr)
    .scale("row")
    .groups(rows="pathway")
    .cluster(cols=False)
    .labels(x="", y="")
    .preset("nature", width="double")
)
```

Heatmaps with more than 5,000 cells are rasterized inside PDF and SVG files,
so the file stays small, while text and lines stay vector.
`plot.source_data()` returns the matrix as drawn (scaled, ordered, masked) for
a journal's source-data file.

## Recipes

Differential expression, row z-scores, clusters cut into three, with sample
groups on top:

```python
(
    sp.heatmap(expr)
    .scale("row")
    .cluster(cols=False, split_rows=3)
    .groups(cols=condition)
    .ticklabels(italic=True)
    .labels(x="", y="")
)
```

Correlation matrix with values:

```python
(
    sp.heatmap(corr.iloc[:6, :6], square=True)
    .mask("upper", diagonal=True)
    .cmap("RdBu", center=0, vmin=-1, vmax=1)
    .values(".2f")
    .colorbar("Pearson r")
    .labels(x="", y="")
)
```

Confusion matrix with counts:

```python
confusion = pd.DataFrame(
    [[48, 2, 0], [5, 40, 5], [1, 3, 46]],
    index=pd.Index(["cat", "dog", "fox"], name="True"),
    columns=pd.Index(["cat", "dog", "fox"], name="Predicted"),
)
sp.heatmap(confusion, square=True).values(".0f").colorbar("Images")
```

## Journal checklist

- **Colour scale.** Use a sequential map for magnitudes and a diverging map
  only when the midpoint means something (0, or 1 for ratios). Avoid rainbow
  and red–green maps (Nature figure guide; Crameri et al. 2020). SecretPlots
  warns about them.
- **Colorbar.** Always include one, with a title and units. Arrow ends show
  values that were clipped by `vmin`/`vmax`/`robust`.
- **Text.** Cell values and labels use the preset's text sizes, so they stay
  within the journal's limits.
- **Order.** State how rows and columns are ordered (clustering method and
  metric, or groups) in the figure legend. One dendrogram order is only one of
  many possible orders.
- **Source data.** `plot.source_data()` gives the plotted numbers.

## Warnings and errors

| Message | What it means |
|---|---|
| `ColormapWarning: Colormap 'jet' is a rainbow map` | Pick a sequential or diverging map from `sp.colormaps()`. |
| `LabelsHiddenWarning: 300 row labels hidden` | Too many rows to label; use `.ticklabels(rows=[...])` or `rows=False`. |
| `LabelsHiddenWarning: ... cell values hidden` | Values don't fit the cells; widen the figure or shorten the format. |
| `Clustering needs complete data` | Drop or fill missing values before `.cluster()`. |
| `groups: column 'x' has several values for row ...` | A group column must be constant within each row (or column). |
| `columns of a wide table can't be grouped by a column name` | Pass a mapping `{column: group}` for column groups. |
| `Use either .groups(rows=...) or .cluster(split_rows=...)` | Choose one way to split the rows. |
| `A triangle mask needs a square matrix` | Use a boolean mask for non-square data. |
| `cmap(log=True) needs positive values` | Use a linear scale or drop values ≤ 0. |
