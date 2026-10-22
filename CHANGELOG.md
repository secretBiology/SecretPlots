# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Ground-up rewrite (1.0.0a1): themes, presets (journal, news, generic), style
  cascade with provenance, font and palette fallbacks, `sp.bar`.
- `sp.scatter` with groups, marker shapes, sizes and fit lines;
  `.grouplabels()` renames the groups.
- `sp.histogram` (alias `sp.hist`): count / probability / percent / density /
  frequency stats, bin rules and widths, discrete and log bins, layered /
  stacked / dodged groups, cumulative mode, `.kde()`, `.fit("normal")`,
  `.refline()`, `.rug()`, `.show_n()`, `.source_data()`.
- `sp.heatmap`: wide or long input, SecretColors and matplotlib colormaps,
  `center`/`robust`/`log`/discrete levels with auto-extended colorbar, cell
  values with contrast-aware text, row/column z-scoring, groups with gaps,
  colour bars and labels, annotation tracks with legend, hierarchical
  clustering (numpy, no scipy) with dendrograms and tree cuts, masks,
  label subsets, `.source_data()`.
- `sp.colormaps()`, `ColormapWarning` for rainbow and red-green maps,
  `SmallSampleWarning`, theme field `cell_edge_width`; theme `sequential` /
  `diverging` accept a colormap name.
- `sp.box` (alias `sp.boxplot`): Tukey / percentile / range whiskers,
  notches, `varwidth`, filled or outlined boxes, optional caps, groups.
- `sp.violin`: Gaussian KDE with `bw_adjust` / `cut`, `scale` = area / count /
  width, `inner` box / quartiles / median, split and half violins.
  `sp.raincloud`: half violin + box + dots.
- Shared steps for box and violin plots: `.points()` (swarm, quasirandom,
  jitter, strip), `.mean()`, `.show_n()`, `.refline()`, `.compare()`
  significance brackets (Mann-Whitney, Welch, Student; Holm / Bonferroni;
  exact p or stars; your own p-values), `.test_results()`, `.caption()`
  (figure-legend text defining the elements), `.source_data()`.
  `SmallSampleWarning` below 5 values per box (10 per violin) without points.
  `edgecolor=` / `linewidth=` for box and violin outlines and for the
  ring around `.points()` dots. `.show_n(label=..., sep=...)` formats the
  sample sizes (e.g. `"n = {n:,}"`).
- `sp.line` (alias `sp.plot`): lines per group with replicates summarized by
  an estimator; `error=` `"sd"` / `"sem"` / `"ci"` (t interval, bootstrap for
  medians) / `"pi"` or your own `yerr=` / `xerr=`; `.errorbars()` as bands or
  bars, nested levels (fan charts), band edges, caps and dodge; `units=`
  spaghetti lines, `style=` dashes, `.markers()`, `.fill()` with gradient,
  `.caption()`, `.source_data()`.
- `sp.fill_between` (alias `sp.area`): areas to a baseline, bands between two
  columns, stacked and 100 % stacked areas, `.split()` above/below colors,
  `.gradient()`, `.lines()`.
- Shared steps for line and area plots: `.endlabels()` direct labels at the
  line ends (moved apart when they would overlap; `label=` template with
  `{group}` for prefixes or a single line's name, `pad=`; labels clear
  right-side tick labels), `.refline()` on either axis
  (dates too), `.grouplabels()`, `.ticklabels()`. Numeric, date and category x.
- `.refline()` on every plot (bar, scatter, line, area, histogram, heatmap,
  box, violin, raincloud), like matplotlib's `axhline` / `axvline`: `axis="y"`
  or `"x"` (default: the value axis), numbers, dates or category names,
  `label=` (value or your own text), `color=`, `linestyle=`, `linewidth=`.
  Calls add lines; `.refline()` without values removes them. Heatmaps take
  row/column names or edge numbers (gap-aware with `.groups()`).
- Theme field `fill_alpha` (opacity of error bands and filled areas).
- Numpy-only statistics module (`SecretPlots.core.stats`): scipy is not needed.

### Removed
- The 0.1.x API (`BarPlot(data).add_*()`, `NetworkPlot`, `genomics`).
