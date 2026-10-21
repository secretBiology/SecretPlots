# SecretPlots

Easy, publication-ready plots in your own visual design.

```python
import SecretPlots as sp

sp.use(preset="nature")
sp.bar(df, x="gene", y="tpm", hue="sample", error="sd").values(".1f").save("fig1.pdf")
```

## How style is decided

Every style field is looked up in these layers, first match wins:

1. your settings on the plot (`.theme(font_size=8)`, `.colors([...])`)
2. the preset's per-plot section (`[plots.bar]`)
3. the preset's theme
4. your active theme (`sp.use(theme="dark")`)
5. the built-in `"secret"` theme (defines everything)

Then the preset's limits are applied (e.g. Nature's 5–7 pt text range). Use
`plot.explain("primary")` or `plot.style_report()` to see where each value came from.
