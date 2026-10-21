"""Title block (headline, subtitle) and footer (note, source) around a plot.

Space is reserved by shrinking the constrained-layout rectangle, so the plot
never overlaps the chrome regardless of font or figure size.
"""

from dataclasses import dataclass

from matplotlib.figure import Figure
from matplotlib.layout_engine import ConstrainedLayoutEngine
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from SecretPlots.core.resolve import Style
from SecretPlots.core.units import PT_PER_INCH

_LINE_HEIGHT = 1.25
_ACCENT_SIZE = (0.32, 0.06)  # width, height in inches
_MIN_PLOT_FRACTION = 0.3


@dataclass(frozen=True)
class ChromeText:
    title: str | None = None
    subtitle: str | None = None
    source: str | None = None
    note: str | None = None

    def __bool__(self) -> bool:
        return any((self.title, self.subtitle, self.source, self.note))


def _height(text: str, size_pt: float) -> float:
    return (text.count("\n") + 1) * size_pt * _LINE_HEIGHT / PT_PER_INCH


def apply_chrome(fig: Figure, style: Style, text: ChromeText) -> None:
    if not text:
        return
    width, height = fig.get_size_inches()
    theme, sizes, chrome = style.theme, style.sizes, style.chrome
    pad = chrome.padding
    left = chrome.title_align == "left"
    x = pad / width if left else 0.5
    ha = "left" if left else "center"

    # Header, top down.
    y = height - pad
    if chrome.accent_bar and (text.title or text.subtitle):
        bar_w, bar_h = _ACCENT_SIZE
        fig.add_artist(
            Rectangle(
                ((pad if left else (width - bar_w) / 2) / width, (y - bar_h) / height),
                bar_w / width,
                bar_h / height,
                transform=fig.transFigure,
                facecolor=chrome.accent_bar,
                edgecolor="none",
            )
        )
        y -= bar_h + pad
    for content, size, weight, color in (
        (text.title, sizes.title, theme.title_weight, theme.text_color),
        (text.subtitle, sizes.subtitle, "normal", theme.text_color),
    ):
        if content:
            fig.text(
                x,
                y / height,
                content,
                ha=ha,
                va="top",
                fontsize=size,
                fontweight=weight,
                color=color,
            )
            y -= _height(content, size) + pad * 0.4
    header = height - y if y < height - pad else 0.0

    # Footer, bottom up.
    y = pad
    source = f"{chrome.source_prefix}{text.source}" if text.source else None
    for content in (source, text.note):
        if content:
            fig.text(
                x,
                y / height,
                content,
                ha=ha,
                va="bottom",
                fontsize=sizes.note,
                color=theme.muted_text_color,
            )
            y += _height(content, sizes.note) + pad * 0.3
    footer = y + pad * 0.5 if y > pad else 0.0
    if footer and chrome.footer_rule:
        rule_y = (footer - pad * 0.25) / height
        fig.add_artist(
            Line2D(
                [pad / width, 1 - pad / width],
                [rule_y, rule_y],
                transform=fig.transFigure,
                color=theme.text_color,
                linewidth=theme.axis_line_width or 0.8,
            )
        )

    plot_fraction = max(_MIN_PLOT_FRACTION, 1 - (header + footer) / height)
    engine = fig.get_layout_engine()
    if isinstance(engine, ConstrainedLayoutEngine):
        engine.set(rect=(0, footer / height, 1, plot_fraction))
