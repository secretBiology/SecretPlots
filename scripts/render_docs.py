"""Render marked Markdown examples into portable SVGs for the documentation.

Run from the repository root:
    python scripts/render_docs.py [page.md ...] [--preview DIR]
Each page is a notebook-like sequence. Put ``<!-- figure: unique-name -->``
immediately after a Python fence whose final expression is a SecretPlots Plot.
Names ending in ``.png`` are written as 300 dpi PNGs (used by the README);
all others as SVG. A full run (no pages given) also deletes unreferenced figures.
"""

import ast
import os
import re
import tempfile
import textwrap
import warnings
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "sp-docs-mpl"))

import matplotlib as mpl
import matplotlib.pyplot as plt

import SecretPlots as sp

ROOT = Path(__file__).resolve().parents[1]
# Fences may be indented (inside admonitions or content tabs); the figure marker
# follows the closing fence at the same indentation.
BLOCK = re.compile(
    r"^(?P<indent>[ ]*)```python\n(?P<code>.*?)^(?P=indent)```"
    r"(?:\n(?P=indent)<!-- figure: (?P<name>[a-z0-9-]+(?:\.png)?) -->)?",
    re.MULTILINE | re.DOTALL,
)


def render(pages: list[Path] | None = None, preview: Path | None = None) -> None:
    """Execute examples in isolation; fail if a marked example cannot render.

    With no ``pages``, every page is rendered and figures no longer referenced
    by any page are deleted. With ``preview``, every figure is written there as
    a low-resolution PNG instead, leaving the documentation assets untouched.
    """
    destination = preview or ROOT / "docs" / "assets" / "figures"
    destination.mkdir(parents=True, exist_ok=True)
    names: set[str] = set()
    # Paths embed fonts, avoiding reliance on browser or Read the Docs fonts.
    mpl.rcParams.update({"svg.hashsalt": "secretplots-docs", "svg.fonttype": "path"})
    warnings.filterwarnings("ignore", category=sp.FontFallbackWarning)
    selected = pages or sorted((ROOT / "docs").rglob("*.md"))
    for page in selected:
        page = page.resolve()
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
                    code = textwrap.dedent(match["code"])
                    name = match["name"]
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
                        png = name.endswith(".png") or preview is not None
                        stem = name.removesuffix(".png")
                        # savefig bypasses publisher format warnings for web previews;
                        # plot sizing, style, and data are exactly those in the example.
                        result.fig.savefig(
                            destination / f"{stem}.{'png' if png else 'svg'}",
                            dpi=110 if preview else 300 if png else 200,
                            metadata={} if png else {"Date": None},
                        )
                        print(f"{page.relative_to(ROOT)} -> {name}", flush=True)
                    plt.close("all")
            finally:
                os.chdir(previous)
    sp.reset()
    if pages is None and preview is None:
        keep = {n if n.endswith(".png") else f"{n}.svg" for n in names}
        for stale in destination.iterdir():
            if stale.name not in keep:
                stale.unlink()
                print(f"Removed unreferenced {stale.name}")
    print(f"Rendered {len(names)} documentation figures.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", nargs="*", type=Path, help="pages (default: all)")
    parser.add_argument(
        "--preview", type=Path, help="write PNG previews to this directory instead"
    )
    args = parser.parse_args()
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
    render(args.pages or None, args.preview)
