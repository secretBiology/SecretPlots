# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [3.0.0] - 2026-10-23

First stable release of the 3.x rewrite. Install with `pip install SecretPlots`
(no `--pre` needed).

### Added
- `Plot.arguments()`: the constructor's arguments as a table (allowed values,
  defaults, descriptions), next to `.options()` for chainable steps and
  `sp.theme_options()` for style fields. `sp.BarPlot.arguments("error")` or
  `plot.arguments("error")` shows one argument; misspellings get a suggestion.
- `sp.survival`: Kaplan-Meier curves (`kind="survival"`), cumulative
  incidence (`"failure"`) and the Nelson-Aalen cumulative hazard (`"cumhaz"`)
  from one row per subject, computed with numpy only (R `survival`
  conventions). Confidence bands (`.ci()`: log-log, log or plain Greenwood
  intervals), censoring ticks (`.censors()`), median guides (`.median()`),
  and a number-at-risk table aligned with the time ticks (`.risk_table()`,
  with optional cumulative events and censorings). `.pvalue()` runs log-rank,
  Gehan-Breslow-Wilcoxon, Tarone-Ware, Peto-Peto and Fleming-Harrington tests,
  stratified (`strata=`), for trend or pairwise with Holm/Bonferroni
  correction, or writes your own p-value; `.hazard_ratio()` fits a Cox model
  with the group as the only covariate (Efron ties, stratified) or writes
  your own (e.g. adjusted) ratios; `.annotate()` adds free text.
  `.statistics()` (medians with CIs), `.test_results()` and `.source_data()`
  return the numbers.
- `sp.forest`: forest plots for subgroup analyses, meta-analyses and
  regression models. Ratio (log axis, no effect at 1) or difference scales
  with journal-style ticks; an "estimate (95% CI)" column; `.table()` columns
  left and right with per-column formats (including `"p"` for p-values) and
  `{group: value}` header-row values such as P for interaction; `group=`
  sections with bold headers and indents (`.groups()`); `.summary()` diamonds;
  `weight=` marker areas; `hue=` dodged estimates with a legend; `panel=`
  side-by-side forests sharing row labels; `.null()` to move, style or
  label the line of no effect (e.g. a non-inferiority margin);
  `.favours()` direction arrows,
  `.stripes()` (every other row or, with `by="group"`, every other section),
  `.dividers()` (styled rules between sections or rows), `.markers()`,
  arrowheads for intervals beyond `.xlim()` (ticks follow the new range;
  non-positive limits on a log axis raise), `.xticks()` for exact ticks,
  `log=False` for ratios on a linear axis;
  height that grows with the rows; `.source_data()`.
- `.refline()`: `label_position` (`"start"`, `"center"`, `"end"`) places
  the label along the line, `label_side` puts it on either side (`"left"`/
  `"right"` of a vertical line, `"above"`/`"below"` a horizontal one), and
  `label_rotation` turns it (e.g. `90` to run it up a vertical line).

### Changed
- `PolicyWarning`: new warning for deliberate rules that change what you asked
  for; each message says what was done, why, and how to opt out.
- Box notches are drawn at their full width (median +/- 1.58 x IQR / sqrt(n)),
  even past the box, as in R and matplotlib; a `SmallSampleWarning` explains
  folded notches. They were clipped to the quartiles, which narrowed them.
- Forest `weight=` markers have area exactly proportional to weight; zero
  weights draw no marker. The old minimum size is now opt-in with
  `.markers(min_size=...)`.
- Stacked areas stack positive values up and negative values down from the
  baseline, like stacked bars; series that change sign get a warning.
- `.source_data()` keeps your column names; generated columns that clash get
  a `_computed` suffix instead of overwriting them.
- `test="wilcoxon"` / `"wilcox"` are rejected as ambiguous (rank-sum or
  signed-rank); use `"mann-whitney"` or `"wilcoxon-rank-sum"`.
- Size overrides passed to methods (`.legend(fontsize=)`, `linewidth=`...)
  are checked against preset limits like theme fields.
- Explicit hue order levels without data keep their colour and position but
  are skipped by fits, curves and tests, with a warning.
- `whis=math.inf` is accepted as `"range"`.

### Fixed
- Percentile error bars no longer crash when the estimate lies outside the
  interval, and they draw the actual interval.
- LOWESS no longer returns NaN when the nearest neighbours sit exactly at the
  cutoff distance.
- Euclidean clustering is stable for data with a large common offset.
- A count/probability/percent curve over unequal bins is rejected instead of
  drawn at the wrong scale.
- Significance brackets are spaced by text height, so labels no longer
  collide with the bracket above; a warning says when they cannot fit.
- Strict mode raises even for warnings already shown in the session.
- `fill_alpha=0` is kept instead of becoming 0.22; alpha in palette colours
  is kept.
- Percent stacks with a nonzero baseline are rejected instead of clipped.
- Theme fields, `bw_adjust`, `cut`, `whis`, `.refline()` and `.log()` reject
  NaN, negative or out-of-range values.
- Student t quantile at df = 1 is accurate in the far tails.

## [3.0.0a1] - 2026-10-22

### Changed
- Missing/non-finite input now raises `DataShapeError` by default in every plot
  constructor. Opt into `missing="drop"`, or `missing="gap"` for lines, areas and
  heatmaps. Empty categorical levels are omitted and duplicate orders rejected.
- Plots capture the active theme/preset/width at construction, including inside
  `with sp.use(...)`; rendering later keeps that selection.
- Header/footer text wraps to the available figure width. Text that leaves too
  little plotting space raises an actionable error instead of overlapping.
- The default diverging colormap runs blue (low) to red (high).
- Default legend titles are sentence case for lowercase column names
  (`cell_type` -> "Cell type"); names with capitals are kept as written.
- `slide-16x9` and `poster` scale line widths, markers, ticks and error-bar caps
  with their larger text.
- Without `hue`, a list given to `.colors()` colors bars, boxes, violins and
  rainclouds in category order.
- One highlighted `hue` group takes the theme's highlight color, as without
  groups; several highlighted groups keep their own colors.
- Bar, box, violin, raincloud, scatter and histogram signatures type `missing`
  as `sp.DropPolicy` (`"raise"` or `"drop"`).

### Fixed
- Line group renaming rebuilds summaries and intervals; `sort=False` preserves
  trajectories, and ordered categorical x metadata survives normalization.
- Logarithmic histogram endpoints include observations at the original range
  boundaries; logarithmic bin widths validate their ratio semantics.
- Invalid p-values are rejected, wide bar columns cannot collide with internal
  names, zero/small box whiskers handle empty candidate sets, and constant
  positive heatmaps retain positive logarithmic color limits.
- Existing-axes and heatmap rendering support the declared Matplotlib 3.9 floor.
- High-confidence t intervals remain accurate for small samples; asymptotic
  Mann–Whitney tests retain very small p-values instead of rounding to zero.
- Heatmaps with `.tracks()` save as SVG and PDF.
- `render(ax=...)` applies the plot's fonts, tick sizes, spines and line weights
  to an axes created outside SecretPlots.
- End labels and the axis title no longer overlap right-side tick labels
  (e.g. `economist-like`).
- `.compare()` brackets on split violins span both halves.
- `.kde()` works on log axes (density estimated on the log scale).
- The raincloud caption describes the box beside the cloud.

### Added
- `.copy()` for independent plot variants; `.format_axis()` for number, percent,
  currency and date ticks; `.encode_groups()` for line/scatter color plus style.
- Regression, missing-data, numerical-reference and difficult-layout checks,
  plus a CI job for minimum runtime dependency versions.
- Ground-up rewrite (3.0.0a1): themes, presets (journal, news, generic), style
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
