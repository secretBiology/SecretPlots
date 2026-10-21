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
