<p align="center">
  <a href="https://secretplots.readthedocs.io">
    <img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/banner.png" alt="SecretPlots: publication-ready scientific figures in a few readable lines of Python" width="100%">
  </a>
</p>

<h1 align="center">SecretPlots</h1>

<p align="center">
  <b>Publication-ready scientific figures in a few readable lines of Python.</b><br>
  Journal presets · statistics built in · colour-blind-safe palettes · fonts embedded
</p>

<p align="center">
  <a href="https://pypi.org/project/SecretPlots/"><img src="https://img.shields.io/pypi/v/SecretPlots?color=0f8b8d&label=PyPI" alt="PyPI"></a>
  <a href="https://pypi.org/project/SecretPlots/"><img src="https://img.shields.io/pypi/pyversions/SecretPlots?color=5b4fcf" alt="Python versions"></a>
  <a href="https://github.com/secretBiology/SecretPlots/actions/workflows/ci.yml"><img src="https://github.com/secretBiology/SecretPlots/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://secretplots.readthedocs.io"><img src="https://img.shields.io/readthedocs/secretplots?label=docs" alt="Documentation"></a>
  <a href="https://github.com/secretBiology/SecretPlots/blob/master/LICENSE"><img src="https://img.shields.io/github/license/secretBiology/SecretPlots?color=e4572e" alt="MIT license"></a>
</p>

<p align="center">
  <a href="https://secretplots.readthedocs.io"><b>Documentation</b></a> ·
  <a href="https://secretplots.readthedocs.io/en/latest/gallery/">Gallery</a> ·
  <a href="https://secretplots.readthedocs.io/en/latest/publication/">Journal-ready figures</a> ·
  <a href="https://github.com/secretBiology/SecretPlots/blob/master/CHANGELOG.md">Changelog</a> ·
  <a href="https://github.com/secretBiology/SecretPlots/issues">Report a bug</a>
</p>

---

## Same calls, better figure

If you can write matplotlib, you can write SecretPlots. Same data, same figure
size, no styling code on either side:

<table>
<tr>
<th width="50%">matplotlib</th>
<th width="50%">SecretPlots</th>
</tr>
<tr>
<td valign="top">

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 3.7),
                       layout="constrained")
for arm, g in tumours.groupby("arm", sort=False):
    ax.plot(g["day"], g["volume"],
            marker="o", label=arm)
ax.set(xlabel="Day",
       ylabel="Tumour volume (mm³)",
       title="Tumour growth")
ax.legend()
```

</td>
<td valign="top">

```python
import SecretPlots as sp

(
    sp.plot(tumours, x="day", y="volume",
            hue="arm")
    .markers()
    .labels(x="Day",
            y="Tumour volume (mm³)",
            title="Tumour growth")
)
```

</td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/compare-matplotlib.png" alt="Tumour growth curves with matplotlib defaults"></td>
<td><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/compare-secretplots.png" alt="The same curves with SecretPlots defaults"></td>
</tr>
</table>

You get a colour-blind-safe palette, a quiet grid, a titled legend outside the
data and readable type without touching `rcParams`. From there, one more step
labels the lines directly (`.endlabels()`), one argument summarises replicate
animals with confidence bands (`error="ci"`), and one line makes it a journal
figure.

## From table to journal figure

```python
import SecretPlots as sp

sp.use(preset="nature")                         # 89 mm column, 5–7 pt text, 300 dpi

(
    sp.box(cells, x="treatment", y="area")
    .points()                                   # show every cell
    .compare(ref="Control", correction="holm")  # significance brackets
    .colors({"Control": "#BBBBBB", "siRNA": "#EE6677", "siRNA + rescue": "#4477AA"})
    .labels(x="", y="Cell area (µm²)")
    .save("figure1.pdf")                        # fonts embedded, ready to upload
)
```

<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/home-example-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/home-example.png" alt="Box plots of cell area with every cell and Holm-corrected P values" width="48%"></picture>
</p>

## Why SecretPlots?

- **Journal presets.** Nature, Science, Cell, PNAS, AHA, Elsevier, Springer,
  IEEE, ACM and NeurIPS presets set column widths, font limits, dpi and file
  formats from each publisher's author guidelines.
- **Statistics where you need them.** Significance brackets with Holm or
  Bonferroni correction, confidence bands, percentile intervals of the
  observations, linear fits with R², KDEs and hierarchical clustering. Most
  plots return their computed numbers as tables (`.source_data()`,
  `.test_results()`).
- **Every observation visible.** Points over boxes, individual trajectories
  under means, rainclouds and rugs, the patterns reviewers ask for with small
  samples.
- **Colour-blind safe.** Palettes and colormaps come from
  [SecretColors](https://github.com/secretBiology/SecretColors). Unsafe maps are
  flagged, and a `print-bw` theme renders the figure in greys.
- **Readable, chainable API.** One constructor plus small steps.
  `plot.arguments()` lists what the constructor takes, `plot.options()` every
  step, and `plot.options("legend")` explains one.
- **Honest defaults.** Missing data raises instead of being silently dropped.
  Font and palette fallbacks are reported, and `plot.explain("font_size")` says
  where any style value came from.

## Installation

```bash
pip install SecretPlots          # or: uv add SecretPlots
```

Requires Python 3.12+. Depends only on matplotlib, numpy, pandas and SecretColors.

Version 3 is a ground-up rewrite and is not compatible with the 0.1.x
releases; pin `SecretPlots<1` if you depend on the old API.

## Gallery

Every image below is unretouched SecretPlots output at Nature single-column
size. The [gallery](https://secretplots.readthedocs.io/en/latest/gallery/)
has the complete, runnable code for each.

### Compare groups and conditions

<table>
<tr>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-qpcr-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-qpcr.png" alt="Grouped bar chart of qPCR fold change with SD error bars"></picture></td>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-raincloud-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-raincloud.png" alt="Raincloud plot of reaction times"></picture></td>
</tr>
</table>

```python
sp.bar(qpcr, x="gene", y="fold", hue="genotype", error="sd").refline(1, linestyle=":").ticklabels(italic=True)
sp.raincloud(stroop, x="condition", y="rt").compare(ref="Congruent", format="stars")
```

### Follow change over time

<table>
<tr>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-tumour-growth-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-tumour-growth.png" alt="Tumour growth curves with individual animals"></picture></td>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-pharmacokinetics-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-pharmacokinetics.png" alt="Pharmacokinetic curves on a log axis"></picture></td>
</tr>
</table>

```python
sp.line(tumours, x="day", y="volume", hue="arm", units="mouse", error="ci").endlabels().log("y")
sp.line(pk, x="hours", y="conc", hue="dose", error="sd").errorbars("bars").markers().log("y")
```

### Find the pattern in a matrix

<table>
<tr>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-expression-heatmap-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-expression-heatmap.png" alt="Clustered expression heatmap with pathway groups"></picture></td>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-correlation-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-correlation.png" alt="Lower-triangle correlation matrix"></picture></td>
</tr>
</table>

```python
sp.heatmap(expression).scale("row").groups(rows="pathway").cluster(cols=False).tracks(cols={"Condition": condition})
sp.heatmap(cohort.corr(), square=True).mask("upper").cmap("tol_bu_rd", center=0).values(".2f")
```

### Relationships and distributions

<table>
<tr>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-volcano-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-volcano.png" alt="Volcano plot"></picture></td>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-regression-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-regression.png" alt="Scatter plot with linear fits and R²"></picture></td>
</tr>
<tr>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-biomarker-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-biomarker.png" alt="Overlaid density histograms with KDE"></picture></td>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-split-violin-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-split-violin.png" alt="Split violin plots"></picture></td>
</tr>
</table>

```python
sp.scatter(genes, x="lfc", y="log_p", hue="call").refline(-1, 1, axis="x").refline(2, axis="y")
sp.scatter(biopsies, x="bmi", y="lipid", hue="tissue").fit("linear", stats=True)
sp.histogram(serum, x="level", hue="cohort", stat="density").kde().show_n()
sp.violin(behaviour, x="genotype", y="score", hue="sex", split=True, inner="quartiles")
```

### Clinical results

<table>
<tr>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-forest-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-forest.png" alt="Subgroup forest plot with an events table and interaction p-values"></picture></td>
<td width="50%"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-survival-dark.png"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-survival.png" alt="Kaplan-Meier curves with a number-at-risk table and log-rank p-value"></picture></td>
</tr>
</table>

```python
sp.forest(trial, label="subgroup", estimate="hr", lower="lower", upper="upper", group="variable").summary("All patients").table(left={"Drug": "drug"})
sp.survival(patients, time="months", event="died", hue="arm").risk_table().median().pvalue().hazard_ratio()
```

## One figure, any journal

Presets describe where a figure is going; themes describe how it looks. Switch
either one without touching your plotting code:

```python
sp.use(preset="nature")                    # for the whole session
plot.preset("ieee")                        # or for one plot
plot.size(width="double", height="60mm")   # the journal's named widths, or any length
plot.theme("print-bw").encode_groups()     # greyscale with dashes and markers
```

| Kind | Presets |
|---|---|
| Journals | `nature` · `science` · `cell` · `pnas` · `aha` · `elsevier` · `springer` · `ieee` · `acm` · `neurips` |
| Everyday | `screen` (default) · `web` · `a4` · `letter` · `slide-16x9` · `poster` |
| Newsroom | `bbc` · `ft-like` · `economist-like` · `nyt-like` · `wapo-like` |

Journal presets cite the guidelines they were built from. If you set a value
outside a journal's limits, you get a `LimitExceededWarning` instead of a
silent change. Newsroom presets ending in `-like` are inspired by publicly
visible chart conventions; they are not affiliated with those publishers and
use open fallback fonts. You can [write your own preset](https://secretplots.readthedocs.io/en/latest/presets/#make-your-own-preset)
in a few lines of TOML.

## Plot types

| | |
|---|---|
| `sp.bar` | Means, sums or values per category; error bars, groups, stacks, value labels |
| `sp.scatter` | Colour, size and marker encodings; linear and LOWESS fits |
| `sp.line` | Means with CI/SD/SEM/PI bands, fan charts, individual units, end labels |
| `sp.area`, `sp.fill_between` | Stacked and 100% areas, envelopes, split by sign, gradients |
| `sp.histogram` | Counts, percent or density; KDE, rug, cumulative, layered, stacked or dodged |
| `sp.heatmap` | Colormaps, z-scoring, clustering, groups, annotation tracks, masks |
| `sp.forest` | Subgroup and meta-analysis forest plots with tables, sections, summary diamonds, weights and side-by-side panels |
| `sp.survival` | Kaplan-Meier, cumulative incidence and cumulative hazard; risk tables, censor ticks, medians, log-rank tests and hazard ratios |
| `sp.box` | Points, means, sample sizes, significance brackets |
| `sp.violin`, `sp.raincloud` | Split violins, inner box/quartiles, half-violin rainclouds |

## Find any option without leaving Python

No need to open the docs or call `help()`. Every plot type describes itself as a
table you can read or search:

```python
sp.BarPlot.arguments()          # what sp.bar(...) accepts: allowed values, defaults
sp.BarPlot.arguments("error")   # one argument
plot.options()                  # every chainable step for this plot
plot.options("legend")          # one step's parameters, allowed values and defaults
sp.theme_options()              # every style field accepted by .theme(...)
plot.explain("font_size")       # where a style value came from
```

## Development

```bash
uv sync --group dev --group docs
uv run pre-commit install
uv run pytest --mpl                       # tests, including image comparisons
uv run python scripts/render_docs.py      # regenerate documentation figures
uv run mkdocs serve                       # preview the documentation
```

See [CONTRIBUTING.md](https://github.com/secretBiology/SecretPlots/blob/master/CONTRIBUTING.md) for adding presets and documentation.
Bug reports, preset requests and pull requests are very welcome.

## License

MIT © Rohit Suratekar and contributors. Colour palettes and colormaps by
[SecretColors](https://github.com/secretBiology/SecretColors).
