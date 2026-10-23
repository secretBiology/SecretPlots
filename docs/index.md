---
hide:
  - navigation
  - toc
---

<div class="sp-hero" markdown>

<p class="eyebrow">Python · matplotlib · journal presets</p>

<h1>Figures that are <span class="accent">ready for the paper</span>.</h1>

SecretPlots turns a pandas table into a publication-ready figure in a few
readable lines. It sizes figures to journal columns, keeps text inside the
journal's font limits, embeds the fonts, and adds the statistics reviewers ask
for.

[Make your first figure](quickstart.md){ .md-button .md-button--primary }
[Browse the gallery](gallery.md){ .md-button }

`pip install SecretPlots`

</div>

<div class="sp-banner" markdown>

![Six SecretPlots figures: box plot with significance, clustered heatmap, tumour growth curves, raincloud, volcano plot and regression.](assets/banner.png)

</div>

## Same calls, better figure

If you know matplotlib, you already know most of SecretPlots: `sp.plot` takes
your table and column names, and `.labels()` names the axes. Same data, same
size, no styling code on either side:

```python
import numpy as np
import pandas as pd

days = np.arange(0, 29, 4)
tumours = pd.DataFrame({
    "day": np.tile(days, 3),
    "arm": np.repeat(["Vehicle", "Drug A", "Drug B"], len(days)),
    "volume": np.concatenate(
        [100 * np.exp(rate * days) for rate in (0.08, 0.045, 0.015)]
    ).round(),
})
```

<div class="grid" markdown>

<div markdown>

**matplotlib**

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 3.7), layout="constrained")
for arm, group in tumours.groupby("arm", sort=False):
    ax.plot(group["day"], group["volume"], marker="o", label=arm)
ax.set(xlabel="Day", ylabel="Tumour volume (mm³)", title="Tumour growth")
ax.legend()
fig
```
<!-- figure: compare-matplotlib.png -->

![The tumour growth curves with matplotlib defaults.](assets/figures/compare-matplotlib.png)

</div>

<div markdown>

**SecretPlots**

```python
import SecretPlots as sp

(
    sp.plot(tumours, x="day", y="volume", hue="arm")
    .markers()
    .labels(x="Day", y="Tumour volume (mm³)", title="Tumour growth")
)
```
<!-- figure: compare-secretplots.png -->

![The same curves with SecretPlots defaults: colour-blind-safe palette, light grid, legend outside the data.](assets/figures/compare-secretplots.png)

</div>

</div>

A colour-blind-safe palette, a quiet grid, a titled legend outside the data
and readable type, with no `rcParams`. From here, `.endlabels()` labels the
lines directly, `error="ci"` summarises replicate animals, and
`sp.use(preset="nature")` resizes everything for the journal.

## From table to Nature figure

<div class="grid" markdown>

```python
import numpy as np
import pandas as pd
import SecretPlots as sp

sp.use(preset="nature")   # 89 mm, 5–7 pt, fonts embedded

rng = np.random.default_rng(1)
cells = pd.DataFrame({
    "treatment": np.repeat(["Control", "siRNA", "siRNA + rescue"], 15),
    "area": np.concatenate([rng.normal(m, 45, 15) for m in (420, 290, 400)]),
})

(
    sp.box(cells, x="treatment", y="area")
    .points()
    .compare(ref="Control", correction="holm")
    .colors({"Control": "#BBBBBB", "siRNA": "#EE6677",
             "siRNA + rescue": "#4477AA"})
    .labels(x="", y="Cell area (µm²)")
)
```
<!-- figure: home-example.png -->

![Box plots of cell area with individual cells and Holm-corrected P values.](assets/figures/home-example.png)

</div>

Then call `.save("figure1.pdf")`. The file is 89 mm wide with TrueType fonts
embedded, the format Nature's production team asks for.

## Why SecretPlots?

<div class="grid cards" markdown>

-   :material-ruler-square-compass:{ .lg } **Journal presets**

    ---

    Nature, Science, Cell, PNAS, IEEE, Springer, Elsevier and more: column
    widths, font limits, dpi and formats from the publishers' guidelines.

    [:octicons-arrow-right-24: Journal-ready figures](publication.md)

-   :material-sigma:{ .lg } **Statistics built in**

    ---

    Significance brackets with Holm or Bonferroni correction, confidence
    bands, linear fits with R², KDEs and clustering, with the numbers
    available as tables.

    [:octicons-arrow-right-24: Box plots](plots/box.md)

-   :material-dots-hexagon:{ .lg } **Show every observation**

    ---

    Points over boxes, individual trajectories under means, rainclouds and
    rug plots: the patterns reviewers expect for small samples.

    [:octicons-arrow-right-24: Violin & raincloud](plots/violin.md)

-   :material-palette-swatch-variant:{ .lg } **Colour-blind safe**

    ---

    Palettes and colormaps from [SecretColors](https://github.com/secretBiology/SecretColors),
    with unsafe maps flagged and a greyscale `print-bw` theme.

    [:octicons-arrow-right-24: Presets & themes](presets.md)

-   :material-magnify-scan:{ .lg } **Discoverable**

    ---

    `plot.arguments()` lists what the constructor takes, `plot.options()`
    every step you can chain, and `sp.theme_options()` every style field.
    No need to search the web.

    [:octicons-arrow-right-24: Find any option](options.md)

-   :material-shield-check-outline:{ .lg } **Honest by default**

    ---

    Missing data raises instead of being silently dropped. Font and colour
    fallbacks are reported, and `plot.explain()` says where each style came from.

    [:octicons-arrow-right-24: Data handling](usage.md)

</div>

## Gallery

<div class="sp-mosaic" markdown>

[![](assets/figures/gallery-dose-response.png)<span>Dose response<small>box · points · stats</small></span>](gallery.md#dose-response)
[![](assets/figures/gallery-expression-heatmap.png)<span>Expression heatmap<small>groups · tracks · clusters</small></span>](gallery.md#expression-heatmap)
[![](assets/figures/gallery-tumour-growth.png)<span>Tumour growth<small>units · 95% CI</small></span>](gallery.md#tumour-growth)
[![](assets/figures/gallery-volcano.png)<span>Volcano plot<small>thresholds · highlight</small></span>](gallery.md#volcano-plot)
[![](assets/figures/gallery-raincloud.png)<span>Raincloud<small>density · box · raw data</small></span>](gallery.md#raincloud)
[![](assets/figures/gallery-correlation.png)<span>Correlation matrix<small>masked · annotated</small></span>](gallery.md#correlation-matrix)
[![](assets/figures/gallery-pharmacokinetics.png)<span>Pharmacokinetics<small>log axis · error bars</small></span>](gallery.md#pharmacokinetics)
[![](assets/figures/gallery-split-violin.png)<span>Split violins<small>two factors · quartiles</small></span>](gallery.md#split-violins)
[![](assets/figures/gallery-forest.png)<span>Subgroup analysis<small>forest · table · interaction</small></span>](gallery.md#subgroup-analysis)
[![](assets/figures/gallery-survival.png)<span>Overall survival<small>Kaplan-Meier · risk table · log-rank</small></span>](gallery.md#overall-survival)

</div>

[See all 16 examples with code :octicons-arrow-right-24:](gallery.md){ .md-button }

## Choose a plot

| Your question | Plot | Highlights |
| --- | --- | --- |
| How do groups compare? | [Box](plots/box.md) · [Violin / raincloud](plots/violin.md) | `.points()`, `.compare()`, `.show_n()`, `split=True` |
| What are the means and errors? | [Bar](plots/bar.md) | `error="sd"`, `hue=`, `stack=`, `.values()` |
| How are two variables related? | [Scatter](plots/scatter.md) | `hue=`, `size=`, `.fit("linear", stats=True)` |
| How does a response change over time? | [Line](plots/line.md) | `error="ci"`, `units=`, `.errorbars()`, `.endlabels()` |
| How do parts of a whole evolve? | [Area / fill between](plots/area.md) | `stack="percent"`, `.split()`, `.gradient()` |
| What does a distribution look like? | [Histogram](plots/histogram.md) | `stat="density"`, `.kde()`, `.rug()`, `cumulative=` |
| Where are the patterns in a matrix? | [Heatmap](plots/heatmap.md) | `.scale("row")`, `.cluster()`, `.groups()`, `.tracks()` |
| How large is an effect, and how certain? | [Forest](plots/forest.md) | `group=`, `.table()`, `.summary()`, `panel=` |
| How long until an event happens? | [Survival](plots/survival.md) | `.risk_table()`, `.pvalue()`, `.hazard_ratio()`, `.median()` |
