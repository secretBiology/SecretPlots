"""MkDocs hooks: generated tables in the documentation.

``<!-- theme-fields -->`` in a page becomes a table of every ``Theme`` field
(from ``sp.theme_options()``), so the API reference never drifts from the
descriptions used at runtime.
"""

from typing import Any

import SecretPlots as sp

_MARKER = "<!-- theme-fields -->"


def _cell(text: object) -> str:
    return str(text).replace("|", "\\|")


def _default(value: object) -> str:
    if isinstance(value, tuple) and len(value) > 4:
        return f"{len(value)} values"
    if isinstance(value, tuple):
        return ", ".join(map(repr, value))
    return repr(value)


def _theme_table() -> str:
    rows = [
        "| Field | Allowed | Default | Description |",
        "|---|---|---|---|",
    ]
    for name, row in sp.theme_options().iterrows():
        rows.append(
            f"| `{name}` | {_cell(row['allowed'])} "
            f"| `{_cell(_default(row['value']))}` | {_cell(row['description'])} |"
        )
    return "\n".join(rows)


def on_page_markdown(markdown: str, **_: Any) -> str:
    if _MARKER in markdown:
        markdown = markdown.replace(_MARKER, _theme_table())
    return markdown
