"""Compose the README / documentation banner from rendered gallery figures.

Run from the repository root after ``python scripts/render_docs.py``:
    python scripts/render_banner.py
Writes docs/assets/banner.png. The tiles are unmodified SecretPlots output.
"""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "sp-docs-mpl"))

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "docs" / "assets" / "figures"
TILES = [
    "gallery-dose-response",
    "gallery-expression-heatmap",
    "gallery-tumour-growth",
    "gallery-raincloud",
    "gallery-volcano",
    "gallery-regression",
]
FONTS = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def banner(path: Path = ROOT / "docs" / "assets" / "banner.png") -> None:
    width, height = 16.0, 6.4
    fig = plt.figure(figsize=(width, height), dpi=150)
    plt.rcParams["font.family"] = FONTS

    background = fig.add_axes((0, 0, 1, 1), zorder=0)
    background.axis("off")
    ramp = LinearSegmentedColormap.from_list("bg", ["#0f1b24", "#182c38", "#1d2440"])
    background.imshow(
        [[0, 0.5, 1], [0.2, 0.6, 1]],
        cmap=ramp,
        aspect="auto",
        extent=(0, 1, 0, 1),
        interpolation="bicubic",
    )
    background.set_xlim(0, 1)
    background.set_ylim(0, 1)

    fig.text(0.045, 0.70, "SecretPlots", color="white", fontsize=50, fontweight="bold")
    fig.text(
        0.047,
        0.585,
        "Publication-ready scientific figures\nin a few readable lines of Python.",
        color="#c9d6dd",
        fontsize=17,
        va="top",
        linespacing=1.45,
    )
    chips = ["Nature", "Science", "Cell", "PNAS", "IEEE", "+16 presets"]
    x = 0.047
    for chip in chips:
        label = fig.text(
            x,
            0.30,
            chip,
            color="#5fd3c8",
            fontsize=11.5,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.45,rounding_size=0.8",
                "facecolor": "#ffffff10",
                "edgecolor": "#5fd3c866",
                "linewidth": 1,
            },
        )
        fig.canvas.draw()
        box = label.get_window_extent().transformed(fig.transFigure.inverted())
        x = box.x1 + 0.014
    fig.text(
        0.047,
        0.14,
        "pip install SecretPlots",
        color="#e6f3f2",
        fontsize=13,
        family="monospace",
    )

    left, right, top, bottom = 0.40, 0.975, 0.93, 0.07
    cols, rows, gap = 3, 2, 0.014
    tile_w = (right - left - gap * (cols - 1)) / cols
    tile_h = (top - bottom - gap * 2.4 * (rows - 1)) / rows
    for index, name in enumerate(TILES):
        r, c = divmod(index, cols)
        x0 = left + c * (tile_w + gap)
        y0 = top - (r + 1) * tile_h - r * gap * 2.4
        card = FancyBboxPatch(
            (x0, y0),
            tile_w,
            tile_h,
            boxstyle="round,pad=0,rounding_size=0.012",
            transform=fig.transFigure,
            facecolor="white",
            edgecolor="none",
            zorder=1,
        )
        fig.patches.append(card)
        image = mpimg.imread(FIGURES / f"{name}.png")
        inset = 0.008
        ax = fig.add_axes(
            (x0 + inset, y0 + inset * 2.5, tile_w - 2 * inset, tile_h - 5 * inset),
            zorder=2,
        )
        ax.imshow(image, interpolation="lanczos")
        ax.set_anchor("C")
        ax.axis("off")
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    banner()
