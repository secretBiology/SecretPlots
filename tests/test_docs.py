"""Run every ```python example in docs/plots/*.md so the docs can't go stale.

Blocks on one page share a namespace (like notebook cells). If a block ends in
an expression that is a plot, it is rendered, so drawing errors surface too.
"""

import ast
import re
from pathlib import Path

import pytest

import SecretPlots as sp

DOCS = Path(__file__).parent.parent / "docs" / "plots"
PAGES = [*sorted(DOCS.glob("*.md")), DOCS.parent / "usage.md"]
_BLOCK = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)


@pytest.mark.parametrize("page", PAGES, ids=[p.stem for p in PAGES])
def test_examples_run(
    page: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # examples may save files
    namespace: dict[str, object] = {}
    blocks = _BLOCK.findall(page.read_text(encoding="utf-8"))
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
