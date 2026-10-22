"""Render marked Markdown examples into portable SVGs for the documentation.

Run from the repository root: python scripts/render_docs.py
Each page is a notebook-like sequence. Put ``<!-- figure: unique-name -->``
immediately after a Python fence whose final expression is a SecretPlots Plot.
"""

import ast
import os
import re
import tempfile
import warnings
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "sp-docs-mpl"))

import matplotlib as mpl
import matplotlib.pyplot as plt

import SecretPlots as sp

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(
    r"^```python\n(.*?)^```(?:\n<!-- figure: ([a-z0-9-]+(?:\.png)?) -->)?",
    re.MULTILINE | re.DOTALL,
)


def render() -> None:
    """Execute examples in isolation; fail if a marked example cannot render."""
    destination = ROOT / "docs" / "assets" / "figures"
    destination.mkdir(parents=True, exist_ok=True)
    names: set[str] = set()
    # Paths embed fonts, avoiding reliance on browser or Read the Docs fonts.
    mpl.rcParams.update({"svg.hashsalt": "secretplots-docs", "svg.fonttype": "path"})
    warnings.filterwarnings("ignore", category=sp.FontFallbackWarning)
    for page in sorted((ROOT / "docs").rglob("*.md")):
        source = page.read_text(encoding="utf-8")
        if "<!-- figure:" not in source:
            continue
        sp.reset()
        namespace: dict[str, object] = {}
        with tempfile.TemporaryDirectory(prefix="secretplots-docs-") as directory:
            previous = Path.cwd()
            os.chdir(directory)
            try:
                for number, match in enumerate(BLOCK.finditer(source), start=1):
                    code, name = match.groups()
                    filename = f"{page.name}[{number}]"
                    tree = ast.parse(code, filename=filename)
                    last = tree.body[-1] if tree.body else None
                    if isinstance(last, ast.Expr):
                        tree.body.pop()
                    exec(compile(tree, filename, "exec"), namespace)
                    result = None
                    if isinstance(last, ast.Expr):
                        result = eval(
                            compile(ast.Expression(last.value), filename, "eval"),
                            namespace,
                        )
                    if name:
                        if name in names:
                            raise ValueError(f"Duplicate figure name: {name}")
                        if not isinstance(result, sp.Plot):
                            raise TypeError(f"{filename}: figure must end with a Plot")
                        names.add(name)
                        # savefig bypasses publisher format warnings for web previews;
                        # plot sizing, style, and data are exactly those in the example.
                        result.fig.savefig(
                            destination
                            / (name if name.endswith(".png") else f"{name}.svg"),
                            dpi=200,
                            metadata={} if name.endswith(".png") else {"Date": None},
                        )
                        print(f"{page.relative_to(ROOT)} -> {name}", flush=True)
                    plt.close("all")
            finally:
                os.chdir(previous)
    sp.reset()
    print(f"Rendered {len(names)} documentation figures.")


if __name__ == "__main__":
    render()
