# Scatter plots

`sp.scatter()` draws one marker per row: two numeric columns against each
other, optionally colored by group, sized by a third column, and with a fit
line.

```python
import numpy as np
import pandas as pd
import SecretPlots as sp

rng = np.random.default_rng(1)
age = rng.uniform(25, 75, 60)
sex = rng.choice(["F", "M"], 60)
df = pd.DataFrame(
    {
        "age": age,
        "bp": 95 + 0.6 * age + np.where(sex == "M", 8, 0) + rng.normal(0, 7, 60),
        "sex": sex,
        "bmi": rng.uniform(18, 35, 60),
    }
)

sp.scatter(df, x="age", y="bp", hue="sex").fit("linear")
```

Every example on this page uses the `df` above (age, systolic blood pressure,
sex and BMI for 60 people). Like every SecretPlots plot, nothing is drawn until
the plot is displayed, saved, shown, or you access `.fig` / `.ax`.

## Contents

- [Signature](#signature)
- [Input data](#input-data)
- [Groups](#groups)
- [Marker shape from a column](#marker-shape-from-a-column)
- [Marker size from a column (bubbles)](#marker-size-from-a-column-bubbles)
- [Fit lines](#fit-lines)
- [Marker style](#marker-style)
- [Colors and highlighting](#colors-and-highlighting)
- [Axes, legend, size and saving](#axes-legend-size-and-saving)
- [Recipes](#recipes)
- [Warnings and errors](#warnings-and-errors)

## Signature

```text
sp.scatter(data=None, x=None, y=None, hue=None, *,
           size=None, style=None, hue_order=None, style_order=None,
           missing="raise") -> ScatterPlot
```

| Argument | Meaning |
|---|---|
| `missing` | `"raise"` (default), `"drop"`; see [data handling](../usage.md). |
| `data` | DataFrame or dict of columns, or an array with two columns (x, y). Can be left out; see below. |
| `x`, `y` | Column names of the two numeric variables, or sequences of numbers when `data` is left out. |
| `hue` | Column with groups, drawn in different colors with a legend. |
| `size` | Numeric column that scales marker area, with a size legend. |
| `style` | Column with groups, drawn in different marker shapes with a legend. |
| `hue_order` | Explicit group order (a list). |
| `style_order` | Explicit order of the `style` values, and so of their shapes (a list). |

Chainable steps specific to scatter plots: `.fit()`, `.grouplabels()`. Everything else (labels,
legend, colors, highlight, limits, log axes, presets, themes, saving) works the
same as for [bar plots](bar.md). Run `sp.ScatterPlot.options()` for the full
list.

## Input data

```python
sp.scatter(df, x="age", y="bp")                       # DataFrame + column names
```

```python
sp.scatter(x=[1.2, 2.3, 3.1, 4.8], y=[2.0, 4.1, 5.9, 8.2])   # plain sequences
```

```python
sp.scatter({"dose": [0, 1, 2, 4], "response": [0.1, 0.4, 0.7, 0.9]},
           x="dose", y="response")                    # dict of columns
```

```python
sp.scatter(np.array([[1, 2], [2, 4], [3, 5]]))        # two-column array: x, y
```

```python
sp.scatter(df[["age", "bp"]])                         # exactly two numeric columns
```

Missing or infinite x, y, hue, size or style values raise an error by default.
Select `missing="drop"` to ignore affected rows. Axis titles default
to the column names; plain sequences have none, so add them with `.labels()`.

## Groups

```python
sp.scatter(df, x="age", y="bp", hue="sex")
```

Groups appear in order of first appearance (or the category order of a pandas
`Categorical`). Set it with `hue_order=["M", "F"]`. Rename groups with
`.grouplabels()`, as a list in group order or a mapping `{old: new}`; later
`.colors()` and `.highlight()` calls use the new names. The legend title is the
`hue` column name; change it with `.legend(title="Sex")`:

```python
(
    sp.scatter(df, x="age", y="bp", hue="sex")
    .grouplabels({"M": "Male", "F": "Female"})
    .legend(title="Sex")
)
```

## Marker shape from a column

```python
df["smoker"] = rng.choice(["no", "yes"], 60)
sp.scatter(df, x="age", y="bp", hue="sex", style="smoker")
```

Each `style` value gets its own marker shape. The first value uses the theme's
`marker` (default circle), and the rest follow in this order: square, triangle,
diamond, down-triangle, plus, cross, star. That allows up to 8 values. Set the
order with `style_order=["yes", "no"]`. The legend lists the colors of the
`hue` groups, then the shapes in gray, under the title `hue / style`.

Pass the same column to both arguments when you want each group to have its
own color and shape, for example so the figure still reads in grayscale. The
legend then shows one combined entry per group:

```python
sp.scatter(df, x="age", y="bp", hue="sex", style="sex")
```

`style` changes only the marker shape. Fit lines, colors and `.highlight()`
still follow `hue`.

## Marker size from a column (bubbles)

```python
sp.scatter(df, x="age", y="bp", size="bmi")
```

Marker **area** grows linearly from 0.4× to 3× the theme's `marker_size`
area, from the smallest to the largest value in the column. The legend shows
three reference sizes (smallest, middle, largest). With both `hue` and `size`,
the legend lists the groups, then the sizes, under the title `hue / size`:

```python
sp.scatter(df, x="age", y="bp", hue="sex", size="bmi").legend("right")
```

## Fit lines

`.fit()` adds a fit line; by default a least-squares line with a 95%
confidence band for the mean, one per group:

```python
sp.scatter(df, x="age", y="bp", hue="sex").fit()
```

| Option | Meaning |
|---|---|
| `kind` | `"linear"` (default), `"lowess"`, or `None` to remove the fit. |
| `ci` | Confidence level of the band around a linear fit (default `0.95`); `None` for no band. |
| `per_group` | `True` (default): one fit per `hue` group, in the group's color. `False`: one fit through all points. |
| `frac` | LOWESS only: fraction of points used for each local fit (default `2/3`). Smaller follows the data more closely. |
| `stats` | Linear only: print `y = ax + b, R² = ...` (per group) in the top-left corner. |

```python
sp.scatter(df, x="age", y="bp").fit("linear", ci=0.99, stats=True)
```

```python
sp.scatter(df, x="age", y="bp", hue="sex").fit(per_group=False, ci=None)
```

LOWESS is a local smoother for curved relationships:

```python
x = np.linspace(0, 10, 80)
sp.scatter(x=x, y=np.sin(x) + rng.normal(0, 0.25, 80)).fit("lowess", frac=0.3)
```

Details:

- The confidence band is for the fitted mean (not a prediction interval) and
  uses Student's t with n − 2 degrees of freedom.
- LOWESS uses tricube-weighted local linear fits without robustness
  iterations, so strong outliers still pull the curve.
- A linear fit needs at least 2 distinct x values, its band at least 3 points;
  LOWESS needs at least 3 points.
- A pooled fit (`per_group=False`, or no groups) is drawn in the text color.

## Marker style

Marker look comes from four theme fields:

| Field | Default | Effect |
|---|---|---|
| `marker` | `"o"` | Marker shape, any [matplotlib marker](https://matplotlib.org/stable/api/markers_api.html): `"o"` circle, `"s"` square, `"^"` triangle, `"D"` diamond, `"x"`, `"+"`, ... Line-only shapes (`"x"`, `"+"`) are stroked in the point color at the theme's `line_width`. |
| `marker_size` | 5 | Marker diameter in pt (the base size when `size=` is used). |
| `marker_alpha` | 0.85 | Opacity, 0 to 1. Lower it when points overlap. |
| `marker_edge_width` | 0.5 | Outline width in pt; the outline uses the axes background color so overlapping points stay distinct. |

```python
sp.scatter(df, x="age", y="bp").theme(marker_size=8, marker_alpha=0.5)
```

```python
sp.scatter(df, x="age", y="bp", hue="sex").theme(marker="s")
```

Set them for every plot with `sp.use(...)` in a theme, or for scatter plots only
in a preset's `[plots.scatter]` section.

## Colors and highlighting

```python
sp.scatter(df, x="age", y="bp").colors("#2a9d8f")                       # one color
```

```python
sp.scatter(df, x="age", y="bp", hue="sex").colors({"F": "#e76f51", "M": "#264653"})
```

`alpha=` makes the colors see-through. Markers are already slightly
transparent (`marker_alpha` in the theme), so `alpha=0.5` halves that:

```python
sp.scatter(df, x="age", y="bp").colors(alpha=0.5)
```

`.highlight()` emphasizes groups and mutes the rest (it needs `hue=`):

```python
sp.scatter(df, x="age", y="bp", hue="sex").highlight("M")
```

## Axes, legend, size and saving

These work exactly as for [bar plots](bar.md):

```python
(
    sp.scatter(df, x="age", y="bp", hue="sex")
    .labels(x="Age (years)", y="Systolic BP (mmHg)")
    .legend("inside", loc="lower right", anchor=(0.98, 0.02), title="")
    .xlim(20, 80)
    .preset("nature")
)
```

```python
sp.scatter(x=[1, 10, 100, 1000], y=[3, 30, 280, 3100]).log("xy")
```

Reference lines (see [bar plots](bar.md#reference-lines)) mark thresholds on
either axis, e.g. the limits of normal blood pressure and an age cutoff:

```python
(
    sp.scatter(df, x="age", y="bp", hue="sex")
    .refline(140, label="hypertension", color="#da1e28")
    .refline(50, axis="x", linestyle=":")
)
```

Unlike bar plots, `.labels(x=...)` here always means your `x` column's axis,
since a scatter plot has no orientation. `grid="value"` (the default) draws
horizontal gridlines and `grid="category"` vertical ones; `"both"`, `"x"`,
`"y"` and `"none"` also work.

```python
plot = sp.scatter(df, x="age", y="bp").fit()
plot.save("age_bp.pdf")
```

## Recipes

Correlation with equation, for a single-column journal figure:

```python
(
    sp.scatter(df, x="age", y="bp")
    .fit("linear", stats=True)
    .labels(x="Age (years)", y="Systolic BP (mmHg)")
    .preset("science")
)
```

Treatment effect by group, with a highlighted group and a shared trend:

```python
(
    sp.scatter(df, x="age", y="bp", hue="sex")
    .highlight("F")
    .fit(per_group=False)
    .legend(title="")
)
```

Bubble chart on a log axis:

```python
countries = pd.DataFrame(
    {
        "gdp": [1.2e3, 8.5e3, 2.1e4, 4.6e4, 6.3e4],
        "life": [62, 71, 76, 81, 79],
        "pop": [45, 120, 60, 25, 330],
    }
)
sp.scatter(countries, x="gdp", y="life", size="pop").log("x").labels(
    x="GDP per capita (USD)", y="Life expectancy (years)"
)
```

## Warnings and errors

| Message | What it means |
|---|---|
| `Column 'ages' not found. Available: ...` | Check the column name. |
| `Values in 'sex' must be numeric` | `x`, `y` and `size` must be numbers; groups go in `hue=`. |
| `x='age' / y='bp' look like column names, but no data was given` | Pass the DataFrame first: `sp.scatter(df, x=..., y=...)`. |
| `Pass x= and y= column names` | The DataFrame doesn't have exactly two numeric columns to use automatically. |
| `A confidence band for ... needs at least 3 points` | Use `.fit(ci=None)` or add data. |
| `Unknown fit 'loess'. Did you mean 'lowess'?` | Use `"linear"` or `"lowess"`. |
| `style= has 9 values, but there are only 8 marker shapes` | Use `hue=` for that column, or group the values first. |
| `Unknown marker 'q'` | Set `marker` to a matplotlib marker such as `"o"`, `"s"` or `"^"`. |
| `highlight() picks hue= groups` | Highlighting works on groups; add `hue=`. |
| `PaletteExtendedWarning` | More groups than palette colors; extra shades were generated. |
