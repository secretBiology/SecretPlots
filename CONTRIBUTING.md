# Contributing

1. `uv sync --group dev && uv run pre-commit install`
2. Make your change with tests (`tests/` mirrors `src/SecretPlots/`).
3. `uv run ruff check . && uv run ruff format . && uv run mypy && uv run pytest --mpl`

## Adding a preset

Presets are TOML files in `src/SecretPlots/presets/data/{journals,news,generic}/`.
Journal presets must cite the publisher's official author guidelines in
`source_url` and record `verified_on`. Newsroom presets that are not based on an
official public style must use the `-like` suffix and open fallback fonts.

## Image tests

Image baselines live in `tests/baseline/`. Regenerate after an intentional visual
change with `uv run pytest --mpl-generate-path=tests/baseline` and review the diff.

## Documentation and figures

The site uses MkDocs Material and is configured for Read the Docs in
`.readthedocs.yaml`, following the [Read the Docs MkDocs configuration](https://docs.readthedocs.com/platform/stable/intro/mkdocs.html).
The hosted build installs the package and `docs/requirements.txt`, regenerates
figures, and builds with warnings treated as errors.

```bash
uv sync --group docs --group dev
uv run python scripts/render_docs.py
uv run pytest tests/test_docs.py
uv run mkdocs build --strict
uv run mkdocs serve
```

For the pinned documentation tool versions used on Read the Docs, install
`docs/requirements.txt` into your build environment. The `docs` dependency
group is useful for testing compatibility with newer documentation tools.

Python fences on each page run in order, like notebook cells. Use seeded
synthetic data and include the setup on the same page. To illustrate a block,
make its final expression a SecretPlots plot and add a marker immediately after
the closing fence:

````markdown
```python
sp.bar({"Control": 12, "Treatment": 19}).values()
```
<!-- figure: descriptive-unique-name -->

![Explain what the reader should see.](assets/figures/descriptive-unique-name.svg)

*Name the options responsible for the visible effect.*
````

On pages in `docs/plots/`, use `../assets/figures/` in the image link.
`python scripts/render_docs.py` executes the examples in temporary directories
and writes the marked plots to `docs/assets/figures/`. Commit these images so
GitHub previews and offline builds also display them. SVGs embed glyph paths
and omit timestamps. Use a `.png` suffix in the marker and link for an explicit
200 dpi raster preview; the annotation-track heatmap uses this because its
annotation legend currently needs the raster renderer.

Keep the caption accurate and add meaningful alt text. Do not change a preview's
style behind the reader's back: include styling in its displayed code. Preview
the gallery and long guides at desktop and mobile widths after layout changes.
The documentation tests execute all Python fences (including new pages) and
check that every figure marker has a matching linked asset.
