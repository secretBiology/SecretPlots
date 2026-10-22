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
  <a href="LICENSE"><img src="https://img.shields.io/github/license/secretBiology/SecretPlots?color=e4572e" alt="MIT license"></a>
</p>

<p align="center">
  <a href="https://secretplots.readthedocs.io"><b>Documentation</b></a> ·
  <a href="https://secretplots.readthedocs.io/en/latest/gallery/">Gallery</a> ·
  <a href="https://secretplots.readthedocs.io/en/latest/publication/">Journal-ready figures</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="https://github.com/secretBiology/SecretPlots/issues">Report a bug</a>
</p>

---

```python
import SecretPlots as sp

sp.use(preset="nature")                       # 89 mm column, 5–7 pt text, 300 dpi

(
    sp.box(cells, x="treatment", y="area")
    .points()                                 # show every cell
    .compare(ref="Control", correction="holm")  # significance brackets
    .labels(x="", y="Cell area (µm²)")
    .save("figure1.pdf")                      # fonts embedded, ready to upload
)
```

> **Status:** version 1.0 is a ground-up rewrite and is in **alpha**. APIs may still change.

## Why SecretPlots?

- **Journal presets.** Nature, Science, Cell, PNAS, AHA, Elsevier, Springer,
  IEEE, ACM and NeurIPS presets set column widths, font limits, dpi and file
  formats from each publisher's author guidelines.
- **Statistics where you need them.** Significance brackets with Holm or
  Bonferroni correction, confidence bands, prediction intervals, linear fits
  with R², KDEs and hierarchical clustering. Every number is available as a table.
- **Every observation visible.** Points over boxes, individual trajectories
  under means, rainclouds and rugs, the patterns reviewers ask for with small
  samples.
- **Colour-blind safe.** Palettes and colormaps come from
  [SecretColors](https://github.com/secretBiology/SecretColors). Unsafe maps are
  flagged, and a `print-bw` theme renders the figure in greys.
- **Readable, chainable API.** One constructor plus small steps.
  `plot.options()` lists every step; `plot.options("legend")` explains one.
- **Honest defaults.** Missing data raises instead of being silently dropped.
  Font and palette fallbacks are reported, and `plot.explain("font_size")` says
  where any style value came from.

## Installation

```bash
pip install SecretPlots          # or: uv add SecretPlots
```

Requires Python 3.12+. Depends only on matplotlib, numpy, pandas and SecretColors.

## Gallery

Every image below is unretouched SecretPlots output at Nature single-column
size. The [gallery](https://secretplots.readthedocs.io/en/latest/gallery/)
has the complete, runnable code for each.

### Compare groups, with the statistics

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-dose-response.png" alt="Dose-response box plot with significance stars"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-raincloud.png" alt="Raincloud plot of reaction times"></td>
</tr>
</table>

```python
sp.box(viability, x="dose", y="viability").points().compare(ref="Vehicle", correction="holm", format="stars")
sp.raincloud(stroop, x="condition", y="rt").compare(ref="Congruent", format="stars")
```

### Follow change over time

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-tumour-growth.png" alt="Tumour growth curves with individual animals"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-pharmacokinetics.png" alt="Pharmacokinetic curves on a log axis"></td>
</tr>
</table>

```python
sp.line(tumours, x="day", y="volume", hue="arm", units="mouse", error="ci").endlabels().log("y")
sp.line(pk, x="hours", y="conc", hue="dose", error="sd").errorbars("bars").markers().log("y")
```

### Find the pattern in a matrix

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-expression-heatmap.png" alt="Clustered expression heatmap with pathway groups"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-correlation.png" alt="Lower-triangle correlation matrix"></td>
</tr>
</table>

```python
sp.heatmap(expression).scale("row").groups(rows="pathway").cluster(cols=False).tracks(cols={"Condition": condition})
sp.heatmap(cohort.corr(), square=True).mask("upper").cmap("tol_bu_rd", center=0).values(".2f")
```

### Relationships and distributions

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-volcano.png" alt="Volcano plot"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-regression.png" alt="Scatter plot with linear fits and R²"></td>
</tr>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-biomarker.png" alt="Overlaid density histograms with KDE"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/secretBiology/SecretPlots/master/docs/assets/figures/gallery-split-violin.png" alt="Split violin plots"></td>
</tr>
</table>

```python
sp.scatter(genes, x="lfc", y="log_p", hue="call").refline(-1, 1, axis="x").refline(2, axis="y")
sp.scatter(biopsies, x="bmi", y="lipid", hue="tissue").fit("linear", stats=True)
sp.histogram(serum, x="level", hue="cohort", stat="density").kde().show_n()
sp.violin(behaviour, x="genotype", y="score", hue="sex", split=True, inner="quartiles")
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
| `sp.box` | Points, means, sample sizes, significance brackets |
| `sp.violin`, `sp.raincloud` | Split violins, inner box/quartiles, half-violin rainclouds |

## Find any option without leaving Python

```python
plot.options()                  # every chainable step for this plot
plot.options("legend")          # one step's parameters, allowed values and defaults
sp.BarPlot.options("values")    # explore without data
sp.theme_options()              # every style field accepted by .theme(...)
```

## Development

```bash
uv sync --group dev --group docs
uv run pre-commit install
uv run pytest --mpl                       # tests, including image comparisons
uv run python scripts/render_docs.py      # regenerate documentation figures
uv run mkdocs serve                       # preview the documentation
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for adding presets and documentation.
Bug reports, preset requests and pull requests are very welcome.

## License

MIT © Rohit Suratekar and contributors. Colour palettes and colormaps by
[SecretColors](https://github.com/secretBiology/SecretColors).
