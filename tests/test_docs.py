"""Run documentation examples and check that illustrated examples have assets.

Blocks on one page share a namespace (like notebook cells). If a block ends in
an expression that is a plot, it is rendered, so drawing errors surface too.
"""

import ast
import re
import textwrap
from pathlib import Path

import pytest

import SecretPlots as sp

DOCS = Path(__file__).parent.parent / "docs"
# Fences may be indented inside admonitions ("??? example") or content tabs.
_BLOCK = re.compile(
    r"^(?P<indent>[ ]*)```python\n(?P<code>.*?)^(?P=indent)```",
    re.DOTALL | re.MULTILINE,
)
PAGES = [
    page
    for page in sorted(DOCS.rglob("*.md"))
    if _BLOCK.search(page.read_text(encoding="utf-8"))
]


@pytest.mark.parametrize("page", PAGES, ids=[p.stem for p in PAGES])
def test_examples_run(
    page: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # examples may save files
    namespace: dict[str, object] = {}
    blocks = [
        textwrap.dedent(m["code"])
        for m in _BLOCK.finditer(page.read_text(encoding="utf-8"))
    ]
    assert blocks, f"no python examples in {page.name}"
    for number, code in enumerate(blocks, start=1):
        tree = ast.parse(code)
        last = tree.body[-1] if tree.body else None
        if isinstance(last, ast.Expr):
            tree.body.pop()
        exec(compile(tree, f"{page.name}[{number}]", "exec"), namespace)
        if isinstance(last, ast.Expr):
            expr = ast.Expression(last.value)
            result = eval(compile(expr, f"{page.name}[{number}]", "eval"), namespace)
            if isinstance(result, sp.Plot):
                result.render()


def test_documented_figures_exist() -> None:
    """Every rendering marker must have a unique, linked, nonempty asset."""
    seen: set[str] = set()
    for page in PAGES:
        source = page.read_text(encoding="utf-8")
        for name in re.findall(r"<!-- figure: ([a-z0-9.-]+) -->", source):
            assert name not in seen, f"duplicate figure marker: {name}"
            seen.add(name)
            filename = name if name.endswith(".png") else f"{name}.svg"
            assert f"assets/figures/{filename})" in source, page
            asset = DOCS / "assets" / "figures" / filename
            assert asset.is_file(), f"missing {asset}; run scripts/render_docs.py"
            assert asset.stat().st_size > 1000, f"empty figure: {asset}"
    assert seen, "no illustrated examples found"
