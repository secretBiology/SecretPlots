# SecretPlots

Easy, publication-ready plots in your own visual design — with presets for
journals (Nature, …) and newsrooms (BBC, NYT-like, FT-like, …).

> Version 1.0 is a ground-up rewrite and is in **alpha**. APIs may change.

```bash
pip install SecretPlots
```

```python
import SecretPlots as sp

sp.use(preset="nature")  # 89 mm wide, 5–7 pt text, embedded fonts
(
    sp.bar(df, x="gene", y="tpm", hue="sample", error="sd")
    .labels(y="TPM")
    .values(".1f")
    .save("fig1.pdf")
)

(
    sp.bar(sales, x="year", y="revenue")
    .chrome(title="Revenue doubled", subtitle="USD, millions", source="Annual report")
    .preset("ft-like")
    .save("chart.png")
)
```

## Ideas

* **Theme** — how a figure looks (palette from
  [SecretColors](https://github.com/secretBiology/SecretColors), fonts, grid).
* **Preset** — where it goes: physical size, font-size limits, dpi, formats,
  title/source furniture. `sp.presets.list()` shows what is available.
* **Nothing is ever missing.** Presets are partial; anything they don't define
  falls back through your theme to the built-in `"secret"` theme. Fonts fall back
  to installed alternatives, palettes extend with shades instead of repeating, and
  every substitution is reported. `plot.explain("primary")` tells you where a value
  came from; `sp.config.strict = True` turns warnings into errors.

Newsroom presets ending in `-like` are inspired by publicly visible chart
conventions; they are not affiliated with or endorsed by those publishers and use
open fallback fonts. The `bbc` preset follows the BBC's public
[bbplot](https://github.com/bbc/bbplot) style.

## Development

```bash
uv sync --group dev
uv run pre-commit install
uv run pytest --mpl
```

MIT licensed.
