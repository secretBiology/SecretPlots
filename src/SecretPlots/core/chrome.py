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
from SecretPlots.errors import DataShapeError

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


def _wrap(
    fig: Figure, content: str, size: float, weight: str | None, available: float
) -> tuple[str, float]:
    """Wrap using rendered glyph widths, including long unbroken words."""
    probe = fig.text(0, 0, "", fontsize=size, fontweight=weight)
    limit = available * fig.dpi

    def fits(value: str) -> bool:
        probe.set_text(value)
        return bool(probe.get_window_extent().width <= limit)

    lines: list[str] = []
    try:
        for paragraph in content.split("\n"):
            current = ""
            for word in paragraph.split():
                candidate = f"{current} {word}" if current else word
                if fits(candidate):
                    current = candidate
                    continue
                if current:
                    lines.append(current)
                current = ""
                for char in word:
                    if current and not fits(current + char):
                        lines.append(current)
                        current = ""
                    current += char
            lines.append(current)
        wrapped = "\n".join(lines)
        probe.set_text(wrapped)
        height = max(_height(wrapped, size), probe.get_window_extent().height / fig.dpi)
        return wrapped, height
    finally:
        probe.remove()


def apply_chrome(fig: Figure, style: Style, text: ChromeText) -> None:
    if not text:
        return
    width, height = fig.get_size_inches()
    theme, sizes, chrome = style.theme, style.sizes, style.chrome
    pad = chrome.padding
    left = chrome.title_align == "left"
    x = pad / width if left else 0.5
    ha = "left" if left else "center"

    available = width - 2 * pad
    if available <= 0:
        raise DataShapeError("Figure is too narrow for its text; use .size(width=...)")
    header_items = [
        (*_wrap(fig, content, size, weight, available), size, weight, color)
        for content, size, weight, color in (
            (text.title, sizes.title, theme.title_weight, theme.text_color),
            (text.subtitle, sizes.subtitle, "normal", theme.text_color),
        )
        if content
    ]
    source = f"{chrome.source_prefix}{text.source}" if text.source else None
    footer_items = [
        _wrap(fig, content, sizes.note, "normal", available)
        for content in (source, text.note)
        if content
    ]
    header_needed = sum(h + pad * 0.4 for _, h, *_ in header_items)
    footer_needed = sum(h + pad * 0.3 for _, h in footer_items)
    accent = sum(_ACCENT_SIZE[1:]) + pad if chrome.accent_bar and header_items else 0
    if header_needed + footer_needed + accent + 3 * pad > height * (
        1 - _MIN_PLOT_FRACTION
    ):
        raise DataShapeError(
            "Title/source text leaves too little plotting space. "
            "Use .size(height='5in'), increase the width, "
            "or shorten the text."
        )

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
    for content, text_height, size, weight, color in header_items:
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
            y -= text_height + pad * 0.4
    header = height - y if y < height - pad else 0.0

    # Footer, bottom up.
    y = pad
    for content, text_height in footer_items:
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
            y += text_height + pad * 0.3
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
